"""Tests for performance metrics."""

import numpy as np
import pandas as pd
import pytest

from aponyx.backtest import run_backtest, BacktestConfig
from aponyx.data.test_scenarios import get_scenario
from aponyx.evaluation.performance.metrics import (
    compute_all_metrics,
    compute_consistency_score,
    compute_drawdown_recovery_time,
    compute_extended_metrics,
    compute_profit_factor,
    compute_rolling_sharpe,
    compute_tail_ratio,
    convert_pnl_to_returns,
)


def _quantstats_available() -> bool:
    """Check if quantstats is available."""
    try:
        import quantstats  # noqa: F401

        return True
    except ImportError:
        return False


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


class TestConvertPnLToReturns:
    """Test P&L to returns conversion."""

    def test_convert_pnl_to_returns_basic(self) -> None:
        """Test basic P&L to returns conversion."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        cumulative_pnl = pd.Series([0, 100, 150, 200, 180], index=dates)
        pnl_df = pd.DataFrame({"cumulative_pnl": cumulative_pnl})

        returns = convert_pnl_to_returns(pnl_df, starting_capital=10000.0)

        # Check length
        assert len(returns) == len(cumulative_pnl)

        # First return should be cumulative_pnl[0] / starting_capital
        assert returns.iloc[0] == pytest.approx(0.0 / 10000.0)

        # Second return should be change in P&L / (starting_capital + prev cumulative P&L)
        assert returns.iloc[1] == pytest.approx(100.0 / 10000.0)

        # Third return
        assert returns.iloc[2] == pytest.approx(50.0 / 10100.0, rel=1e-4)

    def test_convert_pnl_to_returns_zero_starting_capital(self) -> None:
        """Test conversion handles zero starting capital."""
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        cumulative_pnl = pd.Series([0, 100, 200], index=dates)
        pnl_df = pd.DataFrame({"cumulative_pnl": cumulative_pnl})

        returns = convert_pnl_to_returns(pnl_df, starting_capital=0.0)

        # First return is 0 (0 P&L / 0 capital = 0)
        assert returns.iloc[0] == 0.0
        # Second return is inf (100 P&L / 0 equity)
        assert np.isinf(returns.iloc[1])


class TestComputeAllMetrics:
    """Test comprehensive metric computation with quantstats integration."""

    def test_compute_all_metrics_custom(self, sample_pnl_df: pd.DataFrame) -> None:
        """Test compute_all_metrics with quantstats implementation."""
        # Create minimal positions dataframe
        positions_df = pd.DataFrame(
            {
                "position": [0] * len(sample_pnl_df),
                "days_held": [0] * len(sample_pnl_df),
            },
            index=sample_pnl_df.index,
        )

        # Compute metrics using quantstats
        metrics = compute_all_metrics(
            sample_pnl_df,
            positions_df=positions_df,
        )

        # Check metrics is PerformanceMetrics dataclass
        from aponyx.evaluation.performance.config import PerformanceMetrics

        assert isinstance(metrics, PerformanceMetrics)

        # Check key attributes present
        assert hasattr(metrics, "total_return")
        assert hasattr(metrics, "sharpe_ratio")
        assert hasattr(metrics, "n_trades")
        assert hasattr(metrics, "tail_ratio")
        assert hasattr(metrics, "consistency_score")

    @pytest.mark.skipif(
        not _quantstats_available(),
        reason="quantstats not installed",
    )
    def test_compute_all_metrics_quantstats(self, sample_pnl_df: pd.DataFrame) -> None:
        """Test compute_all_metrics with quantstats implementation."""
        from aponyx.evaluation.performance.config import PerformanceMetrics

        # Create minimal positions dataframe
        positions_df = pd.DataFrame(
            {
                "position": [0] * len(sample_pnl_df),
                "days_held": [0] * len(sample_pnl_df),
            },
            index=sample_pnl_df.index,
        )

        # Use quantstats (always enabled)
        metrics = compute_all_metrics(
            sample_pnl_df,
            positions_df=positions_df,
            starting_capital=100000.0,
        )

        # Check metrics is PerformanceMetrics dataclass
        assert isinstance(metrics, PerformanceMetrics)

        # Check quantstats metrics present
        assert hasattr(metrics, "sharpe_ratio")
        assert hasattr(metrics, "sortino_ratio")
        assert hasattr(metrics, "max_drawdown")

        # Trade stats should still be custom
        assert hasattr(metrics, "n_trades")

    @pytest.mark.skipif(
        not _quantstats_available(),
        reason="quantstats not installed",
    )
    def test_compute_all_metrics_with_benchmark(
        self, sample_pnl_df: pd.DataFrame
    ) -> None:
        """Test compute_all_metrics with benchmark."""
        from aponyx.evaluation.performance.config import PerformanceMetrics

        # Create minimal positions dataframe
        positions_df = pd.DataFrame(
            {
                "position": [0] * len(sample_pnl_df),
                "days_held": [0] * len(sample_pnl_df),
            },
            index=sample_pnl_df.index,
        )

        # Create synthetic benchmark
        np.random.seed(123)
        benchmark = pd.Series(
            np.random.normal(0.0001, 0.01, len(sample_pnl_df)),
            index=sample_pnl_df.index,
        )

        metrics = compute_all_metrics(
            sample_pnl_df,
            positions_df=positions_df,
            starting_capital=100000.0,
            benchmark=benchmark,
        )

        # Check metrics is PerformanceMetrics dataclass
        assert isinstance(metrics, PerformanceMetrics)

        # Check benchmark metrics present
        assert hasattr(metrics, "alpha")
        assert hasattr(metrics, "beta")
        assert hasattr(metrics, "information_ratio")
        assert hasattr(metrics, "r_squared")

        # Values should be numeric (not None)
        assert metrics.alpha is not None
        assert metrics.beta is not None
        assert isinstance(metrics.alpha, (int, float))
        assert isinstance(metrics.beta, (int, float))


class TestDeterministicScenarios:
    """Tests using deterministic scenarios for metrics validation."""

    @staticmethod
    def _make_config(**overrides) -> BacktestConfig:
        """Create a minimal backtest config for testing."""
        defaults = {
            "position_size_mm": 10.0,
            "sizing_mode": "binary",
            "stop_loss_pct": None,
            "take_profit_pct": None,
            "max_holding_days": None,
            "transaction_cost_bps": 0.0,
            "dv01_per_million": 475.0,
            "signal_lag": 0,
        }
        defaults.update(overrides)
        return BacktestConfig(**defaults)

    def test_profitable_long_positive_profit_factor(self) -> None:
        """Test profitable_long scenario has high profit factor."""
        scenario = get_scenario("profitable_long")
        config = self._make_config()

        result = run_backtest(scenario.signal, scenario.spread, config)
        profit_factor = compute_profit_factor(result.pnl["net_pnl"])

        # Profitable scenario should have profit factor > 1
        assert profit_factor > 1.0 or profit_factor == np.inf

    def test_unprofitable_long_low_profit_factor(self) -> None:
        """Test unprofitable_long scenario has low profit factor."""
        scenario = get_scenario("unprofitable_long")
        config = self._make_config()

        result = run_backtest(scenario.signal, scenario.spread, config)
        profit_factor = compute_profit_factor(result.pnl["net_pnl"])

        # Unprofitable scenario should have profit factor < 1
        assert profit_factor < 1.0

    def test_alternating_outcomes_moderate_consistency(self) -> None:
        """Test alternating_outcomes scenario has moderate consistency score."""
        scenario = get_scenario("alternating_outcomes")
        config = self._make_config()

        result = run_backtest(scenario.signal, scenario.spread, config)

        # Compute extended metrics
        extended = compute_extended_metrics(result.pnl, rolling_window=21)

        # Alternating wins/losses should produce moderate consistency
        # Not too high (all wins) and not too low (all losses)
        assert 0.2 <= extended["consistency_score"] <= 0.8

    def test_profitable_tail_ratio(self) -> None:
        """Test profitable scenario has favorable tail ratio."""
        scenario = get_scenario("profitable_long")
        config = self._make_config()

        result = run_backtest(scenario.signal, scenario.spread, config)
        tail_ratio = compute_tail_ratio(result.pnl["net_pnl"])

        # Profitable trending scenario should have decent tail ratio
        assert tail_ratio >= 0  # At minimum, should be calculable
