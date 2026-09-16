"""
==============================================================================
HAR-X / N-HAR: Scheduled Macroeconomic News in Multi-Horizon RV Forecasting

Event-aware linear baselines for the FiLM-TCN comparison. Implements the
specification of

    Plihal, T. Scheduled Macroeconomic News Announcements and Forex
    Volatility Forecasting.

adapted to this repository's split, horizons and per-pair event calendars.

Models estimated (nested, in increasing order)
----------------------------------------------
    HAR         Y = b0 + b_d*RV_d + b_w*RV_w + b_m*RV_m
                Corsi (2009). Reference row; identical to HAR_RV_run.py.

    HAR+DOW     HAR + g1*(MON_{t+1} x RV_d) + ... + g4*(FRI_{t+1} x RV_d)
                Plihal Eq. 2. Weekday dummies for the FIRST forecast day,
                INTERACTED with lagged daily RV (not additive) so the
                seasonal effect scales with the volatility level. Wednesday
                is omitted to avoid the dummy trap.
                This is the CONTROL: it is what stops "macro news helps"
                from being a restatement of "Friday is busy" (NFP is always
                a Friday, CPI usually mid-week).

    HAR-X-agg   HAR+DOW + pooled release COUNTS over the forecast window
                (daily total + the non-USD side's count). 2 extra regressors
                on this branch, OLS, no regularisation needed.

    N-HAR       HAR+DOW + ALL evt_* release-type dummies over the forecast
                window, estimated by LASSO with blocked cross-validation.
                Plihal's headline model (his Section 4.2 / Table 3).

The event regressor
-------------------
For release type j and horizon h, the regressor is the horizon mean

    N_j,t^(h) = (1/h) * Sum_{k=1..h} D_j,t+k ,   D_j,s = 1 if j is scheduled on s

which for h=1 is just D_j,t+1. This is KNOWN at time t because the releases
are scheduled, which is the entire reason the design works out-of-sample --
and it is deliberately the same quantity the FiLM head consumes, where
`self.event_embed(event_y).mean(dim=1)` (models/ModernTCN.py:391) mean-pools
the horizon's calendar. Matching it here is what makes FiLM-TCN vs N-HAR an
architecture comparison rather than an information-set comparison.

Target and split (mirrors HAR_RV_run.py exactly, so rows are comparable)
-----------------------------------------------------------------------
    Y_t^(h) = (1/h) * Sum_{k=1..h} ln(RV_{t+k})
    train: year <= 2023   (val folded in)      test: year >= 2024

All four models at a given (pair, horizon) are estimated and scored on an
IDENTICAL row sample, so the loss differences are attributable to the
specification and the per-observation losses can be fed to an MCS / DM test.

Deviations from Plihal, and why
-------------------------------
  * Fixed chronological split instead of his rolling 1000-day window
    re-estimated daily. His protocol cannot be applied to the deep models
    this table is meant to compare against, and an asymmetric protocol would
    invalidate the comparison. We take his SPECIFICATION, not his window
    scheme.
  * No continuous/jump (CJ) decomposition. It needs MRV/MRQ from 5-minute
    returns, which this repository does not carry. His pure N-HAR (no CJ)
    is the model reproduced here.
  * No BMA. It is erratic in his own Table 3 (+204% MSE on USD/JPY CC).

Metrics: MSE, MAE on the ln-RV scale; QLIKE (Patton, 2011) computed on the
variance scale after exponentiation -- identical to utils/metrics.py and
HAR_RV_run.py:292, so rows are comparable across the whole model table.

Usage
-----
    python HAR_X_run.py                       # all 5 pairs, h = 1, 5, 22
    python HAR_X_run.py --pairs EURUSD GBPUSD
    python HAR_X_run.py --horizons 1
==============================================================================
"""

# -- Standard Library ----------------------------------------------------------
import argparse
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# -- Third-party ---------------------------------------------------------------
import numpy as np
import pandas as pd

import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from sklearn.linear_model import lasso_path

# -- Local ---------------------------------------------------------------------
from data_provider.event_preprocessing import (
    DEFAULT_MIN_DAYS, DEFAULT_ON_NONTRADING,
    load_event_features, resolve_event_path, resolve_target_column)


# ==============================================================================
# 0.  CONFIGURATION
# ==============================================================================

TRAIN_END_YEAR  = 2023
TEST_START_YEAR = 2024

