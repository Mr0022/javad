"""HAR-X / N-HAR on three event subsets: HEADLINE, PLIHAL (sectors 1-12), ALL."""
import sys, os, re, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/user/javad")
import numpy as np, pandas as pd
import HAR_X_run as H
from data_provider.event_preprocessing import (load_event_features, resolve_event_path,
                                               _sanitise, DEFAULT_MIN_DAYS, DEFAULT_ON_NONTRADING)

SCR = os.path.dirname(os.path.abspath(__file__))
CLASSIFIED = os.path.join(SCR, "..", "classified.csv")
PLIHAL_SECTORS = ['Agriculture','Energy','Housing & Real Estate','Industrial Sector','Intl. Trade & BoP',
                  'Labor Market','Monetary Sector','National Accounts (GDP)','Personal/Household Sector',
                  'Prices','Retail & Wholesale Sector','Surveys/Cyclical Indicators']

HEADLINE = {
 'USD': ["Gross Domestic Product Annualized","Employment Cost Index","Nonfarm Productivity","Current Account",
         "Nonfarm Payrolls","ADP Employment Change","Retail Sales (MoM)","Industrial Production (MoM)",
         "Capacity Utilization","Personal Income (MoM)","Consumer Credit Change","Personal Spending",
         "New Home Sales (MoM)","Existing Home Sales (MoM)","Durable Goods Orders","Construction Spending (MoM)",
         "Factory Orders (MoM)","Business Inventories","Monthly Budget Statement","Goods and Services Trade Balance",
         "Producer Price Index (MoM)","Consumer Price Index (YoY)","Core Personal Consumption Expenditures - Price Index (MoM)",
         "Consumer Confidence","Michigan Consumer Sentiment Index","ISM Manufacturing PMI","ISM Services PMI",
         "Housing Starts (MoM)","Building Permits (MoM)","Philadelphia Fed Manufacturing Survey",
         "Fed Interest Rate Decision","FOMC Minutes","Initial Jobless Claims","Continuing Jobless Claims"],
 'EUR': ["eur Gross Domestic Product s.a. (QoQ)","ger Gross Domestic Product (QoQ)","eur Employment Change (QoQ)",
         "eur Labor Cost Index","eur Unemployment Rate","ger Unemployment Change","eur Industrial Production s.a. (MoM)",
         "ger Industrial Production s.a. (MoM)","eur Retail Sales (MoM)","ger Retail Sales (MoM)","ger Factory Orders s.a. (MoM)",
         "eur Construction Output s.a (MoM)","eur Trade Balance s.a.","ger Trade Balance s.a.","eur Current Account s.a",
         "eur Harmonized Index of Consumer Prices (YoY)","eur Core Harmonized Index of Consumer Prices (YoY)",
         "ger Consumer Price Index (YoY)","eur Producer Price Index (MoM)","ger Producer Price Index (MoM)",
         "ger Import Price Index (MoM)","eur HCOB Manufacturing PMI","eur HCOB Services PMI","ger IFO – Business Climate",
         "ger ZEW Survey – Economic Sentiment","eur Economic Sentiment Indicator","eur Consumer Confidence",
         "ger GfK Consumer Confidence Survey","eur Sentix Investor Confidence","eur M3 Money Supply (YoY)",
         "eur ECB Main Refinancing Operations Rate","eur ECB Press Conference","eur ECB Monetary Policy Meeting Accounts"],
 'GBP': ["Gross Domestic Product (QoQ)","Gross Domestic Product (MoM)","ILO Unemployment Rate (3M)","Claimant Count Change",
         "Average Earnings Including Bonus (3Mo/Yr)","Industrial Production (MoM)","Manufacturing Production (MoM)",
         "Retail Sales (MoM)","Goods Trade Balance","Current Account","Consumer Price Index (YoY)","Core Consumer Price Index (YoY)",
         "Producer Price Index - Output (MoM) n.s.a","S&P Global Manufacturing PMI","S&P Global Services PMI",
         "S&P Global Construction PMI","GfK Consumer Confidence","CBI Industrial Trends Survey – Orders (MoM)",
         "Public Sector Net Borrowing","Mortgage Approvals","Nationwide Housing Prices s.a (MoM)",
         "BoE Interest Rate Decision","BoE Minutes"],
 'AUD': ["Gross Domestic Product (QoQ)","Employment Change s.a.","Unemployment Rate s.a.","Wage Price Index (QoQ)",
         "Retail Sales s.a. (MoM)","Trade Balance (MoM)","Current Account Balance","Quarterly Consumer Price Index (QoQ)",
         "Quarterly RBA Trimmed Mean CPI (QoQ)","Producer Price Index (QoQ)","Building Permits (MoM)","Private Capital Expenditure",
         "National Australia Bank's Business Confidence","Westpac Consumer Confidence","Private Sector Credit (MoM)",
         "S&P Global Manufacturing PMI","RBA Interest Rate Decision","RBA Meeting Minutes"],
}

