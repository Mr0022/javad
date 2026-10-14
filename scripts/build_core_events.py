"""
Build the release-level news calendars: CORE (data/<PAIR>_EVENTS_CORE.csv) and
EXT (data/<PAIR>_EVENTS_EXT.csv).

The raw calendars (data/<PAIR>_EVENTS.csv) list one row per published SERIES,
so a single statistical release appears many times (CPI MoM, CPI YoY, core CPI
MoM, ... all on the same morning). Both sets are defined at the level of the
RELEASE instead, and the mapping from raw series to releases lives in
data/event_sets/<set>_release_map.csv (one row per raw series, with the release
it belongs to and the release's metadata).

CORE selection rules
--------------------
  R1 Scope       scheduled official statistics and nationally representative
                 surveys of the domestic economy, plus central-bank policy-rate
                 decisions. Excluded: central-bank communication (speeches,
                 minutes, press conferences, reports, testimony), government
                 debt auctions, positioning/supervisory releases (CFTC, stress
                 tests), commodity-market reports (EIA, OPEC, WASDE), political
                 and supranational events, and official forecasts.
  R2 Geography   national aggregates; for the euro area the area aggregate plus
                 its two largest economies (Germany, France). Sub-national
                 releases (regional Fed surveys, Chicago PMI, German state
                 CPIs) are excluded.
  R3 Continuity  a series enters only if it is published throughout the sample:
                 first release on or before 31 Dec 2014 and still published in
                 2025 (checked on the 2012-01-12 .. 2025-06-30 RV sample).
  R4 Release     every series published in the same statistical release
                 (MoM/YoY, s.a./n.s.a., headline/core, sub-indices, flash and
                 final prints, and one producer's same-day multi-country flash
                 PMIs) is ONE announcement, dated on every day any of its
                 series is published.
  R5 Frequency   at least 24 announcements in the sample (the event loader's
                 min_days), which drops annual releases.

EXT
---
  Every CORE release, unchanged, plus the releases R1-R3 left out: minutes
  and other central-bank publications, regional surveys, bond auctions,
  commodity reports, political meetings, and releases that started after 2014
  or stopped before 2025. EXT drops only speech-like communication (speeches,
  testimony, hearings, press conferences), releases with no macro news (CFTC
  positioning, Treasury bill auctions, ECB meetings without a policy decision)
  and rare releases (R5, or first published after 2021). Its map is written by
  analysis/event_set_study/ext/make_ext.py and listed in
  data/event_sets/EXT_EVENT_SET.md.

Usage
-----
    python scripts/build_core_events.py              # CORE
    python scripts/build_core_events.py --set EXT    # EXT
    python run.py ... --data_path EURUSD_lnRV.csv --event_data_path EURUSD_EVENTS_EXT.csv
    python HAR_X_run.py --pairs EURUSD --event_suffix _EXT
"""

import argparse
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_provider.event_preprocessing import _read_raw  # noqa: E402

PAIRS = ["EURUSD", "GBPUSD", "AUDUSD"]
SETS = {"CORE": "core_release_map.csv", "EXT": "ext_release_map.csv"}


def build(root, map_path, suffix="_CORE", pairs=PAIRS):
    rel_map = pd.read_csv(map_path)
    release_of = {(c, m): r for c, m, r in
                  zip(rel_map.currency, rel_map.member, rel_map.release)}
    for pair in pairs:
        raw = _read_raw(os.path.join(root, f"{pair}_EVENTS.csv"))
        # EURUSD_EVENTS.csv prefixes its USD series with 'usd '; the map uses bare names
        key = [(c, re.sub(r"^usd ", "", n) if c == "USD" else n)
               for c, n in zip(raw.Currency, raw.Name)]
        raw["Release"] = [release_of.get(k) for k in key]
        out = (raw.dropna(subset=["Release"])
                  .drop_duplicates(["Date", "Currency", "Release"])
                  .sort_values(["Date", "Currency", "Release"]))
        out = pd.DataFrame({"Date": out.Date.dt.strftime("%Y-%m-%d"),
                            "Name": out.Release, "Currency": out.Currency})
        path = os.path.join(root, f"{pair}_EVENTS{suffix}.csv")
        out.to_csv(path, index=False)
        print(f"{path}: {len(out)} rows, releases per currency "
              f"{out.groupby('Currency').Name.nunique().to_dict()}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    ap.add_argument("--root_path", default="./data")
    ap.add_argument("--set", default="CORE", choices=sorted(SETS),
                    help="release set to build; picks the map and the file suffix")
    ap.add_argument("--map", default=None,
                    help="release map csv (default: <root_path>/event_sets/<set>_release_map.csv)")
    ap.add_argument("--suffix", default=None, help="output suffix (default: _<SET>)")
    ap.add_argument("--pairs", nargs="+", default=PAIRS)
    a = ap.parse_args()
    build(a.root_path, a.map or os.path.join(a.root_path, "event_sets", SETS[a.set]),
          a.suffix or f"_{a.set}", a.pairs)


if __name__ == "__main__":
    main()
