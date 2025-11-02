"""  
Data layer for systematic macro credit strategy.

This module handles data fetching, cleaning, and transformation for:
- CDX indices (IG, HY, XO) across tenors
- VIX equity volatility index
- Credit ETFs (HYG, LQD) used for signal generation

All fetch functions produce standardized DataFrames with DatetimeIndex and validated schemas.
Supports multiple data providers: local files, Bloomberg Terminal, APIs.

Provides dataset registry for tracking and managing available market data files.
"""

from .fetch import fetch_cdx, fetch_vix, fetch_etf
from .sources import FileSource, BloombergSource, APISource, DataSource
from .validation import validate_cdx_schema, validate_vix_schema, validate_etf_schema
from .bloomberg_config import validate_bloomberg_registry
from .registry import DataRegistry, DatasetEntry

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
    # Registry
    "DataRegistry",
    "DatasetEntry",
]