"""Tests for performance analyzer orchestration."""

import numpy as np
import pandas as pd
import pytest

from aponyx.backtest import BacktestResult
from aponyx.evaluation.performance import PerformanceConfig, analyze_backtest_performance


@pytest.fixture
def sample_backtest_result() -> BacktestResult:
    """Generate sample backtest result for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=300, freq="D")

    # Create positions
    signal = np.random.normal(0, 1, 300)
    position = np.where(signal > 0.5, 1, np.where(signal < -0.5, -1, 0))
    days_held = np.arange(300) % 10
    spread = 100 + np.random.normal(0, 5, 300)

    positions_df = pd.DataFrame(
        {
            "signal": signal,
            "position": position,
            "days_held": days_held,
            "spread": spread,
        },
        index=dates,
    )

    # Create P&L
    spread_pnl = position * np.random.normal(50, 100, 300)
    cost = np.where(np.diff(position, prepend=0) != 0, -5, 0)
    net_pnl = spread_pnl + cost
    cumulative_pnl = np.cumsum(net_pnl)

    pnl_df = pd.DataFrame(
        {
            "spread_pnl": spread_pnl,
            "cost": cost,
            "net_pnl": net_pnl,
            "cumulative_pnl": cumulative_pnl,
        },
        index=dates,
    )

    metadata = {
        "signal_id": "test_signal",
        "strategy_id": "test_strategy",
        "config": {
            "entry_threshold": 0.5,
            "exit_threshold": 0.1,
        },
    }

    return BacktestResult(positions=positions_df, pnl=pnl_df, metadata=metadata)


class TestAnalyzeBacktestPerformance:
    """Test main performance analyzer function."""

    def test_analyze_basic(self, sample_backtest_result: BacktestResult) -> None:
        """Test basic performance analysis."""
        result = analyze_backtest_performance(sample_backtest_result)

        assert result.metrics is not None
        assert result.subperiod_analysis is not None
        assert result.attribution is not None
        assert 0 <= result.stability_score <= 1
        assert result.summary != ""
        assert result.timestamp != ""

    def test_analyze_with_custom_config(
        self, sample_backtest_result: BacktestResult
    ) -> None:
        """Test analysis with custom configuration."""
        config = PerformanceConfig(
            min_obs=200, n_subperiods=6, rolling_window=30, attribution_quantiles=5
        )

        result = analyze_backtest_performance(sample_backtest_result, config)

        assert len(result.subperiod_analysis["subperiod_returns"]) == 6
        assert result.config.n_subperiods == 6
        assert result.config.rolling_window == 30

    def test_analyze_insufficient_data_raises(self) -> None:
        """Test that insufficient data raises ValueError."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")

        positions_df = pd.DataFrame(
            {"signal": [0] * 100, "position": [0] * 100}, index=dates
        )
        pnl_df = pd.DataFrame(
            {"net_pnl": [0] * 100, "cumulative_pnl": [0] * 100}, index=dates
        )

        result = BacktestResult(positions=positions_df, pnl=pnl_df, metadata={})

        with pytest.raises(ValueError, match="Insufficient observations"):
            analyze_backtest_performance(result)

    def test_analyze_invalid_index_raises(self) -> None:
        """Test that non-DatetimeIndex raises ValueError."""
        positions_df = pd.DataFrame({"signal": [0] * 300, "position": [0] * 300})
        pnl_df = pd.DataFrame({"net_pnl": [0] * 300, "cumulative_pnl": [0] * 300})

        result = BacktestResult(positions=positions_df, pnl=pnl_df, metadata={})

        with pytest.raises(ValueError, match="must have DatetimeIndex"):
            analyze_backtest_performance(result)

    def test_analyze_missing_columns_raises(
        self, sample_backtest_result: BacktestResult
    ) -> None:
        """Test that missing required columns raises ValueError."""
        # Remove required column
        sample_backtest_result.pnl = sample_backtest_result.pnl.drop(
            columns=["net_pnl"]
        )

        with pytest.raises(ValueError, match="missing required columns"):
            analyze_backtest_performance(sample_backtest_result)

    def test_analyze_metadata_propagation(
        self, sample_backtest_result: BacktestResult
    ) -> None:
        """Test that metadata is properly propagated."""
        result = analyze_backtest_performance(sample_backtest_result)

        assert result.metadata["signal_id"] == "test_signal"
        assert result.metadata["strategy_id"] == "test_strategy"
        assert "evaluator_version" in result.metadata
        assert "backtest_config" in result.metadata
