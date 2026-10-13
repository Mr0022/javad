"""Write <PAIR>_EVENTS_CORE.csv: the raw calendar collapsed to one row per (date, release)."""
import os, sys, re
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from families import F
sys.path.insert(0, '/home/user/javad')
from data_provider.event_preprocessing import _read_raw

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
fam_of = {(x['cur'], m): x['name'] for x in F for m in x['members']}
for pair in ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF']:
    raw = _read_raw(f'/home/user/javad/data/{pair}_EVENTS.csv')
    # EURUSD_EVENTS.csv prefixes its USD names with 'usd '; the release map uses the bare names
    key = [(c, re.sub(r'^usd ', '', n) if c == 'USD' else n) for c, n in zip(raw.Currency, raw.Name)]
    raw['Release'] = [fam_of.get(k) for k in key]
    out = (raw.dropna(subset=['Release'])
              .drop_duplicates(['Date', 'Currency', 'Release'])
              .sort_values(['Date', 'Currency', 'Release']))
    out = pd.DataFrame({'Date': out.Date.dt.strftime('%Y-%m-%d'), 'Name': out.Release, 'Currency': out.Currency})
    out.to_csv(os.path.join(OUT, f'{pair}_EVENTS_CORE.csv'), index=False)
    print(pair, len(out), 'rows', out.groupby('Currency').Name.nunique().to_dict())
