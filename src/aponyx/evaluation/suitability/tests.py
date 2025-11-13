"""
Statistical tests for signal-target relationships.

Provides correlation, regression, and temporal stability tests for
evaluating predictive associations.
"""

import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm

logger = logging.getLogger(__name__)


def compute_correlation(
    signal: pd.Series,
    target: pd.Series,
) -> float:
    """
    Compute Pearson correlation between signal and target.

    Parameters
    ----------
    signal : pd.Series
        Signal time series.
    target : pd.Series
        Target time series (must be aligned with signal).

    Returns
    -------
    float
        Pearson correlation coefficient (-1 to 1).

    Notes
    -----
    Returns 0.0 if either series has zero variance or contains NaN values.

    Examples
    --------
    >>> signal = pd.Series([1, 2, 3, 4, 5])
    >>> target = pd.Series([2, 4, 6, 8, 10])
    >>> compute_correlation(signal, target)
    1.0
    """
    if len(signal) == 0 or len(target) == 0:
        logger.warning("Empty series provided, returning correlation=0.0")
        return 0.0

    if signal.std() == 0 or target.std() == 0:
        logger.warning("Zero variance in series, returning correlation=0.0")
        return 0.0

    corr = signal.corr(target)
    if pd.isna(corr):
        logger.warning("NaN correlation (insufficient data), returning 0.0")
        return 0.0

    logger.debug("Computed correlation: %.4f", corr)
    return float(corr)


def compute_regression_stats(
    signal: pd.Series,
    target: pd.Series,
) -> dict[str, float]:
    """
    Compute OLS regression statistics for signal predicting target.

    Runs ordinary least squares regression: target ~ signal

    Parameters
    ----------
    signal : pd.Series
        Independent variable (predictor).
    target : pd.Series
        Dependent variable (response).

    Returns
    -------
    dict[str, float]
        Dictionary with keys:
        - 'beta': regression coefficient
        - 't_stat': t-statistic for beta
        - 'p_value': p-value for beta
        - 'r_squared': coefficient of determination

    Notes
    -----
    Uses statsmodels OLS with constant term (intercept).
    Returns zeros if regression fails due to insufficient data or numerical issues.

    Examples
    --------
    >>> signal = pd.Series([1, 2, 3, 4, 5])
    >>> target = pd.Series([2, 4, 6, 8, 10])
    >>> stats = compute_regression_stats(signal, target)
    >>> stats['beta']
    2.0
    """
    if len(signal) < 3 or len(target) < 3:
        logger.warning(
            "Insufficient observations for regression (n=%d), returning zeros",
            len(signal),
        )
        return {"beta": 0.0, "t_stat": 0.0, "p_value": 1.0, "r_squared": 0.0}

    try:
        # Add constant for intercept
        X = sm.add_constant(signal.values)
        y = target.values

        # Fit OLS model
        model = sm.OLS(y, X).fit()

        # Extract statistics for signal coefficient (index 1, after constant)
        beta = float(model.params[1])
        t_stat = float(model.tvalues[1])
        p_value = float(model.pvalues[1])
        r_squared = float(model.rsquared)

        logger.debug(
            "Regression: beta=%.4f, t=%.4f, p=%.4f, R²=%.4f",
            beta,
            t_stat,
            p_value,
            r_squared,
        )

        return {
            "beta": beta,
            "t_stat": t_stat,
            "p_value": p_value,
            "r_squared": r_squared,
        }

    except Exception as e:
        logger.warning("Regression failed: %s, returning zeros", e)
        return {"beta": 0.0, "t_stat": 0.0, "p_value": 1.0, "r_squared": 0.0}


