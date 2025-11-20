"""
Load all market data instruments from file sources.

Prerequisites
-------------
Raw data files must exist in data/raw/synthetic/:
- cdx_ig_5y_{hash}.parquet (CDX IG 5Y spreads)
- cdx_ig_10y_{hash}.parquet (CDX IG 10Y spreads)
- cdx_hy_5y_{hash}.parquet (CDX HY 5Y spreads)
- itrx_xover_5y_{hash}.parquet (iTraxx Crossover 5Y spreads)
- itrx_eur_5y_{hash}.parquet (iTraxx Europe 5Y spreads)
- vix_{hash}.parquet (VIX volatility index)
- hyg_{hash}.parquet (HYG high yield ETF)
- lqd_{hash}.parquet (LQD investment grade ETF)

Run 01_generate_synthetic_data.py first if files don't exist.

Outputs
-------
Validated DataFrames for each instrument:
- CDX instruments: spread column with DatetimeIndex
- VIX: close column with DatetimeIndex
- ETF instruments: close column with DatetimeIndex

All data validated against schema expectations.

Examples
--------
Run from project root:
    python -m aponyx.examples.02_fetch_data_file

Expected output: Eight validated DataFrames with ~1260 rows each.
"""

from pathlib import Path

import pandas as pd

from aponyx.config import RAW_DIR
from aponyx.data import fetch_cdx, fetch_vix, fetch_etf, FileSource
from aponyx.data.bloomberg_config import list_securities


def main() -> dict[str, pd.DataFrame]:
    """
    Load and validate all market data from file sources.

    Loads all instruments defined in bloomberg_securities.json from
    the synthetic data directory. Uses fetch interface with FileSource
    to ensure proper validation and schema compliance.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary mapping security IDs to validated DataFrames.
    """
    synthetic_dir = RAW_DIR / "synthetic"
    data = {}

    # Load CDX instruments
    cdx_securities = list_securities(instrument_type="cdx")
    for security in cdx_securities:
        file_path = _find_data_file(synthetic_dir, security)
        df = fetch_cdx(FileSource(file_path), security=security)
        data[security] = df

    # Load VIX
    vix_path = _find_data_file(synthetic_dir, "vix")
    data["vix"] = fetch_vix(FileSource(vix_path))

    # Load ETF instruments
    etf_securities = list_securities(instrument_type="etf")
    for security in etf_securities:
        file_path = _find_data_file(synthetic_dir, security)
        df = fetch_etf(FileSource(file_path), security=security)
        data[security] = df

    return data


def _find_data_file(directory: Path, security: str) -> Path:
    """
    Find data file for security in directory.

    Parameters
    ----------
    directory : Path
        Directory to search for data files.
    security : str
        Security identifier (e.g., "cdx_ig_5y", "vix").

    Returns
    -------
    Path
        Path to data file.
    """
    safe_security = security.replace(".", "_").replace("/", "_")
    pattern = f"{safe_security}_*.parquet"
    matches = list(directory.glob(pattern))
    return matches[0]


if __name__ == "__main__":
    main()
