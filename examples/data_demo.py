"""
Data Layer Demonstration - Fetching, Validation, and Caching

Demonstrates the data layer fetch operations with validation and caching:
1. Generate synthetic market data (CDX, VIX, ETF) and save to files
2. Fetch CDX, VIX, and ETF data using FileSource provider
3. Validate data using schema validators (validate_cdx_schema, validate_vix_schema, validate_etf_schema)
4. Demonstrate cache behavior (miss on first fetch, hit on second fetch)
5. Show data quality metrics and statistics

Output:
  - Validated DataFrames with DatetimeIndex
  - Schema validation results
  - Cache performance (miss/hit logging)

Key Features:
  - Provider pattern abstraction (FileSource, BloombergSource)
  - Unified fetch interface (fetch_cdx, fetch_vix, fetch_etf)
  - Schema validation with constraint checking
  - Transparent TTL-based caching
  - Clean separation of data layer from models layer
"""

import logging
from pathlib import Path

from example_data import generate_example_data
from aponyx.data import (
    fetch_cdx,
    fetch_vix,
    fetch_etf,
    FileSource,
    validate_cdx_schema,
    validate_vix_schema,
    validate_etf_schema,
)
from aponyx.persistence import save_parquet
from aponyx.config import DATA_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_sample_files() -> None:
    """Create sample market data files for fetch demonstrations."""
    print("\n" + "=" * 70)
    print("PART 1: Creating Sample Data Files")
    print("=" * 70)
    
    print("\nGenerating synthetic market data...")
    cdx_df, vix_df, etf_df = generate_example_data(periods=252)
    
    # Save to files for fetch demonstrations
    raw_dir = DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    save_parquet(cdx_df, raw_dir / "cdx_ig_5y.parquet")
    print(f"  OK CDX IG 5Y: {len(cdx_df)} rows -> {raw_dir / 'cdx_ig_5y.parquet'}")
    
    save_parquet(vix_df, raw_dir / "vix.parquet")
    print(f"  OK VIX: {len(vix_df)} rows -> {raw_dir / 'vix.parquet'}")
    
    save_parquet(etf_df, raw_dir / "hyg_etf.parquet")
    print(f"  OK HYG ETF: {len(etf_df)} rows -> {raw_dir / 'hyg_etf.parquet'}")


def demonstrate_fetch_operations() -> tuple:
    """
    Demonstrate fetch operations with FileSource.
    
    Returns
    -------
    tuple
        (cdx_df, vix_df, etf_df) DataFrames with DatetimeIndex.
    """
    print("\n" + "=" * 70)
    print("PART 2: Fetch Operations with Validation")
    print("=" * 70)
    
    raw_dir = DATA_DIR / "raw"
    print(f"\nData directory: {raw_dir}")
    
    # Fetch CDX data
    print("\nFetching CDX data...")
    cdx_source = FileSource(raw_dir / "cdx_ig_5y.parquet")
    cdx_df = fetch_cdx(cdx_source)
    print(f"  OK Loaded {len(cdx_df)} rows")
    print(f"  Columns: {cdx_df.columns.tolist()}")
    print(f"  Date range: {cdx_df.index.min().date()} to {cdx_df.index.max().date()}")
    print(f"  Spread range: [{cdx_df['spread'].min():.2f}, {cdx_df['spread'].max():.2f}] bps")
    
    # Fetch VIX data
    print("\nFetching VIX data...")
    vix_source = FileSource(raw_dir / "vix.parquet")
    vix_df = fetch_vix(vix_source)
    print(f"  OK Loaded {len(vix_df)} rows")
    print(f"  Columns: {vix_df.columns.tolist()}")
    print(f"  Date range: {vix_df.index.min().date()} to {vix_df.index.max().date()}")
    print(f"  Level range: [{vix_df['level'].min():.2f}, {vix_df['level'].max():.2f}]")
    
    # Fetch ETF data
    print("\nFetching ETF data...")
    etf_source = FileSource(raw_dir / "hyg_etf.parquet")
    etf_df = fetch_etf(etf_source)
    print(f"  OK Loaded {len(etf_df)} rows")
    print(f"  Columns: {etf_df.columns.tolist()}")
    print(f"  Date range: {etf_df.index.min().date()} to {etf_df.index.max().date()}")
    print(f"  Spread range: [{etf_df['spread'].min():.2f}, {etf_df['spread'].max():.2f}]")
    
    return cdx_df, vix_df, etf_df


def demonstrate_validation(cdx_df, vix_df, etf_df) -> None:
    """
    Demonstrate schema validation.
    
    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX data with spread column.
    vix_df : pd.DataFrame
        VIX data with level column.
    etf_df : pd.DataFrame
        ETF data with spread column.
    """
    print("\n" + "=" * 70)
    print("PART 3: Schema Validation")
    print("=" * 70)
    
    # Validate CDX schema
    print("\nValidating CDX schema...")
    validate_cdx_schema(cdx_df)
    print("  OK CDX schema valid")
    print("    - Required columns present: date, spread")
    print("    - Spread range check: 0.0 <= spread <= 10000.0 bps")
    print(f"    - Actual range: [{cdx_df['spread'].min():.2f}, {cdx_df['spread'].max():.2f}]")
    
    # Validate VIX schema
    print("\nValidating VIX schema...")
    validate_vix_schema(vix_df)
    print("  OK VIX schema valid")
    print("    - Required columns present: date, level")
    print("    - Level range check: 0.0 <= level <= 200.0")
    print(f"    - Actual range: [{vix_df['level'].min():.2f}, {vix_df['level'].max():.2f}]")
    
    # Validate ETF schema
    print("\nValidating ETF schema...")
    validate_etf_schema(etf_df)
    print("  OK ETF schema valid")
    print("    - Required columns present: date, spread")
    print("    - Spread range check: 0.0 <= spread <= 10000.0")
    print(f"    - Actual range: [{etf_df['spread'].min():.2f}, {etf_df['spread'].max():.2f}]")


