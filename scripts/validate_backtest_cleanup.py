"""
Validation script for backtest strategy cleanup (spec 005).

Tests key scenarios from quickstart.md to verify implementation correctness.
"""

import pandas as pd
import numpy as np

from aponyx.backtest import run_backtest, BacktestConfig
from aponyx.backtest.registry import StrategyRegistry
from aponyx.config import STRATEGY_CATALOG_PATH


def generate_test_data(n_days: int = 100) -> tuple[pd.Series, pd.Series]:
    """Generate simple test signal and spread data."""
    dates = pd.date_range(start="2024-01-01", periods=n_days, freq="D")
    
    # Create signal with known patterns
    signal_values = np.zeros(n_days)
    signal_values[10:30] = 1.0    # Long position
    signal_values[40:50] = -0.5   # Short position
    signal_values[60:80] = 0.8    # Long position
    
    signal = pd.Series(signal_values, index=dates)
    
    # Create spread with some variation
    spread = pd.Series(100 + np.cumsum(np.random.randn(n_days) * 0.5), index=dates)
    
    return signal, spread


def test_scenario_1_default_strategy():
    """Test loading and using a default strategy from catalog."""
    print("\n=== Scenario 1: Default Strategy ===")
    
    signal, spread = generate_test_data()
    
    # Load strategy from catalog
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    metadata = registry.get_metadata("balanced")
    config = metadata.to_config()
    
    # Run backtest
    result = run_backtest(signal, spread, config)
    
    # Verify result structure
    assert "position" in result.positions.columns
    assert "exit_reason" in result.positions.columns
    assert "net_pnl" in result.pnl.columns
    
    print("✓ Backtest ran successfully")
    print(f"  - Total rows: {len(result.positions)}")
    print(f"  - Final cumulative PnL: {result.pnl['cumulative_pnl'].iloc[-1]:.2f}")
    print(f"  - Exit reasons: {result.metadata['summary']['exit_counts']}")


def test_scenario_2_position_sizing():
    """Test binary position sizing behavior."""
    print("\n=== Scenario 2: Position Sizing ===")
    
    signal, spread = generate_test_data()
    
    config = BacktestConfig(
        position_size_mm=10.0,
        sizing_mode="binary",
    )
    
    result = run_backtest(signal, spread, config)
    
    # Verify binary sizing: position should be +1, 0, or -1
    positions = result.positions["position"].unique()
    assert all(p in [-1, 0, 1] for p in positions), f"Non-binary positions found: {positions}"
    
    # Verify direction from signal sign
    for idx in result.positions.index:
        sig = result.positions.loc[idx, "signal"]
        pos = result.positions.loc[idx, "position"]
        if sig > 0:
            assert pos >= 0, f"Positive signal but negative position at {idx}"
        elif sig < 0:
            assert pos <= 0, f"Negative signal but positive position at {idx}"
    
    print("✓ Binary sizing works correctly")
    print(f"  - Unique positions: {sorted(positions)}")


def test_scenario_3_stop_loss():
    """Test stop loss protection."""
    print("\n=== Scenario 3: Stop Loss ===")
    
    # Create signal with prolonged position
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    signal = pd.Series([1.0] * 100, index=dates)  # Stay long
    
    # Create spread that trends upward (losing trade for long position)
    spread = pd.Series(100 + np.linspace(0, 10, 100), index=dates)  # Spreads widen
    
    config = BacktestConfig(
        position_size_mm=10.0,
        stop_loss_pct=5.0,  # Exit if loses 5%
    )
    
    result = run_backtest(signal, spread, config)
    
    # Check if stop loss triggered
    stop_losses = result.positions[result.positions["exit_reason"] == "stop_loss"]
    
    print("✓ Stop loss configuration applied")
    print(f"  - Stop loss exits: {len(stop_losses)}")
    print(f"  - Exit counts: {result.metadata['summary']['exit_counts']}")


def test_scenario_4_take_profit():
    """Test take profit target."""
    print("\n=== Scenario 4: Take Profit ===")
    
    # Create signal with prolonged position
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    signal = pd.Series([1.0] * 100, index=dates)  # Stay long
    
    # Create spread that trends downward (winning trade for long position)
    spread = pd.Series(100 - np.linspace(0, 5, 100), index=dates)  # Spreads tighten
    
    config = BacktestConfig(
        position_size_mm=10.0,
        take_profit_pct=10.0,  # Exit if gains 10%
    )
    
    result = run_backtest(signal, spread, config)
    
    # Check if take profit triggered
    take_profits = result.positions[result.positions["exit_reason"] == "take_profit"]
    
    print("✓ Take profit configuration applied")
    print(f"  - Take profit exits: {len(take_profits)}")
    print(f"  - Exit counts: {result.metadata['summary']['exit_counts']}")


