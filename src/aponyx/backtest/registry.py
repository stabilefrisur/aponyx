"""
Strategy registry for managing backtest strategy metadata and catalog persistence.

Follows the same governance pattern as SignalRegistry for consistency.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

from .config import BacktestConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyMetadata:
    """
    Metadata for a registered backtest strategy.

    Attributes
    ----------
    name : str
        Unique strategy identifier (e.g., "conservative", "balanced").
    description : str
        Human-readable description of strategy characteristics.
    entry_threshold : float
        Signal threshold for entering positions.
    exit_threshold : float
        Signal threshold for exiting positions.
    enabled : bool
        Whether strategy should be included in evaluation.
    """

    name: str
    description: str
    entry_threshold: float
    exit_threshold: float
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate strategy metadata."""
        if not self.name:
            raise ValueError("Strategy name cannot be empty")
        if self.entry_threshold <= self.exit_threshold:
            raise ValueError(
                f"Strategy '{self.name}': entry_threshold ({self.entry_threshold}) "
                f"must be > exit_threshold ({self.exit_threshold})"
            )

    def to_config(
        self,
        position_size: float = 10.0,
        transaction_cost_bps: float = 1.0,
        max_holding_days: int | None = None,
        dv01_per_million: float = 4750.0,
    ) -> BacktestConfig:
        """
        Convert strategy metadata to BacktestConfig.

        Uses strategy thresholds with provided defaults for other parameters.

        Parameters
        ----------
        position_size : float, default 10.0
            Notional position size in millions.
        transaction_cost_bps : float, default 1.0
            Round-trip transaction cost in basis points.
        max_holding_days : int | None, default None
            Maximum days to hold a position before forced exit.
        dv01_per_million : float, default 4750.0
            DV01 per $1MM notional for risk calculations.

        Returns
        -------
        BacktestConfig
            Full backtest configuration with strategy thresholds.

        Examples
        --------
        >>> metadata = StrategyMetadata(
        ...     name="aggressive",
        ...     description="High turnover",
        ...     entry_threshold=1.0,
        ...     exit_threshold=0.5
        ... )
        >>> config = metadata.to_config(position_size=20.0)
        >>> config.entry_threshold
        1.0
        >>> config.position_size
        20.0
        """
        return BacktestConfig(
            entry_threshold=self.entry_threshold,
            exit_threshold=self.exit_threshold,
            position_size=position_size,
            transaction_cost_bps=transaction_cost_bps,
            max_holding_days=max_holding_days,
            dv01_per_million=dv01_per_million,
        )


class StrategyRegistry:
    """
    Registry for strategy metadata with JSON catalog persistence.

    Manages strategy definitions, enabling/disabling strategies, and catalog I/O.
    Follows pattern from models.registry.SignalRegistry.

    Parameters
    ----------
    catalog_path : str | Path
        Path to JSON catalog file containing strategy metadata.

    Examples
    --------
    >>> from aponyx.config import STRATEGY_CATALOG_PATH
    >>> registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    >>> enabled = registry.get_enabled()
    >>> metadata = registry.get_metadata("balanced")
    >>> config = metadata.to_config()
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
            If catalog JSON is invalid or contains duplicate strategy names.
        """
        self._catalog_path = Path(catalog_path)
        self._strategies: dict[str, StrategyMetadata] = {}
        self._load_catalog()

        logger.info(
            "Loaded strategy registry: catalog=%s, strategies=%d, enabled=%d",
            self._catalog_path,
            len(self._strategies),
            len(self.get_enabled()),
        )

    def _load_catalog(self) -> None:
        """Load strategy metadata from JSON catalog file."""
        if not self._catalog_path.exists():
            raise FileNotFoundError(
                f"Strategy catalog not found: {self._catalog_path}"
            )

        with open(self._catalog_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

        if not isinstance(catalog_data, list):
            raise ValueError("Strategy catalog must be a JSON array")

        for entry in catalog_data:
            try:
                metadata = StrategyMetadata(**entry)
                if metadata.name in self._strategies:
                    raise ValueError(
                        f"Duplicate strategy name in catalog: {metadata.name}"
                    )
                self._strategies[metadata.name] = metadata
            except TypeError as e:
                raise ValueError(
                    f"Invalid strategy metadata in catalog: {entry}. Error: {e}"
                ) from e

        logger.debug("Loaded %d strategies from catalog", len(self._strategies))

        # Fail-fast validation: thresholds already validated in __post_init__
        # No additional validation needed beyond dataclass constraints

    def get_metadata(self, name: str) -> StrategyMetadata:
        """
        Retrieve metadata for a specific strategy.

        Parameters
        ----------
        name : str
            Strategy name.

        Returns
        -------
        StrategyMetadata
            Strategy metadata.

        Raises
        ------
        KeyError
            If strategy name is not registered.
        """
        if name not in self._strategies:
            raise KeyError(
                f"Strategy '{name}' not found in registry. "
                f"Available strategies: {sorted(self._strategies.keys())}"
            )
        return self._strategies[name]

    def get_enabled(self) -> dict[str, StrategyMetadata]:
        """
        Get all enabled strategies.

        Returns
        -------
        dict[str, StrategyMetadata]
            Mapping from strategy name to metadata for enabled strategies only.
        """
        return {
            name: meta for name, meta in self._strategies.items() if meta.enabled
        }

    def list_all(self) -> dict[str, StrategyMetadata]:
        """
        Get all registered strategies (enabled and disabled).

        Returns
        -------
        dict[str, StrategyMetadata]
            Mapping from strategy name to metadata for all strategies.
        """
        return self._strategies.copy()

    def save_catalog(self, path: str | Path | None = None) -> None:
        """
        Save strategy metadata to JSON catalog file.

        Parameters
        ----------
        path : str | Path | None
            Output path. If None, overwrites original catalog file.
        """
        output_path = Path(path) if path else self._catalog_path

        catalog_data = [asdict(meta) for meta in self._strategies.values()]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)

        logger.info(
            "Saved strategy catalog: path=%s, strategies=%d",
            output_path,
            len(catalog_data),
        )
