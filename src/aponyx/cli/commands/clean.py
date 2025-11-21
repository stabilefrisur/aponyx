"""
Clean cached results command.

Removes processed outputs to force fresh computation.
"""

import logging
import shutil

import click

from aponyx.config import PROCESSED_DIR

logger = logging.getLogger(__name__)


@click.command(name="clean")
@click.option(
    "--signal",
    type=str,
    help="Clean specific signal results only",
)
@click.option(
    "--all",
    "clean_all",
    is_flag=True,
    help="Clean all cached results",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without deleting",
)
def clean(
    signal: str | None,
    clean_all: bool,
    dry_run: bool,
) -> None:
    """
    Clear cached workflow results.
    
    Examples:

        aponyx clean --signal spread_momentum

        aponyx clean --all

        aponyx clean --all --dry-run
    """
    workflows_dir = PROCESSED_DIR / "workflows"
    
    if not workflows_dir.exists():
        click.echo("No cached results found")
        return
        
    # Determine what to clean
    if signal:
        targets = list(workflows_dir.glob(f"**/{signal}_*"))
        targets.extend(list(workflows_dir.glob(f"**/signals/{signal}")))
        targets.extend(list(workflows_dir.glob(f"**/data/{signal}")))
    elif clean_all:
        targets = [workflows_dir]
    else:
        click.echo("Must specify --signal or --all", err=True)
        raise click.Abort()
        
    if not targets:
        click.echo(f"No cached results found for: {signal}")
        return
        
    # Show/delete targets
    for target in targets:
        if dry_run:
            click.echo(f"Would delete: {target}")
        else:
            logger.info("Deleting %s", target)
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
                
    if dry_run:
        click.echo(f"Dry run: {len(targets)} item(s) would be deleted")
    else:
        click.echo(f"Cleaned {len(targets)} item(s)")
