"""
Performance evaluation module for backtest results.

Provides comprehensive post-backtest analysis including all performance metrics
(basic + extended), subperiod stability, return attribution, and automated reporting.
"""

from .analyzer import analyze_backtest_performance
from .config import PerformanceConfig, PerformanceMetrics, PerformanceResult
from .metrics import compute_all_metrics
from .registry import PerformanceEntry, PerformanceRegistry
from .report import generate_performance_report, save_report

__all__ = [
    "analyze_backtest_performance",
    "PerformanceConfig",
    "PerformanceMetrics",
    "PerformanceResult",
    "PerformanceEntry",
    "PerformanceRegistry",
    "generate_performance_report",
    "save_report",
    "compute_all_metrics",
]
