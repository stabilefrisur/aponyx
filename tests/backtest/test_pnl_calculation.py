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
        entry_threshold=1.5,
        exit_threshold=0.5,
        position_size=10.0,  # $10MM
        dv01_per_million=100.0,  # $100 DV01 per $1MM
        transaction_cost_bps=0.0,  # Disable costs for cleaner test
    )

    result = run_backtest(signal, spread, config)

    # Verify position is held throughout
    assert (result.positions["position"] == 1).all()

    # Day 0: Entry, no previous spread, should have 0 P&L
    assert result.pnl.iloc[0]["spread_pnl"] == 0.0

    # Days 1-9: Each day should show P&L from that day's 1bp spread widening
    # Long position: spread widening = loss
    # Spread change per day = 1bp (in spread points, not decimal)
    # Expected daily P&L: -1.0 * 100 * 10 = -$1,000 per day
    expected_daily_pnl = -1.0 * config.dv01_per_million * config.position_size

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
        entry_threshold=1.5,
        exit_threshold=0.5,
        position_size=10.0,
        dv01_per_million=100.0,
        transaction_cost_bps=0.0,
    )

    result = run_backtest(signal, spread, config)

    # Day 0: Entry, no previous spread
    assert result.pnl.iloc[0]["spread_pnl"] == 0.0

    # Days 1-9: Should have incremental P&L
    # Each day spread widens by 1 point: -1.0 * 100 * 10 = -$1,000
    expected_daily = -1.0 * config.dv01_per_million * config.position_size
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
        entry_threshold=1.5,
        exit_threshold=0.5,
        position_size=10.0,
        dv01_per_million=100.0,
        transaction_cost_bps=0.0,
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
        entry_threshold=1.5,
        exit_threshold=0.5,
        position_size=10.0,
        dv01_per_million=100.0,
        transaction_cost_bps=0.0,
    )

    result = run_backtest(signal, spread, config)

    # Entry spread is first spread value
    entry_spread = spread_values[0]

    # For each day, verify cumulative P&L matches mark-to-market
    for i in range(1, 10):
        current_spread = spread_values[i]
        spread_change_from_entry = current_spread - entry_spread

        # Long position: profit when spreads tighten (negative change)
        expected_mtm = -spread_change_from_entry * config.dv01_per_million * config.position_size
        actual_cumulative = result.pnl.iloc[i]["cumulative_pnl"]

        assert abs(actual_cumulative - expected_mtm) < 0.01, (
            f"Day {i}: MTM=${expected_mtm:.2f}, Cumulative=${actual_cumulative:.2f}"
        )
