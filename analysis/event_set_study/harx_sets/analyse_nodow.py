import glob, os, numpy as np, pandas as pd
from scipy import stats
D = os.path.dirname(os.path.abspath(__file__))
r = pd.concat(pd.read_csv(f) for f in sorted(glob.glob(f"{D}/nodow_[A-Z]*.csv")))
L = pd.concat(pd.read_csv(f) for f in sorted(glob.glob(f"{D}/nodow_losses_*.csv")))
PAIRS = ["EURUSD", "GBPUSD", "AUDUSD"]; SETS = ["HEADLINE", "PLIHAL", "ALL"]

def dm(d, h):
    d = np.asarray(d, float); T = len(d); u = d - d.mean(); Lg = max(h - 1, 0)
    v = u @ u / T + 2 * sum((1 - k / (Lg + 1)) * (u[k:] @ u[:-k]) / T for k in range(1, Lg + 1))
    s = d.mean() / np.sqrt(v / T) * np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    return s, 2 * stats.t.sf(abs(s), T - 1)

har = r[r.model == "HAR"].groupby(["pair", "h"]).mse.first()
assert r[r.model == "HAR"].groupby(["pair", "h"]).mse.nunique().max() == 1   # same HAR in every set
for m in ["HAR-NEWS", "N-HAR", "HAR-X-agg"]:
    print(f"\n### {m}")
    for h in (1, 5):
        print(f" h={h}")
        for p in PAIRS:
            g = r[(r.model == m) & (r.pair == p) & (r.h == h)].set_index("set").mse
            sig = []
            for s in SETS:
                x = L[(L.pair == p) & (L.h == h) & (L.set == s)]
                a = x[x.model == m].set_index("date").se; b = x[x.model == "HAR"].set_index("date").se
                st, pv = dm(a - b, h); sig.append("*" if pv < 0.05 and st < 0 else ("(worse*)" if pv < 0.05 else ""))
            print(f"  {p} HAR {har[(p, h)]:.4f} | " + " | ".join(f"{s} {g[s]:.4f}{sg}" for s, sg in zip(SETS, sig)))
        mm = r[(r.model == m) & (r.h == h)].groupby("set").mse.mean()[SETS]
        hm = har.xs(h, level="h").mean()
        print(f"  MEAN HAR {hm:.4f} | " + " | ".join(f"{s} {mm[s]:.4f} ({100*(mm[s]/hm-1):+.1f}%)" for s in SETS))
print("\nN-HAR selected / candidates:")
print(r[r.model == "N-HAR"].pivot_table(index=["h", "pair"], columns="set", values=["n_sel", "n_cand"]).astype(int))
print("HAR-NEWS rank deficiency max:", r[r.model == "HAR-NEWS"].rank_def.max())
