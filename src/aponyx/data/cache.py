"""
Transparent caching layer for fetched data.

Caches API/provider responses to local Parquet files with staleness tracking.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from ..persistence.parquet_io import save_parquet, load_parquet
from .registry import DataRegistry
from .sources import DataSource, resolve_provider

logger = logging.getLogger(__name__)


def _generate_cache_key(
    source: DataSource,
    instrument: str,
    start_date: str | None,
    end_date: str | None,
    **params: Any,
) -> str:
    """
    Generate unique cache key from fetch parameters.

    Parameters
    ----------
    source : DataSource
        Data source configuration.
    instrument : str
        Instrument identifier.
    start_date : str or None
        Start date.
    end_date : str or None
        End date.
    **params : Any
        Additional parameters.

    Returns
    -------
    str
        Hash-based cache key.
    """
    # Create stable string representation
    key_parts = [
        resolve_provider(source),
        instrument,
        start_date or "none",
        end_date or "none",
        str(sorted(params.items())),
    ]
    key_string = "|".join(key_parts)

    # Generate hash
    hash_obj = hashlib.sha256(key_string.encode())
    return hash_obj.hexdigest()[:16]


def get_cache_path(
    cache_dir: Path,
    provider: str,
    instrument: str,
    cache_key: str,
) -> Path:
    """
    Generate file path for cached data.

    Parameters
    ----------
    cache_dir : Path
        Base cache directory.
    provider : str
        Provider type (file, bloomberg, api).
    instrument : str
        Instrument identifier.
    cache_key : str
        Unique cache key.

    Returns
    -------
    Path
        Path to cache file.
    """
    provider_dir = cache_dir / provider
    provider_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize instrument name for filename
    safe_instrument = instrument.replace(".", "_").replace("/", "_")
    filename = f"{safe_instrument}_{cache_key}.parquet"

    return provider_dir / filename


def is_cache_stale(
    cache_path: Path,
    ttl_days: int | None = None,
) -> bool:
    """
    Check if cached data is stale based on TTL.

    Parameters
    ----------
    cache_path : Path
        Path to cached file.
    ttl_days : int or None
        Time-to-live in days. None means cache never expires.

    Returns
    -------
    bool
        True if cache is stale or doesn't exist.
    """
    if not cache_path.exists():
        return True

    if ttl_days is None:
        return False

    # Check file modification time
    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    age = datetime.now() - mtime

    is_stale = age > timedelta(days=ttl_days)

    if is_stale:
        logger.debug("Cache stale: age=%s, ttl=%d days", age, ttl_days)

    return is_stale


def get_cached_data(
    source: DataSource,
    instrument: str,
    cache_dir: Path,
    start_date: str | None = None,
    end_date: str | None = None,
    ttl_days: int | None = None,
    **params: Any,
) -> pd.DataFrame | None:
    """
    Retrieve data from cache if available and fresh.

    Parameters
    ----------
    source : DataSource
        Data source configuration.
    instrument : str
        Instrument identifier.
    cache_dir : Path
        Cache directory.
    start_date : str or None
        Start date filter.
    end_date : str or None
        End date filter.
    ttl_days : int or None
        Cache TTL in days.
    **params : Any
        Additional fetch parameters.

    Returns
    -------
    pd.DataFrame or None
        Cached data if available and fresh, None otherwise.
    """
    provider = resolve_provider(source)
    cache_key = _generate_cache_key(source, instrument, start_date, end_date, **params)
    cache_path = get_cache_path(cache_dir, provider, instrument, cache_key)

    if is_cache_stale(cache_path, ttl_days):
        logger.debug("Cache miss or stale: %s", cache_path.name)
        return None

    logger.info("Cache hit: %s", cache_path.name)
    return load_parquet(cache_path)


def save_to_cache(
    df: pd.DataFrame,
    source: DataSource,
    instrument: str,
    cache_dir: Path,
    registry: DataRegistry | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    **params: Any,
) -> Path:
    """
    Save fetched data to cache.

    Parameters
    ----------
    df : pd.DataFrame
        Data to cache.
    source : DataSource
        Data source configuration.
    instrument : str
        Instrument identifier.
    cache_dir : Path
        Cache directory.
    registry : DataRegistry or None
        Optional registry to register cached dataset.
    start_date : str or None
        Start date (for cache key).
    end_date : str or None
        End date (for cache key).
    **params : Any
        Additional parameters (for cache key).

    Returns
    -------
    Path
        Path to cached file.
    """
    provider = resolve_provider(source)
    cache_key = _generate_cache_key(source, instrument, start_date, end_date, **params)
    cache_path = get_cache_path(cache_dir, provider, instrument, cache_key)

    # Save to Parquet
    save_parquet(df, cache_path)
    logger.info("Cached data: path=%s, rows=%d", cache_path, len(df))

    # Register in catalog if provided
    if registry is not None:
        registry.register_dataset(
            name=f"cache_{instrument}_{cache_key}",
            file_path=cache_path,
            instrument=instrument,
            metadata={
                "provider": provider,
                "cached_at": datetime.now().isoformat(),
                "cache_key": cache_key,
                "params": params,
            },
        )

    return cache_path
