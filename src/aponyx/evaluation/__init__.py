"""
Evaluation layer for assessing signal-product relationships and backtest performance.

This layer provides:
- Suitability evaluation: Pre-backtest assessment of signal-product pairs
- Performance evaluation: Post-backtest analysis of strategy results
"""

from aponyx.evaluation import performance, suitability

__all__ = ["suitability", "performance"]
