"""Tests for sweep report generation."""

from pathlib import Path

import pandas as pd
import pytest

from aponyx.sweep.config import BaseConfig, ParameterOverride, SweepConfig
from aponyx.sweep.reports import (
    generate_sweep_report,
    save_sweep_report,
)
from aponyx.sweep.results import SweepResult, SweepSummary


@pytest.fixture
def indicator_sweep_result(tmp_path: Path) -> SweepResult:
    """Create a sample indicator sweep result for testing."""
    config = SweepConfig(
        name="test_indicator_sweep",
        description="Test indicator sweep description",
        mode="indicator",
        base=BaseConfig(signal="test_signal"),
        parameters=(
            ParameterOverride(
                path="indicator_transformation.parameters.lookback",
                values=(10, 20, 40),
            ),
            ParameterOverride(
                path="score_transformation.parameters.window",
                values=(20, 40),
            ),
        ),
    )

    results_df = pd.DataFrame(
        [
            {
                "combination_id": 0,
                "indicator_transformation.parameters.lookback": 10,
                "score_transformation.parameters.window": 20,
                "composite_score": 0.85,
                "data_health_score": 0.90,
                "predictive_score": 0.80,
                "economic_score": 0.75,
                "stability_score": 0.95,
                "effect_size_bps": 3.5,
                "sign_consistency_ratio": 0.8,
                "status": "success",
                "error": None,
            },
            {
                "combination_id": 1,
                "indicator_transformation.parameters.lookback": 10,
                "score_transformation.parameters.window": 40,
                "composite_score": 0.82,
                "data_health_score": 0.88,
                "predictive_score": 0.78,
                "economic_score": 0.72,
                "stability_score": 0.92,
                "effect_size_bps": 3.2,
                "sign_consistency_ratio": 0.75,
                "status": "success",
                "error": None,
            },
            {
                "combination_id": 2,
                "indicator_transformation.parameters.lookback": 20,
                "score_transformation.parameters.window": 20,
                "composite_score": 0.88,
                "data_health_score": 0.92,
                "predictive_score": 0.85,
                "economic_score": 0.80,
                "stability_score": 0.96,
                "effect_size_bps": 4.0,
                "sign_consistency_ratio": 0.85,
                "status": "success",
                "error": None,
            },
        ]
    )

    summary = SweepSummary(
        start_time="2025-12-20T10:00:00",
        end_time="2025-12-20T10:01:00",
        duration_seconds=60.0,
        total_combinations=3,
        successful=3,
        failed=0,
        mode="indicator",
    )

    return SweepResult(
        config=config,
        results_df=results_df,
        summary=summary,
        output_dir=tmp_path,
    )


@pytest.fixture
def backtest_sweep_result(tmp_path: Path) -> SweepResult:
    """Create a sample backtest sweep result for testing."""
    config = SweepConfig(
        name="test_backtest_sweep",
        description="Test backtest sweep description",
        mode="backtest",
        base=BaseConfig(signal="test_signal", strategy="test_strategy"),
        parameters=(
            ParameterOverride(
                path="strategy.position_size_mm",
                values=(5.0, 10.0),
            ),
            ParameterOverride(
                path="signal_transformation.parameters.floor",
                values=(-1.0, -2.0),
            ),
        ),
    )

    results_df = pd.DataFrame(
        [
            {
                "combination_id": 0,
                "strategy.position_size_mm": 5.0,
                "signal_transformation.parameters.floor": -1.0,
                "sharpe_ratio": 1.2,
                "sortino_ratio": 1.8,
                "calmar_ratio": 0.9,
                "total_return": 0.15,
                "annualized_return": 0.10,
                "max_drawdown": -0.12,
                "annualized_volatility": 0.08,
                "hit_rate": 0.55,
                "profit_factor": 1.4,
                "n_trades": 50,
                "status": "success",
                "error": None,
            },
            {
                "combination_id": 1,
                "strategy.position_size_mm": 5.0,
                "signal_transformation.parameters.floor": -2.0,
                "sharpe_ratio": 1.1,
                "sortino_ratio": 1.6,
                "calmar_ratio": 0.85,
                "total_return": 0.12,
                "annualized_return": 0.08,
                "max_drawdown": -0.10,
                "annualized_volatility": 0.07,
                "hit_rate": 0.52,
                "profit_factor": 1.3,
                "n_trades": 45,
                "status": "success",
                "error": None,
            },
            {
                "combination_id": 2,
                "strategy.position_size_mm": 10.0,
                "signal_transformation.parameters.floor": -1.0,
                "sharpe_ratio": 1.35,
                "sortino_ratio": 2.0,
                "calmar_ratio": 1.0,
                "total_return": 0.20,
                "annualized_return": 0.14,
                "max_drawdown": -0.14,
                "annualized_volatility": 0.10,
                "hit_rate": 0.58,
                "profit_factor": 1.5,
                "n_trades": 55,
                "status": "success",
                "error": None,
            },
        ]
    )

    summary = SweepSummary(
        start_time="2025-12-20T10:00:00",
        end_time="2025-12-20T10:02:00",
        duration_seconds=120.0,
        total_combinations=3,
        successful=3,
        failed=0,
        mode="backtest",
    )

    return SweepResult(
        config=config,
        results_df=results_df,
        summary=summary,
        output_dir=tmp_path,
    )


