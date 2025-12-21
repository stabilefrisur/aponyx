"""
Load market data from local file sources.

Prerequisites
-------------
Raw data files in data/raw/synthetic/ with registry.json:
- cdx_ig_5y.parquet (CDX IG 5Y spreads)
- vix.parquet (VIX volatility index)
- hyg.parquet (HYG ETF prices)

Run 01_generate_synthetic_data.py first if files don't exist.

Outputs
-------
Prints summary statistics for loaded instruments.

Examples
--------
Run from project root:
    python -m aponyx.examples.02_fetch_data_file

Expected output: Summary stats for 3 instruments.
"""

from aponyx.config import RAW_DIR
from aponyx.data import fetch_security_data, FileSource, UsagePurpose


def main() -> None:
    """
    Load and validate market data from local file sources.

    Demonstrates FileSource provider pattern with registry-based
    security-to-file mapping. Uses synthetic data directory.
    Uses the unified fetch_security_data() interface.
    """
    source = FileSource(RAW_DIR / "synthetic")

    # Load various instrument types (returns validated DataFrames)
    cdx_ig = fetch_security_data(source, "cdx_ig_5y", purpose=UsagePurpose.INDICATOR)
    print(
        f"CDX IG 5Y: {len(cdx_ig)} rows, spread range [{cdx_ig['spread'].min():.1f}, {cdx_ig['spread'].max():.1f}] bps"
    )

    vix = fetch_security_data(source, "vix", purpose=UsagePurpose.INDICATOR)
    print(
        f"VIX: {len(vix)} rows, level range [{vix['level'].min():.1f}, {vix['level'].max():.1f}]"
    )

    etf = fetch_security_data(source, "hyg", purpose=UsagePurpose.PNL)
    print(
        f"HYG ETF: {len(etf)} rows, price range [{etf['price'].min():.2f}, {etf['price'].max():.2f}]"
    )


if __name__ == "__main__":
    main()
