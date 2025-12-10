"""
Models layer for systematic credit strategies.

This module provides signal generation via the four-stage transformation pipeline:
Security → Indicator → Score → Signal → Position

Module Organization:
-------------------
metadata.py         - Metadata dataclasses (SignalMetadata, IndicatorMetadata, TransformationMetadata, SignalTransformationMetadata)
registry.py         - Registry classes for catalog management (IndicatorTransformationRegistry, ScoreTransformationRegistry, SignalTransformationRegistry, SignalRegistry)
orchestrator.py     - compute_registered_signals() batch computation
signal_composer.py  - compose_signal() four-stage pipeline composition
indicators.py       - Indicator compute functions
config.py           - SignalConfig dataclass
"""

from .config import SignalConfig
from .metadata import (
    CatalogValidationError,
    IndicatorMetadata,
    SignalMetadata,
    SignalTransformationMetadata,
    TransformationMetadata,
)
from .orchestrator import compute_registered_signals
from .registry import (
    IndicatorTransformationRegistry,
    ScoreTransformationRegistry,
    SignalRegistry,
    SignalTransformationRegistry,
)

__all__ = [
    "CatalogValidationError",
    "IndicatorMetadata",
    "IndicatorTransformationRegistry",
    "ScoreTransformationRegistry",
    "SignalConfig",
    "SignalMetadata",
    "SignalRegistry",
    "SignalTransformationMetadata",
    "SignalTransformationRegistry",
    "TransformationMetadata",
    "compute_registered_signals",
]
