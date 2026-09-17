"""
Equal-predictive-ability tests for the realized-volatility benchmark.

Two tests, both consuming per-observation losses (not summary metrics), so
every model must be scored on an IDENTICAL sample of forecast origins --
see dm_mcs_run.py, which does the aligning.

Diebold & Mariano (1995), Harvey, Leybourne & Newbold (1997)
------------------------------------------------------------
Pairwise. Tests H0: E[L_a - L_b] = 0 against a two-sided alternative. The
loss differential of an h-step forecast is MA(h-1) under H0, so its long-run
variance is estimated with a Newey-West Bartlett kernel at lag h-1 and the
statistic is compared with a t distribution on n-1 degrees of freedom after
the HLN small-sample correction. For h = 1 this reduces to the plain DM test
with a heteroskedasticity-robust variance.

Hansen, Lunde & Nason (2011)
----------------------------
The Model Confidence Set: the subset of models that contains the best one
with probability at least 1 - alpha. Implemented with the T_max statistic and
a stationary bootstrap (Politis & Romano, 1994), which preserves the serial
dependence that overlapping h-day targets induce. Models are eliminated one
at a time; each model's MCS p-value is the running maximum of the elimination
p-values, so p >= alpha means "kept in the set".

A model surviving the MCS is NOT evidence that it is best -- only that the
sample cannot rule it out. With a few hundred test days and overlapping
targets, expect wide sets.
"""

import numpy as np
import pandas as pd
from scipy import stats


# ==============================================================================
# 1.  LONG-RUN VARIANCE
# ==============================================================================

