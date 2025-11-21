"""
Run workflow command.

Executes research workflows for signal-strategy combinations.
"""

import logging
from pathlib import Path

import click
import yaml

from aponyx.workflows import WorkflowEngine, WorkflowConfig

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
    "--data",
    type=click.Choice(["synthetic", "file", "bloomberg"], case_sensitive=False),
    default="synthetic",
    help="Data source (default: synthetic)",
)
@click.option(
    "--steps",
    type=str,
    help="Comma-separated step list (default: all steps)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-run even if cached outputs exist",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Load configuration from YAML file",
)
def run(
    signal: str | None,
    strategy: str | None,
    data: str,
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
    
    Examples:

        aponyx run --signal spread_momentum --strategy balanced

        aponyx run --signal cdx_vix_gap --strategy aggressive --data bloomberg

        aponyx run --signal spread_momentum --strategy balanced --steps data,signal,backtest --force

        aponyx run --config workflow.yaml

        aponyx run --config workflow.yaml --force
    """
    # Load config from YAML if provided
    config_dict = {}
    if config:
        try:
            with open(config, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f) or {}
            logger.info("Loaded configuration from %s", config)
        except Exception as e:
            click.echo(f"❌ Failed to load config file: {e}", err=True)
            raise click.Abort()
    
    # Command-line options override config file
    signal_name = signal or config_dict.get("signal")
    strategy_name = strategy or config_dict.get("strategy")
    data_source = data if data != "synthetic" else config_dict.get("data", "synthetic")
    force_rerun = force or config_dict.get("force", False)
    
    # Parse steps
    step_list = None
    if steps:
        step_list = [s.strip() for s in steps.split(",")]
    elif "steps" in config_dict:
        step_list = config_dict["steps"]
    
    # Validate required parameters
    if not signal_name or not strategy_name:
        click.echo(
            "❌ Missing required parameters: --signal and --strategy (or --config file)",
            err=True,
        )
        raise click.Abort()
        
    # Create config
    try:
        workflow_config = WorkflowConfig(
            signal_name=signal_name,
            strategy_name=strategy_name,
            data_source=data_source,  # type: ignore
            steps=step_list,  # type: ignore
            force_rerun=force_rerun,
        )
    except ValueError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        raise click.Abort()
        
    # Execute workflow
    click.echo(f"\n🚀 Starting workflow: {signal_name} ({strategy_name})")
    click.echo(f"   Data source: {data_source}")
    if step_list:
        click.echo(f"   Steps: {', '.join(step_list)}")
    if force_rerun:
        click.echo("   Mode: Force re-run")
        
    engine = WorkflowEngine(workflow_config)
    results = engine.execute()
    
    # Display results
    if results["errors"]:
        click.echo(f"\n❌ Workflow failed after {results['steps_completed']} steps", err=True)
        for error in results["errors"]:
            click.echo(f"   Error in {error['step']}: {error['error']}", err=True)
        raise click.Abort()
    else:
        click.echo(f"\n✅ Workflow complete ({results['duration_seconds']:.1f}s)")
        click.echo(f"   Steps completed: {results['steps_completed']}")
        click.echo(f"   Steps skipped: {results['steps_skipped']}")
        click.echo(f"   Results: {results['output_dir']}")
