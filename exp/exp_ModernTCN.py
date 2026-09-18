from data_provider.data_factory import data_provider
from exp.exp_basic import Exp_Basic
from models import ModernTCN
from utils.tools import EarlyStopping, adjust_learning_rate, visual, test_params_flop
from utils.metrics import metric

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch import optim
from torch.optim import lr_scheduler

import math
import os
import time

import warnings
import matplotlib.pyplot as plt
import numpy as np

warnings.filterwarnings('ignore')


class Exp_Main(Exp_Basic):
    def __init__(self, args):
        super(Exp_Main, self).__init__(args)

    def _build_model(self):
        model_dict = {
            'ModernTCN': ModernTCN,
        }
        # When horizon aggregation is enabled the model head must output a
        # single value (the predicted aggregate).  Temporarily set pred_len=1
        # so that ModernTCN builds with target_window=1, then restore the
        # original value so the data loader still loads the full pred_len
        # future steps (needed to build the ground truth in _get_target).
        if getattr(self.args, 'aggregate_horizon', False):
            orig_pred_len = self.args.pred_len
            self.args.pred_len = 1
            model = model_dict[self.args.model].Model(self.args).float()
            self.args.pred_len = orig_pred_len
        else:
            model = model_dict[self.args.model].Model(self.args).float()

        if self.args.use_multi_gpu and self.args.use_gpu:
            model = nn.DataParallel(model, device_ids=self.args.device_ids)
        return model

    def _get_target(self, batch_y, f_dim):
        """Slice the future window from batch_y and optionally aggregate it.

        batch_y carries ln(RV), so log-sum-exp less ln(h) is
        ln( (1/h) * Sum_{k=1..h} RV_{t+k} ) -- the benchmark target defined
        in utils/target_agg.py and shared with HAR-RV and N-HAR. It replaces
        the earlier mean-pool, which averaged logs instead of the variances
        themselves; for pred_len=1 the two coincide.

        Subtracting ln(h) keeps the target on the input series' scale, which
        matters here because RevIN de-normalises with the look-back window's
        own mean: the head then has a small constant to learn rather than
        ln(h)/sigma.
        """
        y = batch_y[:, -self.args.pred_len:, f_dim:].to(self.device)
        if getattr(self.args, 'aggregate_horizon', False):
            h = y.shape[1]                       # == pred_len, the axis reduced
            y = torch.logsumexp(y, dim=1, keepdim=True) - math.log(h)
        return y

    def _model_label(self):
        """The model name this run reports itself as in its loss file.

        It has to separate every variant that trains differently, because
        dm_mcs_run.py groups per-observation losses by
        (pair, horizon, model, date) and averages them: two variants sharing a
        label are silently merged into one row instead of being compared, and
        the one whose name never appears is dropped from the panel entirely.
        These names are what the benchmark notebook's MODELS list expects.
        """
        if not getattr(self.args, 'use_events', False):
            return 'ModernTCN'
        name = 'FiLM-TCN'
        if getattr(self.args, 'event_linear', False):
            name += '-L1'
        if getattr(self.args, 'event_untie', False):
            name += '-U'
        return name

    def _save_losses(self, setting, test_data, preds, trues):
        """Write this run's per-observation TEST losses for the DM / MCS stage.

        One row per forecast origin, keyed by the origin's calendar date so
        dm_mcs_run.py can inner-join the deep models with HAR-RV and N-HAR,
        which index their rows by the same predictor date.

        With --aggregate_horizon the prediction is already a single value per
        origin. Without it the model emits pred_len steps, and the losses are
        averaged over the horizon so every model still contributes exactly one
        number per origin.
        """
        loss_dir = getattr(self.args, 'loss_dir', None)
        if not loss_dir:
            return
        if not hasattr(test_data, 'origin_dates'):
            print('losses: dataset exposes no origin_dates(), skipping')
            return

        dates = np.asarray(test_data.origin_dates())
        if len(preds) < len(dates):
            # the test loader is sequential and unshuffled, so when it drops its
            # final partial batch (data_factory.DROP_LAST_TEST) the scored
            # windows are the FIRST len(preds) origins and the tail is missing
            print(f'losses: {len(dates) - len(preds)} of {len(dates)} test windows '
                  f'were not scored (the test loader dropped its last partial '
                  f'batch); writing the {len(preds)} that were')
            dates = dates[:len(preds)]
        elif len(preds) != len(dates):
            print(f'losses: {len(preds)} predictions vs {len(dates)} origin dates '
                  f'-- skipping rather than writing a misaligned file')
            return

        p = preds.reshape(len(preds), -1).astype(np.float64)
        t = trues.reshape(len(trues), -1).astype(np.float64)
        ratio = np.exp(t - p)                       # RV_actual / RV_predicted
        with np.errstate(over='ignore', invalid='ignore'):
            qlike = ratio - np.log(ratio) - 1.0

        pair = os.path.splitext(os.path.basename(self.args.data_path))[0]
        for suffix in ('_lnRV', '_ln_RV', '_RV'):
            if pair.endswith(suffix):
                pair = pair[: -len(suffix)]
                break

        df = pd.DataFrame({
            'pair': pair,
            'horizon': int(self.args.pred_len),
            'model': self._model_label(),
            'seed': getattr(self.args, 'run_seed', -1),
            'date': pd.to_datetime(dates),
            'se': ((p - t) ** 2).mean(axis=1),
            'ae': np.abs(p - t).mean(axis=1),
            'qlike': np.nanmean(qlike, axis=1),
        })
        os.makedirs(loss_dir, exist_ok=True)
        out = os.path.join(loss_dir, f'{setting}.csv')
        df.to_csv(out, index=False)
        print(f'losses -> {out}  ({len(df)} origins)')

    def _unpack_batch(self, batch):
        """Event datasets yield 6 tensors (past/future events last), plain ones 4."""
        if len(batch) == 6:
            batch_x, batch_y, batch_x_mark, batch_y_mark, event_x, event_y = batch
            event_x = event_x.float().to(self.device)
            event_y = event_y.float().to(self.device)
        else:
            batch_x, batch_y, batch_x_mark, batch_y_mark = batch
            event_x = event_y = None
        return batch_x, batch_y, batch_x_mark, batch_y_mark, event_x, event_y

    def _get_data(self, flag):
        data_set, data_loader = data_provider(self.args, flag)
        return data_set, data_loader

    def _select_optimizer(self):
        model_optim = optim.Adam(self.model.parameters(), lr=self.args.learning_rate)
        return model_optim

    def _select_criterion(self):
        criterion = nn.MSELoss()
        return criterion

    def _event_l1(self):
        """--event_l1 * |W_event_linear|_1, as a term for the TRAINING loss.

        Returns None when there is nothing to penalise, so the reported
        train/val/test losses stay pure MSE and remain comparable with every
        other row of the benchmark.
        """
        lam = float(getattr(self.args, 'event_l1', 0.0) or 0.0)
        if lam <= 0:
            return None
        core = self.model.module if isinstance(self.model, nn.DataParallel) else self.model
        if not hasattr(core, 'event_l1'):
            return None
        pen = core.event_l1()
        return None if pen is None else lam * pen

    def vali(self, vali_data, vali_loader, criterion):
        total_loss = []
        self.model.eval()
        with torch.no_grad():
            for i, batch in enumerate(vali_loader):
                batch_x, batch_y, batch_x_mark, batch_y_mark, event_x, event_y = self._unpack_batch(batch)
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_y.float()

                batch_x_mark = batch_x_mark.float().to(self.device)
                batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if 'Linear' in self.args.model or 'TST' in self.args.model:
                            outputs = self.model(batch_x)
                        elif 'TCN' in self.args.model:
                            outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                            # outputs = self.model(batch_x)   #if decide not to use time stamp, use this code
                        else:
                            if self.args.output_attention:
                                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                            else:
                                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                else:
                    if 'Linear' in self.args.model or 'TST' in self.args.model:
                        outputs = self.model(batch_x)
                    elif 'TCN' in self.args.model:
                        outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                        # outputs = self.model(batch_x)   #if decide not to use time stamp, use this code
                    else:
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                f_dim = -1 if self.args.features == 'MS' else 0
                outputs = outputs[:, -self.args.pred_len:, f_dim:]
                batch_y = self._get_target(batch_y, f_dim)

                pred = outputs.detach().cpu()
                true = batch_y.detach().cpu()

                loss = criterion(pred, true)

                total_loss.append(loss)
        total_loss = np.average(total_loss)
        self.model.train()
        return total_loss

    def train(self, setting):
        train_data, train_loader = self._get_data(flag='train')
        vali_data, vali_loader = self._get_data(flag='val')
        test_data, test_loader = self._get_data(flag='test')

        path = os.path.join(self.args.checkpoints, setting)
        if not os.path.exists(path):
            os.makedirs(path)

        time_now = time.time()

        train_steps = len(train_loader)
        early_stopping = EarlyStopping(patience=self.args.patience, verbose=True)

        model_optim = self._select_optimizer()
        criterion = self._select_criterion()

        if self.args.use_amp:
            scaler = torch.cuda.amp.GradScaler()

        scheduler = lr_scheduler.OneCycleLR(optimizer=model_optim,
                                            steps_per_epoch=train_steps,
                                            pct_start=self.args.pct_start,
                                            epochs=self.args.train_epochs,
                                            max_lr=self.args.learning_rate)

        for epoch in range(self.args.train_epochs):
            iter_count = 0
            train_loss = []

            self.model.train()
            epoch_time = time.time()
            for i, batch in enumerate(train_loader):
                batch_x, batch_y, batch_x_mark, batch_y_mark, event_x, event_y = self._unpack_batch(batch)
                iter_count += 1
                model_optim.zero_grad()
                batch_x = batch_x.float().to(self.device)

                batch_y = batch_y.float().to(self.device)
                batch_x_mark = batch_x_mark.float().to(self.device)
                batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)

                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if 'Linear' in self.args.model or 'TST' in self.args.model:
                            outputs = self.model(batch_x)
                        elif 'TCN' in self.args.model:
                            outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                            #outputs = self.model(batch_x)   #if decide not to use time stamp, use this code
                        else:
                            if self.args.output_attention:
                                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                            else:
                                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)

                        f_dim = -1 if self.args.features == 'MS' else 0
                        outputs = outputs[:, -self.args.pred_len:, f_dim:]
                        batch_y = self._get_target(batch_y, f_dim)
                        loss = criterion(outputs, batch_y)
                        train_loss.append(loss.item())
                        # logged above as pure MSE; the penalty enters only the
                        # tensor that gets backpropagated
                        pen = self._event_l1()
                        if pen is not None:
                            loss = loss + pen
                else:
                    if 'Linear' in self.args.model or 'TST' in self.args.model:
                        outputs = self.model(batch_x)
                    elif 'TCN' in self.args.model:
                        outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                        # outputs = self.model(batch_x)   #if decide not to use time stamp, use this code
                    else:
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]

                        else:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark, batch_y)
                    # print(outputs.shape,batch_y.shape)
                    f_dim = -1 if self.args.features == 'MS' else 0
                    outputs = outputs[:, -self.args.pred_len:, f_dim:]
                    batch_y = self._get_target(batch_y, f_dim)
                    loss = criterion(outputs, batch_y)
                    train_loss.append(loss.item())
                    pen = self._event_l1()
                    if pen is not None:
                        loss = loss + pen

                if (i + 1) % 100 == 0:
                    print("\titers: {0}, epoch: {1} | loss: {2:.7f}".format(i + 1, epoch + 1, loss.item()))
                    speed = (time.time() - time_now) / iter_count
                    left_time = speed * ((self.args.train_epochs - epoch) * train_steps - i)
                    print('\tspeed: {:.4f}s/iter; left time: {:.4f}s'.format(speed, left_time))
                    iter_count = 0
                    time_now = time.time()

                if self.args.use_amp:
                    scaler.scale(loss).backward()
                    scaler.step(model_optim)
                    scaler.update()
                else:
                    loss.backward()
                    model_optim.step()

                if self.args.lradj == 'TST':
                    adjust_learning_rate(model_optim, scheduler, epoch + 1, self.args, printout=False)
                    scheduler.step()

            print("Epoch: {} cost time: {}".format(epoch + 1, time.time() - epoch_time))
            train_loss = np.average(train_loss)
            vali_loss = self.vali(vali_data, vali_loader, criterion)
            test_loss = self.vali(test_data, test_loader, criterion)

            print("Epoch: {0}, Steps: {1} | Train Loss: {2:.7f} Vali Loss: {3:.7f} Test Loss: {4:.7f}".format(
                epoch + 1, train_steps, train_loss, vali_loss, test_loss))
            early_stopping(vali_loss, self.model, path)
            if early_stopping.early_stop:
                print("Early stopping")
                break

            if self.args.lradj != 'TST':
                adjust_learning_rate(model_optim, scheduler, epoch + 1, self.args)
            else:
                print('Updating learning rate to {}'.format(scheduler.get_last_lr()[0]))

        best_model_path = path + '/' + 'checkpoint.pth'
        self.model.load_state_dict(torch.load(best_model_path))

        return self.model

    def test(self, setting, test=0):
        test_data, test_loader = self._get_data(flag='test')

        if test:
            print('loading model')
            self.model.load_state_dict(torch.load(os.path.join('./checkpoints/' + setting, 'checkpoint.pth')))

        preds = []
        trues = []
        inputx = []
        folder_path = './test_results/' + setting + '/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        self.model.eval()
        if self.args.call_structural_reparam and hasattr(self.model, 'structural_reparam'):
            self.model.structural_reparam()

        with torch.no_grad():
            for i, batch in enumerate(test_loader):
                batch_x, batch_y, batch_x_mark, batch_y_mark, event_x, event_y = self._unpack_batch(batch)
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_y.float().to(self.device)

                batch_x_mark = batch_x_mark.float().to(self.device)
                batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp = torch.zeros_like(batch_y[:, -self.args.pred_len:, :]).float()
                dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if 'Linear' in self.args.model or 'TST' in self.args.model:
                            outputs = self.model(batch_x)
                        elif 'TCN' in self.args.model:
                            outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                            # outputs = self.model(batch_x)   #if decide not to use time stamp, use this code
                        else:
                            if self.args.output_attention:
                                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                            else:
                                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                else:
                    if 'Linear' in self.args.model or 'TST' in self.args.model:
                        outputs = self.model(batch_x)
                    elif 'TCN' in self.args.model:
                        outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                        # outputs = self.model(batch_x)   #if decide not to use time stamp, use this code
                    else:
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]

                        else:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)

                f_dim = -1 if self.args.features == 'MS' else 0
                # print(outputs.shape,batch_y.shape)
                outputs = outputs[:, -self.args.pred_len:, f_dim:]
                batch_y = self._get_target(batch_y, f_dim)
                outputs = outputs.detach().cpu().numpy()
                batch_y = batch_y.detach().cpu().numpy()

                pred = outputs  # outputs.detach().cpu().numpy()  # .squeeze()
                true = batch_y  # batch_y.detach().cpu().numpy()  # .squeeze()

                preds.append(pred)
                trues.append(true)
                inputx.append(batch_x.detach().cpu().numpy())
                if i % 20 == 0:
                    input = batch_x.detach().cpu().numpy()
                    gt = np.concatenate((input[0, :, -1], true[0, :, -1]), axis=0)
                    # not `pd`: that shadows the pandas import used below
                    pv = np.concatenate((input[0, :, -1], pred[0, :, -1]), axis=0)
                    visual(gt, pv, os.path.join(folder_path, str(i) + '.pdf'))

        if self.args.test_flop:
            test_params_flop((batch_x.shape[1], batch_x.shape[2]))
            exit()
        # the test loader keeps its final partial batch (data_factory.py), so the
        # per-batch arrays are ragged in their first axis -- concatenate, don't stack
        preds = np.concatenate(preds, axis=0)
        trues = np.concatenate(trues, axis=0)
        inputx = np.concatenate(inputx, axis=0)

        # result save
        folder_path = './results/' + setting + '/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        mae, mse, rmse, mape, mspe, rse, corr, qlike = metric(preds, trues)
        print('mse:{}, mae:{}, rse:{}, qlike:{}'.format(mse, mae, rse, qlike))
        f = open("result.txt", 'a')
        f.write(setting + "  \n")
        f.write('mse:{}, mae:{}, rse:{}, qlike:{}'.format(mse, mae, rse, qlike))
        f.write('\n')
        f.write('\n')
        f.close()

        self._save_losses(setting, test_data, preds, trues)

        # np.save(folder_path + 'metrics.npy', np.array([mae, mse, rmse, mape, mspe,rse, corr]))
        np.save(folder_path + 'pred.npy', preds)
        # np.save(folder_path + 'true.npy', trues)
        # np.save(folder_path + 'x.npy', inputx)
        return {'mse': float(mse), 'mae': float(mae), 'rse': float(rse), 'qlike': float(qlike)}

    def predict(self, setting, load=False):
        pred_data, pred_loader = self._get_data(flag='pred')

        if load:
            path = os.path.join(self.args.checkpoints, setting)
            best_model_path = path + '/' + 'checkpoint.pth'
            self.model.load_state_dict(torch.load(best_model_path))

        preds = []

        self.model.eval()
        with torch.no_grad():
            for i, batch in enumerate(pred_loader):
                batch_x, batch_y, batch_x_mark, batch_y_mark, event_x, event_y = self._unpack_batch(batch)
                batch_x = batch_x.float().to(self.device)
                batch_y = batch_y.float()
                batch_x_mark = batch_x_mark.float().to(self.device)
                batch_y_mark = batch_y_mark.float().to(self.device)

                # decoder input
                dec_inp = torch.zeros([batch_y.shape[0], self.args.pred_len, batch_y.shape[2]]).float().to(
                    batch_y.device)
                dec_inp = torch.cat([batch_y[:, :self.args.label_len, :], dec_inp], dim=1).float().to(self.device)
                # encoder - decoder
                if self.args.use_amp:
                    with torch.cuda.amp.autocast():
                        if 'Linear' in self.args.model or 'TST' in self.args.model:
                            outputs = self.model(batch_x)
                        elif 'TCN' in self.args.model:
                            outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                            # outputs = self.model(batch_x)   #if decide not to use time stamp, use this code
                        else:
                            if self.args.output_attention:
                                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                            else:
                                outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                else:
                    if 'Linear' in self.args.model or 'TST' in self.args.model:
                        outputs = self.model(batch_x)
                    elif 'TCN' in self.args.model:
                        outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                        # outputs = self.model(batch_x)   #if decide not to use time stamp, use this code
                    else:
                        if self.args.output_attention:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)[0]
                        else:
                            outputs = self.model(batch_x, batch_x_mark, dec_inp, batch_y_mark)
                pred = outputs.detach().cpu().numpy()  # .squeeze()
                preds.append(pred)

        preds = np.array(preds)
        preds = preds.reshape(-1, preds.shape[-2], preds.shape[-1])

        # result save
        folder_path = './results/' + setting + '/'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        np.save(folder_path + 'real_prediction.npy', preds)

        return
