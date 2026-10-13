"""Write the CORE calendar tables as LaTeX.

Table 1 follows the layout of Andersen, Bollerslev, Diebold and Vega (2003),
Table 1 (announcement, observations, dates, release time; one panel per
currency). Table 2 follows Plihal's Table 1 (number of announcements by
sector and country). Output:

    data/event_sets/CORE_EVENT_SET_tables.tex             (\\input into a paper)
    data/event_sets/CORE_EVENT_SET_tables_standalone.tex  (compiles on its own)

Preamble needed: \\usepackage{booktabs,longtable,caption}
"""
import json
import os

import pandas as pd

S = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(S, "..", "..", ".."))
OUT = os.path.join(REPO, "data", "event_sets")
fams = json.load(open(f"{S}/families_obs.json"))
times = json.load(open(f"{S}/times_final.json"))

PANELS = [("USD", "U.S. (USD) News Announcements", "ET"),
          ("EUR", "Euro-Area (EUR) News Announcements: Euro Area, Germany, France", "CET"),
          ("GBP", "U.K. (GBP) News Announcements", "UK time"),
          ("AUD", "Australian (AUD) News Announcements", "Sydney time")]
FREQ = [("Q", "Quarterly Announcements"), ("M", "Monthly Announcements"),
        ("P", "Monetary Policy Decisions"), ("W", "Weekly Announcements")]
CATS = ["Real Activity", "Consumption", "Investment", "Government",
        "Net Exports", "Prices", "Forward-Looking", "Monetary"]
CAT_LABEL = {"Government": "Government Purchases", "Monetary": "Money and Credit"}


def esc(s):
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("_", r"\_"), ("#", r"\#"), ("$", r"\$"), ("–", "--"), ("—", "---")]:
        s = s.replace(a, b)
    return s


# time-change notes get letters, so they do not clash with the numbered column notes
notes, note_ix = [], {}


def mark(text):
    if text not in note_ix:
        notes.append(text)
        note_ix[text] = "abcdefghijklmnopqrstuvwxyz"[len(notes) - 1]
    return note_ix[text]


COLS = r"@{}p{0.50\textwidth}rlp{0.21\textwidth}@{}"
t1, n = [], 0
for k, (cur, title, tz) in enumerate(PANELS):
    sub = [f for f in fams if f["cur"] == cur]
    cap = "News Announcements of the CORE Calendar" if k == 0 else "(continued)"
    head = (r"Announcement & Obs.$^{1}$ & Dates$^{2}$ & "
            rf"Announcement Time ({tz})$^{{3}}$ \\")
    t1 += [r"\begin{longtable}{" + COLS + "}",
           rf"\caption*{{\textbf{{Table 1{'' if k == 0 else ' (continued)'}}}\\ {esc(title)}}}"
           + (r"\label{tab:core-calendar}" if k == 0 else "") + r"\\",
           r"\toprule", head, r"\midrule", r"\endfirsthead",
           rf"\multicolumn{{4}}{{@{{}}l}}{{\textit{{{esc(title)} (continued)}}}}\\",
           r"\toprule", head, r"\midrule", r"\endhead",
           r"\bottomrule", r"\endfoot"]
    for code, label in FREQ:
        fs = [f for f in sub if f["freq"] == code]
        if not fs:
            continue
        t1.append(rf"\multicolumn{{4}}{{c}}{{\textit{{{label}}}}}\\[2pt]")
        groups = ([(None, fs)] if code != "M"
                  else [(c, [f for f in fs if f["cat"] == c]) for c in CATS])
        for cat, items in groups:
            if not items:
                continue
            if cat:
                t1.append(rf"\multicolumn{{4}}{{@{{}}l}}{{\textit{{{CAT_LABEL.get(cat, cat)}}}}}\\")
            for f in items:
                n += 1
                t = times[f["fid"]]
                tm = esc(t["time"]) + (rf"$^{{{mark(t['note'])}}}$" if t["note"] else "")
                t1.append(rf"{n}- {esc(f['name'])} & {f['obs']} & "
                          rf"{f['first']}--{f['last']} & {tm} \\")
    t1 += [r"\end{longtable}", ""]