# Forecast horizons and their Newey-West bandwidths: L = 2*(h-1)
HORIZONS = {1: 0, 5: 8, 22: 42}

LAG_W = 5     # weekly HAR component window
LAG_M = 22    # monthly HAR component window

DEFAULT_PAIRS = ["AUDUSD", "EURUSD", "GBPUSD", "USDCHF", "USDJPY"]

# Plihal p. 12: news types whose dummies are correlated above this are merged
# and represented by a single dummy. Without this, LASSO's arbitrary choice
# among collinear predictors makes the selection table unreproducible.
DEDUP_CORR = 0.90

N_CV_BLOCKS = 10    # Plihal p. 18 (Bergmeir & Benitez): blocked, not random
N_LAMBDA    = 60

# Lambda selection rule.
#   'min'  the CV minimum. This is the faithful reading of Plihal, who selects
#          "the best model according to 10-block cross-validation that minimises
#          the MSE loss function" (p. 29). It is the DEFAULT.
#   '1se'  the largest lambda whose CV error is within one standard error of the
#          minimum (Hastie/Tibshirani/Friedman; glmnet's `lambda.1se`).
#
# Run both. With overlapping targets the per-fold CV curve is noisy, and the two
# rules disagree in a way that is itself informative: '1se' is the robustness
# check that tells you whether a gain under 'min' is signal or a lambda artifact.
# On this data 'min' is right at h=1 and h=5, where '1se' over-shrinks to the
# empty model and discards a real 6-12% MSE gain; the one place 'min' misfires
# is GBP/USD at h=22, where it selects 12 dummies and LOSES 20.6% while '1se'
# correctly collapses to HAR+DOW. See the horizon note in the module docstring.
LAMBDA_RULE = "min"

SEP  = "=" * 78
THIN = "-" * 78


# ==============================================================================
# 1.  LOSS FUNCTIONS  (identical to HAR_RV_run.py / utils/metrics.py)
# ==============================================================================

def mse(actual, predicted):
    return float(np.mean((actual - predicted) ** 2))


def mae(actual, predicted):
    return float(np.mean(np.abs(actual - predicted)))


def qlike(actual_ln, predicted_ln):
    """QLIKE (Patton, 2011). Inputs are log-variance; exponentiated internally."""
    rv_act  = np.exp(actual_ln)
    rv_pred = np.exp(predicted_ln)
    valid   = (rv_act > 0) & (rv_pred > 0)
    ratio   = rv_act[valid] / rv_pred[valid]
    return float(np.mean(ratio - np.log(ratio) - 1))


def qlike_per_obs(actual_ln, predicted_ln):
    """Per-observation QLIKE, for the MCS / DM tests downstream."""
    ratio = np.exp(actual_ln) / np.exp(predicted_ln)
    return ratio - np.log(ratio) - 1


def compute_metrics(actual, predicted):
    return {"MSE": mse(actual, predicted),
            "MAE": mae(actual, predicted),
            "QLIKE": qlike(actual, predicted)}


# ==============================================================================
# 2.  DATA LOADING
# ==============================================================================

def load_series(root_path, data_path, target):
    """Load the ln(RV) series, tolerating the per-file date and column drift.

    EURUSD_lnRV.csv dates are M/D/Y and its column is 'ln_RV'; the other four
    are ISO dates with 'lnRV'. resolve_target_column handles the column, and
    format='mixed' handles the dates (dayfirst=False -- '1/12/2012' is the
    12th of January, matching AUDUSD's 2012-01-12 start).
    """
    df = pd.read_csv(os.path.join(root_path, data_path))
    col = resolve_target_column(df.columns, target)
    df = df.dropna(subset=["date", col]).copy()
    df["date"] = pd.to_datetime(df["date"], format="mixed", dayfirst=False)
    df = df.sort_values("date").drop_duplicates(subset="date")
    out = pd.DataFrame({"ln_RV": df[col].to_numpy(dtype=float)},
                       index=pd.DatetimeIndex(df["date"]))
    out.index.name = "date"
    return out


def build_har_core(df):
    """The three Corsi (2009) components. All use information available AT t."""
    df = df.copy()
    df["RV_d"] = df["ln_RV"]
    df["RV_w"] = df["ln_RV"].rolling(LAG_W).mean()
    df["RV_m"] = df["ln_RV"].rolling(LAG_M).mean()
    return df


