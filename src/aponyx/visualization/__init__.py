"""
Visualization layer for research framework.

Provides modular plotting interface for backtest results, signals, and risk metrics.
All functions return Plotly figure objects for integration with Streamlit or notebooks.
"""

from .plots import (
    plot_drawdown,
    plot_equity_curve,
    plot_research_dashboard,
    plot_signal,
)
from .visualizer import Visualizer

__all__ = [
    "Visualizer",
    "plot_equity_curve",
    "plot_signal",
    "plot_drawdown",
    "plot_research_dashboard",
]
