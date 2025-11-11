"""
Protocol definitions for backtest engine extensibility.

These protocols define the interface for swappable backtest components,
allowing easy integration of external libraries (vectorbt, backtrader, etc.)
while maintaining our domain-specific API.
"""

from typing import Protocol

import pandas as pd

from .config import BacktestConfig
from .engine import BacktestResult


class BacktestEngine(Protocol):
    """
    Protocol for backtest engine implementations.

    This allows swapping between our simple implementation and
    more sophisticated libraries while maintaining the same API.

    Examples
    --------
    >>> # Our implementation
    >>> from aponyx.backtest import run_backtest
    >>> result = run_backtest(signal, spread, config)
    >>>
    >>> # Future: vectorbt wrapper
    >>> from aponyx.backtest.adapters import VectorBTEngine
    >>> engine = VectorBTEngine()
    >>> result = engine.run(signal, spread, config)
    """

    def run(
        self,
        composite_signal: pd.Series,
        spread: pd.Series,
        config: BacktestConfig | None = None,
    ) -> BacktestResult:
        """
        Execute backtest on signal and price data.

        Parameters
        ----------
        composite_signal : pd.Series
            Daily positioning scores from signal computation.
        spread : pd.Series
            CDX spread levels aligned to signal dates.
        config : BacktestConfig | None
            Backtest parameters. Uses defaults if None.

        Returns
        -------
        BacktestResult
            Complete backtest results including positions and P&L.
        """
        ...


class PerformanceCalculator(Protocol):
    """
    Protocol for performance metrics calculation.

    Allows swapping between our simple implementation and
    libraries like quantstats, empyrical, pyfolio, etc.

    Examples
    --------
    >>> # Our implementation (now in evaluation.performance)
    >>> from aponyx.evaluation.performance import compute_all_metrics
    >>> metrics = compute_all_metrics(result.pnl, result.positions)
    >>>
    >>> # Future: quantstats wrapper
    >>> from aponyx.backtest.adapters import QuantStatsCalculator
    >>> calc = QuantStatsCalculator()
    >>> metrics = calc.compute(result.pnl, result.positions)
    """

    def compute(
        self,
        pnl_df: pd.DataFrame,
        positions_df: pd.DataFrame,
    ) -> pd.DataFrame | dict:
        """
        Compute performance metrics from backtest results.

        Parameters
        ----------
        pnl_df : pd.DataFrame
            Daily P&L data with 'net_pnl' and 'cumulative_pnl' columns.
        positions_df : pd.DataFrame
            Daily position data with 'position' and 'days_held' columns.

        Returns
        -------
        pd.DataFrame | dict
            Performance statistics. Format may vary by implementation.
        """
        ...