def forward_mean(frame, h):
    """Mean over rows [t+1 .. t+h], in trading-day space.

    rolling(h).mean() is the trailing mean over [t-h+1 .. t]; shift(-h) slides
    that window forward to [t+1 .. t+h]. Same construction as the target in
    HAR_RV_run.py:205, so regressors and target span the same window.
    """
    return frame.rolling(h).mean().shift(-h)


def build_dow(index):
    """Weekday dummies for the FIRST forecast day (the next TRADING day).

    Using the next trading day rather than the next calendar day keeps the
    dummy aligned with where the target window actually starts, which matters
    across holidays and the gaps present in these series.
    """
    next_dow = pd.Series(index, index=index).shift(-1).dt.dayofweek
    return pd.DataFrame(
        {"MON": (next_dow == 0).astype(float),
         "TUE": (next_dow == 1).astype(float),
         "THU": (next_dow == 3).astype(float),
         "FRI": (next_dow == 4).astype(float)},
        index=index)   # Wednesday omitted: dummy trap


# ==============================================================================
# 3.  EVENT REGRESSOR CONSTRUCTION
# ==============================================================================

def select_agg_columns(event_cols):
    """Pooled count regressors for HAR-X-agg, chosen to avoid exact collinearity.

    With the calendar's Impact column dropped, the impact decomposition
    (n_events_high/medium/low) and the impact-weighted event_score no longer
    exist. What survives is the daily total and the per-currency split, and
    those form one partition:

        n_events = sum over the pair's currencies (e.g. eur + usd)

    so they cannot all enter. We keep the total plus the non-USD side; the USD
    count is then implied. That is 2 regressors here against 5 on the
    impact-aware branch, and the difference is most of why HAR-X-agg is weaker.
    'event_coverage' is a data-availability flag, not news, and is excluded.
    """
    cand = ["n_events"]
    cand += sorted(c for c in event_cols
                   if c.startswith("n_events_") and not c.startswith("n_events_usd"))
    return [c for c in cand if c in event_cols]


def drop_rank_deficient(X, cols, tol=1e-8):
    """Greedily keep the largest linearly independent subset of columns.

    A defensive pass: the partitions above are checked analytically, but the
    per-currency column set is generated from whatever currencies appear in
    each pair's calendar, so the exact redundancies differ by pair.
    """
    keep, kept_idx = [], []
    for j, c in enumerate(cols):
        trial = kept_idx + [j]
        M = X[:, trial]
        M = M - M.mean(axis=0, keepdims=True)
        s = np.linalg.svd(M, compute_uv=False)
        if s[-1] > tol * max(s[0], 1.0):
            keep.append(c)
            kept_idx.append(j)
    return keep, kept_idx


def dedup_dummies(daily, cols, thresh=DEDUP_CORR):
    """Merge release types whose DAILY dummies correlate above `thresh`.

    Plihal p. 12. Grouping is done on the raw daily dummies, not the horizon
    means -- the latter are mechanically more correlated as h grows and would
    over-merge. Groups are connected components of the thresholded correlation
    graph; the representative is the most frequently scheduled member.

    Returns (representatives, {representative: [members]}).
    """
    sub = daily[cols]
    keep = [c for c in cols if sub[c].std() > 0]
    if not keep:
        return [], {}
    C = np.corrcoef(sub[keep].to_numpy(dtype=float), rowvar=False)
    C = np.nan_to_num(C, nan=0.0)

    n = len(keep)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(i + 1, n):
            if abs(C[i, j]) >= thresh:
                union(i, j)

    groups = {}
    for i, c in enumerate(keep):
        groups.setdefault(find(i), []).append(c)

    freq = sub[keep].sum(axis=0)
    reps, members = [], {}
    for g in groups.values():
        rep = max(g, key=lambda c: (freq[c], c))
        reps.append(rep)
        members[rep] = sorted(g)
    reps.sort()
    return reps, members


# ==============================================================================
# 4.  DESIGN MATRIX ASSEMBLY
# ==============================================================================

