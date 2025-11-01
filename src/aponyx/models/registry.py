"""
Signal registry for managing signal metadata and catalog persistence.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignalMetadata:
    """
    Metadata for a registered signal computation.

    Attributes
    ----------
    name : str
        Unique signal identifier (e.g., "cdx_etf_basis").
    description : str
        Human-readable description of signal purpose and logic.
    compute_function_name : str
        Name of the compute function in signals module (e.g., "compute_cdx_etf_basis").
    data_requirements : dict[str, str]
        Mapping from market data keys to required column names.
        Example: {"cdx": "spread", "etf": "spread"}
    arg_mapping : list[str]
        Ordered list of data keys to pass as positional arguments to compute function.
        Example: ["cdx", "etf"] means call compute_fn(market_data["cdx"], market_data["etf"], config)
    enabled : bool
        Whether signal should be included in computation.
    """

    name: str
    description: str
    compute_function_name: str
    data_requirements: dict[str, str]
    arg_mapping: list[str]
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate signal metadata."""
        if not self.name:
            raise ValueError("Signal name cannot be empty")
        if not self.compute_function_name:
            raise ValueError("Compute function name cannot be empty")
        if not self.arg_mapping:
            raise ValueError("arg_mapping cannot be empty")
        # Validate arg_mapping is subset of data_requirements keys
        missing_args = set(self.arg_mapping) - set(self.data_requirements.keys())
        if missing_args:
            raise ValueError(
                f"arg_mapping contains keys not in data_requirements: {missing_args}"
            )


class SignalRegistry:
    """
    Registry for signal metadata with JSON catalog persistence.

    Manages signal definitions, enabling/disabling signals, and catalog I/O.
    Follows pattern from persistence.registry.DataRegistry.

    Parameters
    ----------
    catalog_path : str | Path
        Path to JSON catalog file containing signal metadata.

    Examples
    --------
    >>> registry = SignalRegistry("src/aponyx/models/signal_catalog.json")
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
            raise FileNotFoundError(
                f"Signal catalog not found: {self._catalog_path}"
            )

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
        return {
            name: meta for name, meta in self._signals.items() if meta.enabled
        }

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

        logger.info("Saved signal catalog: path=%s, signals=%d", output_path, len(catalog_data))
