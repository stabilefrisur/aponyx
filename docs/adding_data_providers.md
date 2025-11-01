# Adding Data Providers

## Overview

The data layer uses a **provider pattern** to support multiple data sources (files, Bloomberg, APIs) through a common interface. This guide shows how to add a new data provider to the framework.

**Goal:** Extend data sources without modifying existing code—add new providers as separate modules.

## Provider Architecture

### Current Providers

| Provider | Module | Status | Use Case |
|----------|--------|--------|----------|
| `FileSource` | `providers/file.py` | ✅ Implemented | Local Parquet/CSV files |
| `BloombergSource` | `providers/bloomberg.py` | ✅ Implemented | Bloomberg Terminal data (requires manual `blpapi` install) |
| `APISource` | *(not yet created)* | ❌ Not implemented | REST API endpoints |

### Bloomberg Provider Setup

The Bloomberg provider requires manual installation of the `blpapi` library:

1. Download `blpapi` from Bloomberg's developer portal
2. Install manually: `pip install path/to/blpapi-*.whl`
3. Install aponyx with Bloomberg support: `uv pip install aponyx[bloomberg]`

The `xbbg` wrapper is included in the `bloomberg` optional dependency, but `blpapi` itself must be installed separately due to Bloomberg's proprietary distribution.

### Provider Interface

All providers implement:

```python
from typing import Protocol
import pandas as pd

class DataSource(Protocol):
    """Protocol for data source implementations."""
    
    def fetch(self, **params) -> pd.DataFrame:
        """
        Fetch data according to provider-specific parameters.
        
        Returns
        -------
        pd.DataFrame
            Raw data with consistent index and column structure.
        """
        ...
```

## Adding a New Provider

### Step 1: Create Provider Module

Create `src/aponyx/data/providers/my_provider.py`:

```python
"""
Custom data provider implementation.

Fetches data from [describe your source].
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class MyCustomSource:
    """
    Data source for [your data provider].
    
    Parameters
    ----------
    connection_params : dict[str, Any]
        Provider-specific connection parameters.
    cache : Cache | None, optional
        Optional cache instance for caching results.
    """
    
    def __init__(
        self,
        connection_params: dict[str, Any],
        cache: Any | None = None,
    ):
        self.connection_params = connection_params
        self.cache = cache
        logger.info("Initialized MyCustomSource: params=%s", connection_params)
    
    def fetch(self, **query_params) -> pd.DataFrame:
        """
        Fetch data from custom source.
        
        Parameters
        ----------
        **query_params
            Provider-specific query parameters (ticker, date range, etc.).
        
        Returns
        -------
        pd.DataFrame
            Raw data with datetime index.
        """
        logger.info("Fetching data: params=%s", query_params)
        
        # Check cache first (if available)
        if self.cache:
            cache_key = self._generate_cache_key(query_params)
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.debug("Cache hit: %s", cache_key)
                return cached_data
        
        # Fetch from source
        raw_data = self._fetch_from_source(query_params)
        
        # Cache result (if cache available)
        if self.cache:
            self.cache.set(cache_key, raw_data)
            logger.debug("Cached data: %s", cache_key)
        
        return raw_data
    
    def _fetch_from_source(self, params: dict[str, Any]) -> pd.DataFrame:
        """
        Implement provider-specific data fetching logic.
        
        This is where you connect to your data source and retrieve data.
        """
        # Your implementation here
        # Example: API call, database query, etc.
        raise NotImplementedError("Implement provider-specific fetch logic")
    
    def _generate_cache_key(self, params: dict[str, Any]) -> str:
        """Generate deterministic cache key from parameters."""
        # Simple hash-based key generation
        import hashlib
        param_str = str(sorted(params.items()))
        return f"mycustom_{hashlib.md5(param_str.encode()).hexdigest()[:12]}"
```

### Step 2: Update Provider Init

Add to `src/aponyx/data/providers/__init__.py`:

```python
"""Data provider implementations."""

from .file import FileSource
from .bloomberg import BloombergSource
from .my_provider import MyCustomSource  # Add new provider

__all__ = [
    "FileSource",
    "BloombergSource",
    "MyCustomSource",  # Export new provider
]
```

### Step 3: Create Fetch Function

Add to `src/aponyx/data/fetch.py`:

```python
def fetch_my_data(
    source: MyCustomSource,
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """
    Fetch custom data using MyCustomSource provider.
    
    Parameters
    ----------
    source : MyCustomSource
        Data source instance.
    ticker : str
        Instrument identifier.
    start_date : str | None, optional
        Start date (YYYY-MM-DD format).
    end_date : str | None, optional
        End date (YYYY-MM-DD format).
    
    Returns
    -------
    pd.DataFrame
        Validated data with datetime index and required columns.
    """
    logger.info("Fetching data for %s", ticker)
    
    # Fetch raw data
    query_params = {"ticker": ticker}
    if start_date:
        query_params["start_date"] = start_date
    if end_date:
        query_params["end_date"] = end_date
    
    raw_df = source.fetch(**query_params)
    
    # Validate using appropriate schema
    from aponyx.data.validation import validate_schema
    validated_df = validate_schema(raw_df, schema_type="my_custom")
    
    logger.info("Fetched %d rows for %s", len(validated_df), ticker)
    return validated_df
```

