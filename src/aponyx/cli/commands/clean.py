"""
Clean cached results command.

Removes processed outputs to force fresh computation.
"""

import logging
from pathlib import Path

import click

from aponyx.config import DATA_WORKFLOWS_DIR, INDICATOR_CACHE_DIR
from aponyx.persistence.parquet_io import invalidate_indicator_cache

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
    "--indicators",
    is_flag=True,
    help="Clean indicator cache",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without deleting",
)
def clean(
    signal: str | None,
    clean_all: bool,
    indicators: bool,
    dry_run: bool,
) -> None:
    """
    Clear cached workflow results and indicator cache.

    \b
    Examples:
        aponyx clean --signal spread_momentum
        aponyx clean --all
        aponyx clean --indicators
        aponyx clean --all --indicators
        aponyx clean --all --dry-run
    """
    # Handle indicator cache cleaning
    if indicators:
        _clean_indicator_cache(dry_run)
        if not signal and not clean_all:
            # If only --indicators flag, we're done
            return
    workflows_dir = DATA_WORKFLOWS_DIR

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
        # Get all workflow subdirectories (not the workflows_dir itself)
        workflow_subdirs = [d for d in workflows_dir.iterdir() if d.is_dir()]
        if not workflow_subdirs:
            click.echo("No cached results found")
            return

        targets = []
        for subdir in workflow_subdirs:
            targets.extend(_collect_targets(subdir))
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
            # Always show what we're deleting
            click.echo(f"Deleting: {rel_path}")
            logger.debug("Deleting %s", target)
            try:
                if target.is_dir():
                    # Use rmdir for directories (they should be empty by now)
                    target.rmdir()
                else:
                    target.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning("Failed to delete %s: %s", target, e)
                click.echo(f"  Failed: {e}", err=True)

    # Summary
    if dry_run:
        click.echo(f"\nDry run complete: {len(targets)} item(s) would be deleted")
    else:
        click.echo(f"\nCleaned {deleted_count}/{len(targets)} item(s)")


def _clean_indicator_cache(dry_run: bool) -> None:
    """
    Clean all cached indicator values.

    Parameters
    ----------
    dry_run : bool
        If True, only show what would be deleted.
    """
    if not INDICATOR_CACHE_DIR.exists():
        click.echo("No indicator cache found")
        return

    # Collect all cache files
    cache_files = list(INDICATOR_CACHE_DIR.glob("*.parquet"))

    if not cache_files:
        click.echo("No cached indicators found")
        return

    if dry_run:
        click.echo(f"\nWould delete {len(cache_files)} cached indicator(s):")
        for cache_file in sorted(cache_files):
            click.echo(f"  {cache_file.name}")
        click.echo(f"\nDry run complete: {len(cache_files)} indicator(s) would be deleted")
    else:
        click.echo(f"Cleaning {len(cache_files)} cached indicator(s)...")
        deleted_count = 0

        for cache_file in cache_files:
            try:
                # Extract indicator name from cache key (format: {name}_{params_hash}_{data_hash}.parquet)
                indicator_name = cache_file.stem.split("_")[0]
                click.echo(f"Deleting cached indicator: {indicator_name}")
                cache_file.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning("Failed to delete %s: %s", cache_file, e)
                click.echo(f"  Failed: {e}", err=True)

        click.echo(f"\nCleaned {deleted_count}/{len(cache_files)} indicator cache file(s)")
