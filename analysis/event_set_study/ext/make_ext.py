"""Build the EXT release set: map, calendars, excluded-series list and tables.

    python analysis/event_set_study/ext/make_ext.py

writes
    data/event_sets/ext_release_map.csv       raw series -> release: CORE's rows verbatim, then the added ones
    data/event_sets/ext_excluded.csv          every raw series in no EXT release, with the reason
    data/<PAIR>_EVENTS_EXT.csv                through scripts/build_core_events.py
    data/event_sets/EXT_EVENT_SET.md          rules, what is left out, Tables 1-3
    data/event_sets/EXT_EVENT_SET_tables.tex  Tables 1-3 in LaTeX (+ _standalone.tex)

It stops if a raw series sits in no release, is named by no exclusion rule and
is not rare; if a COVERED series falls outside its CORE release's days; if an
added release breaks X3 (first published before 2022) or X5 (at least 24
announcements in every pair that carries it); or if a CORE release comes out
different from the CORE calendar.
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

S = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(S, "..", "..", ".."))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))
from build_core_events import PAIRS, build  # noqa: E402
from data_provider.event_preprocessing import (  # noqa: E402
    _align_to_trading_days, _read_raw, build_daily_event_features, read_trading_dates)
from families_ext import CORE, GROUPS, NEW, exclusion_reason  # noqa: E402

DATA = os.path.join(REPO, "data")
OUT = os.path.join(DATA, "event_sets")
MIN_DAYS = 24                     # X5, the event loader's min_days
FIRST_BEFORE = "2022-01-01"       # X3: the deep models train on 2012-2021
TZ = {"USD": "ET", "EUR": "CET", "GBP": "UK", "AUD": "Sydney"}
# Table 1 counts come from this pair's calendar (the USD rows are the same in all three)
HOME = {"USD": "GBPUSD", "EUR": "EURUSD", "GBP": "GBPUSD", "AUD": "AUDUSD"}
CURS = list(HOME)
PANELS = [("USD", "U.S. (USD) News Announcements", "ET"),
          ("EUR", "Euro-Area (EUR) News Announcements: euro area, Germany, France", "CET"),
          ("GBP", "U.K. (GBP) News Announcements", "UK time"),
          ("AUD", "Australian (AUD) News Announcements", "Sydney time")]
CATS = ["Real Activity", "Consumption", "Investment", "Government",
        "Net Exports", "Prices", "Forward-Looking", "Monetary"]
CAT_LABEL = {"Government": "Government Purchases", "Monetary": "Money and Credit"}
SECT = ["Agriculture", "Energy", "Housing and Real Estate", "Industrial Sector", "Intl Trade & BoP",
        "Labor Market", "Monetary Sector", "National Accounts (GDP)", "Personal/Household Sector", "Prices",
        "Retail & Wholesale Sector", "Surveys/Cyclical Indicators", "Government Finance",
        "Political & Supranational"]
COLS = [("USD", "US"), ("EUR", "EA"), ("GBP", "UK"), ("AUD", "AU")]
ADDED = [("R1", "C", "Central-bank publications (minutes, accounts, reports, bulletins)"),
         ("R1", "A", "Government bond auctions"),
         ("R1", "X", "Commodity-market reports"),
         ("R1", "S", "Political and supranational meetings, official forecasts"),
         ("R2", None, "Sub-national releases (regional Fed surveys, Chicago PMI, ISM-New York, German state CPIs)"),
         ("R3", None, "Started after 2014 or stopped before 2025")]
REASONS = ["speech-like", "no macro news", "rare", "first published after 2021"]


def fail(msg):
    raise SystemExit(f"make_ext.py: {msg}")


# ---- raw calendars and trading days ------------------------------------------
dates = {p: pd.DatetimeIndex(read_trading_dates(DATA, f"{p}_lnRV.csv", "ln_RV")) for p in PAIRS}


def raw_calendar(pair):
    raw = _read_raw(os.path.join(DATA, f"{pair}_EVENTS.csv"))
    # EURUSD_EVENTS.csv prefixes its USD series with 'usd '; the maps use bare names
    raw["Name"] = [re.sub(r"^usd ", "", n) if c == "USD" else n for c, n in zip(raw.Currency, raw.Name)]
    return raw


def day_stats(cal, pair, key):
    """obs = trading days after rolling onto the pair's RV calendar (what the loader
    counts); first/last = publication dates inside the RV sample (CORE's Table 1)."""
    td = dates[pair]
    al, _ = _align_to_trading_days(cal, td, "roll")
    obs = al.groupby(key).trade_date.nunique()
    ins = cal[(cal.Date >= td.min()) & (cal.Date <= td.max())]
    first, last = ins.groupby(key).Date.min(), ins.groupby(key).Date.max()
    return pd.DataFrame({"obs": obs, "first": first, "last": last}).dropna(subset=["obs"])


raw = {p: raw_calendar(p) for p in PAIRS}
inv = pd.concat([day_stats(raw[HOME[c]][raw[HOME[c]].Currency == c], HOME[c], ["Currency", "Name"])
                 for c in CURS]).reset_index()
inv["obs"] = inv.obs.astype(int)

# ---- the release map ----------------------------------------------------------
core_map = pd.read_csv(os.path.join(OUT, "core_release_map.csv"))
core_group = {x["fid"]: x["freq"] for x in CORE}
new_map = pd.DataFrame([dict(currency=x["cur"], country=x["country"], release_id=x["fid"], release=x["name"],
                             frequency=x["frequency"], category=x["cat"], sector=x["sector"], member=m,
                             time_local=x["time"], time_note=x["time_note"] or np.nan, time_zone=TZ[x["cur"]],
                             in_core=False, core_rule=x["core_rule"], table_group=x["group"])
                        for x in NEW for m in x["members"]])
ext_map = pd.concat([core_map.assign(in_core=True, core_rule="", table_group=core_map.release_id.map(core_group)),
                     new_map], ignore_index=True)

if set(new_map.release_id) & set(core_map.release_id):
    fail("an added release reuses a CORE release_id")
if ext_map.groupby("release_id").release.nunique().max() > 1:
    fail("a release_id carries two names")
if ext_map.drop_duplicates("release_id").duplicated(["currency", "release"]).any():
    fail("two releases of one currency share a name")
if ext_map.duplicated(["currency", "member"]).any():
    fail("a raw series is mapped to two releases")
known = set(zip(inv.Currency, inv.Name))
missing = [(c, m) for c, m in zip(new_map.currency, new_map.member) if (c, m) not in known]
if missing:
    fail(f"added members not in the raw calendars: {missing}")
named = [(c, m) for c, m in zip(ext_map.currency, ext_map.member) if exclusion_reason(c, m)]
if named:
    fail(f"EXT members that an exclusion rule names: {named}")

# ---- what stays out -------------------------------------------------------------
members = set(zip(ext_map.currency, ext_map.member))
release_days = {}
for (cur, rid), g in ext_map.groupby(["currency", "release_id"]):
    r = raw[HOME[cur]]
    release_days[rid] = set(r[(r.Currency == cur) & r.Name.isin(g.member)].Date)

excl = []
for r in inv.itertuples():
    if (r.Currency, r.Name) in members:
        continue
    why = exclusion_reason(r.Currency, r.Name)
    if why is None:
        if r.obs >= MIN_DAYS:
            fail(f"{r.Currency} {r.Name!r} ({r.obs} announcements) is in no release and no exclusion rule names it")
        why = ("rare", f"fewer than {MIN_DAYS} announcements")
    rr = raw[HOME[r.Currency]]
    own = set(rr[(rr.Currency == r.Currency) & (rr.Name == r.Name)].Date)
    if why[0] == "covered by a CORE release":
        # within a day: the vendor sometimes stamps one series of a release a day apart
        near = {d + pd.Timedelta(days=k) for d in release_days[why[1]] for k in (-1, 0, 1)}
        if len(own & near) < 0.95 * len(own):
            fail(f"{r.Name!r} is not published on the days of {why[1]}")
    if why[0] == "first published after 2021" and r.first < pd.Timestamp(FIRST_BEFORE):
        fail(f"{r.Name!r} is first published {r.first.date()}, before {FIRST_BEFORE}")
    excl.append(dict(currency=r.Currency, series=r.Name, days=r.obs, first=r.first.date(), last=r.last.date(),
                     reason=why[0], detail=why[1]))
excl = pd.DataFrame(excl).sort_values(["reason", "currency", "series"])

map_path = os.path.join(OUT, "ext_release_map.csv")
ext_map.to_csv(map_path, index=False)
excl.to_csv(os.path.join(OUT, "ext_excluded.csv"), index=False)
build(DATA, map_path, "_EXT")

# ---- release statistics, and the checks on them -------------------------------
cal = {p: pd.read_csv(os.path.join(DATA, f"{p}_EVENTS_EXT.csv"), parse_dates=["Date"]) for p in PAIRS}
for p in PAIRS:
    core_cal = pd.read_csv(os.path.join(DATA, f"{p}_EVENTS_CORE.csv"), parse_dates=["Date"])
    sub = cal[p][cal[p].Name.isin(set(core_cal.Name)) & cal[p].Currency.isin(set(core_cal.Currency))]
    sub = sub.merge(core_cal[["Currency", "Name"]].drop_duplicates(), on=["Currency", "Name"])
    if not sub.reset_index(drop=True).equals(core_cal):
        fail(f"{p}: the CORE releases in the EXT calendar differ from {p}_EVENTS_CORE.csv")
    pair_obs = day_stats(cal[p], p, ["Currency", "Name"]).obs
    if pair_obs.min() < MIN_DAYS:
        fail(f"{p}: {pair_obs.idxmin()} has {int(pair_obs.min())} announcements (< {MIN_DAYS})")

stats = pd.concat([day_stats(cal[HOME[c]][cal[HOME[c]].Currency == c], HOME[c], ["Currency", "Name"]) for c in CURS])
rels = ext_map.drop_duplicates("release_id").copy()
rels["obs"] = [int(stats.loc[(c, n), "obs"]) for c, n in zip(rels.currency, rels.release)]
rels["first"] = [stats.loc[(c, n), "first"] for c, n in zip(rels.currency, rels.release)]
rels["last"] = [stats.loc[(c, n), "last"] for c, n in zip(rels.currency, rels.release)]
late = rels[~rels.in_core & (rels["first"] >= pd.Timestamp(FIRST_BEFORE))]
if len(late):
    fail(f"added releases first published after 2021: {list(late.release)}")

core_obs = {x["fid"]: x for x in json.load(open(os.path.join(S, "..", "core", "families_obs.json")))}
for r in rels[rels.in_core].itertuples():
    x = core_obs[r.release_id]
    if (r.obs, r.first.strftime("%m/%d/%y"), r.last.strftime("%m/%d/%y")) != (x["obs"], x["first"], x["last"]):
        fail(f"{r.release_id}: obs/dates differ from CORE's Table 1")

# loader view: one evt_* column per release, none lost to min_days
cols = {}
for p in PAIRS:
    cols[p] = {}
    for tag, fn in [("raw", f"{p}_EVENTS.csv"), ("CORE", f"{p}_EVENTS_CORE.csv"), ("EXT", f"{p}_EVENTS_EXT.csv")]:
        w = build_daily_event_features(os.path.join(DATA, fn), dates[p], verbose=False)
        cols[p][tag] = (sum(c.startswith("evt_") for c in w.columns), len(w.columns) - 1)
    n_rel = int(rels.currency.isin(["USD", p[:3]]).sum())
    if cols[p]["EXT"][0] != n_rel:
        fail(f"{p}: the loader builds {cols[p]['EXT'][0]} evt_* columns from {n_rel} releases")

# ---- table content ------------------------------------------------------------
order = {x["fid"]: i for i, x in enumerate(CORE)} | {x["fid"]: len(CORE) + i for i, x in enumerate(NEW)}
rels["order"] = rels.release_id.map(order)
rels = rels.sort_values("order")
n_new, n_core = int((~rels.in_core).sum()), int(rels.in_core.sum())
by_cur = rels.groupby("currency").size()
fmt = lambda d: d.strftime("%m/%d/%y")


def table1_rows(cur):
    """[(group label, [(category or None, [release rows])])] in Table 1 order."""
    sub = rels[rels.currency == cur]
    out = []
    for code, label in GROUPS:
        g = sub[sub.table_group == code]
        if not len(g):
            continue
        parts = ([(None, g)] if code != "M" else [(c, g[g.category == c]) for c in CATS])
        out.append((label, [(c, x) for c, x in parts if len(x)]))
    return out


sect = (pd.crosstab(rels.sector, rels.currency).reindex(index=SECT, columns=[c for c, _ in COLS])
        .fillna(0).astype(int))
missing_sect = set(rels.sector) - set(SECT)
if missing_sect:
    fail(f"sectors missing from Table 2: {missing_sect}")
added = []
for rule, group, label in ADDED:
    g = rels[~rels.in_core & (rels.core_rule == rule)]
    if group:
        g = g[g.table_group == group]
    added.append((label, rule, g.groupby("currency").size().reindex([c for c, _ in COLS]).fillna(0).astype(int)))
if sum(a[2].sum() for a in added) != n_new:
    fail("Table 3 does not add up to the added releases")
left = (excl.groupby(["reason", "currency"]).size().unstack(fill_value=0)
        .reindex(index=REASONS + ["covered by a CORE release"], columns=CURS).fillna(0).astype(int))

# ---- markdown -----------------------------------------------------------------
notes, note_ix = [], {}


def note_no(text):
    if text not in note_ix:
        notes.append(text)
        note_ix[text] = len(notes)
    return note_ix[text]


md = ["# EXT news-announcement set", "",
      "Release-level calendar of scheduled announcements for the three pairs (EUR/USD, GBP/USD,",
      f"AUD/USD): every CORE release ([CORE_EVENT_SET.md](CORE_EVENT_SET.md)), unchanged, plus {n_new}",
      "releases that CORE's scope, geography and continuity rules left out. Built by",
      "`analysis/event_set_study/ext/make_ext.py` into `data/event_sets/ext_release_map.csv` and",
      "`data/<PAIR>_EVENTS_EXT.csv`; `python scripts/build_core_events.py --set EXT` rebuilds the",
      "calendars from the map. Every raw series that is in no EXT release is listed, with the",
      "reason, in `data/event_sets/ext_excluded.csv`.", "",
      "Indicator columns the event loader builds from each calendar (`evt_*`, at its default",
      f"`min_days={MIN_DAYS}`; the loader adds `n_events` and one `n_events_<cur>` per currency):", "",
      "| Calendar | " + " | ".join(f"{p[:3]}/{p[3:]}" for p in PAIRS) + " |",
      "|---|" + "---|" * len(PAIRS),
      "| raw, one column per published series (`<PAIR>_EVENTS.csv`) | "
      + " | ".join(str(cols[p]["raw"][0]) for p in PAIRS) + " |",
      "| CORE (`<PAIR>_EVENTS_CORE.csv`) | " + " | ".join(str(cols[p]["CORE"][0]) for p in PAIRS) + " |",
      "| **EXT** (`<PAIR>_EVENTS_EXT.csv`) | " + " | ".join(f"**{cols[p]['EXT'][0]}**" for p in PAIRS) + " |",
      "",
      "The gap between EXT and the raw count is speech-like and other left-out series (below) and,",
      "mostly, series of one release published on the same days (CPI MoM, YoY and core; NFP,",
      "unemployment rate and earnings; flash and final PMIs), which would add identical columns.", "",
      "## Selection rules", "",
      "- **X1 Scope.** Every scheduled release in the calendars, except (a) speech-like communication: "
      "speeches, testimony and parliamentary hearings, press conferences, and the Jackson Hole symposium "
      "(the decision, statement or report they accompany stays in, so no announcement day is lost); and "
      "(b) releases with no macroeconomic news: CFTC positioning reports (published after the Friday "
      "session, on Tuesday's positions), Treasury bill auctions (weekly cash management), and ECB "
      "Governing Council meetings without a monetary-policy decision. Replaces CORE's R1.",
      "- **X2 Geography.** No restriction: sub-national releases (regional Fed surveys, Chicago PMI, "
      "ISM-New York, German state CPIs) are in. Replaces R2.",
      f"- **X3 Training coverage.** A release enters if it is first published before 1 Jan 2022, so it "
      "occurs in the deep models' training years (2012–2021); releases that stop before 2025 stay in. "
      "Replaces R3. It drops the ABS monthly CPI indicator (from Sep-2022) and the Ai Group Industry "
      "Index (from Feb-2023).",
      "- **X4 Release as the unit.** As R4: all series published in one statistical release form one "
      "announcement, dated on every day any of them is published.",
      f"- **X5 Frequency.** As R5: at least {MIN_DAYS} announcements in the sample.", "",
      f"The {n_core} CORE releases enter unchanged, so each CORE indicator is also an EXT indicator with "
      "identical values. Series of a CORE release that CORE's R3 left out of its member list (ISM "
      "sub-indices, U6, Michigan inflation expectations, ...) are published on that release's days and "
      "stay covered by it.", "",
      "Sample: 12 Jan 2012 – 30 Jun 2025 (the RV sample).", "",
      "## What is left out", "",
      "Raw calendar series in no EXT release, by reason (USD counted once; all series in the sample, "
      "rare ones included):", "",
      "| Reason | " + " | ".join(CURS) + " | Total |", "|---|" + "---|" * (len(CURS) + 1)]
for reason in REASONS:
    row = left.loc[reason]
    md.append(f"| {reason} | " + " | ".join(str(row[c]) for c in CURS) + f" | {row.sum()} |")
tot = left.loc[REASONS].sum()
md += ["| **left out** | " + " | ".join(f"**{tot[c]}**" for c in CURS) + f" | **{tot.sum()}** |",
       "| *covered by a CORE release (not left out)* | "
       + " | ".join(str(left.loc['covered by a CORE release', c]) for c in CURS)
       + f" | {left.loc['covered by a CORE release'].sum()} |", ""]
nomacro = excl[excl.reason == "no macro news"]
md += ["- **speech-like**: every central-bank and political speech, testimony and hearing (e.g. "
       "*Fed's Williams speech*, *Fed's Chair Powell testifies*, *BoE Monetary Policy Report "
       "Hearings*), and the FOMC and ECB press conferences.",
       "- **no macro news**: " + "; ".join(f"{c} *{s}*" for c, s in zip(nomacro.currency, nomacro.series)) + ".",
       f"- **rare**: fewer than {MIN_DAYS} announcements — annual and one-off events (elections, "
       "summits on a single issue, budget days, stress tests) and series that ran only briefly.",
       "- **first published after 2021**: " + "; ".join(sorted(set(
           excl[excl.reason == "first published after 2021"].detail))) + ".", ""]


def md_table1():
    out, n = [], 0
    for cur, title, tz in PANELS:
        out += [f"**Table 1{'' if cur == 'USD' else ' (continued)'}: {title}**", "",
                f"| Announcement | Obs.¹ | Dates² | Announcement Time ({tz})³ |", "|---|---|---|---|"]
        for label, parts in table1_rows(cur):
            out.append(f"| ***{label}*** | | | |")
            for cat, g in parts:
                if cat:
                    out.append(f"| *{CAT_LABEL.get(cat, cat)}* | | | |")
                for r in g.itertuples():
                    n += 1
                    note = r.time_note if isinstance(r.time_note, str) else ""
                    tm = r.time_local + (f"⁽{note_no(note)}⁾" if note else "")
                    out.append(f"| {n}- {r.release}{'' if r.in_core else ' †'} | {r.obs} | "
                               f"{fmt(r.first)}–{fmt(r.last)} | {tm} |")
        out.append("")
    return out


md += ["## Table 1", ""] + md_table1()
md += ["Notes: Monthly announcements are grouped into real activity, the components of GDP (consumption, "
       "investment, government purchases, net exports), prices, forward-looking indicators, and money and "
       f"credit. † marks the {n_new} releases EXT adds to CORE; the other {n_core} rows are the CORE "
       "releases, unchanged.", "",
       "1. Number of announcement days in the sample (a day counts once even if several series of the "
       "release are published that day; flash and final prints count separately).",
       "2. First and last announcement in the sample.",
       "3. Scheduled local time of the publisher: U.S. Eastern Time; Central European Time for the euro "
       "area, Germany and France; UK local time; Sydney local time. For the added releases it is the time "
       "at the end of the sample; \"varies\" marks meetings and other releases without a fixed time, "
       "\"—\" a release time we have not verified.", ""]
md += [f"- ⁽{i}⁾ {t}" for i, t in enumerate(notes, 1)]
md += ["", "Also: U.K. producer prices end on 02/19/25 because the ONS suspended the PPI publication in 2025.", ""]

md += ["## Table 2", "", "**Table 2: The Number of Different News Announcements by Sector**", "",
       "| # | Sector | " + " | ".join(l for _, l in COLS) + " | Total |", "|---|---|" + "---|" * (len(COLS) + 1)]
for i, s in enumerate(SECT, 1):
    row = sect.loc[s]
    md.append(f"| {i} | {s} | " + " | ".join(str(row[c]) for c, _ in COLS) + f" | {row.sum()} |")
tot2 = sect.sum()
md += ["| | **Total** | " + " | ".join(f"**{tot2[c]}**" for c, _ in COLS) + f" | **{tot2.sum()}** |", "",
       "Notes: Number of different announcements (releases) per currency, classified into Plihal's "
       "Bloomberg sectors (Agriculture to Surveys/Cyclical Indicators), plus Government Finance (budget "
       "statements, public-sector borrowing, government bond auctions) and Political & Supranational (EU, "
       "G7, G20 and IMF meetings, European Commission forecasts). Central-bank decisions and publications "
       "(minutes, accounts, reports, bulletins) are in the Monetary Sector. EA covers the euro area, "
       "Germany and France.", ""]

md += ["## Table 3", "", f"**Table 3: The {n_new} Releases EXT Adds to CORE, by the CORE Rule That Left Them Out**",
       "", "| CORE rule | Releases | " + " | ".join(l for _, l in COLS) + " | Total |",
       "|---|---|" + "---|" * (len(COLS) + 1)]
tot3 = sum(a[2] for a in added)
for label, rule, counts in added:
    md.append(f"| {rule} | {label} | " + " | ".join(str(counts[c]) for c, _ in COLS) + f" | {counts.sum()} |")
md += ["| | **Total** | " + " | ".join(f"**{tot3[c]}**" for c, _ in COLS) + f" | **{tot3.sum()}** |", "",
       "Notes: R1 scope, R2 geography, R3 continuity (see CORE_EVENT_SET.md). A release CORE excluded on "
       "more than one rule is counted under the first.", ""]
open(os.path.join(OUT, "EXT_EVENT_SET.md"), "w").write("\n".join(md))

# ---- LaTeX ----------------------------------------------------------------------


def esc(s):
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"),
                 ("$", r"\$"), ("–", "--"), ("—", "---")]:
        s = s.replace(a, b)
    return s


