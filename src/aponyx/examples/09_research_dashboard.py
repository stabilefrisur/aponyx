"""
Generate research dashboard from completed workflow results.

Prerequisites
-------------
Completed workflow run with:
- metadata.json: Workflow configuration and signal info
- signal.parquet: Signal time series
- positions.parquet: Position series from backtest (optional)
- pnl.parquet: P&L series from backtest (optional)

Outputs
-------
- Interactive 5-panel research dashboard (HTML export)
- Displays signal pipeline stages alongside traded product

Usage
-----
Run from project root:
    python -m aponyx.examples.09_research_dashboard

Or specify workflow directory:
    python -m aponyx.examples.09_research_dashboard data/workflows/my_workflow/

Examples
--------
>>> from aponyx.examples import generate_research_dashboard
>>> fig = generate_research_dashboard("data/workflows/test_workflow_20251214_215911/")
>>> fig.show()  # Interactive display
>>> fig.write_html("dashboard.html")  # Export to file
"""

import json
import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from aponyx.config import (
    DATA_DIR,
    DATA_WORKFLOWS_DIR,
    INDICATOR_TRANSFORMATION_PATH,
    REGISTRY_PATH,
    SCORE_TRANSFORMATION_PATH,
    SIGNAL_CATALOG_PATH,
    SIGNAL_TRANSFORMATION_PATH,
)
from aponyx.data import DataRegistry, FileSource, fetch_cdx, fetch_etf, fetch_vix
from aponyx.models import (
    IndicatorTransformationRegistry,
    ScoreTransformationRegistry,
    SignalRegistry,
    SignalTransformationRegistry,
)
from aponyx.models.signal_composer import compose_signal
from aponyx.persistence import load_parquet
from aponyx.visualization import plot_research_dashboard

logger = logging.getLogger(__name__)


def main() -> go.Figure | None:
    """
    Execute research dashboard generation workflow.

    Loads workflow results and generates 5-panel research dashboard.

    Returns
    -------
    go.Figure or None
        Dashboard figure if successful, None if workflow not found.

    Notes
    -----
    Uses most recent workflow if no argument provided.
    Pass workflow directory as command-line argument to specify.
    """
    # Get workflow directory from command line or find most recent
    if len(sys.argv) > 1:
        workflow_dir = Path(sys.argv[1])
    else:
        workflow_dir = find_most_recent_workflow()

    if workflow_dir is None:
        logger.warning("No workflow found in %s", DATA_WORKFLOWS_DIR)
        print("No workflow found. Run a workflow first.")
        return None

    print(f"Loading workflow: {workflow_dir.name}")
    return generate_and_save_dashboard(workflow_dir)


def find_most_recent_workflow() -> Path | None:
    """
    Find most recent workflow directory.

    Returns
    -------
    Path or None
        Path to most recent workflow directory, or None if none found.

    Notes
    -----
    Searches DATA_WORKFLOWS_DIR for directories with metadata.json.
    Returns most recently modified directory.
    """
    if not DATA_WORKFLOWS_DIR.exists():
        return None

    workflows = []
    for item in DATA_WORKFLOWS_DIR.iterdir():
        if item.is_dir() and (item / "metadata.json").exists():
            workflows.append(item)

    if not workflows:
        return None

    # Sort by modification time, most recent first
    workflows.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return workflows[0]


def load_workflow_metadata(workflow_dir: Path) -> dict:
    """
    Load workflow metadata from metadata.json.

    Parameters
    ----------
    workflow_dir : Path
        Path to workflow directory.

    Returns
    -------
    dict
        Workflow metadata including signal, product, strategy, etc.

    Raises
    ------
    FileNotFoundError
        If metadata.json not found in workflow directory.
    ValueError
        If required fields missing from metadata.
    """
    metadata_path = workflow_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Validate required fields
    required_fields = ["signal", "product"]
    missing = [f for f in required_fields if f not in metadata]
    if missing:
        raise ValueError(f"Missing required metadata fields: {missing}")

    return metadata