def assemble(series, events, h, agg_cols, evt_cols):
    """One frame per horizon holding the target and every candidate regressor.

    Every model at this horizon is fitted on the rows that survive here, so
    all four share an identical sample and their per-observation losses line
    up for the MCS / DM tests.
    """
    base = build_har_core(series)
    base["Y_h"] = forward_mean(base["ln_RV"], h)

    dow = build_dow(base.index)
    for c in dow.columns:
        # interacted with lagged daily RV, not additive (Plihal Eq. 2)
        base[f"DOW_{c}"] = dow[c] * base["RV_d"]

    fwd = forward_mean(events[agg_cols + evt_cols], h)
    fwd.columns = [f"EV_{c}" for c in fwd.columns]
    out = pd.concat([base, fwd], axis=1)

    need = ["Y_h", "RV_d", "RV_w", "RV_m"] + list(fwd.columns)
    return out.dropna(subset=need)


def split_by_year(df):
    train = df[df.index.year <= TRAIN_END_YEAR]
    test  = df[df.index.year >= TEST_START_YEAR]
    if len(train) == 0 or len(test) == 0:
        raise ValueError(f"empty split: train={len(train)} test={len(test)}")
    return train, test


# ==============================================================================
# 5.  OLS ESTIMATION
# ==============================================================================

def fit_ols(train, test, cols, h):
    """OLS with Newey-West HAC standard errors, bandwidth L = 2*(h-1)."""
    nw = HORIZONS[h]
    X_tr = sm.add_constant(train[cols], has_constant="add")
    X_te = sm.add_constant(test[cols],  has_constant="add")
    res = OLS(train["Y_h"], X_tr).fit(
        cov_type="HAC", cov_kwds={"maxlags": max(nw, 1), "use_correction": True})
    return res, res.predict(X_te).to_numpy(dtype=float)


# ==============================================================================
# 6.  LASSO WITH BLOCKED CROSS-VALIDATION  (N-HAR)
# ==============================================================================
#
# Three points that are not in the paper but decide whether this works:
#
#   1. The HAR core and the weekday controls are left UNPENALISED. They are
#      the model, not the hypothesis under test; shrinking b_d/b_w/b_m towards
#      zero would degrade the baseline and flatter the news dummies. This is
#      handled exactly by Frisch-Waugh-Lovell: for the problem
#          min_{b,c} ||y - Zb - Xc||^2 + lambda*||c||_1
#      the minimiser in c solves the same LASSO on Z-residualised (y, X), and
#      b is recovered by OLS afterwards.
#
#   2. The penalised columns are STANDARDISED, so one L1 budget is not spent
#      unevenly across releases of differing frequency.
#
#   3. CV folds are contiguous BLOCKS, and observations within h rows of a
#      held-out block are PURGED from that fold's training part. At h=5 and
#      h=22 the targets overlap, so an unpurged split leaks the validation
#      window into training through the overlap and picks too small a lambda.
# ==============================================================================

def _residualise(Z, other):
    """Return M_Z @ other, the part of `other` orthogonal to the columns of Z."""
    coef, *_ = np.linalg.lstsq(Z, other, rcond=None)
    return other - Z @ coef


def _fit_given_alpha(Z, X, y, alpha):
    """Fit the unpenalised/penalised split at one alpha; return (b, c)."""
    yr = _residualise(Z, y.reshape(-1, 1)).ravel()
    Xr = _residualise(Z, X)
    _, coefs, _ = lasso_path(Xr, yr, alphas=[alpha])
    c = coefs[:, 0]
    b, *_ = np.linalg.lstsq(Z, y - X @ c, rcond=None)
    return b, c


