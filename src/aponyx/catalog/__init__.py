"""
Unified YAML Catalog & CatalogManager module.

Provides a centralized interface for managing catalog configurations
(signals, strategies, transformations, securities) as YAML source files
with JSON generation for runtime registries.

Example
-------
>>> from aponyx.catalog import CatalogManager
>>> manager = CatalogManager()
>>> manager.load()
>>> result = manager.validate()
>>> if result.passed:
...     manager.sync()
"""

from aponyx.catalog.entries import (
    ChannelConfig,
    IndicatorTransformationEntry,
    InstrumentEntry,
    ScoreTransformationEntry,
    SecurityEntry,
    SignalEntry,
    SignalTransformationEntry,
    StrategyEntry,
)
from aponyx.catalog.loader import (
    load_catalogs_yaml,
    load_securities_yaml,
    save_catalogs_yaml,
    save_securities_yaml,
)
from aponyx.catalog.manager import CatalogManager
from aponyx.catalog.migration import migrate_json_to_yaml, verify_round_trip
from aponyx.catalog.sync import sync_to_json
from aponyx.catalog.validator import validate_catalogs

__all__ = [
    # Entry types
    "ChannelConfig",
    "IndicatorTransformationEntry",
    "InstrumentEntry",
    "ScoreTransformationEntry",
    "SecurityEntry",
    "SignalEntry",
    "SignalTransformationEntry",
    "StrategyEntry",
    # Loader functions
    "load_catalogs_yaml",
    "load_securities_yaml",
    "save_catalogs_yaml",
    "save_securities_yaml",
    # Manager
    "CatalogManager",
    # Migration
    "migrate_json_to_yaml",
    "verify_round_trip",
    # Sync
    "sync_to_json",
    # Validation
    "validate_catalogs",
]