tex_notes, tex_ix = [], {}


def mark(text):
    if text not in tex_ix:
        tex_notes.append(text)
        tex_ix[text] = "abcdefghijklmnopqrstuvwxyz"[len(tex_notes) - 1]
    return tex_ix[text]


TCOLS = r"@{}p{0.50\textwidth}rlp{0.21\textwidth}@{}"
t1, n = [], 0
for k, (cur, title, tz) in enumerate(PANELS):
    head = rf"Announcement & Obs.$^{{1}}$ & Dates$^{{2}}$ & Announcement Time ({tz})$^{{3}}$ \\"
    # every longtable steps the table counter, captioned or not: step back before
    # each continuation panel so all four print, and count, as one table
    t1 += ([r"\addtocounter{table}{-1}"] if k else []) + [
           r"\begin{longtable}{" + TCOLS + "}",
           rf"\caption*{{\textbf{{Table \thetable{'' if k == 0 else '{} (continued)'}}}\\ {esc(title)}}}"
           + (r"\label{tab:ext-calendar}" if k == 0 else "") + r"\\",
           r"\toprule", head, r"\midrule", r"\endfirsthead",
           rf"\multicolumn{{4}}{{@{{}}l}}{{\textit{{{esc(title)} (continued)}}}}\\",
           r"\toprule", head, r"\midrule", r"\endhead", r"\bottomrule", r"\endfoot"]
    for label, parts in table1_rows(cur):
        t1.append(rf"\multicolumn{{4}}{{c}}{{\textit{{{label}}}}}\\[2pt]")
        for cat, g in parts:
            if cat:
                t1.append(rf"\multicolumn{{4}}{{@{{}}l}}{{\textit{{{CAT_LABEL.get(cat, cat)}}}}}\\")
            for r in g.itertuples():
                n += 1
                note = r.time_note if isinstance(r.time_note, str) else ""
                tm = esc(r.time_local) + (rf"$^{{{mark(note)}}}$" if note else "")
                t1.append(rf"{n}- {esc(r.release)}{'' if r.in_core else r'$^{\dagger}$'} & {r.obs} & "
                          rf"{fmt(r.first)}--{fmt(r.last)} & {tm} \\")
    t1 += [r"\end{longtable}", ""]
