#!/usr/bin/env python3
"""
Bayesian hyperparameter search for FiLM-TCN with Optuna, scored on the TEST split.

FiLM-TCN is ModernTCN with the news-event conditioning switched on
(``--use_events``): past releases enter the backbone as their own channel
(``--event_fusion channel``) and the horizon's KNOWN release calendar
FiLM-conditions the head.  exp/exp_ModernTCN.py labels exactly that
configuration 'FiLM-TCN', and dm_mcs_run.py lists it under that name.

How this differs from tune.py
-----------------------------
tune.py watches the VALIDATION split (2022-2023): early stopping, the saved
checkpoint, Optuna's pruning reports and the returned objective all come from
it, and the test years are never touched during the search.  This script
watches the TEST split (2024-) for all four of those instead.  Everything else
-- search space, TPE sampler, median pruner, resumable sqlite study, outputs --
matches tune.py, so the two protocols are directly comparable.

*** Read this before quoting any number this script prints. ***
Choosing the hyperparameters, the stopping epoch and the checkpoint on the test
years makes the resulting test metric a selection-biased, in-sample quantity:
it is the best of (n_trials x train_epochs) peeks at the test set, so it is
optimistic by construction and is NOT out-of-sample forecast accuracy.  It
answers "how well could FiLM-TCN have done on 2024-25 with hindsight" -- an
oracle-tuning upper bound, useful as a diagnostic or as a reviewer's
sensitivity check, but not a number to drop into a like-for-like table against
HAR-RV, N-HAR or the val-tuned ModernTCN.  To keep that readable, the
validation metrics are still computed every epoch and stored on every trial
(user attributes ``val_*``) purely as a reference, and ``--select_on val``
reproduces tune.py's honest protocol with this same base config and outputs.

Base configuration
------------------
The fixed settings and the starting point of the search are the tuned h=1
FiLM-TCN run:

    python run.py --is_training 1 --model_id ModernTCN_h1 --model ModernTCN \
      --data custom --root_path ./data/ --data_path EURUSD_lnRV.csv \
      --features S --target lnRV --enc_in 1 --dec_in 1 --c_out 1 \
      --aggregate_mean --seq_len 70 --pred_len 1 \
      --patch_size 16 --patch_stride 8 --ffn_ratio 2 \
      --num_blocks 2 2 2 2 --large_size 27 27 27 27 --small_size 5 5 5 5 \
      --dims 32 32 32 32 --dw_dims 32 32 32 32 \
      --dropout 0.5 --head_dropout 0.13413677333143775 --revin 1 \
      --use_multi_scale False --lradj TST --pct_start 0.3 \
      --learning_rate 0.0063484758647924695 --batch_size 256 \
      --train_epochs 40 --patience 8 --num_workers 0 --itr 5 \
      --use_events --event_dim 16 --event_fusion channel

Its searchable values are in BASE_PARAMS below and are enqueued as trial 0, so
the study always contains the config it started from and every later trial is
scored against it.  Its non-searchable settings (dataset, horizon, aggregation,
epoch budget, patience, schedule, event fusion) are this script's CLI defaults.

Usage
-----
    python tune_filmtcn.py                         # h=1, EURUSD, 50 trials, test-selected
    python tune_filmtcn.py --pred_len 5 --n_trials 80
    python tune_filmtcn.py --objective qlike       # search QLIKE instead of MSE
    python tune_filmtcn.py --select_on val         # tune.py's protocol, same base config
    python tune_filmtcn.py --n_seeds 3             # average each trial over 3 seeds

Results land in <output_dir>/<study_name>/: study.db (resume by re-running the
same command), best_params.json, all_trials.csv, best_command.sh and the Optuna
plots.  --reset deletes the study first; do that after editing the search space.
"""

import argparse
import copy
import json
import os
import random
import shutil
import sys
import warnings

import numpy as np
import torch
from torch.optim import lr_scheduler
from torch.utils.data import DataLoader

warnings.filterwarnings('ignore')

import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exp.exp_ModernTCN import Exp_Main
from utils.metrics import metric
from utils.tools import EarlyStopping, adjust_learning_rate
from data_provider.event_preprocessing import (
    DEFAULT_MIN_DAYS, DEFAULT_ON_NONTRADING,
    count_event_features, event_kwargs_from_args, resolve_event_path)


# ---------------------------------------------------------------------------
# Search space -- identical to tune.py's, so a test-selected study and a
# val-selected one explore exactly the same set of configs.
# ---------------------------------------------------------------------------

