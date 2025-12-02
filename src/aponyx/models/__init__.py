"""
Models layer for systematic credit strategies.

This module provides signal generation via the indicator + transformation composition pattern.

Module Organization:
-------------------
metadata.py         - Metadata dataclasses (SignalMetadata, IndicatorMetadata, TransformationMetadata)
registry.py         - Registry classes for catalog management
orchestrator.py     - compute_registered_signals() batch computation
signal_composer.py  - compose_signal() indicator + transformation composition
indicators.py       - Indicator compute functions
config.py           - SignalConfig dataclass
"""

from .config import SignalConfig
from .metadata import SignalMetadata
from .orchestrator import compute_registered_signals
from .registry import SignalRegistry

__all__ = [
    "SignalConfig",
    "SignalMetadata",
    "SignalRegistry",
    "compute_registered_signals",
]