def blocked_cv_lasso(Z_tr, X_tr, y_tr, h, n_blocks=N_CV_BLOCKS, n_lambda=N_LAMBDA,
                     rule=LAMBDA_RULE):
    """Choose lambda by blocked, purged CV. Returns (alpha, cv_mse, folds)."""
    n = len(y_tr)

    # lambda grid from the full-sample residualised problem
    yr = _residualise(Z_tr, y_tr.reshape(-1, 1)).ravel()
    Xr = _residualise(Z_tr, X_tr)
    a_max = float(np.max(np.abs(Xr.T @ yr))) / n
    if not np.isfinite(a_max) or a_max <= 0:
        a_max = 1.0
    alphas = np.logspace(np.log10(a_max), np.log10(a_max * 1e-4), n_lambda)

    bounds = np.linspace(0, n, n_blocks + 1).astype(int)
    errs = np.full((n_blocks, n_lambda), np.nan)

    for k in range(n_blocks):
        lo, hi = bounds[k], bounds[k + 1]
        if hi - lo < 5:
            continue
        val = np.arange(lo, hi)
        # purge overlapping targets on both sides of the held-out block
        mask = np.ones(n, dtype=bool)
        mask[max(0, lo - h):min(n, hi + h)] = False
        tr = np.flatnonzero(mask)
        if len(tr) < X_tr.shape[1] + Z_tr.shape[1] + 10:
            continue

        Zk, Xk, yk = Z_tr[tr], X_tr[tr], y_tr[tr]
        yrk = _residualise(Zk, yk.reshape(-1, 1)).ravel()
        Xrk = _residualise(Zk, Xk)
        _, coefs, _ = lasso_path(Xrk, yrk, alphas=alphas)

        for m in range(n_lambda):
            c = coefs[:, m]
            b, *_ = np.linalg.lstsq(Zk, yk - Xk @ c, rcond=None)
            pred = Z_tr[val] @ b + X_tr[val] @ c
            errs[k, m] = np.mean((y_tr[val] - pred) ** 2)

    cv = np.nanmean(errs, axis=0)
    if np.all(np.isnan(cv)):
        return alphas[0], np.nan, 0
    best = int(np.nanargmin(cv))

    if rule == "1se":
        n_ok = np.sum(~np.isnan(errs), axis=0)
        se = np.nanstd(errs, axis=0) / np.sqrt(np.maximum(n_ok, 1))
        thresh = cv[best] + se[best]
        # alphas descend, so the first index within one SE is the largest
        # lambda (most shrinkage) that CV cannot distinguish from the minimum
        ok = np.flatnonzero(~np.isnan(cv) & (cv <= thresh))
        if len(ok):
            best = int(ok[0])

    n_folds = int(np.sum(~np.isnan(errs[:, best])))
    return float(alphas[best]), float(cv[best]), n_folds


def fit_nhar(train, test, z_cols, x_cols, h, rule=LAMBDA_RULE):
    """N-HAR: unpenalised HAR+DOW core, LASSO over the release-type dummies."""
    Z_tr = sm.add_constant(train[z_cols], has_constant="add").to_numpy(dtype=float)
    Z_te = sm.add_constant(test[z_cols],  has_constant="add").to_numpy(dtype=float)
    y_tr = train["Y_h"].to_numpy(dtype=float)

    Xr_tr = train[x_cols].to_numpy(dtype=float)
    Xr_te = test[x_cols].to_numpy(dtype=float)

    # standardise the penalised block on TRAIN statistics only
    mu = Xr_tr.mean(axis=0)
    sd = Xr_tr.std(axis=0)
    live = sd > 1e-12                      # constant on train -> unidentified
    mu, sd = mu[live], sd[live]
    X_tr = (Xr_tr[:, live] - mu) / sd
    X_te = (Xr_te[:, live] - mu) / sd
    live_cols = [c for c, k in zip(x_cols, live) if k]

    alpha, cv_mse, n_folds = blocked_cv_lasso(Z_tr, X_tr, y_tr, h, rule=rule)
    b, c = _fit_given_alpha(Z_tr, X_tr, y_tr, alpha)
    pred = Z_te @ b + X_te @ c

    # fold stability at the chosen alpha: an honest stand-in for Plihal's
    # rolling-window selection frequency, which a fixed split cannot produce
    n = len(y_tr)
    bounds = np.linspace(0, n, N_CV_BLOCKS + 1).astype(int)
    hits = np.zeros(len(live_cols))
    used = 0
    for k in range(N_CV_BLOCKS):
        lo, hi = bounds[k], bounds[k + 1]
        mask = np.ones(n, dtype=bool)
        mask[max(0, lo - h):min(n, hi + h)] = False
        tr = np.flatnonzero(mask)
        if len(tr) < X_tr.shape[1] + Z_tr.shape[1] + 10:
            continue
        _, ck = _fit_given_alpha(Z_tr[tr], X_tr[tr], y_tr[tr], alpha)
        hits += (np.abs(ck) > 1e-10)
        used += 1
    stability = hits / used if used else np.zeros(len(live_cols))

    info = {
        "alpha": alpha,
        "rule": rule,
        "cv_mse": cv_mse,
        "cv_folds": n_folds,
        "n_selected": int(np.sum(np.abs(c) > 1e-10)),
        "n_candidates": len(live_cols),
        "coef": dict(zip(live_cols, c)),
        "stability": dict(zip(live_cols, stability)),
        "core": dict(zip(["const"] + list(z_cols), b)),
    }
    return info, pred


