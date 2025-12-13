# Adding Data Providers

## Overview

The data layer uses a **provider pattern** to support multiple data sources (files, Bloomberg, APIs) through a common interface. This guide shows how to add a new data provider to the framework.

**Goal:** Extend data sources without modifying existing code—add new providers as separate modules.

## Provider Architecture

### Current Providers

| Provider | Module | Status | Use Case |
|----------|--------|--------|----------|
| `FileSource` | `providers/file.py` | ✅ Implemented | Local Parquet/CSV files |
| `BloombergSource` | `providers/bloomberg.py` | ✅ Implemented | Bloomberg Terminal data (requires `xbbg` and manual `blpapi` install) |
| `APISource` | `sources.py` (dataclass only) | ⚠️ Defined but no fetch implementation | REST API endpoints |

### Bloomberg Provider Setup

The Bloomberg provider requires manual installation of the `blpapi` library:

1. Download `blpapi` from Bloomberg's developer portal
2. Install manually: `pip install path/to/blpapi-*.whl`
3. Install aponyx with Bloomberg support: `uv pip install aponyx[bloomberg]`

The `xbbg` wrapper is included in the `bloomberg` optional dependency, but `blpapi` itself must be installed separately due to Bloomberg's proprietary distribution.

**Intraday Updates:** Bloomberg provider supports efficient current-day updates via BDP.

---

## Data Storage Architecture

The project uses a three-tier storage structure:

| Directory | Purpose | Lifecycle | Regenerable |
|-----------|---------|-----------|-------------|
| `data/raw/` | Original source data (Bloomberg downloads, synthetic generation) | **Permanent** — Never auto-deleted | ❌ No |
| `data/cache/` | Performance optimization for repeated reads | **Temporary** — TTL-based expiration | ✅ Yes |
| `data/workflows/` | Timestamped workflow outputs (signals, backtests, reports, visualizations) | **Temporary** — Recomputable from raw | ✅ Yes |

**Data Flow:**
```
Raw Storage (Bloomberg/Synthetic)
    ↓
Cache Layer (TTL-based, automatic)
    ↓
Models/Signals
    ↓
Processed Storage (Results)
```

**Key Principle:** Raw data is the source of truth. Cache and processed data can always be regenerated from raw.

### Raw Data Storage

**File Naming:** `{instrument}_{security}_{hash}.parquet`

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

**Metadata Sidecar:** Each `.parquet` file has a corresponding `.json` metadata file:

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

### Cache Layer

**Purpose:** Transparent time-to-live (TTL) based caching for data fetching operations.

**Cache Location:**
```
data/
  cache/
    file/           # Temporary cache from FileSource loads
      cdx_ig_5y_abc123.parquet
```

**Configuration:**
```python
from aponyx.config import CACHE_ENABLED, CACHE_TTL_DAYS

# Default: enabled, 1 day TTL
# Control per fetch call:
df = fetch_cdx(source, security="cdx_ig_5y", use_cache=True)  # Use cache
df = fetch_cdx(source, security="cdx_ig_5y", use_cache=False)  # Skip cache
```

**Automatic Invalidation:**
1. **TTL expiration:** Entry older than `CACHE_TTL_DAYS`
2. **Source modification:** Source file modified after cache creation

**Intraday Updates (Bloomberg only):**
```python
# Morning: Full history
cdx_df = fetch_cdx(BloombergSource(), security="cdx_ig_5y")

# Afternoon: Update only today (~10x faster)
cdx_df = fetch_cdx(BloombergSource(), security="cdx_ig_5y", update_current_day=True)
```

**Benefits:**
- ~10x faster than full refetch
- 500x less data transfer (1 point vs 1800 days)
- Preserves historical data in cache

### Provider Interface

Providers are defined as dataclasses and used by fetch functions:

