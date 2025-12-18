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
        Static transaction cost in basis points per trade.
        Used when transaction_cost_pct is None.
        For CDX IG 5Y with typical spread ~60bps: 2.5% × 60 ≈ 1.5bps.
    transaction_cost_pct : float | None
        Dynamic transaction cost as percentage of current spread.
        Industry standard: 0.025 (2.5%) for CDX indices.
        When set, overrides transaction_cost_bps with spread-dependent costs.
        Cost = transaction_cost_pct × current_spread × notional_mm × 100.
    dv01_per_million : float
        DV01 per $1MM notional for risk calculations.
        CDX IG 5Y with ~4.75 year duration: ~475.
    signal_lag : int
        Number of days to lag the signal before execution.
        0 = same-day execution (idealized), 1 = next-day execution (realistic).
        Helps prevent look-ahead bias in backtests.
        Default is 1 for realistic execution timing.
    entry_threshold : float | None
        Minimum absolute signal value required to enter a position.
        Only signals with |signal| >= entry_threshold trigger entry.
        Should be wider than neutral_range in signal transformation to allow
        reversion signals to run before exiting.
        None = any non-zero signal triggers entry (legacy behavior).

    Notes
    -----
    - Signal-based triggers: non-zero signal = enter, zero signal = exit.
    - Proportional sizing: position scaled by signal magnitude (default).
    - Binary sizing: full position for any non-zero signal (use as runtime override).
    - PnL-based exits (stop loss, take profit) trigger cooldown before re-entry.
    - Transaction costs are applied symmetrically on entry and exit.
    - signal_lag models realistic execution timing and prevents look-ahead bias.
    - entry_threshold creates asymmetric entry/exit: enter at extremes, exit at neutral.

    Transaction Cost Modes
    ----------------------
    - **Static mode** (transaction_cost_pct=None): Uses fixed transaction_cost_bps.
      Pre-calibrate as: 0.025 × typical_spread (e.g., 0.025 × 60bp = 1.5bp).
    - **Dynamic mode** (transaction_cost_pct set): Uses percentage of current spread.
      Industry standard is 2.5% (0.025) per UBS Credit Beta methodology.

    Entry/Exit Asymmetry
    --------------------
    For mean-reversion strategies, entry_threshold should be wider than the
    signal's neutral_range. Example:
    - entry_threshold=1.8: Only enter when |signal| >= 1.8
    - neutral_range=[-0.5, 0.5]: Exit when signal enters this zone
    This allows the reversion to run before closing the trade.

    Examples
    --------
    >>> # Static mode: pre-calibrated 1.5bps for typical 60bp spread
    >>> config = BacktestConfig(..., transaction_cost_bps=1.5, transaction_cost_pct=None)

    >>> # Dynamic mode: 2.5% of current spread
    >>> config = BacktestConfig(..., transaction_cost_bps=0.0, transaction_cost_pct=0.025)

    >>> # Entry threshold for reversion strategy
    >>> config = BacktestConfig(..., entry_threshold=1.8)  # Enter at extremes only
    """

    position_size_mm: float
    sizing_mode: str
    stop_loss_pct: float | None
    take_profit_pct: float | None
    max_holding_days: int | None
    transaction_cost_bps: float
    dv01_per_million: float
    signal_lag: int = 1
    transaction_cost_pct: float | None = None
    entry_threshold: float | None = None

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
        if self.transaction_cost_pct is not None and not (
            0 < self.transaction_cost_pct <= 1
        ):
            raise ValueError(
                f"transaction_cost_pct must be in (0, 1], got {self.transaction_cost_pct}"
            )
        if self.signal_lag < 0:
            raise ValueError(f"signal_lag must be non-negative, got {self.signal_lag}")
        if self.entry_threshold is not None and self.entry_threshold <= 0:
            raise ValueError(
                f"entry_threshold must be positive, got {self.entry_threshold}"
            )