CHOICES = {
    'seq_len':      [22, 35, 70, 180],
    'patch_size':   [4, 8, 16, 32],
    'patch_stride': [2, 4, 8],
    'dim':          [32, 64, 128, 256],
    'large_size':   [13, 27, 31, 51],
    'small_size':   [3, 5, 7],   # always <= large_size
    'batch_size':   [64, 128, 256, 512],
    'revin':        [0, 1],
    'event_dim':    [4, 8, 16],
}
RANGES = {
    'ffn_ratio':     (1, 4),      # int
    'num_blocks':    (1, 3),      # int
    'dropout':       (0.0, 0.5),  # float
    'head_dropout':  (0.0, 0.5),  # float
    'learning_rate': (1e-5, 1e-2),  # float, log scale
}

# The searchable half of the base config above: enqueued as the study's first
# trial so the search starts from a known-good point instead of a random one.
BASE_PARAMS = {
    'seq_len':       70,
    'patch_size':    16,
    'patch_stride':  8,
    'dim':           32,
    'ffn_ratio':     2,
    'large_size':    27,
    'small_size':    5,
    'num_blocks':    2,
    'dropout':       0.5,
    'head_dropout':  0.13413677333143775,
    'learning_rate': 0.0063484758647924695,
    'batch_size':    256,
    'revin':         1,
    'event_dim':     16,
}

METRICS = ('mse', 'mae', 'rse', 'qlike')   # all four: smaller is better


def check_base_params():
    """A base value outside the search space would make trial 0 unreachable."""
    for k, allowed in CHOICES.items():
        if BASE_PARAMS[k] not in allowed:
            raise ValueError(f'BASE_PARAMS[{k!r}]={BASE_PARAMS[k]!r} is not in CHOICES[{k!r}]={allowed}')
    for k, (lo, hi) in RANGES.items():
        if not lo <= BASE_PARAMS[k] <= hi:
            raise ValueError(f'BASE_PARAMS[{k!r}]={BASE_PARAMS[k]!r} is outside RANGES[{k!r}]={(lo, hi)}')


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def sample_params(trial: optuna.Trial, use_events: bool) -> dict:
    """One draw from the search space, as a flat dict of raw Optuna values."""
    p = {
        'seq_len':       trial.suggest_categorical('seq_len',      CHOICES['seq_len']),
        'patch_size':    trial.suggest_categorical('patch_size',   CHOICES['patch_size']),
        # Optuna requires a categorical's choice set to be the same in every
        # trial, so patch_stride is always drawn from the full list and clamped
        # to patch_size in apply_params rather than filtered here.
        'patch_stride':  trial.suggest_categorical('patch_stride', CHOICES['patch_stride']),
        'dim':           trial.suggest_categorical('dim',          CHOICES['dim']),
        'ffn_ratio':     trial.suggest_int('ffn_ratio',  *RANGES['ffn_ratio']),
        'large_size':    trial.suggest_categorical('large_size',   CHOICES['large_size']),
        'small_size':    trial.suggest_categorical('small_size',   CHOICES['small_size']),
        'num_blocks':    trial.suggest_int('num_blocks', *RANGES['num_blocks']),
        'dropout':       trial.suggest_float('dropout',      *RANGES['dropout']),
        'head_dropout':  trial.suggest_float('head_dropout', *RANGES['head_dropout']),
        'learning_rate': trial.suggest_float('learning_rate', *RANGES['learning_rate'], log=True),
        'batch_size':    trial.suggest_categorical('batch_size',   CHOICES['batch_size']),
        # use_multi_scale stays False: forward_feature never calls the
        # lat/smooth/upsample layers, so True is a head-size mismatch at runtime
        'revin':         trial.suggest_categorical('revin',        CHOICES['revin']),
    }
    if use_events:
        # event_fusion / event_past / event_future are fixed by the base config;
        # only the event embedding width is searched
        p['event_dim'] = trial.suggest_categorical('event_dim', CHOICES['event_dim'])
    return p


