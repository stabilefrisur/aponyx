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
from .loaders import find_raw_file, load_instrument_from_raw

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
]
