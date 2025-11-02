"""
Data Layer Demonstration - Loading, Validation, Caching, and Registry

Demonstrates the complete data layer workflow:
1. Generate synthetic market data for multiple instruments
   - CDX IG, CDX HY, VIX, HYG ETF (209 trading days)
2. Save datasets to Parquet files with metadata
3. Register datasets in central JSON registry
4. Query registry by instrument type and date range
5. Fetch CDX, VIX, and ETF market data with schema validation:
   - CDX index spreads (validate_cdx_schema)
   - VIX volatility levels (validate_vix_schema)
   - ETF prices (validate_etf_schema)
6. Demonstrate caching behavior (second fetch uses cache)
7. Display summary statistics and data quality metrics

Output: 
  - Parquet files in data/raw/
  - Registry in data/registry.json
  - Validated DataFrames with DatetimeIndex

Key Features:
  - Type-safe Parquet I/O with schema validation
  - Central registry for dataset discovery
  - Metadata tracking (instrument, frequency, date range)
  - DatasetEntry dataclass for type-safe access
  - Transparent caching for repeated fetches
  - Clean separation of data layer from models layer
  - Business logic checks (spread/price bounds)
"""

import logging
import pandas as pd
from datetime import datetime

from example_data import generate_persistence_data
from aponyx.data import (
    fetch_cdx,
    fetch_vix,
    fetch_etf,
    FileSource,
    DataRegistry,
    DatasetEntry,
)
from aponyx.persistence import save_parquet, load_parquet, save_json, load_json
from aponyx.config import DATA_DIR, REGISTRY_PATH, LOGS_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_sample_data() -> None:
    """
    Create sample market data files for demonstration.

    Generates synthetic CDX spread, VIX, and ETF data and saves to Parquet.
    """
    print("\n" + "=" * 60)
    print("PART 1: Creating Sample Data and Registry")
    print("=" * 60)
    print("\nCreating sample market data...")

    # Generate all datasets using centralized helper
    datasets = generate_persistence_data(periods=209)

    # Save each dataset
    save_parquet(datasets["cdx_ig_5y"], DATA_DIR / "raw" / "cdx_ig_5y.parquet")
    print(f"  ✓ Saved CDX IG 5Y: {len(datasets['cdx_ig_5y'])} rows")

    save_parquet(datasets["cdx_hy_5y"], DATA_DIR / "raw" / "cdx_hy_5y.parquet")
    print(f"  ✓ Saved CDX HY 5Y: {len(datasets['cdx_hy_5y'])} rows")

    save_parquet(datasets["vix"], DATA_DIR / "raw" / "vix.parquet")
    print(f"  ✓ Saved VIX: {len(datasets['vix'])} rows")

    save_parquet(datasets["hyg_etf"], DATA_DIR / "raw" / "hyg_etf.parquet")
    print(f"  ✓ Saved HYG ETF: {len(datasets['hyg_etf'])} rows")


def register_datasets() -> None:
    """
    Register all datasets in the central registry.

    Creates a DataRegistry and registers all available market data files
    with appropriate metadata.
    """
    print("\nRegistering datasets...")

    registry = DataRegistry(REGISTRY_PATH, DATA_DIR)

    # Register CDX instruments
    registry.register_dataset(
        name="cdx_ig_5y",
        file_path=DATA_DIR / "raw" / "cdx_ig_5y.parquet",
        instrument="CDX.NA.IG",
        tenor="5Y",
        metadata={"source": "synthetic", "frequency": "daily"},
    )

    registry.register_dataset(
        name="cdx_hy_5y",
        file_path=DATA_DIR / "raw" / "cdx_hy_5y.parquet",
        instrument="CDX.NA.HY",
        tenor="5Y",
        metadata={"source": "synthetic", "frequency": "daily"},
    )

    # Register market data
    registry.register_dataset(
        name="vix",
        file_path=DATA_DIR / "raw" / "vix.parquet",
        instrument="VIX",
        metadata={"source": "synthetic", "frequency": "daily"},
    )

    registry.register_dataset(
        name="hyg_etf",
        file_path=DATA_DIR / "raw" / "hyg_etf.parquet",
        instrument="HYG",
        metadata={"source": "synthetic", "frequency": "daily", "type": "ETF"},
    )

    print(f"  ✓ Registered {len(registry.list_datasets())} datasets")


