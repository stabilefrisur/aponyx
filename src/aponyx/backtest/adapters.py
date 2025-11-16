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
    ...         entries = signal > config.entry_threshold
    ...         exits = signal.abs() < config.exit_threshold
    ...         portfolio = vbt.Portfolio.from_signals(
    ...             close=spread,
    ...             entries=entries,
    ...             exits=exits,
    ...             size=config.position_size,
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
