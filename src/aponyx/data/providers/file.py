"""
File-based data provider for Parquet and CSV files.

Handles local file loading with automatic format detection.
"""

import logging
from typing import Any

import pandas as pd

from ...persistence.parquet_io import load_parquet
from ..sources import FileSource

logger = logging.getLogger(__name__)


def fetch_from_file(
    source: FileSource,
    instrument: str,
    start_date: str | None = None,
    end_date: str | None = None,
    **params: Any,
) -> pd.DataFrame:
    """
    Fetch data from local Parquet or CSV file.

    Parameters
    ----------
    source : FileSource
        File source configuration with path.
    instrument : str
        Instrument identifier (for logging).
    start_date : str or None
        Optional start date filter (ISO format).
    end_date : str or None
        Optional end date filter (ISO format).
    **params : Any
        Additional parameters (unused for file provider).

    Returns
    -------
    pd.DataFrame
        Raw data loaded from file (validation happens in fetch layer).

    Raises
    ------
    ValueError
        If file format is not supported.
    FileNotFoundError
        If file does not exist.

    Notes
    -----
    - Automatically detects Parquet vs CSV from file extension
    - Date filtering applied after loading (files assumed small enough)
    - Does not perform schema validation (handled by fetch layer)
    """
    file_path = source.path
    logger.info("Fetching %s from file: %s", instrument, file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    # Load based on file type
    if file_path.suffix == ".parquet":
        df = load_parquet(file_path)
    elif file_path.suffix == ".csv":
        df = pd.read_csv(file_path)
        # Convert 'date' column to DatetimeIndex if present
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            logger.debug("Converted 'date' column to DatetimeIndex")
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    # Apply date filtering if requested
    if isinstance(df.index, pd.DatetimeIndex):
        if start_date is not None:
            start = pd.Timestamp(start_date)
            df = df[df.index >= start]
            logger.debug("Filtered to start_date >= %s: %d rows", start_date, len(df))

        if end_date is not None:
            end = pd.Timestamp(end_date)
            df = df[df.index <= end]
            logger.debug("Filtered to end_date <= %s: %d rows", end_date, len(df))

    logger.info("Loaded %d rows from file", len(df))
    return df