def demonstrate_registry_usage() -> None:
    """Demonstrate registry query and filtering capabilities."""
    print("\nDemonstrating registry queries...")

    registry = DataRegistry(REGISTRY_PATH, DATA_DIR)

    # List all datasets
    all_datasets = registry.list_datasets()
    print(f"  Total datasets: {len(all_datasets)}")

    # Filter by CDX instruments
    cdx_datasets = [d for d in all_datasets if "cdx" in d]
    print(f"  CDX instruments: {cdx_datasets}")

    # Get detailed info using type-safe dataclass
    entry = registry.get_dataset_entry("cdx_ig_5y")
    print("\n  CDX IG 5Y details:")
    print(f"    Type: {type(entry).__name__}")
    print(f"    Instrument: {entry.instrument}")
    print(f"    Tenor: {entry.tenor}")
    print(f"    Date range: {entry.start_date[:10]} to {entry.end_date[:10]}")
    print(f"    Rows: {entry.row_count}")
    print(f"    Metadata: {entry.metadata}")
    
    # Demonstrate type-safe attribute access benefits
    print("\n  Type-safe benefits:")
    print("    - IDE autocomplete works for all attributes ✓")
    print(f"    - Typed attributes: {type(entry.instrument).__name__}, {type(entry.row_count).__name__}")
    print("    - No KeyError risk from typos ✓")


def demonstrate_dataclass_features() -> None:
    """Demonstrate DatasetEntry dataclass features."""
    print("\nDemonstrating DatasetEntry dataclass...")
    
    registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    
    # Get multiple entries and work with them type-safely
    print("\n  Processing multiple datasets:")
    for name in ["cdx_ig_5y", "cdx_hy_5y", "vix"]:
        entry = registry.get_dataset_entry(name)
        print(f"    {entry.instrument:12s} ({entry.tenor or 'N/A':3s}): {entry.row_count:3d} rows")
    
    # Demonstrate conversion methods
    print("\n  Dataclass conversion methods:")
    entry = registry.get_dataset_entry("hyg_etf")
    
    # Convert to dict for JSON serialization
    entry_dict = entry.to_dict()
    print(f"    to_dict(): {type(entry_dict).__name__} with {len(entry_dict)} keys")
    
    # Recreate from dict
    restored = DatasetEntry.from_dict(entry_dict)
    print(f"    from_dict(): {type(restored).__name__}")
    print(f"    Roundtrip preserves data: {restored.instrument == entry.instrument}")
    
    # Show practical use case: filtering datasets by row count
    print("\n  Practical example - filter by row count:")
    all_names = registry.list_datasets()
    large_datasets = [
        name for name in all_names
        if registry.get_dataset_entry(name).row_count and 
           registry.get_dataset_entry(name).row_count > 100
    ]
    print(f"    Datasets with >100 rows: {large_datasets}")