def apply_params(cfg: argparse.Namespace, params: dict) -> argparse.Namespace:
    """Write one draw into a config namespace (ModernTCN wants per-stage lists)."""
    cfg.seq_len         = params['seq_len']
    cfg.patch_size      = params['patch_size']
    cfg.patch_stride    = min(params['patch_stride'], params['patch_size'])
    cfg.dims            = [params['dim']] * 4
    cfg.dw_dims         = [params['dim']] * 4
    cfg.ffn_ratio       = params['ffn_ratio']
    cfg.large_size      = [params['large_size']] * 4
    cfg.small_size      = [params['small_size']] * 4
    cfg.num_blocks      = [params['num_blocks']] * 4
    cfg.dropout         = params['dropout']
    cfg.head_dropout    = params['head_dropout']
    cfg.learning_rate   = params['learning_rate']
    cfg.batch_size      = params['batch_size']
    cfg.use_multi_scale = False
    cfg.revin           = params['revin']
    if cfg.use_events:
        cfg.event_dim = params['event_dim']
    return cfg


# ---------------------------------------------------------------------------
# Experiment: training whose model selection watches a split we choose
# ---------------------------------------------------------------------------

class SelectOnSplitExp(Exp_Main):
    """Exp_Main with the monitored split, Optuna reporting and pruning wired in.

    ``args.select_on`` names the split that drives early stopping, the saved
    checkpoint and the objective ('test' here, 'val' for tune.py's protocol).
    The other split is still evaluated every epoch and reported, but never
    influences anything.
    """

    def _eval_data(self, flag):
        """A deterministic, complete loader over one split.

        data_provider only makes the TEST loader sequential: 'val' comes back
        shuffled and with drop_last=True, so at batch_size 256 it scores a
        random 512 of EURUSD's 519 val windows and its loss moves between
        evaluations of the very same weights. Nothing here may depend on the
        batch order, so the dataset is rewrapped: shuffle off, every window
        scored. For 'test' this is exactly what data_provider already returns
        (DROP_LAST_TEST is False).
        """
        data_set, _ = self._get_data(flag=flag)
        return DataLoader(data_set,
                          batch_size  = self.args.batch_size,
                          shuffle     = False,
                          num_workers = self.args.num_workers,
                          drop_last   = False)

    @torch.no_grad()
    def evaluate(self, loader) -> dict:
        """Full pass over a loader -> the same metrics run.py reports.

        Scored over the concatenated predictions, exactly like Exp_Main.test,
        rather than as a mean of per-batch losses: the test loader keeps its
        final partial batch (data_factory.DROP_LAST_TEST), so the two differ.
        """
        was_training = self.model.training
        self.model.eval()
        f_dim = -1 if self.args.features == 'MS' else 0
        preds, trues = [], []
        for batch in loader:
            batch_x, batch_y, batch_x_mark, _, event_x, event_y = self._unpack_batch(batch)
            batch_x      = batch_x.float().to(self.device)
            batch_y      = batch_y.float().to(self.device)
            batch_x_mark = batch_x_mark.float().to(self.device)

            outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
            outputs = outputs[:, -self.args.pred_len:, f_dim:]
            target  = self._get_target(batch_y, f_dim)

            preds.append(outputs.detach().cpu().numpy())
            trues.append(target.detach().cpu().numpy())
        if was_training:
            self.model.train()

        preds = np.concatenate(preds, axis=0)
        trues = np.concatenate(trues, axis=0)
        mae, mse, rmse, mape, mspe, rse, corr, qlike = metric(preds, trues)
        return {'mse': float(mse), 'mae': float(mae), 'rse': float(rse), 'qlike': float(qlike)}

    def train_select(self, setting: str, trial: optuna.Trial = None) -> dict:
        a = self.args
        monitored = a.select_on                      # 'test' by default
        reference = 'val' if monitored == 'test' else 'test'

        _, train_loader  = self._get_data(flag='train')
        monitor_loader   = self._eval_data(monitored)
        reference_loader = self._eval_data(reference)

        path = os.path.join(a.checkpoints, setting)
        os.makedirs(path, exist_ok=True)

        train_steps = len(train_loader)
        model_optim = self._select_optimizer()
        criterion   = self._select_criterion()
        # EarlyStopping also writes checkpoint.pth on every improvement, so the
        # file left behind is the monitored split's best epoch -- the same
        # train-then-reload-best protocol run.py uses
        early_stop  = EarlyStopping(patience=a.patience, verbose=False)
        scheduler   = lr_scheduler.OneCycleLR(
            optimizer      = model_optim,
            steps_per_epoch= train_steps,
            pct_start      = a.pct_start,
            epochs         = a.train_epochs,
            max_lr         = a.learning_rate,
        )

        f_dim = -1 if a.features == 'MS' else 0
        best_score, best_epoch, epochs_run = float('inf'), -1, 0

        for epoch in range(a.train_epochs):
            epochs_run = epoch + 1
            self.model.train()
            train_loss = []

            for batch in train_loader:
                batch_x, batch_y, batch_x_mark, _, event_x, event_y = self._unpack_batch(batch)
                model_optim.zero_grad()

                batch_x      = batch_x.float().to(self.device)
                batch_y      = batch_y.float().to(self.device)
                batch_x_mark = batch_x_mark.float().to(self.device)

                outputs = self.model(batch_x, batch_x_mark, event_x=event_x, event_y=event_y)
                outputs = outputs[:, -a.pred_len:, f_dim:]
                loss    = criterion(outputs, self._get_target(batch_y, f_dim))

                loss.backward()
                model_optim.step()
                train_loss.append(loss.item())

                if a.lradj == 'TST':
                    adjust_learning_rate(model_optim, scheduler, epoch + 1, a, printout=False)
                    scheduler.step()

            # only the monitored split is scored per epoch. The reference split
            # is scored once, from the reloaded best checkpoint below -- that is
            # the value reported, so a per-epoch pass over it was pure cost
            mon = self.evaluate(monitor_loader)
            score = mon[a.objective]

            if score < best_score:
                best_score, best_epoch = score, epoch + 1

            if a.verbose:
                print(f'    epoch {epoch + 1:>3}/{a.train_epochs} | train '
                      f'{np.average(train_loss):.6f} | {monitored} {a.objective} {score:.6f}')

            if trial is not None:
                trial.report(float(score), epoch)
                if trial.should_prune():
                    raise optuna.TrialPruned()

            early_stop(score, self.model, path)
            if early_stop.early_stop:
                break

            if a.lradj != 'TST':
                adjust_learning_rate(model_optim, scheduler, epoch + 1, a, printout=False)

        # reload the monitored split's best epoch and score it, as run.py does
        ckpt = os.path.join(path, 'checkpoint.pth')
        if os.path.exists(ckpt):
            self.model.load_state_dict(torch.load(ckpt, map_location=self.device))
        mon = self.evaluate(monitor_loader)
        ref = self.evaluate(reference_loader)

        return {
            'objective':  float(mon[a.objective]),
            'best_epoch': best_epoch,
            'epochs_run': epochs_run,
            monitored:    mon,
            reference:    ref,
        }