def key(cur, name):
    # USD names carry a 'usd ' prefix in EURUSD_EVENTS.csv only; drop it so files agree
    if cur == 'USD':
        name = re.sub(r'^usd ', '', name)
    return f"evt_{cur}_{_sanitise(name)}"

LOSSES = []
cls = pd.read_csv(CLASSIFIED)
plihal_keys = {key(c, n) for c, n, s in zip(cls.Currency, cls.Name, cls.sector) if s in PLIHAL_SECTORS}
headline_keys = {key(c, n) for c, names in HEADLINE.items() for n in names}

def subset(evt_all, which):
    norm = {c: re.sub(r'^evt_USD_usd_', 'evt_USD_', c) for c in evt_all}
    if which == 'ALL':
        return list(evt_all)
    pool = headline_keys if which == 'HEADLINE' else plihal_keys
    return [c for c in evt_all if norm[c] in pool]

def run(pair, horizons=(1, 5), sets=('HEADLINE', 'PLIHAL', 'ALL')):
    data_path = f"{pair}_lnRV.csv"
    series = H.load_series("data", data_path, "ln_RV")
    events = load_event_features("data", resolve_event_path("data", data_path, None), series.index,
                                 verbose=False, min_days=DEFAULT_MIN_DAYS, on_nontrading=DEFAULT_ON_NONTRADING)
    events = events.set_index(pd.DatetimeIndex(events["date"])).drop(columns="date")
    evt_all = [c for c in events.columns if c.startswith("evt_")]
    train_mask = events.index.year <= H.TRAIN_END_YEAR
    rows = []
    for which in sets:
        cols = subset(evt_all, which)
        if which == 'HEADLINE':   # every headline release must be found in this pair's calendar
            fx = pair.replace('USD', '') or 'USD'
            want = {k for k in headline_keys if k.startswith('evt_USD_') or k.startswith(f'evt_{fx}_')}
            got = {re.sub(r'^evt_USD_usd_', 'evt_USD_', c) for c in cols}
            assert want == got, (pair, sorted(want - got))
        n_by_cur = pd.Series([c.split('_')[1] for c in cols]).value_counts().to_dict()
        reps, _ = H.dedup_dummies(events.loc[train_mask], cols)
        for h in horizons:
            df = H.assemble(series, events, h, reps)
            train, test = H.split_by_year(df)
            har = ["RV_d", "RV_w", "RV_m"]; dow = ["DOW_MON", "DOW_TUE", "DOW_THU", "DOW_FRI"]
            ev = [f"EV_{c}" for c in reps]
            y = test["Y_h"].to_numpy(float)
            _, p_dow = H.fit_ols(train, test, har + dow, h)
            news, p_news = H.fit_har_news(train, test, har + dow, ev, h)
            info, p_nhar = H.fit_nhar(train, test, har + dow, ev, h)
            base = H.mse(y, p_dow)
            for m, p in (("HAR+DOW", p_dow), ("HAR-NEWS", p_news), ("N-HAR", p_nhar)):
                LOSSES.append(pd.DataFrame({"pair": pair, "h": h, "set": which, "model": m,
                                            "date": test.index, "se": (y - p) ** 2}))
            rows.append(dict(pair=pair, h=h, set=which, n_usd=n_by_cur.get('USD', 0),
                             n_fx=sum(v for k, v in n_by_cur.items() if k != 'USD'),
                             n_after_dedup=len(reps), n_test=len(test),
                             mse_har_dow=base, mse_har_news=H.mse(y, p_news), mse_nhar=H.mse(y, p_nhar),
                             nhar_selected=info["n_selected"], har_news_rank_def=news["n_params"] - news["rank"]))
            r = rows[-1]
            print(f"{pair} h={h} {which:<8} USD={r['n_usd']:>3} FX={r['n_fx']:>3} dedup={r['n_after_dedup']:>3} "
                  f"HAR+DOW={base:.4f} HAR-NEWS={r['mse_har_news']:.4f} N-HAR={r['mse_nhar']:.4f} "
                  f"sel={r['nhar_selected']}", flush=True)
    return rows

if __name__ == "__main__":
    pairs = sys.argv[1:] or ["EURUSD", "GBPUSD", "AUDUSD"]
    out = []
    for p in pairs:
        out += run(p)
    tag = '_'.join(pairs)
    pd.DataFrame(out).to_csv(os.path.join(SCR, f"results2_{tag}.csv"), index=False)
    pd.concat(LOSSES).to_csv(os.path.join(SCR, f"losses_{tag}.csv"), index=False)
