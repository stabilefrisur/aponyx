"""
Performance evaluation module for backtest results.

Provides comprehensive post-backtest analysis including extended metrics,
subperiod stability, return attribution, and automated reporting.
"""

from .analyzer import analyze_backtest_performance
from .config import PerformanceConfig, PerformanceResult
from .registry import PerformanceEntry, PerformanceRegistry
from .report import generate_performance_report, save_report

__all__ = [
    "analyze_backtest_performance",
    "PerformanceConfig",
    "PerformanceResult",
    "PerformanceEntry",
    "PerformanceRegistry",
    "generate_performance_report",
    "save_report",
]