def newey_west_var(x, lag):
    """Newey-West (1987) long-run variance of the MEAN of x, Bartlett kernel.

    Returns Var(mean(x)) = (1/n) * [gamma_0 + 2 * sum_j w_j gamma_j], the
    quantity a t statistic on mean(x) divides by.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 2:
        return np.nan
    d = x - x.mean()
    gamma0 = float(d @ d) / n
    total = gamma0
    for j in range(1, int(lag) + 1):
        if j >= n:
            break
        w = 1.0 - j / (lag + 1.0)
        gamma_j = float(d[j:] @ d[:-j]) / n
        total += 2.0 * w * gamma_j
    # a negative estimate is possible in small samples; fall back to gamma_0
    if not np.isfinite(total) or total <= 0:
        total = gamma0
    return total / n


# ==============================================================================
# 2.  DIEBOLD-MARIANO
# ==============================================================================

def dm_test(loss_a, loss_b, h=1, hln=True):
    """Two-sided Diebold-Mariano test on two aligned per-observation losses.

    Parameters
    ----------
    loss_a, loss_b : array-like
        Per-observation losses of model A and model B, in the same order and
        for the same forecast origins.
    h : int
        Forecast horizon in trading days; sets the HAC truncation lag to h-1.
    hln : bool
        Apply the Harvey-Leybourne-Newbold small-sample correction and use a
        t(n-1) reference distribution. Recommended, and the default.

    Returns
    -------
    dict with keys: stat, p_value, mean_diff, n. mean_diff < 0 means A has
    the lower loss (A is better).
    """
    a = np.asarray(loss_a, dtype=float)
    b = np.asarray(loss_b, dtype=float)
    if a.shape != b.shape:
        raise ValueError(f'loss arrays differ in length: {a.shape} vs {b.shape}')

    d = a - b
    d = d[np.isfinite(d)]
    n = d.size
    out = {'stat': np.nan, 'p_value': np.nan,
           'mean_diff': float(d.mean()) if n else np.nan, 'n': int(n)}
    if n < 3:
        return out

    # identical forecasts (e.g. HAR-RV vs N-HAR's own HAR reference row) give
    # an exactly zero differential: no evidence of a difference, not an error
    scale = max(np.abs(a).mean(), np.abs(b).mean(), 1e-300)
    if np.allclose(d, 0.0, atol=1e-12 * scale):
        out['stat'], out['p_value'], out['mean_diff'] = 0.0, 1.0, 0.0
        return out

    var_mean = newey_west_var(d, lag=max(int(h) - 1, 0))
    if not np.isfinite(var_mean) or var_mean <= 0:
        return out

    stat = d.mean() / np.sqrt(var_mean)

    if hln:
        # Harvey, Leybourne & Newbold (1997) eq. 9
        corr = (n + 1 - 2 * h + h * (h - 1) / n) / n
        stat *= np.sqrt(max(corr, 0.0)) if corr > 0 else 1.0
        p = 2.0 * stats.t.sf(abs(stat), df=n - 1)
    else:
        p = 2.0 * stats.norm.sf(abs(stat))

    out['stat'] = float(stat)
    out['p_value'] = float(p)
    return out


# ==============================================================================
# 3.  MODEL CONFIDENCE SET
# ==============================================================================

def _stationary_bootstrap_indices(n, block_len, n_boot, rng):
    """Politis & Romano (1994) stationary bootstrap index matrix (n_boot, n)."""
    p = 1.0 / max(block_len, 1)
    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, size=n_boot)
    for t in range(1, n):
        cont = rng.random(n_boot) >= p          # continue the current block
        nxt = (idx[:, t - 1] + 1) % n
        idx[:, t] = np.where(cont, nxt, rng.integers(0, n, size=n_boot))
    return idx


def mcs(losses, alpha=0.10, n_boot=2000, block_len=None, h=1, seed=2021):
    """Hansen-Lunde-Nason Model Confidence Set, T_max variant.

    Parameters
    ----------
    losses : pd.DataFrame
        Per-observation losses, one COLUMN per model, one ROW per forecast
        origin. Rows must already be aligned across models.
    alpha : float
        The MCS is {model : mcs_p >= alpha}.
    n_boot : int
        Stationary-bootstrap replications.
    block_len : int or None
        Expected block length. Defaults to max(h, 2), so overlapping h-day
        targets stay inside a block.
    h : int
        Forecast horizon, used only for the default block length.
    seed : int
        Bootstrap seed, so the set is reproducible.

    Returns
    -------
    pd.DataFrame indexed by model with columns:
        mean_loss     -- sample mean loss
        mcs_p         -- MCS p-value (running max of elimination p-values)
        in_mcs        -- mcs_p >= alpha
        rank          -- 1 = lowest mean loss
        eliminated_at -- elimination order, NaN for survivors
    """
    L = pd.DataFrame(losses).dropna()
    models = list(L.columns)
    n, m = L.shape
    if m < 2:
        raise ValueError('MCS needs at least two models')

    if block_len is None:
        block_len = max(int(h), 2)

    rng = np.random.default_rng(seed)
    idx = _stationary_bootstrap_indices(n, block_len, n_boot, rng)

    Lv = L.to_numpy(dtype=float)                       # (n, m)
    # bootstrap means for every model: (n_boot, m)
    boot_means = Lv[idx].mean(axis=1)
    means = Lv.mean(axis=0)                            # (m,)

    alive = list(range(m))
    mcs_p = {}
    order = {}
    step = 0

    while len(alive) > 1:
        sub = np.array(alive)
        mu = means[sub]                                # (k,)
        bm = boot_means[:, sub]                        # (n_boot, k)
        k = sub.size

        # pairwise mean differences and their bootstrap variance
        dij = mu[:, None] - mu[None, :]                # (k, k)
        bdij = bm[:, :, None] - bm[:, None, :]         # (n_boot, k, k)
        centred = bdij - dij[None, :, :]
        var_ij = (centred ** 2).mean(axis=0)           # (k, k)
        np.fill_diagonal(var_ij, np.inf)               # t_ii := 0
        var_ij = np.where(var_ij <= 0, np.inf, var_ij)

        t_ij = dij / np.sqrt(var_ij)
        t_boot = centred / np.sqrt(var_ij)[None, :, :]

        # T_max: the worst model's largest standardised excess loss
        t_i = t_ij.max(axis=1)                         # (k,)
        t_boot_i = t_boot.max(axis=2)                  # (n_boot, k)
        T = t_i.max()
        T_boot = t_boot_i.max(axis=1)                  # (n_boot,)

        p = float((T_boot >= T).mean())
        step += 1
        prev = max(mcs_p.values()) if mcs_p else 0.0
        p_running = max(p, prev)                       # HLN monotonicity

        worst_local = int(np.argmax(t_i))
        worst = int(sub[worst_local])
        mcs_p[worst] = p_running
        order[worst] = step
        alive.remove(worst)

    # the survivor is in the set by construction
    last = alive[0]
    mcs_p[last] = 1.0
    order[last] = np.nan

    res = pd.DataFrame({
        'mean_loss': means,
        'mcs_p': [mcs_p[i] for i in range(m)],
        'eliminated_at': [order[i] for i in range(m)],
    }, index=models)
    res['in_mcs'] = res['mcs_p'] >= alpha
    res['rank'] = res['mean_loss'].rank(method='min').astype(int)
    return res[['mean_loss', 'rank', 'mcs_p', 'in_mcs', 'eliminated_at']]
