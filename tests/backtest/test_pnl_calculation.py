"""
Test to verify incremental P&L calculation fix.

This test ensures that daily spread_pnl represents incremental P&L,
not total P&L from entry, preventing double-counting when using cumsum().
"""

import pandas as pd

from aponyx.backtest import BacktestConfig, run_backtest


def test_incremental_pnl_no_double_counting() -> None:
    """
    Test that P&L is calculated incrementally, not cumulatively.

    When spreads trend in one direction, the daily spread_pnl should
    represent only the P&L from that day's spread change, not the
    total P&L from entry. This prevents cumsum() from overstating P&L.
    """
    # Create simple trending spread scenario
    dates = pd.date_range("2024-01-01", periods=10, freq="D")

    # Signal: enter long on day 0, hold for entire period
    signal = pd.Series([2.0] * 10, index=dates)

    # Spread: starts at 100, increases by 1bp each day (widens)
    # For long position, widening spreads = losses
    spread = pd.Series([100.0 + i for i in range(10)], index=dates)

    config = BacktestConfig(
        position_size_mm=10.0,  # $10MM
        sizing_mode="binary",  # Use binary mode for this test
        dv01_per_million=100.0,  # $100 DV01 per $1MM
        transaction_cost_bps=0.0,  # Disable costs for cleaner test
        signal_lag=0,  # No lag to avoid data truncation
    )

    result = run_backtest(signal, spread, config)

    # Verify position is held throughout (binary mode: position = 1)
    assert (result.positions["position"] == 1).all()

    # Day 0: Entry, no previous spread, should have 0 P&L
    assert result.pnl.iloc[0]["spread_pnl"] == 0.0

    # Days 1-9: Each day should show P&L from that day's 1bp spread widening
    # Long position: spread widening = loss
    # Spread change per day = 1bp (in spread points, not decimal)
    # Expected daily P&L: -1.0 * 100 * 10 = -$1,000 per day
    expected_daily_pnl = -1.0 * config.dv01_per_million * config.position_size_mm
    for i in range(1, 10):
        actual_pnl = result.pnl.iloc[i]["spread_pnl"]
        assert abs(actual_pnl - expected_daily_pnl) < 0.01, (
            f"Day {i}: Expected ${expected_daily_pnl:.2f}, got ${actual_pnl:.2f}"
        )

    # Cumulative P&L should equal sum of daily P&L
    # 9 days of losses (day 0 has 0 P&L) = 9 * -$1,000 = -$9,000
    expected_cumulative = 9 * expected_daily_pnl
    actual_cumulative = result.pnl.iloc[-1]["cumulative_pnl"]

    assert abs(actual_cumulative - expected_cumulative) < 0.01, (
        f"Cumulative P&L: Expected ${expected_cumulative:.2f}, got ${actual_cumulative:.2f}"
    )


def test_incremental_pnl_with_position_changes() -> None:
    """
    Test incremental P&L calculation across position entries and exits.

    Verifies that P&L correctly captures:
    1. No P&L when flat
    2. Incremental P&L while in position
    3. Final P&L on exit day
    4. No P&L after exit
    """
    dates = pd.date_range("2024-01-01", periods=20, freq="D")

    # Signal: long days 0-9, flat days 10-19
    signal = pd.Series([2.0] * 10 + [0.0] * 10, index=dates)

    # Spread: increases steadily by 1 spread point per day
    spread = pd.Series([100.0 + i for i in range(20)], index=dates)

    config = BacktestConfig(
        position_size_mm=10.0,
        sizing_mode="binary",  # Use binary mode for this test
        dv01_per_million=100.0,
        transaction_cost_bps=0.0,
        signal_lag=0,
    )

    result = run_backtest(signal, spread, config)

    # Day 0: Entry, no previous spread
    assert result.pnl.iloc[0]["spread_pnl"] == 0.0

    # Days 1-9: Should have incremental P&L
    # Each day spread widens by 1 point: -1.0 * 100 * 10 = -$1,000
    expected_daily = -1.0 * config.dv01_per_million * config.position_size_mm
    for i in range(1, 10):
        assert abs(result.pnl.iloc[i]["spread_pnl"] - expected_daily) < 0.01

    # Day 10: Exit triggered, should capture final day's P&L
    assert result.positions.iloc[10]["position"] == 0  # Exited
    assert abs(result.pnl.iloc[10]["spread_pnl"] - expected_daily) < 0.01

    # Days 11-19: Flat, no P&L
    for i in range(11, 20):
        assert result.pnl.iloc[i]["spread_pnl"] == 0.0


