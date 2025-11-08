"""
Parquet I/O utilities for time series data persistence.

Handles efficient storage and retrieval of market data (CDX spreads, VIX, ETF prices)
with metadata preservation and validation.
"""

import logging
from pathlib import Path
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
                "Date filtering requires DatetimeIndex. " f"Got {type(df.index).__name__}"
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
    logger.info("Found %d Parquet files in %s (pattern=%s)", len(files), directory, pattern)
    return files
