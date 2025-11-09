"""
Protocol interfaces for third-party analytics library integration.

Defines protocols for performance analyzers and attribution engines,
enabling future integration with QuantStats, vectorbt, or other
performance analytics frameworks without modifying core code.
"""

from typing import Any, Protocol

import pandas as pd


class PerformanceAnalyzer(Protocol):
    """
    Protocol for performance analysis engines.

    Defines interface for computing comprehensive performance metrics
    from backtest results. Enables integration with third-party libraries
    like QuantStats or custom analytics engines.

    Examples
    --------
    >>> class QuantStatsAdapter:
    ...     def analyze(self, returns: pd.Series, benchmark: pd.Series | None = None) -> dict[str, Any]:
    ...         import quantstats as qs
    ...         return {
    ...             'sharpe': qs.stats.sharpe(returns),
    ...             'sortino': qs.stats.sortino(returns),
    ...             'max_dd': qs.stats.max_drawdown(returns),
    ...             # ... other QuantStats metrics
    ...         }
    """

    def analyze(
        self,
        returns: pd.Series,
        benchmark: pd.Series | None = None,
    ) -> dict[str, Any]:
        """
        Analyze performance of return series.

        Parameters
        ----------
        returns : pd.Series
            Daily return series with DatetimeIndex.
        benchmark : pd.Series | None
            Optional benchmark returns for relative metrics.

        Returns
        -------
        dict[str, Any]
            Performance metrics dictionary.
        """
        ...


class AttributionEngine(Protocol):
    """
    Protocol for return attribution engines.

    Defines interface for decomposing returns by various factors.
    Enables integration with third-party attribution frameworks or
    custom multi-factor attribution engines.

    Examples
    --------
    >>> class FactorAttributionAdapter:
    ...     def attribute(
    ...         self,
    ...         returns: pd.Series,
    ...         factors: pd.DataFrame,
    ...     ) -> dict[str, dict[str, float]]:
    ...         # Factor-based attribution logic
    ...         return {
    ...             'factor_exposures': {...},
    ...             'factor_returns': {...},
    ...             'residual': {...},
    ...         }
    """

    def attribute(
        self,
        returns: pd.Series,
        factors: pd.DataFrame,
    ) -> dict[str, dict[str, float]]:
        """
        Attribute returns to factor exposures.

        Parameters
        ----------
        returns : pd.Series
            Daily return series with DatetimeIndex.
        factors : pd.DataFrame
            Factor exposure DataFrame (rows=dates, cols=factors).

        Returns
        -------
        dict[str, dict[str, float]]
            Nested dictionary with attribution results.
        """
        ...


# Future adapter implementations:
# - QuantStatsPerformanceAnalyzer
# - VectorbtPerformanceAnalyzer
# - CustomMultiFactorAttribution
# - RegimeConditionalAttribution
