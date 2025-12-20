"""
Sweep CLI command for parameter sensitivity analysis.

Provides the `aponyx sweep` command for running parameter sweeps
defined in YAML configuration files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)


@click.command(name="sweep")
@click.argument(
    "config_path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview combinations without executing evaluations.",
)
def sweep(
    config_path: Path,
    dry_run: bool,
) -> None:
    """
    Run parameter sweep from YAML configuration file.

    Executes parameter sensitivity analysis across indicator or backtest
    configurations. Results are saved to data/sweeps/{name}_{timestamp}/.

    \b
    Examples:
        # Run sweep
        aponyx sweep examples/sweep_lookback.yaml

        # Preview combinations without running
        aponyx sweep examples/sweep_lookback.yaml --dry-run
    """
    from aponyx.sweep import load_sweep_config, run_sweep

    # Load configuration
    try:
        config = load_sweep_config(config_path)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(f"Invalid sweep configuration: {e}")

    # Validate catalog references
    try:
        _validate_sweep_config(config)
    except ValueError as e:
        raise click.ClickException(str(e))

    # Display configuration
    _display_sweep_config(config, dry_run)

    # Run sweep
    try:
        result = run_sweep(config, dry_run=dry_run)
    except KeyboardInterrupt:
        click.echo("\nSweep interrupted by user.")
        raise click.Abort()
    except Exception as e:
        raise click.ClickException(f"Sweep failed: {e}")

    # Display results summary
    _display_sweep_summary(result, dry_run)


def _validate_sweep_config(config: Any) -> None:
    """
    Validate sweep config references against catalogs.

    Parameters
    ----------
    config : SweepConfig
        Sweep configuration to validate.

    Raises
    ------
    ValueError
        If signal or strategy not found in catalogs.
    """
    from aponyx.config import SIGNAL_CATALOG_PATH, STRATEGY_CATALOG_PATH
    from aponyx.models.registry import SignalRegistry
    from aponyx.backtest.registry import StrategyRegistry

    # Validate signal exists
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    if not signal_registry.signal_exists(config.base.signal):
        available = ", ".join(sorted(signal_registry.list_all().keys()))
        raise ValueError(
            f"Signal '{config.base.signal}' not found in catalog.\n"
            f"Available signals: {available}"
        )

    # Validate strategy exists (for backtest mode)
    if config.mode == "backtest" and config.base.strategy:
        strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
        if not strategy_registry.strategy_exists(config.base.strategy):
            available = ", ".join(sorted(strategy_registry.list_all().keys()))
            raise ValueError(
                f"Strategy '{config.base.strategy}' not found in catalog.\n"
                f"Available strategies: {available}"
            )


def _display_sweep_config(config: Any, dry_run: bool) -> None:
    """Display sweep configuration summary."""
    click.echo("=== Sweep Configuration ===")
    click.echo(f"Name:         {config.name}")
    click.echo(f"Description:  {config.description}")
    click.echo(f"Mode:         {config.mode}")
    click.echo(f"Signal:       {config.base.signal}")
    if config.base.strategy:
        click.echo(f"Strategy:     {config.base.strategy}")

    # Calculate total combinations
    total = 1
    for p in config.parameters:
        total *= len(p.values)

    if config.max_combinations:
        click.echo(f"Combinations: {min(total, config.max_combinations)} (limited from {total})")
    else:
        click.echo(f"Combinations: {total}")

    click.echo("\nParameters:")
    for p in config.parameters:
        click.echo(f"  - {p.path}: {list(p.values)}")

    if dry_run:
        click.echo("\n[DRY RUN - No evaluations will be executed]")

    click.echo("=" * 27)
    click.echo()


def _display_sweep_summary(result: Any, dry_run: bool) -> None:
    """Display sweep execution summary."""
    click.echo()
    click.echo("=== Sweep Summary ===")

    if dry_run:
        click.echo(f"Combinations previewed: {result.summary.total_combinations}")
    else:
        click.echo(f"Total combinations: {result.summary.total_combinations}")
        click.echo(f"Successful:         {result.summary.successful}")
        click.echo(f"Failed:             {result.summary.failed}")
        click.echo(f"Success rate:       {result.summary.success_rate:.1%}")
        click.echo(f"Duration:           {result.summary.duration_seconds:.1f}s")
        click.echo(f"Results saved:      {result.output_dir}")

    click.echo("=" * 21)
