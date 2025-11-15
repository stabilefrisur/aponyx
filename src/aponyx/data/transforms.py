"""
Time series transformation functions for financial data.

Provides standardized transformations with consistent edge case handling:
- First difference (absolute change)
- Percent change (relative change)
- Log returns (continuous compounding)
- Z-score normalization (standardization)
- Normalized change (volatility-adjusted)
"""

import logging
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TransformType = Literal[
    "diff",
    "pct_change",
    "log_return",
    "z_score",
    "normalized_change",
]


def apply_transform(
    series: pd.Series,
    transform: TransformType,
    *,
    window: int | None = None,
    min_periods: int | None = None,
    periods: int = 1,
) -> pd.Series:
    """
    Apply time series transformation with edge case handling.

    Parameters
    ----------
    series : pd.Series
        Input time series with DatetimeIndex.
    transform : TransformType
        Type of transformation to apply:
        - 'diff': First difference (x[t] - x[t-periods])
        - 'pct_change': Percent change ((x[t] - x[t-periods]) / x[t-periods])
        - 'log_return': Log return (log(x[t] / x[t-periods]))
        - 'z_score': Rolling z-score normalization
        - 'normalized_change': Change normalized by rolling volatility
    window : int or None
        Rolling window size for z_score and normalized_change.
        Required for these transforms, ignored for others.
    min_periods : int or None
        Minimum observations for rolling calculations.
        Defaults to window if not specified.
    periods : int, default 1
        Number of periods for differencing operations.

    Returns
    -------
    pd.Series
        Transformed series with same DatetimeIndex.
        NaN values propagate from input or calculation.

    Raises
    ------
    ValueError
        If required parameters are missing for transform type.
        If log_return used on series with non-positive values.

    Examples
    --------
    >>> spreads = pd.Series([100, 105, 103, 108], index=pd.date_range('2024-01-01', periods=4))
    >>> apply_transform(spreads, 'diff')
    >>> apply_transform(spreads, 'pct_change')
    >>> apply_transform(spreads, 'z_score', window=20, min_periods=10)

    Notes
    -----
    - All transforms preserve DatetimeIndex alignment
    - NaN handling follows pandas conventions (NaN in = NaN out)
    - Division by zero in pct_change produces inf (pandas default)
    - log_return validates input is positive before calculation
    """
    if transform == "diff":
        return _diff(series, periods)
    elif transform == "pct_change":
        return _pct_change(series, periods)
    elif transform == "log_return":
        return _log_return(series, periods)
    elif transform == "z_score":
        if window is None:
            raise ValueError("window parameter required for z_score transform")
        return _z_score(series, window, min_periods)
    elif transform == "normalized_change":
        if window is None:
            raise ValueError("window parameter required for normalized_change transform")
        return _normalized_change(series, window, min_periods, periods)
    else:
        raise ValueError(f"Unknown transform type: {transform}")


def _diff(series: pd.Series, periods: int = 1) -> pd.Series:
    """
    Compute first difference: x[t] - x[t-periods].

    Parameters
    ----------
    series : pd.Series
        Input time series.
    periods : int, default 1
        Number of periods to difference.

    Returns
    -------
    pd.Series
        First differences.

    Notes
    -----
    First `periods` observations will be NaN.
    """
    return series.diff(periods)


def _pct_change(series: pd.Series, periods: int = 1) -> pd.Series:
    """
    Compute percent change: (x[t] - x[t-periods]) / x[t-periods].

    Parameters
    ----------
    series : pd.Series
        Input time series.
    periods : int, default 1
        Number of periods for change calculation.

    Returns
    -------
    pd.Series
        Percent changes.

    Notes
    -----
    - Division by zero produces inf (pandas default behavior)
    - First `periods` observations will be NaN
    - Use for cross-asset comparison where scales differ
    """
    return series.pct_change(periods)


def _log_return(series: pd.Series, periods: int = 1) -> pd.Series:
    """
    Compute log returns: log(x[t] / x[t-periods]).

    Parameters
    ----------
    series : pd.Series
        Input time series. Must contain only positive values.
    periods : int, default 1
        Number of periods for return calculation.

    Returns
    -------
    pd.Series
        Log returns.

    Raises
    ------
    ValueError
        If series contains non-positive values (zero or negative).

    Notes
    -----
    - Validates all non-NaN values are positive before calculation
    - First `periods` observations will be NaN
    - Preferred for risk calculations (continuous compounding)
    - Approximates pct_change for small changes
    """
    # Check for non-positive values (excluding NaN)
    non_positive = (series <= 0) & series.notna()
    if non_positive.any():
        n_invalid = non_positive.sum()
        raise ValueError(
            f"log_return requires positive values, found {n_invalid} non-positive entries"
        )

    return np.log(series / series.shift(periods))


def _z_score(series: pd.Series, window: int, min_periods: int | None = None) -> pd.Series:
    """
    Compute rolling z-score: (x - rolling_mean) / rolling_std.

    Parameters
    ----------
    series : pd.Series
        Input time series.
    window : int
        Rolling window size for mean and std calculation.
    min_periods : int or None
        Minimum observations required. Defaults to window.

    Returns
    -------
    pd.Series
        Rolling z-scores (zero mean, unit variance within window).

    Notes
    -----
    - Useful for regime-independent signals
    - First `window - 1` (or `min_periods - 1`) observations will be NaN
    - Division by zero std produces inf (pandas default)
    - More robust than raw differences when volatility varies over time
    """
    if min_periods is None:
        min_periods = window

    rolling_mean = series.rolling(window=window, min_periods=min_periods).mean()
    rolling_std = series.rolling(window=window, min_periods=min_periods).std()

    return (series - rolling_mean) / rolling_std


def _normalized_change(
    series: pd.Series,
    window: int,
    min_periods: int | None = None,
    periods: int = 1,
) -> pd.Series:
    """
    Compute change normalized by rolling volatility: (x[t] - x[t-periods]) / rolling_std.

    Parameters
    ----------
    series : pd.Series
        Input time series.
    window : int
        Rolling window for volatility calculation.
    min_periods : int or None
        Minimum observations required. Defaults to window.
    periods : int, default 1
        Number of periods for change calculation.

    Returns
    -------
    pd.Series
        Volatility-normalized changes.

    Notes
    -----
    - Combines absolute change with volatility scaling
    - Useful when comparing signals across different regimes
    - Similar to z_score but uses absolute change instead of deviation from mean
    - First `max(window, periods)` observations will be NaN
    """
    if min_periods is None:
        min_periods = window

    change = series.diff(periods)
    rolling_std = series.rolling(window=window, min_periods=min_periods).std()

    return change / rolling_std
