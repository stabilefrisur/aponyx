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
    ticker: str,
    instrument: str,
    security: str,
    start_date: str | None = None,
    end_date: str | None = None,
    **params: Any,
) -> pd.DataFrame:
    """
    Fetch data from local Parquet or CSV file using security-based lookup.

    Parameters
    ----------
    source : FileSource
        File source configuration with base_dir and security_mapping.
    ticker : str
        Ticker identifier (unused for file provider, for signature compatibility).
    instrument : str
        Instrument type (cdx, vix, etf).
    security : str
        Security identifier to fetch (e.g., 'cdx_ig_5y', 'vix', 'hyg').
    start_date : str or None
        Optional start date filter (ISO format, unused for file provider).
    end_date : str or None
        Optional end date filter (ISO format, unused for file provider).
    **params : Any
        Additional parameters (unused for file provider).

    Returns
    -------
    pd.DataFrame
        Raw data loaded from file (validation happens in fetch layer).

    Raises
    ------
    ValueError
        If security not found in mapping or file format not supported.
    FileNotFoundError
        If file does not exist.

    Notes
    -----
    - Uses security_mapping to resolve security ID to filename
    - Automatically detects Parquet vs CSV from file extension
    - Adds 'security' column if instrument requires it
    - Date filtering not performed (files pre-filtered to match needs)
    """
    # Resolve security to filename
    if security not in source.security_mapping:
        available = ", ".join(sorted(source.security_mapping.keys()))
        raise ValueError(
            f"Security '{security}' not found in registry. Available: {available}"
        )

    filename = source.security_mapping[security]
    file_path = source.base_dir / filename

    logger.info(
        "Fetching %s (security=%s) from file: %s", instrument, security, file_path
    )

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

    # Add security column if instrument requires it
    from ..bloomberg_config import get_instrument_spec

    try:
        inst_spec = get_instrument_spec(instrument)
        if inst_spec.requires_security_metadata and "security" not in df.columns:
            df["security"] = security
            logger.debug("Added security column: %s", security)
    except ValueError:
        # Unknown instrument type, skip metadata enrichment
        logger.debug(
            "Unknown instrument type '%s', skipping metadata enrichment", instrument
        )

    logger.info("Loaded %d rows from file", len(df))
    return df
