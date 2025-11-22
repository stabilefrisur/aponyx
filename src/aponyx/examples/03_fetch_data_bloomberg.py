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

    Fetches all securities defined in bloomberg_securities.json.
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
    from aponyx.data.bloomberg_config import get_security_spec

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")

    source = BloombergSource()
    data = {}

    # Load all securities from catalog
    all_securities = list_securities()
    for security_id in all_securities:
        spec = get_security_spec(security_id)
        instrument_type = spec.instrument_type

        if instrument_type == "vix":
            df = fetch_vix(
                source,
                start_date=start_date,
                end_date=end_date,
            )
        elif instrument_type == "etf":
            df = fetch_etf(
                source,
                security=security_id,
                start_date=start_date,
                end_date=end_date,
            )
        elif instrument_type == "cdx":
            df = fetch_cdx(
                source,
                security=security_id,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            raise ValueError(f"Unknown instrument type: {instrument_type}")

        data[security_id] = df

    return data


if __name__ == "__main__":
    main()