```python
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

@dataclass(frozen=True)
class FileSource:
    """File-based data source (Parquet or CSV)."""
    path: Path

@dataclass(frozen=True)
class BloombergSource:
    """Bloomberg Terminal data source."""
    pass

# Fetch functions handle provider-specific logic
def fetch_from_file(
    file_path: str | Path,
    instrument: str,
    start_date: str | None = None,
    end_date: str | None = None,
    **params,
) -> pd.DataFrame:
    """Fetch data from local file."""
    ...
```

## Adding a New Provider

### Step 1: Define Data Source

Add to `src/aponyx/data/sources.py`:

```python
"""Data source configuration for pluggable data providers."""

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class MyCustomSource:
    """
    Custom data source for [your provider].
    
    Attributes
    ----------
    endpoint : str
        API endpoint or connection string.
    params : dict[str, Any] | None
        Additional connection parameters.
    """
    endpoint: str
    params: dict[str, Any] | None = None


# Update DataSource union type
DataSource = FileSource | BloombergSource | MyCustomSource
```

### Step 2: Create Provider Fetch Function

Create `src/aponyx/data/providers/my_provider.py`:

```python
"""
Custom data provider fetch implementation.

Fetches data from [describe your source].
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_from_mycustom(
    endpoint: str,
    instrument: str,
    start_date: str | None = None,
    end_date: str | None = None,
    **params: Any,
) -> pd.DataFrame:
        """
        Fetch data from custom source.
        
        Parameters
        ----------
        endpoint : str
            API endpoint or data source URL.
        instrument : str
            Instrument identifier.
        start_date : str | None
            Optional start date filter (ISO format).
        end_date : str | None
            Optional end date filter (ISO format).
        **params : Any
            Additional provider-specific parameters.
        
        Returns
        -------
        pd.DataFrame
            Raw data with datetime index.
            
        Notes
        -----
        Caching is handled by the fetch layer, not provider implementation.
        """
        logger.info("Fetching %s from endpoint: %s", instrument, endpoint)
        
        # Implement provider-specific data fetching logic
        # Example: API call, database query, etc.
        # Your implementation here
        
        # Build query parameters
        query_params = {"instrument": instrument}
        if start_date:
            query_params["start_date"] = start_date
        if end_date:
            query_params["end_date"] = end_date
        query_params.update(params)
        
        # Fetch data (example - implement actual logic)
        df = self._make_request(endpoint, query_params)
        
        logger.info("Loaded %d rows from custom source", len(df))
        return df
    
    def _make_request(self, endpoint: str, params: dict[str, Any]) -> pd.DataFrame:
        """Make actual request to data source."""
        raise NotImplementedError("Implement provider-specific request logic")
```

### Step 3: Update Provider Init

Add to `src/aponyx/data/providers/__init__.py`:

```python
"""Data provider implementations."""

from .file import fetch_from_file
from .bloomberg import fetch_from_bloomberg
from .my_provider import fetch_from_mycustom  # Add new provider

__all__ = [
    "fetch_from_file",
    "fetch_from_bloomberg",
    "fetch_from_mycustom",  # Export new fetch function
]
```

### Step 4: Integrate with Fetch Layer

Update `src/aponyx/data/fetch.py` to support new provider:

```python
from .sources import MyCustomSource, resolve_provider
from .providers.my_provider import fetch_from_mycustom

def _get_provider_fetch_function(source: DataSource):
    """Get fetch function for data source."""
    provider_type = resolve_provider(source)
    
    if provider_type == "file":
        return fetch_from_file
    elif provider_type == "bloomberg":
        return fetch_from_bloomberg
    elif provider_type == "mycustom":  # Add new provider
        return fetch_from_mycustom
    else:
        raise ValueError(f"Unsupported provider: {provider_type}")

# Then use in instrument fetch functions:
def fetch_cdx(
    source: DataSource | None = None,
    security: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = CACHE_ENABLED,
) -> pd.DataFrame:
    """Fetch CDX data from any provider."""
    # ... caching logic ...
    
    fetch_fn = _get_provider_fetch_function(source)
    
    if isinstance(source, MyCustomSource):
        df = fetch_fn(
            endpoint=source.endpoint,
            instrument="cdx",
            start_date=start_date,
            end_date=end_date,
            **(source.params or {}),
        )
    # ... other providers ...
```

