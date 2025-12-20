#!/usr/bin/env python
"""
Clean Runtime Data Utility

Deletes all non-static, runtime-generated data including:
- Data files (raw, processed, cache)
- Logs and metadata
- Evaluation reports (suitability, performance)
- Runtime registries (data, suitability, performance)

PRESERVES static configuration files:
- Signal catalog (signal_catalog.json)
- Strategy catalog (strategy_catalog.json)
- Bloomberg config (bloomberg_securities.json, bloomberg_instruments.json)

Usage:
    python scripts/clean_runtime_data.py [--dry-run] [--verbose]

Options:
    --dry-run   Show what would be deleted without actually deleting
    --verbose   Show detailed information about each file/directory
"""

import argparse
import logging
import shutil
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Directories to clean (will remove all contents)
CLEAN_DIRS = [
    PROJECT_ROOT / "data" / "raw",
    PROJECT_ROOT / "data" / "workflows",
    PROJECT_ROOT / "data" / "cache",
    PROJECT_ROOT / "data" / "sweeps",
    PROJECT_ROOT / "data" / ".registries",
    PROJECT_ROOT / "logs",
]

# Static config files (explicitly preserved)
STATIC_CONFIGS = [
    PROJECT_ROOT / "src" / "aponyx" / "models" / "signal_catalog.json",
    PROJECT_ROOT / "src" / "aponyx" / "backtest" / "strategy_catalog.json",
    PROJECT_ROOT / "src" / "aponyx" / "data" / "bloomberg_securities.json",
    PROJECT_ROOT / "src" / "aponyx" / "data" / "bloomberg_instruments.json",
    PROJECT_ROOT / "src" / "aponyx" / "data" / "synthetic_params.json",
]


def clean_directory(dir_path: Path, dry_run: bool = False, verbose: bool = False) -> tuple[int, int]:
    """
    Clean all contents of a directory.
    
    Parameters
    ----------
    dir_path : Path
        Directory to clean.
    dry_run : bool
        If True, only show what would be deleted.
    verbose : bool
        If True, show detailed information.
    
    Returns
    -------
    tuple[int, int]
        (files_deleted, dirs_deleted)
    """
    if not dir_path.exists():
        if verbose:
            logger.info(f"  Directory does not exist: {dir_path.relative_to(PROJECT_ROOT)}")
        return 0, 0
    
    files_deleted = 0
    dirs_deleted = 0
    
    # Iterate over directory contents
    for item in dir_path.iterdir():
        if item.is_file():
            if dry_run:
                logger.info(f"  Would delete file: {item.relative_to(PROJECT_ROOT)}")
            else:
                if verbose:
                    logger.info(f"  Deleting file: {item.relative_to(PROJECT_ROOT)}")
                item.unlink()
            files_deleted += 1
        
        elif item.is_dir():
            if dry_run:
                logger.info(f"  Would delete directory: {item.relative_to(PROJECT_ROOT)}/")
            else:
                if verbose:
                    logger.info(f"  Deleting directory: {item.relative_to(PROJECT_ROOT)}/")
                shutil.rmtree(item)
            dirs_deleted += 1
    
    return files_deleted, dirs_deleted


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Clean all runtime-generated data (preserves static config files)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
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
        help="Show detailed information about each file/directory",
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.warning("DRY RUN MODE - No files will be deleted")
    
    logger.info("=" * 80)
    logger.info("CLEANING RUNTIME DATA")
    logger.info("=" * 80)
    
    # Summary counters
    total_files = 0
    total_dirs = 0
    
    # Clean directories
    logger.info("\nCleaning directories:")
    for dir_path in CLEAN_DIRS:
        logger.info(f"\n{dir_path.relative_to(PROJECT_ROOT)}/")
        files, dirs = clean_directory(dir_path, args.dry_run, args.verbose)
        total_files += files
        total_dirs += dirs
        if not args.verbose and (files > 0 or dirs > 0):
            logger.info(f"  Removed: {files} files, {dirs} directories")
    
    # Show preserved files
    logger.info("\n" + "=" * 80)
    logger.info("PRESERVED STATIC CONFIGURATION FILES")
    logger.info("=" * 80)
    for config_path in STATIC_CONFIGS:
        status = "✓" if config_path.exists() else "✗ (missing)"
        logger.info(f"  {status} {config_path.relative_to(PROJECT_ROOT)}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    action = "Would delete" if args.dry_run else "Deleted"
    logger.info(f"{action}: {total_files} files, {total_dirs} directories")
    
    if args.dry_run:
        logger.info("\nRun without --dry-run to actually delete files")
    else:
        logger.info("\n✓ Runtime data cleaned successfully")


if __name__ == "__main__":
    main()
