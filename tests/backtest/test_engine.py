"""
Unit tests for backtest engine.
"""

import numpy as np
import pandas as pd
import pytest

from aponyx.backtest import (
    BacktestConfig,
    run_backtest,
)
from aponyx.evaluation.performance import compute_all_metrics


@pytest.fixture
def sample_signal_and_spread() -> tuple[pd.Series, pd.Series]:
    """Generate synthetic signal and spread data for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    np.random.seed(42)

    # Create signal with clear regime changes
    signal = pd.Series(
        np.concatenate(
            [
                np.full(20, 0.5),  # Neutral
                np.full(15, 2.0),  # Strong long
                np.full(20, 0.3),  # Neutral
                np.full(15, -2.0),  # Strong short
                np.full(30, 0.2),  # Neutral
            ]
        ),
        index=dates,
    )

    # Spread that trends opposite to position (for P&L testing)
    spread = pd.Series(
        100 + np.cumsum(np.random.randn(100) * 0.5),
        index=dates,
    )

    return signal, spread


def test_backtest_config_validation() -> None:
    """Test that config validation catches invalid parameters."""
    # Valid config should work
    BacktestConfig(entry_threshold=1.5, exit_threshold=0.5)

    # Entry <= exit should raise
    with pytest.raises(ValueError, match="entry_threshold.*must be >"):
        BacktestConfig(entry_threshold=1.0, exit_threshold=1.0)

    # Negative position size should raise
    with pytest.raises(ValueError, match="position_size must be positive"):
        BacktestConfig(position_size=-10.0)

    # Negative transaction cost should raise
    with pytest.raises(ValueError, match="transaction_cost_bps must be non-negative"):
        BacktestConfig(transaction_cost_bps=-1.0)

    # Negative signal lag should raise
    with pytest.raises(ValueError, match="signal_lag must be non-negative"):
        BacktestConfig(signal_lag=-1)

    # Test default signal_lag value
    config = BacktestConfig()
    assert config.signal_lag == 1  # Default should be 1 for realistic execution


def test_run_backtest_returns_result(
    sample_signal_and_spread: tuple[pd.Series, pd.Series],
) -> None:
    """Test that backtest returns properly structured result."""
    signal, spread = sample_signal_and_spread
    result = run_backtest(signal, spread)

    # Check structure
    assert hasattr(result, "positions")
    assert hasattr(result, "pnl")
    assert hasattr(result, "metadata")

    # Check positions DataFrame
    assert isinstance(result.positions, pd.DataFrame)
    assert "signal" in result.positions.columns
    assert "position" in result.positions.columns
    assert "days_held" in result.positions.columns
    assert "spread" in result.positions.columns

    # Check P&L DataFrame
    assert isinstance(result.pnl, pd.DataFrame)
    assert "spread_pnl" in result.pnl.columns
    assert "cost" in result.pnl.columns
    assert "net_pnl" in result.pnl.columns
    assert "cumulative_pnl" in result.pnl.columns

    # Check metadata
    assert "config" in result.metadata
    assert "summary" in result.metadata


def test_run_backtest_generates_positions(
    sample_signal_and_spread: tuple[pd.Series, pd.Series],
) -> None:
    """Test that backtest generates positions based on thresholds."""
    signal, spread = sample_signal_and_spread
    config = BacktestConfig(entry_threshold=1.5, exit_threshold=0.5)
    result = run_backtest(signal, spread, config)

    # Should have some long positions (signal = 2.0)
    assert (result.positions["position"] == 1).any()

    # Should have some short positions (signal = -2.0)
    assert (result.positions["position"] == -1).any()

    # Should have neutral periods (signal below threshold)
    assert (result.positions["position"] == 0).any()


def test_run_backtest_tracks_holding_period(
    sample_signal_and_spread: tuple[pd.Series, pd.Series],
) -> None:
    """Test that backtest correctly tracks days held."""
    signal, spread = sample_signal_and_spread
    result = run_backtest(signal, spread)

    # When in position, days_held should increment
    in_position = result.positions[result.positions["position"] != 0]
    if len(in_position) > 1:
        # Days held should increase during position
        consecutive_positions = in_position[
            in_position.index.to_series().diff() == pd.Timedelta(days=1)
        ]
        if len(consecutive_positions) > 0:
            assert (consecutive_positions["days_held"] > 0).any()


def test_run_backtest_applies_transaction_costs(
    sample_signal_and_spread: tuple[pd.Series, pd.Series],
) -> None:
    """Test that transaction costs are applied on trades."""
    signal, spread = sample_signal_and_spread
    config = BacktestConfig(transaction_cost_bps=2.0, position_size=10.0)
    result = run_backtest(signal, spread, config)

    # Total costs should be positive (costs incurred)
    total_costs = result.pnl["cost"].sum()
    assert total_costs > 0

    # Costs should only occur on trade entry/exit
    trades = result.positions["position"].diff().fillna(0) != 0
    n_trades = trades.sum()
    if n_trades > 0:
        assert result.pnl["cost"].gt(0).sum() <= n_trades


def test_run_backtest_calculates_pnl(
    sample_signal_and_spread: tuple[pd.Series, pd.Series],
) -> None:
    """Test that P&L calculation is reasonable."""
    signal, spread = sample_signal_and_spread
    result = run_backtest(signal, spread)

    # Net P&L should be spread P&L minus costs
    expected_net = result.pnl["spread_pnl"] - result.pnl["cost"]
    pd.testing.assert_series_equal(result.pnl["net_pnl"], expected_net, check_names=False)

    # Cumulative P&L should be cumulative sum of net P&L
    expected_cum = result.pnl["net_pnl"].cumsum()
    pd.testing.assert_series_equal(result.pnl["cumulative_pnl"], expected_cum, check_names=False)


def test_compute_all_metrics_structure() -> None:
    """Test that performance metrics returns all expected fields."""
    # Create simple synthetic backtest result
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    pnl_df = pd.DataFrame(
        {
            "net_pnl": np.random.randn(100) * 100,
            "cumulative_pnl": np.cumsum(np.random.randn(100) * 100),
        },
        index=dates,
    )
    positions_df = pd.DataFrame(
        {
            "position": np.random.choice([0, 1, -1], size=100),
            "days_held": np.random.randint(0, 10, size=100),
        },
        index=dates,
    )

    metrics = compute_all_metrics(pnl_df, positions_df)

    # Check all fields exist
    assert hasattr(metrics, "sharpe_ratio")
    assert hasattr(metrics, "sortino_ratio")
    assert hasattr(metrics, "max_drawdown")
    assert hasattr(metrics, "calmar_ratio")
    assert hasattr(metrics, "total_return")
    assert hasattr(metrics, "annualized_return")
    assert hasattr(metrics, "annualized_volatility")
    assert hasattr(metrics, "hit_rate")
    assert hasattr(metrics, "avg_win")
    assert hasattr(metrics, "avg_loss")
    assert hasattr(metrics, "win_loss_ratio")
    assert hasattr(metrics, "n_trades")
    assert hasattr(metrics, "avg_holding_days")


def test_compute_all_metrics_values(
    sample_signal_and_spread: tuple[pd.Series, pd.Series],
) -> None:
    """Test that performance metrics have reasonable values."""
    signal, spread = sample_signal_and_spread
    result = run_backtest(signal, spread)
    metrics = compute_all_metrics(result.pnl, result.positions)

    # Hit rate should be between 0 and 1
    assert 0.0 <= metrics.hit_rate <= 1.0

    # Max drawdown should be negative or zero
    assert metrics.max_drawdown <= 0

    # Number of trades should be non-negative integer
    assert metrics.n_trades >= 0
    assert isinstance(metrics.n_trades, int)

    # Average holding days should be non-negative
    assert metrics.avg_holding_days >= 0


def test_backtest_metadata_logging(
    sample_signal_and_spread: tuple[pd.Series, pd.Series],
) -> None:
    """Test that backtest logs complete metadata."""
    signal, spread = sample_signal_and_spread
    config = BacktestConfig(entry_threshold=2.0, position_size=15.0)
    result = run_backtest(signal, spread, config)

    # Check config is logged
    assert result.metadata["config"]["entry_threshold"] == 2.0
    assert result.metadata["config"]["position_size"] == 15.0

    # Check summary statistics exist
    assert "n_trades" in result.metadata["summary"]
    assert "total_pnl" in result.metadata["summary"]
    assert "start_date" in result.metadata["summary"]
    assert "end_date" in result.metadata["summary"]


def test_backtest_with_max_holding_days(
    sample_signal_and_spread: tuple[pd.Series, pd.Series],
) -> None:
    """Test that max holding days constraint is enforced."""
    signal, spread = sample_signal_and_spread
    config = BacktestConfig(entry_threshold=1.5, max_holding_days=5)
    result = run_backtest(signal, spread, config)

    # No position should be held longer than max_holding_days
    in_position = result.positions[result.positions["position"] != 0]
    if len(in_position) > 0:
        assert in_position["days_held"].max() <= config.max_holding_days


def test_run_backtest_validates_index_types() -> None:
    """Test that backtest validates input index types."""
    # Create signal and spread with non-datetime indices
    signal = pd.Series([1.0, 2.0, 3.0], index=[0, 1, 2])
    spread = pd.Series([100.0, 101.0, 102.0], index=[0, 1, 2])

    # Should raise ValueError for non-DatetimeIndex
    with pytest.raises(ValueError, match="signal must have DatetimeIndex"):
        run_backtest(signal, spread)

    # Test with valid signal but invalid spread
    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    signal_valid = pd.Series([1.0, 2.0, 3.0], index=dates)

    with pytest.raises(ValueError, match="spread must have DatetimeIndex"):
        run_backtest(signal_valid, spread)


def test_run_backtest_validates_empty_data_after_alignment() -> None:
    """Test that backtest raises error when alignment produces no valid data."""
    # Create non-overlapping date ranges
    dates1 = pd.date_range("2024-01-01", periods=5, freq="D")
    dates2 = pd.date_range("2024-02-01", periods=5, freq="D")

    signal = pd.Series([1.0, 2.0, 3.0, 2.0, 1.0], index=dates1)
    spread = pd.Series([100.0, 101.0, 102.0, 101.0, 100.0], index=dates2)

    with pytest.raises(ValueError, match="No valid data after alignment"):
        run_backtest(signal, spread, BacktestConfig(signal_lag=0))


def test_signal_lag_shifts_execution() -> None:
    """Test that signal_lag properly delays signal execution."""
    # Create deterministic signal and spread
    dates = pd.date_range("2024-01-01", periods=10, freq="D")

    # Strong signal on day 3 only
    signal = pd.Series([0.0] * 10, index=dates)
    signal.iloc[3] = 3.0  # Strong long signal

    # Constant spread for simplicity
    spread = pd.Series([100.0] * 10, index=dates)

    # Test with no lag (default behavior)
    config_no_lag = BacktestConfig(entry_threshold=2.0, signal_lag=0)
    result_no_lag = run_backtest(signal, spread, config_no_lag)

    # Test with 1-day lag
    config_lag = BacktestConfig(entry_threshold=2.0, signal_lag=1)
    result_lag = run_backtest(signal, spread, config_lag)

    # With no lag, position should be taken on day 3 (when signal appears)
    # With 1-day lag, position should be taken on day 4 (next day)

    # Find first non-zero position for each backtest
    first_position_no_lag = (
        result_no_lag.positions[result_no_lag.positions["position"] != 0].index[0]
        if (result_no_lag.positions["position"] != 0).any()
        else None
    )

    first_position_lag = (
        result_lag.positions[result_lag.positions["position"] != 0].index[0]
        if (result_lag.positions["position"] != 0).any()
        else None
    )

    # Verify lag effect
    if first_position_no_lag is not None and first_position_lag is not None:
        assert first_position_lag > first_position_no_lag
        assert (first_position_lag - first_position_no_lag).days == 1


def test_signal_lag_metadata_logging() -> None:
    """Test that signal_lag is properly logged in metadata."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    signal = pd.Series(np.random.randn(50), index=dates)
    spread = pd.Series(100 + np.random.randn(50), index=dates)

    config = BacktestConfig(signal_lag=2)
    result = run_backtest(signal, spread, config)

    # Verify signal_lag is in metadata
    assert "signal_lag" in result.metadata["config"]
    assert result.metadata["config"]["signal_lag"] == 2


