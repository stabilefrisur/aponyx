"""
List catalog items command.

Displays available signals, products, indicators, transformations, securities,
datasets, strategies, and workflow steps.
"""

import json
import logging

import click

from aponyx.models.registry import (
    SignalRegistry,
    IndicatorTransformationRegistry,
    ScoreTransformationRegistry,
    SignalTransformationRegistry,
)
from aponyx.backtest.registry import StrategyRegistry
from aponyx.data.registry import DataRegistry
from aponyx.workflows.registry import StepRegistry
from aponyx.config import (
    SIGNAL_CATALOG_PATH,
    INDICATOR_TRANSFORMATION_PATH,
    SCORE_TRANSFORMATION_PATH,
    SIGNAL_TRANSFORMATION_PATH,
    STRATEGY_CATALOG_PATH,
    BLOOMBERG_SECURITIES_PATH,
    REGISTRY_PATH,
    DATA_DIR,
    DATA_WORKFLOWS_DIR,
)

logger = logging.getLogger(__name__)


@click.command(name="list")
@click.argument(
    "item_type",
    type=click.Choice(
        [
            "signals",
            "products",
            "indicators",
            "score-transformations",
            "signal-transformations",
            "securities",
            "datasets",
            "strategies",
            "steps",
            "workflows",
        ],
        case_sensitive=False,
    ),
)
@click.option(
    "--signal",
    type=str,
    help="Filter workflows by signal name (workflows only)",
)
@click.option(
    "--product",
    type=str,
    help="Filter workflows by product (workflows only)",
)
@click.option(
    "--strategy",
    type=str,
    help="Filter workflows by strategy name (workflows only)",
)
def list_items(
    item_type: str,
    signal: str | None,
    product: str | None,
    strategy: str | None,
) -> None:
    """
    List available catalog items or workflow results.

    ITEM_TYPE can be: signals, products, indicators, score-transformations,
    signal-transformations, securities, datasets, strategies, steps, or workflows

    \b
    Examples:
        aponyx list signals
        aponyx list indicators
        aponyx list score-transformations
        aponyx list signal-transformations
        aponyx list products
        aponyx list workflows
        aponyx list workflows --signal spread_momentum
        aponyx list workflows --product cdx_ig_5y --strategy balanced
    """
    # Validate that filters only apply to workflows
    if item_type != "workflows" and (signal or product or strategy):
        click.echo(
            "Error: --signal, --product, and --strategy filters only apply to 'workflows'",
            err=True,
        )
        raise click.Abort()

    if item_type == "signals":
        registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        signals = registry.list_all()

        for signal_name, metadata in signals.items():
            click.echo(f"{signal_name:<25} {metadata.description}")

    elif item_type == "products":
        # Products are the tradeable instruments (securities with CDX instrument type)
        with open(BLOOMBERG_SECURITIES_PATH, "r", encoding="utf-8") as f:
            securities = json.load(f)

        products = {
            name: info
            for name, info in securities.items()
            if info.get("instrument_type") == "cdx"
        }

        for product_name, info in products.items():
            desc = info.get("description", "No description")
            click.echo(f"{product_name:<20} {desc}")

    elif item_type == "indicators":
        registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
        indicators = registry.list_all()

        for indicator_name, metadata in indicators.items():
            click.echo(f"{indicator_name:<30} {metadata.description}")

    elif item_type == "score-transformations":
        registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
        transformations = registry.list_all()

        for transform_name, metadata in transformations.items():
            click.echo(f"{transform_name:<25} {metadata.description}")

    elif item_type == "signal-transformations":
        registry = SignalTransformationRegistry(SIGNAL_TRANSFORMATION_PATH)
        transformations = registry.list_all()

        for transform_name, metadata in transformations.items():
            click.echo(f"{transform_name:<25} {metadata.description}")

    elif item_type == "securities":
        # All securities (CDX, ETF, VIX, etc.)
        with open(BLOOMBERG_SECURITIES_PATH, "r", encoding="utf-8") as f:
            securities = json.load(f)

        for security_name, info in securities.items():
            desc = info.get("description", "No description")
            instrument_type = info.get("instrument_type", "unknown")
            click.echo(f"{security_name:<20} {instrument_type:<10} {desc}")

    elif item_type == "datasets":
        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        datasets = registry.list_datasets()

        for dataset in datasets:
            info = registry.get_dataset_info(dataset)
            # Try to get security from params, fall back to instrument type
            params = info.get("metadata", {}).get("params", {})
            instrument = params.get("security") or info.get("instrument", "unknown")
            # Extract source from metadata
            source = info.get("metadata", {}).get("provider", "unknown")
            click.echo(f"{dataset:<40} {instrument:<20} {source}")

    elif item_type == "strategies":
        registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
        strategies = registry.list_all()

        for strategy_name, metadata in strategies.items():
            click.echo(f"{strategy_name:<20} {metadata.description}")

    elif item_type == "steps":
        # Display canonical workflow step order with descriptions
        step_registry = StepRegistry()
        steps = step_registry.get_canonical_order()

        click.echo("Workflow steps (canonical order):\n")
        for i, step_name in enumerate(steps, 1):
            # Get description from step class docstring
            descriptions = {
                "data": "Load/fetch market data from registry or sources",
                "signal": "Compute signal values from market data",
                "suitability": "Evaluate signal-product suitability",
                "backtest": "Run strategy backtest with risk tracking",
                "performance": "Compute extended performance metrics",
                "visualization": "Generate interactive charts",
            }
            desc = descriptions.get(step_name, "No description available")
            click.echo(f"{i}. {step_name:<15} {desc}")

    elif item_type == "workflows":
        from datetime import datetime

        if not DATA_WORKFLOWS_DIR.exists():
            click.echo("No workflows found")
            return

        # Collect all workflow metadata
        workflows = []
        for workflow_dir in DATA_WORKFLOWS_DIR.iterdir():
            if not workflow_dir.is_dir():
                continue

            metadata_path = workflow_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                # Skip workflows without label (old format)
                if "label" not in metadata:
                    continue

                workflows.append(
                    {
                        "dir": workflow_dir,
                        "label": metadata.get("label", "unknown"),
                        "signal": metadata.get("signal", "unknown"),
                        "strategy": metadata.get("strategy", "unknown"),
                        "product": metadata.get("product", "unknown"),
                        "status": metadata.get("status", "unknown"),
                        "timestamp": metadata.get("timestamp", ""),
                    }
                )
            except Exception as e:
                logger.debug("Failed to load metadata from %s: %s", workflow_dir, e)
                continue

        if not workflows:
            click.echo("No workflows found")
            return

        # Apply filters
        if signal:
            workflows = [w for w in workflows if w["signal"] == signal]
        if product:
            workflows = [w for w in workflows if w["product"] == product]
        if strategy:
            workflows = [w for w in workflows if w["strategy"] == strategy]

        if not workflows:
            click.echo("No workflows match the specified filters")
            return

        # Sort by timestamp descending (newest first)
        workflows.sort(key=lambda w: w["timestamp"], reverse=True)

        # Apply limit only if no filters active
        has_filters = bool(signal or product or strategy)
        if not has_filters and len(workflows) > 50:
            workflows_to_show = workflows[:50]
            click.echo(
                f"Showing 50 most recent workflows (of {len(workflows)} total). Use filters to narrow results.\n"
            )
        else:
            workflows_to_show = workflows

        # Display header
        click.echo(
            f"{'IDX':<5} {'LABEL':<25} {'SIGNAL':<20} {'STRATEGY':<15} {'PRODUCT':<15} {'STATUS':<10} {'TIMESTAMP':<20}"
        )
        click.echo("-" * 115)

        # Display workflows
        for idx, workflow in enumerate(workflows_to_show):
            # Parse timestamp for display
            try:
                ts = datetime.fromisoformat(workflow["timestamp"])
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_str = (
                    workflow["timestamp"][:19] if workflow["timestamp"] else "unknown"
                )

            click.echo(
                f"{idx:<5} "
                f"{workflow['label'][:24]:<25} "
                f"{workflow['signal'][:19]:<20} "
                f"{workflow['strategy'][:14]:<15} "
                f"{workflow['product'][:14]:<15} "
                f"{workflow['status']:<10} "
                f"{ts_str}"
            )

        # Show summary
        if has_filters:
            click.echo(
                f"\nShowing {len(workflows_to_show)} workflow(s) matching filters"
            )
        else:
            click.echo(f"\nShowing {len(workflows_to_show)} workflow(s)")

        # Note about indices
        click.echo(
            "\nNote: Indices are ephemeral and change as new workflows are added."
        )
        click.echo("Use workflow label for stable references in report command.")
