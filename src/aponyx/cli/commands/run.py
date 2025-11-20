"""
Run workflow command.

Executes research workflows for signal-strategy combinations.
"""

import logging

import click

from aponyx.workflows import WorkflowEngine, WorkflowConfig

logger = logging.getLogger(__name__)


@click.command(name="run")
@click.option(
    "--signal",
    required=True,
    type=str,
    help="Signal name from signal catalog",
)
@click.option(
    "--strategy",
    required=True,
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
def run(
    signal: str,
    strategy: str,
    data: str,
    steps: str | None,
    force: bool,
) -> None:
    """
    Run research workflow for signal-strategy combination.
    
    Executes full pipeline: data -> signal -> evaluation -> backtest -> visualization.
    Skips completed steps unless --force is specified.
    
    Examples:
    
        aponyx run --signal spread_momentum --strategy balanced
        
        aponyx run --signal cdx_vix_gap --strategy aggressive --data bloomberg
        
        aponyx run --signal spread_momentum --strategy balanced --steps data,signal,backtest --force
    """
    # Parse steps
    step_list = None
    if steps:
        step_list = [s.strip() for s in steps.split(",")]
        
    # Create config
    try:
        config = WorkflowConfig(
            signal_name=signal,
            strategy_name=strategy,
            data_source=data,  # type: ignore
            steps=step_list,  # type: ignore
            force_rerun=force,
        )
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise click.Abort()
        
    # Execute workflow
    click.echo(f"\nStarting workflow: {signal} ({strategy})")
    click.echo(f"   Data source: {data}")
    if step_list:
        click.echo(f"   Steps: {', '.join(step_list)}")
    if force:
        click.echo("   Mode: Force re-run")
        
    engine = WorkflowEngine(config)
    results = engine.execute()
    
    # Display results
    if results["errors"]:
        click.echo(f"\nWorkflow failed after {results['steps_completed']} steps", err=True)
        for error in results["errors"]:
            click.echo(f"   Error in {error['step']}: {error['error']}", err=True)
        raise click.Abort()
    else:
        click.echo(f"\nWorkflow complete ({results['duration_seconds']:.1f}s)")
        click.echo(f"   Steps completed: {results['steps_completed']}")
        click.echo(f"   Steps skipped: {results['steps_skipped']}")
        click.echo(f"   Results: {results['output_dir']}")
