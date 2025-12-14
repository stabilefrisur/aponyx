#!/usr/bin/env python3
"""Clean all Python and tool cache directories from the project.

This script recursively finds and removes:
- __pycache__ directories and .pyc files
- .pytest_cache directories
- .mypy_cache directories
- .ruff_cache directories
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


def clean_env_cache(root_dir: Path, dry_run: bool = False) -> dict[str, int]:
    """
    Remove all cache directories and .pyc files from root_dir.

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

    # Cache directory patterns to clean
    cache_patterns = [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    ]

    # Directories to exclude from cleaning
    exclude_patterns = {".venv", "venv", ".env", "env"}

    def should_skip(path: Path) -> bool:
        """Check if path is in an excluded directory."""
        return any(part in exclude_patterns for part in path.parts)

    # Find and remove cache directories
    for pattern in cache_patterns:
        for cache_dir in root_dir.rglob(pattern):
            if cache_dir.is_dir() and not should_skip(cache_dir):
                if dry_run:
                    logger.info("Would remove directory: %s", cache_dir)
                else:
                    logger.debug("Removing directory: %s", cache_dir)
                    shutil.rmtree(cache_dir)
                stats["directories"] += 1

    # Find and remove .pyc files not in __pycache__
    for pyc_file in root_dir.rglob("*.pyc"):
        if pyc_file.is_file() and not should_skip(pyc_file):
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
        description="Clean Python and tool cache directories (.pyc, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache)"
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

    logger.info("Cleaning Python and tool cache files from: %s", root_dir)
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be deleted")

    stats = clean_env_cache(root_dir, dry_run=args.dry_run)

    action = "Would remove" if args.dry_run else "Removed"
    logger.info(
        "%s %d cache directories and %d .pyc files",
        action,
        stats["directories"],
        stats["files"],
    )


if __name__ == "__main__":
    main()