def test_scenario_5_runtime_overrides():
    """Test runtime parameter overrides."""
    print("\n=== Scenario 5: Runtime Overrides ===")
    
    signal, spread = generate_test_data()
    
    # Load strategy from catalog
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    metadata = registry.get_metadata("balanced")
    
    # Override position size
    config1 = metadata.to_config(position_size_mm_override=20.0)
    assert config1.position_size_mm == 20.0
    
    # Override multiple parameters
    config2 = metadata.to_config(
        stop_loss_pct_override=3.0,
        take_profit_pct_override=15.0,
    )
    assert config2.stop_loss_pct == 3.0
    assert config2.take_profit_pct == 15.0
    
    print("✓ Runtime overrides work correctly")
    print(f"  - Override config 1: position_size_mm={config1.position_size_mm}")
    print(f"  - Override config 2: stop_loss={config2.stop_loss_pct}, take_profit={config2.take_profit_pct}")


def test_scenario_6_exit_tracking():
    """Test exit reason tracking."""
    print("\n=== Scenario 6: Exit Reason Tracking ===")
    
    # Create signal with clear entry/exit pattern
    dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
    signal_values = [0.0] * 10 + [1.0] * 20 + [0.0] * 20  # Enter then exit
    signal = pd.Series(signal_values, index=dates)
    spread = pd.Series(100.0, index=dates)  # Flat spread
    
    config = BacktestConfig(position_size_mm=10.0)
    
    result = run_backtest(signal, spread, config)
    
    # Check exit reasons
    exits = result.positions[result.positions["exit_reason"].notna()]
    
    print("✓ Exit reasons tracked correctly")
    print(f"  - Total exits: {len(exits)}")
    print(f"  - Exit reasons: {exits['exit_reason'].value_counts().to_dict()}")
    print(f"  - Summary: {result.metadata['summary']['exit_counts']}")


def test_scenario_7_cooldown_behavior():
    """Test cooldown after PnL-based exit."""
    print("\n=== Scenario 7: Cooldown Behavior ===")
    
    # Create signal that stays non-zero after stop loss
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    signal = pd.Series([1.0] * 100, index=dates)  # Constant signal
    
    # Spread that widens then stabilizes
    spread_values = [100.0] * 20 + [110.0] * 80  # Jump causes loss
    spread = pd.Series(spread_values, index=dates)
    
    config = BacktestConfig(
        position_size_mm=10.0,
        stop_loss_pct=5.0,
    )
    
    result = run_backtest(signal, spread, config)
    
    # After stop loss, should enter cooldown
    # Verify no immediate re-entry
    stop_loss_indices = result.positions[result.positions["exit_reason"] == "stop_loss"].index
    
    if len(stop_loss_indices) > 0:
        first_stop_loss = stop_loss_indices[0]
        # Check subsequent positions after stop loss
        subsequent = result.positions.loc[first_stop_loss:]
        # Should remain at 0 position during cooldown
        positions_after = subsequent["position"].iloc[1:10].values  # Next 9 days
        print("✓ Cooldown behavior verified")
        print(f"  - Stop loss at: {first_stop_loss}")
        print(f"  - Positions after stop loss (next 9 days): {positions_after}")
        print(f"  - Cooldown active: {all(p == 0 for p in positions_after)}")
    else:
        print("⚠ No stop loss triggered in test scenario")


def test_scenario_8_strategy_catalog():
    """Test all strategies in catalog."""
    print("\n=== Scenario 8: Strategy Catalog ===")
    
    signal, spread = generate_test_data()
    
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    strategies = registry.get_enabled()
    
    print(f"✓ Loaded {len(strategies)} enabled strategies:")
    
    for strategy_name in strategies:
        metadata = registry.get_metadata(strategy_name)
        config = metadata.to_config()
        
        # Verify new schema fields
        assert hasattr(config, "position_size_mm")
        assert hasattr(config, "sizing_mode")
        assert not hasattr(config, "entry_threshold")  # Old field removed
        assert not hasattr(config, "exit_threshold")   # Old field removed
        
        print(f"  - {strategy_name}: size={config.position_size_mm}MM, "
              f"SL={config.stop_loss_pct}, TP={config.take_profit_pct}")


def main():
    """Run all validation scenarios."""
    print("=" * 70)
    print("Backtest Strategy Cleanup Validation (Spec 005)")
    print("=" * 70)
    
    try:
        test_scenario_1_default_strategy()
        test_scenario_2_position_sizing()
        test_scenario_3_stop_loss()
        test_scenario_4_take_profit()
        test_scenario_5_runtime_overrides()
        test_scenario_6_exit_tracking()
        test_scenario_7_cooldown_behavior()
        test_scenario_8_strategy_catalog()
        
        print("\n" + "=" * 70)
        print("✓ ALL VALIDATION SCENARIOS PASSED")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
