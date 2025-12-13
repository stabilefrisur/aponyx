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

from .metadata import (
    CatalogValidationError,
    IndicatorMetadata,
    SignalMetadata,
    SignalTransformationMetadata,
    TransformationMetadata,
)

logger = logging.getLogger(__name__)


class IndicatorTransformationRegistry:
    """
    Registry for indicator transformation catalog with JSON persistence and fail-fast validation.

    Manages indicator transformation definitions from the catalog JSON file, validates that
    referenced compute functions exist, and provides query interfaces for
    enabled/disabled indicator transformations.

    Parameters
    ----------
    catalog_path : str | Path
        Path to JSON catalog file containing indicator transformation metadata.

    Examples
    --------
    >>> from aponyx.config import INDICATOR_TRANSFORMATION_PATH
    >>> registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
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
        ValueError
            If indicator name is not registered.
        """
        if name not in self._indicators:
            raise ValueError(
                f"Indicator '{name}' not found in registry. "
                f"Available indicators: {sorted(self._indicators.keys())}"
            )
        return self._indicators[name]

    def get_all_indicators(self) -> list[str]:
        """
        Get all indicator names.

        Returns
        -------
        list[str]
            List of all indicator names (enabled and disabled).
        """
        return list(self._indicators.keys())

    def get_enabled_indicators(self) -> list[str]:
        """
        Get all enabled indicator names.

        Returns
        -------
        list[str]
            List of enabled indicator names only.
        """
        return [name for name, meta in self._indicators.items() if meta.enabled]

    def get_enabled(self) -> dict[str, IndicatorMetadata]:
        """
        Get all enabled indicators.

        Returns
        -------
        dict[str, IndicatorMetadata]
            Mapping from indicator name to metadata for enabled indicators only.
        """
        return {name: meta for name, meta in self._indicators.items() if meta.enabled}

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
            # Every signal references exactly one indicator transformation
            indicator_name = signal_meta.indicator_transformation
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


