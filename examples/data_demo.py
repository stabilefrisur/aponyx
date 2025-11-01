"""
Data Layer Demonstration - Loading, Validation, and Caching

Demonstrates the data layer workflow for market data:
1. Fetch CDX, VIX, and ETF market data from Bloomberg Terminal
2. Load data with automatic schema validation:
   - CDX index spreads (validate_cdx_schema)
   - VIX volatility levels (validate_vix_schema)
   - ETF prices (validate_etf_schema)
3. Demonstrate caching behavior (second fetch uses cache)
4. Display summary statistics and data quality metrics

Output: Validated DataFrames with DatetimeIndex and quality metrics

Key Features:
  - Type-safe loading with DatetimeIndex enforcement
  - Schema validation (required columns, data types)
  - Business logic checks (spread/price bounds)
  - Transparent caching for repeated fetches
  - Clean separation of data layer from models layer

Requirements:
  - Active Bloomberg Terminal session
  - xbbg package installed: uv sync --extra bloomberg
"""

import logging

from aponyx.data import (
    fetch_cdx,
    fetch_vix,
    fetch_etf,
    BloombergSource,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run data layer demonstration."""
    logger.info("Starting data layer demonstration")

    # Configure Bloomberg Terminal data source
    logger.info("Configuring Bloomberg Terminal data source...")
    source = BloombergSource()
    logger.info("Bloomberg source configured (requires active Terminal session)")

    # Fetch individual data sources
    logger.info("\nFetching data from Bloomberg Terminal...")

    cdx_ig = fetch_cdx(source, security="cdx_ig_5y")
    logger.info("CDX IG fetched: %d rows, spread_mean=%.2f", len(cdx_ig), cdx_ig["spread"].mean())

    vix = fetch_vix(source)
    logger.info("VIX fetched: %d rows, vix_mean=%.2f", len(vix), vix["level"].mean())

    hyg = fetch_etf(source, security="hyg")
    logger.info("HYG fetched: %d rows, price_mean=%.2f", len(hyg), hyg["spread"].mean())

    # Demonstrate caching by fetching again
    logger.info("\nDemonstrating cache functionality...")
    cdx_ig_cached = fetch_cdx(source, security="cdx_ig_5y")
    logger.info("CDX IG from cache: %d rows", len(cdx_ig_cached))

    # Display summary statistics
    logger.info("\nData Quality Summary:")
    logger.info("CDX IG: %d rows, date_range=%s to %s",
                len(cdx_ig),
                cdx_ig.index.min().date(),
                cdx_ig.index.max().date())
    logger.info("  spread: mean=%.2f, min=%.2f, max=%.2f",
                cdx_ig["spread"].mean(),
                cdx_ig["spread"].min(),
                cdx_ig["spread"].max())

    logger.info("VIX: %d rows, date_range=%s to %s",
                len(vix),
                vix.index.min().date(),
                vix.index.max().date())
    logger.info("  level: mean=%.2f, min=%.2f, max=%.2f",
                vix["level"].mean(),
                vix["level"].min(),
                vix["level"].max())

    logger.info("HYG ETF: %d rows, date_range=%s to %s",
                len(hyg),
                hyg.index.min().date(),
                hyg.index.max().date())
    logger.info("  spread: mean=%.2f, min=%.2f, max=%.2f",
                hyg["spread"].mean(),
                hyg["spread"].min(),
                hyg["spread"].max())

    # Validate data integrity
    logger.info("\nData Integrity Checks:")
    logger.info("CDX missing values: %d", cdx_ig.isna().sum().sum())
    logger.info("VIX missing values: %d", vix.isna().sum().sum())
    logger.info("HYG missing values: %d", hyg.isna().sum().sum())

    logger.info("\nData layer demonstration complete!")


if __name__ == "__main__":
    main()
