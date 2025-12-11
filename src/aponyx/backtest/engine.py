"""
Core backtesting engine for signal-to-position simulation.

This module converts signals into positions and simulates P&L.
Design is intentionally simple to allow easy replacement with external
libraries while maintaining our domain-specific logic.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd

from .config import BacktestConfig

logger = logging.getLogger(__name__)


class PositionState(Enum):
    """
    Internal state machine for position tracking.
    
    States
    ------
    NO_POSITION : No active position, ready to enter
    IN_POSITION : Active position (long or short)
    COOLDOWN : After premature exit, waiting for signal to reset to zero
    """
    NO_POSITION = "no_position"
    IN_POSITION = "in_position"
    COOLDOWN = "cooldown"


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
        - exit_reason: reason for position exit (if applicable)
    pnl : pd.DataFrame
        Daily P&L breakdown with columns:
        - spread_pnl: P&L from spread changes
        - cost: transaction costs
        - net_pnl: total net P&L
        - cumulative_pnl: running total
    metadata : dict
        Backtest configuration and execution details, including exit_counts summary.

    Notes
    -----
    This structure is designed to be easily convertible to formats
    expected by third-party backtest libraries (e.g., vectorbt).
    
    Exit Reasons
    ------------
    - None: No exit (position unchanged or entry)
    - "signal": Signal returned to zero
    - "stop_loss": Stop loss triggered
    - "take_profit": Take profit triggered
    - "max_holding_days": Max holding period reached
    - "reversal": Signal sign changed
    """

    positions: pd.DataFrame
    pnl: pd.DataFrame
    metadata: dict[str, Any]