# ---------------------------------------------------------------------------
# Objective
# ---------------------------------------------------------------------------

def objective(trial: optuna.Trial, base_cfg: argparse.Namespace) -> float:
    args = apply_params(copy.copy(base_cfg), sample_params(trial, base_cfg.use_events))

    print(f'\n[trial {trial.number}] ' + '  '.join(f'{k}={v}' for k, v in trial.params.items()))

    per_seed = []
    for k in range(args.n_seeds):
        seed = args.random_seed + k
        args.run_seed = seed
        set_seed(seed)
        setting = (f'{"filmtcn" if args.use_events else "moderntcn"}'
                   f'_optuna_t{trial.number}_s{k}')
        exp = None
        try:
            exp = SelectOnSplitExp(args)
            # Only the first seed reports to the pruner: later seeds would
            # report their epoch 0 against the first seed's epoch 0 step.
            per_seed.append(exp.train_select(setting, trial=trial if k == 0 else None))
        except optuna.TrialPruned:
            raise
        except Exception as exc:
            print(f'[trial {trial.number}] failed: {type(exc).__name__}: {exc}')
            raise optuna.TrialPruned()
        finally:
            del exp
            if not args.keep_checkpoints:
                shutil.rmtree(os.path.join(args.checkpoints, setting), ignore_errors=True)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    # Every trial carries BOTH splits' metrics: the monitored one is what the
    # search optimises, the other is the reference the docstring warns about.
    for split in ('test', 'val'):
        for name in METRICS:
            vals = np.array([r[split][name] for r in per_seed], dtype=np.float64)
            trial.set_user_attr(f'{split}_{name}', float(vals.mean()))
            if len(vals) > 1:
                trial.set_user_attr(f'{split}_{name}_std', float(vals.std(ddof=1)))
    trial.set_user_attr('best_epoch', [r['best_epoch'] for r in per_seed])
    trial.set_user_attr('epochs_run', [r['epochs_run'] for r in per_seed])
    trial.set_user_attr('n_seeds', args.n_seeds)

    value = float(np.mean([r['objective'] for r in per_seed]))
    print(f'[trial {trial.number}] {args.select_on} {args.objective} = {value:.6f} '
          f'(best epoch {[r["best_epoch"] for r in per_seed]})')
    return value


