"""
Unit tests for backtest module.
"""

from aponyx.backtest import BacktestConfig
from aponyx.backtest.registry import StrategyMetadata


def make_test_config(**overrides) -> BacktestConfig:
    """
    Create a BacktestConfig with test defaults for unit testing.

    This helper provides sensible defaults that match the 'balanced' strategy
    from strategy_catalog.json. Use this instead of BacktestConfig() directly
    in tests to make the test defaults explicit.

    Parameters
    ----------
    **overrides
        Any BacktestConfig parameters to override from defaults.

    Returns
    -------
    BacktestConfig
        Configuration with test defaults and any specified overrides.

    Examples
    --------
    >>> config = make_test_config()  # All test defaults
    >>> config = make_test_config(signal_lag=0)  # Override signal_lag only
    >>> config = make_test_config(stop_loss_pct=3.0, sizing_mode="binary")
    """
    defaults = {
        "position_size_mm": 10.0,
        "sizing_mode": "proportional",
        "stop_loss_pct": None,
        "take_profit_pct": None,
        "max_holding_days": None,
        "transaction_cost_bps": 1.0,
        "dv01_per_million": 475.0,
        "signal_lag": 1,
    }
    defaults.update(overrides)
    return BacktestConfig(**defaults)


def make_test_strategy_metadata(**overrides) -> StrategyMetadata:
    """
    Create a StrategyMetadata with test defaults for unit testing.

    This helper provides sensible defaults for testing StrategyMetadata
    validation and conversion. All strategy-governed fields have explicit
    defaults for testing purposes.

    Parameters
    ----------
    **overrides
        Any StrategyMetadata parameters to override from defaults.

    Returns
    -------
    StrategyMetadata
        Metadata with test defaults and any specified overrides.

    Examples
    --------
    >>> meta = make_test_strategy_metadata()  # All test defaults
    >>> meta = make_test_strategy_metadata(name="custom", stop_loss_pct=5.0)
    """
    defaults = {
        "name": "test_strategy",
        "description": "Test strategy for unit testing",
        "position_size_mm": 10.0,
        "sizing_mode": "proportional",
        "stop_loss_pct": None,
        "take_profit_pct": None,
        "max_holding_days": None,
        "transaction_cost_bps": 1.0,
        "dv01_per_million": 475.0,
        "enabled": True,
    }
    defaults.update(overrides)
    return StrategyMetadata(**defaults)
