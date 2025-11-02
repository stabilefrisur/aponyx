"""
Backtesting engine for CDX overlay strategy.

This module provides a lightweight backtesting framework optimized for
credit index strategies. The design prioritizes transparency and extensibility,
with clean interfaces that can wrap more powerful libraries later.

Core Components
---------------
- engine: Position generation and P&L simulation
- metrics: Performance and risk statistics
- config: Backtest parameters and constraints
- protocols: Abstract interfaces for extensibility
"""

from .config import BacktestConfig
from .engine import run_backtest, BacktestResult
from .metrics import compute_performance_metrics, PerformanceMetrics
from .protocols import BacktestEngine, PerformanceCalculator
from .registry import StrategyRegistry, StrategyMetadata

__all__ = [
    "BacktestConfig",
    "run_backtest",
    "BacktestResult",
    "compute_performance_metrics",
    "PerformanceMetrics",
    "BacktestEngine",
    "PerformanceCalculator",
    "StrategyRegistry",
    "StrategyMetadata",
]