note_lines = [
    r"\begin{flushleft}\footnotesize",
    r"\textit{Notes:} Monthly announcements are grouped into real activity, the "
    r"components of GDP (consumption, investment, government purchases, net exports), "
    r"prices, forward-looking indicators, and money and credit. Each row is one "
    r"scheduled statistical release; all series published in that release "
    r"(month-on-month and year-on-year changes, seasonally adjusted or not, headline "
    r"and core, flash and final prints) form one announcement.\\[2pt]",
    r"$^{1}$ Number of announcement days in the sample, 12 January 2012 to 30 June 2025 "
    r"(flash and final prints count separately).\\",
    r"$^{2}$ First and last announcement in the sample (mm/dd/yy).\\",
    r"$^{3}$ Scheduled local time of the publisher: U.S. Eastern Time; Central European "
    r"Time for the euro area, Germany and France; UK local time; Sydney local time.\\",
]
note_lines += [rf"$^{{{note_ix[x]}}}$ {esc(x)}\\" for x in notes]
note_lines += [r"U.K. producer prices end in February 2025, when the ONS suspended the "
               r"PPI publication. JOLTS and the S\&P Global U.S. services PMI enter the "
               r"calendar in December 2013.",
               r"\end{flushleft}", ""]
t1 += note_lines

# ---- Table 2: counts by sector (Plihal layout) ------------------------------
SECT = ["Housing and Real Estate", "Industrial Sector", "Intl Trade & BoP", "Labor Market",
        "Monetary Sector", "National Accounts (GDP)", "Personal/Household Sector", "Prices",
        "Retail & Wholesale Sector", "Surveys/Cyclical Indicators", "Government Finance"]
CUR = [("USD", "US"), ("EUR", "EA"), ("GBP", "UK"), ("AUD", "AU")]
df = pd.DataFrame(fams)
ct = (pd.crosstab(df.sector, df.cur).reindex(index=SECT, columns=[c for c, _ in CUR])
      .fillna(0).astype(int))
t2 = [r"\begin{table}[htbp]", r"\centering",
      r"\caption{The Number of Different News Announcements by Sector}",
      r"\label{tab:core-sectors}", r"\begin{tabular}{rl" + "r" * len(CUR) + "r}",
      r"\toprule",
      r"\# & Sector & " + " & ".join(l for _, l in CUR) + r" & Total \\", r"\midrule"]
for i, s in enumerate(SECT, 1):
    row = ct.loc[s]
    t2.append(rf"{i} & {esc(s)} & " + " & ".join(str(row[c]) for c, _ in CUR)
              + rf" & {row.sum()} \\")
tot = ct.sum()
t2 += [r"\midrule",
       r" & Total & " + " & ".join(str(tot[c]) for c, _ in CUR) + rf" & {tot.sum()} \\",
       r"\bottomrule", r"\end{tabular}",
       r"\begin{minipage}{0.85\textwidth}\vspace{4pt}\footnotesize",
       r"\textit{Notes:} Number of different announcements (releases) per country, "
       r"classified into Plihal's Bloomberg sectors. Agriculture and Energy are empty "
       r"because commodity-market reports are excluded and are omitted; Government "
       r"Finance (budget statements, public-sector borrowing) is added. EA covers the "
       r"euro area, Germany and France.",
       r"\end{minipage}", r"\end{table}", ""]

header = ["% CORE news-announcement calendar: Table 1 (announcement list) and",
          "% Table 2 (announcements by sector). Generated by",
          "% analysis/event_set_study/core/make_tex.py -- do not edit by hand.",
          "% Preamble: \\usepackage{booktabs,longtable,caption}", ""]
body = "\n".join(header + t1 + t2)
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "CORE_EVENT_SET_tables.tex"), "w").write(body)
open(os.path.join(OUT, "CORE_EVENT_SET_tables_standalone.tex"), "w").write(
    "\\documentclass[11pt]{article}\n\\usepackage[margin=2cm]{geometry}\n"
    "\\usepackage{booktabs,longtable,caption}\n\\begin{document}\n"
    "\\input{CORE_EVENT_SET_tables}\n\\end{document}\n")
print(f"{n} announcements, {len(notes)} time notes -> {OUT}")
