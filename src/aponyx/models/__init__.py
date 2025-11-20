"""
Models layer for systematic credit strategies.

This module provides signal generation and strategy logic for the CDX overlay pilot.

Module Organization (Option B pattern):
---------------------------------------
metadata.py      - SignalMetadata dataclass
registry.py      - SignalRegistry catalog management
orchestrator.py  - compute_registered_signals() batch computation
signals.py       - Individual signal compute functions
config.py        - SignalConfig dataclass
"""

from .signals import (
    compute_cdx_etf_basis,
    compute_cdx_vix_gap,
    compute_spread_momentum,
)
from .config import SignalConfig
from .metadata import SignalMetadata
from .registry import SignalRegistry
from .orchestrator import compute_registered_signals, get_required_data_keys

__all__ = [
    "compute_cdx_etf_basis",
    "compute_cdx_vix_gap",
    "compute_spread_momentum",
    "SignalConfig",
    "SignalMetadata",
    "SignalRegistry",
    "compute_registered_signals",
    "get_required_data_keys",
]
