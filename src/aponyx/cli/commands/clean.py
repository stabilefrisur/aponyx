"""
Clean cached results command.

Removes processed outputs to force fresh computation.
"""

import logging
import shutil
from pathlib import Path

import click

from aponyx.config import PROCESSED_DIR

logger = logging.getLogger(__name__)


def _collect_targets(base_path: Path) -> list[Path]:
    """
    Recursively collect all files and directories to delete.
    
    Parameters
    ----------
    base_path : Path
        Root directory to collect from.
        
    Returns
    -------
    list[Path]
        List of all files and directories, depth-first order.
    """
    targets = []
    
    if not base_path.exists():
        return targets
        
    if base_path.is_file():
        targets.append(base_path)
    elif base_path.is_dir():
        # Collect files and subdirectories recursively
        for item in sorted(base_path.rglob("*"), reverse=True):
            targets.append(item)
        # Add the directory itself last
        targets.append(base_path)
        
    return targets


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
        pattern_targets = list(workflows_dir.glob(f"**/{signal}_*"))
        pattern_targets.extend(list(workflows_dir.glob(f"**/signals/{signal}")))
        pattern_targets.extend(list(workflows_dir.glob(f"**/data/{signal}")))
        
        # Collect all files/dirs from pattern matches
        targets = []
        for target in pattern_targets:
            targets.extend(_collect_targets(target))
            
    elif clean_all:
        targets = _collect_targets(workflows_dir)
    else:
        click.echo("Must specify --signal or --all", err=True)
        raise click.Abort()
        
    if not targets:
        click.echo(f"No cached results found for: {signal}")
        return
        
    # Show what will be deleted
    if dry_run:
        click.echo(f"Would delete {len(targets)} item(s):\n")
        
    deleted_count = 0
    for target in targets:
        # Display path relative to workflows dir for clarity
        rel_path = target.relative_to(workflows_dir.parent)
        
        if dry_run:
            click.echo(f"  {rel_path}")
        else:
            logger.debug("Deleting %s", target)
            try:
                if target.is_dir():
                    # Use rmdir for directories (they should be empty by now)
                    target.rmdir()
                else:
                    target.unlink()
                deleted_count += 1
                click.echo(f"Deleted: {rel_path}")
            except Exception as e:
                logger.warning("Failed to delete %s: %s", target, e)
                
    # Summary
    if dry_run:
        click.echo(f"\nDry run complete: {len(targets)} item(s) would be deleted")
    else:
        click.echo(f"\nCleaned {deleted_count}/{len(targets)} item(s)")
