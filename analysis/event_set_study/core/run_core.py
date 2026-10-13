"""HAR / HAR-NEWS / N-HAR / HAR-X-agg on the CORE release calendar (plain HAR core, no weekday terms)."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, '/home/user/javad')
import numpy as np, pandas as pd
import HAR_X_run as H
from data_provider.event_preprocessing import load_event_features

CAL = sys.argv[1]; pair = sys.argv[2]; OUT = sys.argv[3]
series = H.load_series("/home/user/javad/data", f"{pair}_lnRV.csv", "ln_RV")
ev = load_event_features(CAL, f"{pair}_EVENTS_CORE.csv", series.index, verbose=False)
ev = ev.set_index(pd.DatetimeIndex(ev["date"])).drop(columns="date")
evt = [c for c in ev.columns if c.startswith("evt_")]
reps, groups = H.dedup_dummies(ev.loc[ev.index.year <= H.TRAIN_END_YEAR], evt)
ev["AGG_total"] = ev[evt].sum(axis=1)
ev["AGG_fx"] = ev[[c for c in evt if not c.startswith("evt_USD_")]].sum(axis=1)
HAR = ["RV_d", "RV_w", "RV_m"]
rows, losses = [], []
for h in (1, 5):
    df = H.assemble(series, ev, h, reps + ["AGG_total", "AGG_fx"])
    tr, te = H.split_by_year(df)
    y = te["Y_h"].to_numpy(float); evc = [f"EV_{c}" for c in reps]
    P = {}
    _, P["HAR"] = H.fit_ols(tr, te, HAR, h)
    news, P["HAR-NEWS"] = H.fit_har_news(tr, te, HAR, evc, h)
    info, P["N-HAR"] = H.fit_nhar(tr, te, HAR, evc, h)
    _, P["HAR-X-agg"] = H.fit_ols(tr, te, HAR + ["EV_AGG_total", "EV_AGG_fx"], h)
    for m, p in P.items():
        rows.append(dict(pair=pair, h=h, set="CORE", model=m, n_test=len(te), mse=H.mse(y, p),
                         n_sel=info["n_selected"] if m == "N-HAR" else np.nan, n_cand=len(reps), n_raw=len(evt),
                         rank_def=(news["n_params"] - news["rank"]) if m == "HAR-NEWS" else np.nan))
        losses.append(pd.DataFrame({"pair": pair, "h": h, "set": "CORE", "model": m, "date": te.index, "se": (y - p) ** 2}))
    print(pair, h, len(evt), "->", len(reps), {m: round(H.mse(y, p), 4) for m, p in P.items()}, "sel", info["n_selected"], flush=True)
merged = {k: v for k, v in groups.items() if len(v) > 1}
pd.DataFrame(rows).to_csv(os.path.join(OUT, f"core_{pair}.csv"), index=False)
pd.concat(losses).to_csv(os.path.join(OUT, f"core_losses_{pair}.csv"), index=False)
pd.Series({k: "; ".join(v) for k, v in merged.items()}).to_csv(os.path.join(OUT, f"core_merged_{pair}.csv"))