# ==============================================================================
# 7.  PER-PAIR DRIVER
# ==============================================================================

def run_pair(pair, root_path, target, horizons, event_kwargs,
             rule=LAMBDA_RULE, verbose=True):
    data_path  = f"{pair}_lnRV.csv"
    event_path = resolve_event_path(root_path, data_path, None)

    series = load_series(root_path, data_path, target)
    events = load_event_features(root_path, event_path, series.index,
                                 verbose=False, **event_kwargs)
    events = events.set_index(pd.DatetimeIndex(events["date"])).drop(columns="date")
    events.index.name = "date"

    all_cols = list(events.columns)
    evt_all  = [c for c in all_cols if c.startswith("evt_")]
    agg_cols = select_agg_columns(all_cols)

    # dedup on TRAIN rows only -- the merge map must not see the test window
    train_mask = events.index.year <= TRAIN_END_YEAR
    evt_reps, evt_groups = dedup_dummies(events.loc[train_mask], evt_all)

    if verbose:
        print(f"\n{SEP}\n{pair}\n{SEP}")
        print(f"  series      : {len(series)} obs, "
              f"{series.index[0].date()} .. {series.index[-1].date()}")
        print(f"  calendar    : {event_path}")
        print(f"  evt_ dummies: {len(evt_all)} raw -> {len(evt_reps)} after "
              f"merging at |corr| >= {DEDUP_CORR}")
        print(f"  agg counts  : {agg_cols}")

    rows, sel_rows, loss_rows = [], [], []

    for h in horizons:
        df = assemble(series, events, h, agg_cols, evt_reps)
        train, test = split_by_year(df)

        har_cols = ["RV_d", "RV_w", "RV_m"]
        dow_cols = ["DOW_MON", "DOW_TUE", "DOW_THU", "DOW_FRI"]
        agg_ev   = [f"EV_{c}" for c in agg_cols]
        evt_ev   = [f"EV_{c}" for c in evt_reps]

        # defensive rank check on the pooled-count block
        agg_keep, _ = drop_rank_deficient(
            train[har_cols + dow_cols + agg_ev].to_numpy(dtype=float),
            har_cols + dow_cols + agg_ev)
        agg_keep = [c for c in agg_keep if c in agg_ev]

        y_te = test["Y_h"].to_numpy(dtype=float)
        preds, extra = {}, {}

        _, preds["HAR"]     = fit_ols(train, test, har_cols, h)
        _, preds["HAR+DOW"] = fit_ols(train, test, har_cols + dow_cols, h)
        _, preds["HAR-X-agg"] = fit_ols(
            train, test, har_cols + dow_cols + agg_keep, h)

        info, preds["N-HAR"] = fit_nhar(
            train, test, har_cols + dow_cols, evt_ev, h, rule=rule)
        extra["N-HAR"] = info

        if verbose:
            print(f"\n  h = {h:<3} train={len(train):>5}  test={len(test):>5}  "
                  f"candidates={info['n_candidates']:>3}  "
                  f"selected={info['n_selected']:>3}  "
                  f"alpha={info['alpha']:.5f}({rule})  cv_folds={info['cv_folds']}")
            print(f"    {'model':<12}{'MSE':>12}{'MAE':>12}{'QLIKE':>12}"
                  f"{'dMSE% vs HAR+DOW':>20}")

        base_mse = mse(y_te, preds["HAR+DOW"])
        for name in ["HAR", "HAR+DOW", "HAR-X-agg", "N-HAR"]:
            m = compute_metrics(y_te, preds[name])
            imp = 100.0 * (m["MSE"] - base_mse) / base_mse
            rows.append({"pair": pair, "horizon": h, "model": name,
                         "n_train": len(train), "n_test": len(test),
                         **m, "dMSE_pct_vs_HAR_DOW": imp,
                         "n_selected": extra.get(name, {}).get("n_selected", np.nan),
                         "alpha": extra.get(name, {}).get("alpha", np.nan)})
            if verbose:
                print(f"    {name:<12}{m['MSE']:>12.6f}{m['MAE']:>12.6f}"
                      f"{m['QLIKE']:>12.6f}{imp:>19.2f}%")

            # per-observation losses, for the MCS / DM stage
            loss_rows.append(pd.DataFrame({
                "pair": pair, "horizon": h, "model": name,
                "date": test.index,
                "se": (y_te - preds[name]) ** 2,
                "ae": np.abs(y_te - preds[name]),
                "qlike": qlike_per_obs(y_te, preds[name])}))

        for col, coef in info["coef"].items():
            if abs(coef) > 1e-10:
                name = col[len("EV_"):]
                sel_rows.append({
                    "pair": pair, "horizon": h, "regressor": name,
                    "coef_std": coef,
                    "fold_stability": info["stability"].get(col, np.nan),
                    "merged_with": "; ".join(
                        c for c in evt_groups.get(name, []) if c != name)})

    return rows, sel_rows, loss_rows