def run_backtest(
    signal: pd.Series,
    spread: pd.Series,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """
    Run backtest converting signals to positions and computing P&L.

    Parameters
    ----------
    signal : pd.Series
        Daily positioning scores from signal transformation.
        DatetimeIndex with float values. Non-zero = enter, zero = exit.
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
    Position Logic (Signal-Based Triggers):
    - Non-zero signal → Enter position (direction from sign)
    - Zero signal → Exit position
    - PnL-based exits → Cooldown state (no re-entry until signal resets)
    - Sign change → Reversal (exit and enter opposite direction)
    - Binary sizing: full position_size_mm for any non-zero signal

    P&L Calculation:
    - Long position: profit when spreads tighten (P&L = -ΔSpread * DV01)
    - Short position: profit when spreads widen (P&L = ΔSpread * DV01)
    - Transaction costs applied on entry and exit
    - P&L expressed in dollars per $1MM notional

    Risk Management:
    - Stop loss: exit if cumulative_pnl < -stop_loss_pct × position_value / 100
    - Take profit: exit if cumulative_pnl > take_profit_pct × position_value / 100
    - Max holding days: forced exit after specified days
    - Cooldown after PnL exits prevents re-entry until signal returns to zero

    Examples
    --------
    >>> config = BacktestConfig(position_size_mm=10.0, stop_loss_pct=5.0)
    >>> result = run_backtest(signal, cdx_spread, config)
    >>> sharpe = result.pnl['net_pnl'].mean() / result.pnl['net_pnl'].std() * np.sqrt(252)
    """
    if config is None:
        config = BacktestConfig()
    
    # Validate proportional sizing not yet implemented
    if config.sizing_mode == "proportional":
        raise NotImplementedError("Proportional sizing mode not yet implemented")

    logger.info(
        "Starting backtest: dates=%d, sizing_mode=%s, position_size=%.1fMM, signal_lag=%d",
        len(signal),
        config.sizing_mode,
        config.position_size_mm,
        config.signal_lag,
    )

    # Validate inputs
    if not isinstance(signal.index, pd.DatetimeIndex):
        raise ValueError("signal must have DatetimeIndex")
    if not isinstance(spread.index, pd.DatetimeIndex):
        raise ValueError("spread must have DatetimeIndex")

    # Apply signal lag if specified
    if config.signal_lag > 0:
        lagged_signal = signal.shift(config.signal_lag)
    else:
        lagged_signal = signal

    # Align data
    aligned = pd.DataFrame(
        {
            "signal": lagged_signal,
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
    prev_spread = 0.0
    state = PositionState.NO_POSITION
    cumulative_position_pnl = 0.0
    position_entry_value = 0.0
    exit_counts = {
        "signal": 0,
        "stop_loss": 0,
        "take_profit": 0,
        "max_holding_days": 0,
        "reversal": 0,
    }

    for date, row in aligned.iterrows():
        signal_val = row["signal"]
        spread_level = row["spread"]

        # Initialize tracking for this iteration
        entry_cost = 0.0
        exit_cost = 0.0
        exit_reason = None
        
        # Store position before any state changes (for P&L calculation)
        position_before_update = current_position
        prev_spread_before_update = prev_spread

        # Signal-based triggers: non-zero = enter, zero = exit
        signal_is_zero = abs(signal_val) < 1e-9
        
        # Determine new position direction from signal sign
        if not signal_is_zero:
            target_position = 1 if signal_val > 0 else -1
        else:
            target_position = 0

        # State machine logic
        if state == PositionState.NO_POSITION:
            # Ready to enter on non-zero signal
            if not signal_is_zero:
                current_position = target_position
                days_held = 0
                state = PositionState.IN_POSITION
                cumulative_position_pnl = 0.0
                position_entry_value = config.position_size_mm * config.dv01_per_million
                entry_cost = config.transaction_cost_bps * config.position_size_mm * 100
                logger.debug(
                    "Entry: date=%s, signal=%.2f, position=%d",
                    date,
                    signal_val,
                    current_position,
                )
        
        elif state == PositionState.IN_POSITION:
            days_held += 1
            
            # Check PnL-based exits first (before signal exits)
            check_stop_loss = (
                config.stop_loss_pct is not None
                and cumulative_position_pnl < -config.stop_loss_pct * position_entry_value / 100
            )
            check_take_profit = (
                config.take_profit_pct is not None
                and cumulative_position_pnl > config.take_profit_pct * position_entry_value / 100
            )
            check_max_holding = (
                config.max_holding_days is not None
                and days_held >= config.max_holding_days
            )
            
            # Take profit takes precedence over stop loss if both trigger
            if check_take_profit:
                exit_reason = "take_profit"
                exit_cost = config.transaction_cost_bps * config.position_size_mm * 100
                current_position = 0
                days_held = 0
                state = PositionState.COOLDOWN
                exit_counts["take_profit"] += 1
                logger.debug(
                    "Take profit exit: date=%s, cumulative_pnl=%.0f",
                    date,
                    cumulative_position_pnl,
                )
            elif check_stop_loss:
                exit_reason = "stop_loss"
                exit_cost = config.transaction_cost_bps * config.position_size_mm * 100
                current_position = 0
                days_held = 0
                state = PositionState.COOLDOWN
                exit_counts["stop_loss"] += 1
                logger.debug(
                    "Stop loss exit: date=%s, cumulative_pnl=%.0f",
                    date,
                    cumulative_position_pnl,
                )
            elif check_max_holding:
                exit_reason = "max_holding_days"
                exit_cost = config.transaction_cost_bps * config.position_size_mm * 100
                current_position = 0
                days_held = 0
                state = PositionState.COOLDOWN
                exit_counts["max_holding_days"] += 1
                logger.debug(
                    "Max holding days exit: date=%s, days_held=%d",
                    date,
                    days_held,
                )
            # Check signal-based exits
            elif signal_is_zero:
                exit_reason = "signal"
                exit_cost = config.transaction_cost_bps * config.position_size_mm * 100
                current_position = 0
                days_held = 0
                state = PositionState.NO_POSITION
                exit_counts["signal"] += 1
                logger.debug("Signal exit: date=%s, signal=%.2f", date, signal_val)
            # Check for sign reversal
            elif target_position != current_position:
                exit_reason = "reversal"
                exit_cost = config.transaction_cost_bps * config.position_size_mm * 100
                # Exit and immediately enter opposite position
                entry_cost = config.transaction_cost_bps * config.position_size_mm * 100
                current_position = target_position
                days_held = 0
                cumulative_position_pnl = 0.0
                position_entry_value = config.position_size_mm * config.dv01_per_million
                state = PositionState.IN_POSITION
                exit_counts["reversal"] += 1
                logger.debug(
                    "Sign reversal: date=%s, signal=%.2f, new_position=%d",
                    date,
                    signal_val,
                    current_position,
                )
        
        elif state == PositionState.COOLDOWN:
            # Wait for signal to return to zero before allowing new entry
            if signal_is_zero:
                state = PositionState.NO_POSITION
                logger.debug("Cooldown released: date=%s", date)
            # Otherwise stay in cooldown (no action)

        # Calculate incremental P&L for this day
        if position_before_update != 0:
            spread_change = spread_level - prev_spread_before_update
            spread_pnl = (
                -position_before_update
                * spread_change
                * config.dv01_per_million
                * config.position_size_mm
            )
            # Update cumulative position P&L (only when in position)
            cumulative_position_pnl += spread_pnl
        else:
            spread_pnl = 0.0

        total_cost = entry_cost + exit_cost
        net_pnl = spread_pnl - total_cost

        # Update previous spread for next iteration
        prev_spread = spread_level

        # Record position state
        positions.append(
            {
                "date": date,
                "signal": signal_val,
                "position": current_position,
                "days_held": days_held,
                "spread": spread_level,
                "exit_reason": exit_reason,
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
            "position_size_mm": config.position_size_mm,
            "sizing_mode": config.sizing_mode,
            "stop_loss_pct": config.stop_loss_pct,
            "take_profit_pct": config.take_profit_pct,
            "max_holding_days": config.max_holding_days,
            "transaction_cost_bps": config.transaction_cost_bps,
            "dv01_per_million": config.dv01_per_million,
            "signal_lag": config.signal_lag,
        },
        "summary": {
            "start_date": str(aligned.index[0]),
            "end_date": str(aligned.index[-1]),
            "total_days": len(aligned),
            "n_trades": int(n_trades),
            "total_pnl": float(total_pnl),
            "avg_pnl_per_trade": float(avg_pnl_per_trade),
            "exit_counts": exit_counts,
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