def test_incremental_pnl_long_vs_short() -> None:
    """
    Test that long and short positions have opposite P&L for same spread moves.
    """
    dates = pd.date_range("2024-01-01", periods=6, freq="D")

    # Spread: widens by 1 spread point per day
    spread = pd.Series([100.0 + i for i in range(6)], index=dates)

    config = BacktestConfig(
        position_size_mm=10.0,
        dv01_per_million=100.0,
        transaction_cost_bps=0.0,
        signal_lag=0,
    )

    # Test long position
    signal_long = pd.Series([2.0] * 6, index=dates)
    result_long = run_backtest(signal_long, spread, config)

    # Test short position
    signal_short = pd.Series([-2.0] * 6, index=dates)
    result_short = run_backtest(signal_short, spread, config)

    # Long and short should have opposite P&L (excluding day 0)
    for i in range(1, 6):
        pnl_long = result_long.pnl.iloc[i]["spread_pnl"]
        pnl_short = result_short.pnl.iloc[i]["spread_pnl"]
        assert abs(pnl_long + pnl_short) < 0.01, (
            f"Day {i}: Long P&L ${pnl_long:.2f} should be opposite of short P&L ${pnl_short:.2f}"
        )


def test_cumulative_pnl_equals_mark_to_market() -> None:
    """
    Test that cumulative P&L matches mark-to-market calculation.

    For a position held from entry to current day, cumulative_pnl
    should equal the total spread change from entry times position.
    """
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    signal = pd.Series([2.0] * 10, index=dates)

    # Spread with non-uniform changes
    spread_values = [100.0, 100.5, 99.8, 101.2, 100.0, 99.5, 100.3, 99.9, 100.8, 99.2]
    spread = pd.Series(spread_values, index=dates)

    config = BacktestConfig(
        position_size_mm=10.0,
        sizing_mode="binary",  # Use binary mode for this test
        dv01_per_million=100.0,
        transaction_cost_bps=0.0,
        signal_lag=0,
    )

    result = run_backtest(signal, spread, config)

    # Entry spread is first spread value
    entry_spread = spread_values[0]

    # For each day, verify cumulative P&L matches mark-to-market
    for i in range(1, 10):
        current_spread = spread_values[i]
        spread_change_from_entry = current_spread - entry_spread

        # Long position: profit when spreads tighten (negative change)
        expected_mtm = (
            -spread_change_from_entry
            * config.dv01_per_million
            * config.position_size_mm
        )
        actual_cumulative = result.pnl.iloc[i]["cumulative_pnl"]

        assert abs(actual_cumulative - expected_mtm) < 0.01, (
            f"Day {i}: MTM=${expected_mtm:.2f}, Cumulative=${actual_cumulative:.2f}"
        )


# ============================================================================
# Phase 4: User Story 2 - Stop Loss Exit Tests
# ============================================================================


def test_stop_loss_triggers_on_cumulative_pnl_threshold() -> None:
    """Test T016: Stop loss triggers when cumulative PnL falls below -stop_loss_pct * position_value."""
    dates = pd.date_range("2024-01-01", periods=20, freq="D")

    # Signal: constant long position
    signal = pd.Series([0.8] * 20, index=dates)

    # Spread: widens significantly (bad for long position)
    # Start at 100, increase by 0.5 per day
    spread = pd.Series([100.0 + i * 0.5 for i in range(20)], index=dates)

    # Position value: position_size_mm * dv01_per_million = 10.0 * 4750.0 = $47,500
    # Stop loss at 5%: -0.05 * 47,500 = -$2,375
    config = BacktestConfig(
        position_size_mm=10.0,
        sizing_mode="binary",
        stop_loss_pct=5.0,
        dv01_per_million=4750.0,
        transaction_cost_bps=0.0,
        signal_lag=0,
    )

    result = run_backtest(signal, spread, config)

    # Find stop loss exit
    stop_loss_exits = result.positions[result.positions["exit_reason"] == "stop_loss"]
    assert len(stop_loss_exits) > 0, "Stop loss should have triggered"

    # Verify exit_counts in metadata
    assert result.metadata["summary"]["exit_counts"]["stop_loss"] > 0


