"""
Clean cached results command.

Removes processed outputs to force fresh computation.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import click

from aponyx.config import DATA_WORKFLOWS_DIR, INDICATOR_CACHE_DIR
from aponyx.persistence.parquet_io import invalidate_indicator_cache

logger = logging.getLogger(__name__)


def _parse_days(older_than: str) -> int:
    """
    Parse days from string format like '30d', '7d', '90d'.
    
    Parameters
    ----------
    older_than : str
        String in format '<number>d'.
    
    Returns
    -------
    int
        Number of days.
    
    Raises
    ------
    click.ClickException
        If format is invalid.
    """
    if not older_than.endswith('d'):
        raise click.ClickException(
            f"Invalid format '{older_than}'. Expected format: '<number>d' (e.g., '30d', '7d')"
        )
    
    try:
        days = int(older_than[:-1])
        if days <= 0:
            raise ValueError
        return days
    except ValueError:
        raise click.ClickException(
            f"Invalid number in '{older_than}'. Must be a positive integer."
        )


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
    help="Filter workflows by signal name (use with --workflows)",
)
@click.option(
    "--all",
    "clean_all",
    is_flag=True,
    help="Clean all cached results",
)
@click.option(
    "--workflows",
    is_flag=True,
    help="Clean workflow results",
)
@click.option(
    "--older-than",
    type=str,
    help="Delete workflows older than specified days (format: '30d', '7d', '90d'). Use with --workflows.",
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
    workflows: bool,
    older_than: str | None,
    indicators: bool,
    dry_run: bool,
) -> None:
    """
    Clear cached workflow results and indicator cache.

    \b
    Examples:
        # Clean all workflow results
        aponyx clean --workflows --all
        
        # Clean workflows older than 30 days
        aponyx clean --workflows --older-than 30d
        
        # Clean old workflows for specific signal
        aponyx clean --workflows --signal spread_momentum --older-than 30d
        
        # Clean indicator cache
        aponyx clean --indicators
        
        # Preview changes without deleting
        aponyx clean --workflows --older-than 30d --dry-run
    """
    # Handle indicator cache cleaning
    if indicators:
        _clean_indicator_cache(dry_run)
        if not signal and not clean_all and not workflows:
            # If only --indicators flag, we're done
            return
    
    # Validate options
    if older_than and not workflows:
        click.echo("Error: --older-than requires --workflows flag", err=True)
        raise click.Abort()
    
    # Handle workflow cleaning
    if workflows or clean_all:
        _clean_workflows(
            signal_filter=signal,
            clean_all=clean_all,
            older_than=older_than,
            dry_run=dry_run,
        )
        return
    
    # If no workflow/indicator flags, show error
    if not indicators:
        click.echo("Must specify --workflows, --indicators, or --all", err=True)
        raise click.Abort()


def _clean_workflows(
    signal_filter: str | None,
    clean_all: bool,
    older_than: str | None,
    dry_run: bool,
) -> None:
    """
    Clean workflow directories based on filters.
    
    Parameters
    ----------
    signal_filter : str | None
        Filter by signal name.
    clean_all : bool
        Clean all workflows (ignore age filter).
    older_than : str | None
        Delete workflows older than specified days (format: '30d').
    dry_run : bool
        Preview without deleting.
    """
    workflows_dir = DATA_WORKFLOWS_DIR

    if not workflows_dir.exists():
        click.echo("No workflows found")
        return
    
    # Parse age threshold if provided
    age_threshold = None
    if older_than:
        days = _parse_days(older_than)
        age_threshold = datetime.now() - timedelta(days=days)
    
    # Collect workflow directories to delete
    workflow_dirs_to_delete = []
    
    for workflow_dir in workflows_dir.iterdir():
        if not workflow_dir.is_dir():
            continue
        
        # Load metadata for filtering
        metadata_path = workflow_dir / "metadata.json"
        if not metadata_path.exists():
            # Include directories without metadata if --all specified
            if clean_all:
                workflow_dirs_to_delete.append(workflow_dir)
            continue
        
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            logger.debug("Failed to load metadata from %s: %s", workflow_dir, e)
            if clean_all:
                workflow_dirs_to_delete.append(workflow_dir)
            continue
        
        # Apply signal filter
        if signal_filter:
            if metadata.get("signal") != signal_filter:
                continue
        
        # Apply age filter (unless --all specified)
        if not clean_all and age_threshold:
            timestamp_str = metadata.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp >= age_threshold:
                        # Workflow is newer than threshold, skip
                        continue
                except Exception as e:
                    logger.debug("Failed to parse timestamp from %s: %s", workflow_dir, e)
                    continue
        
        # Add to deletion list
        workflow_dirs_to_delete.append(workflow_dir)
    
    if not workflow_dirs_to_delete:
        if signal_filter:
            click.echo(f"No workflows found matching signal '{signal_filter}'")
        elif older_than:
            click.echo(f"No workflows found older than {older_than}")
        else:
            click.echo("No workflows found")
        return
    
    # Collect all files and directories from matched workflows
    targets = []
    for workflow_dir in workflow_dirs_to_delete:
        targets.extend(_collect_targets(workflow_dir))
    
    # Display summary
    if dry_run:
        click.echo(f"Would delete {len(workflow_dirs_to_delete)} workflow(s) ({len(targets)} items):\n")
    
    deleted_count = 0
    for target in targets:
        # Display path relative to workflows dir for clarity
        rel_path = target.relative_to(workflows_dir.parent)

        if dry_run:
            click.echo(f"  {rel_path}")
        else:
            # Show workflow directory names being deleted
            if target.parent == workflows_dir and target.is_dir():
                click.echo(f"Deleting workflow: {target.name}")
            logger.debug("Deleting %s", target)
            try:
                if target.is_dir():
                    target.rmdir()
                else:
                    target.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning("Failed to delete %s: %s", target, e)
                click.echo(f"  Failed: {e}", err=True)
    
    # Summary
    if dry_run:
        click.echo(f"\nDry run complete: {len(workflow_dirs_to_delete)} workflow(s) would be deleted")
    else:
        click.echo(f"\nCleaned {deleted_count}/{len(targets)} item(s) from {len(workflow_dirs_to_delete)} workflow(s)")


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
