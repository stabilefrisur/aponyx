"""Unit tests for backtest module."""

from aponyx.backtest import BacktestConfig, SpreadReturnCalculator, resolve_calculator
from aponyx.backtest.registry import StrategyMetadata, StrategyRegistry
from aponyx.config import STRATEGY_CATALOG_PATH

# Default DV01 for test spread calculators
DEFAULT_TEST_DV01 = 475.0


def make_minimal_test_config(**overrides) -> BacktestConfig:
    """
    Create a BacktestConfig with minimal defaults for unit testing.

    INTENTIONAL DEVIATION FROM CATALOG: This helper uses relaxed defaults
    (no stop-loss, no take-profit) to simplify test assertions. Use this
    when testing position logic, P&L calculations, or other mechanics
    where risk management exits would complicate the test.

    For tests that require catalog-accurate defaults, use make_catalog_test_config().

    Note: DV01 is no longer part of BacktestConfig. Use make_test_calculator()
    to get a calculator for tests.

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
        "entry_threshold": None,  # Intentionally None for simpler tests (legacy behavior)
        "transaction_cost_bps": 1.0,
        "transaction_cost_pct": None,  # Static mode by default
        "signal_lag": 1,
    }
    defaults.update(overrides)
    return BacktestConfig(**defaults)


def make_test_calculator(
    dv01_per_million: float = DEFAULT_TEST_DV01,
) -> SpreadReturnCalculator:
    """
    Create a SpreadReturnCalculator for unit testing.

    Parameters
    ----------
    dv01_per_million : float, default 475.0
        DV01 per $1MM notional.

    Returns
    -------
    SpreadReturnCalculator
        Calculator for spread-based products.

    Examples
    --------
    >>> calculator = make_test_calculator()
    >>> calculator = make_test_calculator(dv01_per_million=500.0)
    """
    return SpreadReturnCalculator(dv01_per_million=dv01_per_million)


def make_catalog_test_config(
    strategy_name: str = "balanced",
    product: str = "cdx_ig_5y",
    **overrides,
) -> BacktestConfig:
    """
    Create a BacktestConfig by loading defaults from the strategy catalog.

    Use this when tests require catalog-accurate defaults, such as testing
    that catalog values are correctly applied or integration tests.

    Note: DV01 is no longer part of BacktestConfig. Use make_catalog_test_calculator()
    to get a calculator for tests.

    Parameters
    ----------
    strategy_name : str, default "balanced"
        Name of the strategy to load from strategy_catalog.json.
    product : str, default "cdx_ig_5y"
        Product identifier to load microstructure params from bloomberg_securities.json.
    **overrides
        Any BacktestConfig parameters to override after loading from catalog.

    Returns
    -------
    BacktestConfig
        Configuration with catalog defaults and any specified overrides.

    Examples
    --------
    >>> config = make_catalog_test_config()  # Load 'balanced' strategy with cdx_ig_5y
    >>> config = make_catalog_test_config("conservative", "cdx_hy_5y")
    >>> config = make_catalog_test_config(stop_loss_pct_override=3.0)  # Catalog defaults + override
    """
    from aponyx.data import get_product_microstructure

    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    metadata = registry.get_metadata(strategy_name)
    microstructure = get_product_microstructure(product)

    return metadata.to_config(
        transaction_cost_bps=microstructure.transaction_cost_bps,
        **{
            f"{k}_override": v
            for k, v in overrides.items()
            if not k.endswith("_override")
        },
        **{k: v for k, v in overrides.items() if k.endswith("_override")},
    )


def make_catalog_test_calculator(product: str = "cdx_ig_5y"):
    """
    Create a ReturnCalculator by loading from product microstructure.

    Parameters
    ----------
    product : str, default "cdx_ig_5y"
        Product identifier to load microstructure params from bloomberg_securities.json.

    Returns
    -------
    ReturnCalculator
        Calculator appropriate for the product's quote_type.

    Examples
    --------
    >>> calculator = make_catalog_test_calculator()  # SpreadReturnCalculator for cdx_ig_5y
    >>> calculator = make_catalog_test_calculator("hyg")  # PriceReturnCalculator for ETF
    """
    from aponyx.data import get_product_microstructure

    microstructure = get_product_microstructure(product)
    return resolve_calculator(
        quote_type=microstructure.quote_type,
        dv01_per_million=microstructure.dv01_per_million,
    )


# Backwards compatibility alias
make_test_config = make_minimal_test_config


def make_minimal_test_metadata(**overrides) -> StrategyMetadata:
    """
    Create a StrategyMetadata with minimal defaults for unit testing.

    INTENTIONAL DEVIATION FROM CATALOG: This helper uses relaxed defaults
    (no stop-loss, no take-profit) to simplify test assertions for
    StrategyMetadata validation and conversion.

    For tests that require catalog-accurate metadata, use make_catalog_test_metadata().

    Note: StrategyMetadata no longer contains microstructure fields
    (transaction_cost_bps, dv01_per_million). These are now loaded from
    bloomberg_securities.json at runtime.

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
        "entry_threshold": None,  # Intentionally None for simpler tests (legacy behavior)
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