# ---------------------------------------------------------------------------
# Base config: everything the search does NOT touch
# ---------------------------------------------------------------------------

def build_base_config(t: argparse.Namespace) -> argparse.Namespace:
    cfg = argparse.Namespace()

    cfg.model    = 'ModernTCN'          # + use_events == FiLM-TCN
    cfg.model_id = t.model_id
    cfg.des      = 'optuna'

    # Dataset
    cfg.data      = t.data
    cfg.root_path = t.root_path
    cfg.data_path = t.data_path
    cfg.features  = t.features
    cfg.target    = t.target
    cfg.freq      = t.freq
    cfg.embed     = t.embed

    # Task
    cfg.seq_len   = t.seq_len           # overwritten per trial
    cfg.label_len = t.label_len
    cfg.pred_len  = t.pred_len
    cfg.enc_in    = t.enc_in
    cfg.dec_in    = t.enc_in
    cfg.c_out     = t.enc_in
    cfg.aggregate_horizon = t.aggregate_horizon

    # Training budget
    cfg.train_epochs = t.train_epochs
    cfg.patience     = t.patience
    cfg.num_workers  = t.num_workers
    cfg.checkpoints  = t.checkpoints
    cfg.itr          = 1
    cfg.n_seeds      = t.n_seeds
    cfg.random_seed  = t.random_seed
    cfg.run_seed     = t.random_seed

    # This script's own switches
    cfg.select_on        = t.select_on
    cfg.objective        = t.objective
    cfg.keep_checkpoints = t.keep_checkpoints
    cfg.verbose          = t.verbose

    # News events (FiLM-TCN). event_fusion / past / future are fixed across the
    # study; only event_dim is searched.
    cfg.use_events          = t.use_events
    cfg.event_data_path     = t.event_data_path
    cfg.event_min_days      = t.event_min_days
    cfg.event_on_nontrading = t.event_on_nontrading
    cfg.event_fusion        = t.event_fusion
    cfg.event_past          = True
    cfg.event_future        = True
    cfg.event_dim           = t.event_dim   # overwritten per trial
    cfg.event_in            = 0
    if cfg.use_events:
        if cfg.data == 'custom':
            cfg.data = 'custom_events'
        cfg.event_data_path = resolve_event_path(
            cfg.root_path, cfg.data_path, cfg.event_data_path)
        cfg.event_in = count_event_features(
            cfg.root_path, cfg.data_path, cfg.target, cfg.event_data_path,
            **event_kwargs_from_args(cfg))
        print(f'news events: {cfg.event_in} feature columns from {cfg.event_data_path} '
              f'(fusion={cfg.event_fusion})')

    # Optimiser / schedule, fixed by the base config
    cfg.pct_start = t.pct_start
    cfg.lradj     = t.lradj
    cfg.use_amp   = False
    cfg.loss      = 'mse'
    cfg.loss_dir  = ''                  # no per-observation dump during a search

    # Fixed ModernTCN structure
    cfg.stem_ratio              = 6
    cfg.downsample_ratio        = 2
    cfg.small_kernel_merged     = False
    cfg.call_structural_reparam = False
    cfg.affine                  = 0
    cfg.subtract_last           = 0
    cfg.decomposition           = 0
    cfg.kernel_size             = 25
    cfg.individual              = 0
    cfg.use_multi_scale         = False

    # Legacy Transformer knobs: unused, but data_provider / the model dict read them
    cfg.embed_type       = 0
    cfg.d_model          = 512
    cfg.n_heads          = 8
    cfg.e_layers         = 2
    cfg.d_layers         = 1
    cfg.d_ff             = 2048
    cfg.moving_avg       = 25
    cfg.factor           = 1
    cfg.distil           = True
    cfg.activation       = 'gelu'
    cfg.output_attention = False
    cfg.do_predict       = False
    cfg.fc_dropout       = 0.05
    cfg.padding_patch    = 'end'
    cfg.patch_len        = 16
    cfg.stride           = 8
    cfg.test_flop        = False

    # GPU
    cfg.use_gpu       = torch.cuda.is_available()
    cfg.gpu           = 0
    cfg.use_multi_gpu = False
    cfg.devices       = '0'
    cfg.device_ids    = [0]

    return apply_params(cfg, BASE_PARAMS)


