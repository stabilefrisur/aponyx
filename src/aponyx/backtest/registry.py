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

    Strategy metadata defines trading behavior only. Product-specific
    microstructure parameters (DV01, transaction costs) are loaded from
    bloomberg_securities.json at runtime based on the workflow's product.

    Attributes
    ----------
    name : str
        Unique strategy identifier (e.g., "conservative", "balanced").
    description : str
        Human-readable description of strategy characteristics.
    position_size_mm : float
        Baseline notional position size in millions.
    sizing_mode : str
        Position sizing mode: 'binary' (full position for any non-zero signal)
        or 'proportional' (scaled by signal magnitude).
    stop_loss_pct : float | None
        Stop loss as percentage of initial position value. None to disable.
    take_profit_pct : float | None
        Take profit as percentage of initial position value. None to disable.
    max_holding_days : int | None
        Maximum days to hold a position before forced exit. None for no limit.
    entry_threshold : float | None
        Minimum absolute signal value required to enter a position.
        Only signals with |signal| >= entry_threshold trigger entry.
        Should be wider than neutral_range in signal transformation to allow
        reversion signals to run before exiting.
        None = any non-zero signal triggers entry (legacy behavior).
    enabled : bool
        Whether strategy should be included in evaluation.
    """

    name: str
    description: str
    position_size_mm: float
    sizing_mode: str
    stop_loss_pct: float | None
    take_profit_pct: float | None
    max_holding_days: int | None
    entry_threshold: float | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate strategy metadata."""
        if not self.name:
            raise ValueError("Strategy name cannot be empty")
        if self.position_size_mm <= 0:
            raise ValueError(
                f"Strategy '{self.name}': position_size_mm must be positive, "
                f"got {self.position_size_mm}"
            )
        if self.sizing_mode not in {"binary", "proportional"}:
            raise ValueError(
                f"Strategy '{self.name}': sizing_mode must be 'binary' or 'proportional', "
                f"got '{self.sizing_mode}'"
            )
        if self.stop_loss_pct is not None and not (0 < self.stop_loss_pct <= 100):
            raise ValueError(
                f"Strategy '{self.name}': stop_loss_pct must be in (0, 100], "
                f"got {self.stop_loss_pct}"
            )
        if self.take_profit_pct is not None and not (0 < self.take_profit_pct <= 100):
            raise ValueError(
                f"Strategy '{self.name}': take_profit_pct must be in (0, 100], "
                f"got {self.take_profit_pct}"
            )
        if self.max_holding_days is not None and self.max_holding_days <= 0:
            raise ValueError(
                f"Strategy '{self.name}': max_holding_days must be positive, "
                f"got {self.max_holding_days}"
            )
        if self.entry_threshold is not None and self.entry_threshold <= 0:
            raise ValueError(
                f"Strategy '{self.name}': entry_threshold must be positive, "
                f"got {self.entry_threshold}"
            )

    def to_config(
        self,
        dv01_per_million: float,
        transaction_cost_bps: float,
        position_size_mm_override: float | None = None,
        sizing_mode_override: str | None = None,
        stop_loss_pct_override: float | None = None,
        take_profit_pct_override: float | None = None,
        max_holding_days_override: int | None = None,
        entry_threshold_override: float | None = None,
        transaction_cost_pct: float | None = None,
    ) -> BacktestConfig:
        """
        Convert strategy metadata to BacktestConfig.

        Requires product-specific microstructure parameters (DV01, transaction cost)
        to be passed in. These come from bloomberg_securities.json via
        get_product_microstructure() in the workflow layer.

        Parameters
        ----------
        dv01_per_million : float
            DV01 per $1MM notional for the product being backtested.
        transaction_cost_bps : float
            Transaction cost in basis points for the product.
        position_size_mm_override : float | None, default None
            Override catalog position_size_mm value.
        sizing_mode_override : str | None, default None
            Override catalog sizing_mode value.
        stop_loss_pct_override : float | None, default None
            Override catalog stop_loss_pct value (use False to explicitly disable).
        take_profit_pct_override : float | None, default None
            Override catalog take_profit_pct value (use False to explicitly disable).
        max_holding_days_override : int | None, default None
            Override catalog max_holding_days value (use False to explicitly disable).
        entry_threshold_override : float | None, default None
            Override catalog entry_threshold value (use False to explicitly disable).
        transaction_cost_pct : float | None, default None
            Dynamic transaction cost as percentage of current spread.
            When set, this overrides transaction_cost_bps with spread-dependent costs.

        Returns
        -------
        BacktestConfig
            Full backtest configuration with strategy and product parameters.

        Examples
        --------
        >>> from aponyx.data import get_product_microstructure
        >>> metadata = StrategyMetadata(
        ...     name="balanced", description="Balanced strategy",
        ...     position_size_mm=10.0, sizing_mode="proportional",
        ...     stop_loss_pct=5.0, take_profit_pct=10.0, max_holding_days=None
        ... )
        >>> params = get_product_microstructure("cdx_ig_5y")
        >>> config = metadata.to_config(
        ...     dv01_per_million=params.dv01_per_million,
        ...     transaction_cost_bps=params.transaction_cost_bps
        ... )
        >>> config.dv01_per_million
        475.0
        """
        return BacktestConfig(
            position_size_mm=(
                position_size_mm_override
                if position_size_mm_override is not None
                else self.position_size_mm
            ),
            sizing_mode=(
                sizing_mode_override
                if sizing_mode_override is not None
                else self.sizing_mode
            ),
            stop_loss_pct=(
                stop_loss_pct_override
                if stop_loss_pct_override is not None
                else self.stop_loss_pct
            ),
            take_profit_pct=(
                take_profit_pct_override
                if take_profit_pct_override is not None
                else self.take_profit_pct
            ),
            max_holding_days=(
                max_holding_days_override
                if max_holding_days_override is not None
                else self.max_holding_days
            ),
            entry_threshold=(
                entry_threshold_override
                if entry_threshold_override is not None
                else self.entry_threshold
            ),
            transaction_cost_bps=transaction_cost_bps,
            dv01_per_million=dv01_per_million,
            transaction_cost_pct=transaction_cost_pct,
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
            raise FileNotFoundError(f"Strategy catalog not found: {self._catalog_path}")

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
        return {name: meta for name, meta in self._strategies.items() if meta.enabled}

    def list_all(self) -> dict[str, StrategyMetadata]:
        """
        Get all registered strategies (enabled and disabled).

        Returns
        -------
        dict[str, StrategyMetadata]
            Mapping from strategy name to metadata for all strategies.
        """
        return self._strategies.copy()

    def strategy_exists(self, name: str) -> bool:
        """
        Check if strategy is registered.

        Parameters
        ----------
        name : str
            Strategy name.

        Returns
        -------
        bool
            True if strategy exists in registry.
        """
        return name in self._strategies

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