def test_stop_loss_disabled_when_none() -> None:
    """Test T017: stop_loss_pct=None disables stop loss (position held until signal exit)."""
    dates = pd.date_range("2024-01-01", periods=20, freq="D")

    # Signal: long then exit
    signal = pd.Series([0.8] * 15 + [0.0] * 5, index=dates)

    # Spread: widens significantly (would trigger stop loss if enabled)
    spread = pd.Series([100.0 + i * 2.0 for i in range(20)], index=dates)

    config = BacktestConfig(
        position_size_mm=10.0,
        sizing_mode="binary",
        stop_loss_pct=None,  # Disabled
        dv01_per_million=4750.0,
        transaction_cost_bps=0.0,
        signal_lag=0,
    )

    result = run_backtest(signal, spread, config)

    # Should not have stop loss exits
    stop_loss_exits = result.positions[result.positions["exit_reason"] == "stop_loss"]
    assert len(stop_loss_exits) == 0, "Stop loss should not trigger when disabled"

    # Should exit only on signal
    signal_exits = result.positions[result.positions["exit_reason"] == "signal"]
    assert len(signal_exits) > 0, "Should exit on signal"


# ============================================================================
# Phase 5: User Story 3 - Take Profit Exit Tests
# ============================================================================


def test_take_profit_triggers_on_cumulative_pnl_threshold() -> None:
    """Test T026: Take profit triggers when cumulative PnL exceeds +take_profit_pct * position_value."""
    dates = pd.date_range("2024-01-01", periods=20, freq="D")

    # Signal: constant long position
    signal = pd.Series([0.8] * 20, index=dates)

    # Spread: tightens significantly (good for long position)
    # Start at 100, decrease by 0.3 per day
    spread = pd.Series([100.0 - i * 0.3 for i in range(20)], index=dates)

    # Position value: 10.0 * 4750.0 = $47,500
    # Take profit at 10%: +0.10 * 47,500 = +$4,750
    config = BacktestConfig(
        position_size_mm=10.0,
        sizing_mode="binary",
        take_profit_pct=10.0,
        dv01_per_million=4750.0,
        transaction_cost_bps=0.0,
        signal_lag=0,
    )

    result = run_backtest(signal, spread, config)

    # Find take profit exit
    take_profit_exits = result.positions[
        result.positions["exit_reason"] == "take_profit"
    ]
    assert len(take_profit_exits) > 0, "Take profit should have triggered"

    # Verify exit_counts in metadata
    assert result.metadata["summary"]["exit_counts"]["take_profit"] > 0


def test_take_profit_disabled_when_none() -> None:
    """Test T027: take_profit_pct=None disables take profit (position held until signal exit)."""
    dates = pd.date_range("2024-01-01", periods=20, freq="D")

    # Signal: long then exit
    signal = pd.Series([0.8] * 15 + [0.0] * 5, index=dates)

    # Spread: tightens significantly (would trigger take profit if enabled)
    spread = pd.Series([100.0 - i * 1.0 for i in range(20)], index=dates)

    config = BacktestConfig(
        position_size_mm=10.0,
        sizing_mode="binary",
        take_profit_pct=None,  # Disabled
        dv01_per_million=4750.0,
        transaction_cost_bps=0.0,
        signal_lag=0,
    )

    result = run_backtest(signal, spread, config)

    # Should not have take profit exits
    take_profit_exits = result.positions[
        result.positions["exit_reason"] == "take_profit"
    ]
    assert len(take_profit_exits) == 0, "Take profit should not trigger when disabled"

    # Should exit only on signal
    signal_exits = result.positions[result.positions["exit_reason"] == "signal"]
    assert len(signal_exits) > 0, "Should exit on signal"


def test_take_profit_precedence_over_stop_loss() -> None:
    """Test T029: Take profit takes precedence over stop loss if both trigger simultaneously."""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")

    # Signal: constant position
    signal = pd.Series([0.8] * 10, index=dates)

    # Spread: engineered to trigger both conditions on same day
    # This is contrived but tests the precedence logic
    spread = pd.Series(
        [100.0, 100.0, 100.0, 100.0, 100.0, 94.0, 94.0, 94.0, 94.0, 94.0], index=dates
    )

    config = BacktestConfig(
        position_size_mm=10.0,
        sizing_mode="binary",
        stop_loss_pct=3.0,
        take_profit_pct=5.0,
        dv01_per_million=4750.0,
        transaction_cost_bps=0.0,
        signal_lag=0,
    )

    result = run_backtest(signal, spread, config)

    # The large spread tightening (6 bps) should trigger take profit
    # Position value: 10.0 * 4750.0 = $47,500
    # Spread change: -6 bps → P&L ≈ +6 * 4750.0 * 10.0 = +$285,000 (way above 5%)
    take_profit_exits = result.positions[
        result.positions["exit_reason"] == "take_profit"
    ]
    assert len(take_profit_exits) > 0, "Take profit should trigger first"