def load_market_data_for_signal(
    signal_name: str,
    indicator_registry: IndicatorTransformationRegistry,
    signal_registry: SignalRegistry,
    data_source_path: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Load market data required for signal computation.

    Parameters
    ----------
    signal_name : str
        Signal identifier.
    indicator_registry : IndicatorTransformationRegistry
        Registry for indicator metadata.
    signal_registry : SignalRegistry
        Registry for signal metadata.
    data_source_path : Path or None, optional
        Path to data source directory. Uses default if None.

    Returns
    -------
    dict[str, pd.DataFrame]
        Market data keyed by instrument type (cdx, vix, etf, etc.).

    Notes
    -----
    Determines required securities from signal and indicator metadata.
    Loads data using FileSource provider pattern.
    """
    # Get signal and indicator metadata
    signal_metadata = signal_registry.get_metadata(signal_name)
    indicator_name = signal_metadata.indicator_transformation
    indicator_metadata = indicator_registry.get_metadata(indicator_name)

    # Determine data source
    if data_source_path is not None:
        source = FileSource(data_source_path)
    else:
        # Try synthetic data first
        synthetic_path = DATA_DIR / "raw" / "synthetic"
        if synthetic_path.exists() and (synthetic_path / "registry.json").exists():
            source = FileSource(synthetic_path)
        else:
            # Fall back to DataRegistry
            registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
            market_data = {}
            for inst_type, security in indicator_metadata.default_securities.items():
                df = registry.load_dataset_by_security(security)
                if df is not None:
                    market_data[inst_type] = df
            return market_data

    # Load data using fetch functions
    market_data = {}
    for inst_type, security in indicator_metadata.default_securities.items():
        logger.debug("Loading %s data: security=%s", inst_type, security)
        if inst_type == "cdx":
            market_data[inst_type] = fetch_cdx(source, security=security)
        elif inst_type == "vix":
            market_data[inst_type] = fetch_vix(source, security=security)
        elif inst_type == "etf":
            market_data[inst_type] = fetch_etf(source, security=security)
        else:
            logger.warning("Unknown instrument type: %s", inst_type)

    return market_data


def recompute_signal_with_intermediates(
    signal_name: str,
    market_data: dict[str, pd.DataFrame],
    indicator_registry: IndicatorTransformationRegistry,
    score_registry: ScoreTransformationRegistry,
    signal_transformation_registry: SignalTransformationRegistry,
    signal_registry: SignalRegistry,
    *,
    indicator_transformation_override: str | None = None,
    score_transformation_override: str | None = None,
    signal_transformation_override: str | None = None,
) -> dict[str, pd.Series]:
    """
    Recompute signal with intermediate stage outputs.

    Parameters
    ----------
    signal_name : str
        Signal identifier.
    market_data : dict[str, pd.DataFrame]
        Market data keyed by instrument type.
    indicator_registry : IndicatorTransformationRegistry
        Registry for indicator metadata.
    score_registry : ScoreTransformationRegistry
        Registry for score transformation metadata.
    signal_transformation_registry : SignalTransformationRegistry
        Registry for signal transformation metadata.
    signal_registry : SignalRegistry
        Registry for signal metadata.
    indicator_transformation_override : str or None, optional
        Override indicator transformation from catalog.
    score_transformation_override : str or None, optional
        Override score transformation from catalog.
    signal_transformation_override : str or None, optional
        Override signal transformation from catalog.

    Returns
    -------
    dict[str, pd.Series]
        Dict with keys: indicator, score, signal.

    Notes
    -----
    Uses compose_signal with include_intermediates=True.
    """
    result = compose_signal(
        signal_name=signal_name,
        market_data=market_data,
        indicator_registry=indicator_registry,
        score_registry=score_registry,
        signal_transformation_registry=signal_transformation_registry,
        signal_registry=signal_registry,
        indicator_transformation_override=indicator_transformation_override,
        score_transformation_override=score_transformation_override,
        signal_transformation_override=signal_transformation_override,
        include_intermediates=True,
    )
    return result


def load_backtest_results(workflow_dir: Path) -> tuple[pd.Series, pd.Series]:
    """
    Load positions and P&L from backtest results.

    Parameters
    ----------
    workflow_dir : Path
        Path to workflow directory.

    Returns
    -------
    tuple[pd.Series, pd.Series]
        Positions series and P&L series.

    Notes
    -----
    If backtest files not found, returns synthetic placeholder series.
    Checks both root directory and backtest/ subdirectory.
    """
    # Check possible locations for backtest results
    possible_backtest_dirs = [
        workflow_dir,
        workflow_dir / "backtest",
    ]

    positions_df = None
    pnl_df = None

    for backtest_dir in possible_backtest_dirs:
        positions_path = backtest_dir / "positions.parquet"
        pnl_path = backtest_dir / "pnl.parquet"

        if positions_path.exists() and pnl_path.exists():
            positions_df = load_parquet(positions_path)
            pnl_df = load_parquet(pnl_path)
            break

    if positions_df is not None and pnl_df is not None:
        positions = (
            positions_df["position"]
            if "position" in positions_df.columns
            else positions_df.iloc[:, 0]
        )
        pnl = pnl_df["net_pnl"] if "net_pnl" in pnl_df.columns else pnl_df.iloc[:, 0]
        return positions, pnl

    # If backtest not run, check for signal file and create placeholder
    possible_signal_dirs = [
        workflow_dir,
        workflow_dir / "signals",
    ]

    for signal_dir in possible_signal_dirs:
        signal_path = signal_dir / "signal.parquet"
        if signal_path.exists():
            signal_df = load_parquet(signal_path)
            dates = signal_df.index

            # Create placeholder series
            positions = pd.Series(0.0, index=dates, name="position")
            pnl = pd.Series(0.0, index=dates, name="net_pnl")

            logger.warning(
                "Backtest results not found - using placeholder positions/pnl"
            )
            return positions, pnl

    raise FileNotFoundError(
        f"Neither backtest results nor signal file found in {workflow_dir}"
    )


def generate_and_save_dashboard(workflow_dir: Path) -> go.Figure:
    """
    Generate and save research dashboard for workflow.

    Parameters
    ----------
    workflow_dir : Path
        Path to completed workflow directory.

    Returns
    -------
    go.Figure
        Research dashboard figure.

    Raises
    ------
    FileNotFoundError
        If workflow directory or metadata not found.
    ValueError
        If metadata is invalid.

    Notes
    -----
    Saves dashboard as HTML to workflow directory.
    """
    # Step 1: Load metadata
    metadata = load_workflow_metadata(workflow_dir)
    signal_name = metadata["signal"]
    product = metadata["product"]

    # Extract transformation overrides from metadata (if present)
    indicator_override = metadata.get("indicator_transformation_override")
    score_override = metadata.get("score_transformation_override")
    signal_trans_override = metadata.get("signal_transformation_override")

    print(f"Signal: {signal_name}, Product: {product}")
    if indicator_override:
        print(f"  Indicator override: {indicator_override}")
    if score_override:
        print(f"  Score transformation override: {score_override}")
    if signal_trans_override:
        print(f"  Signal transformation override: {signal_trans_override}")

    # Step 2: Load registries
    indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
    score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
    signal_transformation_registry = SignalTransformationRegistry(
        SIGNAL_TRANSFORMATION_PATH
    )
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

    # Step 3: Load market data
    print("Loading market data...")
    market_data = load_market_data_for_signal(
        signal_name=signal_name,
        indicator_registry=indicator_registry,
        signal_registry=signal_registry,
    )

    # Step 4: Recompute signal with intermediates
    print("Computing signal pipeline stages...")
    signal_result = recompute_signal_with_intermediates(
        signal_name=signal_name,
        market_data=market_data,
        indicator_registry=indicator_registry,
        score_registry=score_registry,
        signal_transformation_registry=signal_transformation_registry,
        signal_registry=signal_registry,
        indicator_transformation_override=indicator_override,
        score_transformation_override=score_override,
        signal_transformation_override=signal_trans_override,
    )

    # Step 5: Load backtest results
    print("Loading backtest results...")
    positions, pnl = load_backtest_results(workflow_dir)

    # Step 6: Get traded product spread
    # Use CDX spread as traded product (most common case)
    if "cdx" in market_data:
        traded_product = market_data["cdx"]["spread"]
    elif "etf" in market_data:
        traded_product = market_data["etf"]["price"]
    else:
        # Fallback: use first available series
        first_key = next(iter(market_data.keys()))
        first_col = market_data[first_key].columns[0]
        traded_product = market_data[first_key][first_col]

    # Step 7: Generate dashboard
    print("Generating dashboard...")
    fig = plot_research_dashboard(
        traded_product=traded_product,
        indicator=signal_result["indicator"],
        score=signal_result["score"],
        signal=signal_result["signal"],
        positions=positions,
        pnl=pnl,
        title=f"Research Dashboard: {signal_name}",
    )

    # Step 8: Save to workflow visualizations directory
    visualizations_dir = workflow_dir / "visualizations"
    visualizations_dir.mkdir(parents=True, exist_ok=True)
    output_path = visualizations_dir / "research_dashboard.html"
    fig.write_html(str(output_path))
    print(f"Dashboard saved: {output_path}")

    return fig


if __name__ == "__main__":
    # Configure logging for example script
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    result = main()
    if result is not None:
        print("Dashboard generated successfully!")
