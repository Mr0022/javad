"""
Preprocessing for the per-pair macro news-event calendars (``data/<PAIR>_EVENTS.csv``).

Every FX pair carries its own calendar next to its own realised-volatility
series, and the two are paired **by filename**::

    data/EURUSD_lnRV.csv  <->  data/EURUSD_EVENTS.csv
    data/AUDUSD_lnRV.csv  <->  data/AUDUSD_EVENTS.csv

so ``--data_path AUDUSD_lnRV.csv`` picks up ``AUDUSD_EVENTS.csv`` on its own and
``--event_data_path`` only has to be passed to override that (see
``derive_event_path`` / ``resolve_event_path``).

The raw calendar is a **long** table with one row per scheduled release::

    Date,Name,Currency
    2012-01-02,HCOB Manufacturing PMI,EUR
    2012-01-03,Unemployment Change,EUR

An ``Impact`` column may be present in the file; it is IGNORED. Impact ratings
are a vendor's subjective label rather than an observable, they are not part of
the published release schedule, and they can be revised after the fact -- so
conditioning on them weakens the ex-ante claim that every regressor was knowable
at forecast time. Nothing downstream (HAR-X, N-HAR, the FiLM/channel event
conditioning) sees impact on this branch.

``Dataset_Custom_Events`` (and the FiLM/channel event conditioning in
``models/ModernTCN.py``) needs a **wide** daily matrix instead: one row per
trading day, a ``date`` column and numeric feature columns.  This module does
that conversion, and is the single place where the raw -> wide contract lives so
that ``run.py``, ``tune.py`` and the dataset all agree on the column set.

Output columns
--------------
``n_events*`` / ``event_*`` (counts -- standardised on TRAIN years by the loader)
    ``n_events``            total releases that day
    ``n_events_<cur>``      ... per currency actually present in the file, e.g.
                            ``n_events_eur`` / ``n_events_usd`` for EURUSD and
                            ``n_events_aud`` / ``n_events_usd`` for AUDUSD
    ``event_coverage``      1 on days inside the calendar's date range, else 0.
                            Only emitted when the target series actually extends
                            beyond the calendar, so the model can tell "no events
                            scheduled" apart from "no event data collected".

``evt_<CUR>_<Name>`` (multi-hot indicators -- kept raw 0/1 by the loader)
    One column per (Currency, Name) release type seen on at least ``min_days``
    distinct trading days.  With impact gone, recurrence is the only filter, so
    the long tail of frequent-but-minor releases (bill auctions, Redbook, rig
    counts) now survives wherever it is regular enough -- raise ``min_days`` if
    you want a tighter set.

Calendar alignment
------------------
Releases land on dates the target series does not trade (market holidays, gaps
in the RV series): 308 in-range releases over 228 dates against
``EURUSD_lnRV.csv``, 836 over 259 dates against ``realized_volatility.csv``,
most of them weekdays.  Dropping them loses real information, so by default they
are **rolled forward** onto the next trading day, where the market actually
prices them in.  Pass ``on_nontrading='drop'`` for the older drop-on-reindex
behaviour.
Releases dated before the first trading day are always dropped (rolling them
would pile the whole pre-history onto day one).
"""

import os
import re
import warnings

import numpy as np
import pandas as pd

# raw long-format schema. 'Impact' may also be present and is ignored.
RAW_COLUMNS = ('Date', 'Name', 'Currency')

EVENT_SUFFIX = '_EVENTS.csv'
# target series are named <PAIR>_lnRV.csv; this is stripped to get <PAIR>
SERIES_SUFFIXES = ('_lnRV',)
DEFAULT_DATA_PATH = 'EURUSD_lnRV.csv'
DEFAULT_MIN_DAYS = 24
DEFAULT_ON_NONTRADING = 'roll'

# build_daily_event_features is called once per dataset split (train/val/test)
# plus once by run.py/tune.py to size the event embedding; the inputs are
# identical every time, so memoise rather than re-pivot 66k rows four times.
_CACHE = {}


def _sanitise(name):
    """'Consumer Price Index ex Food & Energy (YoY)' -> 'Consumer_Price_Index_ex_Food_Energy_YoY'."""
    name = name.replace("'", '').replace('’', '')   # Fed's -> Feds
    name = re.sub(r'[^0-9A-Za-z]+', '_', name)
    return name.strip('_')