def demonstrate_caching() -> None:
    """Demonstrate cache miss and cache hit behavior."""
    print("\n" + "=" * 70)
    print("PART 4: Cache Behavior Demonstration")
    print("=" * 70)
    
    source = FileSource(DATA_DIR / "raw" / "cdx_ig_5y.parquet")
    
    print("\nFirst fetch (cache miss expected)...")
    print("  Watch for 'Cache miss' in logs below:")
    cdx_first = fetch_cdx(source, use_cache=True)
    print(f"  OK Fetched {len(cdx_first)} rows")
    
    print("\nSecond fetch (cache hit expected)...")
    print("  Watch for 'Cache hit' in logs below:")
    cdx_second = fetch_cdx(source, use_cache=True)
    print(f"  OK Retrieved {len(cdx_second)} rows from cache")
    
    # Verify data consistency
    import pandas as pd
    if cdx_first.equals(cdx_second):
        print("\n  OK Cache consistency verified (DataFrames identical)")
    else:
        print("\n  WARNING: Data mismatch between fetches")
    
    print("\nCache benefits:")
    print("  OK Reduced I/O on repeated fetches")
    print("  OK Faster data access for iterative development")
    print("  OK Automatic staleness checking via TTL")
    print("  OK Transparent to user code (same API)")


def demonstrate_data_quality(cdx_df, vix_df, etf_df) -> None:
    """
    Show data quality metrics and statistics.
    
    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX data.
    vix_df : pd.DataFrame
        VIX data.
    etf_df : pd.DataFrame
        ETF data.
    """
    print("\n" + "=" * 70)
    print("PART 5: Data Quality Metrics")
    print("=" * 70)
    
    print("\nData Integrity Checks:")
    print(f"  CDX missing values: {cdx_df.isna().sum().sum()}")
    print(f"  VIX missing values: {vix_df.isna().sum().sum()}")
    print(f"  ETF missing values: {etf_df.isna().sum().sum()}")
    
    print("\nDate Index Checks:")
    print(f"  CDX date continuity: {cdx_df.index.is_monotonic_increasing}")
    print(f"  VIX date continuity: {vix_df.index.is_monotonic_increasing}")
    print(f"  ETF date continuity: {etf_df.index.is_monotonic_increasing}")
    
    print("\nSummary Statistics:")
    print("\nCDX IG 5Y:")
    print(f"  Observations: {len(cdx_df)}")
    print(f"  Mean spread: {cdx_df['spread'].mean():.2f} bps")
    print(f"  Std dev: {cdx_df['spread'].std():.2f} bps")
    print(f"  Range: [{cdx_df['spread'].min():.2f}, {cdx_df['spread'].max():.2f}]")
    
    print("\nVIX:")
    print(f"  Observations: {len(vix_df)}")
    print(f"  Mean level: {vix_df['level'].mean():.2f}")
    print(f"  Std dev: {vix_df['level'].std():.2f}")
    print(f"  Range: [{vix_df['level'].min():.2f}, {vix_df['level'].max():.2f}]")
    
    print("\nHYG ETF:")
    print(f"  Observations: {len(etf_df)}")
    print(f"  Mean spread: {etf_df['spread'].mean():.2f}")
    print(f"  Std dev: {etf_df['spread'].std():.2f}")
    print(f"  Range: [{etf_df['spread'].min():.2f}, {etf_df['spread'].max():.2f}]")


def main() -> None:
    """Run complete data layer demonstration."""
    print("=" * 70)
    print("DATA LAYER DEMONSTRATION")
    print("Fetching, Validation, and Caching")
    print("=" * 70)
    
    # Run demonstrations
    create_sample_files()
    cdx_df, vix_df, etf_df = demonstrate_fetch_operations()
    demonstrate_validation(cdx_df, vix_df, etf_df)
    demonstrate_caching()
    demonstrate_data_quality(cdx_df, vix_df, etf_df)
    
    # Summary
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nKey Features Demonstrated:")
    print("  OK FileSource provider for local files")
    print("  OK Unified fetch interface (fetch_cdx, fetch_vix, fetch_etf)")
    print("  OK Schema validation with constraint checking")
    print("  OK Transparent caching (miss then hit)")
    print("  OK Data quality metrics and integrity checks")
    print("  OK DatetimeIndex with proper alignment")
    print("  OK Clean separation from models layer")
    print("=" * 70)
    
    print("\nNext steps:")
    print("  -> See persistence_demo.py for Parquet/JSON I/O and registry")
    print("  -> See bloomberg_demo.py for Bloomberg Terminal integration")
    print("  -> See models_demo.py for signal computation")


if __name__ == "__main__":
    main()