def compute_rolling_betas(
    signal: pd.Series,
    target: pd.Series,
    window: int,
) -> pd.Series:
    """
    Compute rolling regression betas using sliding window.

    Parameters
    ----------
    signal : pd.Series
        Signal time series with DatetimeIndex.
    target : pd.Series
        Target time series with DatetimeIndex (aligned with signal).
    window : int
        Rolling window size in observations (e.g., 252 for ~1 year daily data).

    Returns
    -------
    pd.Series
        Time series of rolling beta coefficients.
        Index matches input series; first (window-1) values are NaN.

    Notes
    -----
    Uses OLS regression in each window: target ~ signal + constant.
    Minimum window size is 50 observations for reliable estimation.

    Implementation uses rolling window with apply to compute regression
    beta coefficient in each window.

    Examples
    --------
    >>> signal = pd.Series([...], index=date_range)
    >>> target = pd.Series([...], index=date_range)
    >>> rolling_betas = compute_rolling_betas(signal, target, window=252)
    >>> rolling_betas.mean()  # Average beta across all windows
    """
    if len(signal) < window:
        logger.warning(
            "Insufficient data for rolling window (n=%d < window=%d), returning empty series",
            len(signal),
            window,
        )
        return pd.Series([], dtype=float, index=signal.index[:0])

    # Preallocate result array
    betas = np.full(len(signal), np.nan)

    # Compute beta for each window
    for i in range(window - 1, len(signal)):
        window_signal = signal.iloc[i - window + 1 : i + 1]
        window_target = target.iloc[i - window + 1 : i + 1]

        if len(window_signal) < 3:
            continue

        try:
            X = sm.add_constant(window_signal.values)
            y = window_target.values
            model = sm.OLS(y, X).fit()
            betas[i] = float(model.params[1])
        except Exception:
            pass  # Keep as NaN

    rolling_betas = pd.Series(betas, index=signal.index, name=signal.name)

    logger.debug(
        "Computed %d rolling betas (window=%d, valid=%d)",
        len(rolling_betas),
        window,
        rolling_betas.notna().sum(),
    )

    return rolling_betas


def compute_stability_metrics(
    rolling_betas: pd.Series,
    aggregate_beta: float,
) -> dict[str, float]:
    """
    Compute stability metrics from rolling beta coefficients.

    Parameters
    ----------
    rolling_betas : pd.Series
        Time series of rolling beta coefficients from compute_rolling_betas().
    aggregate_beta : float
        Overall beta coefficient from full-sample regression.
        Used as reference for sign consistency check.

    Returns
    -------
    dict[str, float]
        Dictionary with keys:
        - 'sign_consistency_ratio': Proportion of windows matching aggregate sign
        - 'beta_cv': Coefficient of variation (std / |mean|)
        - 'n_windows': Number of valid rolling windows

    Notes
    -----
    Sign consistency ratio ≥ 0.8 indicates stable directional relationship.
    Beta CV < 0.5 indicates low magnitude variation (stable effect size).

    Windows with beta ≈ 0 (|beta| < 0.01) are excluded from sign consistency
    to avoid spurious sign flips in noise.

    Examples
    --------
    >>> rolling_betas = pd.Series([1.5, 1.8, 1.6, 1.7, 1.9])
    >>> aggregate_beta = 1.7
    >>> metrics = compute_stability_metrics(rolling_betas, aggregate_beta)
    >>> metrics['sign_consistency_ratio']
    1.0  # All same sign
    >>> metrics['beta_cv']
    0.08  # Low variation
    """
    # Remove NaN values
    valid_betas = rolling_betas.dropna()

    if len(valid_betas) == 0:
        logger.warning("No valid rolling betas, returning zero metrics")
        return {
            "sign_consistency_ratio": 0.0,
            "beta_cv": 0.0,
            "n_windows": 0,
        }

    # Sign consistency: proportion of windows with same sign as aggregate
    aggregate_sign = np.sign(aggregate_beta)

    # Filter out near-zero betas (|beta| < 0.01) to avoid noise
    non_zero_mask = np.abs(valid_betas) >= 0.01
    if non_zero_mask.sum() == 0:
        sign_consistency_ratio = 0.0
    else:
        same_sign = (np.sign(valid_betas[non_zero_mask]) == aggregate_sign).sum()
        sign_consistency_ratio = float(same_sign / non_zero_mask.sum())

    # Coefficient of variation: std / |mean|
    beta_mean = valid_betas.mean()
    beta_std = valid_betas.std()

    if abs(beta_mean) < 1e-10:
        beta_cv = 0.0
    else:
        beta_cv = float(beta_std / abs(beta_mean))

    logger.debug(
        "Stability metrics: sign_ratio=%.3f, CV=%.3f, n_windows=%d",
        sign_consistency_ratio,
        beta_cv,
        len(valid_betas),
    )

    return {
        "sign_consistency_ratio": sign_consistency_ratio,
        "beta_cv": beta_cv,
        "n_windows": len(valid_betas),
    }
