"""
Load market data from Bloomberg Terminal.

Prerequisites
-------------
Active Bloomberg Terminal session required.

Note: Bloomberg data is automatically cached and saved to data/raw/bloomberg/.

Outputs
-------
Prints summary statistics for loaded instruments.

Examples
--------
Run from project root:
    python -m aponyx.examples.03_fetch_data_bloomberg

Expected output: Summary stats for 3 instruments with 5 years of data.
"""

from datetime import datetime, timedelta

from aponyx.data import fetch_cdx, fetch_vix, fetch_etf, BloombergSource


def main() -> None:
    """
    Load market data from Bloomberg Terminal.

    Demonstrates BloombergSource provider pattern with date range.
    Data is automatically cached and saved to raw/bloomberg/.
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")

    source = BloombergSource()

    # Fetch different instrument types (auto-cached and validated)
    cdx_ig = fetch_cdx(source, security="cdx_ig_5y", start_date=start_date, end_date=end_date)
    print(f"CDX IG 5Y: {len(cdx_ig)} rows, spread range [{cdx_ig['spread'].min():.1f}, {cdx_ig['spread'].max():.1f}] bps")

    vix = fetch_vix(source, start_date=start_date, end_date=end_date)
    print(f"VIX: {len(vix)} rows, level range [{vix['level'].min():.1f}, {vix['level'].max():.1f}]")

    hyg = fetch_etf(source, security="hyg", start_date=start_date, end_date=end_date)
    print(f"HYG ETF: {len(hyg)} rows, price range [{hyg['price'].min():.2f}, {hyg['price'].max():.2f}]")


if __name__ == "__main__":
    main()