def test_signal_lag_prevents_look_ahead_bias() -> None:
    """Test that signal_lag prevents using future information."""
    # Create scenario where future signal would affect past trades without lag
    dates = pd.date_range("2024-01-01", periods=20, freq="D")

    # Signal turns positive on day 10
    signal = pd.Series([0.0] * 10 + [3.0] * 10, index=dates)
    spread = pd.Series([100.0] * 20, index=dates)

    config = BacktestConfig(entry_threshold=2.0, signal_lag=1)
    result = run_backtest(signal, spread, config)

    # With 1-day lag, signal data is shifted, reducing available dates
    # After alignment, we should have 19 days (lost 1 to lag)
    assert len(result.positions) == 19

    # Check using date-based indexing to avoid off-by-one errors
    # Signal appears on 2024-01-10, with 1-day lag executes on 2024-01-11
    signal_date = pd.Timestamp("2024-01-10")
    execution_date = pd.Timestamp("2024-01-11")

    # No position before execution date
    early_positions = result.positions[result.positions.index < execution_date]
    assert (early_positions["position"] == 0).all()

    # Position should exist on or after execution date
    later_positions = result.positions[result.positions.index >= execution_date]
    assert (later_positions["position"] != 0).any()


def test_signal_lag_with_various_lags() -> None:
    """Test that different signal lag values produce expected data truncation."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    signal = pd.Series(np.random.randn(100), index=dates)
    spread = pd.Series(100 + np.random.randn(100), index=dates)

    # Test different lag values
    for lag in [0, 1, 2, 5]:
        config = BacktestConfig(signal_lag=lag)
        result = run_backtest(signal, spread, config)

        # Result length should be original length minus lag
        expected_length = 100 - lag
        assert len(result.positions) == expected_length
        assert len(result.pnl) == expected_length

        # First date should be lag days after original start
        expected_first_date = dates[lag]
        assert result.positions.index[0] == expected_first_date


def test_signal_lag_interaction_with_max_holding_days() -> None:
    """Test that signal_lag and max_holding_days work together correctly."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")

    # Strong signal for first 20 days
    signal = pd.Series([3.0] * 20 + [0.0] * 10, index=dates)
    spread = pd.Series([100.0] * 30, index=dates)

    config = BacktestConfig(
        entry_threshold=2.0,
        exit_threshold=0.5,
        max_holding_days=5,
        signal_lag=1,
    )
    result = run_backtest(signal, spread, config)

    # Find positions held
    in_position = result.positions[result.positions["position"] != 0]

    if len(in_position) > 0:
        # No position should exceed max_holding_days
        assert in_position["days_held"].max() <= config.max_holding_days

        # With lag, entry should be delayed
        first_position_date = in_position.index[0]
        assert first_position_date > dates[0]


