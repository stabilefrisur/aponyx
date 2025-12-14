"""
Configuration for backtest engine.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestConfig:
    """
    Backtest parameters and trading constraints.

    Attributes
    ----------
    position_size_mm : float
        Notional position size in millions (e.g., 10.0 = $10MM).
    sizing_mode : str
        Position sizing mode: 'binary' (full position for any non-zero signal)
        or 'proportional' (scaled by signal magnitude).
    stop_loss_pct : float | None
        Stop loss as percentage of initial position value. None to disable.
    take_profit_pct : float | None
        Take profit as percentage of initial position value. None to disable.
    max_holding_days : int | None
        Maximum days to hold a position before forced exit. None for no limit.
    transaction_cost_bps : float
        Round-trip transaction cost in basis points.
        Typical CDX costs: 0.5-2.0 bps depending on liquidity.
    dv01_per_million : float
        DV01 per $1MM notional for risk calculations.
        CDX IG 5Y with ~4.75 year duration: ~475.
    signal_lag : int
        Number of days to lag the signal before execution.
        0 = same-day execution (idealized), 1 = next-day execution (realistic).
        Helps prevent look-ahead bias in backtests.
        Default is 1 for realistic execution timing.

    Notes
    -----
    - Signal-based triggers: non-zero signal = enter, zero signal = exit.
    - Proportional sizing: position scaled by signal magnitude (default).
    - Binary sizing: full position for any non-zero signal (use as runtime override).
    - PnL-based exits (stop loss, take profit) trigger cooldown before re-entry.
    - Transaction costs are applied symmetrically on entry and exit.
    - signal_lag models realistic execution timing and prevents look-ahead bias.
    """

    position_size_mm: float
    sizing_mode: str
    stop_loss_pct: float | None
    take_profit_pct: float | None
    max_holding_days: int | None
    transaction_cost_bps: float
    dv01_per_million: float
    signal_lag: int = 1

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.position_size_mm <= 0:
            raise ValueError(
                f"position_size_mm must be positive, got {self.position_size_mm}"
            )
        if self.sizing_mode not in {"binary", "proportional"}:
            raise ValueError(
                f"sizing_mode must be 'binary' or 'proportional', got '{self.sizing_mode}'"
            )
        if self.stop_loss_pct is not None and not (0 < self.stop_loss_pct <= 100):
            raise ValueError(
                f"stop_loss_pct must be in (0, 100], got {self.stop_loss_pct}"
            )
        if self.take_profit_pct is not None and not (0 < self.take_profit_pct <= 100):
            raise ValueError(
                f"take_profit_pct must be in (0, 100], got {self.take_profit_pct}"
            )
        if self.max_holding_days is not None and self.max_holding_days <= 0:
            raise ValueError(
                f"max_holding_days must be positive, got {self.max_holding_days}"
            )
        if self.transaction_cost_bps < 0:
            raise ValueError(
                f"transaction_cost_bps must be non-negative, got {self.transaction_cost_bps}"
            )
        if self.signal_lag < 0:
            raise ValueError(f"signal_lag must be non-negative, got {self.signal_lag}")