t1 += [r"\begin{flushleft}\footnotesize",
       r"\textit{Notes:} Monthly announcements are grouped into real activity, the components of GDP "
       r"(consumption, investment, government purchases, net exports), prices, forward-looking indicators, "
       r"and money and credit. Each row is one scheduled release; all series published in that release "
       r"(month-on-month and year-on-year changes, seasonally adjusted or not, headline and core, flash and "
       rf"final prints) form one announcement. $^{{\dagger}}$~Added to the CORE calendar ({n_new} releases); "
       rf"the other {n_core} rows are the CORE releases, unchanged.\\[2pt]",
       r"$^{1}$ Number of announcement days in the sample, 12 January 2012 to 30 June 2025 (flash and final "
       r"prints count separately).\\",
       r"$^{2}$ First and last announcement in the sample (mm/dd/yy).\\",
       r"$^{3}$ Scheduled local time of the publisher: U.S. Eastern Time; Central European Time for the euro "
       r"area, Germany and France; UK local time; Sydney local time. For the added releases, the time at the "
       r"end of the sample; ``varies'' marks meetings and other releases without a fixed time, --- a release "
       r"time not verified.\\"]
t1 += [rf"$^{{{tex_ix[x]}}}$ {esc(x)}\\" for x in tex_notes]
t1 += [r"U.K. producer prices end in February 2025, when the ONS suspended the PPI publication.",
       r"\end{flushleft}", ""]