# ==============================================================================
# 8.  MAIN
# ==============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="HAR+DOW / HAR-X-agg / N-HAR event-aware linear baselines")
    ap.add_argument("--root_path", type=str, default="./data")
    ap.add_argument("--pairs", type=str, nargs="+", default=DEFAULT_PAIRS)
    ap.add_argument("--horizons", type=int, nargs="+", default=[1, 5, 22])
    ap.add_argument("--target", type=str, default="ln_RV")
    ap.add_argument("--output_dir", type=str, default="HAR-X results")
    ap.add_argument("--lambda_rule", type=str, default=LAMBDA_RULE,
                    choices=["1se", "min"],
                    help="LASSO lambda from blocked CV: 'min' takes the CV "
                         "minimum, '1se' the largest lambda within one standard "
                         "error of it (more shrinkage, far steadier at h=22)")
    ap.add_argument("--event_min_days", type=int, default=DEFAULT_MIN_DAYS)
    ap.add_argument("--event_on_nontrading", type=str,
                    default=DEFAULT_ON_NONTRADING, choices=["roll", "drop"])
    args = ap.parse_args()

    for h in args.horizons:
        if h not in HORIZONS:
            ap.error(f"horizon {h} has no Newey-West bandwidth configured; "
                     f"known horizons are {sorted(HORIZONS)}")

    event_kwargs = {"min_days": args.event_min_days,
                    "on_nontrading": args.event_on_nontrading}

    os.makedirs(args.output_dir, exist_ok=True)

    all_rows, all_sel, all_loss = [], [], []
    for pair in args.pairs:
        try:
            rows, sel, loss = run_pair(pair, args.root_path, args.target,
                                       args.horizons, event_kwargs,
                                       rule=args.lambda_rule)
        except FileNotFoundError as e:
            print(f"\n[skip] {pair}: {e}", file=sys.stderr)
            continue
        all_rows += rows
        all_sel  += sel
        all_loss += loss

    if not all_rows:
        print("no pairs ran", file=sys.stderr)
        return 1

    metrics = pd.DataFrame(all_rows)
    metrics.to_csv(os.path.join(args.output_dir, "har_x_metrics.csv"),
                   index=False)

    if all_sel:
        pd.DataFrame(all_sel).sort_values(
            ["pair", "horizon", "fold_stability"], ascending=[True, True, False]
        ).to_csv(os.path.join(args.output_dir, "nhar_selected.csv"), index=False)

    losses = pd.concat(all_loss, ignore_index=True)
    losses.to_csv(os.path.join(args.output_dir, "har_x_losses.csv"), index=False)

    # ---- summary table ------------------------------------------------------
    print(f"\n{SEP}\nSUMMARY -- mean across pairs ({len(args.pairs)} pairs)\n{SEP}")
    piv = (metrics.groupby(["horizon", "model"])[["MSE", "MAE", "QLIKE"]]
           .mean().round(4))
    print(piv.to_string())

    order = ["HAR", "HAR+DOW", "HAR-X-agg", "N-HAR"]
    lines = ["| Pair | h | " + " | ".join(f"{m} MSE" for m in order) + " |",
             "|---|---|" + "---|" * len(order)]
    for (pair, h), g in metrics.groupby(["pair", "horizon"], sort=False):
        by = g.set_index("model")["MSE"]
        lines.append(f"| {pair} | {h} | " +
                     " | ".join(f"{by.get(m, float('nan')):.4f}" for m in order) + " |")
    md = os.path.join(args.output_dir, "har_x_table.md")
    with open(md, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"\nwrote:\n  {os.path.join(args.output_dir, 'har_x_metrics.csv')}"
          f"\n  {os.path.join(args.output_dir, 'nhar_selected.csv')}"
          f"\n  {os.path.join(args.output_dir, 'har_x_losses.csv')}"
          f"\n  {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
