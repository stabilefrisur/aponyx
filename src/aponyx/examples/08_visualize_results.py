"""
Generate visualization charts for backtest results.

Prerequisites
-------------
Backtest results saved from backtest execution (06_run_backtest.py):
- P&L file: data/processed/backtests/{signal}_{strategy}_pnl.parquet
- Positions file: data/processed/backtests/{signal}_{strategy}_positions.parquet

Outputs
-------
Three Plotly figure objects:
- Equity curve: cumulative P&L over time
- Drawdown chart: underwater equity visualization
- Signal plot: time series of signal values with thresholds

Examples
--------
Run from project root:
    python -m aponyx.examples.08_visualize_results

Expected output: Three interactive Plotly charts displayed or saved.
Figures can be rendered in notebooks, Streamlit apps, or exported to HTML.
"""

import pandas as pd
import plotly.graph_objects as go

from aponyx.config import PROCESSED_DIR
from aponyx.persistence import load_parquet
from aponyx.visualization import plot_equity_curve, plot_drawdown, plot_signal


def main() -> dict[str, go.Figure]:
    """
    Execute visualization workflow.

    Loads backtest results and generates three key charts:
    equity curve, drawdown, and signal time series.

    Returns
    -------
    dict[str, go.Figure]
        Dictionary of figure names to Plotly figure objects.

    Notes
    -----
    Figures are returned for flexible rendering (Streamlit, Jupyter, HTML).
    To display in Jupyter: fig.show()
    To save to HTML: fig.write_html("output.html")
    To display in Streamlit: st.plotly_chart(fig)
    """
    signal_name, strategy_name = define_visualization_parameters()
    pnl, positions = load_backtest_data(signal_name, strategy_name)
    return generate_all_charts(pnl, positions, signal_name, strategy_name)


def define_visualization_parameters() -> tuple[str, str]:
    """
    Define visualization parameters.

    Returns
    -------
    tuple[str, str]
        Signal name and strategy name.

    Notes
    -----
    Must match the signal-strategy combination from backtest step.
    """
    signal_name = "spread_momentum"
    strategy_name = "balanced"
    return signal_name, strategy_name


def load_backtest_data(
    signal_name: str,
    strategy_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load P&L and positions from backtest results.

    Parameters
    ----------
    signal_name : str
        Name of signal.
    strategy_name : str
        Name of strategy.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        P&L DataFrame and positions DataFrame.

    Notes
    -----
    Loads data saved by 06_run_backtest.py from processed directory.
    P&L DataFrame contains net_pnl column for equity curve.
    Positions DataFrame contains signal column for signal plot.
    """
    backtests_dir = PROCESSED_DIR / "backtests"

    pnl_path = backtests_dir / f"{signal_name}_{strategy_name}_pnl.parquet"
    positions_path = backtests_dir / f"{signal_name}_{strategy_name}_positions.parquet"

    pnl = load_parquet(pnl_path)
    positions = load_parquet(positions_path)

    return pnl, positions


def generate_all_charts(
    pnl: pd.DataFrame,
    positions: pd.DataFrame,
    signal_name: str,
    strategy_name: str,
) -> dict[str, go.Figure]:
    """
    Generate all visualization charts.

    Parameters
    ----------
    pnl : pd.DataFrame
        P&L data with net_pnl column.
    positions : pd.DataFrame
        Positions data with signal column.
    signal_name : str
        Signal name for titles.
    strategy_name : str
        Strategy name for titles.

    Returns
    -------
    dict[str, go.Figure]
        Dictionary with keys: equity_curve, drawdown, signal.

    Notes
    -----
    Charts are configured for research presentation:
    - Equity curve shows drawdown shading for regime visualization
    - Drawdown uses underwater chart format (absolute dollars)
    - Signal includes ±2 threshold lines for regime boundaries
    """
    figures = {}

    figures["equity_curve"] = create_equity_curve(
        pnl,
        signal_name,
        strategy_name,
    )

    figures["drawdown"] = create_drawdown_chart(
        pnl,
        signal_name,
        strategy_name,
    )

    figures["signal"] = create_signal_chart(
        positions,
        signal_name,
    )

    return figures


def create_equity_curve(
    pnl: pd.DataFrame,
    signal_name: str,
    strategy_name: str,
) -> go.Figure:
    """
    Create equity curve chart with drawdown shading.

    Parameters
    ----------
    pnl : pd.DataFrame
        P&L data with net_pnl column.
    signal_name : str
        Signal name for title.
    strategy_name : str
        Strategy name for title.

    Returns
    -------
    go.Figure
        Plotly equity curve figure.

    Notes
    -----
    Uses net_pnl column for cumulative P&L calculation.
    Drawdown shading highlights underwater periods in red.
    """
    title = f"Equity Curve: {signal_name} ({strategy_name})"
    return plot_equity_curve(
        pnl["net_pnl"],
        title=title,
        show_drawdown_shading=True,
    )


def create_drawdown_chart(
    pnl: pd.DataFrame,
    signal_name: str,
    strategy_name: str,
) -> go.Figure:
    """
    Create drawdown chart showing peak-to-trough decline.

    Parameters
    ----------
    pnl : pd.DataFrame
        P&L data with net_pnl column.
    signal_name : str
        Signal name for title.
    strategy_name : str
        Strategy name for title.

    Returns
    -------
    go.Figure
        Plotly drawdown figure.

    Notes
    -----
    Uses underwater chart format (absolute dollars).
    Drawdown is always non-positive (zero at peaks, negative otherwise).
    """
    title = f"Drawdown: {signal_name} ({strategy_name})"
    return plot_drawdown(
        pnl["net_pnl"],
        title=title,
        show_underwater_chart=True,
    )


def create_signal_chart(
    positions: pd.DataFrame,
    signal_name: str,
) -> go.Figure:
    """
    Create signal time series chart with threshold lines.

    Parameters
    ----------
    positions : pd.DataFrame
        Positions data with signal column.
    signal_name : str
        Signal name for title.

    Returns
    -------
    go.Figure
        Plotly signal figure.

    Notes
    -----
    Threshold lines at ±2 mark typical entry/exit levels.
    Signal convention: positive = long credit risk (buy CDX).
    """
    title = f"Signal: {signal_name}"
    signal = positions["signal"]
    signal.name = signal_name

    return plot_signal(
        signal,
        title=title,
        threshold_lines=[-2.0, 2.0],
    )


if __name__ == "__main__":
    main()