class TestGenerateSweepReport:
    """Tests for generate_sweep_report function."""

    def test_indicator_report_header(
        self, indicator_sweep_result: SweepResult
    ) -> None:
        """Report includes name, description, mode, and signal."""
        report = generate_sweep_report(indicator_sweep_result)

        assert "# Sweep Analysis Report: test_indicator_sweep" in report
        assert "Test indicator sweep description" in report
        assert "**Mode:** indicator" in report
        assert "**Signal:** `test_signal`" in report

    def test_backtest_report_includes_strategy(
        self, backtest_sweep_result: SweepResult
    ) -> None:
        """Backtest report includes strategy name."""
        report = generate_sweep_report(backtest_sweep_result)

        assert "**Strategy:** `test_strategy`" in report

    def test_swept_parameters_section(
        self, indicator_sweep_result: SweepResult
    ) -> None:
        """Report includes swept parameters table."""
        report = generate_sweep_report(indicator_sweep_result)

        assert "## Swept Parameters" in report
        assert "`indicator_transformation.lookback`" in report
        assert "`score_transformation.window`" in report
        assert "10, 20, 40" in report
        assert "20, 40" in report

    def test_execution_summary_section(
        self, indicator_sweep_result: SweepResult
    ) -> None:
        """Report includes execution summary."""
        report = generate_sweep_report(indicator_sweep_result)

        assert "## Execution Summary" in report
        assert "Total Combinations | 3" in report
        assert "Successful | 3" in report
        assert "Failed | 0" in report
        assert "Success Rate | 100.0%" in report

    def test_top_results_section_indicator(
        self, indicator_sweep_result: SweepResult
    ) -> None:
        """Indicator report shows top results by composite_score."""
        report = generate_sweep_report(indicator_sweep_result)

        assert "## Top" in report
        assert "composite_score" in report
        # Best result should be ranked first (lookback=20, window=20 with 0.88)
        assert "0.880" in report

    def test_top_results_section_backtest(
        self, backtest_sweep_result: SweepResult
    ) -> None:
        """Backtest report shows top results by sharpe_ratio."""
        report = generate_sweep_report(backtest_sweep_result)

        assert "sharpe_ratio" in report
        assert "sortino_ratio" in report
        # Best result (1.35) should appear
        assert "1.350" in report

    def test_statistics_section(
        self, indicator_sweep_result: SweepResult
    ) -> None:
        """Report includes metric statistics."""
        report = generate_sweep_report(indicator_sweep_result)

        assert "## Metric Statistics" in report
        assert "Mean" in report
        assert "Std" in report
        assert "Min" in report
        assert "Max" in report

    def test_parameter_sensitivity_section(
        self, indicator_sweep_result: SweepResult
    ) -> None:
        """Report includes parameter sensitivity analysis."""
        report = generate_sweep_report(indicator_sweep_result)

        assert "## Parameter Sensitivity" in report
        assert "`indicator_transformation.lookback`" in report
        assert "`score_transformation.window`" in report


class TestSaveSweepReport:
    """Tests for save_sweep_report function."""

    def test_saves_to_output_dir(
        self, indicator_sweep_result: SweepResult, tmp_path: Path
    ) -> None:
        """Report is saved to sweep_analysis.md in output directory."""
        report_path = save_sweep_report(indicator_sweep_result, tmp_path)

        assert report_path.exists()
        assert report_path.name == "sweep_analysis.md"
        assert report_path.parent == tmp_path

    def test_uses_result_output_dir_by_default(
        self, indicator_sweep_result: SweepResult
    ) -> None:
        """Uses result.output_dir when no output_dir provided."""
        report_path = save_sweep_report(indicator_sweep_result)

        assert report_path.parent == indicator_sweep_result.output_dir
        assert report_path.exists()

    def test_report_content_is_written(
        self, indicator_sweep_result: SweepResult, tmp_path: Path
    ) -> None:
        """File content matches generated report."""
        report_path = save_sweep_report(indicator_sweep_result, tmp_path)

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# Sweep Analysis Report: test_indicator_sweep" in content
        assert "## Swept Parameters" in content
        assert "## Execution Summary" in content

    def test_creates_output_dir_if_missing(
        self, indicator_sweep_result: SweepResult, tmp_path: Path
    ) -> None:
        """Creates output directory if it doesn't exist."""
        new_dir = tmp_path / "new_sweep_dir"
        assert not new_dir.exists()

        report_path = save_sweep_report(indicator_sweep_result, new_dir)

        assert new_dir.exists()
        assert report_path.exists()


class TestEmptyResults:
    """Tests for edge cases with empty or failed results."""

    def test_all_failed_results(self, tmp_path: Path) -> None:
        """Report handles all-failed results gracefully."""
        config = SweepConfig(
            name="failed_sweep",
            description="All failed",
            mode="indicator",
            base=BaseConfig(signal="test"),
            parameters=(
                ParameterOverride(
                    path="indicator_transformation.parameters.lookback",
                    values=(10,),
                ),
            ),
        )

        results_df = pd.DataFrame(
            [
                {
                    "combination_id": 0,
                    "indicator_transformation.parameters.lookback": 10,
                    "status": "failed",
                    "error": "Test error",
                }
            ]
        )

        summary = SweepSummary(
            start_time="2025-12-20T10:00:00",
            end_time="2025-12-20T10:00:01",
            duration_seconds=1.0,
            total_combinations=1,
            successful=0,
            failed=1,
            mode="indicator",
        )

        result = SweepResult(
            config=config,
            results_df=results_df,
            summary=summary,
            output_dir=tmp_path,
        )

        report = generate_sweep_report(result)

        # Should not raise, should indicate no successful results
        assert "No successful results" in report or "failed_sweep" in report