def demonstrate_data_fetching() -> None:
    """Demonstrate data fetching with validation and caching."""
    print("\n" + "=" * 60)
    print("PART 2: Data Fetching with Validation and Caching")
    print("=" * 60)
    print("\nFetching data with schema validation...")

    # Configure file-based data source
    source = FileSource(DATA_DIR / "raw")
    
    # Fetch individual data sources
    cdx_ig = fetch_cdx(source, security="cdx_ig_5y")
    logger.info("CDX IG fetched: %d rows, spread_mean=%.2f", len(cdx_ig), cdx_ig["spread"].mean())

    vix = fetch_vix(source)
    logger.info("VIX fetched: %d rows, level_mean=%.2f", len(vix), vix["close"].mean())

    hyg = fetch_etf(source, security="hyg")
    logger.info("HYG fetched: %d rows, price_mean=%.2f", len(hyg), hyg["close"].mean())

    # Demonstrate caching by fetching again
    print("\nDemonstrating cache functionality...")
    cdx_ig_cached = fetch_cdx(source, security="cdx_ig_5y")
    logger.info("CDX IG from cache: %d rows", len(cdx_ig_cached))

    # Display summary statistics
    print("\nData Quality Summary:")
    print(f"CDX IG: {len(cdx_ig)} rows, date_range={cdx_ig.index.min().date()} to {cdx_ig.index.max().date()}")
    print(f"  spread: mean={cdx_ig['spread'].mean():.2f}, min={cdx_ig['spread'].min():.2f}, max={cdx_ig['spread'].max():.2f}")

    print(f"VIX: {len(vix)} rows, date_range={vix.index.min().date()} to {vix.index.max().date()}")
    print(f"  close: mean={vix['close'].mean():.2f}, min={vix['close'].min():.2f}, max={vix['close'].max():.2f}")

    print(f"HYG ETF: {len(hyg)} rows, date_range={hyg.index.min().date()} to {hyg.index.max().date()}")
    print(f"  close: mean={hyg['close'].mean():.2f}, min={hyg['close'].min():.2f}, max={hyg['close'].max():.2f}")

    # Validate data integrity
    print("\nData Integrity Checks:")
    print(f"CDX missing values: {cdx_ig.isna().sum().sum()}")
    print(f"VIX missing values: {vix.isna().sum().sum()}")
    print(f"HYG missing values: {hyg.isna().sum().sum()}")


def demonstrate_data_loading() -> None:
    """Demonstrate data loading with filters."""
    print("\n" + "=" * 60)
    print("PART 3: Advanced Data Loading")
    print("=" * 60)
    print("\nDemonstrating data loading...")

    # Load full dataset
    cdx_ig = load_parquet(DATA_DIR / "raw" / "cdx_ig_5y.parquet")
    print(f"  Loaded full CDX IG dataset: {len(cdx_ig)} rows")

    # Load with date filter
    recent = load_parquet(
        DATA_DIR / "raw" / "cdx_ig_5y.parquet",
        start_date=pd.Timestamp("2024-10-01"),
    )
    print(f"  Loaded recent data (Oct 2024): {len(recent)} rows")

    # Load specific columns
    spreads_only = load_parquet(
        DATA_DIR / "raw" / "cdx_ig_5y.parquet",
        columns=["spread"],
    )
    print(f"  Loaded spread column only: {spreads_only.columns.tolist()}")


def save_run_metadata() -> None:
    """Save example run metadata to JSON."""
    print("\nSaving run metadata...")

    metadata = {
        "run_id": "demo_20241102",
        "timestamp": datetime.now(),
        "parameters": {
            "momentum_window": 5,
            "volatility_window": 20,
            "instruments": ["CDX.IG.5Y", "CDX.HY.5Y"],
        },
        "data_version": "0.1.0",
        "output_path": DATA_DIR / "processed" / "signals.parquet",
    }

    output_path = save_json(metadata, LOGS_DIR / "run_metadata.json")
    print(f"  ✓ Saved metadata to {output_path}")

    # Load it back
    loaded = load_json(output_path)
    print(f"  ✓ Verified: Run ID = {loaded['run_id']}")


def main() -> None:
    """Run complete data layer demonstration."""
    print("=" * 60)
    print("Data Layer Complete Demonstration")
    print("=" * 60)

    create_sample_data()
    register_datasets()
    demonstrate_registry_usage()
    demonstrate_dataclass_features()
    demonstrate_data_fetching()
    demonstrate_data_loading()
    save_run_metadata()

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("  ✓ Parquet I/O with compression and filtering")
    print("  ✓ JSON I/O with datetime/Path support")
    print("  ✓ DataRegistry for dataset catalog management")
    print("  ✓ DatasetEntry dataclass for type-safe access")
    print("  ✓ Registry queries and filtering")
    print("  ✓ Schema validation (CDX, VIX, ETF)")
    print("  ✓ Transparent caching for repeated fetches")
    print("  ✓ Data quality checks and integrity validation")
    print("=" * 60)


if __name__ == "__main__":
    main()
