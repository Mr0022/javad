from data_provider.data_loader import Dataset_Custom, Dataset_Custom_Events, Dataset_Pred
from data_provider.data_loader import Dataset_HAR_Residual
from data_provider.event_preprocessing import (
    event_kwargs_from_args, resolve_event_path)
from torch.utils.data import DataLoader

# Whether the TEST loader drops its final partial batch. True reproduces the
# repo's original behaviour (and the metrics that go with it); False scores
# every test window. See the note in data_provider() before changing it.
DROP_LAST_TEST = True

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
        # KNOWN CONSEQUENCE, kept deliberately: dropping the final partial test
        # batch means only floor(n_test / batch_size) * batch_size windows are
        # scored. At batch_size 256 with ~384 test windows that is the first
        # 256 -- which for these series is 2024 almost exactly, so H1-2025 (a
        # higher-volatility regime including the April 2025 spike) is excluded
        # from every deep metric. The share scored also depends on batch_size:
        # 64/128 score ~all, 256 scores 2/3, 512 scores nothing at all.
        # The deep models therefore sit on a shorter, earlier sample than
        # HAR-RV / N-HAR, and dm_mcs_run.py reports that mismatch and tests the
        # intersection. Set DROP_LAST_TEST = False to score the whole window.
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
