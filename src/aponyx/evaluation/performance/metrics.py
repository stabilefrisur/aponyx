"""
Extended risk and stability metrics for performance evaluation.

Provides advanced metrics beyond standard backtest statistics, including
rolling performance diagnostics, drawdown recovery analysis, tail risk,
and consistency measures. Consolidates all performance metrics (basic + extended)
into a unified computation function.
"""

import logging

import numpy as np
import pandas as pd

from .config import PerformanceMetrics

logger = logging.getLogger(__name__)


def compute_all_metrics(
    pnl_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    rolling_window: int = 63,
) -> PerformanceMetrics:
    """
    Compute all performance metrics (basic + extended) from backtest results.

    Consolidates computation of 21 comprehensive metrics including returns,
    risk-adjusted ratios, trade statistics, and stability measures. Optimizes
    shared calculations (drawdown, daily stats) to avoid redundancy.

    Parameters
    ----------
    pnl_df : pd.DataFrame
        Daily P&L data with 'net_pnl' and 'cumulative_pnl' columns.
    positions_df : pd.DataFrame
        Daily position data with 'position' and 'days_held' columns.
    rolling_window : int
        Window length for rolling metrics. Default: 63 days (3 months).

    Returns
    -------
    PerformanceMetrics
        Complete set of 21 performance statistics organized by category.

    Notes
    -----
    Calculations assume:
    - 252 trading days per year for annualization
    - No risk-free rate (excess returns = total returns)
    - Daily P&L represents actual trading results

    Shared intermediates (running_max, drawdown, daily stats) are computed
    once and reused across metrics for efficiency.

    Examples
    --------
    >>> from aponyx.evaluation.performance import compute_all_metrics
    >>> metrics = compute_all_metrics(result.pnl, result.positions)
    >>> print(f"Sharpe: {metrics.sharpe_ratio:.2f}, Trades: {metrics.n_trades}")
    """
    from aponyx.evaluation.performance.config import PerformanceMetrics

    logger.debug("Computing all performance metrics: rolling_window=%d", rolling_window)

    # ==================== Shared Intermediates ====================
    daily_pnl = pnl_df["net_pnl"]
    cum_pnl = pnl_df["cumulative_pnl"]
    n_days = len(pnl_df)
    n_years = n_days / 252.0

    # Daily statistics (shared by Sharpe, Sortino, volatility)
    daily_mean = daily_pnl.mean()
    daily_std = daily_pnl.std()

    # Drawdown analysis (shared by max_drawdown and recovery metrics)
    running_max = cum_pnl.expanding().max()
    drawdown = cum_pnl - running_max
    max_drawdown = drawdown.min()

    # ==================== Return Metrics ====================
    total_return = cum_pnl.iloc[-1]
    annualized_return = total_return / n_years if n_years > 0 else 0.0

    # ==================== Risk-Adjusted Metrics ====================
    annualized_vol = daily_std * np.sqrt(252)

    # Sharpe ratio
    if daily_std > 0:
        sharpe_ratio = (daily_mean / daily_std) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    # Sortino ratio (downside deviation)
    downside_returns = daily_pnl[daily_pnl < 0]
    if len(downside_returns) > 0:
        downside_std = downside_returns.std()
        if downside_std > 0:
            sortino_ratio = (daily_mean / downside_std) * np.sqrt(252)
        else:
            sortino_ratio = 0.0
    else:
        sortino_ratio = sharpe_ratio  # No downside = same as Sharpe

    # Calmar ratio
    if max_drawdown < 0:
        calmar_ratio = annualized_return / abs(max_drawdown)
    else:
        calmar_ratio = 0.0

    # ==================== Trade Statistics ====================
    # Identify trade entries (transitions from flat to positioned)
    prev_position = positions_df["position"].shift(1).fillna(0)
    position_entries = (prev_position == 0) & (positions_df["position"] != 0)
    n_trades = position_entries.sum()

    # Compute P&L per trade by grouping consecutive positions
    position_changes = (positions_df["position"] != prev_position).astype(int)
    trade_id = position_changes.cumsum()

    # Only include periods where we have a position
    active_trades = positions_df[positions_df["position"] != 0].copy()

    if len(active_trades) > 0:
        active_trades["trade_id"] = trade_id[positions_df["position"] != 0]

        # Sum P&L per trade_id
        trade_pnls = (
            pnl_df.loc[active_trades.index].groupby(active_trades["trade_id"])["net_pnl"].sum()
        )

        trade_pnls_array = trade_pnls.values
        winning_trades = trade_pnls_array[trade_pnls_array > 0]
        losing_trades = trade_pnls_array[trade_pnls_array < 0]

        hit_rate = len(winning_trades) / len(trade_pnls_array) if len(trade_pnls_array) > 0 else 0.0
        avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0.0
        avg_loss = losing_trades.mean() if len(losing_trades) > 0 else 0.0

        if avg_loss < 0:
            win_loss_ratio = abs(avg_win / avg_loss)
        else:
            win_loss_ratio = 0.0
    else:
        hit_rate = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        win_loss_ratio = 0.0

    # Holding period statistics
    holding_periods = positions_df[positions_df["position"] != 0]["days_held"]
    avg_holding_days = holding_periods.mean() if len(holding_periods) > 0 else 0.0

    # ==================== Stability Metrics ====================
    # Rolling Sharpe statistics
    rolling_sharpe = compute_rolling_sharpe(daily_pnl, window=rolling_window)
    rolling_sharpe_mean = rolling_sharpe.mean()
    rolling_sharpe_std = rolling_sharpe.std()

    # Drawdown recovery (pass pre-computed intermediates)
    recovery_stats = _compute_drawdown_recovery_optimized(cum_pnl, running_max, drawdown)

    # Tail risk
    tail_ratio = compute_tail_ratio(daily_pnl)

    # Profitability metrics
    profit_factor = compute_profit_factor(daily_pnl)

    # Consistency
    consistency_score = compute_consistency_score(daily_pnl, window=21)

    # ==================== Assemble Result ====================
    logger.debug(
        "Computed 21 metrics: sharpe=%.2f, trades=%d, profit_factor=%.2f",
        sharpe_ratio,
        n_trades,
        profit_factor,
    )

    return PerformanceMetrics(
        # Returns
        total_return=total_return,
        annualized_return=annualized_return,
        # Risk-adjusted
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
        max_drawdown=max_drawdown,
        annualized_volatility=annualized_vol,
        # Trade stats
        n_trades=int(n_trades),
        hit_rate=hit_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        win_loss_ratio=win_loss_ratio,
        avg_holding_days=avg_holding_days,
        # Stability
        rolling_sharpe_mean=rolling_sharpe_mean,
        rolling_sharpe_std=rolling_sharpe_std,
        max_dd_recovery_days=recovery_stats["max_dd_recovery_days"],
        avg_recovery_days=recovery_stats["avg_recovery_days"],
        n_drawdowns=recovery_stats["n_drawdowns"],
        tail_ratio=tail_ratio,
        profit_factor=profit_factor,
        consistency_score=consistency_score,
    )


