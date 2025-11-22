#!/usr/bin/env python3
"""Clean all __pycache__ directories from the project.

This script recursively finds and removes all __pycache__ directories
and .pyc files from the project root.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def clean_pycache(root_dir: Path, dry_run: bool = False) -> dict[str, int]:
    """
    Remove all __pycache__ directories and .pyc files from root_dir.

    Parameters
    ----------
    root_dir : Path
        Root directory to search for cache files.
    dry_run : bool, optional
        If True, only report what would be deleted without actually deleting.

    Returns
    -------
    dict[str, int]
        Statistics with 'directories' and 'files' counts.
    """
    stats = {"directories": 0, "files": 0}

    # Find and remove __pycache__ directories
    for pycache_dir in root_dir.rglob("__pycache__"):
        if pycache_dir.is_dir():
            if dry_run:
                logger.info("Would remove directory: %s", pycache_dir)
            else:
                logger.debug("Removing directory: %s", pycache_dir)
                shutil.rmtree(pycache_dir)
            stats["directories"] += 1

    # Find and remove .pyc files not in __pycache__
    for pyc_file in root_dir.rglob("*.pyc"):
        if pyc_file.is_file():
            if dry_run:
                logger.info("Would remove file: %s", pyc_file)
            else:
                logger.debug("Removing file: %s", pyc_file)
                pyc_file.unlink()
            stats["files"] += 1

    return stats


def main() -> None:
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean __pycache__ directories and .pyc files from the project"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root directory (defaults to script parent directory)",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Determine project root
    if args.root:
        root_dir = args.root.resolve()
    else:
        # Script is in scripts/, so parent is project root
        root_dir = Path(__file__).parent.parent.resolve()

    logger.info("Cleaning Python cache files from: %s", root_dir)
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be deleted")

    stats = clean_pycache(root_dir, dry_run=args.dry_run)

    action = "Would remove" if args.dry_run else "Removed"
    logger.info(
        "%s %d __pycache__ directories and %d .pyc files",
        action,
        stats["directories"],
        stats["files"],
    )


if __name__ == "__main__":
    main()
