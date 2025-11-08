"""
Performance and risk metrics for backtest analysis.

Provides standard quantitative metrics for strategy evaluation.
Metrics follow industry conventions and are compatible with common
performance attribution frameworks.
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """
    Container for strategy performance statistics.

    Attributes
    ----------
    sharpe_ratio : float
        Annualized Sharpe ratio (assumes 252 trading days).
    sortino_ratio : float
        Annualized Sortino ratio (downside deviation).
    max_drawdown : float
        Maximum peak-to-trough decline in cumulative P&L.
    calmar_ratio : float
        Annualized return divided by max drawdown.
    total_return : float
        Total P&L over backtest period.
    annualized_return : float
        Total return annualized to yearly basis.
    annualized_volatility : float
        Annualized standard deviation of daily returns.
    hit_rate : float
        Proportion of profitable trades (0.0 to 1.0).
    avg_win : float
        Average P&L of winning trades.
    avg_loss : float
        Average P&L of losing trades (negative).
    win_loss_ratio : float
        Absolute value of avg_win / avg_loss.
    n_trades : int
        Total number of round-trip trades.
    avg_holding_days : float
        Average days per trade.

    Notes
    -----
    All ratios use risk-free rate = 0 for simplicity.
    Metrics are based on daily P&L, not mark-to-market equity curve.
    """

    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    total_return: float
    annualized_return: float
    annualized_volatility: float
    hit_rate: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    n_trades: int
    avg_holding_days: float


def compute_performance_metrics(
    pnl_df: pd.DataFrame,
    positions_df: pd.DataFrame,
) -> PerformanceMetrics:
    """
    Compute comprehensive performance metrics from backtest results.

    Parameters
    ----------
    pnl_df : pd.DataFrame
        Daily P&L data with 'net_pnl' and 'cumulative_pnl' columns.
    positions_df : pd.DataFrame
        Daily position data with 'position' and 'days_held' columns.

    Returns
    -------
    PerformanceMetrics
        Complete set of performance statistics.

    Notes
    -----
    Calculations assume:
    - 252 trading days per year for annualization
    - No risk-free rate (excess returns = total returns)
    - Daily P&L represents actual trading results

    Sharpe and Sortino use daily P&L volatility, not equity curve volatility.
    This better captures strategy risk for overlay strategies.

    Examples
    --------
    >>> metrics = compute_performance_metrics(result.pnl, result.positions)
    >>> print(f"Sharpe: {metrics.sharpe_ratio:.2f}, Max DD: ${metrics.max_drawdown:,.0f}")
    """
    logger.info("Computing performance metrics")

    # Basic statistics
    daily_pnl = pnl_df["net_pnl"]
    cum_pnl = pnl_df["cumulative_pnl"]
    n_days = len(pnl_df)
    n_years = n_days / 252.0

    # Return metrics
    total_return = cum_pnl.iloc[-1]
    annualized_return = total_return / n_years if n_years > 0 else 0.0

    # Risk metrics
    daily_std = daily_pnl.std()
    annualized_vol = daily_std * np.sqrt(252)

    # Sharpe ratio (using daily P&L, not equity curve)
    if daily_std > 0:
        sharpe_ratio = (daily_pnl.mean() / daily_std) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    # Sortino ratio (downside deviation)
    downside_returns = daily_pnl[daily_pnl < 0]
    if len(downside_returns) > 0:
        downside_std = downside_returns.std()
        if downside_std > 0:
            sortino_ratio = (daily_pnl.mean() / downside_std) * np.sqrt(252)
        else:
            sortino_ratio = 0.0
    else:
        sortino_ratio = sharpe_ratio  # No downside = same as Sharpe

    # Drawdown analysis
    running_max = cum_pnl.expanding().max()
    drawdown = cum_pnl - running_max
    max_drawdown = drawdown.min()

    # Calmar ratio
    if max_drawdown < 0:
        calmar_ratio = annualized_return / abs(max_drawdown)
    else:
        calmar_ratio = 0.0

    # Trade-level statistics
    # Identify trade entries (transitions from flat to positioned)
    prev_position = positions_df["position"].shift(1).fillna(0)
    position_entries = (prev_position == 0) & (positions_df["position"] != 0)
    n_trades = position_entries.sum()

    # Compute P&L per trade by grouping consecutive positions
    # Assign a trade_id to each position period
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

    logger.info(
        "Metrics computed: sharpe=%.2f, max_dd=$%.0f, hit_rate=%.1f%%",
        sharpe_ratio,
        max_drawdown,
        hit_rate * 100,
    )

    return PerformanceMetrics(
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        calmar_ratio=calmar_ratio,
        total_return=total_return,
        annualized_return=annualized_return,
        annualized_volatility=annualized_vol,
        hit_rate=hit_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        win_loss_ratio=win_loss_ratio,
        n_trades=int(n_trades),
        avg_holding_days=avg_holding_days,
    )