t2 = [r"\begin{table}[htbp]", r"\centering",
      r"\caption{The Number of Different News Announcements by Sector (EXT Calendar)}",
      r"\label{tab:ext-sectors}", r"\begin{tabular}{rl" + "r" * len(COLS) + "r}", r"\toprule",
      r"\# & Sector & " + " & ".join(l for _, l in COLS) + r" & Total \\", r"\midrule"]
for i, s in enumerate(SECT, 1):
    row = sect.loc[s]
    t2.append(rf"{i} & {esc(s)} & " + " & ".join(str(row[c]) for c, _ in COLS) + rf" & {row.sum()} \\")
t2 += [r"\midrule", r" & Total & " + " & ".join(str(tot2[c]) for c, _ in COLS) + rf" & {tot2.sum()} \\",
       r"\bottomrule", r"\end{tabular}",
       r"\begin{minipage}{0.85\textwidth}\vspace{4pt}\footnotesize",
       r"\textit{Notes:} Number of different announcements (releases) per country, classified into "
       r"Plihal's Bloomberg sectors (Agriculture to Surveys/Cyclical Indicators), plus Government Finance "
       r"(budget statements, public-sector borrowing, government bond auctions) and Political \& "
       r"Supranational (EU, G7, G20 and IMF meetings, European Commission forecasts). Central-bank "
       r"decisions and publications are in the Monetary Sector. EA covers the euro area, Germany and France.",
       r"\end{minipage}", r"\end{table}", ""]

