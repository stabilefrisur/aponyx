"""
Tests for suitability evaluation reporting.

Tests Markdown report generation and file persistence.
"""

import pytest
import pandas as pd
import numpy as np

from aponyx.evaluation.suitability.evaluator import (
    evaluate_signal_suitability,
    SuitabilityResult,
)
from aponyx.evaluation.suitability.report import generate_suitability_report, save_report


@pytest.fixture
def sample_pass_result() -> SuitabilityResult:
    """Create a sample PASS result."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=600, freq="D")
    signal = pd.Series(np.random.randn(600), index=dates, name="test_signal")
    target_changes = signal * 5.0 + np.random.randn(600) * 0.1
    target = target_changes.cumsum() + 100.0

    return evaluate_signal_suitability(signal, target)


@pytest.fixture
def sample_fail_result() -> SuitabilityResult:
    """Create a sample FAIL result."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=600, freq="D")
    signal = pd.Series(np.random.randn(600), index=dates)
    target = pd.Series(np.random.randn(600), index=dates)  # No correlation

    return evaluate_signal_suitability(signal, target)


class TestGenerateSuitabilityReport:
    """Test report generation logic."""

    def test_report_contains_all_sections(self, sample_pass_result):
        """Test that report contains all expected sections."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check main sections
        assert "# Signal-Product Suitability Evaluation Report" in report
        assert "## Executive Summary" in report
        assert "## Component Analysis" in report
        assert "Data Health Score" in report
        assert "Predictive Association Score" in report
        assert "Economic Relevance Score" in report
        assert "Temporal Stability Score" in report
        assert "## Composite Scoring" in report
        assert "## Decision Criteria" in report

    def test_pass_decision_indicator(self, sample_pass_result):
        """Test PASS decision shows correct indicator."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        assert "✅ PASS" in report

    def test_fail_decision_indicator(self, sample_fail_result):
        """Test FAIL decision shows correct indicator."""
        report = generate_suitability_report(
            sample_fail_result, "random_signal", "CDX_IG"
        )

        # Should be HOLD or FAIL
        assert any(marker in report for marker in ["⚠️ HOLD", "❌ FAIL"])

    def test_metrics_table_included(self, sample_pass_result):
        """Test that metrics are included."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for key metrics
        assert "Valid Observations" in report
        assert "Missing Data" in report
        assert "Composite Score" in report

    def test_component_scores_table(self, sample_pass_result):
        """Test that component scores table is included."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for component scores in Composite Scoring section
        assert "Composite Scoring" in report
        assert "Data Health" in report
        assert "Predictive" in report
        assert "Economic" in report
        assert "Stability" in report

    def test_correlation_table(self, sample_pass_result):
        """Test that correlation values are shown."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for correlation section
        assert "Correlation" in report
        # Correlations should be present for configured lags
        assert "1-day" in report or "Lag" in report

    def test_report_includes_timestamp(self, sample_pass_result):
        """Test that report includes evaluation timestamp."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        assert "Evaluation Date" in report
        assert sample_pass_result.timestamp[:10] in report  # Date portion

    def test_report_includes_config_details(self, sample_pass_result):
        """Test that configuration parameters are documented."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Should include decision criteria info
        assert "Decision Criteria" in report
        assert "PASS" in report
        assert "HOLD" in report
        assert "FAIL" in report


class TestSaveReport:
    """Test report file saving."""

    def test_saves_to_specified_path(self, tmp_path, sample_pass_result):
        """Test that report saves to specified directory."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        returned_path = save_report(report, "test_signal", "CDX_IG", tmp_path)

        assert returned_path.exists()
        assert returned_path.parent == tmp_path
        assert "test_signal_CDX_IG" in returned_path.name

    def test_creates_parent_directories(self, tmp_path, sample_pass_result):
        """Test that parent directories are created."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        output_dir = tmp_path / "subdir" / "nested"
        returned_path = save_report(report, "test_signal", "CDX_IG", output_dir)

        assert returned_path.exists()
        assert returned_path.parent.exists()

    def test_saved_content_matches(self, tmp_path, sample_pass_result):
        """Test that saved content matches generated report."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        returned_path = save_report(report, "test_signal", "CDX_IG", tmp_path)

        saved_content = returned_path.read_text(encoding="utf-8")
        assert saved_content == report

    def test_overwrites_existing_file(self, tmp_path, sample_pass_result):
        """Test that reports can be saved multiple times to same directory."""
        report1 = generate_suitability_report(
            sample_pass_result, "signal1", "PROD1"
        )
        report2 = generate_suitability_report(
            sample_pass_result, "signal2", "PROD2"
        )

        path1 = save_report(report1, "signal1", "PROD1", tmp_path)
        path2 = save_report(report2, "signal2", "PROD2", tmp_path)

        # Both files should exist with different names
        assert path1.exists()
        assert path2.exists()
        assert "signal1_PROD1" in path1.name
        assert "signal2_PROD2" in path2.name
