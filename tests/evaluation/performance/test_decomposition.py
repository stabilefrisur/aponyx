"""Tests for return attribution and decomposition."""

import numpy as np
import pandas as pd
import pytest

from aponyx.evaluation.performance.decomposition import (
    attribute_by_direction,
    attribute_by_signal_strength,
    attribute_by_win_loss,
    compute_attribution,
)


@pytest.fixture
def sample_backtest_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate sample backtest data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=100, freq="D")

    # Create positions with signal
    signal = np.random.normal(0, 2, 100)
    position = np.where(signal > 0.5, 1, np.where(signal < -0.5, -1, 0))

    positions_df = pd.DataFrame({"signal": signal, "position": position}, index=dates)

    # Create P&L aligned with positions
    net_pnl = position * np.random.normal(5, 10, 100)

    pnl_df = pd.DataFrame({"net_pnl": net_pnl}, index=dates)

    return pnl_df, positions_df


class TestDirectionalAttribution:
    """Test directional attribution."""

    def test_attribute_by_direction_basic(
        self, sample_backtest_data: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        """Test basic directional attribution."""
        pnl_df, positions_df = sample_backtest_data

        attr = attribute_by_direction(pnl_df, positions_df)

        assert "long_pnl" in attr
        assert "short_pnl" in attr
        assert "long_pct" in attr
        assert "short_pct" in attr

        # Percentages should sum to ~1.0
        assert abs(attr["long_pct"] + attr["short_pct"] - 1.0) < 0.01

    def test_attribute_by_direction_all_long(self) -> None:
        """Test attribution with only long positions."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")

        pnl_df = pd.DataFrame({"net_pnl": [10] * 10}, index=dates)
        positions_df = pd.DataFrame({"position": [1] * 10}, index=dates)

        attr = attribute_by_direction(pnl_df, positions_df)

        assert attr["long_pct"] == 1.0
        assert attr["short_pct"] == 0.0
        assert attr["long_pnl"] == 100

    def test_attribute_by_direction_zero_pnl(self) -> None:
        """Test attribution with zero total P&L."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")

        pnl_df = pd.DataFrame({"net_pnl": [0] * 10}, index=dates)
        positions_df = pd.DataFrame({"position": [1, -1] * 5}, index=dates)

        attr = attribute_by_direction(pnl_df, positions_df)

        assert attr["long_pct"] == 0.0
        assert attr["short_pct"] == 0.0


class TestSignalStrengthAttribution:
    """Test signal strength attribution."""

    def test_attribute_by_signal_strength_basic(
        self, sample_backtest_data: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        """Test basic signal strength attribution."""
        pnl_df, positions_df = sample_backtest_data

        attr = attribute_by_signal_strength(pnl_df, positions_df, n_quantiles=3)

        assert "q1_pnl" in attr
        assert "q2_pnl" in attr
        assert "q3_pnl" in attr
        assert "q1_pct" in attr
        assert "q2_pct" in attr
        assert "q3_pct" in attr
        assert "quantile_labels" in attr

        # Percentages should sum to ~1.0
        total_pct = attr["q1_pct"] + attr["q2_pct"] + attr["q3_pct"]
        assert abs(total_pct - 1.0) < 0.01

    def test_attribute_by_signal_strength_no_positions(self) -> None:
        """Test signal strength attribution with no positions."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")

        pnl_df = pd.DataFrame({"net_pnl": [0] * 10}, index=dates)
        positions_df = pd.DataFrame({"signal": [1.0] * 10, "position": [0] * 10}, index=dates)

        attr = attribute_by_signal_strength(pnl_df, positions_df, n_quantiles=3)

        # Should handle gracefully
        assert all(attr[f"q{i}_pnl"] == 0.0 for i in range(1, 4))

    def test_attribute_by_signal_strength_quantiles(
        self, sample_backtest_data: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        """Test signal strength attribution with different quantiles."""
        pnl_df, positions_df = sample_backtest_data

        # Test with 5 quantiles
        attr = attribute_by_signal_strength(pnl_df, positions_df, n_quantiles=5)

        assert "q5_pnl" in attr
        assert len(attr["quantile_labels"]) == 5


class TestWinLossAttribution:
    """Test win/loss attribution."""

    def test_attribute_by_win_loss_basic(
        self, sample_backtest_data: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        """Test basic win/loss attribution."""
        pnl_df, positions_df = sample_backtest_data

        attr = attribute_by_win_loss(pnl_df, positions_df)

        assert "gross_wins" in attr
        assert "gross_losses" in attr
        assert "net_pnl" in attr
        assert "win_contribution" in attr
        assert "loss_contribution" in attr

        assert attr["gross_wins"] >= 0
        assert attr["gross_losses"] <= 0

    def test_attribute_by_win_loss_all_wins(self) -> None:
        """Test win/loss attribution with all wins."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")

        pnl_df = pd.DataFrame({"net_pnl": [10] * 10}, index=dates)
        positions_df = pd.DataFrame({"position": [1] * 10}, index=dates)

        attr = attribute_by_win_loss(pnl_df, positions_df)

        assert attr["gross_wins"] == 100
        assert attr["gross_losses"] == 0
        assert attr["win_contribution"] == 1.0
        assert attr["loss_contribution"] == 0.0

    def test_attribute_by_win_loss_balanced(self) -> None:
        """Test win/loss attribution with balanced wins/losses."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")

        pnl_df = pd.DataFrame({"net_pnl": [10, -10] * 5}, index=dates)
        positions_df = pd.DataFrame({"position": [1] * 10}, index=dates)

        attr = attribute_by_win_loss(pnl_df, positions_df)

        assert attr["gross_wins"] == 50
        assert attr["gross_losses"] == -50
        assert attr["net_pnl"] == 0


class TestComputeAttribution:
    """Test comprehensive attribution orchestration."""

    def test_compute_attribution_basic(
        self, sample_backtest_data: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        """Test basic attribution computation."""
        pnl_df, positions_df = sample_backtest_data

        attribution = compute_attribution(pnl_df, positions_df, n_quantiles=3)

        assert "direction" in attribution
        assert "signal_strength" in attribution
        assert "win_loss" in attribution

        # Check nested structure
        assert "long_pnl" in attribution["direction"]
        assert "q1_pnl" in attribution["signal_strength"]
        assert "gross_wins" in attribution["win_loss"]

    def test_compute_attribution_quantiles(
        self, sample_backtest_data: tuple[pd.DataFrame, pd.DataFrame]
    ) -> None:
        """Test attribution with different quantiles."""
        pnl_df, positions_df = sample_backtest_data

        attribution = compute_attribution(pnl_df, positions_df, n_quantiles=5)

        # Should have 5 quantiles
        assert "q5_pnl" in attribution["signal_strength"]
        assert len(attribution["signal_strength"]["quantile_labels"]) == 5
