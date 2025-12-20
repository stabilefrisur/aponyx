"""
Unit tests for strategy registry.
"""

import pytest

from aponyx.backtest import BacktestConfig
from aponyx.backtest.registry import StrategyMetadata, StrategyRegistry
from aponyx.config import STRATEGY_CATALOG_PATH

from . import make_minimal_test_metadata, make_test_strategy_metadata


# ============================================================================
# Phase 6: User Story 4 - Strategy Migration Tests
# ============================================================================


def test_strategy_registry_loads_new_schema() -> None:
    """Test T035: StrategyRegistry loads new schema successfully."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

    # Should load all strategies (4 base strategies: conservative, balanced, aggressive, experimental)
    all_strategies = registry.list_all()
    assert len(all_strategies) == 4  # 4 base strategies (no _proportional variants)

    # Check that strategies have new schema fields (no microstructure fields)
    for name, metadata in all_strategies.items():
        assert hasattr(metadata, "position_size_mm")
        assert hasattr(metadata, "sizing_mode")
        assert hasattr(metadata, "stop_loss_pct")
        assert hasattr(metadata, "take_profit_pct")
        assert hasattr(metadata, "max_holding_days")
        assert hasattr(metadata, "entry_threshold")
        # Microstructure fields should NOT be in metadata
        assert not hasattr(metadata, "transaction_cost_bps")
        assert not hasattr(metadata, "dv01_per_million")


def test_all_strategies_have_position_sizing_fields() -> None:
    """Test T036: All strategies have position_size_mm and sizing_mode fields with proportional default."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

    for name, metadata in registry.list_all().items():
        # position_size_mm must be positive
        assert metadata.position_size_mm > 0, (
            f"Strategy {name}: position_size_mm must be positive"
        )

        # sizing_mode should be proportional (new default for all strategies)
        assert metadata.sizing_mode == "proportional", (
            f"Strategy {name}: sizing_mode should be 'proportional' (default)"
        )


def test_entry_threshold_present_in_strategies() -> None:
    """Test T037: entry_threshold is now a valid optional field in strategies."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

    for name, metadata in registry.list_all().items():
        # entry_threshold should now be a valid attribute (can be None or positive value)
        assert hasattr(metadata, "entry_threshold"), (
            f"Strategy {name}: entry_threshold should be an attribute"
        )
        # If set, must be positive
        if metadata.entry_threshold is not None:
            assert metadata.entry_threshold > 0, (
                f"Strategy {name}: entry_threshold must be positive if set"
            )
        # exit_threshold should NOT exist (exits are based on signal returning to zero/neutral)
        assert not hasattr(metadata, "exit_threshold"), (
            f"Strategy {name}: exit_threshold should not exist"
        )
        # Microstructure fields should also not exist (moved to product)
        assert not hasattr(metadata, "transaction_cost_bps"), (
            f"Strategy {name}: transaction_cost_bps should not exist (moved to product)"
        )
        assert not hasattr(metadata, "dv01_per_million"), (
            f"Strategy {name}: dv01_per_million should not exist (moved to product)"
        )


def test_strategy_metadata_to_config_produces_valid_backtest_config() -> None:
    """Test T038: StrategyMetadata.to_config() produces valid BacktestConfig with product params."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

    # Test microstructure params from different products
    from aponyx.data import get_product_microstructure

    products = ["cdx_ig_5y", "cdx_hy_5y"]

    for product in products:
        microstructure = get_product_microstructure(product)

        # Test for each strategy
        for name, metadata in registry.list_all().items():
            config = metadata.to_config(
                transaction_cost_bps=microstructure.transaction_cost_bps
            )

            # Should be valid BacktestConfig
            assert isinstance(config, BacktestConfig)

            # Should preserve strategy parameters
            assert config.position_size_mm == metadata.position_size_mm
            assert config.sizing_mode == metadata.sizing_mode
            assert config.stop_loss_pct == metadata.stop_loss_pct
            assert config.take_profit_pct == metadata.take_profit_pct
            assert config.max_holding_days == metadata.max_holding_days

            # Should have product microstructure parameters
            assert config.transaction_cost_bps == microstructure.transaction_cost_bps


