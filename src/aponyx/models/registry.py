"""
Registry classes for managing indicator, transformation, and signal catalogs.

This module manages catalog lifecycles:
- Loading metadata from JSON
- Validating definitions (compute functions exist, parameters valid)
- Querying enabled/disabled entries
- Tracking dependencies between indicators and signals
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from . import signals
from .metadata import IndicatorMetadata, SignalMetadata, TransformationMetadata

logger = logging.getLogger(__name__)


class IndicatorRegistry:
    """
    Registry for indicator catalog with JSON persistence and fail-fast validation.

    Manages indicator definitions from the catalog JSON file, validates that
    referenced compute functions exist, and provides query interfaces for
    enabled/disabled indicators.

    Parameters
    ----------
    catalog_path : str | Path
        Path to JSON catalog file containing indicator metadata.

    Examples
    --------
    >>> from aponyx.config import INDICATOR_CATALOG_PATH
    >>> registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
    >>> enabled = registry.get_enabled()
    >>> metadata = registry.get_metadata("cdx_etf_spread_diff")
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
            If catalog JSON is invalid or contains duplicate indicator names.
        """
        self._catalog_path = Path(catalog_path)
        self._indicators: dict[str, IndicatorMetadata] = {}
        self._dependencies: dict[str, list[str]] = {}  # indicator -> signals
        self._load_catalog()

        logger.info(
            "Loaded indicator registry: catalog=%s, indicators=%d, enabled=%d",
            self._catalog_path,
            len(self._indicators),
            len(self.get_enabled()),
        )

    def _load_catalog(self) -> None:
        """Load indicator metadata from JSON catalog file."""
        if not self._catalog_path.exists():
            raise FileNotFoundError(
                f"Indicator catalog not found: {self._catalog_path}"
            )

        with open(self._catalog_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

        if not isinstance(catalog_data, list):
            raise ValueError("Indicator catalog must be a JSON array")

        for entry in catalog_data:
            try:
                metadata = IndicatorMetadata(**entry)
                if metadata.name in self._indicators:
                    raise ValueError(
                        f"Duplicate indicator name in catalog: {metadata.name}"
                    )
                self._indicators[metadata.name] = metadata
            except TypeError as e:
                raise ValueError(
                    f"Invalid indicator metadata in catalog: {entry}. Error: {e}"
                ) from e

        logger.debug("Loaded %d indicators from catalog", len(self._indicators))

        # Fail-fast validation: ensure all compute functions exist
        self._validate_catalog()

    def _validate_catalog(self) -> None:
        """
        Validate that all indicator compute functions exist in indicators module.

        Raises
        ------
        ValueError
            If any compute function name does not exist in indicators module.
        """
        # Import here to avoid circular dependency
        try:
            from . import indicators
        except ImportError:
            logger.warning(
                "indicators module not found, skipping compute function validation"
            )
            return

        for name, metadata in self._indicators.items():
            if not hasattr(indicators, metadata.compute_function_name):
                raise ValueError(
                    f"Indicator '{name}' references non-existent compute function: "
                    f"{metadata.compute_function_name}"
                )

        logger.debug("Validated %d indicator compute functions", len(self._indicators))

    def get_metadata(self, name: str) -> IndicatorMetadata:
        """
        Retrieve metadata for a specific indicator.

        Parameters
        ----------
        name : str
            Indicator name.

        Returns
        -------
        IndicatorMetadata
            Indicator metadata.

        Raises
        ------
        KeyError
            If indicator name is not registered.
        """
        if name not in self._indicators:
            raise KeyError(
                f"Indicator '{name}' not found in registry. "
                f"Available indicators: {sorted(self._indicators.keys())}"
            )
        return self._indicators[name]

    def get_enabled(self) -> dict[str, IndicatorMetadata]:
        """
        Get all enabled indicators.

        Returns
        -------
        dict[str, IndicatorMetadata]
            Mapping from indicator name to metadata for enabled indicators only.
        """
        return {
            name: meta for name, meta in self._indicators.items() if meta.enabled
        }

    def list_all(self) -> dict[str, IndicatorMetadata]:
        """
        Get all registered indicators (enabled and disabled).

        Returns
        -------
        dict[str, IndicatorMetadata]
            Mapping from indicator name to metadata for all indicators.
        """
        return self._indicators.copy()

    def indicator_exists(self, name: str) -> bool:
        """
        Check if indicator is registered.

        Parameters
        ----------
        name : str
            Indicator name.

        Returns
        -------
        bool
            True if indicator exists in registry.
        """
        return name in self._indicators

    def get_dependent_signals(self, indicator_name: str) -> list[str]:
        """
        Get list of signals that depend on this indicator.

        Parameters
        ----------
        indicator_name : str
            Indicator name.

        Returns
        -------
        list[str]
            List of signal names that reference this indicator.
        """
        return self._dependencies.get(indicator_name, []).copy()

    def get_all_dependencies(self) -> dict[str, list[str]]:
        """
        Get complete dependency graph.

        Returns
        -------
        dict[str, list[str]]
            Mapping from indicator name to list of dependent signal names.
        """
        return {k: v.copy() for k, v in self._dependencies.items()}

    def _build_dependency_index(self, signal_registry: "SignalRegistry") -> None:
        """
        Build reverse index of indicator → signals dependencies.

        Parameters
        ----------
        signal_registry : SignalRegistry
            Signal registry to extract dependencies from.
        """
        self._dependencies.clear()

        for signal_name, signal_meta in signal_registry.list_all().items():
            # Only process new-pattern signals with indicator dependencies
            if signal_meta.indicator_dependencies:
                for indicator_name in signal_meta.indicator_dependencies:
                    if indicator_name not in self._dependencies:
                        self._dependencies[indicator_name] = []
                    self._dependencies[indicator_name].append(signal_name)

        logger.debug(
            "Built dependency index: %d indicators with dependencies",
            len(self._dependencies),
        )

    def save_catalog(self, path: str | Path | None = None) -> None:
        """
        Save indicator metadata to JSON catalog file.

        Parameters
        ----------
        path : str | Path | None
            Output path. If None, overwrites original catalog file.
        """
        output_path = Path(path) if path else self._catalog_path

        catalog_data = [asdict(meta) for meta in self._indicators.values()]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)

        logger.info(
            "Saved indicator catalog: path=%s, indicators=%d",
            output_path,
            len(catalog_data),
        )


class TransformationRegistry:
    """
    Registry for transformation catalog with JSON persistence and validation.

    Manages transformation definitions from the catalog JSON file and provides
    query interfaces for enabled/disabled transformations.

    Parameters
    ----------
    catalog_path : str | Path
        Path to JSON catalog file containing transformation metadata.

    Examples
    --------
    >>> from aponyx.config import TRANSFORMATION_CATALOG_PATH
    >>> registry = TransformationRegistry(TRANSFORMATION_CATALOG_PATH)
    >>> enabled = registry.get_enabled()
    >>> metadata = registry.get_metadata("z_score_20d")
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
            If catalog JSON is invalid or contains duplicate transformation names.
        """
        self._catalog_path = Path(catalog_path)
        self._transformations: dict[str, TransformationMetadata] = {}
        self._load_catalog()

        logger.info(
            "Loaded transformation registry: catalog=%s, transformations=%d, enabled=%d",
            self._catalog_path,
            len(self._transformations),
            len(self.get_enabled()),
        )

    def _load_catalog(self) -> None:
        """Load transformation metadata from JSON catalog file."""
        if not self._catalog_path.exists():
            raise FileNotFoundError(
                f"Transformation catalog not found: {self._catalog_path}"
            )

        with open(self._catalog_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

        if not isinstance(catalog_data, list):
            raise ValueError("Transformation catalog must be a JSON array")

        for entry in catalog_data:
            try:
                metadata = TransformationMetadata(**entry)
                if metadata.name in self._transformations:
                    raise ValueError(
                        f"Duplicate transformation name in catalog: {metadata.name}"
                    )
                self._transformations[metadata.name] = metadata
            except TypeError as e:
                raise ValueError(
                    f"Invalid transformation metadata in catalog: {entry}. Error: {e}"
                ) from e

        logger.debug(
            "Loaded %d transformations from catalog", len(self._transformations)
        )

    def get_metadata(self, name: str) -> TransformationMetadata:
        """
        Retrieve metadata for a specific transformation.

        Parameters
        ----------
        name : str
            Transformation name.

        Returns
        -------
        TransformationMetadata
            Transformation metadata.

        Raises
        ------
        KeyError
            If transformation name is not registered.
        """
        if name not in self._transformations:
            raise KeyError(
                f"Transformation '{name}' not found in registry. "
                f"Available transformations: {sorted(self._transformations.keys())}"
            )
        return self._transformations[name]

    def get_enabled(self) -> dict[str, TransformationMetadata]:
        """
        Get all enabled transformations.

        Returns
        -------
        dict[str, TransformationMetadata]
            Mapping from transformation name to metadata for enabled transformations only.
        """
        return {
            name: meta for name, meta in self._transformations.items() if meta.enabled
        }

    def list_all(self) -> dict[str, TransformationMetadata]:
        """
        Get all registered transformations (enabled and disabled).

        Returns
        -------
        dict[str, TransformationMetadata]
            Mapping from transformation name to metadata for all transformations.
        """
        return self._transformations.copy()

    def transformation_exists(self, name: str) -> bool:
        """
        Check if transformation is registered.

        Parameters
        ----------
        name : str
            Transformation name.

        Returns
        -------
        bool
            True if transformation exists in registry.
        """
        return name in self._transformations

    def save_catalog(self, path: str | Path | None = None) -> None:
        """
        Save transformation metadata to JSON catalog file.

        Parameters
        ----------
        path : str | Path | None
            Output path. If None, overwrites original catalog file.
        """
        output_path = Path(path) if path else self._catalog_path

        catalog_data = [asdict(meta) for meta in self._transformations.values()]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)

        logger.info(
            "Saved transformation catalog: path=%s, transformations=%d",
            output_path,
            len(catalog_data),
        )


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

        For legacy signals, validates compute_function_name exists.
        For new-pattern signals, validation of indicator/transformation references
        happens at runtime when registries are linked.

        Raises
        ------
        ValueError
            If any compute function name does not exist in signals module.
        """
        for name, metadata in self._signals.items():
            # Only validate legacy signals with compute_function_name
            if metadata.compute_function_name:
                if not hasattr(signals, metadata.compute_function_name):
                    raise ValueError(
                        f"Signal '{name}' references non-existent compute function: "
                        f"{metadata.compute_function_name}"
                    )

        logger.debug("Validated signal compute functions")

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
