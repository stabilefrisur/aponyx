"""Tests for performance report generation."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aponyx.evaluation.performance import (
    PerformanceConfig,
    PerformanceMetrics,
    PerformanceResult,
    generate_performance_report,
    save_report,
)
from aponyx.evaluation.performance.report import generate_quantstats_tearsheet


def _quantstats_available() -> bool:
    """Check if quantstats is available."""
    try:
        import quantstats  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture
def sample_performance_result() -> PerformanceResult:
    """Generate sample performance result for testing."""
    metrics = PerformanceMetrics(
        total_return=4000.0,
        annualized_return=2000.0,
        sharpe_ratio=1.5,
        sortino_ratio=1.8,
        calmar_ratio=2.0,
        max_drawdown=-1000.0,
        annualized_volatility=800.0,
        n_trades=100,
        hit_rate=0.65,
        avg_win=80.0,
        avg_loss=-40.0,
        win_loss_ratio=2.0,
        avg_holding_days=5.0,
        rolling_sharpe_mean=1.5,
        rolling_sharpe_std=0.3,
        max_dd_recovery_days=45.0,
        avg_recovery_days=20.0,
        n_drawdowns=5,
        tail_ratio=1.2,
        profit_factor=1.8,
        consistency_score=0.65,
    )
    return PerformanceResult(
        metrics=metrics,
        subperiod_analysis={
            "subperiod_returns": [1000, 1500, -500, 2000],
            "subperiod_sharpes": [1.2, 1.5, -0.5, 2.0],
            "positive_periods": 3,
            "consistency_rate": 0.75,
        },
        attribution={
            "direction": {"long_pnl": 3000, "short_pnl": 1000, "long_pct": 0.75, "short_pct": 0.25},
            "signal_strength": {
                "q1_pnl": 500,
                "q2_pnl": 1500,
                "q3_pnl": 2000,
                "q1_pct": 0.125,
                "q2_pct": 0.375,
                "q3_pct": 0.5,
                "quantile_labels": ["Q1", "Q2", "Q3"],
            },
            "win_loss": {
                "gross_wins": 5000,
                "gross_losses": -1000,
                "net_pnl": 4000,
                "win_contribution": 0.8,
                "loss_contribution": 0.2,
            },
        },
        stability_score=0.75,
        summary="Strong performance with good stability",
        timestamp="2024-01-01T12:00:00",
        config=PerformanceConfig(),
        metadata={"evaluator_version": "0.1.0"},
    )


class TestGeneratePerformanceReport:
    """Test performance report generation."""

    def test_generate_report_basic(self, sample_performance_result: PerformanceResult) -> None:
        """Test basic report generation."""
        report = generate_performance_report(
            sample_performance_result, "test_signal", "test_strategy"
        )

        assert isinstance(report, str)
        assert len(report) > 100

        # Check key sections
        assert "# Backtest Performance Evaluation Report" in report
        assert "test_signal" in report
        assert "test_strategy" in report
        assert "Executive Summary" in report
        assert "Extended Performance Metrics" in report
        assert "Subperiod Stability Analysis" in report
        assert "Return Attribution" in report

    def test_generate_report_contains_metrics(
        self, sample_performance_result: PerformanceResult
    ) -> None:
        """Test that report contains metric values."""
        report = generate_performance_report(
            sample_performance_result, "test_signal", "test_strategy"
        )

        # Check metric values appear
        assert "1.500" in report  # Sharpe
        assert "1.800" in report  # Profit factor
        assert "1.200" in report  # Tail ratio
        assert "0.750" in report  # Stability score

    def test_generate_report_stability_indicators(self) -> None:
        """Test stability indicators in report."""
        # Create metrics with PerformanceMetrics dataclass
        metrics = PerformanceMetrics(
            total_return=280.0,
            annualized_return=140.0,
            sharpe_ratio=1.2,
            sortino_ratio=1.5,
            calmar_ratio=1.4,
            max_drawdown=-100.0,
            annualized_volatility=50.0,
            n_trades=50,
            hit_rate=0.75,
            avg_win=10.0,
            avg_loss=-5.0,
            win_loss_ratio=2.0,
            avg_holding_days=3.0,
            rolling_sharpe_mean=1.2,
            rolling_sharpe_std=0.3,
            profit_factor=1.8,
            tail_ratio=1.5,
            consistency_score=0.65,
            max_dd_recovery_days=30.0,
            avg_recovery_days=15.0,
            n_drawdowns=5,
        )

        # Create subperiod_analysis dict (matching _compute_subperiod_metrics output)
        subperiod_analysis = {
            "subperiod_returns": [100.0, -50.0, 150.0, 80.0],
            "subperiod_sharpes": [1.5, -0.8, 2.1, 1.2],
            "positive_periods": 3,
            "consistency_rate": 0.75,
        }

        # Create attribution dict (matching compute_attribution output)
        attribution = {
            "direction": {
                "long_pnl": 200.0,
                "short_pnl": 80.0,
                "long_pct": 0.71,
                "short_pct": 0.29,
            },
            "signal_strength": {
                "q1_pnl": 50.0,
                "q1_pct": 0.18,
                "q2_pnl": 80.0,
                "q2_pct": 0.29,
                "q3_pnl": 150.0,
                "q3_pct": 0.54,
                "quantile_labels": ["Q1", "Q2", "Q3"],
            },
            "win_loss": {
                "gross_wins": 400.0,
                "gross_losses": -120.0,
                "net_pnl": 280.0,
                "win_contribution": 0.77,
                "loss_contribution": 0.23,
            },
        }

        # High stability
        result_high = PerformanceResult(
            metrics=metrics,
            subperiod_analysis=subperiod_analysis,
            attribution=attribution,
            stability_score=0.8,
            summary="Test",
            timestamp="2024-01-01",
            config=PerformanceConfig(),
            metadata={},
        )

        report = generate_performance_report(result_high, "sig", "strat")
        assert "✅ Strong" in report

        # Moderate stability
        result_mod = PerformanceResult(
            metrics=metrics,
            subperiod_analysis=subperiod_analysis,
            attribution=attribution,
            stability_score=0.6,
            summary="Test",
            timestamp="2024-01-01",
            config=PerformanceConfig(),
            metadata={},
        )

        report = generate_performance_report(result_mod, "sig", "strat")
        assert "⚠️ Moderate" in report

        # Weak stability
        result_weak = PerformanceResult(
            metrics=metrics,
            subperiod_analysis=subperiod_analysis,
            attribution=attribution,
            stability_score=0.3,
            summary="Test",
            timestamp="2024-01-01",
            config=PerformanceConfig(),
            metadata={},
        )

        report = generate_performance_report(result_weak, "sig", "strat")
        assert "❌ Weak" in report


class TestSaveReport:
    """Test report file saving."""

    def test_save_report_basic(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test basic report saving."""
        report = generate_performance_report(
            sample_performance_result, "test_signal", "test_strategy"
        )

        output_path = save_report(report, "test_signal", "test_strategy", tmp_path)

        assert output_path.exists()
        assert output_path.suffix == ".md"
        assert "test_signal" in output_path.name
        assert "test_strategy" in output_path.name

    def test_save_report_creates_directory(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test that save_report creates directory if needed."""
        output_dir = tmp_path / "nested" / "reports"

        report = generate_performance_report(
            sample_performance_result, "test_signal", "test_strategy"
        )

        output_path = save_report(report, "test_signal", "test_strategy", output_dir)

        assert output_dir.exists()
        assert output_path.exists()

    def test_save_report_content_matches(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test that saved content matches generated report."""
        report = generate_performance_report(
            sample_performance_result, "test_signal", "test_strategy"
        )

        output_path = save_report(report, "test_signal", "test_strategy", tmp_path)

        saved_content = output_path.read_text(encoding="utf-8")

        assert saved_content == report


class TestQuantstatsTearsheet:
    """Test quantstats tearsheet generation."""

    @pytest.mark.skipif(
        not _quantstats_available(),
        reason="quantstats not installed",
    )
    def test_generate_tearsheet_basic(self, tmp_path: Path) -> None:
        """Test basic tearsheet generation."""
        # Create synthetic returns
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)

        output_path = tmp_path / "test_tearsheet.html"

        result = generate_quantstats_tearsheet(
            returns=returns,
            benchmark=None,
            output_path=output_path,
            title="Test Strategy",
        )

        assert result == output_path
        assert output_path.exists()
        assert output_path.suffix == ".html"

    @pytest.mark.skipif(
        not _quantstats_available(),
        reason="quantstats not installed",
    )
    def test_generate_tearsheet_with_benchmark(self, tmp_path: Path) -> None:
        """Test tearsheet generation with benchmark."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)
        benchmark = pd.Series(np.random.normal(0.0005, 0.015, 252), index=dates)

        output_path = tmp_path / "test_tearsheet_benchmark.html"

        result = generate_quantstats_tearsheet(
            returns=returns,
            benchmark=benchmark,
            output_path=output_path,
            title="Test Strategy vs Benchmark",
        )

        assert result == output_path
        assert output_path.exists()

    def test_generate_tearsheet_error_handling(self, tmp_path: Path) -> None:
        """Test tearsheet generation error handling."""
        # Test with invalid returns to trigger error
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        returns = pd.Series([np.nan] * 5, index=dates)  # All NaN will cause issues

        output_path = tmp_path / "test_tearsheet.html"

        result = generate_quantstats_tearsheet(
            returns=returns,
            benchmark=None,
            output_path=output_path,
            title="Test Strategy",
        )

        # Should return None on error
        assert result is None

    def test_generate_report_with_tearsheet_enabled(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test report generation with tearsheet enabled."""
        # Add returns to metadata
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)
        sample_performance_result.metadata["returns"] = returns

        report = generate_performance_report(
            sample_performance_result,
            "test_signal",
            "test_strategy",
            generate_tearsheet=True,
            output_dir=tmp_path,
        )

        assert isinstance(report, str)

        # Check if tearsheet was created (only if quantstats available)
        if _quantstats_available():
            tearsheet_files = list(tmp_path.glob("*_tearsheet.html"))
            assert len(tearsheet_files) == 1
            assert "test_signal" in tearsheet_files[0].name
            assert "test_strategy" in tearsheet_files[0].name

    def test_generate_report_with_tearsheet_disabled(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test report generation with tearsheet disabled."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="D")
        returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)
        sample_performance_result.metadata["returns"] = returns

        report = generate_performance_report(
            sample_performance_result,
            "test_signal",
            "test_strategy",
            generate_tearsheet=False,
            output_dir=tmp_path,
        )

        assert isinstance(report, str)

        # No tearsheet should be created
        tearsheet_files = list(tmp_path.glob("*_tearsheet.html"))
        assert len(tearsheet_files) == 0


