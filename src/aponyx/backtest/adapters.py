"""
Example adapters for third-party backtest libraries.

These stubs demonstrate how to wrap external libraries while maintaining
our domain-specific API. Uncomment and implement when ready to integrate.

Usage
-----
# Uncomment the imports and implementation when ready to use
# from aponyx.backtest.adapters import VectorBTEngine
# engine = VectorBTEngine()
# result = engine.run(signal, spread, config)
"""

# import pandas as pd
# import vectorbt as vbt  # type: ignore
# from ..config import BacktestConfig
# from ..engine import BacktestResult
# from ..protocols import BacktestEngine


# class VectorBTEngine:
#     """
#     Adapter for vectorbt backtesting library.
#
#     Wraps vectorbt's Portfolio class to match our BacktestEngine protocol.
#     Provides access to vectorbt's optimized performance and advanced analytics.
#
#     Examples
#     --------
#     >>> engine = VectorBTEngine()
#     >>> result = engine.run(signal, cdx_spread, config)
#     >>> # Result is still a BacktestResult, but computed via vectorbt
#     """
#
#     def run(
#         self,
#         signal: pd.Series,
#         spread: pd.Series,
#         config: BacktestConfig | None = None,
#     ) -> BacktestResult:
#         """
#         Run backtest using vectorbt.
#
#         Converts our signal/spread data to vectorbt format,
#         executes backtest, and translates results back to BacktestResult.
#         """
#         if config is None:
#             from ..config import BacktestConfig
#             config = BacktestConfig()
#
#         # Convert signal to vectorbt entries/exits
#         entries = signal > config.entry_threshold
#         exits = signal.abs() < config.exit_threshold
#
#         # Run vectorbt portfolio simulation
#         portfolio = vbt.Portfolio.from_signals(
#             close=spread,
#             entries=entries,
#             exits=exits,
#             size=config.position_size,
#             fees=config.transaction_cost_bps / 10000,  # Convert bps to decimal
#         )
#
#         # Convert vectorbt results to our BacktestResult format
#         positions_df = pd.DataFrame({
#             "signal": signal,
#             "position": portfolio.positions.values,
#             "days_held": portfolio.holding_duration.values,
#             "spread": spread,
#         })
#
#         pnl_df = pd.DataFrame({
#             "spread_pnl": portfolio.returns.values,
#             "cost": portfolio.fees.values,
#             "net_pnl": portfolio.returns.values - portfolio.fees.values,
#             "cumulative_pnl": portfolio.cumulative_returns.values,
#         })
#
#         metadata = {
#             "engine": "vectorbt",
#             "config": config.__dict__,
#             "summary": portfolio.stats().to_dict(),
#         }
#
#         return BacktestResult(
#             positions=positions_df,
#             pnl=pnl_df,
#             metadata=metadata,
#         )


# class QuantStatsCalculator:
#     """
#     Adapter for quantstats performance analytics.
#
#     Wraps quantstats to match our PerformanceCalculator protocol.
#     Provides institutional-grade performance attribution and risk metrics.
#
#     Examples
#     --------
#     >>> calc = QuantStatsCalculator()
#     >>> metrics = calc.compute(result.pnl, result.positions)
#     >>> # Returns comprehensive metrics compatible with our framework
#     """
#
#     def compute(
#         self,
#         pnl_df: pd.DataFrame,
#         positions_df: pd.DataFrame,
#     ) -> dict:
#         """
#         Compute metrics using quantstats.
#
#         Converts our P&L data to returns series,
#         computes metrics via quantstats, and returns results.
#         """
#         import quantstats as qs  # type: ignore
#
#         # Convert P&L to returns
#         returns = pnl_df["net_pnl"] / pnl_df["cumulative_pnl"].shift(1).fillna(1)
#
#         # Compute quantstats metrics
#         metrics = {
#             "sharpe": qs.stats.sharpe(returns),
#             "sortino": qs.stats.sortino(returns),
#             "max_drawdown": qs.stats.max_drawdown(returns),
#             "calmar": qs.stats.calmar(returns),
#             "total_return": qs.stats.comp(returns),
#             "win_rate": qs.stats.win_rate(returns),
#             # Add more as needed
#         }
#
#         return metrics
