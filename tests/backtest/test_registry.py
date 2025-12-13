"""
Unit tests for strategy registry.
"""

import pytest

from aponyx.backtest import BacktestConfig
from aponyx.backtest.registry import StrategyMetadata, StrategyRegistry
from aponyx.config import STRATEGY_CATALOG_PATH


# ============================================================================
# Phase 6: User Story 4 - Strategy Migration Tests
# ============================================================================


def test_strategy_registry_loads_new_schema() -> None:
    """Test T035: StrategyRegistry loads new schema successfully."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    
    # Should load all strategies (4 base strategies: conservative, balanced, aggressive, experimental)
    all_strategies = registry.list_all()
    assert len(all_strategies) == 4  # 4 base strategies (no _proportional variants)
    
    # Check that strategies have new schema fields
    for name, metadata in all_strategies.items():
        assert hasattr(metadata, "position_size_mm")
        assert hasattr(metadata, "sizing_mode")
        assert hasattr(metadata, "stop_loss_pct")
        assert hasattr(metadata, "take_profit_pct")
        assert hasattr(metadata, "max_holding_days")
        assert hasattr(metadata, "transaction_cost_bps")
        assert hasattr(metadata, "dv01_per_million")


def test_all_strategies_have_position_sizing_fields() -> None:
    """Test T036: All strategies have position_size_mm and sizing_mode fields with proportional default."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    
    for name, metadata in registry.list_all().items():
        # position_size_mm must be positive
        assert metadata.position_size_mm > 0, f"Strategy {name}: position_size_mm must be positive"
        
        # sizing_mode should be proportional (new default for all strategies)
        assert metadata.sizing_mode == "proportional", (
            f"Strategy {name}: sizing_mode should be 'proportional' (default)"
        )


def test_entry_exit_thresholds_not_present() -> None:
    """Test T037: entry_threshold/exit_threshold are not present in loaded strategies."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    
    for name, metadata in registry.list_all().items():
        # Old fields should not exist
        assert not hasattr(metadata, "entry_threshold"), (
            f"Strategy {name}: entry_threshold should not exist"
        )
        assert not hasattr(metadata, "exit_threshold"), (
            f"Strategy {name}: exit_threshold should not exist"
        )


def test_strategy_metadata_to_config_produces_valid_backtest_config() -> None:
    """Test T038: StrategyMetadata.to_config() produces valid BacktestConfig."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    
    # Test for each strategy
    for name, metadata in registry.list_all().items():
        config = metadata.to_config()
        
        # Should be valid BacktestConfig
        assert isinstance(config, BacktestConfig)
        
        # Should preserve strategy parameters
        assert config.position_size_mm == metadata.position_size_mm
        assert config.sizing_mode == metadata.sizing_mode
        assert config.stop_loss_pct == metadata.stop_loss_pct
        assert config.take_profit_pct == metadata.take_profit_pct
        assert config.max_holding_days == metadata.max_holding_days
        assert config.transaction_cost_bps == metadata.transaction_cost_bps
        assert config.dv01_per_million == metadata.dv01_per_million


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
    assert (aggressive.stop_loss_pct is None or aggressive.stop_loss_pct >= 10.0)


def test_experimental_strategy_disabled() -> None:
    """Test T043: Experimental strategy is configured for testing (enabled=false)."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    experimental = registry.get_metadata("experimental")
    
    # Experimental should be disabled
    assert experimental.enabled is False


def test_strategy_metadata_validation() -> None:
    """Test that StrategyMetadata validates parameters correctly."""
    # Valid metadata should work
    metadata = StrategyMetadata(
        name="test",
        description="Test strategy",
        position_size_mm=10.0,
        sizing_mode="binary",
    )
    assert metadata.name == "test"
    
    # Invalid position_size_mm should raise
    with pytest.raises(ValueError, match="position_size_mm must be positive"):
        StrategyMetadata(
            name="test",
            description="Test",
            position_size_mm=-5.0,
        )
    
    # Invalid sizing_mode should raise
    with pytest.raises(ValueError, match="sizing_mode must be"):
        StrategyMetadata(
            name="test",
            description="Test",
            sizing_mode="invalid",
        )
    
    # Invalid stop_loss_pct should raise
    with pytest.raises(ValueError, match="stop_loss_pct must be in"):
        StrategyMetadata(
            name="test",
            description="Test",
            stop_loss_pct=0.0,
        )
    
    with pytest.raises(ValueError, match="stop_loss_pct must be in"):
        StrategyMetadata(
            name="test",
            description="Test",
            stop_loss_pct=150.0,
        )