def best_run_command(t: argparse.Namespace, params: dict) -> str:
    """The run.py invocation that reproduces a trial, for the --itr final run."""
    p = dict(BASE_PARAMS)
    p.update(params)
    four = lambda v: ' '.join([str(v)] * 4)
    parts = [
        'python run.py --is_training 1',
        f'--model_id {t.model_id} --model ModernTCN',
        f'--data {t.data} --root_path {t.root_path} --data_path {t.data_path}',
        f'--features {t.features} --target {t.target} '
        f'--enc_in {t.enc_in} --dec_in {t.enc_in} --c_out {t.enc_in}',
    ]
    agg = '--aggregate_mean ' if t.aggregate_horizon else ''
    parts.append(f"{agg}--seq_len {p['seq_len']} --pred_len {t.pred_len}")
    parts.append(f"--patch_size {p['patch_size']} "
                 f"--patch_stride {min(p['patch_stride'], p['patch_size'])} "
                 f"--ffn_ratio {p['ffn_ratio']}")
    parts.append(f"--num_blocks {four(p['num_blocks'])} --large_size {four(p['large_size'])} "
                 f"--small_size {four(p['small_size'])}")
    parts.append(f"--dims {four(p['dim'])} --dw_dims {four(p['dim'])}")
    parts.append(f"--dropout {p['dropout']} --head_dropout {p['head_dropout']} --revin {p['revin']}")
    parts.append(f"--use_multi_scale False --lradj {t.lradj} --pct_start {t.pct_start}")
    parts.append(f"--learning_rate {p['learning_rate']} --batch_size {p['batch_size']}")
    parts.append(f"--train_epochs {t.train_epochs} --patience {t.patience} "
                 f"--num_workers {t.num_workers} --itr {t.final_itr}")
    if t.use_events:
        parts.append(f"--use_events --event_dim {p['event_dim']} --event_fusion {t.event_fusion}")
    return ' \\\n  '.join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description='Optuna HPO for FiLM-TCN, selecting and reporting on the test split',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # --- what the search optimises -----------------------------------------
    p.add_argument('--select_on', type=str, default='test', choices=['test', 'val'],
                   help="split that drives early stopping, the checkpoint and the objective. "
                        "'test' is this script's point (and is selection-biased: see the module "
                        "docstring); 'val' reproduces tune.py's protocol")
    p.add_argument('--objective', type=str, default='mse', choices=list(METRICS),
                   help='metric minimised on --select_on (all four: smaller is better)')

    # --- dataset / task (defaults = the base config) ------------------------
    p.add_argument('--data',      type=str, default='custom', help='dataset type; custom -> custom_events with events on')
    p.add_argument('--root_path', type=str, default='./data/')
    p.add_argument('--data_path', type=str, default='EURUSD_lnRV.csv')
    p.add_argument('--features',  type=str, default='S', choices=['M', 'S', 'MS'])
    p.add_argument('--target',    type=str, default='lnRV')
    p.add_argument('--enc_in',    type=int, default=1, help='input variables (also sets dec_in / c_out)')
    p.add_argument('--freq',      type=str, default='h')
    p.add_argument('--embed',     type=str, default='timeF')
    p.add_argument('--seq_len',   type=int, default=70, help='fallback look-back; seq_len is searched')
    p.add_argument('--label_len', type=int, default=0,  help='unused by ModernTCN; must be <= seq_len')
    p.add_argument('--pred_len',  type=int, default=1,  help='forecast horizon h')
    p.add_argument('--aggregate_horizon', '--aggregate_mean', dest='aggregate_horizon',
                   action='store_true', default=True,
                   help='predict ln( (1/h) sum_k RV_{t+k} ), the benchmark target '
                        '(utils/target_agg.py). On by default, as in the base config')
    p.add_argument('--no_aggregate_mean', dest='aggregate_horizon', action='store_false',
                   help='forecast each of the h steps instead of the aggregate')
    p.add_argument('--model_id', type=str, default=None,
                   help='name used in the reconstructed run.py command (default: FiLMTCN_h<pred_len>)')

    # --- training budget per trial -----------------------------------------
    p.add_argument('--train_epochs', type=int, default=40)
    p.add_argument('--patience',     type=int, default=8)
    p.add_argument('--batch_size',   type=int, default=256, help='fallback only; batch_size is searched')
    p.add_argument('--num_workers',  type=int, default=0)
    p.add_argument('--lradj',        type=str, default='TST')
    p.add_argument('--pct_start',    type=float, default=0.3)
    p.add_argument('--n_seeds',      type=int, default=1,
                   help='seeds per trial (random_seed + 0..n-1); the trial value is their mean. '
                        '>1 buys a less noisy objective at n times the cost')
    p.add_argument('--final_itr',    type=int, default=5,
                   help='--itr written into the reconstructed run.py command')

    # --- study --------------------------------------------------------------
    p.add_argument('--n_trials',   type=int, default=50)
    p.add_argument('--study_name', type=str, default=None, help='auto-generated if omitted')
    p.add_argument('--output_dir', type=str, default='./optuna_results/')
    p.add_argument('--checkpoints', type=str, default='./optuna_checkpoints/')
    p.add_argument('--random_seed', type=int, default=2021)
    p.add_argument('--n_startup_trials', type=int, default=10,
                   help='random trials before TPE takes over, and before the pruner engages')
    p.add_argument('--n_warmup_steps', type=int, default=5,
                   help='epochs a trial is safe from the pruner')
    p.add_argument('--no_enqueue_base', dest='enqueue_base', action='store_false', default=True,
                   help='do not seed a fresh study with the base config as trial 0')
    p.add_argument('--reset', action='store_true',
                   help='delete the existing study DB first (do this after editing the search space)')
    p.add_argument('--keep_checkpoints', action='store_true',
                   help='keep each trial\'s checkpoint.pth instead of deleting it when the trial ends')
    p.add_argument('--verbose', action='store_true', help='print a line per epoch')

    # --- news events (FiLM-TCN) ---------------------------------------------
    p.add_argument('--use_events', action='store_true', default=True,
                   help='the FiLM-TCN conditioning; on by default (that is the model being tuned)')
    p.add_argument('--no_events', dest='use_events', action='store_false',
                   help='tune plain ModernTCN instead, same protocol -- the ablation baseline')
    p.add_argument('--event_data_path', type=str, default=None,
                   help='event calendar inside root_path; defaults to the one paired with '
                        '--data_path by name (EURUSD_lnRV.csv -> EURUSD_EVENTS.csv)')
    p.add_argument('--event_min_days', type=int, default=DEFAULT_MIN_DAYS)
    p.add_argument('--event_on_nontrading', type=str, default=DEFAULT_ON_NONTRADING,
                   choices=['roll', 'drop'])
    p.add_argument('--event_fusion', type=str, default='channel', choices=['inject', 'channel'],
                   help='how past events enter the backbone; fixed across the study')
    p.add_argument('--event_dim', type=int, default=16, help='fallback only; event_dim is searched')

    args = p.parse_args()
    if args.model_id is None:
        args.model_id = f'{"FiLMTCN" if args.use_events else "ModernTCN"}_h{args.pred_len}'
    return args


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    check_base_params()
    t = parse_args()
    set_seed(t.random_seed)

    base_cfg = build_base_config(t)

    pair = os.path.splitext(os.path.basename(t.data_path))[0]
    for suffix in ('_lnRV', '_ln_RV', '_RV'):
        if pair.endswith(suffix):
            pair = pair[: -len(suffix)]
            break
    model_name = 'filmtcn' if t.use_events else 'moderntcn'
    # everything that changes what a trial's VALUE means goes in the name, so a
    # re-run with different settings starts its own study instead of silently
    # resuming one whose trials are not comparable
    study_name = t.study_name or (
        f'{model_name}_{t.select_on}sel_{pair}_pl{t.pred_len}_{t.objective}'
        + (f'_x{t.n_seeds}seeds' if t.n_seeds > 1 else ''))

    out_dir = os.path.join(t.output_dir, study_name)
    os.makedirs(out_dir, exist_ok=True)
    db_path = os.path.join(out_dir, 'study.db')

    if t.reset and os.path.exists(db_path):
        os.remove(db_path)
        print(f'removed existing study DB: {db_path}')

    print('\n' + '=' * 72)
    print(f'  Optuna HPO -- {"FiLM-TCN" if t.use_events else "ModernTCN"} '
          f'({pair}, h={t.pred_len})')
    print(f'  Selecting on : {t.select_on.upper()}  (objective: {t.objective})')
    print(f'  Trials       : {t.n_trials}   seeds/trial: {t.n_seeds}')
    print(f'  Epochs/trial : {t.train_epochs}   patience: {t.patience}')
    print(f'  Results      : {out_dir}')
    if t.select_on == 'test':
        print('-' * 72)
        print('  NOTE: early stopping, the checkpoint and the objective all read the')
        print('  TEST years, so the test metrics below are selection-biased and are')
        print('  NOT out-of-sample accuracy. Every trial also carries val_* metrics')
        print('  for reference; --select_on val runs the unbiased protocol.')
    print('=' * 72 + '\n')

    study = optuna.create_study(
        study_name     = study_name,
        direction      = 'minimize',
        sampler        = TPESampler(n_startup_trials=t.n_startup_trials, seed=t.random_seed),
        pruner         = MedianPruner(n_startup_trials=t.n_startup_trials,
                                      n_warmup_steps=t.n_warmup_steps,
                                      interval_steps=1),
        storage        = f'sqlite:///{db_path}',
        load_if_exists = True,      # re-running the same command resumes
    )

    # Seed a fresh study with the base config, so the study always contains the
    # point it started from. On a resumed study the trial is already in the DB.
    if t.enqueue_base and not study.get_trials(deepcopy=False):
        params = {k: v for k, v in BASE_PARAMS.items() if t.use_events or k != 'event_dim'}
        study.enqueue_trial(params)
        print('trial 0 enqueued with the base config\n')

    study.optimize(lambda trial: objective(trial, base_cfg), n_trials=t.n_trials)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    best = study.best_trial
    print('\n' + '=' * 72)
    print(f'  Best trial : #{best.number}')
    print(f'  {t.select_on} {t.objective} : {best.value:.6f}')
    print('  Params     :')
    for k, v in best.params.items():
        print(f'    {k}: {v}')
    print('  Metrics at that config:')
    for split in ('test', 'val'):
        row = '  '.join(f'{m}={best.user_attrs.get(f"{split}_{m}", float("nan")):.6f}' for m in METRICS)
        tag = ' (selected on)' if split == t.select_on else ''
        print(f'    {split:<5}{tag or "":<15} {row}')
    print('=' * 72 + '\n')

    payload = {
        'study_name': study_name,
        'select_on': t.select_on,
        'objective': t.objective,
        'best_value': best.value,
        'best_trial': best.number,
        'params': best.params,
        'metrics': dict(best.user_attrs),
        'base_params': BASE_PARAMS,
        'fixed': {
            'data_path': t.data_path, 'pred_len': t.pred_len,
            'aggregate_horizon': t.aggregate_horizon, 'use_events': t.use_events,
            'event_fusion': t.event_fusion, 'train_epochs': t.train_epochs,
            'patience': t.patience, 'lradj': t.lradj, 'n_seeds': t.n_seeds,
            'random_seed': t.random_seed,
        },
        'caveat': ('early stopping, checkpoint selection and the objective all read the '
                   f'{t.select_on} split; test metrics from a test-selected study are '
                   'selection-biased and are not out-of-sample accuracy'),
    }
    best_params_path = os.path.join(out_dir, 'best_params.json')
    with open(best_params_path, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f'best params  -> {best_params_path}')

    csv_path = os.path.join(out_dir, 'all_trials.csv')
    study.trials_dataframe().to_csv(csv_path, index=False)
    print(f'all trials   -> {csv_path}')

    cmd_path = os.path.join(out_dir, 'best_command.sh')
    with open(cmd_path, 'w') as f:
        f.write('#!/bin/sh\n')
        f.write(f'# best trial #{best.number} of study {study_name}\n')
        f.write(f'# {t.select_on} {t.objective} = {best.value:.6f} during the search\n')
        f.write(f'# {payload["caveat"]}\n\n')
        f.write(best_run_command(t, best.params) + '\n')
    print(f'run command  -> {cmd_path}')

    try:
        import plotly  # noqa: F401
        optuna.visualization.plot_optimization_history(study).write_html(
            os.path.join(out_dir, 'optimization_history.html'))
        optuna.visualization.plot_param_importances(study).write_html(
            os.path.join(out_dir, 'param_importances.html'))
        optuna.visualization.plot_parallel_coordinate(study).write_html(
            os.path.join(out_dir, 'parallel_coordinate.html'))
        print(f'plots        -> {out_dir}')
    except ImportError:
        print('install plotly for the HTML plots: pip install plotly')


if __name__ == '__main__':
    main()
