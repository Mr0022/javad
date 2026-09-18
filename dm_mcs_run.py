"""
==============================================================================
Equal-predictive-ability tests for the four benchmark models
==============================================================================

Reads the per-observation TEST losses every model writes and runs, for each
(pair, horizon, loss function):

  * Diebold-Mariano  -- every pair of models, two-sided, Newey-West at lag
                        h-1 with the Harvey-Leybourne-Newbold correction
  * Model Confidence Set -- Hansen, Lunde & Nason (2011), T_max, stationary
                        bootstrap

Alignment is the whole point of this script
-------------------------------------------
Both tests require every model to be scored on an IDENTICAL sample. The two
model families would not produce one by default: Dataset_Custom back-fills the
deep models' test slice by seq_len, so they would forecast from the last 2023
trading day onwards, while HAR-RV and N-HAR index rows by the predictor date
and start at the first 2024 row. Two settings remove that gap at the source --
data_loader.TEST_ORIGIN_ALIGN = 1 drops the deep models' extra leading origin,
and data_factory.DROP_LAST_TEST = False stops the test loader discarding its
final partial batch -- so all four models arrive here on the same origins.
Every loss file is keyed by its FORECAST ORIGIN date (the last day whose
information the forecast used) and this script inner-joins on
(pair, horizon, date), which should now drop nothing. The surviving row count
is reported per cell as `n`; a cell whose models disagree on their origins is
reported as misaligned and a cell where the join collapses is skipped loudly,
rather than either being tested on whatever happens to overlap.

Seeds
-----
Deep runs sweep --itr seeds and write one file each. Per-observation losses
are averaged across seeds, so the tests compare the seed-averaged loss of the
training procedure, not one lucky initialisation. --seed_agg none instead
keeps seeds as separate models (ModernTCN@2021, ...), which is a way to see
the seed spread next to the between-model spread.

Usage
-----
    python dm_mcs_run.py \
        --losses "benchmark_h1_h5/har_rv/*/HAR-RV results/har_rv_losses.csv" \
                 "benchmark_h1_h5/har_x/har_x_losses.csv" \
                 "benchmark_h1_h5/losses/*.csv" \
        --out_dir benchmark_h1_h5/tests
==============================================================================
"""

import argparse
import glob
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from utils.forecast_tests import dm_test, mcs

LOSS_COLS = ["se", "ae", "qlike"]
LOSS_LABEL = {"se": "MSE", "ae": "MAE", "qlike": "QLIKE"}
DEFAULT_MODELS = ["HAR-RV", "HAR-NEWS", "N-HAR", "ModernTCN", "FiLM-TCN",
                  "FiLM-TCN-L1"]
KEY = ["pair", "horizon", "model", "date"]


# ==============================================================================
# 1.  COLLECT
# ==============================================================================

def load_losses(patterns, models, seed_agg="mean"):
    """Read every matching loss csv into one tidy frame, one row per
    (pair, horizon, model, origin date)."""
    paths = []
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if not hits:
            print(f"  ! no files matched {pat!r}")
        paths.extend(hits)
    if not paths:
        raise SystemExit("no loss files found -- run the models first")

    frames = []
    for p in paths:
        df = pd.read_csv(p, parse_dates=["date"])
        missing = [c for c in KEY + LOSS_COLS if c not in df.columns]
        if missing:
            print(f"  ! {p}: missing {missing}, skipped")
            continue
        frames.append(df)
        print(f"  {len(df):>6} rows  {p}")
    raw = pd.concat(frames, ignore_index=True)

    keep = raw[raw["model"].isin(models)].copy()
    dropped = sorted(set(raw["model"]) - set(models))
    if dropped:
        print(f"\n  ignoring models not in --models: {dropped}")
    if keep.empty:
        raise SystemExit(f"none of {models} present; file models are "
                         f"{sorted(set(raw['model']))}")

    if seed_agg == "none" and "seed" in keep.columns:
        has_seed = keep["seed"].notna() & (keep["seed"] != -1)
        keep.loc[has_seed, "model"] = (keep.loc[has_seed, "model"].astype(str)
                                       + "@" + keep.loc[has_seed, "seed"].astype(int).astype(str))

    # average the per-observation losses over seeds (and guard against a run
    # being collected twice, which would otherwise double-weight it)
    agg = keep.groupby(KEY, as_index=False)[LOSS_COLS].mean()
    if "seed" in keep.columns:
        n_seeds = (keep.groupby(["pair", "horizon", "model"])["seed"]
                   .nunique().rename("n_seeds").reset_index())
        agg = agg.merge(n_seeds, on=["pair", "horizon", "model"], how="left")
    return agg


