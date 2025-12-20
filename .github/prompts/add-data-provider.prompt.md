---
description: Create a new data provider following the DataSource protocol
name: Add Data Provider
---

# Create New Data Provider

Create a new data provider following the DataSource protocol pattern.

## User Request

${input:provider_description:Describe the data provider you want to create}

## Implementation Steps

### Step 1: Define Source Dataclass

Add to `src/aponyx/data/sources.py`:

```python
@dataclass(frozen=True)
class MySource:
    """Configuration for my data provider."""
    endpoint: str
    api_key: str | None = None
    timeout_seconds: int = 30
```

### Step 2: Create Provider Module

Create `src/aponyx/data/providers/my_provider.py`:

```python
"""My custom data provider implementation."""

import logging
from typing import Any

import pandas as pd

from aponyx.data.sources import MySource

logger = logging.getLogger(__name__)


def fetch_from_my_source(
    source: MySource,
    instrument: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """
    Fetch data from my custom provider.
    
    Parameters
    ----------
    source : MySource
        Source configuration.
    instrument : str
        Instrument identifier.
    start_date : str or None, optional
        Start date in YYYY-MM-DD format.
    end_date : str or None, optional
        End date in YYYY-MM-DD format.
    
    Returns
    -------
    pd.DataFrame
        Data with DatetimeIndex and appropriate columns.
    
    Raises
    ------
    ValueError
        If instrument not found or invalid date range.
    """
    logger.info("Fetching %s from my source", instrument)
    
    # Implementation...
    df = pd.DataFrame()  # Your fetch logic
    
    # REQUIRED: Ensure DatetimeIndex
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    
    return df
```

### Step 3: Register Provider

Update `resolve_provider` in `src/aponyx/data/sources.py`:

```python
def resolve_provider(source: DataSource) -> Any:
    """Resolve provider function based on source type."""
    if isinstance(source, FileSource):
        from .providers.file_provider import fetch_from_file
        return fetch_from_file
    elif isinstance(source, BloombergSource):
        from .providers.bloomberg import fetch_from_bloomberg
        return fetch_from_bloomberg
    elif isinstance(source, MySource):
        from .providers.my_provider import fetch_from_my_source
        return fetch_from_my_source
    else:
        raise ValueError(f"Unknown source type: {type(source)}")
```

### Step 4: Add Tests

Create `tests/data/providers/test_my_provider.py`:

```python
"""Tests for my custom data provider."""

import pandas as pd
import pytest

from aponyx.data.sources import MySource
from aponyx.data.providers.my_provider import fetch_from_my_source


class TestMyProvider:
    """Tests for my provider."""
    
    def test_fetch_returns_dataframe_with_datetime_index(self):
        """Verify return type and index."""
        source = MySource(endpoint="https://api.example.com")
        df = fetch_from_my_source(source, "test_instrument")
        
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)
    
    def test_fetch_with_date_range(self):
        """Verify date filtering works."""
        source = MySource(endpoint="https://api.example.com")
        df = fetch_from_my_source(
            source, 
            "test_instrument",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        
        assert df.index.min() >= pd.Timestamp("2024-01-01")
        assert df.index.max() <= pd.Timestamp("2024-12-31")
```

## Provider Pattern Constraints

1. **All DataFrames MUST have DatetimeIndex**
2. Use frozen dataclasses for source configs
3. No imports from models/backtest/evaluation layers
4. Implement validation for data ranges (CDX: 0-10,000 bps, VIX: 0-200)

## Validation

After implementation:
1. Run `uv run pytest tests/data/providers/test_my_provider.py -v`
2. Run `uv run mypy src/aponyx/data/`
