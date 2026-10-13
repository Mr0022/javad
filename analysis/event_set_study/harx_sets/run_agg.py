"""HAR-X-agg (removed in ac9b329): HAR+DOW + pooled release counts, plain OLS, no LASSO.

Counts are the forward horizon mean of (a) all releases in the set that day and
(b) the non-USD releases in the set, exactly the two regressors the old model used
(n_events + n_events_<fx>), but built from each event set instead of the raw calendar.
'RAW' reproduces the original definition: every release in the calendar file.
"""
import os, sys, re, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/user/javad")
import numpy as np, pandas as pd
import HAR_X_run as H
import run_sets_losses as S
from data_provider.event_preprocessing import load_event_features, resolve_event_path

D = os.path.dirname(os.path.abspath(__file__))
rows = []
for pair in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]:
    dp = f"{pair}_lnRV.csv"
    series = H.load_series("data", dp, "ln_RV")
    ev = load_event_features("data", resolve_event_path("data", dp, None), series.index, verbose=False)
    ev = ev.set_index(pd.DatetimeIndex(ev["date"])).drop(columns="date")
    evt_all = [c for c in ev.columns if c.startswith("evt_")]
    fx = pair.replace("USD", "").lower()
    for which in ["HEADLINE", "PLIHAL", "ALL", "RAW"]:
        if which == "RAW":
            tot, fxc = ev["n_events"], ev[f"n_events_{fx}"]
        else:
            cols = S.subset(evt_all, which)
            tot = ev[cols].sum(axis=1)
            fxc = ev[[c for c in cols if not c.startswith("evt_USD_")]].sum(axis=1)
        ev["AGG_total"], ev["AGG_fx"] = tot, fxc
        for h in (1, 5):
            df = H.assemble(series, ev, h, ["AGG_total", "AGG_fx"])
            tr, te = H.split_by_year(df)
            har = ["RV_d", "RV_w", "RV_m"]; dow = ["DOW_MON", "DOW_TUE", "DOW_THU", "DOW_FRI"]
            y = te["Y_h"].to_numpy(float)
            _, p_dow = H.fit_ols(tr, te, har + dow, h)
            res, p_agg = H.fit_ols(tr, te, har + dow + ["EV_AGG_total", "EV_AGG_fx"], h)
            rows.append(dict(pair=pair, h=h, set=which, n_test=len(te),
                             mse_har_dow=H.mse(y, p_dow), mse_agg=H.mse(y, p_agg),
                             b_total=res.params["EV_AGG_total"], t_total=res.tvalues["EV_AGG_total"],
                             b_fx=res.params["EV_AGG_fx"], t_fx=res.tvalues["EV_AGG_fx"]))
r = pd.DataFrame(rows)
r.to_csv(os.path.join(D, "results_agg.csv"), index=False)
pd.set_option("display.width", 200)
print(r.round(4).to_string(index=False))
