"""
Multi-horizon target construction for the realized-volatility benchmark.

For horizon h the dependent variable is the log of the realized variance
AVERAGED over the forecast window:

    Y_t^(h) = ln( (1/h) * Sum_{k=1}^{h} RV_{t+k} )

The series on disk is already ln(RV), so this is a log-sum-exp over the
window, less ln(h):

    Y_t^(h) = ln( Sum_{k=1}^{h} exp( ln RV_{t+k} ) ) - ln(h)

This replaces the earlier forward mean of logs, (1/h) * Sum_{k=1}^{h} ln RV_{t+k}.
The two are genuinely different quantities -- by Jensen's inequality the mean
of logs sits below the log of the mean, and the gap widens with the dispersion
of RV inside the window, so quiet and turbulent weeks are re-weighted. That
Jensen gap IS the change; averaging rather than summing the variance only
removes the constant ln(h) on top of it. For h = 1 every one of these
definitions collapses to ln(RV_{t+1}), so h = 1 results are unaffected.

Averaging rather than summing keeps the target on the same scale as the input
series, which matters in two places:

  * the deep models de-normalise through RevIN using the look-back window's
    own mean and standard deviation, so a target centred near that mean
    leaves the head a small constant to learn rather than ln(h)/sigma;
  * the numbers stay directly comparable with the previous mean-of-logs
    results and with the h-day-average convention of Corsi (2009) and
    Bollerslev, Patton & Quaedvlieg (2016).

For the linear models the choice is cosmetic: ln(Sum RV) and ln(mean RV)
differ by a constant, an OLS intercept absorbs it exactly, N-HAR's LASSO
residualises the target against an intercept-carrying block before
penalising, and QLIKE (Patton, 2011) depends on the ratio
RV_act / RV_pred only. All three therefore score identically either way.

MSE and MAE remain on the ln-RV scale and stay comparable across models
because every model in the benchmark is scored against this same Y_t^(h).

Used by the four benchmark models: HAR-RV (HAR_RV_run.py), N-HAR
(HAR_X_run.py), and ModernTCN / FiLM-TCN, which reach it through
--aggregate_horizon and torch.logsumexp in exp/exp_ModernTCN.py. The retired
LSTM and HAR-residual hybrid paths were deliberately left on the old
forward-mean-of-logs target, so their h > 1 numbers do not line up with the
benchmark table.
"""

import numpy as np
import pandas as pd


def forward_log_mean_rv(ln_rv: pd.Series, h: int) -> pd.Series:
    """ln of the RV averaged over the FUTURE window [t+1 .. t+h].

        Y_t^(h) = ln( (1/h) * Sum_{k=1}^{h} exp( ln RV_{t+k} ) )

    rolling(h).mean() gives the trailing mean over [t-h+1 .. t]; the final
    shift(-h) slides that window forward to [t+1 .. t+h], so row t only ever
    uses observations strictly after t and there is no look-ahead.

    The exponentials are taken relative to the series maximum so exp() cannot
    overflow; the shift is added back on the log scale, leaving the result
    mathematically unchanged.

    Parameters
    ----------
    ln_rv : pd.Series
        Log realized variance, indexed in trading-day order.
    h : int
        Forecast horizon in trading days.

    Returns
    -------
    pd.Series
        Y^(h), aligned to ln_rv's index; the last h rows are NaN.
    """
    s = pd.Series(ln_rv, dtype=float)
    c = s.max()
    if not np.isfinite(c):
        c = 0.0
    rv = np.exp(s - c)
    return np.log(rv.rolling(h).mean()).shift(-h) + c