class ScoreTransformationRegistry:
    """
    Registry for score transformation catalog with JSON persistence and validation.

    Manages score transformation definitions from the catalog JSON file and provides
    query interfaces for enabled/disabled score transformations.

    Parameters
    ----------
    catalog_path : str | Path
        Path to JSON catalog file containing score transformation metadata.

    Examples
    --------
    >>> from aponyx.config import SCORE_TRANSFORMATION_PATH
    >>> registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
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


class SignalTransformationRegistry:
    """
    Registry for signal transformation catalog with JSON persistence and fail-fast validation.

    Manages signal transformation definitions (floor, cap, neutral_range, scaling) from
    the catalog JSON file and provides query interfaces for enabled/disabled signal transformations.

    Parameters
    ----------
    catalog_path : str | Path
        Path to JSON catalog file containing signal transformation metadata.

    Examples
    --------
    >>> from aponyx.config import SIGNAL_TRANSFORMATION_PATH
    >>> registry = SignalTransformationRegistry(SIGNAL_TRANSFORMATION_PATH)
    >>> enabled = registry.get_enabled()
    >>> metadata = registry.get_metadata("bounded_1_5")
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
        CatalogValidationError
            If any transformation violates constraints (floor > cap, etc.).
        """
        self._catalog_path = Path(catalog_path)
        self._signal_transformations: dict[str, SignalTransformationMetadata] = {}
        self._load_catalog()

        logger.info(
            "Loaded signal transformation registry: catalog=%s, transformations=%d, enabled=%d",
            self._catalog_path,
            len(self._signal_transformations),
            len(self.get_enabled()),
        )

    def _load_catalog(self) -> None:
        """Load signal transformation metadata from JSON catalog file."""
        if not self._catalog_path.exists():
            raise FileNotFoundError(
                f"Signal transformation catalog not found: {self._catalog_path}"
            )

        with open(self._catalog_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

        if not isinstance(catalog_data, list):
            raise ValueError("Signal transformation catalog must be a JSON array")

        for entry in catalog_data:
            try:
                # Convert neutral_range from list to tuple for frozen dataclass
                if "neutral_range" in entry and entry["neutral_range"] is not None:
                    entry["neutral_range"] = tuple(entry["neutral_range"])
                
                metadata = SignalTransformationMetadata(**entry)
                if metadata.name in self._signal_transformations:
                    raise ValueError(
                        f"Duplicate signal transformation name in catalog: {metadata.name}"
                    )
                self._signal_transformations[metadata.name] = metadata
            except TypeError as e:
                raise ValueError(
                    f"Invalid signal transformation metadata in catalog: {entry}. Error: {e}"
                ) from e

        logger.debug(
            "Loaded %d signal transformations from catalog",
            len(self._signal_transformations),
        )

    def get_metadata(self, name: str) -> SignalTransformationMetadata:
        """
        Retrieve metadata for a specific signal transformation.

        Parameters
        ----------
        name : str
            Signal transformation name.

        Returns
        -------
        SignalTransformationMetadata
            Signal transformation metadata.

        Raises
        ------
        KeyError
            If signal transformation name is not registered.
        """
        if name not in self._signal_transformations:
            raise KeyError(
                f"Signal transformation '{name}' not found in registry. "
                f"Available signal transformations: {sorted(self._signal_transformations.keys())}"
            )
        return self._signal_transformations[name]

    def get_enabled(self) -> dict[str, SignalTransformationMetadata]:
        """
        Get all enabled signal transformations.

        Returns
        -------
        dict[str, SignalTransformationMetadata]
            Mapping from transformation name to metadata for enabled transformations only.
        """
        return {
            name: meta
            for name, meta in self._signal_transformations.items()
            if meta.enabled
        }

    def list_all(self) -> dict[str, SignalTransformationMetadata]:
        """
        Get all registered signal transformations (enabled and disabled).

        Returns
        -------
        dict[str, SignalTransformationMetadata]
            Mapping from transformation name to metadata for all transformations.
        """
        return self._signal_transformations.copy()

    def transformation_exists(self, name: str) -> bool:
        """
        Check if signal transformation is registered.

        Parameters
        ----------
        name : str
            Signal transformation name.

        Returns
        -------
        bool
            True if signal transformation exists in registry.
        """
        return name in self._signal_transformations

    def save_catalog(self, path: str | Path | None = None) -> None:
        """
        Save signal transformation metadata to JSON catalog file.

        Parameters
        ----------
        path : str | Path | None
            Output path. If None, overwrites original catalog file.
        """
        output_path = Path(path) if path else self._catalog_path

        # Convert tuples back to lists for JSON serialization
        catalog_data = []
        for meta in self._signal_transformations.values():
            entry = asdict(meta)
            if entry["neutral_range"] is not None:
                entry["neutral_range"] = list(entry["neutral_range"])
            catalog_data.append(entry)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)

        logger.info(
            "Saved signal transformation catalog: path=%s, transformations=%d",
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
        Validate that all signal transformation references are non-empty strings.

        Validates the four-stage transformation pipeline references:
        - indicator_transformation (reference to indicator_transformation.json)
        - score_transformation (reference to score_transformation.json)
        - signal_transformation (reference to signal_transformation.json)

        Note: This method validates structure only. Cross-registry validation
        (checking if referenced transformations exist) is performed at compose_signal
        time when all registries are available.

        Raises
        ------
        CatalogValidationError
            If any transformation reference is empty or missing.
        """
        for name, metadata in self._signals.items():
            # Enforce non-empty transformation references
            if not metadata.indicator_transformation:
                raise CatalogValidationError(
                    catalog="signal_catalog.json",
                    entry=name,
                    field="indicator_transformation",
                    value=metadata.indicator_transformation,
                    constraint="indicator_transformation is required (cannot be empty)",
                    suggestion="Specify an indicator from indicator_transformation.json",
                )

            if not metadata.score_transformation:
                raise CatalogValidationError(
                    catalog="signal_catalog.json",
                    entry=name,
                    field="score_transformation",
                    value=metadata.score_transformation,
                    constraint="score_transformation is required (cannot be empty)",
                    suggestion="Specify a transformation from score_transformation.json",
                )

            if not metadata.signal_transformation:
                raise CatalogValidationError(
                    catalog="signal_catalog.json",
                    entry=name,
                    field="signal_transformation",
                    value=metadata.signal_transformation,
                    constraint="signal_transformation is required (cannot be empty)",
                    suggestion="Specify a transformation from signal_transformation.json (e.g., 'passthrough')",
                )

        logger.debug("Validated signal metadata transformation references")

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

    def signal_exists(self, name: str) -> bool:
        """
        Check if signal is registered.

        Parameters
        ----------
        name : str
            Signal name.

        Returns
        -------
        bool
            True if signal exists in registry.
        """
        return name in self._signals

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
