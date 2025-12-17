"""Unit tests for backtest module."""

from aponyx.backtest import BacktestConfig
from aponyx.backtest.registry import StrategyMetadata, StrategyRegistry
from aponyx.config import STRATEGY_CATALOG_PATH


def make_minimal_test_config(**overrides) -> BacktestConfig:
    """
    Create a BacktestConfig with minimal defaults for unit testing.

    INTENTIONAL DEVIATION FROM CATALOG: This helper uses relaxed defaults
    (no stop-loss, no take-profit) to simplify test assertions. Use this
    when testing position logic, P&L calculations, or other mechanics
    where risk management exits would complicate the test.

    For tests that require catalog-accurate defaults, use make_catalog_test_config().

    Parameters
    ----------
    **overrides
        Any BacktestConfig parameters to override from defaults.

    Returns
    -------
    BacktestConfig
        Configuration with minimal test defaults and any specified overrides.

    Examples
    --------
    >>> config = make_minimal_test_config()  # Relaxed defaults
    >>> config = make_minimal_test_config(signal_lag=0)  # Override signal_lag
    >>> config = make_minimal_test_config(stop_loss_pct=3.0)  # Enable stop-loss
    """
    defaults = {
        "position_size_mm": 10.0,
        "sizing_mode": "proportional",
        "stop_loss_pct": None,  # Intentionally None for simpler tests
        "take_profit_pct": None,  # Intentionally None for simpler tests
        "max_holding_days": None,
        "transaction_cost_bps": 1.0,
        "transaction_cost_pct": None,  # Static mode by default
        "dv01_per_million": 475.0,
        "signal_lag": 1,
    }
    defaults.update(overrides)
    return BacktestConfig(**defaults)


def make_catalog_test_config(
    strategy_name: str = "balanced",
    **overrides,
) -> BacktestConfig:
    """
    Create a BacktestConfig by loading defaults from the strategy catalog.

    Use this when tests require catalog-accurate defaults, such as testing
    that catalog values are correctly applied or integration tests.

    Parameters
    ----------
    strategy_name : str, default "balanced"
        Name of the strategy to load from strategy_catalog.json.
    **overrides
        Any BacktestConfig parameters to override after loading from catalog.

    Returns
    -------
    BacktestConfig
        Configuration with catalog defaults and any specified overrides.

    Examples
    --------
    >>> config = make_catalog_test_config()  # Load 'balanced' strategy
    >>> config = make_catalog_test_config("conservative")  # Load 'conservative'
    >>> config = make_catalog_test_config(signal_lag=0)  # Catalog defaults + override
    """
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    metadata = registry.get_metadata(strategy_name)
    return metadata.to_config(**{f"{k}_override": v for k, v in overrides.items()})


# Backwards compatibility alias
make_test_config = make_minimal_test_config


def make_minimal_test_metadata(**overrides) -> StrategyMetadata:
    """
    Create a StrategyMetadata with minimal defaults for unit testing.

    INTENTIONAL DEVIATION FROM CATALOG: This helper uses relaxed defaults
    (no stop-loss, no take-profit) to simplify test assertions for
    StrategyMetadata validation and conversion.

    For tests that require catalog-accurate metadata, use make_catalog_test_metadata().

    Parameters
    ----------
    **overrides
        Any StrategyMetadata parameters to override from defaults.

    Returns
    -------
    StrategyMetadata
        Metadata with minimal test defaults and any specified overrides.

    Examples
    --------
    >>> meta = make_minimal_test_metadata()  # Relaxed defaults
    >>> meta = make_minimal_test_metadata(name="custom", stop_loss_pct=5.0)
    """
    defaults = {
        "name": "test_strategy",
        "description": "Test strategy for unit testing",
        "position_size_mm": 10.0,
        "sizing_mode": "proportional",
        "stop_loss_pct": None,  # Intentionally None for simpler tests
        "take_profit_pct": None,  # Intentionally None for simpler tests
        "max_holding_days": None,
        "transaction_cost_bps": 1.0,
        "dv01_per_million": 475.0,
        "enabled": True,
    }
    defaults.update(overrides)
    return StrategyMetadata(**defaults)


def make_catalog_test_metadata(strategy_name: str = "balanced") -> StrategyMetadata:
    """
    Load a StrategyMetadata directly from the strategy catalog.

    Use this when tests require catalog-accurate metadata, such as testing
    that catalog values are correctly loaded or integration tests.

    Parameters
    ----------
    strategy_name : str, default "balanced"
        Name of the strategy to load from strategy_catalog.json.

    Returns
    -------
    StrategyMetadata
        Metadata loaded directly from the catalog.

    Examples
    --------
    >>> meta = make_catalog_test_metadata()  # Load 'balanced' strategy
    >>> meta = make_catalog_test_metadata("conservative")  # Load 'conservative'
    """
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    return registry.get_metadata(strategy_name)


# Backwards compatibility alias
make_test_strategy_metadata = make_minimal_test_metadata
