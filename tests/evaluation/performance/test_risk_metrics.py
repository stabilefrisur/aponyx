"""Tests for extended risk metrics."""

import numpy as np
import pandas as pd
import pytest

from aponyx.evaluation.performance.risk_metrics import (
    compute_consistency_score,
    compute_drawdown_recovery_time,
    compute_extended_metrics,
    compute_profit_factor,
    compute_rolling_sharpe,
    compute_tail_ratio,
)


@pytest.fixture
def sample_pnl_series() -> pd.Series:
    """Generate sample P&L series for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=252, freq="D")
    pnl = pd.Series(np.random.normal(10, 50, 252), index=dates)
    return pnl


@pytest.fixture
def sample_pnl_df() -> pd.DataFrame:
    """Generate sample P&L DataFrame for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=252, freq="D")
    net_pnl = np.random.normal(10, 50, 252)
    cumulative_pnl = np.cumsum(net_pnl)

    return pd.DataFrame(
        {"net_pnl": net_pnl, "cumulative_pnl": cumulative_pnl}, index=dates
    )


class TestRollingSharpe:
    """Test rolling Sharpe ratio computation."""

    def test_rolling_sharpe_basic(self, sample_pnl_series: pd.Series) -> None:
        """Test basic rolling Sharpe computation."""
        rolling_sharpe = compute_rolling_sharpe(sample_pnl_series, window=63)

        assert len(rolling_sharpe) == len(sample_pnl_series)
        # Early values filled with 0, proper values start after window-1
        assert (rolling_sharpe[:62] == 0.0).all()
        assert rolling_sharpe[62:].notna().all()

    def test_rolling_sharpe_values(self) -> None:
        """Test rolling Sharpe with known values."""
        # Varying returns (positive trend)
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        pnl = pd.Series(np.random.normal(1.0, 0.5, 100), index=dates)

        rolling_sharpe = compute_rolling_sharpe(pnl, window=21)

        # Should be positive (positive mean, some volatility)
        assert rolling_sharpe.iloc[-1] > 0

    def test_rolling_sharpe_zero_std(self) -> None:
        """Test rolling Sharpe with zero std gives inf."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        pnl = pd.Series([5.0] * 100, index=dates)

        rolling_sharpe = compute_rolling_sharpe(pnl, window=21)

        # Zero std with positive mean gives inf
        assert np.isinf(rolling_sharpe.iloc[-1])


class TestDrawdownRecovery:
    """Test drawdown recovery metrics."""

    def test_drawdown_recovery_basic(self, sample_pnl_df: pd.DataFrame) -> None:
        """Test basic drawdown recovery computation."""
        recovery = compute_drawdown_recovery_time(sample_pnl_df["cumulative_pnl"])

        assert "max_dd_recovery_days" in recovery
        assert "avg_recovery_days" in recovery
        assert "n_drawdowns" in recovery

        assert recovery["n_drawdowns"] >= 0

    def test_drawdown_recovery_no_recovery(self) -> None:
        """Test max DD not recovered returns inf."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        # Monotonically declining
        cumulative_pnl = pd.Series(range(100, 0, -1), index=dates)

        recovery = compute_drawdown_recovery_time(cumulative_pnl)

        assert recovery["max_dd_recovery_days"] == np.inf

    def test_drawdown_recovery_immediate(self) -> None:
        """Test immediate recovery."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        # No drawdown
        cumulative_pnl = pd.Series(range(10), index=dates)

        recovery = compute_drawdown_recovery_time(cumulative_pnl)

        assert recovery["n_drawdowns"] == 0


class TestTailRatio:
    """Test tail ratio computation."""

    def test_tail_ratio_basic(self, sample_pnl_series: pd.Series) -> None:
        """Test basic tail ratio computation."""
        tail_ratio = compute_tail_ratio(sample_pnl_series)

        assert tail_ratio >= 0

    def test_tail_ratio_symmetric(self) -> None:
        """Test tail ratio with symmetric distribution."""
        np.random.seed(42)
        pnl = pd.Series(np.random.normal(0, 1, 1000))

        tail_ratio = compute_tail_ratio(pnl)

        # Should be close to 1 for symmetric distribution
        assert 0.8 < tail_ratio < 1.2

    def test_tail_ratio_insufficient_data(self) -> None:
        """Test tail ratio with insufficient data."""
        pnl = pd.Series([1, 2, 3])

        tail_ratio = compute_tail_ratio(pnl)

        assert tail_ratio == 0.0


class TestProfitFactor:
    """Test profit factor computation."""

    def test_profit_factor_basic(self, sample_pnl_series: pd.Series) -> None:
        """Test basic profit factor computation."""
        pf = compute_profit_factor(sample_pnl_series)

        assert pf >= 0

    def test_profit_factor_all_wins(self) -> None:
        """Test profit factor with all wins."""
        pnl = pd.Series([1, 2, 3, 4, 5])

        pf = compute_profit_factor(pnl)

        assert pf == np.inf

    def test_profit_factor_all_losses(self) -> None:
        """Test profit factor with all losses."""
        pnl = pd.Series([-1, -2, -3, -4, -5])

        pf = compute_profit_factor(pnl)

        assert pf == 0.0

    def test_profit_factor_known_value(self) -> None:
        """Test profit factor with known values."""
        pnl = pd.Series([10, 20, -5, -5])  # Gross profit=30, gross loss=10

        pf = compute_profit_factor(pnl)

        assert pf == 3.0


class TestConsistencyScore:
    """Test consistency score computation."""

    def test_consistency_score_basic(self, sample_pnl_series: pd.Series) -> None:
        """Test basic consistency score computation."""
        consistency = compute_consistency_score(sample_pnl_series, window=21)

        assert 0 <= consistency <= 1

    def test_consistency_score_always_positive(self) -> None:
        """Test consistency score with always positive returns."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        pnl = pd.Series([1.0] * 100, index=dates)

        consistency = compute_consistency_score(pnl, window=21)

        assert consistency == 1.0

    def test_consistency_score_always_negative(self) -> None:
        """Test consistency score with always negative returns."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        pnl = pd.Series([-1.0] * 100, index=dates)

        consistency = compute_consistency_score(pnl, window=21)

        assert consistency == 0.0


class TestExtendedMetrics:
    """Test comprehensive extended metrics computation."""

    def test_extended_metrics_basic(self, sample_pnl_df: pd.DataFrame) -> None:
        """Test basic extended metrics computation."""
        metrics = compute_extended_metrics(sample_pnl_df, rolling_window=63)

        # Check all expected keys present
        expected_keys = {
            "rolling_sharpe_mean",
            "rolling_sharpe_std",
            "max_dd_recovery_days",
            "avg_recovery_days",
            "n_drawdowns",
            "tail_ratio",
            "profit_factor",
            "consistency_score",
        }

        assert set(metrics.keys()) == expected_keys

        # Check value ranges
        assert -10 < metrics["rolling_sharpe_mean"] < 10
        assert metrics["rolling_sharpe_std"] >= 0
        assert metrics["n_drawdowns"] >= 0
        assert metrics["tail_ratio"] >= 0
        assert metrics["profit_factor"] >= 0
        assert 0 <= metrics["consistency_score"] <= 1
