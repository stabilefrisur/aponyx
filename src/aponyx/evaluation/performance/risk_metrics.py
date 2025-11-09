"""
Extended risk and stability metrics for performance evaluation.

Provides advanced metrics beyond standard backtest statistics, including
rolling performance diagnostics, drawdown recovery analysis, tail risk,
and consistency measures.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_rolling_sharpe(
    pnl_series: pd.Series,
    window: int = 63,
) -> pd.Series:
    """
    Compute rolling Sharpe ratio over specified window.

    Parameters
    ----------
    pnl_series : pd.Series
        Daily P&L time series with DatetimeIndex.
    window : int
        Rolling window length in days. Default: 63 (3 months).

    Returns
    -------
    pd.Series
        Rolling annualized Sharpe ratio.

    Notes
    -----
    Assumes 252 trading days per year for annualization.
    Uses zero risk-free rate for simplicity.
    First (window - 1) values will be NaN.

    Examples
    --------
    >>> rolling_sharpe = compute_rolling_sharpe(pnl_df['net_pnl'], window=63)
    >>> print(f"Latest 3M Sharpe: {rolling_sharpe.iloc[-1]:.2f}")
    """
    logger.debug("Computing rolling Sharpe: window=%d days", window)

    rolling_mean = pnl_series.rolling(window).mean()
    rolling_std = pnl_series.rolling(window).std()

    # Annualize (handle zero std)
    rolling_sharpe = rolling_mean / rolling_std * np.sqrt(252)
    rolling_sharpe = rolling_sharpe.fillna(0.0)

    valid_count = (rolling_mean.notna() & rolling_std.notna()).sum()
    logger.debug("Rolling Sharpe computed: %d valid observations", valid_count)

    return rolling_sharpe


def compute_drawdown_recovery_time(cumulative_pnl: pd.Series) -> dict[str, float]:
    """
    Compute drawdown recovery statistics.

    Calculates time required to recover from maximum drawdown and
    average recovery time across all drawdown periods.

    Parameters
    ----------
    cumulative_pnl : pd.Series
        Cumulative P&L time series with DatetimeIndex.

    Returns
    -------
    dict[str, float]
        Dictionary with keys:
        - 'max_dd_recovery_days': Days to recover from max drawdown (np.inf if not recovered)
        - 'avg_recovery_days': Average recovery time across all drawdowns
        - 'n_drawdowns': Number of distinct drawdown periods

    Notes
    -----
    A drawdown period starts when equity falls below previous peak
    and ends when equity reaches a new peak.

    Examples
    --------
    >>> recovery = compute_drawdown_recovery_time(pnl_df['cumulative_pnl'])
    >>> print(f"Max DD recovery: {recovery['max_dd_recovery_days']:.0f} days")
    """
    logger.debug("Computing drawdown recovery metrics")

    running_max = cumulative_pnl.expanding().max()
    drawdown = cumulative_pnl - running_max

    # Find maximum drawdown
    max_dd_idx = drawdown.idxmin()

    # Find when max drawdown started (last peak before max DD)
    peaks_before = running_max[:max_dd_idx]
    if len(peaks_before) > 0:
        max_dd_start = peaks_before[peaks_before == running_max[max_dd_idx]].index[-1]
    else:
        max_dd_start = cumulative_pnl.index[0]

    # Find recovery point (when equity reaches peak level again)
    peak_level = running_max[max_dd_idx]
    recovery_mask = (cumulative_pnl.index > max_dd_idx) & (cumulative_pnl >= peak_level)

    if recovery_mask.any():
        recovery_idx = cumulative_pnl[recovery_mask].index[0]
        max_dd_recovery_days = (recovery_idx - max_dd_start).days
    else:
        max_dd_recovery_days = np.inf

    # Count all drawdown periods
    in_drawdown = drawdown < 0
    drawdown_starts = (~in_drawdown.shift(1, fill_value=False)) & in_drawdown
    n_drawdowns = drawdown_starts.sum()

    # Compute average recovery time for all recovered drawdowns
    recovery_times = []
    current_dd_start = None

    for idx in cumulative_pnl.index:
        if drawdown[idx] < 0 and current_dd_start is None:
            # Start of new drawdown
            current_dd_start = idx
        elif drawdown[idx] == 0 and current_dd_start is not None:
            # Recovery from drawdown
            recovery_days = (idx - current_dd_start).days
            recovery_times.append(recovery_days)
            current_dd_start = None

    avg_recovery_days = np.mean(recovery_times) if recovery_times else 0.0

    logger.debug(
        "Drawdown recovery: max_dd_recovery=%.0f days, n_drawdowns=%d",
        max_dd_recovery_days if max_dd_recovery_days != np.inf else -1,
        n_drawdowns,
    )

    return {
        "max_dd_recovery_days": max_dd_recovery_days,
        "avg_recovery_days": avg_recovery_days,
        "n_drawdowns": int(n_drawdowns),
    }


def compute_tail_ratio(pnl_series: pd.Series, percentile: float = 95.0) -> float:
    """
    Compute tail ratio as measure of upside vs downside tail risk.

    Ratio of absolute values of right tail (gains) to left tail (losses).
    Values > 1 indicate favorable asymmetry (larger wins than losses).

    Parameters
    ----------
    pnl_series : pd.Series
        Daily P&L time series.
    percentile : float
        Percentile for tail definition. Default: 95.0 (top/bottom 5%).

    Returns
    -------
    float
        Tail ratio (right_tail / abs(left_tail)).
        Returns 0 if insufficient data or undefined.

    Notes
    -----
    Tail ratio complements traditional skewness by focusing on
    extreme outcomes rather than entire distribution.

    Examples
    --------
    >>> tail_ratio = compute_tail_ratio(pnl_df['net_pnl'])
    >>> print(f"Tail ratio: {tail_ratio:.2f}")  # > 1 is favorable
    """
    logger.debug("Computing tail ratio: percentile=%.1f", percentile)

    if len(pnl_series) < 20:
        logger.warning("Insufficient data for tail ratio: %d observations", len(pnl_series))
        return 0.0

    right_tail = np.percentile(pnl_series, percentile)
    left_tail = np.percentile(pnl_series, 100 - percentile)

    if left_tail < 0:
        tail_ratio = abs(right_tail / left_tail)
    else:
        tail_ratio = 0.0

    logger.debug("Tail ratio: %.3f (right=%.2f, left=%.2f)", tail_ratio, right_tail, left_tail)

    return tail_ratio


def compute_profit_factor(pnl_series: pd.Series) -> float:
    """
    Compute profit factor as ratio of gross profits to gross losses.

    Parameters
    ----------
    pnl_series : pd.Series
        Daily P&L time series.

    Returns
    -------
    float
        Profit factor (sum of gains / abs(sum of losses)).
        Returns 0 if no losses or insufficient data.

    Notes
    -----
    Profit factor > 1 indicates profitable strategy.
    Differs from win/loss ratio by using sums, not averages.

    Examples
    --------
    >>> pf = compute_profit_factor(pnl_df['net_pnl'])
    >>> print(f"Profit factor: {pf:.2f}")  # > 1 is profitable
    """
    logger.debug("Computing profit factor")

    gross_profit = pnl_series[pnl_series > 0].sum()
    gross_loss = abs(pnl_series[pnl_series < 0].sum())

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = 0.0 if gross_profit == 0 else np.inf

    logger.debug(
        "Profit factor: %.3f (profit=%.2f, loss=%.2f)", profit_factor, gross_profit, gross_loss
    )

    return profit_factor


def compute_consistency_score(pnl_series: pd.Series, window: int = 21) -> float:
    """
    Compute consistency score as proportion of positive rolling windows.

    Measures how consistently the strategy generates positive returns
    over rolling periods.

    Parameters
    ----------
    pnl_series : pd.Series
        Daily P&L time series.
    window : int
        Rolling window length in days. Default: 21 (1 month).

    Returns
    -------
    float
        Consistency score (0-1 scale).
        Proportion of rolling windows with positive cumulative P&L.

    Notes
    -----
    Higher scores indicate more consistent performance.
    Complements traditional Sharpe by focusing on win frequency
    rather than risk-adjusted returns.

    Examples
    --------
    >>> consistency = compute_consistency_score(pnl_df['net_pnl'], window=21)
    >>> print(f"Consistency: {consistency:.1%}")  # Higher is better
    """
    logger.debug("Computing consistency score: window=%d days", window)

    rolling_sum = pnl_series.rolling(window).sum()
    positive_windows = (rolling_sum > 0).sum()
    total_windows = rolling_sum.notna().sum()

    if total_windows > 0:
        consistency = positive_windows / total_windows
    else:
        consistency = 0.0

    logger.debug(
        "Consistency score: %.3f (%d/%d positive windows)",
        consistency,
        positive_windows,
        total_windows,
    )

    return consistency


def compute_extended_metrics(
    pnl_df: pd.DataFrame,
    rolling_window: int = 63,
) -> dict[str, float]:
    """
    Compute all extended risk and stability metrics.

    Orchestrates computation of rolling Sharpe, drawdown recovery,
    tail ratios, profit factor, and consistency metrics.

    Parameters
    ----------
    pnl_df : pd.DataFrame
        P&L DataFrame with 'net_pnl' and 'cumulative_pnl' columns.
    rolling_window : int
        Window length for rolling metrics. Default: 63 days.

    Returns
    -------
    dict[str, float]
        Dictionary with all extended metrics:
        - rolling_sharpe_mean: Average rolling Sharpe
        - rolling_sharpe_std: Volatility of rolling Sharpe
        - max_dd_recovery_days: Recovery time from max drawdown
        - avg_recovery_days: Average recovery across all drawdowns
        - n_drawdowns: Count of drawdown periods
        - tail_ratio: Upside/downside tail ratio
        - profit_factor: Gross profits / gross losses
        - consistency_score: Proportion of positive rolling windows

    Notes
    -----
    This function provides a comprehensive risk profile beyond
    standard backtest metrics. All metrics are computed from
    daily P&L, not equity curve.

    Examples
    --------
    >>> extended = compute_extended_metrics(result.pnl, rolling_window=63)
    >>> print(f"Avg rolling Sharpe: {extended['rolling_sharpe_mean']:.2f}")
    """
    logger.info("Computing extended risk metrics: window=%d days", rolling_window)

    # Rolling Sharpe statistics
    rolling_sharpe = compute_rolling_sharpe(pnl_df["net_pnl"], window=rolling_window)
    rolling_sharpe_mean = rolling_sharpe.mean()
    rolling_sharpe_std = rolling_sharpe.std()

    # Drawdown recovery
    recovery_stats = compute_drawdown_recovery_time(pnl_df["cumulative_pnl"])

    # Tail risk
    tail_ratio = compute_tail_ratio(pnl_df["net_pnl"])

    # Profitability metrics
    profit_factor = compute_profit_factor(pnl_df["net_pnl"])

    # Consistency
    consistency_score = compute_consistency_score(pnl_df["net_pnl"], window=21)

    metrics = {
        "rolling_sharpe_mean": rolling_sharpe_mean,
        "rolling_sharpe_std": rolling_sharpe_std,
        "max_dd_recovery_days": recovery_stats["max_dd_recovery_days"],
        "avg_recovery_days": recovery_stats["avg_recovery_days"],
        "n_drawdowns": recovery_stats["n_drawdowns"],
        "tail_ratio": tail_ratio,
        "profit_factor": profit_factor,
        "consistency_score": consistency_score,
    }

    logger.info(
        "Extended metrics computed: profit_factor=%.2f, tail_ratio=%.2f, consistency=%.1f%%",
        profit_factor,
        tail_ratio,
        consistency_score * 100,
    )

    return metrics