# ==============================================================================
# 2.  ALIGN
# ==============================================================================

def aligned_panel(df, pair, horizon, loss):
    """date x model matrix of one loss, restricted to origins every model has."""
    sub = df[(df["pair"] == pair) & (df["horizon"] == horizon)]
    wide = sub.pivot_table(index="date", columns="model", values=loss)
    return wide.dropna(axis=0, how="any").sort_index()


# ==============================================================================
# 3.  TESTS
# ==============================================================================

def run_cell(panel, pair, horizon, loss, alpha, n_boot, seed):
    """DM for every model pair + one MCS, on one aligned panel."""
    models = list(panel.columns)
    dm_rows, mcs_rows = [], []

    for i, a in enumerate(models):
        for b in models[i + 1:]:
            r = dm_test(panel[a].to_numpy(), panel[b].to_numpy(), h=horizon)
            better = (a if r["mean_diff"] < 0 else b) if np.isfinite(r["mean_diff"]) else None
            dm_rows.append({
                "pair": pair, "horizon": horizon, "loss": LOSS_LABEL[loss],
                "model_a": a, "model_b": b,
                "mean_loss_a": float(panel[a].mean()),
                "mean_loss_b": float(panel[b].mean()),
                "mean_diff": r["mean_diff"], "dm_stat": r["stat"],
                "p_value": r["p_value"], "n": r["n"],
                "better": better,
                "significant_5pct": bool(np.isfinite(r["p_value"]) and r["p_value"] < 0.05),
            })

    res = mcs(panel, alpha=alpha, n_boot=n_boot, h=horizon, seed=seed)
    for model, row in res.iterrows():
        mcs_rows.append({
            "pair": pair, "horizon": horizon, "loss": LOSS_LABEL[loss],
            "model": model, "mean_loss": row["mean_loss"], "rank": int(row["rank"]),
            "mcs_p": row["mcs_p"], "in_mcs": bool(row["in_mcs"]),
            "eliminated_at": row["eliminated_at"], "n": len(panel),
        })
    return dm_rows, mcs_rows


