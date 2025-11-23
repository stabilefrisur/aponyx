"""
Data layer for systematic macro credit strategy.

This module handles data fetching, cleaning, and transformation for:
- CDX indices (IG, HY, XO) across tenors
- VIX equity volatility index
- Credit ETFs (HYG, LQD) used for signal generation

All fetch functions produce standardized DataFrames with DatetimeIndex and validated schemas.
Supports multiple data providers: local files, Bloomberg Terminal, APIs.

Provides dataset registry for tracking and managing available market data files.
Time series transformations (diff, pct_change, log_return, z_score, normalized_change)
available for signal generation and analysis.
"""

import logging

from ..config import RAW_DIR
from .fetch import fetch_cdx, fetch_vix, fetch_etf
from .sources import FileSource, BloombergSource, APISource, DataSource
from .validation import (
    validate_cdx_schema,
    validate_vix_schema,
    validate_etf_schema,
    handle_duplicate_index,
)
from .bloomberg_config import validate_bloomberg_registry
from .registry import DataRegistry, DatasetEntry
from .transforms import apply_transform, TransformType
from .requirements import get_required_data_keys
from .fetch_registry import get_fetch_spec, list_instruments
from .loaders import find_raw_file, load_instrument_from_raw, load_signal_required_data

logger = logging.getLogger(__name__)


def get_available_sources() -> list[str]:
    """Get list of available data sources from RAW_DIR subdirectories.

    Returns
    -------
    list[str]
        List of available source names (subdirectory names under RAW_DIR).

    Notes
    -----
    Scans RAW_DIR for subdirectories and returns their names.
    Logs warning if subdirectory exists but is empty.
    """
    if not RAW_DIR.exists():
        logger.warning("RAW_DIR does not exist: %s", RAW_DIR)
        return []

    sources = []
    for item in RAW_DIR.iterdir():
        if item.is_dir():
            source_name = item.name
            sources.append(source_name)

            # Warn if directory is empty
            if not any(item.iterdir()):
                logger.debug("Data source directory is empty: %s", source_name)

    return sorted(sources)


__all__ = [
    # Fetch functions
    "fetch_cdx",
    "fetch_vix",
    "fetch_etf",
    # Data sources
    "FileSource",
    "BloombergSource",
    "APISource",
    "DataSource",
    "get_available_sources",
    # Validation
    "validate_cdx_schema",
    "validate_vix_schema",
    "validate_etf_schema",
    "validate_bloomberg_registry",
    "handle_duplicate_index",
    # Registry
    "DataRegistry",
    "DatasetEntry",
    # Transformations
    "apply_transform",
    "TransformType",
    # Requirements
    "get_required_data_keys",
    # Fetch registry
    "get_fetch_spec",
    "list_instruments",
    # Loaders
    "find_raw_file",
    "load_instrument_from_raw",
    "load_signal_required_data",
]
