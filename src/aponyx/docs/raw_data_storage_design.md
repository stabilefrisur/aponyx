# Raw Data Storage Design

## Overview

Raw data storage represents the permanent source of truth for market data. Unlike cache (which can be deleted), raw files are never automatically removed and include comprehensive metadata for reproducibility.

## File Naming Convention

### Raw Storage (Permanent)

**Format:** `{instrument}_{security}_{hash}.parquet`

**Examples:**
```
cdx_cdx_ig_5y_b1f849bfe3a1.parquet
vix_vix_00252a34df0f.parquet
etf_hyg_108d48a6a616.parquet
```

**Hash Generation:**
- 12-character SHA256 hash prefix
- Computed from: provider, instrument, date range, row count, metadata
- Ensures uniqueness across different data pulls
- Enables versioning without explicit version numbers

**Metadata Sidecar:**

Each `.parquet` file has a corresponding `.json` metadata file:

```json
{
  "provider": "synthetic",
  "instrument": "cdx",
  "security": "cdx_ig_5y",
  "stored_at": "2025-11-16T20:32:53.953000",
  "date_range": {
    "start": "2020-11-17",
    "end": "2025-11-16"
  },
  "row_count": 1304,
  "columns": ["spread", "security"],
  "hash": "b1f849bfe3a1",
  "generation_params": {
    "base_spread": 100.0,
    "volatility": 5.0
  }
}
```

### Processed Storage (Derived)

**Format:** `{instrument}_{security}.parquet`

**Examples:**
```
signals.parquet
cdx_signals.parquet
performance_metrics.parquet
```

Processed files do not need hashes because:
1. They are derived from raw data (reproducible)
2. They are regenerated from scratch each workflow run
3. Simpler names improve usability in notebooks

## Provider Alignment

Both Bloomberg and synthetic sources now use the same hash-based naming:

| Source | Format | Example |
|--------|--------|---------|
| Bloomberg | `{instrument}_{security}_{hash}.parquet` | `cdx_cdx_ig_5y_a1b2c3d4e5f6.parquet` |
| Synthetic | `{instrument}_{security}_{hash}.parquet` | `cdx_cdx_ig_5y_b1f849bfe3a1.parquet` |

## Directory Structure

```
data/
├── raw/                           # Permanent source of truth
│   ├── bloomberg/                 # Bloomberg Terminal data
│   │   ├── cdx_cdx_ig_5y_a1b2.parquet
│   │   ├── cdx_cdx_ig_5y_a1b2.json
│   │   ├── vix_vix_c3d4.parquet
│   │   └── vix_vix_c3d4.json
│   └── synthetic/                 # Generated test data
│       ├── cdx_cdx_ig_5y_b1f8.parquet
│       ├── cdx_cdx_ig_5y_b1f8.json
│       ├── vix_vix_0025.parquet
│       └── vix_vix_0025.json
├── processed/                     # Derived data products
│   ├── signals.parquet
│   └── backtest_results.parquet
└── cache/                         # Temporary performance cache
    └── bloomberg/
        └── cdx_cdx_ig_5y_f7e6.parquet
```

## Workflow Integration

### Data Download (Bloomberg)

```python
from aponyx.data import fetch_cdx
from aponyx.data.sources import BloombergSource

# Fetch from Bloomberg
df = fetch_cdx(
    source=BloombergSource(),
    security="cdx_ig_5y",
    start_date="2020-01-01",
    end_date="2025-11-16",
)

# Automatically saved to:
# data/raw/bloomberg/cdx_cdx_ig_5y_{hash}.parquet
# data/raw/bloomberg/cdx_cdx_ig_5y_{hash}.json
```

### Synthetic Generation

```python
from aponyx.data.sample_data import generate_for_fetch_interface

# Generate synthetic data
file_paths = generate_for_fetch_interface(
    output_path=Path("data/raw/synthetic"),
    start_date="2020-01-01",
    years=5,
)

# Creates:
# data/raw/synthetic/cdx_cdx_ig_5y_{hash}.parquet
# data/raw/synthetic/cdx_cdx_ig_5y_{hash}.json
```

### Notebook Loading (Data-Source Agnostic)

```python
from pathlib import Path
from aponyx.data import fetch_cdx
from aponyx.data.sources import FileSource
from aponyx.config import RAW_DIR

# Find most recent raw file (hash-based naming)
def find_raw_file(pattern: str) -> Path:
    matches = list(raw_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No raw file found: {pattern}")
    # Use most recent file
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]

# Load from either bloomberg/ or synthetic/
cdx_file = find_raw_file("cdx_cdx_ig_5y_*.parquet")
source = FileSource(str(cdx_file))

df = fetch_cdx(source, security="cdx_ig_5y")
# Works identically for both Bloomberg and synthetic data
```

## Migration Path

Existing raw files without hashes are **not automatically migrated**. The hash-based system applies to:

1. **New Bloomberg downloads** (via `01_data_download.ipynb`)
2. **New synthetic generation** (via `generate_synthetic_data.py`)

Old files can coexist but should be regenerated to benefit from metadata tracking.

## Benefits

1. **Uniqueness:** Different date ranges create different files (no overwrites)
2. **Provenance:** Metadata JSON tracks exact parameters and timestamps
3. **Versioning:** Implicit versioning through hash without manual version numbers
4. **Consistency:** Identical convention across all data providers
5. **Reproducibility:** Full metadata enables exact reproduction of data pulls
6. **Cleanup Safety:** Hash-based names make it clear which files are duplicates

## Implementation Details

**Hash Function:** `fetch.py::save_to_raw()`

```python
def save_to_raw(
    df: pd.DataFrame,
    provider: str,
    instrument: str,
    raw_dir: Path,
    registry: DataRegistry | None = None,
    **metadata_params,
) -> Path:
    # Generate hash from content and metadata
    hash_input = "|".join([
        provider,
        instrument,
        str(df.index.min()),
        str(df.index.max()),
        str(len(df)),
        str(sorted(metadata_params.items())),
    ])
    file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
    
    # Save data and metadata sidecar
    filename = f"{instrument}_{file_hash}.parquet"
    # ...
```

**Synthetic Generator:** `sample_data.py::generate_for_fetch_interface()`

Uses identical hash generation for consistency.

## Related Documentation

- **Cache Design:** `src/aponyx/docs/caching_design.md`
- **Data Registry:** `src/aponyx/data/registry.py`
- **Bloomberg Config:** `src/aponyx/data/bloomberg_config.py`
- **Governance:** `src/aponyx/docs/governance_design.md`

---

**Last Updated:** November 16, 2025  
**Author:** stabilefrisur
