import glob, os, numpy as np, pandas as pd
from scipy import stats
D = os.path.dirname(os.path.abspath(__file__))
res = pd.concat(pd.read_csv(f) for f in sorted(glob.glob(f"{D}/results2_*.csv")))
los = pd.concat(pd.read_csv(f) for f in sorted(glob.glob(f"{D}/losses_*.csv")))
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]; SETS = ["HEADLINE", "PLIHAL", "ALL"]

def dm(d, h):
    """Diebold-Mariano with Newey-West (lag h-1) and the HLN small-sample correction."""
    d = np.asarray(d, float); T = len(d); dbar = d.mean(); u = d - dbar
    L = max(h - 1, 0)
    v = u @ u / T + 2 * sum((1 - k / (L + 1)) * (u[k:] @ u[:-k]) / T for k in range(1, L + 1))
    stat = dbar / np.sqrt(v / T)
    stat *= np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    return stat, 2 * stats.t.sf(abs(stat), T - 1)

print("MSE table (N-HAR / HAR-NEWS), HAR+DOW for reference")
for h in (1, 5):
    print(f"\n h = {h}")
    for p in PAIRS:
        g = res[(res.pair == p) & (res.h == h)].set_index("set")
        print(f"  {p}  HAR+DOW {g.mse_har_dow.iloc[0]:.4f} | " + " | ".join(
            f"{s}: N-HAR {g.loc[s, 'mse_nhar']:.4f} HAR-NEWS {g.loc[s, 'mse_har_news']:.4f}" for s in SETS))
    m = res[res.h == h].groupby("set")[["mse_har_dow", "mse_har_news", "mse_nhar"]].mean().loc[SETS]
    print("  mean:\n", m.round(4).to_string())

print("\nDM tests (negative stat = first set better), model-wise")
for model in ("N-HAR", "HAR-NEWS"):
    for h in (1, 5):
        for a, b in (("HEADLINE", "ALL"), ("PLIHAL", "ALL"), ("HEADLINE", "PLIHAL")):
            out = []
            for p in PAIRS:
                x = los[(los.pair == p) & (los.h == h) & (los.model == model)]
                A = x[x.set == a].set_index("date").se; B = x[x.set == b].set_index("date").se
                st, pv = dm((A - B).dropna(), h)
                out.append(f"{p} {st:+.2f}(p={pv:.2f})")
            print(f"  {model:<8} h={h} {a} vs {b}: " + "  ".join(out))
