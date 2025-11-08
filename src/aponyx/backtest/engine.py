"""
Core backtesting engine for signal-to-position simulation.

This module converts signals into positions and simulates P&L.
Design is intentionally simple to allow easy replacement with external
libraries while maintaining our domain-specific logic.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from .config import BacktestConfig

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """
    Container for backtest outputs.

    Attributes
    ----------
    positions : pd.DataFrame
        Daily position history with columns:
        - signal: signal value
        - position: current position (+1, 0, -1)
        - days_held: days in current position
        - spread: CDX spread level (for P&L calc)
    pnl : pd.DataFrame
        Daily P&L breakdown with columns:
        - spread_pnl: P&L from spread changes
        - cost: transaction costs
        - net_pnl: total net P&L
        - cumulative_pnl: running total
    metadata : dict
        Backtest configuration and execution details.

    Notes
    -----
    This structure is designed to be easily convertible to formats
    expected by third-party backtest libraries (e.g., vectorbt).
    """

    positions: pd.DataFrame
    pnl: pd.DataFrame
    metadata: dict[str, Any]


def run_backtest(
    composite_signal: pd.Series,
    spread: pd.Series,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """
    Run backtest converting signals to positions and computing P&L.

    Parameters
    ----------
    composite_signal : pd.Series
        Daily positioning scores from signal computation.
        DatetimeIndex with float values.
    spread : pd.Series
        CDX spread levels aligned to signal dates.
        Used for P&L calculation.
    config : BacktestConfig | None
        Backtest parameters. Uses defaults if None.

    Returns
    -------
    BacktestResult
        Complete backtest results including positions and P&L.

    Notes
    -----
    Position Logic:
    - Enter long (sell protection) when signal > entry_threshold
    - Enter short (buy protection) when signal < -entry_threshold
    - Exit when |signal| < exit_threshold or max_holding_days reached
    - No position scaling in pilot (binary on/off)

    P&L Calculation:
    - Long position: profit when spreads tighten (P&L = -ΔSpread * DV01)
    - Short position: profit when spreads widen (P&L = ΔSpread * DV01)
    - Transaction costs applied on entry and exit
    - P&L expressed in dollars per $1MM notional

    Examples
    --------
    >>> config = BacktestConfig(entry_threshold=1.5, position_size=10.0)
    >>> result = run_backtest(composite_signal, cdx_spread, config)
    >>> sharpe = result.pnl['net_pnl'].mean() / result.pnl['net_pnl'].std() * np.sqrt(252)
    """
    if config is None:
        config = BacktestConfig()

    logger.info(
        "Starting backtest: dates=%d, entry_threshold=%.2f, position_size=%.1fMM",
        len(composite_signal),
        config.entry_threshold,
        config.position_size,
    )

    # Validate inputs
    if not isinstance(composite_signal.index, pd.DatetimeIndex):
        raise ValueError("composite_signal must have DatetimeIndex")
    if not isinstance(spread.index, pd.DatetimeIndex):
        raise ValueError("spread must have DatetimeIndex")

    # Align data
    aligned = pd.DataFrame(
        {
            "signal": composite_signal,
            "spread": spread,
        }
    ).dropna()

    if len(aligned) == 0:
        raise ValueError("No valid data after alignment")

    # Initialize tracking
    positions = []
    pnl_records = []
    current_position = 0
    days_held = 0
    entry_spread = 0.0

    for date, row in aligned.iterrows():
        signal = row["signal"]
        spread_level = row["spread"]

        # Initialize cost tracking for this iteration
        entry_cost = 0.0
        exit_cost = 0.0

        # Store position before any state changes (for P&L calculation)
        position_before_update = current_position
        entry_spread_before_update = entry_spread

        # Determine position based on signal thresholds
        if current_position == 0:
            # Not in position - check entry conditions
            if signal > config.entry_threshold:
                current_position = 1  # Long credit risk (sell protection)
                days_held = 0
                entry_spread = spread_level
                entry_cost = config.transaction_cost_bps * config.position_size * 100
            elif signal < -config.entry_threshold:
                current_position = -1  # Short credit risk (buy protection)
                days_held = 0
                entry_spread = spread_level
                entry_cost = config.transaction_cost_bps * config.position_size * 100
        else:
            # In position - check exit conditions
            days_held += 1

            exit_signal = abs(signal) < config.exit_threshold
            exit_time = config.max_holding_days is not None and days_held >= config.max_holding_days

            if exit_signal or exit_time:
                # Exit position (will apply exit cost and capture final P&L)
                exit_cost = config.transaction_cost_bps * config.position_size * 100
                current_position = 0
                days_held = 0

        # Calculate P&L based on position we held during this period
        # Use position_before_update to capture P&L on exit day
        if position_before_update != 0:
            # Spread change: negative when tightening, positive when widening
            spread_change = spread_level - entry_spread_before_update
            # Long position profits from tightening (negative spread change)
            # Short position profits from widening (positive spread change)
            # P&L = -position * spread_change * DV01 * position_size
            spread_pnl = (
                -position_before_update
                * spread_change
                * config.dv01_per_million
                * config.position_size
            )
        else:
            spread_pnl = 0.0

        total_cost = entry_cost + exit_cost
        net_pnl = spread_pnl - total_cost

        # Record position state
        positions.append(
            {
                "date": date,
                "signal": signal,
                "position": current_position,
                "days_held": days_held,
                "spread": spread_level,
            }
        )

        # Record P&L
        pnl_records.append(
            {
                "date": date,
                "spread_pnl": spread_pnl,
                "cost": total_cost,
                "net_pnl": net_pnl,
            }
        )

    # Convert to DataFrames
    positions_df = pd.DataFrame(positions).set_index("date")
    pnl_df = pd.DataFrame(pnl_records).set_index("date")
    pnl_df["cumulative_pnl"] = pnl_df["net_pnl"].cumsum()

    # Calculate summary statistics (count round-trip trades: entries only)
    prev_position = positions_df["position"].shift(1).fillna(0)
    position_entries = (prev_position == 0) & (positions_df["position"] != 0)
    n_trades = position_entries.sum()
    total_pnl = pnl_df["cumulative_pnl"].iloc[-1]
    avg_pnl_per_trade = total_pnl / n_trades if n_trades > 0 else 0.0

    metadata = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "entry_threshold": config.entry_threshold,
            "exit_threshold": config.exit_threshold,
            "position_size": config.position_size,
            "transaction_cost_bps": config.transaction_cost_bps,
            "max_holding_days": config.max_holding_days,
            "dv01_per_million": config.dv01_per_million,
        },
        "summary": {
            "start_date": str(aligned.index[0]),
            "end_date": str(aligned.index[-1]),
            "total_days": len(aligned),
            "n_trades": int(n_trades),
            "total_pnl": float(total_pnl),
            "avg_pnl_per_trade": float(avg_pnl_per_trade),
        },
    }

    logger.info(
        "Backtest complete: trades=%d, total_pnl=$%.0f, avg_per_trade=$%.0f",
        n_trades,
        total_pnl,
        avg_pnl_per_trade,
    )

    return BacktestResult(
        positions=positions_df,
        pnl=pnl_df,
        metadata=metadata,
    )
