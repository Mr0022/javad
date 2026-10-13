"""Event HAR models with NO weekday terms: core = plain HAR (RV_d, RV_w, RV_m).

HAR        : OLS on the HAR core
HAR-NEWS   : HAR + every event dummy in the set, OLS (no penalty)
N-HAR      : HAR + event dummies, LASSO on the dummies only (HAR core unpenalised)
HAR-X-agg  : HAR + 2 pooled counts (all releases in set, non-USD releases in set), OLS
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import HAR_X_run as H
import run_sets_losses as S
from data_provider.event_preprocessing import load_event_features, resolve_event_path

D = os.path.dirname(os.path.abspath(S.__file__))
pair = sys.argv[1]
dp = f"{pair}_lnRV.csv"
series = H.load_series("data", dp, "ln_RV")
ev = load_event_features("data", resolve_event_path("data", dp, None), series.index, verbose=False)
ev = ev.set_index(pd.DatetimeIndex(ev["date"])).drop(columns="date")
evt_all = [c for c in ev.columns if c.startswith("evt_")]
train_mask = ev.index.year <= H.TRAIN_END_YEAR
HAR = ["RV_d", "RV_w", "RV_m"]
rows, losses = [], []
for which in ["HEADLINE", "PLIHAL", "ALL"]:
    cols = S.subset(evt_all, which)
    reps, _ = H.dedup_dummies(ev.loc[train_mask], cols)
    ev["AGG_total"] = ev[cols].sum(axis=1)
    ev["AGG_fx"] = ev[[c for c in cols if not c.startswith("evt_USD_")]].sum(axis=1)
    for h in (1, 5):
        df = H.assemble(series, ev, h, reps + ["AGG_total", "AGG_fx"])
        tr, te = H.split_by_year(df)
        y = te["Y_h"].to_numpy(float)
        evc = [f"EV_{c}" for c in reps]
        preds = {}
        _, preds["HAR"] = H.fit_ols(tr, te, HAR, h)
        news, preds["HAR-NEWS"] = H.fit_har_news(tr, te, HAR, evc, h)
        info, preds["N-HAR"] = H.fit_nhar(tr, te, HAR, evc, h)
        _, preds["HAR-X-agg"] = H.fit_ols(tr, te, HAR + ["EV_AGG_total", "EV_AGG_fx"], h)
        for m, p in preds.items():
            rows.append(dict(pair=pair, h=h, set=which, model=m, n_test=len(te), mse=H.mse(y, p),
                             n_sel=info["n_selected"] if m == "N-HAR" else np.nan,
                             n_cand=len(reps), rank_def=(news["n_params"] - news["rank"]) if m == "HAR-NEWS" else np.nan))
            losses.append(pd.DataFrame({"pair": pair, "h": h, "set": which, "model": m,
                                        "date": te.index, "se": (y - p) ** 2}))
        print(pair, h, which, {m: round(H.mse(y, p), 4) for m, p in preds.items()}, "sel", info["n_selected"], "/", len(reps), flush=True)
pd.DataFrame(rows).to_csv(os.path.join(D, f"nodow_{pair}.csv"), index=False)
pd.concat(losses).to_csv(os.path.join(D, f"nodow_losses_{pair}.csv"), index=False)
