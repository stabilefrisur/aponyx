"""
Load all market data instruments from Bloomberg Terminal.

Prerequisites
-------------
Active Bloomberg Terminal session required.
Bloomberg securities configured in data/bloomberg_securities.json:
- CDX instruments (IG 5Y, IG 10Y, HY 5Y, iTraxx Europe 5Y, iTraxx Crossover 5Y)
- VIX volatility index
- Credit ETFs (HYG, LQD)

Note: Bloomberg data is automatically saved to data/raw/bloomberg/ with
hash-based naming for permanent storage.

Outputs
-------
Validated DataFrames for each instrument:
- CDX instruments: spread column with DatetimeIndex
- VIX: close column with DatetimeIndex
- ETF instruments: close column with DatetimeIndex

Data saved to:
- Raw storage: data/raw/bloomberg/{security}_{hash}.parquet (permanent)
- Cache: data/cache/bloomberg_{instrument}_{hash}.parquet (temporary)

Examples
--------
Run from project root:
    python -m aponyx.examples.03_fetch_data_bloomberg

Expected output: Eight validated DataFrames with historical data.
Date range depends on Bloomberg data availability (typically 5+ years).
"""

from datetime import datetime, timedelta

import pandas as pd

from aponyx.data import fetch_cdx, fetch_vix, fetch_etf, BloombergSource
from aponyx.data.bloomberg_config import list_securities


def main() -> dict[str, pd.DataFrame]:
    """
    Load and validate all market data from Bloomberg Terminal.

    Fetches all instruments defined in bloomberg_securities.json.
    Uses fetch interface with BloombergSource for automatic validation,
    caching, and raw storage.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary mapping security IDs to validated DataFrames.

    Notes
    -----
    Data is automatically saved to raw/bloomberg/ for permanent storage.
    Subsequent calls use cache unless data is stale (see CACHE_TTL_DAYS config).
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")

    source = BloombergSource()
    data = {}

    # Load CDX instruments
    cdx_securities = list_securities(instrument_type="cdx")
    for security in cdx_securities:
        df = fetch_cdx(
            source,
            security=security,
            start_date=start_date,
            end_date=end_date,
        )
        data[security] = df

    # Load VIX
    data["vix"] = fetch_vix(
        source,
        start_date=start_date,
        end_date=end_date,
    )

    # Load ETF instruments
    etf_securities = list_securities(instrument_type="etf")
    for security in etf_securities:
        df = fetch_etf(
            source,
            security=security,
            start_date=start_date,
            end_date=end_date,
        )
        data[security] = df

    return data


if __name__ == "__main__":
    main()
