from data_provider.data_loader import Dataset_Custom, Dataset_Custom_Events, Dataset_Pred
from data_provider.data_loader import Dataset_HAR_Residual
from data_provider.event_preprocessing import (
    event_kwargs_from_args, resolve_event_path)
from torch.utils.data import DataLoader

# Whether the TEST loader drops its final partial batch. False scores every
# test window, which is what makes the deep models comparable with HAR-RV and
# N-HAR; True reproduces the repo's original behaviour (and the metrics that go
# with it) at the cost of that comparability. See the note in data_provider().
DROP_LAST_TEST = False

data_dict = {
    'custom': Dataset_Custom,
    'custom_events': Dataset_Custom_Events,
    'har_residual': Dataset_HAR_Residual,
}


def data_provider(args, flag):
    Data = data_dict[args.data]
    timeenc = 0 if args.embed != 'timeF' else 1

    if flag == 'test':
        shuffle_flag = False
        # DROP_LAST_TEST = False keeps the final partial batch, so every test
        # window is scored and the deep models sit on the same sample as
        # HAR-RV / N-HAR. Setting it True drops that batch: only
        # floor(n_test / batch_size) * batch_size windows are then scored, and
        # at batch_size 256 with ~385 test windows that is the FIRST 256 --
        # which for these series is 2024 almost exactly, so H1-2025 (a
        # higher-volatility regime including the April 2025 spike) drops out of
        # every deep metric while the linear models keep it. The share scored
        # would also depend on batch_size (64/128 score ~all, 256 scores 2/3,
        # 512 scores nothing at all), making the deep sample an artefact of an
        # optimiser setting. dm_mcs_run.py reports any such mismatch.
        drop_last = DROP_LAST_TEST
        batch_size = args.batch_size
        freq = args.freq
    elif flag == 'pred':
        shuffle_flag = False
        drop_last = False
        batch_size = 1
        freq = args.freq
        Data = Dataset_Pred
    else:
        shuffle_flag = True
        drop_last = True
        batch_size = args.batch_size
        freq = args.freq

    extra_kwargs = {}
    if Data is Dataset_Custom_Events:
        extra_kwargs['event_path'] = resolve_event_path(
            args.root_path, args.data_path, getattr(args, 'event_data_path', None))
        extra_kwargs['event_kwargs'] = event_kwargs_from_args(args)
    elif Data is Dataset_Pred and getattr(args, 'use_events', False):
        raise NotImplementedError(
            'flag="pred" (Dataset_Pred) does not support --use_events; '
            'events beyond the dataset are unknown to Dataset_Pred')

    data_set = Data(
        root_path=args.root_path,
        data_path=args.data_path,
        flag=flag,
        size=[args.seq_len, args.label_len, args.pred_len],
        features=args.features,
        target=args.target,
        timeenc=timeenc,
        freq=freq,
        **extra_kwargs
    )
    print(flag, len(data_set))
    data_loader = DataLoader(
        data_set,
        batch_size=batch_size,
        shuffle=shuffle_flag,
        num_workers=args.num_workers,
        drop_last=drop_last)
    return data_set, data_loader
