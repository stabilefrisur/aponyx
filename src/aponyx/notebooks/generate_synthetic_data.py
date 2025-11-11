#!/usr/bin/env python
"""
Generate Synthetic Data for Development

This script replaces step 01 (Bloomberg data download) when Bloomberg Terminal
is not available. It generates synthetic market data that can be used with
subsequent workflow stages (02, 03, 04, 05).

Run this script before executing the other notebooks in development environments.

Usage
-----
Command line:
    python generate_synthetic_data.py

From Python:
    from aponyx.notebooks.generate_synthetic_data import main, setup_synthetic_data

    # Simple interface (for notebooks)
    setup_synthetic_data(years_of_history=5)

    # Detailed interface (command line)
    main(years_of_history=5)
"""

import logging
from datetime import datetime, timedelta

from aponyx.config import DATA_DIR
from aponyx.data.sample_data import generate_for_fetch_interface

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_synthetic_data(years_of_history: int = 5) -> None:
    """
    Generate and cache synthetic market data for notebook workflows.

    Simple interface for use within notebooks. Generates cache files silently
    and returns control immediately.

    Parameters
    ----------
    years_of_history : int, default 5
        Number of years of historical data to generate.

    Notes
    -----
    Creates cache files in data/cache/file/ directory:
    - cdx_cdx_ig_5y.parquet
    - vix_vix.parquet
    - etf_hyg.parquet

    These files are automatically discovered by notebooks that use FileSource.

    Examples
    --------
    >>> from aponyx.notebooks.generate_synthetic_data import setup_synthetic_data
    >>> setup_synthetic_data(years_of_history=5)
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=years_of_history * 365)).strftime("%Y-%m-%d")

    cache_dir = DATA_DIR / "cache" / "file"
    cache_dir.mkdir(parents=True, exist_ok=True)

    generate_for_fetch_interface(
        output_dir=cache_dir,
        start_date=start_date,
        end_date=end_date,
        seed=42,
    )


def main(years_of_history: int = 5) -> None:
    """
    Generate synthetic data for all workflow stages.

    Parameters
    ----------
    years_of_history : int, default 5
        Number of years of historical data to generate.
    """
    print("=" * 80)
    print("SYNTHETIC DATA GENERATION — Development Mode")
    print("=" * 80)
    print("\nThis script generates synthetic market data for development/testing.")
    print("Use this when Bloomberg Terminal is not available.\n")

    # Calculate date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=years_of_history * 365)).strftime("%Y-%m-%d")

    cache_dir = DATA_DIR / "cache" / "file"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print("Configuration:")
    print(f"  Years of history: {years_of_history}")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Cache directory: {cache_dir}")
    print("\nGenerating synthetic data...")

    # Generate all required data files
    file_paths = generate_for_fetch_interface(
        output_dir=cache_dir,
        start_date=start_date,
        end_date=end_date,
        seed=42,
    )

    print("\n[OK] Synthetic data generation complete!")
    print("\nGenerated Files:")
    for security, path in file_paths.items():
        size_kb = path.stat().st_size / 1024
        print(f"  {security}: {path.name} ({size_kb:.1f} KB)")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\nYou can now run the workflow notebooks:")
    print("  1. Skip 01_data_download.ipynb (Bloomberg not available)")
    print("  2. Run 02_signal_computation.ipynb")
    print("  3. Run 03_suitability_evaluation.ipynb")
    print("  4. Run 04_backtest_execution.ipynb (when available)")
    print("  5. Run 05_analysis.ipynb (when available)")
    print("\nNotebooks will auto-detect the synthetic data cache.")
    print()


if __name__ == "__main__":
    main()
