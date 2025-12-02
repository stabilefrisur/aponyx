"""
List catalog items command.

Displays available signals, products, indicators, transformations, securities,
datasets, strategies, and workflow steps.
"""

import json
import logging
from pathlib import Path

import click

from aponyx.models.registry import (
    SignalRegistry,
    IndicatorRegistry,
    TransformationRegistry,
)
from aponyx.backtest.registry import StrategyRegistry
from aponyx.data.registry import DataRegistry
from aponyx.workflows.registry import StepRegistry
from aponyx.config import (
    SIGNAL_CATALOG_PATH,
    INDICATOR_CATALOG_PATH,
    TRANSFORMATION_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
    BLOOMBERG_SECURITIES_PATH,
    REGISTRY_PATH,
    DATA_DIR,
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
            "transformations",
            "securities",
            "datasets",
            "strategies",
            "steps",
        ],
        case_sensitive=False,
    ),
)
def list_items(item_type: str) -> None:
    """
    List available catalog items.

    ITEM_TYPE can be: signals, products, indicators, transformations,
    securities, datasets, strategies, or steps

    \b
    Examples:
        aponyx list signals
        aponyx list products
        aponyx list indicators
        aponyx list transformations
        aponyx list securities
        aponyx list datasets
        aponyx list strategies
        aponyx list steps
    """
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
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        indicators = registry.list_all()

        for indicator_name, metadata in indicators.items():
            click.echo(f"{indicator_name:<30} {metadata.description}")

    elif item_type == "transformations":
        registry = TransformationRegistry(TRANSFORMATION_CATALOG_PATH)
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