t3 = [r"\begin{table}[htbp]", r"\centering",
      r"\caption{Releases the EXT Calendar Adds to CORE, by the CORE Rule That Left Them Out}",
      r"\label{tab:ext-added}", r"\begin{tabular}{lp{0.42\textwidth}" + "r" * len(COLS) + "r}", r"\toprule",
      r"Rule & Releases & " + " & ".join(l for _, l in COLS) + r" & Total \\", r"\midrule"]
for label, rule, counts in added:
    t3.append(rf"{rule} & {esc(label)} & " + " & ".join(str(counts[c]) for c, _ in COLS)
              + rf" & {counts.sum()} \\")
t3 += [r"\midrule", r" & Total & " + " & ".join(str(tot3[c]) for c, _ in COLS) + rf" & {tot3.sum()} \\",
       r"\bottomrule", r"\end{tabular}",
       r"\begin{minipage}{0.85\textwidth}\vspace{4pt}\footnotesize",
       r"\textit{Notes:} R1 scope, R2 geography, R3 continuity of the CORE calendar. A release CORE "
       r"excluded on more than one rule is counted under the first.",
       r"\end{minipage}", r"\end{table}", ""]

header = ["% EXT news-announcement calendar: Table 1 (announcement list), Table 2",
          "% (announcements by sector) and Table 3 (releases added to CORE). Generated by",
          "% analysis/event_set_study/ext/make_ext.py -- do not edit by hand.",
          "% Preamble: \\usepackage{booktabs,longtable,caption}", ""]
open(os.path.join(OUT, "EXT_EVENT_SET_tables.tex"), "w").write("\n".join(header + t1 + t2 + t3))
open(os.path.join(OUT, "EXT_EVENT_SET_tables_standalone.tex"), "w").write(
    "\\documentclass[11pt]{article}\n\\usepackage[margin=2cm]{geometry}\n"
    "\\usepackage{booktabs,longtable,caption}\n\\begin{document}\n"
    "\\input{EXT_EVENT_SET_tables}\n\\end{document}\n")

print(f"EXT: {len(rels)} releases ({n_core} CORE + {n_new} added) "
      f"{by_cur.reindex(CURS).to_dict()}; {len(excl)} raw series left out or covered")
for p in PAIRS:
    print(f"  {p}: evt_* columns raw {cols[p]['raw'][0]}, CORE {cols[p]['CORE'][0]}, EXT {cols[p]['EXT'][0]} "
          f"(all feature columns {cols[p]['EXT'][1]})")
