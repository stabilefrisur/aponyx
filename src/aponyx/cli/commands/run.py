"""
Run workflow command.

Executes research workflows for signal-strategy combinations.
"""

import logging
from pathlib import Path

import click
import yaml

from aponyx.workflows import WorkflowEngine, WorkflowConfig
from aponyx.models.registry import SignalRegistry
from aponyx.config import SIGNAL_CATALOG_PATH

logger = logging.getLogger(__name__)


@click.command(name="run")
@click.option(
    "--signal",
    type=str,
    help="Signal name from signal catalog",
)
@click.option(
    "--strategy",
    type=str,
    help="Strategy name from strategy catalog",
)
@click.option(
    "--product",
    type=str,
    default="cdx_ig_5y",
    help="Product identifier for backtesting (default: cdx_ig_5y)",
)
@click.option(
    "--data",
    type=str,
    default="synthetic",
    help="Data source (default: synthetic). Available: synthetic, file, bloomberg, or any custom source in data/raw/",
)
@click.option(
    "--securities",
    type=str,
    help="Security mapping as 'type1:security1,type2:security2' (e.g., 'cdx:cdx_hy_5y,etf:hyg')",
)
@click.option(
    "--steps",
    type=str,
    help="Comma-separated step list (default: all steps)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-run cached steps; with --data bloomberg, also refreshes current day data from Bloomberg",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Load configuration from YAML file",
)
def run(
    signal: str | None,
    strategy: str | None,
    product: str,
    data: str,
    securities: str | None,
    steps: str | None,
    force: bool,
    config: Path | None,
) -> None:
    """
    Run research workflow for signal-strategy combination.

    Executes full pipeline: data -> signal -> evaluation -> backtest -> visualization.
    Skips completed steps unless --force is specified.

    Configuration can be provided via command-line options or a YAML config file.
    Command-line options override values from config file.

    \b
    Examples:
        # Basic usage
        aponyx run --signal spread_momentum --strategy balanced

        # Bloomberg data source
        aponyx run --signal cdx_vix_gap --strategy aggressive --data bloomberg

        # Custom product
        aponyx run --signal spread_momentum --strategy balanced --product cdx_hy_5y

        # Custom security mapping (run signal with different securities)
        aponyx run --signal cdx_etf_basis --securities cdx:cdx_hy_5y,etf:hyg --strategy balanced

        # Partial pipeline
        aponyx run --signal spread_momentum --strategy balanced --steps data,signal,backtest

        # Force re-run (refreshes Bloomberg data if --data bloomberg)
        aponyx run --signal spread_momentum --strategy balanced --force

        # YAML configuration
        aponyx run --config workflow.yaml
    """
    # Load config from YAML if provided
    config_dict = {}
    if config:
        try:
            with open(config, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f) or {}
            logger.info("Loaded configuration from %s", config)
        except Exception as e:
            click.echo(f"Failed to load config file: {e}", err=True)
            raise click.Abort()

    # Command-line options override config file
    signal_name = signal or config_dict.get("signal")
    strategy_name = strategy or config_dict.get("strategy")
    product_id = product or config_dict.get("product", "cdx_ig_5y")
    data_source = data or config_dict.get("data", "synthetic")
    force_rerun = force or config_dict.get("force", False)

    # Parse security mapping
    security_mapping = None
    if securities:
        try:
            security_mapping = {}
            for pair in securities.split(","):
                inst_type, security_id = pair.split(":")
                security_mapping[inst_type.strip()] = security_id.strip()
        except ValueError:
            click.echo(
                "Error: Invalid --securities format. Use 'type1:security1,type2:security2'",
                err=True,
            )
            raise click.Abort()
    elif "securities" in config_dict:
        security_mapping = config_dict["securities"]

    # Parse steps
    step_list = None
    if steps:
        step_list = [s.strip() for s in steps.split(",")]
    elif "steps" in config_dict:
        step_list = config_dict["steps"]

    # Validate required parameters
    if not signal_name or not strategy_name:
        click.echo("Error: Missing --signal and --strategy", err=True)
        raise click.Abort()

    # Create config
    try:
        workflow_config = WorkflowConfig(
            signal_name=signal_name,
            strategy_name=strategy_name,
            product=product_id,
            data_source=data_source,  # type: ignore
            security_mapping=security_mapping,
            steps=step_list,  # type: ignore
            force_rerun=force_rerun,
        )
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise click.Abort()

    # Get signal metadata to show input instruments and securities
    try:
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        signal_metadata = signal_registry.get_metadata(signal_name)
        
        # Get the securities that will be used (custom mapping or defaults)
        if security_mapping:
            securities_to_use = security_mapping
        else:
            securities_to_use = signal_metadata.default_securities
        
        # Format: instrument1:security1, instrument2:security2, ...
        securities_display = ", ".join(
            f"{inst_type}:{sec}" for inst_type, sec in sorted(securities_to_use.items())
        )
    except Exception:
        securities_display = "unknown"

    # Display workflow config in new format
    click.echo(f"Signal: {signal_name} ({securities_display})")
    click.echo(f"Strategy: {strategy_name}")
    click.echo(f"Product: {product_id}")
    click.echo(f"Data: {data_source}")
    if step_list:
        click.echo(f"Steps: {', '.join(step_list)}")
    else:
        click.echo(f"Steps: all")
    click.echo(f"Force re-run: {force_rerun}")
    click.echo()

    # Execute workflow
    engine = WorkflowEngine(workflow_config)
    results = engine.execute()

    # Display results
    if results["errors"]:
        click.echo(f"Workflow failed: {results['steps_completed']} steps completed", err=True)
        for error in results["errors"]:
            click.echo(f"  {error['step']}: {error['error']}", err=True)
        raise click.Abort()

    click.echo(
        f"Completed {results['steps_completed']} steps in {results['duration_seconds']:.1f}s"
    )
    if results["steps_skipped"] > 0:
        click.echo(f"Skipped {results['steps_skipped']} cached steps")
    click.echo(f"Results: {results['output_dir']}")
