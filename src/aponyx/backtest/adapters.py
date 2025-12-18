"""
Protocol interfaces for third-party backtest library integration.

Defines protocols for backtest engines and portfolio simulators,
enabling future integration with vectorbt, bt, or other backtesting
frameworks without modifying core code.
"""

from typing import Protocol

import pandas as pd

from .config import BacktestConfig
from .engine import BacktestResult


class BacktestEngine(Protocol):
    """
    Protocol for backtest execution engines.

    Defines interface for running backtests from signal data.
    Enables integration with third-party libraries like vectorbt
    or custom simulation engines.

    Examples
    --------
    >>> class VectorBTAdapter:
    ...     def run(
    ...         self,
    ...         signal: pd.Series,
    ...         spread: pd.Series,
    ...         config: BacktestConfig | None = None,
    ...     ) -> BacktestResult:
    ...         import vectorbt as vbt
    ...         # Entry when signal exceeds threshold (or any non-zero if no threshold)
    ...         if config.entry_threshold is not None:
    ...             entries = signal.abs() >= config.entry_threshold
    ...         else:
    ...             entries = signal != 0
    ...         # Exit when signal returns to zero (via signal transformation's neutral_range)
    ...         exits = signal == 0
    ...         portfolio = vbt.Portfolio.from_signals(
    ...             close=spread,
    ...             entries=entries,
    ...             exits=exits,
    ...             size=config.position_size_mm,
    ...             fees=config.transaction_cost_bps / 10000,
    ...         )
    ...         # Convert vectorbt results to BacktestResult
    ...         return BacktestResult(...)
    """

    def run(
        self,
        signal: pd.Series,
        spread: pd.Series,
        config: BacktestConfig | None = None,
    ) -> BacktestResult:
        """
        Execute backtest from signal data.

        Parameters
        ----------
        signal : pd.Series
            Trading signal with DatetimeIndex.
        spread : pd.Series
            Market spread data with DatetimeIndex.
        config : BacktestConfig | None
            Backtest configuration parameters.

        Returns
        -------
        BacktestResult
            Standardized backtest results.
        """
        ...


# Future adapter implementations:
# - VectorBTBacktestEngine
# - ZiplineBacktestEngine
# - CustomEventDrivenEngine