### Step 4: Add Schema Validation (Optional)

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

### Step 5: Write Tests

Create `tests/data/test_my_provider.py`:

```python
"""Tests for custom data provider."""

import pytest
import pandas as pd
from aponyx.data.providers import MyCustomSource
from aponyx.data import fetch_my_data


@pytest.fixture
def mock_source():
    """Create test data source."""
    connection_params = {"endpoint": "https://api.example.com"}
    return MyCustomSource(connection_params)


def test_fetch_basic(mock_source, monkeypatch):
    """Test basic data fetching."""
    # Mock the internal fetch method
    def mock_fetch(params):
        return pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "value": range(10),
        })
    
    monkeypatch.setattr(mock_source, "_fetch_from_source", mock_fetch)
    
    # Fetch data
    df = fetch_my_data(mock_source, ticker="TEST")
    
    # Validate
    assert len(df) == 10
    assert "value" in df.columns
```

## Example: REST API Provider

### Implementation

```python
"""REST API data provider."""

import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class APISource:
    """
    Generic REST API data source.
    
    Parameters
    ----------
    base_url : str
        API base URL.
    api_key : str | None, optional
        API authentication key.
    cache : Cache | None, optional
        Optional cache instance.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        cache: Any | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.cache = cache
        logger.info("Initialized APISource: url=%s", base_url)
    
    def fetch(self, endpoint: str, **params) -> pd.DataFrame:
        """
        Fetch data from API endpoint.
        
        Parameters
        ----------
        endpoint : str
            API endpoint path (e.g., "/market-data/cdx").
        **params
            Query parameters for API request.
        
        Returns
        -------
        pd.DataFrame
            JSON response converted to DataFrame.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add authentication if available
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        logger.info("GET %s with params=%s", url, params)
        
        # Make request
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        # Parse JSON to DataFrame
        data = response.json()
        df = pd.DataFrame(data)
        
        # Convert date column if present
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        
        logger.debug("Fetched %d rows from API", len(df))
        return df
```

### Usage

```python
from aponyx.data.providers import APISource
from aponyx.data.cache import Cache

# Setup API source with caching
cache = Cache(ttl_seconds=3600)
api = APISource(
    base_url="https://api.example.com",
    api_key="your-key-here",
    cache=cache,
)

# Fetch data
df = api.fetch(
    endpoint="/market-data/cdx",
    ticker="CDX.NA.IG.5Y",
    start_date="2024-01-01",
    end_date="2024-12-31",
)
```

## Provider Design Patterns

### Pattern 1: Connection Pooling

```python
class PooledDatabaseSource:
    """Database source with connection pooling."""
    
    def __init__(self, connection_string: str, pool_size: int = 5):
        from sqlalchemy import create_engine
        self.engine = create_engine(
            connection_string,
            pool_size=pool_size,
            pool_pre_ping=True,
        )
    
    def fetch(self, query: str, **params) -> pd.DataFrame:
        """Execute SQL query with connection pool."""
        return pd.read_sql(query, self.engine, params=params)
```

### Pattern 2: Lazy Initialization

```python
class LazyBloombergSource:
    """Bloomberg source with lazy connection."""
    
    def __init__(self):
        self._connection = None
    
    @property
    def connection(self):
        """Initialize connection on first use."""
        if self._connection is None:
            from bloomberg import connect  # Heavy import
            self._connection = connect()
            logger.info("Bloomberg connection established")
        return self._connection
    
    def fetch(self, ticker: str, **params) -> pd.DataFrame:
        """Fetch using lazy-initialized connection."""
        return self.connection.get_data(ticker, **params)
```

### Pattern 3: Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustAPISource:
    """API source with automatic retry on failures."""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
    )
    def fetch(self, **params) -> pd.DataFrame:
        """Fetch with automatic retry on network errors."""
        response = requests.get(self.url, params=params)
        response.raise_for_status()
        return pd.DataFrame(response.json())
```

## Best Practices

1. **Implement caching support** for expensive data fetching
2. **Log all operations** (connections, queries, errors)
3. **Validate output schema** before returning data
4. **Handle errors gracefully** with informative messages
5. **Use type hints** for all parameters and return values
6. **Test with mocked data** to avoid external dependencies
7. **Document connection requirements** (credentials, network access)
8. **Follow naming convention**: `*Source` for provider classes

## Troubleshooting

### Provider Not Found

```python
# Check import
from aponyx.data.providers import MyCustomSource  # Should work

# Verify __init__.py exports
from aponyx.data import providers
print(dir(providers))  # Should list MyCustomSource
```

### Cache Not Working

```python
# Ensure cache is passed to provider
from aponyx.data.cache import Cache

cache = Cache()
source = MyCustomSource(params, cache=cache)  # Pass cache here

# Enable debug logging to see cache hits/misses
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Authentication Failures

```python
# Don't hardcode credentials in code
import os

api_key = os.environ.get("MY_API_KEY")
if not api_key:
    raise ValueError("MY_API_KEY environment variable not set")

source = APISource(base_url="...", api_key=api_key)
```

---

**Maintained by stabilefrisur**  
**Last Updated:** October 31, 2025
