"""
Tests for report generation.

Validates report data collection, console/markdown/HTML formatting,
and error handling.
"""

from pathlib import Path

import pytest

from aponyx.reporting.generator import (
    generate_report,
    ReportFormat,
    ReportData,
    _collect_report_data,
    _generate_console_report,
    _generate_markdown_report,
    _generate_html_report,
)


@pytest.fixture
def sample_suitability_report() -> str:
    """Generate sample suitability report markdown."""
    return """
# Suitability Evaluation

| Component | Score |
|-----------|-------|
| Data Health | 0.85 |
| Predictive | 0.75 |
| Economic | 0.70 |
| Stability | 0.80 |

**Decision:** PROCEED
"""


@pytest.fixture
def sample_performance_report() -> str:
    """Generate sample performance report markdown."""
    return """
# Performance Analysis

| Metric | Value |
|--------|-------|
| Sharpe Ratio | 1.25 |
| Total Return | 15.3% |
| Max Drawdown | -8.5% |
| Win Rate | 58.2% |
"""


class TestReportFormat:
    """Test ReportFormat enum."""

    def test_report_format_values(self):
        """Test ReportFormat has expected values."""
        assert ReportFormat.CONSOLE == "console"
        assert ReportFormat.MARKDOWN == "markdown"
        assert ReportFormat.HTML == "html"


class TestReportData:
    """Test ReportData dataclass."""

    def test_report_data_creation(self):
        """Test creating ReportData instance."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="spread_momentum",
            strategy_name="balanced",
            suitability_report="Test suitability",
            performance_report="Test performance",
            has_visualizations=True,
        )

        assert data.signal_name == "spread_momentum"
        assert data.strategy_name == "balanced"
        assert data.suitability_report == "Test suitability"

    def test_report_data_defaults(self):
        """Test ReportData default values."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
        )

        assert data.suitability_report is None
        assert data.performance_report is None
        assert data.has_visualizations is False


class TestCollectReportData:
    """Test report data collection."""

    def test_collect_report_data_success(
        self,
        tmp_path,
        sample_suitability_report,
        sample_performance_report,
    ):
        """Test collecting report data from workflow outputs."""
        # Create mock workflow directory
        workflow_dir = tmp_path / "spread_momentum_balanced_20241120_123456"
        workflow_dir.mkdir()
        reports_dir = workflow_dir / "reports"
        reports_dir.mkdir()

        # Create test reports with new timestamped naming
        suitability_file = reports_dir / "suitability_evaluation_20241120_123456.md"
        suitability_file.write_text(sample_suitability_report)

        performance_file = reports_dir / "performance_analysis_20241120_123456.md"
        performance_file.write_text(sample_performance_report)

        # Call _collect_report_data directly
        data = _collect_report_data(
            workflow_dir,
            "test_label",
            "spread_momentum",
            "balanced",
        )

        assert data.signal_name == "spread_momentum"
        assert data.strategy_name == "balanced"
        assert data.suitability_report is not None
        assert data.performance_report is not None

    def test_collect_report_data_no_results(
        self,
        tmp_path,
    ):
        """Test error when no workflow results exist."""
        # Create a fake workflow dir for the test
        fake_workflow_dir = tmp_path / "nonexistent_20241120_123456"
        fake_workflow_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="No reports found"):
            _collect_report_data(
                fake_workflow_dir,
                "test_label",
                "nonexistent_signal",
                "nonexistent_strategy",
            )


class TestGenerateConsoleReport:
    """Test console report generation."""

    def test_generate_console_report_basic(self):
        """Test basic console report generation."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
            suitability_report="Test suitability content",
            performance_report="Test performance content",
        )

        report = _generate_console_report(data)

        assert "test_signal" in report
        assert "test_strategy" in report
        assert "SUITABILITY EVALUATION" in report
        assert "PERFORMANCE ANALYSIS" in report

    def test_generate_console_report_with_visualizations(self, tmp_path):
        """Test console report includes visualization references."""
        from aponyx.config import DATA_WORKFLOWS_DIR

        # Create mock visualization directory
        viz_dir = (
            DATA_WORKFLOWS_DIR
            / "test_signal_test_strategy_20241120_123456"
            / "visualizations"
        )
        viz_dir.mkdir(parents=True, exist_ok=True)

        # Create mock visualization file
        viz_file = viz_dir / "equity_curve.html"
        viz_file.write_text("<html>chart</html>")

        data = ReportData(
            workflow_dir=DATA_WORKFLOWS_DIR
            / "test_signal_test_strategy_20241120_123456",
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
            has_visualizations=True,
        )

        report = _generate_console_report(data)

        assert "VISUALIZATIONS" in report


class TestGenerateMarkdownReport:
    """Test markdown report generation."""

    def test_generate_markdown_report_basic(
        self,
        sample_suitability_report,
        sample_performance_report,
    ):
        """Test basic markdown report generation."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
            suitability_report=sample_suitability_report,
            performance_report=sample_performance_report,
        )

        report = _generate_markdown_report(data)

        assert "# Research Report: test_label" in report
        assert "## Suitability Evaluation" in report
        assert "## Performance Analysis" in report
        assert "**Generated:**" in report

    def test_generate_markdown_report_with_workflow_dir(self):
        """Test markdown report includes workflow directory."""
        data = ReportData(
            workflow_dir=Path("/test/workflows/test_signal_20241120"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
        )

        report = _generate_markdown_report(data)

        assert "## Workflow Details" in report
        assert "test_signal_20241120" in report


class TestGenerateHTMLReport:
    """Test HTML report generation."""

    def test_generate_html_report_basic(self):
        """Test basic HTML report generation."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
            suitability_report="# Test\n\n**Bold text**",
            performance_report="## Metrics\n\n`code`",
        )

        report = _generate_html_report(data)

        assert "<!DOCTYPE html>" in report
        assert "<html" in report
        assert "</html>" in report
        assert "test_signal" in report
        assert "test_strategy" in report

    def test_generate_html_report_converts_markdown(self):
        """Test HTML report converts markdown formatting."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
            suitability_report="**Bold** and `code`",
        )

        report = _generate_html_report(data)

        assert "<strong>Bold</strong>" in report
        assert "<code>code</code>" in report

    def test_generate_html_report_with_tables(self):
        """Test HTML report handles markdown tables."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
            performance_report="""
