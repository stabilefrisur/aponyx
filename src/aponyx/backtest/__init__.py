"""
Backtesting engine for CDX overlay strategy.

This module provides a lightweight backtesting framework optimized for
credit index strategies. The design prioritizes transparency and extensibility,
with clean interfaces that can wrap more powerful libraries later.

Core Components
---------------
- engine: Position generation and P&L simulation
- config: Backtest parameters and constraints
- protocols: Abstract interfaces for extensibility
- registry: Strategy catalog management

Note: Performance metrics have been moved to aponyx.evaluation.performance
"""

from .config import BacktestConfig
from .engine import run_backtest, BacktestResult
from .protocols import BacktestEngine, PerformanceCalculator
from .registry import StrategyRegistry, StrategyMetadata

__all__ = [
    "BacktestConfig",
    "run_backtest",
    "BacktestResult",
    "BacktestEngine",
    "PerformanceCalculator",
    "StrategyRegistry",
    "StrategyMetadata",
]
