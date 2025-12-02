"""
Parquet I/O utilities for time series data and indicator cache persistence.

Handles efficient storage and retrieval of market data (CDX spreads, VIX, ETF prices)
and computed indicators with metadata preservation and validation.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def save_parquet(
    df: pd.DataFrame,
    path: str | Path,
    compression: str = "snappy",
    index: bool = True,
) -> Path:
    """
    Save DataFrame to Parquet with optimized settings for time series data.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to persist. For time series, index should be DatetimeIndex.
    path : str or Path
        Target file path. Parent directories created if needed.
    compression : str, default "snappy"
        Compression algorithm. Options: "snappy", "gzip", "brotli", "zstd".
    index : bool, default True
        Whether to write DataFrame index to file.

    Returns
    -------
    Path
        Absolute path to the saved file.

    Raises
    ------
    ValueError
        If DataFrame is empty or path is invalid.

    Examples
    --------
    >>> df = pd.DataFrame({'spread': [100, 105, 98]},
    ...                   index=pd.date_range('2024-01-01', periods=3))
    >>> save_parquet(df, 'data/cdx_ig_5y.parquet')
    """
    if df.empty:
        raise ValueError("Cannot save empty DataFrame")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Saving DataFrame to Parquet: path=%s, rows=%d, columns=%d, compression=%s",
        path,
        len(df),
        len(df.columns),
        compression,
    )

    df.to_parquet(
        path,
        engine="pyarrow",
        compression=compression,
        index=index,
    )

    logger.debug("Successfully saved %d bytes to %s", path.stat().st_size, path)
    return path.absolute()


def load_parquet(
    path: str | Path,
    columns: list[str] | None = None,
    start_date: pd.Timestamp | None = None,
    end_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Load DataFrame from Parquet with optional filtering.

    Parameters
    ----------
    path : str or Path
        Source file path.
    columns : list of str, optional
        Subset of columns to load. If None, loads all columns.
    start_date : pd.Timestamp, optional
        Filter data from this date (inclusive). Requires DatetimeIndex.
    end_date : pd.Timestamp, optional
        Filter data to this date (inclusive). Requires DatetimeIndex.

    Returns
    -------
    pd.DataFrame
        Loaded and optionally filtered DataFrame.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    ValueError
        If date filtering is requested but index is not DatetimeIndex.

    Examples
    --------
    >>> df = load_parquet('data/cdx_ig_5y.parquet',
    ...                   start_date=pd.Timestamp('2024-01-01'))
    >>> df = load_parquet('data/vix.parquet', columns=['close'])
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found: {path}")

    logger.info("Loading Parquet file: path=%s, columns=%s", path, columns or "all")

    df = pd.read_parquet(path, engine="pyarrow", columns=columns)

    # Apply date filtering if requested
    if start_date is not None or end_date is not None:
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError(
                f"Date filtering requires DatetimeIndex. Got {type(df.index).__name__}"
            )

        if start_date is not None:
            df = df[df.index >= start_date]
        if end_date is not None:
            df = df[df.index <= end_date]

        logger.debug(
            "Applied date filter: start=%s, end=%s, resulting_rows=%d",
            start_date,
            end_date,
            len(df),
        )

    logger.info("Loaded %d rows, %d columns from %s", len(df), len(df.columns), path)
    return df


def list_parquet_files(directory: str | Path, pattern: str = "*.parquet") -> list[Path]:
    """
    List all Parquet files in a directory matching a pattern.

    Parameters
    ----------
    directory : str or Path
        Directory to search.
    pattern : str, default "*.parquet"
        Glob pattern for file matching.

    Returns
    -------
    list of Path
        Sorted list of matching file paths.

    Examples
    --------
    >>> files = list_parquet_files('data/', pattern='cdx_*.parquet')
    >>> files = list_parquet_files('data/raw/')
    """
    directory = Path(directory)
    if not directory.exists():
        logger.debug("Directory does not exist: %s", directory)
        return []

    files = sorted(directory.glob(pattern))
    logger.info(
        "Found %d Parquet files in %s (pattern=%s)", len(files), directory, pattern
    )
    return files


def generate_indicator_cache_key(
    indicator_name: str,
    parameters: dict[str, Any],
    input_data: dict[str, pd.DataFrame],
) -> str:
    """
    Generate deterministic cache key for indicator computation.

    Cache key format: {indicator_name}_{params_hash}_{data_hash}

    Parameters
    ----------
    indicator_name : str
        Name of the indicator.
    parameters : dict[str, Any]
        Indicator computation parameters.
    input_data : dict[str, pd.DataFrame]
        Input market data DataFrames.

    Returns
    -------
    str
        Cache key string.

    Examples
    --------
    >>> key = generate_indicator_cache_key(
    ...     "cdx_etf_spread_diff",
    ...     {"lookback": 5},
    ...     {"cdx": cdx_df, "etf": etf_df}
    ... )
    >>> key
    'cdx_etf_spread_diff_a1b2c3d4_e5f6g7h8'
    """
    # Hash parameters
    params_str = json.dumps(parameters, sort_keys=True)
    params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:8]

    # Hash input data (concatenate all DataFrame hashes)
    data_hashes = []
    for key in sorted(input_data.keys()):
        df_hash = hashlib.sha256(
            pd.util.hash_pandas_object(input_data[key]).values
        ).hexdigest()[:8]
        data_hashes.append(df_hash)
    data_hash = hashlib.sha256("".join(data_hashes).encode()).hexdigest()[:8]

    cache_key = f"{indicator_name}_{params_hash}_{data_hash}"
    logger.debug("Generated cache key: %s", cache_key)
    return cache_key


def save_indicator_to_cache(
    indicator_series: pd.Series,
    cache_key: str,
    cache_dir: Path,
) -> Path:
    """
    Save computed indicator to cache.

    Parameters
    ----------
    indicator_series : pd.Series
        Computed indicator time series.
    cache_key : str
        Cache key from generate_indicator_cache_key().
    cache_dir : Path
        Root cache directory (e.g., data/cache/indicators/).

    Returns
    -------
    Path
        Path to saved cache file.

    Examples
    --------
    >>> from aponyx.config import INDICATOR_CACHE_DIR
    >>> cache_path = save_indicator_to_cache(
    ...     indicator_series,
    ...     "cdx_etf_spread_diff_a1b2c3d4_e5f6g7h8",
    ...     INDICATOR_CACHE_DIR
    ... )
    """
    cache_path = cache_dir / f"{cache_key}.parquet"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Convert Series to DataFrame for parquet storage
    df = indicator_series.to_frame(name="value")

    save_parquet(df, cache_path, compression="snappy", index=True)

    logger.info("Cached indicator: key=%s, rows=%d", cache_key, len(indicator_series))
    return cache_path


def load_indicator_from_cache(
    cache_key: str,
    cache_dir: Path,
) -> pd.Series | None:
    """
    Load indicator from cache if available.

    Parameters
    ----------
    cache_key : str
        Cache key from generate_indicator_cache_key().
    cache_dir : Path
        Root cache directory (e.g., data/cache/indicators/).

    Returns
    -------
    pd.Series or None
        Cached indicator series if found, None otherwise.

    Examples
    --------
    >>> from aponyx.config import INDICATOR_CACHE_DIR
    >>> indicator = load_indicator_from_cache(
    ...     "cdx_etf_spread_diff_a1b2c3d4_e5f6g7h8",
    ...     INDICATOR_CACHE_DIR
    ... )
    """
    cache_path = cache_dir / f"{cache_key}.parquet"

    if not cache_path.exists():
        logger.debug("Cache miss: key=%s", cache_key)
        return None

    try:
        df = load_parquet(cache_path)
        indicator_series = df["value"]
        logger.info("Cache hit: key=%s, rows=%d", cache_key, len(indicator_series))
        return indicator_series
    except Exception as e:
        logger.warning("Failed to load cache: key=%s, error=%s", cache_key, e)
        return None


def invalidate_indicator_cache(
    indicator_name: str | None = None,
    cache_dir: Path | None = None,
) -> int:
    """
    Invalidate indicator cache by deleting cache files.

    Parameters
    ----------
    indicator_name : str or None
        Specific indicator to invalidate. If None, invalidates all indicators.
    cache_dir : Path or None
        Cache directory. If None, uses default from config.

    Returns
    -------
    int
        Number of cache files deleted.

    Examples
    --------
    >>> from aponyx.config import INDICATOR_CACHE_DIR
    >>> # Invalidate specific indicator
    >>> deleted = invalidate_indicator_cache("cdx_etf_spread_diff", INDICATOR_CACHE_DIR)
    >>> # Invalidate all indicators
    >>> deleted = invalidate_indicator_cache(None, INDICATOR_CACHE_DIR)
    """
    if cache_dir is None:
        from ..config import INDICATOR_CACHE_DIR

        cache_dir = INDICATOR_CACHE_DIR

    if not cache_dir.exists():
        logger.debug("Cache directory does not exist: %s", cache_dir)
        return 0

    # Determine pattern for deletion
    if indicator_name:
        pattern = f"{indicator_name}_*.parquet"
    else:
        pattern = "*.parquet"

    # Delete matching files
    cache_files = list(cache_dir.glob(pattern))
    deleted_count = 0
    for cache_file in cache_files:
        try:
            cache_file.unlink()
            deleted_count += 1
            logger.debug("Deleted cache file: %s", cache_file)
        except Exception as e:
            logger.warning("Failed to delete cache file %s: %s", cache_file, e)

    logger.info(
        "Invalidated indicator cache: pattern=%s, deleted=%d",
        pattern,
        deleted_count,
    )
    return deleted_count