# ==============================================================================
# 4.  MAIN
# ==============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="Diebold-Mariano and Model Confidence Set tests over the "
                    "benchmark's per-observation losses.")
    ap.add_argument("--losses", nargs="+", required=True,
                    help="glob(s) matching per-observation loss csvs")
    ap.add_argument("--out_dir", type=str, default="tests")
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS,
                    help=f"models to compare (default: {' '.join(DEFAULT_MODELS)})")
    ap.add_argument("--alpha", type=float, default=0.10,
                    help="MCS level; the set is {model : mcs_p >= alpha}")
    ap.add_argument("--n_boot", type=int, default=2000,
                    help="stationary-bootstrap replications for the MCS")
    ap.add_argument("--seed", type=int, default=2021, help="bootstrap seed")
    ap.add_argument("--seed_agg", choices=["mean", "none"], default="mean",
                    help="'mean' averages deep losses over seeds; 'none' keeps "
                         "each seed as its own model")
    ap.add_argument("--min_obs", type=int, default=30,
                    help="skip a cell whose aligned sample is smaller than this")
    args = ap.parse_args()

    print("=" * 78)
    print("  Collecting per-observation losses")
    print("=" * 78)
    df = load_losses(args.losses, args.models, args.seed_agg)

    pairs = sorted(df["pair"].unique())
    horizons = sorted(df["horizon"].unique())
    print(f"\n  models   : {sorted(df['model'].unique())}")
    print(f"  pairs    : {pairs}")
    print(f"  horizons : {horizons}")

    dm_all, mcs_all, skipped, misaligned = [], [], [], []
    for pair in pairs:
        for h in horizons:
            probe = aligned_panel(df, pair, h, "se")
            have = list(probe.columns)
            if len(have) < 2 or len(probe) < args.min_obs:
                skipped.append((pair, h, len(have), len(probe)))
                continue

            # every model should already be scored on the same origins
            # (data_loader.TEST_ORIGIN_ALIGN); say so when they are not,
            # rather than quietly testing whatever happens to overlap
            raw = (df[(df["pair"] == pair) & (df["horizon"] == h)]
                   .groupby("model")["date"].nunique())
            counts = {m: int(raw.get(m, 0)) for m in have}
            if len(set(counts.values())) > 1:
                print(f"\n  {pair} h={h}: models were scored on DIFFERENT samples "
                      f"{counts} -- testing the {len(probe)} origins they share")
                misaligned.append((pair, h, counts, len(probe)))
            else:
                print(f"\n  {pair} h={h}: {len(probe)} shared origins, "
                      f"{len(have)} models {have}")
            for loss in LOSS_COLS:
                panel = aligned_panel(df, pair, h, loss)
                d, m = run_cell(panel, pair, h, loss,
                                args.alpha, args.n_boot, args.seed)
                dm_all.extend(d)
                mcs_all.extend(m)
                survivors = [r["model"] for r in m if r["in_mcs"]]
                print(f"      {LOSS_LABEL[loss]:<6} MCS({args.alpha:.2f}) = "
                      f"{', '.join(survivors) if survivors else '(empty)'}")

    if skipped:
        print("\n  skipped cells (fewer than 2 models or too few shared origins):")
        for pair, h, nm, no in skipped:
            print(f"    {pair} h={h}: {nm} models, {no} shared origins")

    if misaligned:
        print(f"\n  ! {len(misaligned)} cell(s) had models scored on different "
              f"samples; each was tested on the intersection. Expected 0 -- see "
              f"data_provider/data_loader.py:TEST_ORIGIN_ALIGN")
    else:
        print("\n  every model was scored on the same origins in every cell")

    if not dm_all:
        raise SystemExit("\nnothing to test -- no cell had two aligned models")

    os.makedirs(args.out_dir, exist_ok=True)
    dm_df = pd.DataFrame(dm_all)
    mcs_df = pd.DataFrame(mcs_all)
    dm_path = os.path.join(args.out_dir, "dm_tests.csv")
    mcs_path = os.path.join(args.out_dir, "mcs_results.csv")
    dm_df.to_csv(dm_path, index=False)
    mcs_df.to_csv(mcs_path, index=False)

    print("\n" + "=" * 78)
    print("  MCS membership rate  (share of pair x horizon cells kept)")
    print("=" * 78)
    rate = (mcs_df.groupby(["loss", "model"])["in_mcs"].mean().unstack("loss") * 100)
    print(rate.round(0).to_string())

    n_cells = len(dm_df[["pair", "horizon"]].drop_duplicates())
    print("\n" + "=" * 78)
    print(f"  Diebold-Mariano: significant at 5% in how many of the "
          f"{n_cells} (pair, horizon) cells")
    print("=" * 78)
    sig = (dm_df.groupby(["loss", "model_a", "model_b"])["significant_5pct"]
           .agg(n_significant="sum", n_cells="count"))
    print(sig.to_string())

    print(f"\nwrote:\n  {dm_path}\n  {mcs_path}")


if __name__ == "__main__":
    main()