def _compute_drawdown_recovery_optimized(
    cumulative_pnl: pd.Series,
    running_max: pd.Series,
    drawdown: pd.Series,
) -> dict[str, float]:
    """
    Compute drawdown recovery using pre-computed intermediates.

    Optimized version that accepts pre-computed running_max and drawdown
    to avoid redundant calculation when called from compute_all_metrics.

    Parameters
    ----------
    cumulative_pnl : pd.Series
        Cumulative P&L time series.
    running_max : pd.Series
        Expanding maximum of cumulative P&L.
    drawdown : pd.Series
        Drawdown series (cumulative_pnl - running_max).

    Returns
    -------
    dict[str, float]
        Recovery statistics (max_dd_recovery_days, avg_recovery_days, n_drawdowns).
    """
    logger.debug("Computing drawdown recovery from pre-computed intermediates")

    # Find maximum drawdown
    max_dd_idx = drawdown.idxmin()

    # Find when max drawdown started
    peaks_before = running_max[:max_dd_idx]
    if len(peaks_before) > 0:
        max_dd_start = peaks_before[peaks_before == running_max[max_dd_idx]].index[-1]
    else:
        max_dd_start = cumulative_pnl.index[0]

    # Find recovery point
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

    # Compute average recovery time
    recovery_times = []
    current_dd_start = None

    for idx in cumulative_pnl.index:
        if drawdown[idx] < 0 and current_dd_start is None:
            current_dd_start = idx
        elif drawdown[idx] == 0 and current_dd_start is not None:
            recovery_days = (idx - current_dd_start).days
            recovery_times.append(recovery_days)
            current_dd_start = None

    avg_recovery_days = np.mean(recovery_times) if recovery_times else 0.0

    return {
        "max_dd_recovery_days": max_dd_recovery_days,
        "avg_recovery_days": avg_recovery_days,
        "n_drawdowns": int(n_drawdowns),
    }


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
