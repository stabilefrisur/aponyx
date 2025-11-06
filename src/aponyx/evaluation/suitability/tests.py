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


def compute_subperiod_betas(
    signal: pd.Series,
    target: pd.Series,
    n_splits: int = 2,
) -> list[float]:
    """
    Compute regression betas for temporal subperiods.

    Splits the sample chronologically and runs separate regressions in each
    subperiod to test temporal stability of the relationship.

    Parameters
    ----------
    signal : pd.Series
        Signal time series.
    target : pd.Series
        Target time series (must be aligned with signal).
    n_splits : int, default=2
        Number of chronological splits (must be >= 2).

    Returns
    -------
    list[float]
        List of beta coefficients, one per subperiod.

    Notes
    -----
    Useful for detecting regime changes or non-stationarity.
    Returns empty list if insufficient data for splitting.

    Examples
    --------
    >>> signal = pd.Series([1, 2, 3, 4, 5, 6])
    >>> target = pd.Series([2, 4, 6, 8, 10, 12])
    >>> betas = compute_subperiod_betas(signal, target, n_splits=2)
    >>> len(betas)
    2
    """
    if len(signal) < n_splits * 10:  # Require at least 10 obs per split
        logger.warning(
            "Insufficient data for %d splits (n=%d), returning empty list",
            n_splits,
            len(signal),
        )
        return []

    # Split into chronological subperiods
    split_size = len(signal) // n_splits
    betas = []

    for i in range(n_splits):
        start_idx = i * split_size
        end_idx = (i + 1) * split_size if i < n_splits - 1 else len(signal)

        signal_sub = signal.iloc[start_idx:end_idx]
        target_sub = target.iloc[start_idx:end_idx]

        logger.debug(
            "Subperiod %d: indices %d-%d (n=%d)",
            i + 1,
            start_idx,
            end_idx,
            len(signal_sub),
        )

        stats = compute_regression_stats(signal_sub, target_sub)
        betas.append(stats["beta"])

    logger.debug("Subperiod betas: %s", betas)
    return betas


def check_sign_consistency(betas: list[float]) -> bool:
    """
    Check if all beta coefficients have consistent sign.

    Parameters
    ----------
    betas : list[float]
        List of beta coefficients from subperiod analysis.

    Returns
    -------
    bool
        True if all betas have the same sign (all positive or all negative),
        False otherwise. Returns False if list is empty or contains zeros.

    Notes
    -----
    Sign consistency indicates temporal stability of the predictive relationship.
    Zero betas are treated as inconsistent (no stable relationship).

    Examples
    --------
    >>> check_sign_consistency([1.5, 2.0, 1.8])
    True
    >>> check_sign_consistency([1.5, -0.5, 1.8])
    False
    >>> check_sign_consistency([0.0, 1.5])
    False
    """
    if not betas:
        logger.debug("Empty beta list, returning inconsistent")
        return False

    # Filter out zeros (treat as inconsistent)
    non_zero_betas = [b for b in betas if abs(b) > 1e-10]

    if not non_zero_betas:
        logger.debug("All betas are zero, returning inconsistent")
        return False

    # Check if all have same sign
    signs = [np.sign(b) for b in non_zero_betas]
    consistent = len(set(signs)) == 1

    logger.debug(
        "Sign consistency check: betas=%s, signs=%s, consistent=%s",
        betas,
        signs,
        consistent,
    )

    return consistent
