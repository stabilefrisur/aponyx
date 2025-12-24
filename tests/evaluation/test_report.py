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
from aponyx.evaluation.suitability.report import (
    generate_suitability_report,
    save_report,
)


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

        # Check main sections per template
        assert "# Indicator Suitability Evaluation Report" in report
        assert "## Configuration Summary" in report
        assert "### Indicator Parameters" in report
        assert "### Data Summary" in report
        assert "## Evaluation Results" in report
        assert "### Component Scores" in report
        assert "## Detailed Component Analysis" in report
        assert "Data Health Score" in report
        assert "Predictive Association Score" in report
        assert "Economic Relevance Score" in report
        assert "Temporal Stability Score" in report

    def test_metrics_table_included(self, sample_pass_result):
        """Test that metrics are included."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for key metrics
        assert "Valid Observations" in report
        assert "Missing Data" in report
        assert "Date Range" in report

    def test_component_scores_table(self, sample_pass_result):
        """Test that component scores table is included."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for component scores in Evaluation Results section
        assert "### Component Scores" in report
        assert "Data Health" in report
        assert "Predictive Association" in report
        assert "Economic Relevance" in report
        assert "Temporal Stability" in report

    def test_correlation_table(self, sample_pass_result):
        """Test that correlation values are shown."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for correlation section
        assert "Correlation" in report
        assert "Lag" in report

    def test_report_includes_timestamp(self, sample_pass_result):
        """Test that report includes evaluation timestamp."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        assert "Evaluation Date" in report
        assert sample_pass_result.timestamp[:10] in report  # Date portion

    def test_predictive_table_includes_pvalue(self, sample_pass_result):
        """Test that predictive association table includes p-value column."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for p-value column header
        assert "P-Value" in report

    def test_component_table_includes_interpretation(self, sample_pass_result):
        """Test that component scores table includes interpretation column."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for interpretation column in Component Scores section
        assert "| Interpretation |" in report
        # Check for interpretation labels (at least one should appear)
        assert any(label in report for label in ["Excellent", "Strong", "Moderate", "Weak", "Low"])

    def test_weights_shown_as_percentage(self, sample_pass_result):
        """Test that weights are displayed as percentages."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Check for percentage format (e.g., "20%", "40%")
        assert "20%" in report or "40%" in report

    def test_report_includes_indicator_metadata_when_provided(self, sample_pass_result):
        """Test that indicator metadata section appears when provided."""
        indicator_metadata = {
            "name": "cdx_etf_basis",
            "description": "Spread differential between CDX IG 5Y and LQD ETF",
            "output_units": "basis_points",
            "lookback": 20,
            "compute_function_name": "compute_cdx_etf_spread_diff",
            "securities": ["cdx_ig_5y", "lqd"],
        }

        report = generate_suitability_report(
            sample_pass_result,
            "cdx_etf_basis",
            "CDX_IG",
            indicator_metadata=indicator_metadata,
        )

        assert "## Configuration Summary" in report
        assert "### Indicator Parameters" in report
        assert "cdx_etf_basis" in report
        assert "basis_points" in report

    def test_report_works_without_indicator_metadata(self, sample_pass_result):
        """Test that report generates without indicator metadata (uses defaults)."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Should still generate valid report with Configuration Summary
        assert "Suitability Evaluation Report" in report
        assert "### Indicator Parameters" in report
        # Should show N/A for missing metadata
        assert "N/A" in report

    def test_report_includes_date_range_when_provided(self, sample_pass_result):
        """Test that data summary section includes date_range when provided."""
        report = generate_suitability_report(
            sample_pass_result,
            "test_signal",
            "CDX_IG",
            date_range=("2020-01-01", "2024-12-24"),
        )

        assert "### Data Summary" in report
        assert "2020-01-01" in report
        assert "2024-12-24" in report

    def test_report_footer_links_to_correct_docs(self, sample_pass_result):
        """Test that footer links to correct documentation file."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Should link to the actual design doc
        assert "signal_suitability_design.md" in report
        # Should NOT have the old incorrect path
        assert "docs/suitability_evaluation.md" not in report

    def test_no_executive_summary_section(self, sample_pass_result):
        """Test that report does not have Executive Summary (per template)."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Template does not include Executive Summary
        assert "## Executive Summary" not in report

    def test_no_decision_criteria_section(self, sample_pass_result):
        """Test that report does not have Decision Criteria (per template)."""
        report = generate_suitability_report(
            sample_pass_result, "test_signal", "CDX_IG"
        )

        # Template does not include Decision Criteria section
        assert "## Decision Criteria" not in report


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
        assert "suitability_evaluation_" in returned_path.name

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
        report1 = generate_suitability_report(sample_pass_result, "signal1", "PROD1")
        report2 = generate_suitability_report(sample_pass_result, "signal2", "PROD2")

        path1 = save_report(report1, "signal1", "PROD1", tmp_path)
        path2 = save_report(report2, "signal2", "PROD2", tmp_path)

        # Both files should exist with different names
        assert path1.exists()
        assert path2.exists()
        assert "suitability_evaluation_" in path1.name
        assert "suitability_evaluation_" in path2.name


class TestComputePvalue:
    """Test p-value computation helper."""

    def test_compute_pvalue_significant(self):
        """Test p-value for significant t-statistic."""
        from aponyx.evaluation.suitability.report import _compute_pvalue

        # t=2.0 with n=102 (df=100) should give ~0.048 (significant at 0.05)
        pval = _compute_pvalue(2.0, 102)
        assert 0.04 < pval < 0.05

    def test_compute_pvalue_not_significant(self):
        """Test p-value for non-significant t-statistic."""
        from aponyx.evaluation.suitability.report import _compute_pvalue

        # t=1.0 with n=102 (df=100) should give ~0.32 (not significant)
        pval = _compute_pvalue(1.0, 102)
        assert 0.30 < pval < 0.35

    def test_compute_pvalue_zero_tstat(self):
        """Test p-value for zero t-statistic."""
        from aponyx.evaluation.suitability.report import _compute_pvalue

        # t=0.0 should give p=1.0 (no effect)
        pval = _compute_pvalue(0.0, 102)
        assert pval == 1.0