def test_backtest_with_sparse_signals() -> None:
    """Test backtest behavior with infrequent signal triggers."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")

    # Signal crosses threshold only a few times
    signal = pd.Series([0.0] * 100, index=dates)
    signal.iloc[10] = 2.5  # Single spike
    signal.iloc[50] = -2.5  # Another spike
    signal.iloc[75] = 2.0  # Final spike

    spread = pd.Series(100 + np.random.randn(100) * 0.5, index=dates)

    config = BacktestConfig(
        entry_threshold=2.0,
        exit_threshold=0.5,
        signal_lag=0,  # No lag for precise testing
    )
    result = run_backtest(signal, spread, config)

    # Should have limited trading activity
    trades = (result.positions["position"].diff().fillna(0) != 0).sum()
    assert trades <= 6  # At most 3 entries and 3 exits


def test_backtest_with_rapid_signal_changes() -> None:
    """Test backtest with rapidly oscillating signals."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")

    # Alternating strong signals that cross zero
    signal_values = [2.5 if i % 2 == 0 else -2.5 for i in range(50)]
    signal = pd.Series(signal_values, index=dates)

    spread = pd.Series([100.0] * 50, index=dates)

    config = BacktestConfig(
        entry_threshold=2.0,
        exit_threshold=0.5,
        signal_lag=0,
    )
    result = run_backtest(signal, spread, config)

    # With alternating signals, should take positions
    # Entry threshold of 2.0 means signal of 2.5/-2.5 will trigger
    assert (result.positions["position"] != 0).any()

    # Verify transaction costs are incurred
    assert result.pnl["cost"].sum() > 0


