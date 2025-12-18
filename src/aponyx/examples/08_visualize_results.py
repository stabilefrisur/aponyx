"""
Generate visualization charts for backtest results.

Prerequisites
-------------
Completed workflow run with saved results:
- signals/indicator.parquet: Indicator time series
- signals/score.parquet: Score time series
- signals/signal.parquet: Signal time series
- backtest/pnl.parquet: P&L series
- backtest/positions.parquet: Position series

OR legacy backtest results from 06_run_backtest.py:
- data/workflows/backtests/{signal}_{strategy}_pnl.parquet
- data/workflows/backtests/{signal}_{strategy}_positions.parquet

Outputs
-------
Four Plotly figure objects:
- Equity curve: cumulative P&L over time
- Drawdown chart: underwater equity visualization
- Signal plot: time series of signal values with thresholds
- Research dashboard: 5-panel view of full signal pipeline

Examples
--------
Run from project root with workflow directory:
    python -m aponyx.examples.08_visualize_results data/workflows/test_workflow_20251218_123456/

Or run with defaults (uses legacy backtest path):
    python -m aponyx.examples.08_visualize_results

Expected output: Four interactive Plotly charts displayed or saved.
Figures can be rendered in notebooks, Streamlit apps, or exported to HTML.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from aponyx.config import DATA_DIR, DATA_WORKFLOWS_DIR
from aponyx.persistence import load_parquet
from aponyx.visualization import (
    plot_drawdown,
    plot_equity_curve,
    plot_research_dashboard,
    plot_signal,
)


def main() -> dict[str, go.Figure]:
    """
    Execute visualization workflow.

    Loads workflow or backtest results and generates visualization charts
    including equity curve, drawdown, signal, and research dashboard.

    Returns
    -------
    dict[str, go.Figure]
        Dictionary of figure names to Plotly figure objects.

    Notes
    -----
    If workflow directory provided as argument, loads from workflow structure.
    Otherwise falls back to legacy backtest path.

    Figures are returned for flexible rendering (Streamlit, Jupyter, HTML).
    To display in Jupyter: fig.show()
    To save to HTML: fig.write_html("output.html")
    To display in Streamlit: st.plotly_chart(fig)
    """
    # Check for workflow directory argument
    if len(sys.argv) > 1:
        workflow_dir = Path(sys.argv[1])
        return generate_from_workflow(workflow_dir)

    # Fall back to legacy behavior
    signal_name, strategy_name = define_visualization_parameters()
    pnl, positions = load_backtest_data(signal_name, strategy_name)
    return generate_all_charts(pnl, positions, signal_name, strategy_name)


def generate_from_workflow(workflow_dir: Path) -> dict[str, go.Figure]:
    """
    Generate all visualizations from a completed workflow directory.

    Parameters
    ----------
    workflow_dir : Path
        Path to workflow directory containing signals/ and backtest/ folders.

    Returns
    -------
    dict[str, go.Figure]
        Dictionary with keys: equity_curve, drawdown, signal, research_dashboard.

    Notes
    -----
    Loads saved intermediates (indicator, score, signal) and backtest results
    to generate full research dashboard alongside standard charts.
    """
    # Load metadata for signal/strategy names
    metadata_path = workflow_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    signal_name = metadata["signal"]
    strategy_name = metadata.get("strategy", "unknown")
    product = metadata["product"]

    # Load signal intermediates
    signals_dir = workflow_dir / "signals"
    indicator = load_parquet(signals_dir / "indicator.parquet")["value"]
    score = load_parquet(signals_dir / "score.parquet")["value"]
    signal = load_parquet(signals_dir / "signal.parquet")["value"]

    # Load backtest results
    backtest_dir = workflow_dir / "backtest"
    pnl_df = load_parquet(backtest_dir / "pnl.parquet")
    positions_df = load_parquet(backtest_dir / "positions.parquet")

    pnl = pnl_df["net_pnl"]
    positions = positions_df["position"]

    # Load traded product spread from raw data
    synthetic_path = DATA_DIR / "raw" / "synthetic"
    traded_product_path = synthetic_path / f"{product}.parquet"
    if traded_product_path.exists():
        traded_product_df = load_parquet(traded_product_path)
        traded_product = traded_product_df["spread"]
    else:
        # Fallback: use indicator as placeholder (shouldn't happen normally)
        traded_product = indicator

    # Generate all charts
    figures = {}
    title_prefix = f"{signal_name} ({strategy_name})"

    figures["equity_curve"] = plot_equity_curve(
        pnl,
        title=f"Equity Curve: {title_prefix}",
        show_drawdown_shading=True,
    )

    figures["drawdown"] = plot_drawdown(
        pnl,
        title=f"Drawdown: {title_prefix}",
    )

    figures["signal"] = plot_signal(
        signal,
        title=f"Signal: {signal_name}",
        threshold_lines=[-2.0, 2.0],
    )

    figures["research_dashboard"] = plot_research_dashboard(
        traded_product=traded_product,
        indicator=indicator,
        score=score,
        signal=signal,
        positions=positions,
        pnl=pnl,
        title=f"Research Dashboard: {signal_name}",
    )

    return figures


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
    backtests_dir = DATA_WORKFLOWS_DIR / "backtests"

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
