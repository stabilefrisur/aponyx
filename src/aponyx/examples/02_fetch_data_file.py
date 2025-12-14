"""
Load all market data instruments from file sources.

Prerequisites
-------------
Raw data files must exist in data/raw/synthetic/ with registry.json:
- cdx_ig_5y_{hash}.parquet (CDX IG 5Y spreads)
- cdx_ig_10y_{hash}.parquet (CDX IG 10Y spreads)
- cdx_hy_5y_{hash}.parquet (CDX HY 5Y spreads)
- itrx_xover_5y_{hash}.parquet (iTraxx Crossover 5Y spreads)
- itrx_eur_5y_{hash}.parquet (iTraxx Europe 5Y spreads)
- vix_{hash}.parquet (VIX volatility index)
- hyg_{hash}.parquet (HYG high yield ETF)
- lqd_{hash}.parquet (LQD investment grade ETF)
- registry.json (security-to-file mapping)

Run scripts/generate_synthetic.py first if files don't exist.

Outputs
-------
Validated DataFrames for each instrument:
- CDX instruments: spread column with DatetimeIndex
- VIX: level column with DatetimeIndex
- ETF instruments: close column with DatetimeIndex

All data validated against schema expectations.

Examples
--------
Run from project root:
    python -m aponyx.examples.02_fetch_data_file

Expected output: Eight validated DataFrames with ~1260 rows each.
"""


import pandas as pd

from aponyx.config import RAW_DIR
from aponyx.data import fetch_cdx, fetch_vix, fetch_etf, FileSource
from aponyx.data.bloomberg_config import list_securities


def main() -> dict[str, pd.DataFrame]:
    """
    Load and validate all market data from file sources.

    Loads all instruments defined in bloomberg_securities.json from
    the synthetic data directory. Uses FileSource with registry-based
    lookup for security-to-file mapping.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary mapping security IDs to validated DataFrames.
    """
    synthetic_dir = RAW_DIR / "synthetic"

    # Initialize FileSource with registry (auto-loads registry.json)
    source = FileSource(synthetic_dir)

    data = {}

    # Load CDX instruments
    cdx_securities = list_securities(instrument_type="cdx")
    for security in cdx_securities:
        df = fetch_cdx(source, security=security)
        data[security] = df

    # Load VIX
    data["vix"] = fetch_vix(source, security="vix")

    # Load ETF instruments
    etf_securities = list_securities(instrument_type="etf")
    for security in etf_securities:
        df = fetch_etf(source, security=security)
        data[security] = df

    return data


if __name__ == "__main__":
    main()