def test_backtest_alignment_with_mismatched_dates() -> None:
    """Test that backtest correctly aligns signal and spread with different date ranges."""
    # Signal has more data
    signal_dates = pd.date_range("2024-01-01", periods=100, freq="D")
    # Spread has less data and different start
    spread_dates = pd.date_range("2024-01-10", periods=50, freq="D")

    signal = pd.Series(np.random.randn(100), index=signal_dates)
    spread = pd.Series(100 + np.random.randn(50), index=spread_dates)

    config = BacktestConfig(signal_lag=0)
    result = run_backtest(signal, spread, config)

    # Result should only include overlapping dates
    assert len(result.positions) == 50
    assert result.positions.index[0] == spread_dates[0]
    assert result.positions.index[-1] == spread_dates[-1]


def test_backtest_with_signal_lag_and_alignment() -> None:
    """Test interaction between signal lag and data alignment."""
    signal_dates = pd.date_range("2024-01-01", periods=100, freq="D")
    spread_dates = pd.date_range("2024-01-05", periods=90, freq="D")

    signal = pd.Series(np.random.randn(100), index=signal_dates)
    spread = pd.Series(100 + np.random.randn(90), index=spread_dates)

    # 2-day lag
    config = BacktestConfig(signal_lag=2)
    result = run_backtest(signal, spread, config)

    # After lag and alignment, check that we got valid data
    # Signal starts 2024-01-01, spread starts 2024-01-05
    # With 2-day lag, lagged signal starts 2024-01-03
    # Overlap is still full 90 days because signal extends well beyond spread
    assert len(result.positions) == 90

    # First date should match spread start (signal has enough coverage)
    assert result.positions.index[0] == spread_dates[0]

    # Verify signal_lag is reflected in metadata
    assert result.metadata["config"]["signal_lag"] == 2


