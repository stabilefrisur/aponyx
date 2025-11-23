"""
List catalog items command.

Displays available signals, strategies, datasets, and workflow steps.
"""

import logging

import click

from aponyx.models.registry import SignalRegistry
from aponyx.backtest.registry import StrategyRegistry
from aponyx.data.registry import DataRegistry
from aponyx.workflows.registry import StepRegistry
from aponyx.config import (
    SIGNAL_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
    REGISTRY_PATH,
    DATA_DIR,
)

logger = logging.getLogger(__name__)


@click.command(name="list")
@click.argument(
    "item_type",
    type=click.Choice(
        ["signals", "strategies", "datasets", "steps"], case_sensitive=False
    ),
)
def list_items(item_type: str) -> None:
    """
    List available catalog items.

    ITEM_TYPE can be: signals, strategies, datasets, or steps

    \b
    Examples:
        aponyx list signals
        aponyx list strategies
        aponyx list datasets
        aponyx list steps
    """
    if item_type == "signals":
        registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        signals = registry.list_all()

        for signal_name, metadata in signals.items():
            click.echo(f"{signal_name:<20} {metadata.description}")

    elif item_type == "strategies":
        registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
        strategies = registry.list_all()

        for strategy_name, metadata in strategies.items():
            click.echo(f"{strategy_name:<20} {metadata.description}")

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
            click.echo(f"{dataset:<30} {instrument:<20} {source}")

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
