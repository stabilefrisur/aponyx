"""
CatalogManager for unified catalog operations.

Provides a central interface for loading, validating, and syncing
catalog configurations between YAML sources and JSON outputs.
"""

import logging
from pathlib import Path
from typing import Any

from aponyx.catalog.data import CatalogsData, SecuritiesData
from aponyx.catalog.entries import (
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
from aponyx.catalog.sync_types import SyncResult
from aponyx.catalog.validation_types import ValidationResult
from aponyx.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Type alias for entry types
EntryType = (
    IndicatorTransformationEntry
    | ScoreTransformationEntry
    | SignalTransformationEntry
    | SignalEntry
    | StrategyEntry
    | SecurityEntry
    | InstrumentEntry
)

# Valid category names
CATALOG_CATEGORIES = frozenset({
    "indicator_transformations",
    "score_transformations",
    "signal_transformations",
    "signals",
    "strategies",
})

SECURITY_CATEGORIES = frozenset({
    "securities",
    "instruments",
})

ALL_CATEGORIES = CATALOG_CATEGORIES | SECURITY_CATEGORIES


class CatalogManager:
    """
    Central manager for YAML catalog operations.

    Provides unified API for loading, validating, and syncing
    catalog configurations between YAML sources and JSON outputs.

    Attributes
    ----------
    config_dir : Path
        Directory containing catalogs.yaml and securities.yaml.

    Examples
    --------
    >>> from pathlib import Path
    >>> from aponyx.catalog import CatalogManager
    >>> manager = CatalogManager(Path("config"))
    >>> manager.load()
    >>> result = manager.validate()
    >>> if result.passed:
    ...     manager.sync()
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Initialize CatalogManager.

        Parameters
        ----------
        config_dir : Path | None
            Directory containing catalogs.yaml and securities.yaml.
            Defaults to PROJECT_ROOT / "config".

        Raises
        ------
        FileNotFoundError
            If config_dir does not exist.
        """
        if config_dir is None:
            config_dir = PROJECT_ROOT / "config"

        if not config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")

        self._config_dir = config_dir
        self._catalogs_path = config_dir / "catalogs.yaml"
        self._securities_path = config_dir / "securities.yaml"

        self._catalogs_data: CatalogsData | None = None
        self._securities_data: SecuritiesData | None = None
        self._loaded = False

        logger.debug("CatalogManager initialized with config_dir: %s", config_dir)

    @property
    def config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self._config_dir

    @property
    def catalogs_data(self) -> CatalogsData | None:
        """Get loaded catalogs data (None if not loaded)."""
        return self._catalogs_data

    @property
    def securities_data(self) -> SecuritiesData | None:
        """Get loaded securities data (None if not loaded)."""
        return self._securities_data

    def _ensure_loaded(self) -> None:
        """Raise if load() has not been called."""
        if not self._loaded:
            raise RuntimeError("load() must be called before this operation")

    def load(self) -> None:
        """
        Load YAML catalog files into memory.

        Loads both catalogs.yaml and securities.yaml,
        preserving comments for round-trip editing.

        Raises
        ------
        FileNotFoundError
            If catalogs.yaml or securities.yaml not found.
        ValueError
            If YAML structure is invalid.
        """
        logger.info("Loading catalogs from %s", self._config_dir)

        self._catalogs_data = load_catalogs_yaml(self._catalogs_path)
        self._securities_data = load_securities_yaml(self._securities_path)
        self._loaded = True

        total = (
            len(self._catalogs_data.indicator_transformations)
            + len(self._catalogs_data.score_transformations)
            + len(self._catalogs_data.signal_transformations)
            + len(self._catalogs_data.signals)
            + len(self._catalogs_data.strategies)
            + len(self._securities_data.securities)
            + len(self._securities_data.instruments)
        )
        logger.info("Loaded %d catalog entries", total)

    def validate(self) -> ValidationResult:
        """
        Validate catalog entries and cross-references.

        Checks:
        - Required fields present
        - Field constraints satisfied
        - Cross-references resolve correctly
        - No duplicate names

        Returns
        -------
        ValidationResult
            Validation outcome with errors, warnings, and summary.

        Raises
        ------
        RuntimeError
            If load() not called first.
        """
        self._ensure_loaded()

        # Import here to avoid circular import
        from aponyx.catalog.validator import validate_catalogs

        assert self._catalogs_data is not None
        assert self._securities_data is not None

        return validate_catalogs(self._catalogs_data, self._securities_data)

    def sync(self, dry_run: bool = False) -> SyncResult:
        """
        Synchronize YAML sources to JSON catalog files.

        Validates before syncing; fails if validation errors exist.

        Parameters
        ----------
        dry_run : bool, default False
            If True, report what would change without writing files.

        Returns
        -------
        SyncResult
            Sync outcome with written files and any errors.

        Raises
        ------
        RuntimeError
            If load() not called first.
        ValueError
            If validation fails (no files written).
        """
        self._ensure_loaded()

        # Validate first
        validation = self.validate()
        if not validation.passed:
            raise ValueError(
                f"Validation failed with {len(validation.errors)} error(s). "
                "Fix errors before syncing."
            )

        # Import here to avoid circular import
        from aponyx.catalog.sync import sync_to_json
        from aponyx.config import PACKAGE_ROOT

        assert self._catalogs_data is not None
        assert self._securities_data is not None

        return sync_to_json(
            catalogs=self._catalogs_data,
            securities=self._securities_data,
            output_dir=PACKAGE_ROOT,
            dry_run=dry_run,
        )

    def get(self, category: str, name: str) -> EntryType:
        """
        Get a specific catalog entry by category and name.

        Parameters
        ----------
        category : str
            Category name: "signals", "strategies", "indicator_transformations",
            "score_transformations", "signal_transformations", "securities",
            "instruments".
        name : str
            Entry name within category.

        Returns
        -------
        EntryType
            The entry dataclass (SignalEntry, StrategyEntry, etc.).

        Raises
        ------
        KeyError
            If category or name not found.
        RuntimeError
            If load() not called first.
        """
        self._ensure_loaded()

        if category not in ALL_CATEGORIES:
            raise KeyError(f"Unknown category: {category}. Valid: {sorted(ALL_CATEGORIES)}")

        assert self._catalogs_data is not None
        assert self._securities_data is not None

        # Get entries based on category
        entries: dict[str, Any]
        if category == "indicator_transformations":
            entries = {e.name: e for e in self._catalogs_data.indicator_transformations}
        elif category == "score_transformations":
            entries = {e.name: e for e in self._catalogs_data.score_transformations}
        elif category == "signal_transformations":
            entries = {e.name: e for e in self._catalogs_data.signal_transformations}
        elif category == "signals":
            entries = {e.name: e for e in self._catalogs_data.signals}
        elif category == "strategies":
            entries = {e.name: e for e in self._catalogs_data.strategies}
        elif category == "securities":
            entries = self._securities_data.securities
        elif category == "instruments":
            entries = self._securities_data.instruments
        else:
            raise KeyError(f"Unknown category: {category}")

        if name not in entries:
            raise KeyError(f"Entry '{name}' not found in category '{category}'")

        return entries[name]

    def list_items(self, category: str) -> list[str]:
        """
        List all entry names in a category.

        Parameters
        ----------
        category : str
            Category name.

        Returns
        -------
        list[str]
            List of entry names.

        Raises
        ------
        KeyError
            If category not found.
        RuntimeError
            If load() not called first.
        """
        self._ensure_loaded()

        if category not in ALL_CATEGORIES:
            raise KeyError(f"Unknown category: {category}. Valid: {sorted(ALL_CATEGORIES)}")

        assert self._catalogs_data is not None
        assert self._securities_data is not None

        if category == "indicator_transformations":
            return [e.name for e in self._catalogs_data.indicator_transformations]
        elif category == "score_transformations":
            return [e.name for e in self._catalogs_data.score_transformations]
        elif category == "signal_transformations":
            return [e.name for e in self._catalogs_data.signal_transformations]
        elif category == "signals":
            return [e.name for e in self._catalogs_data.signals]
        elif category == "strategies":
            return [e.name for e in self._catalogs_data.strategies]
        elif category == "securities":
            return list(self._securities_data.securities.keys())
        elif category == "instruments":
            return list(self._securities_data.instruments.keys())
        else:
            raise KeyError(f"Unknown category: {category}")

    def add(self, category: str, entry: EntryType) -> None:
        """
        Add a new entry to a category.

        Parameters
        ----------
        category : str
            Category name.
        entry : EntryType
            Entry dataclass to add.

        Raises
        ------
        ValueError
            If entry with same name already exists.
        RuntimeError
            If load() not called first.
        """
        self._ensure_loaded()

        if category not in ALL_CATEGORIES:
            raise KeyError(f"Unknown category: {category}. Valid: {sorted(ALL_CATEGORIES)}")

        assert self._catalogs_data is not None
        assert self._securities_data is not None

        # Check for duplicates
        existing = self.list_items(category)
        if entry.name in existing:
            raise ValueError(f"Entry '{entry.name}' already exists in category '{category}'")

        # Add to appropriate list/dict
        if category == "indicator_transformations":
            if not isinstance(entry, IndicatorTransformationEntry):
                raise TypeError(f"Expected IndicatorTransformationEntry, got {type(entry)}")
            self._catalogs_data.indicator_transformations.append(entry)
        elif category == "score_transformations":
            if not isinstance(entry, ScoreTransformationEntry):
                raise TypeError(f"Expected ScoreTransformationEntry, got {type(entry)}")
            self._catalogs_data.score_transformations.append(entry)
        elif category == "signal_transformations":
            if not isinstance(entry, SignalTransformationEntry):
                raise TypeError(f"Expected SignalTransformationEntry, got {type(entry)}")
            self._catalogs_data.signal_transformations.append(entry)
        elif category == "signals":
            if not isinstance(entry, SignalEntry):
                raise TypeError(f"Expected SignalEntry, got {type(entry)}")
            self._catalogs_data.signals.append(entry)
        elif category == "strategies":
            if not isinstance(entry, StrategyEntry):
                raise TypeError(f"Expected StrategyEntry, got {type(entry)}")
            self._catalogs_data.strategies.append(entry)
        elif category == "securities":
            if not isinstance(entry, SecurityEntry):
                raise TypeError(f"Expected SecurityEntry, got {type(entry)}")
            self._securities_data.securities[entry.name] = entry
        elif category == "instruments":
            if not isinstance(entry, InstrumentEntry):
                raise TypeError(f"Expected InstrumentEntry, got {type(entry)}")
            self._securities_data.instruments[entry.name] = entry

        logger.debug("Added entry '%s' to category '%s'", entry.name, category)

    def remove(self, category: str, name: str) -> None:
        """
        Remove an entry from a category.

        Parameters
        ----------
        category : str
            Category name.
        name : str
            Entry name to remove.

        Raises
        ------
        KeyError
            If entry not found.
        RuntimeError
            If load() not called first.
        """
        self._ensure_loaded()

        if category not in ALL_CATEGORIES:
            raise KeyError(f"Unknown category: {category}. Valid: {sorted(ALL_CATEGORIES)}")

        assert self._catalogs_data is not None
        assert self._securities_data is not None

        # Remove from appropriate list/dict
        if category == "indicator_transformations":
            ind_entries = self._catalogs_data.indicator_transformations
            for i, ind_e in enumerate(ind_entries):
                if ind_e.name == name:
                    ind_entries.pop(i)
                    logger.debug("Removed entry '%s' from '%s'", name, category)
                    return
            raise KeyError(f"Entry '{name}' not found in category '{category}'")

        elif category == "score_transformations":
            score_entries = self._catalogs_data.score_transformations
            for i, score_e in enumerate(score_entries):
                if score_e.name == name:
                    score_entries.pop(i)
                    logger.debug("Removed entry '%s' from '%s'", name, category)
                    return
            raise KeyError(f"Entry '{name}' not found in category '{category}'")

        elif category == "signal_transformations":
            sig_trans_entries = self._catalogs_data.signal_transformations
            for i, sig_trans_e in enumerate(sig_trans_entries):
                if sig_trans_e.name == name:
                    sig_trans_entries.pop(i)
                    logger.debug("Removed entry '%s' from '%s'", name, category)
                    return
            raise KeyError(f"Entry '{name}' not found in category '{category}'")

        elif category == "signals":
            signal_entries = self._catalogs_data.signals
            for i, signal_e in enumerate(signal_entries):
                if signal_e.name == name:
                    signal_entries.pop(i)
                    logger.debug("Removed entry '%s' from '%s'", name, category)
                    return
            raise KeyError(f"Entry '{name}' not found in category '{category}'")

        elif category == "strategies":
            strategy_entries = self._catalogs_data.strategies
            for i, strategy_e in enumerate(strategy_entries):
                if strategy_e.name == name:
                    strategy_entries.pop(i)
                    logger.debug("Removed entry '%s' from '%s'", name, category)
                    return
            raise KeyError(f"Entry '{name}' not found in category '{category}'")

        elif category == "securities":
            if name not in self._securities_data.securities:
                raise KeyError(f"Entry '{name}' not found in category '{category}'")
            del self._securities_data.securities[name]
            logger.debug("Removed entry '%s' from '%s'", name, category)

        elif category == "instruments":
            if name not in self._securities_data.instruments:
                raise KeyError(f"Entry '{name}' not found in category '{category}'")
            del self._securities_data.instruments[name]
            logger.debug("Removed entry '%s' from '%s'", name, category)

    def save(self) -> None:
        """
        Save in-memory changes back to YAML files.

        Preserves comments and formatting.

        Raises
        ------
        RuntimeError
            If load() not called first.
        """
        self._ensure_loaded()

        assert self._catalogs_data is not None
        assert self._securities_data is not None

        save_catalogs_yaml(self._catalogs_data, self._catalogs_path)
        save_securities_yaml(self._securities_data, self._securities_path)

        logger.info("Saved catalogs to %s", self._config_dir)
