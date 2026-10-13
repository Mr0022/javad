"""Render Table 1 (ABDV layout: announcement list) and Table 2 (Plihal layout: counts by sector)."""
import json, sys, os
import pandas as pd
S = os.path.dirname(os.path.abspath(__file__))
fams = json.load(open(f'{S}/families_obs.json'))
times = json.load(open(f'{S}/times_final.json'))          # fid -> {time, tz, note}

PANELS = [('USD', 'U.S. (USD) News Announcements', 'ET'),
          ('EUR', 'Euro-Area (EUR) News Announcements: euro area, Germany, France', 'CET'),
          ('GBP', 'U.K. (GBP) News Announcements', 'UK time'),
          ('JPY', 'Japanese (JPY) News Announcements', 'JST'),
          ('AUD', 'Australian (AUD) News Announcements', 'Sydney time'),
          ('CHF', 'Swiss (CHF) News Announcements', 'CET')]
FREQ = [('Q', 'Quarterly Announcements'), ('M', 'Monthly Announcements'),
        ('P', 'Monetary Policy Decisions'), ('W', 'Weekly Announcements')]
CATS = ['Real Activity', 'Consumption', 'Investment', 'Government', 'Net Exports', 'Prices', 'Forward-Looking', 'Monetary']
CAT_LABEL = {'Government': 'Government Purchases', 'Monetary': 'Money and Credit'}

notes, note_ix = [], {}
def fn(text):
    if text not in note_ix:
        notes.append(text); note_ix[text] = len(notes)
    return note_ix[text]

out, n = [], 0
for cur, title, tz in PANELS:
    sub = [f for f in fams if f['cur'] == cur]
    out.append(f'**Table 1{"" if cur == "USD" else " (continued)"}: {title}**\n')
    out.append(f'| Announcement | Obs.¹ | Dates² | Announcement Time ({tz})³ |')
    out.append('|---|---|---|---|')
    for fcode, flabel in FREQ:
        fs = [f for f in sub if f['freq'] == fcode]
        if not fs: continue
        out.append(f'| ***{flabel}*** | | | |')
        groups = [(None, fs)] if fcode != 'M' else [(c, [f for f in fs if f['cat'] == c]) for c in CATS]
        for cat, items in groups:
            if not items: continue
            if cat: out.append(f'| *{CAT_LABEL.get(cat, cat)}* | | | |')
            for f in items:
                n += 1
                t = times[f['fid']]
                tm = t['time'] + (f"⁽{fn(t['note'])}⁾" if t['note'] else '')
                out.append(f"| {n}- {f['name']} | {f['obs']} | {f['first']}–{f['last']} | {tm} |")
    out.append('')
table1 = '\n'.join(out)

# ---- Table 2: counts by sector (Plihal layout) ----
SECT = ['Housing and Real Estate', 'Industrial Sector', 'Intl Trade & BoP', 'Labor Market', 'Monetary Sector',
        'National Accounts (GDP)', 'Personal/Household Sector', 'Prices', 'Retail & Wholesale Sector',
        'Surveys/Cyclical Indicators', 'Government Finance']
COLS = [('USD', 'US'), ('EUR', 'EA'), ('GBP', 'UK'), ('JPY', 'JP'), ('AUD', 'AU'), ('CHF', 'CH')]
df = pd.DataFrame(fams)
ct = pd.crosstab(df.sector, df.cur).reindex(index=SECT, columns=[c for c, _ in COLS]).fillna(0).astype(int)
t2 = ['**Table 2: The Number of Different News Announcements by Sector**\n',
      '| # | Sector | ' + ' | '.join(l for _, l in COLS) + ' | Total |', '|---|---|' + '---|' * (len(COLS) + 1)]
for i, s in enumerate(SECT, 1):
    row = ct.loc[s]
    t2.append(f'| {i} | {s} | ' + ' | '.join(str(row[c]) for c, _ in COLS) + f' | {row.sum()} |')
tot = ct.sum()
t2.append('| | **Total** | ' + ' | '.join(f'**{tot[c]}**' for c, _ in COLS) + f' | **{tot.sum()}** |')
table2 = '\n'.join(t2)

open(f'{S}/table1.md', 'w').write(table1)
open(f'{S}/table2.md', 'w').write(table2)
json.dump(notes, open(f'{S}/table1_notes.json', 'w'), indent=1)
print(table2); print(len(notes), 'time notes'); print(n, 'rows')
