"""
Demonstration of visualization layer capabilities.

Shows basic usage patterns for plotting equity curves, signals, and drawdowns.
"""

import logging

import numpy as np
import pandas as pd

from aponyx.visualization import (
    Visualizer,
    plot_drawdown,
    plot_equity_curve,
    plot_signal,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_pnl(n_days: int = 252, seed: int = 42) -> pd.Series:
    """
    Generate synthetic daily P&L for demonstration.

    Parameters
    ----------
    n_days : int, default 252
        Number of trading days to simulate.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    pd.Series
        Daily P&L with DatetimeIndex.
    """
    np.random.seed(seed)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq="D")

    # Synthetic P&L with trend and volatility
    drift = 0.02
    vol = 1.5
    returns = np.random.normal(drift, vol, n_days)

    # Add regime change midway
    returns[n_days // 2 : n_days // 2 + 50] -= 3

    pnl = pd.Series(returns, index=dates, name="daily_pnl")
    return pnl


def generate_sample_signal(n_days: int = 252, seed: int = 42) -> pd.Series:
    """
    Generate synthetic z-score signal for demonstration.

    Parameters
    ----------
    n_days : int, default 252
        Number of observations.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    pd.Series
        Z-score normalized signal.
    """
    np.random.seed(seed)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq="D")

    # Mean-reverting signal around zero
    signal = np.random.normal(0, 1, n_days)
    signal = pd.Series(signal, index=dates, name="momentum_signal")

    # Add autocorrelation
    signal = signal.rolling(5).mean().fillna(0)

    return signal


def demo_functional_interface() -> None:
    """Demonstrate functional plotting interface."""
    logger.info("=== Functional Interface Demo ===")

    # Generate sample data
    pnl = generate_sample_pnl()
    signal = generate_sample_signal()

    # Equity curve
    fig_equity = plot_equity_curve(
        pnl,
        title="Sample Strategy Equity Curve",
        show_drawdown_shading=True,
    )
    logger.info("Generated equity curve plot")

    # Signal plot with thresholds
    fig_signal = plot_signal(
        signal,
        title="Momentum Signal (Z-Score)",
        threshold_lines=[-2, 2],
    )
    logger.info("Generated signal plot")

    # Drawdown plot
    fig_drawdown = plot_drawdown(
        pnl,
        title="Strategy Drawdown",
        show_underwater_chart=True,
    )
    logger.info("Generated drawdown plot")

    # Note: Figures are returned but not shown
    # In Jupyter: fig_equity.show()
    # In Streamlit: st.plotly_chart(fig_equity)
    logger.info("Plots ready for rendering (not displayed in script mode)")


def demo_visualizer_class() -> None:
    """Demonstrate object-oriented Visualizer interface."""
    logger.info("=== Visualizer Class Demo ===")

    # Initialize visualizer with custom theme
    viz = Visualizer(theme="plotly_white")

    # Generate sample data
    pnl = generate_sample_pnl(n_days=365)
    signal = generate_sample_signal(n_days=365)

    # Use visualizer methods
    fig_equity = viz.equity_curve(
        pnl,
        title="Annual Strategy Performance",
        show_drawdown_shading=False,
    )
    logger.info("Generated equity curve via Visualizer")

    fig_signal = viz.signal(
        signal,
        title="Signal Evolution",
        threshold_lines=[-1.5, 1.5],
    )
    logger.info("Generated signal plot via Visualizer")

    fig_drawdown = viz.drawdown(
        pnl,
        title="Underwater Equity",
        show_underwater_chart=True,
    )
    logger.info("Generated drawdown plot via Visualizer")

    # Future: viz.attribution(...), viz.dashboard(...)
    logger.info("Visualizer class ready for future extensions")


def demo_integration_patterns() -> None:
    """Show common integration patterns."""
    logger.info("=== Integration Patterns Demo ===")

    pnl = generate_sample_pnl()

    # Pattern 1: Jupyter notebook
    logger.info("Jupyter pattern: fig = plot_equity_curve(pnl); fig.show()")

    # Pattern 2: Streamlit (future)
    logger.info("Streamlit pattern: st.plotly_chart(plot_equity_curve(pnl))")

    # Pattern 3: Export to HTML
    fig = plot_equity_curve(pnl)
    # fig.write_html("equity_curve.html")
    logger.info("Export pattern: fig.write_html('output.html')")

    # Pattern 4: Batch visualization
    viz = Visualizer(theme="plotly_dark")
    # for strategy in strategies:
    #     fig = viz.equity_curve(strategy.pnl)
    #     fig.write_html(f"{strategy.name}.html")
    logger.info("Batch pattern: iterate and export with Visualizer")


def main() -> None:
    """Run all visualization demonstrations."""
    logger.info("Starting visualization layer demo\n")

    demo_functional_interface()
    print()

    demo_visualizer_class()
    print()

    demo_integration_patterns()
    print()

    logger.info("Demo complete. Plots generated but not displayed in script mode.")
    logger.info("To view interactively, run cells in Jupyter or use fig.show()")


if __name__ == "__main__":
    main()
