"""
Persistence Layer Demonstration - Data I/O and Registry Management

Demonstrates Parquet and JSON I/O operations with DataRegistry:
1. Fetch market data from Bloomberg Terminal (primary) or generate synthetic fallback
2. Save datasets to Parquet files with automatic directory creation
3. Register datasets in central JSON registry with metadata
4. Query registry by instrument type and date range
5. Load data with optional filtering (date range, columns)
6. Demonstrate DatasetEntry dataclass for type-safe registry access
7. Save and load JSON metadata for run tracking

Output: 
  - Parquet files in data/raw/
  - Registry in data/registry.json
  - Run metadata in logs/run_metadata.json

Key Features:
  - Type-safe Parquet I/O with automatic path handling
  - Central registry for dataset discovery and metadata
  - DatasetEntry dataclass with to_dict()/from_dict() conversion
  - Selective loading with column and date filtering
  - JSON I/O with datetime and Path serialization support
  - Real data ingestion workflow from Bloomberg Terminal
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from example_data import generate_persistence_data
from aponyx.data import DataRegistry, DatasetEntry, fetch_cdx, fetch_vix, fetch_etf
from aponyx.persistence import save_parquet, load_parquet, save_json, load_json
from aponyx.config import DATA_DIR, REGISTRY_PATH, LOGS_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global flag to track data source
_using_bloomberg = False


def demonstrate_parquet_io() -> dict[str, Path]:
    """
    Demonstrate Parquet save/load operations with Bloomberg or synthetic data.
    
    Returns
    -------
    dict[str, Path]
        Mapping of instrument names to file paths.
    """
    global _using_bloomberg
    
    print("\n" + "=" * 70)
    print("PART 1: Parquet I/O Operations")
    print("=" * 70)
    
    # Try Bloomberg Terminal first
    print("\nAttempting Bloomberg Terminal connection...")
    try:
        from aponyx.data import BloombergSource
        
        source = BloombergSource()
        logger.info("Bloomberg Terminal connection established")
        print("  OK Bloomberg Terminal available")
        print("  Fetching data from 2024-01-01 to present...")
        _using_bloomberg = True
        
        # Fetch from Bloomberg and create datasets dict
        cdx_ig = fetch_cdx(source, security="cdx_ig_5y", start_date="2024-01-01")
        cdx_hy = fetch_cdx(source, security="cdx_hy_5y", start_date="2024-01-01")
        vix = fetch_vix(source, start_date="2024-01-01")
        hyg = fetch_etf(source, security="hyg", start_date="2024-01-01")
        
        datasets = {
            "cdx_ig_5y": cdx_ig,
            "cdx_hy_5y": cdx_hy,
            "vix": vix,
            "hyg_etf": hyg,
        }
        
        logger.info("Fetched %d datasets from Bloomberg", len(datasets))
        print(f"  OK Fetched {len(datasets)} instruments from Bloomberg")
        
    except (ImportError, ModuleNotFoundError) as e:
        logger.warning("Bloomberg Terminal not available: missing xbbg or blpapi module")
        print("  ! Bloomberg Terminal not installed")
        print(f"    Reason: {e}")
        print("\n  Falling back to synthetic data...")
        _using_bloomberg = False
        
        datasets = generate_persistence_data(periods=209)
        logger.info("Generated %d datasets synthetically", len(datasets))
        print(f"  OK Generated {len(datasets)} instruments")
        
    except BaseException as e:
        # Catch pytest.Skipped and other xbbg errors
        error_str = str(e).lower()
        error_type = str(type(e).__name__).lower()
        if "blpapi" in error_str or "could not import" in error_str or "skipped" in error_type:
            logger.warning("Bloomberg Terminal not available: blpapi module missing")
            print("  ! Bloomberg Terminal not installed")
        else:
            logger.warning("Bloomberg Terminal connection failed: %s", e)
            print("  ! Bloomberg Terminal not running or authentication failed")
            print(f"    Reason: {type(e).__name__}: {e}")
        
        print("\n  Falling back to synthetic data...")
        _using_bloomberg = False
        
        datasets = generate_persistence_data(periods=209)
        logger.info("Generated %d datasets synthetically", len(datasets))
        print(f"  OK Generated {len(datasets)} instruments")
    
    # Save each dataset to Parquet
    data_source = "Bloomberg" if _using_bloomberg else "synthetic"
    print(f"\nSaving Parquet files ({data_source} data)...")
    file_paths = {}
    
    for name, df in datasets.items():
        file_path = DATA_DIR / "raw" / f"{name}.parquet"
        save_parquet(df, file_path)
        file_paths[name] = file_path
        logger.info("Saved %s: %d rows to %s", name, len(df), file_path)
        print(f"  OK {name}: {len(df)} rows -> {file_path}")
    
    # Load data back
    print("\nLoading Parquet files...")
    for name, path in file_paths.items():
        df = load_parquet(path)
        print(f"  OK {name}: {len(df)} rows, columns={df.columns.tolist()}")
    
    # Demonstrate selective loading
    print("\nSelective loading examples...")
    
    # Load specific columns only
    spreads_only = load_parquet(
        file_paths["cdx_ig_5y"],
        columns=["spread"],
    )
    print(f"  OK Loaded columns only: {spreads_only.columns.tolist()}")
    
    # Load date range (if Bloomberg data, use recent dates)
    import pandas as pd
    if _using_bloomberg:
        # Use a recent date from the Bloomberg data
        start_date = pd.Timestamp("2024-10-01")
    else:
        # Use synthetic data date
        start_date = pd.Timestamp("2024-10-01")
    
    recent = load_parquet(
        file_paths["vix"],
        start_date=start_date,
    )
    print(f"  OK Loaded date range (Oct 2024+): {len(recent)} rows")
    
    return file_paths


def demonstrate_registry_operations(file_paths: dict[str, Path]) -> None:
    """
    Demonstrate DataRegistry CRUD operations.
    
    Parameters
    ----------
    file_paths : dict[str, Path]
        Mapping of instrument names to file paths.
    """
    global _using_bloomberg
    
    print("\n" + "=" * 70)
    print("PART 2: DataRegistry Operations")
    print("=" * 70)
    
    # Initialize registry
    print("\nInitializing DataRegistry...")
    registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    print(f"  OK Registry path: {REGISTRY_PATH}")
    
    # Register datasets with metadata
    data_source = "bloomberg" if _using_bloomberg else "synthetic"
    print(f"\nRegistering datasets ({data_source} data)...")
    
    registry.register_dataset(
        name="cdx_ig_5y",
        file_path=file_paths["cdx_ig_5y"],
        instrument="CDX.NA.IG",
        tenor="5Y",
        metadata={"source": data_source, "frequency": "daily"},
    )
    
    registry.register_dataset(
        name="cdx_hy_5y",
        file_path=file_paths["cdx_hy_5y"],
        instrument="CDX.NA.HY",
        tenor="5Y",
        metadata={"source": data_source, "frequency": "daily"},
    )
    
    registry.register_dataset(
        name="vix",
        file_path=file_paths["vix"],
        instrument="VIX",
        metadata={"source": data_source, "frequency": "daily"},
    )
    
    registry.register_dataset(
        name="hyg_etf",
        file_path=file_paths["hyg_etf"],
        instrument="HYG",
        metadata={"source": data_source, "frequency": "daily", "type": "ETF"},
    )
    
    logger.info("Registered %d datasets with source=%s", len(file_paths), data_source)
    print(f"  OK Registered {len(file_paths)} datasets")
    
    # Query registry
    print("\nQuerying registry...")
    
    all_datasets = registry.list_datasets()
    print(f"  Total datasets: {len(all_datasets)}")
    print(f"  Dataset names: {all_datasets}")
    
    # Filter by instrument type
    cdx_datasets = [name for name in all_datasets if "cdx" in name]
    print(f"  CDX instruments: {cdx_datasets}")


def demonstrate_dataclass_features() -> None:
    """Demonstrate DatasetEntry dataclass features and type safety."""
    print("\n" + "=" * 70)
    print("PART 3: DatasetEntry Dataclass Features")
    print("=" * 70)
    
    registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    
    # Type-safe attribute access
    print("\nType-safe attribute access...")
    entry = registry.get_dataset_entry("cdx_ig_5y")
    
    print(f"  Type: {type(entry).__name__}")
    print(f"  Instrument: {entry.instrument}")
    print(f"  Tenor: {entry.tenor}")
    print(f"  Date range: {entry.start_date[:10]} to {entry.end_date[:10]}")
    print(f"  Rows: {entry.row_count}")
    print(f"  Metadata: {entry.metadata}")
    
    # Dataclass benefits
    print("\n  Type-safe benefits:")
    print("    OK IDE autocomplete for all attributes")
    print("    OK No KeyError risk from typos")
    print(f"    OK Typed attributes: {type(entry.instrument).__name__}, {type(entry.row_count).__name__}")
    
    # Iterate over multiple datasets
    print("\nProcessing multiple datasets type-safely...")
    for name in ["cdx_ig_5y", "cdx_hy_5y", "vix", "hyg_etf"]:
        entry = registry.get_dataset_entry(name)
        tenor_str = entry.tenor or "N/A"
        print(f"  {entry.instrument:12s} ({tenor_str:3s}): {entry.row_count:3d} rows")
    
    # Dataclass conversion methods
    print("\nDataclass conversion methods...")
    entry = registry.get_dataset_entry("hyg_etf")
    
    # Convert to dict for serialization
    entry_dict = entry.to_dict()
    print(f"  to_dict(): {type(entry_dict).__name__} with {len(entry_dict)} keys")
    
    # Recreate from dict
    restored = DatasetEntry.from_dict(entry_dict)
    print(f"  from_dict(): {type(restored).__name__}")
    print(f"  Roundtrip preserves data: {restored.instrument == entry.instrument}")
    
    # Practical filtering example
    print("\nPractical example - filter datasets by row count...")
    all_names = registry.list_datasets()
    large_datasets = [
        name for name in all_names
        if registry.get_dataset_entry(name).row_count and 
           registry.get_dataset_entry(name).row_count > 100
    ]
    print(f"  Datasets with >100 rows: {large_datasets}")


def demonstrate_json_io() -> None:
    """Demonstrate JSON save/load operations with metadata tracking."""
    print("\n" + "=" * 70)
    print("PART 4: JSON I/O for Metadata Tracking")
    print("=" * 70)
    
    print("\nSaving run metadata to JSON...")
    
    # Create comprehensive metadata
    metadata = {
        "run_id": "persistence_demo_20241102",
        "timestamp": datetime.now(),
        "framework_version": "0.1.1",
        "parameters": {
            "lookback": 20,
            "entry_threshold": 1.5,
            "exit_threshold": 0.75,
            "instruments": ["CDX.IG.5Y", "CDX.HY.5Y", "VIX", "HYG"],
        },
        "data_info": {
            "start_date": "2024-01-01",
            "periods": 209,
            "seed": 42,
        },
        "output_paths": {
            "registry": str(REGISTRY_PATH),
            "data_dir": str(DATA_DIR),
        },
    }
    
    # Save metadata
    metadata_path = save_json(metadata, LOGS_DIR / "persistence_demo_metadata.json")
    print(f"  OK Saved to: {metadata_path}")
    
    # Load metadata back
    print("\nLoading metadata from JSON...")
    loaded = load_json(metadata_path)
    
    print(f"  Run ID: {loaded['run_id']}")
    print(f"  Timestamp: {loaded['timestamp']}")
    print(f"  Framework version: {loaded['framework_version']}")
    print(f"  Instruments: {loaded['parameters']['instruments']}")
    
    # Verify datetime serialization
    print("\n  JSON serialization features:")
    print("    OK Automatic datetime serialization")
    print("    OK Path object serialization")
    print("    OK Pretty-printed with indent=2")


def demonstrate_update_operations() -> None:
    """Demonstrate registry update and deletion operations."""
    print("\n" + "=" * 70)
    print("PART 5: Registry Update Operations")
    print("=" * 70)
    
    registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    
    # Add new metadata to existing entry
    print("\nUpdating dataset metadata...")
    entry = registry.get_dataset_entry("cdx_ig_5y")
    original_metadata = entry.metadata.copy() if entry.metadata else {}
    
    # Update with additional info
    updated_metadata = {
        **original_metadata,
        "updated_at": datetime.now().isoformat(),
        "quality_check": "passed",
    }
    
    registry.register_dataset(
        name="cdx_ig_5y",
        file_path=entry.file_path,
        instrument=entry.instrument,
        tenor=entry.tenor,
        metadata=updated_metadata,
    )
    
    updated_entry = registry.get_dataset_entry("cdx_ig_5y")
    print(f"  OK Updated metadata: {updated_entry.metadata}")
    
    # List all datasets again
    print(f"\n  Total datasets after update: {len(registry.list_datasets())}")


def main() -> None:
    """Run complete persistence layer demonstration."""
    global _using_bloomberg
    
    print("=" * 70)
    print("PERSISTENCE LAYER DEMONSTRATION")
    print("Parquet I/O, JSON I/O, and DataRegistry Management")
    print("=" * 70)
    
    # Run demonstrations
    file_paths = demonstrate_parquet_io()
    demonstrate_registry_operations(file_paths)
    demonstrate_dataclass_features()
    demonstrate_json_io()
    demonstrate_update_operations()
    
    # Summary
    data_source = "Bloomberg Terminal" if _using_bloomberg else "Synthetic data"
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print(f"\nData source used: {data_source}")
    print("\nKey Features Demonstrated:")
    if _using_bloomberg:
        print("  OK Real data ingestion workflow from Bloomberg Terminal")
        print("  OK Bloomberg fetch → save → register pipeline")
    else:
        print("  OK Graceful fallback when Bloomberg unavailable")
    print("  OK Parquet save/load with automatic path handling")
    print("  OK Selective loading (date range, columns)")
    print("  OK DataRegistry CRUD operations")
    print("  OK DatasetEntry dataclass for type-safe access")
    print("  OK Registry queries and filtering")
    print("  OK JSON I/O with datetime/Path serialization")
    print("  OK Metadata tracking for reproducibility")
    print("  OK Registry update operations")
    print("=" * 70)
    
    print("\nGenerated files:")
    print(f"  - Parquet data: {DATA_DIR / 'raw'}/")
    print(f"  - Registry: {REGISTRY_PATH}")
    print(f"  - Metadata: {LOGS_DIR / 'persistence_demo_metadata.json'}")
    if not _using_bloomberg:
        print("\nNext steps:")
        print("  -> Install Bloomberg Terminal and xbbg to use real data")


if __name__ == "__main__":
    main()
