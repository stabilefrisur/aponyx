"""
Evaluation layer for assessing signal-product relationships.

This layer sits between signal generation and backtesting, providing tools to
evaluate whether signals contain economically and statistically meaningful
information for traded products.
"""

from aponyx.evaluation import suitability

__all__ = ["suitability"]