def test_conservative_strategy_has_appropriate_risk_management() -> None:
    """Test T040: Conservative strategy has appropriate risk management parameters."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    conservative = registry.get_metadata("conservative")

    # Conservative should have smaller position size
    assert conservative.position_size_mm <= 10.0

    # Conservative should have tighter stop loss
    assert conservative.stop_loss_pct is not None
    assert conservative.stop_loss_pct <= 5.0

    # Conservative should have take profit defined
    assert conservative.take_profit_pct is not None


def test_balanced_strategy_has_moderate_parameters() -> None:
    """Test T041: Balanced strategy has moderate parameters."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    balanced = registry.get_metadata("balanced")

    # Balanced should have moderate position size
    assert balanced.position_size_mm == 10.0

    # Balanced should have moderate risk management
    assert balanced.stop_loss_pct is not None
    assert balanced.stop_loss_pct >= 3.0
    assert balanced.stop_loss_pct <= 10.0


def test_aggressive_strategy_has_wide_bands() -> None:
    """Test T042: Aggressive strategy has wide risk bands."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    aggressive = registry.get_metadata("aggressive")

    # Aggressive should have larger position size
    assert aggressive.position_size_mm >= 10.0

    # Aggressive should have wider stop loss or null take profit
    assert aggressive.stop_loss_pct is None or aggressive.stop_loss_pct >= 10.0


def test_experimental_strategy_disabled() -> None:
    """Test T043: Experimental strategy is configured for testing (enabled=false)."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    experimental = registry.get_metadata("experimental")

    # Experimental should be disabled
    assert experimental.enabled is False


def test_strategy_metadata_validation() -> None:
    """Test that StrategyMetadata validates parameters correctly."""
    # Valid metadata should work
    metadata = make_test_strategy_metadata(
        name="test",
        description="Test strategy",
        position_size_mm=10.0,
        sizing_mode="binary",
    )
    assert metadata.name == "test"

    # Invalid position_size_mm should raise
    with pytest.raises(ValueError, match="position_size_mm must be positive"):
        make_test_strategy_metadata(
            name="test",
            description="Test",
            position_size_mm=-5.0,
        )

    # Invalid sizing_mode should raise
    with pytest.raises(ValueError, match="sizing_mode must be"):
        make_test_strategy_metadata(
            name="test",
            description="Test",
            sizing_mode="invalid",
        )

    # Invalid stop_loss_pct should raise
    with pytest.raises(ValueError, match="stop_loss_pct must be in"):
        make_test_strategy_metadata(
            name="test",
            description="Test",
            stop_loss_pct=0.0,
        )

    with pytest.raises(ValueError, match="stop_loss_pct must be in"):
        make_test_strategy_metadata(
            name="test",
            description="Test",
            stop_loss_pct=150.0,
        )

    # Invalid entry_threshold should raise
    with pytest.raises(ValueError, match="entry_threshold must be positive"):
        make_test_strategy_metadata(
            name="test",
            description="Test",
            entry_threshold=0.0,
        )

    with pytest.raises(ValueError, match="entry_threshold must be positive"):
        make_test_strategy_metadata(
            name="test",
            description="Test",
            entry_threshold=-1.0,
        )

    # Valid entry_threshold should work
    metadata_with_threshold = make_test_strategy_metadata(
        name="test",
        description="Test strategy",
        entry_threshold=1.5,
    )
    assert metadata_with_threshold.entry_threshold == 1.5


def test_strategy_metadata_to_config_requires_microstructure_params() -> None:
    """Test that to_config() requires transaction_cost_bps (DV01 is now in calculator)."""
    metadata = make_test_strategy_metadata(
        name="test",
        description="Test strategy",
    )

    # Should work when transaction_cost_bps is provided
    config = metadata.to_config(
        transaction_cost_bps=1.5,
    )
    assert config.transaction_cost_bps == 1.5

    # Should fail without required params
    with pytest.raises(TypeError):
        metadata.to_config()  # type: ignore  # Missing required args


def test_strategy_metadata_to_config_preserves_entry_threshold() -> None:
    """Test that to_config() preserves entry_threshold from metadata."""
    metadata = make_test_strategy_metadata(
        name="test",
        description="Test strategy",
        entry_threshold=1.8,
    )

    config = metadata.to_config(
        transaction_cost_bps=1.5,
    )
    assert config.entry_threshold == 1.8


def test_strategy_metadata_to_config_entry_threshold_override() -> None:
    """Test that to_config() allows entry_threshold override."""
    metadata = make_test_strategy_metadata(
        name="test",
        description="Test strategy",
        entry_threshold=1.8,
    )

    # Override with different value
    config = metadata.to_config(
        transaction_cost_bps=1.5,
        entry_threshold_override=2.0,
    )
    assert config.entry_threshold == 2.0

    # Override to None (disable)
    metadata_with_threshold = make_test_strategy_metadata(
        name="test",
        description="Test strategy",
        entry_threshold=1.8,
    )
    # Note: Can't override to None since None means "use catalog value"
    # This is consistent with other override patterns
