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
@click.option(
    "--max",
    "max_combinations",
    type=int,
    default=None,
    help="Override max_combinations from config.",
)
@click.option(
    "--top",
    type=int,
    default=None,
    help="Show top N results sorted by metric after completion.",
)
@click.option(
    "--sort-by",
    type=str,
    default="sharpe_ratio",
    help="Metric to sort results by (default: sharpe_ratio).",
)
def sweep(
    config_path: Path,
    dry_run: bool,
    max_combinations: int | None,
    top: int | None,
    sort_by: str,
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

        # Limit combinations
        aponyx sweep examples/sweep_lookback.yaml --max 10

        # Show top 5 results sorted by Sharpe
        aponyx sweep examples/sweep_lookback.yaml --top 5 --sort-by sharpe_ratio
    """
    from aponyx.sweep import load_sweep_config, run_sweep
    from aponyx.sweep.config import SweepConfig

    # Load configuration
    try:
        config = load_sweep_config(config_path)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except ValueError as e:
        raise click.ClickException(f"Invalid sweep configuration: {e}")

    # Apply max_combinations override if specified
    if max_combinations is not None:
        config = SweepConfig(
            name=config.name,
            description=config.description,
            mode=config.mode,
            base=config.base,
            parameters=config.parameters,
            max_combinations=max_combinations,
        )
        click.echo(f"Override: max_combinations={max_combinations}")

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

    # Display top results if requested
    if top is not None and not dry_run:
        _display_top_results(result.results_df, sort_by, top)


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
    click.echo(f"Name:        {config.name}")
    click.echo(f"Description: {config.description}")
    click.echo(f"Mode:        {config.mode}")
    click.echo(f"Signal:      {config.base.signal}")
    if config.base.strategy:
        click.echo(f"Strategy:    {config.base.strategy}")

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


def _display_top_results(
    results_df: Any,
    sort_by: str,
    limit: int,
) -> None:
    """Display top results table."""
    import pandas as pd
    from aponyx.sweep.results import get_top_results

    try:
        top_df = get_top_results(results_df, sort_by=sort_by, limit=limit)
    except KeyError as e:
        click.echo(f"\nWarning: {e}", err=True)
        return

    if len(top_df) == 0:
        click.echo("\nNo successful results to display.")
        return

    click.echo(f"\n=== Top {limit} Results (sorted by {sort_by}) ===")

    # Format and display as table
    # Select relevant columns for display
    display_cols = ["combination_id"]

    # Add parameter columns (those with dots in name)
    param_cols = [c for c in top_df.columns if "." in c]
    display_cols.extend(param_cols)

    # Add metric columns
    metric_cols = [
        "sharpe_ratio",
        "max_drawdown",
        "hit_rate",
        "n_trades",
        "annualized_return",
        "mean",
        "std",
        "skewness",
        "kurtosis",
        "autocorr_1",
        "correlation_to_product",
    ]
    display_cols.extend([c for c in metric_cols if c in top_df.columns])

    # Create display DataFrame
    display_df = top_df[[c for c in display_cols if c in top_df.columns]]

    # Format numeric columns
    pd.set_option("display.float_format", lambda x: f"{x:.4f}")
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 200)

    click.echo(display_df.to_string(index=False))
