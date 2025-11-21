"""
Generate synthetic market data for all instruments.

Prerequisites
-------------
None — this is the first step in the workflow.

Outputs
-------
Raw synthetic data files in data/raw/synthetic/:
- cdx_ig_5y_{hash}.parquet (CDX spread data)
- cdx_ig_10y_{hash}.parquet (CDX spread data)
- cdx_hy_5y_{hash}.parquet (CDX spread data)
- itrx_xover_5y_{hash}.parquet (CDX spread data)
- itrx_eur_5y_{hash}.parquet (CDX spread data)
- vix_{hash}.parquet (VIX volatility index)
- hyg_{hash}.parquet (High yield ETF spreads)
- lqd_{hash}.parquet (Investment grade ETF spreads)

Each file includes metadata JSON with generation parameters.

Examples
--------
Run from project root:
    python -m aponyx.examples.01_generate_synthetic_data

Expected output: 8 parquet files with 5 years of daily data (~1260 rows each).
"""

from aponyx.config import RAW_DIR
from aponyx.data.sample_data import generate_for_fetch_interface


def main() -> None:
    """
    Generate synthetic market data for testing and demonstrations.

    Creates realistic time series data for all instruments defined in
    bloomberg_securities.json, using hash-based naming compatible with
    the data fetch interface.
    """
    output_dir = RAW_DIR / "synthetic"

    generate_for_fetch_interface(
        output_dir=output_dir,
        start_date="2020-01-01",
        end_date="2025-01-01",
        seed=42,
    )


if __name__ == "__main__":
    main()
