"""
Signal registry for managing signal catalog persistence and validation.

This module manages the signal catalog lifecycle:
- Loading signal metadata from JSON
- Validating signal definitions (compute functions exist)
- Querying enabled/disabled signals
- Persisting catalog changes
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from . import signals
from .metadata import SignalMetadata

logger = logging.getLogger(__name__)


class SignalRegistry:
    """
    Registry for signal catalog with JSON persistence and fail-fast validation.

    Manages signal definitions from the catalog JSON file, validates that
    referenced compute functions exist, and provides query interfaces for
    enabled/disabled signals.

    This class follows the catalog governance pattern (see governance_design.md):
    - Immutable after load (frozen dataclass metadata)
    - Fail-fast validation at initialization
    - Read-only during runtime (edits require manual JSON modification)

    Parameters
    ----------
    catalog_path : str | Path
        Path to JSON catalog file containing signal metadata.

    Examples
    --------
    >>> from aponyx.config import SIGNAL_CATALOG_PATH
    >>> registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    >>> enabled = registry.get_enabled()
    >>> metadata = registry.get_metadata("cdx_etf_basis")
    """

    def __init__(self, catalog_path: str | Path) -> None:
        """
        Initialize registry and load catalog from JSON file.

        Parameters
        ----------
        catalog_path : str | Path
            Path to JSON catalog file.

        Raises
        ------
        FileNotFoundError
            If catalog file does not exist.
        ValueError
            If catalog JSON is invalid or contains duplicate signal names.
        """
        self._catalog_path = Path(catalog_path)
        self._signals: dict[str, SignalMetadata] = {}
        self._load_catalog()

        logger.info(
            "Loaded signal registry: catalog=%s, signals=%d, enabled=%d",
            self._catalog_path,
            len(self._signals),
            len(self.get_enabled()),
        )

    def _load_catalog(self) -> None:
        """Load signal metadata from JSON catalog file."""
        if not self._catalog_path.exists():
            raise FileNotFoundError(f"Signal catalog not found: {self._catalog_path}")

        with open(self._catalog_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

        if not isinstance(catalog_data, list):
            raise ValueError("Signal catalog must be a JSON array")

        for entry in catalog_data:
            try:
                metadata = SignalMetadata(**entry)
                if metadata.name in self._signals:
                    raise ValueError(
                        f"Duplicate signal name in catalog: {metadata.name}"
                    )
                self._signals[metadata.name] = metadata
            except TypeError as e:
                raise ValueError(
                    f"Invalid signal metadata in catalog: {entry}. Error: {e}"
                ) from e

        logger.debug("Loaded %d signals from catalog", len(self._signals))

        # Fail-fast validation: ensure all compute functions exist
        self._validate_catalog()

    def _validate_catalog(self) -> None:
        """
        Validate that all signal compute functions exist in signals module.

        Raises
        ------
        ValueError
            If any compute function name does not exist in signals module.
        """
        for name, metadata in self._signals.items():
            if not hasattr(signals, metadata.compute_function_name):
                raise ValueError(
                    f"Signal '{name}' references non-existent compute function: "
                    f"{metadata.compute_function_name}"
                )

        logger.debug("Validated %d signal compute functions", len(self._signals))

    def get_metadata(self, name: str) -> SignalMetadata:
        """
        Retrieve metadata for a specific signal.

        Parameters
        ----------
        name : str
            Signal name.

        Returns
        -------
        SignalMetadata
            Signal metadata.

        Raises
        ------
        KeyError
            If signal name is not registered.
        """
        if name not in self._signals:
            raise KeyError(
                f"Signal '{name}' not found in registry. "
                f"Available signals: {sorted(self._signals.keys())}"
            )
        return self._signals[name]

    def get_enabled(self) -> dict[str, SignalMetadata]:
        """
        Get all enabled signals.

        Returns
        -------
        dict[str, SignalMetadata]
            Mapping from signal name to metadata for enabled signals only.
        """
        return {name: meta for name, meta in self._signals.items() if meta.enabled}

    def list_all(self) -> dict[str, SignalMetadata]:
        """
        Get all registered signals (enabled and disabled).

        Returns
        -------
        dict[str, SignalMetadata]
            Mapping from signal name to metadata for all signals.
        """
        return self._signals.copy()

    def save_catalog(self, path: str | Path | None = None) -> None:
        """
        Save signal metadata to JSON catalog file.

        Parameters
        ----------
        path : str | Path | None
            Output path. If None, overwrites original catalog file.
        """
        output_path = Path(path) if path else self._catalog_path

        catalog_data = [asdict(meta) for meta in self._signals.values()]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)

        logger.info(
            "Saved signal catalog: path=%s, signals=%d", output_path, len(catalog_data)
        )