| Metric | Value |
|--------|-------|
| Sharpe | 1.5 |
| Return | 20% |
""",
        )

        report = _generate_html_report(data)

        assert "<table>" in report
        assert "<th>" in report
        assert "<td>" in report


class TestGenerateReport:
    """Test main report generation function."""

    def test_generate_report_console(self, tmp_path):
        """Test generating console report."""
        # Create test workflow directory with metadata
        workflow_dir = tmp_path / "test_workflow_20241120_123456"
        workflow_dir.mkdir()
        metadata_path = workflow_dir / "metadata.json"
        import json

        metadata_path.write_text(
            json.dumps(
                {
                    "label": "test_workflow",
                    "signal": "test_signal",
                    "strategy": "test_strategy",
                }
            )
        )

        # Need at least one report file for generate_report to work
        reports_dir = workflow_dir / "reports"
        reports_dir.mkdir()
        (reports_dir / "suitability_evaluation_20241120.md").write_text("Test content")

        result = generate_report(
            workflow_dir=workflow_dir,
            format=ReportFormat.CONSOLE,
        )

        # generate_report returns a dict with 'content' and 'output_path'
        assert isinstance(result, dict)
        assert "content" in result
        assert isinstance(result["content"], str)
        assert "test_workflow" in result["content"]
        assert result["output_path"] is None  # Console format doesn't save to file

    def test_generate_report_markdown_with_file(self, tmp_path):
        """Test generating markdown report saves to file."""
        # Create test workflow directory with metadata
        workflow_dir = tmp_path / "test_workflow_20241120_123456"
        workflow_dir.mkdir()
        metadata_path = workflow_dir / "metadata.json"
        import json

        metadata_path.write_text(
            json.dumps(
                {
                    "label": "test_workflow",
                    "signal": "test_signal",
                    "strategy": "test_strategy",
                }
            )
        )

        # Need at least one report file
        reports_dir = workflow_dir / "reports"
        reports_dir.mkdir()
        (reports_dir / "performance_analysis_20241120.md").write_text("Test content")

        result = generate_report(
            workflow_dir=workflow_dir,
            format=ReportFormat.MARKDOWN,
        )

        # generate_report saves to workflow's reports folder for non-console formats
        assert isinstance(result, dict)
        assert result["output_path"] is not None
        assert result["output_path"].exists()
        assert "test_signal" in result["content"]

    def test_generate_report_html_with_file(self, tmp_path):
        """Test generating HTML report saves to file."""
        # Create test workflow directory with metadata
        workflow_dir = tmp_path / "test_workflow_20241120_123456"
        workflow_dir.mkdir()
        metadata_path = workflow_dir / "metadata.json"
        import json

        metadata_path.write_text(
            json.dumps(
                {
                    "label": "test_workflow",
                    "signal": "test_signal",
                    "strategy": "test_strategy",
                }
            )
        )

        # Need at least one report file
        reports_dir = workflow_dir / "reports"
        reports_dir.mkdir()
        (reports_dir / "suitability_evaluation_20241120.md").write_text("Test content")

        result = generate_report(
            workflow_dir=workflow_dir,
            format=ReportFormat.HTML,
        )

        # generate_report saves to workflow's reports folder for non-console formats
        assert isinstance(result, dict)
        assert result["output_path"] is not None
        assert result["output_path"].exists()
        assert "<!DOCTYPE html>" in result["content"]

    def test_generate_report_string_format(self, tmp_path):
        """Test generate_report accepts string format."""
        # Create test workflow directory with metadata
        workflow_dir = tmp_path / "test_workflow_20241120_123456"
        workflow_dir.mkdir()
        metadata_path = workflow_dir / "metadata.json"
        import json

        metadata_path.write_text(
            json.dumps(
                {
                    "label": "test_workflow",
                    "signal": "test_signal",
                    "strategy": "test_strategy",
                }
            )
        )

        # Need at least one report file
        reports_dir = workflow_dir / "reports"
        reports_dir.mkdir()
        (reports_dir / "performance_analysis_20241120.md").write_text("Test content")

        result = generate_report(
            workflow_dir=workflow_dir,
            format="markdown",
        )

        # generate_report returns a dict with 'content' and 'output_path'
        assert isinstance(result, dict)
        assert isinstance(result["content"], str)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_generate_console_report_empty_data(self):
        """Test console report with minimal data."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
        )

        report = _generate_console_report(data)

        assert "test_signal" in report
        assert "test_strategy" in report

    def test_generate_markdown_report_no_sections(self):
        """Test markdown report with no content sections."""
        data = ReportData(
            workflow_dir=Path("/test/dir"),
            label="test_label",
            signal_name="test_signal",
            strategy_name="test_strategy",
        )

        report = _generate_markdown_report(data)

        # Should still have header with label
        assert "# Research Report: test_label" in report
        assert "test_signal" in report
