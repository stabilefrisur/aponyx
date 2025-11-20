"""
List catalog items command.

Displays available signals, strategies, and datasets.
"""

import logging

import click

from aponyx.models.registry import SignalRegistry
from aponyx.backtest.registry import StrategyRegistry
from aponyx.data.registry import DataRegistry
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
    type=click.Choice(["signals", "strategies", "datasets"], case_sensitive=False),
)
def list_items(item_type: str) -> None:
    """
    List available catalog items.
    
    ITEM_TYPE can be: signals, strategies, or datasets
    
    Examples:
    
        aponyx list signals
        
        aponyx list strategies
        
        aponyx list datasets
    """
    click.echo()
    
    if item_type == "signals":
        registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        signals = registry.list_all()
        
        click.echo("Available Signals:")
        for signal_name, metadata in signals.items():
            click.echo(f"  • {signal_name:<20} — {metadata.description}")
            
    elif item_type == "strategies":
        registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
        strategies = registry.list_all()
        
        click.echo("Available Strategies:")
        for strategy_name, metadata in strategies.items():
            click.echo(f"  • {strategy_name:<20} — {metadata.description}")
            
    elif item_type == "datasets":
        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        datasets = registry.list_datasets()
        
        click.echo("Registered Datasets:")
        for dataset in datasets:
            info = registry.get_dataset_info(dataset)
            instrument = info.get("metadata", {}).get("params", {}).get("security", "unknown")
            click.echo(f"  • {dataset:<30} — {instrument}")
            
    click.echo()