### Step 5: Update Provider Resolution

Add to `src/aponyx/data/sources.py`:

```python
def resolve_provider(source: DataSource) -> str:
    """Resolve data source to provider type identifier."""
    if isinstance(source, FileSource):
        return "file"
    elif isinstance(source, BloombergSource):
        return "bloomberg"
    elif isinstance(source, MyCustomSource):  # Add new provider
        return "mycustom"
    else:
        raise ValueError(f"Unknown source type: {type(source)}")
```

### Step 6: Add Schema Validation (Optional)

If your data has a specific structure, add a schema in `src/aponyx/data/schemas.py`:

```python
from dataclasses import dataclass

@dataclass
class MyCustomSchema:
    """Schema for custom data provider."""
    
    required_columns: list[str] = field(
        default_factory=lambda: ["date", "value", "volume"]
    )
    date_column: str = "date"
    numeric_columns: list[str] = field(
        default_factory=lambda: ["value", "volume"]
    )
```

### Step 7: Write Tests

Create `tests/data/test_my_provider.py`:

```python
"""Tests for custom data provider."""

import pytest
import pandas as pd
from aponyx.data import fetch_cdx
from aponyx.data.sources import MyCustomSource


def test_fetch_basic(monkeypatch):
    """Test basic data fetching with custom provider."""
    # Create source
    source = MyCustomSource(
        endpoint="https://api.example.com",
        params={"api_key": "test"},
    )
    
    # Mock the provider fetch function
    def mock_fetch(*args, **kwargs):
        return pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "spread": range(100, 110),
            "security": ["cdx_ig_5y"] * 10,
        }).set_index("date")
    
    from aponyx.data import providers
    monkeypatch.setattr(providers, "fetch_from_mycustom", mock_fetch)
    
    # Fetch data
    df = fetch_cdx(source, security="cdx_ig_5y")
    
    # Validate
    assert len(df) == 10
    assert "spread" in df.columns
```

## Example: REST API Provider

### Source Definition

Add to `src/aponyx/data/sources.py`:

```python
@dataclass(frozen=True)
class APISource:
    """
    Generic REST API data source.
    
    Attributes
    ----------
    endpoint : str
        API endpoint URL.
    api_key : str | None
        API authentication key.
    params : dict[str, Any] | None
        Additional request parameters.
    """
    endpoint: str
    api_key: str | None = None
    params: dict[str, Any] | None = None

# Update DataSource union
DataSource = FileSource | BloombergSource | APISource
```

### Provider Implementation

Create `src/aponyx/data/providers/api.py`:

```python
"""REST API data provider."""

import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)


def fetch_from_api(
    endpoint: str,
    instrument: str,
    api_key: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    **params: Any,
) -> pd.DataFrame:
    """
    Fetch data from REST API endpoint.
    
    Parameters
    ----------
    endpoint : str
        API endpoint URL.
    instrument : str
        Instrument identifier.
    api_key : str | None
        Optional API key for authentication.
    start_date : str | None
        Start date filter (ISO format).
    end_date : str | None
        End date filter (ISO format).
    **params : Any
        Additional query parameters.
    
    Returns
    -------
    pd.DataFrame
        JSON response converted to DataFrame with DatetimeIndex.
    """
    # Build request parameters
    query_params = {"instrument": instrument}
    if start_date:
        query_params["start_date"] = start_date
    if end_date:
        query_params["end_date"] = end_date
    query_params.update(params)
    
    # Add authentication if available
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    logger.info("GET %s with params=%s", endpoint, query_params)
    
    # Make request
    response = requests.get(endpoint, params=query_params, headers=headers)
    response.raise_for_status()
    
    # Parse JSON to DataFrame
    data = response.json()
    df = pd.DataFrame(data)
    
    # Convert date column if present
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    
    logger.info("Fetched %d rows from API", len(df))
    return df
```