def test_backtest_metadata_completeness() -> None:
    """Test that all metadata fields are populated correctly."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    signal = pd.Series(np.random.randn(50), index=dates)
    spread = pd.Series(100 + np.random.randn(50), index=dates)

    config = BacktestConfig(
        entry_threshold=1.8,
        exit_threshold=0.6,
        position_size=12.5,
        transaction_cost_bps=1.5,
        max_holding_days=10,
        dv01_per_million=5000.0,
        signal_lag=2,
    )
    result = run_backtest(signal, spread, config)

    # Verify all config parameters are in metadata
    assert result.metadata["config"]["entry_threshold"] == 1.8
    assert result.metadata["config"]["exit_threshold"] == 0.6
    assert result.metadata["config"]["position_size"] == 12.5
    assert result.metadata["config"]["transaction_cost_bps"] == 1.5
    assert result.metadata["config"]["max_holding_days"] == 10
    assert result.metadata["config"]["dv01_per_million"] == 5000.0
    assert result.metadata["config"]["signal_lag"] == 2

    # Verify summary statistics
    assert "timestamp" in result.metadata
    assert "start_date" in result.metadata["summary"]
    assert "end_date" in result.metadata["summary"]
    assert "total_days" in result.metadata["summary"]
    assert "n_trades" in result.metadata["summary"]
    assert "total_pnl" in result.metadata["summary"]
    assert "avg_pnl_per_trade" in result.metadata["summary"]

    # Verify timestamp is valid ISO format
    from datetime import datetime

    timestamp = datetime.fromisoformat(result.metadata["timestamp"])
    assert timestamp is not None


def test_backtest_determinism() -> None:
    """Test that backtest produces identical results for same inputs."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    np.random.seed(42)
    signal = pd.Series(np.random.randn(50), index=dates)
    spread = pd.Series(100 + np.random.randn(50), index=dates)

    config = BacktestConfig(entry_threshold=1.5)

    # Run twice
    result1 = run_backtest(signal, spread, config)
    result2 = run_backtest(signal, spread, config)

    # Results should be identical
    pd.testing.assert_frame_equal(result1.positions, result2.positions)
    pd.testing.assert_frame_equal(result1.pnl, result2.pnl)

    # Metadata timestamp will differ, but config and summary should match
    assert result1.metadata["config"] == result2.metadata["config"]
    assert result1.metadata["summary"] == result2.metadata["summary"]


def test_backtest_with_zero_threshold() -> None:
    """Test backtest with zero exit threshold (always in position)."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")

    # Signal oscillates around entry threshold
    signal = pd.Series(
        [2.0, 1.0, 0.5, 2.5, 1.5, 0.8] * 5,
        index=dates,
    )
    spread = pd.Series([100.0] * 30, index=dates)

    config = BacktestConfig(
        entry_threshold=1.5,
        exit_threshold=0.0,  # Never exit on signal decay
        signal_lag=0,
    )
    result = run_backtest(signal, spread, config)

    # Once entered, should stay in position (no signal-based exits)
    first_entry_idx = (result.positions["position"] != 0).idxmax()
    if first_entry_idx:
        positions_after_entry = result.positions.loc[first_entry_idx:]
        # Should maintain position (only changes if max_holding_days hits, which is None)
        assert (positions_after_entry["position"] != 0).all()