def _normalise_names(df):
    """Collapse whitespace and fold spelling variants that differ only in case.

    The calendar contains e.g. both 'Consumer Price Index (EU Norm) (YoY)' and
    '... (EU norm) (YoY)'; left alone they become two half-populated columns.
    Each case-insensitive group is mapped to its most frequent spelling.
    """
    df = df.copy()
    df['Name'] = df['Name'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
    key = df['Name'].str.lower()
    # most frequent spelling per case-insensitive key, ties broken alphabetically
    counts = df.groupby([key.rename('_k'), 'Name']).size().rename('n').reset_index()
    counts = counts.sort_values(['_k', 'n', 'Name'], ascending=[True, False, True])
    canon = counts.drop_duplicates('_k').set_index('_k')['Name']
    df['Name'] = key.map(canon).values
    return df


def _read_raw(path):
    df = pd.read_csv(path)
    missing = [c for c in RAW_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f'{path}: expected a long-format event calendar with columns '
            f'{list(RAW_COLUMNS)}, missing {missing}. Columns found: {list(df.columns)}')

    df = df[list(RAW_COLUMNS)].copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Currency'] = df['Currency'].astype(str).str.strip().str.upper()

    bad_date = df['Date'].isna()
    if bad_date.any():
        warnings.warn(f'{path}: dropping {int(bad_date.sum())} rows with unparseable Date')
        df = df[~bad_date]

    return _normalise_names(df).reset_index(drop=True)


def _align_to_trading_days(df, trading_dates, on_nontrading):
    """Map each release onto a trading day, or drop it."""
    td = pd.DatetimeIndex(trading_dates).sort_values()
    if on_nontrading == 'drop':
        keep = df['Date'].isin(set(td))
        return df.loc[keep].assign(trade_date=df.loc[keep, 'Date']), int((~keep).sum())

    if on_nontrading != 'roll':
        raise ValueError(f"on_nontrading must be 'roll' or 'drop', got {on_nontrading!r}")

    # next trading day at or after the release date; before the series starts or
    # after it ends there is no such day, so those releases are dropped
    pos = np.searchsorted(td.values, df['Date'].values, side='left')
    inside = (pos < len(td)) & (df['Date'].values >= td.values[0])
    out = df.loc[inside].copy()
    out['trade_date'] = td.values[pos[inside]]
    return out, int((~inside).sum())


def build_daily_event_features(event_file, trading_dates,
                               min_days=DEFAULT_MIN_DAYS,
                               on_nontrading=DEFAULT_ON_NONTRADING,
                               verbose=True):
    """Long-format calendar -> wide daily matrix indexed by ``trading_dates``.

    Parameters
    ----------
    event_file : str
        Path to the raw ``events_daily.csv``.  A file that is already wide (has a
        ``date`` column and no ``Name`` column) is passed through
        unchanged, so ``--event_data_path events.csv`` keeps working.
    trading_dates : sequence of datetime-like
        The target series' dates, in order.  The result has exactly these rows.
    min_days :
        An ``evt_*`` indicator is emitted for a (Currency, Name) release type
        seen on at least ``min_days`` distinct trading days. Impact ratings are
        ignored, so recurrence is the only filter.
    on_nontrading : {'roll', 'drop'}
        What to do with releases dated on a non-trading day.

    Returns
    -------
    pandas.DataFrame with a ``date`` column plus float32 feature columns.
    """
    trading_dates = pd.DatetimeIndex(pd.to_datetime(pd.Series(list(trading_dates))))

    raw = _read_raw(event_file)

    aligned, n_unaligned = _align_to_trading_days(raw, trading_dates, on_nontrading)
    if verbose and n_unaligned:
        verb = 'rolled onto the next trading day' if on_nontrading == 'roll' else 'dropped'
        note = ('outside the target series date range, dropped' if on_nontrading == 'roll'
                else 'not on a trading day, dropped')
        print(f'events: {len(raw) - n_unaligned} releases aligned '
              f'({verb} where needed), {n_unaligned} {note}')

    idx = trading_dates
    counts = {}

    def _daily(mask, name):
        s = aligned.loc[mask].groupby('trade_date').size()
        counts[name] = s.reindex(idx).fillna(0.0).to_numpy(dtype=np.float32)

    _daily(pd.Series(True, index=aligned.index), 'n_events')
    # one column per currency actually present, so EURUSD yields
    # n_events_eur/_usd and AUDUSD yields n_events_aud/_usd without any edits
    for cur in sorted(raw['Currency'].unique()):
        _daily(aligned['Currency'] == cur, f'n_events_{_sanitise(cur).lower()}')

    # ---- multi-hot indicators for the release types worth modelling ----------
    stats = (aligned.groupby(['Currency', 'Name'])
             .agg(days=('trade_date', 'nunique'))
             .reset_index())
    sel = stats[stats['days'] >= min_days]
    sel = sel.sort_values(['Currency', 'Name'])

    indicators = {}
    picked = aligned.merge(sel[['Currency', 'Name']], on=['Currency', 'Name'], how='inner')
    if len(picked):
        wide = (picked.assign(one=np.float32(1))
                .pivot_table(index='trade_date', columns=['Currency', 'Name'],
                             values='one', aggfunc='max', fill_value=0.0)
                .reindex(idx).fillna(0.0))
        for (cur, name) in wide.columns:
            col = f'evt_{cur}_{_sanitise(name)}'
            if col in indicators:                # distinct names, same slug
                suffix = 2
                while f'{col}_{suffix}' in indicators:
                    suffix += 1
                col = f'{col}_{suffix}'
            indicators[col] = wide[(cur, name)].to_numpy(dtype=np.float32)

    out = pd.DataFrame({'date': trading_dates, **counts, **indicators})

    # ---- coverage flag, only when the target outruns the calendar -----------
    lo, hi = raw['Date'].min(), raw['Date'].max()
    covered = ((trading_dates >= lo) & (trading_dates <= hi)).astype(np.float32)
    if covered.min() == 0.0:
        n_out = int((covered == 0).sum())
        out['event_coverage'] = covered
        if verbose:
            warnings.warn(
                f'{os.path.basename(event_file)} covers {lo.date()}..{hi.date()} but the target '
                f'series has {n_out} trading day(s) outside that range; those days carry zero '
                f'events and are flagged by the "event_coverage" column. Consider a target '
                f'series confined to the calendar\'s range.')

    if verbose:
        n_evt = sum(c.startswith('evt_') for c in out.columns)
        print(f'events: {len(out.columns) - 1} feature columns '
              f'({n_evt} evt_* indicators from {len(stats)} release types, '
              f'min_days={min_days}; impact ignored) '
              f'over {len(out)} trading days')
    return out


def derive_event_path(data_path):
    """``AUDUSD_lnRV.csv`` -> ``AUDUSD_EVENTS.csv``; pairs a series with its calendar.

    The directory part of ``data_path`` is preserved, so a series in a
    subdirectory looks for its calendar alongside itself.
    """
    head, base = os.path.split(data_path)
    stem = os.path.splitext(base)[0]
    for suffix in SERIES_SUFFIXES:
        if stem.lower().endswith(suffix.lower()):
            stem = stem[:-len(suffix)]
            break
    return os.path.join(head, stem + EVENT_SUFFIX)


def available_event_files(root_path):
    try:
        names = os.listdir(root_path)
    except OSError:
        return []
    return sorted(n for n in names if n.endswith(EVENT_SUFFIX))


def resolve_event_path(root_path, data_path, event_path=None):
    """Pick the calendar for ``data_path``, or honour an explicit ``event_path``.

    An explicitly supplied ``event_path`` always wins. Otherwise the calendar is
    derived from the series filename; if that file is missing we raise rather
    than silently fall back, because the quiet failure here is training one
    currency pair against another pair's news calendar.
    """
    if event_path:
        return event_path

    derived = derive_event_path(data_path)
    if os.path.exists(os.path.join(root_path, derived)):
        return derived

    found = available_event_files(root_path)
    raise FileNotFoundError(
        f'--use_events needs an event calendar for {data_path!r}: expected '
        f'{derived!r} in {root_path!r}, which does not exist. '
        + (f'Calendars present: {found}. ' if found else 'No *_EVENTS.csv files are present. ')
        + 'Add it, or name one explicitly with --event_data_path.')


def _is_wide(event_file):
    head = pd.read_csv(event_file, nrows=0)
    return 'date' in head.columns and not set(RAW_COLUMNS[1:]).issubset(head.columns)


def load_event_features(root_path, event_path, trading_dates, **kwargs):
    """Return the wide daily event matrix for ``root_path/event_path``.

    Accepts either the raw long calendar or an already-preprocessed wide file
    (as produced by ``python -m data_provider.event_preprocessing``, or the
    legacy ``data/events.csv``), so both keep working via ``--event_data_path``.
    Results are memoised across the train/val/test datasets.
    """
    path = os.path.join(root_path, event_path)
    trading_dates = pd.DatetimeIndex(pd.to_datetime(pd.Series(list(trading_dates))))

    key = (os.path.abspath(path), len(trading_dates),
           trading_dates[0] if len(trading_dates) else None,
           trading_dates[-1] if len(trading_dates) else None,
           tuple(sorted(kwargs.items())))
    if key in _CACHE:
        return _CACHE[key].copy()

    if _is_wide(path):
        # legacy already-daily file: align by date, absent days = no events
        df = pd.read_csv(path)
        df['date'] = pd.to_datetime(df['date'])
        cols = [c for c in df.columns if c != 'date']
        df = df.drop_duplicates(subset='date').set_index('date')
        vals = df.reindex(trading_dates)[cols].to_numpy(dtype=np.float32)
        out = pd.DataFrame(np.nan_to_num(vals, nan=0.0), columns=cols)
        out.insert(0, 'date', trading_dates)
    else:
        out = build_daily_event_features(path, trading_dates, **kwargs)

    _CACHE[key] = out
    return out.copy()


def resolve_target_column(columns, target):
    """Find ``target`` among ``columns``, tolerating naming drift between series.

    The series files are exported per pair and do not agree on spelling:
    EURUSD_lnRV.csv calls the column ``ln_RV`` while AUDUSD/USDCHF/USDJPY call it
    ``lnRV``. Rather than force one ``--target`` per file, match exactly first,
    then case- and separator-insensitively, then fall back to the only non-date
    column when the file has just one. Anything more ambiguous raises.
    """
    cols = list(columns)
    if target in cols:
        return target

    def norm(x):
        return re.sub(r'[^0-9a-z]', '', str(x).lower())

    hits = [c for c in cols if norm(c) == norm(target)]
    if len(hits) == 1:
        return hits[0]

    others = [c for c in cols if c != 'date']
    if len(others) == 1:
        return others[0]

    raise KeyError(
        f'target column {target!r} not found; columns are {cols}. '
        'Pass --target with one of those names.')


def read_trading_dates(root_path, data_path, target):
    """The target series' dates, filtered exactly as ``Dataset_Custom`` filters them."""
    df = pd.read_csv(os.path.join(root_path, data_path))
    target = resolve_target_column(df.columns, target)
    df = df.dropna(subset=['date', target]).reset_index(drop=True)
    return pd.to_datetime(df['date'])


def count_event_features(root_path, data_path, target, event_path=None, **kwargs):
    """``event_in`` for the model: how many feature columns the calendar yields."""
    event_path = resolve_event_path(root_path, data_path, event_path)
    dates = read_trading_dates(root_path, data_path, target)
    return len(load_event_features(root_path, event_path, dates, **kwargs).columns) - 1


def event_kwargs_from_args(args):
    """Pull the preprocessing options off an argparse namespace / config object."""
    return {
        'min_days': getattr(args, 'event_min_days', DEFAULT_MIN_DAYS),
        'on_nontrading': getattr(args, 'event_on_nontrading', DEFAULT_ON_NONTRADING),
    }


def _main():
    import argparse
    p = argparse.ArgumentParser(
        description='Preprocess the raw news-event calendar into a wide daily matrix.')
    p.add_argument('--root_path', type=str, default='./data/')
    p.add_argument('--data_path', type=str, default=DEFAULT_DATA_PATH,
                   help='target series whose trading calendar the events are aligned to')
    p.add_argument('--event_data_path', type=str, default=None,
                   help='defaults to the calendar paired with --data_path by name')
    p.add_argument('--target', type=str, default='ln_RV')
    p.add_argument('--event_min_days', type=int, default=DEFAULT_MIN_DAYS)
    p.add_argument('--event_on_nontrading', type=str, default=DEFAULT_ON_NONTRADING,
                   choices=['roll', 'drop'])
    p.add_argument('--out', type=str, default=None,
                   help='where to write the wide csv (default: <root_path>/events_daily_features.csv)')
    a = p.parse_args()

    event_path = resolve_event_path(a.root_path, a.data_path, a.event_data_path)
    dates = read_trading_dates(a.root_path, a.data_path, a.target)
    df = build_daily_event_features(
        os.path.join(a.root_path, event_path), dates,
        min_days=a.event_min_days,
        on_nontrading=a.event_on_nontrading)
    default_out = os.path.splitext(os.path.basename(event_path))[0] + '_features.csv'
    out = a.out or os.path.join(a.root_path, default_out)
    df.to_csv(out, index=False, float_format='%g')
    print(f'wrote {out}  shape={df.shape}')


if __name__ == '__main__':
    _main()