### Usage

```python
from aponyx.data import fetch_cdx
from aponyx.data.sources import MyCustomSource

# Setup custom source
source = MyCustomSource(
    endpoint="https://api.example.com/market-data",
    params={"api_key": "your-key-here"},
)

# Fetch data (caching handled automatically)
df = fetch_cdx(
    source=source,
    security="cdx_ig_5y",
    start_date="2024-01-01",
    end_date="2024-12-31",
)
```

## Provider Design Patterns

### Pattern 1: Stateful Connection

```python
# For providers requiring persistent connections,
# manage state in module-level variables

_connection = None

def _get_connection():
    """Get or create connection instance."""
    global _connection
    if _connection is None:
        _connection = initialize_connection()
        logger.info("Connection established")
    return _connection

def fetch_from_database(
    query: str,
    instrument: str,
    **params,
) -> pd.DataFrame:
    """Fetch using persistent connection."""
    conn = _get_connection()
    return pd.read_sql(query, conn, params=params)
```

### Pattern 2: Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
)
def fetch_from_api(
    endpoint: str,
    instrument: str,
    **params,
) -> pd.DataFrame:
    """Fetch with automatic retry on network errors."""
    response = requests.get(endpoint, params=params)
    response.raise_for_status()
    return pd.DataFrame(response.json())
```

### Pattern 3: Batch Fetching

```python
def fetch_from_batch_api(
    endpoint: str,
    instrument: str,
    start_date: str | None = None,
    end_date: str | None = None,
    batch_size: int = 1000,
    **params,
) -> pd.DataFrame:
    """Fetch data in batches for large date ranges."""
    all_data = []
    
    # Split date range into batches
    batches = _create_date_batches(start_date, end_date, batch_size)
    
    for batch_start, batch_end in batches:
        logger.debug("Fetching batch: %s to %s", batch_start, batch_end)
        batch_df = _fetch_single_batch(
            endpoint,
            instrument,
            batch_start,
            batch_end,
            **params,
        )
        all_data.append(batch_df)
    
    # Combine all batches
    return pd.concat(all_data).sort_index()
```

## Best Practices

1. **Define data sources as frozen dataclasses** for immutability
2. **Implement fetch functions** instead of class methods for simplicity
3. **Let the fetch layer handle caching** - providers should focus on data retrieval
4. **Log all operations** (connections, queries, errors) using %-formatting
5. **Validate output schema** in the fetch layer, not provider
6. **Handle errors gracefully** with informative messages
7. **Use type hints** for all parameters and return values
8. **Test with mocked data** to avoid external dependencies
9. **Document connection requirements** (credentials, network access)
10. **Follow naming convention**: `fetch_from_*` for provider functions

## Troubleshooting

### Provider Not Found

```python
# Check import
from aponyx.data.providers import fetch_from_mycustom  # Should work

# Verify __init__.py exports
from aponyx.data import providers
print(dir(providers))  # Should list fetch_from_mycustom
```

### Cache Not Working

```python
# Enable debug logging to see cache operations
import logging
logging.basicConfig(level=logging.DEBUG)

# Check if caching is enabled
from aponyx.config import CACHE_ENABLED, CACHE_TTL_DAYS
print(f"Cache enabled: {CACHE_ENABLED}, TTL: {CACHE_TTL_DAYS} days")

# Explicitly control cache usage
df = fetch_cdx(source, security="cdx_ig_5y", use_cache=True)
```

### Authentication Failures

```python
# Don't hardcode credentials in source definitions
import os

api_key = os.environ.get("MY_API_KEY")
if not api_key:
    raise ValueError("MY_API_KEY environment variable not set")

source = APISource(
    endpoint="https://api.example.com",
    api_key=api_key,
)
```

---

**Maintained by:** stabilefrisur  
**Last Updated:** December 13, 2025
