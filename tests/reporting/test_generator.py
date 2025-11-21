"""
Tests for report generation.

Validates report data collection, console/markdown/HTML formatting,
and error handling.
"""

from pathlib import Path
from unittest.mock import patch

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
            signal_name="spread_momentum",
            strategy_name="balanced",
            suitability_report="Test suitability",
            performance_report="Test performance",
            has_visualizations=True,
            workflow_dir=Path("/test/dir"),
        )
        
        assert data.signal_name == "spread_momentum"
        assert data.strategy_name == "balanced"
        assert data.suitability_report == "Test suitability"

    def test_report_data_defaults(self):
        """Test ReportData default values."""
        data = ReportData(
            signal_name="test_signal",
            strategy_name="test_strategy",
        )
        
        assert data.suitability_report is None
        assert data.performance_report is None
        assert data.has_visualizations is False
        assert data.workflow_dir is None


class TestCollectReportData:
    """Test report data collection."""

    @patch("aponyx.reporting.generator.EVALUATION_DIR")
    @patch("aponyx.reporting.generator.PERFORMANCE_REPORTS_DIR")
    @patch("aponyx.reporting.generator.PROCESSED_DIR")
    def test_collect_report_data_success(
        self,
        mock_processed_dir,
        mock_perf_dir,
        mock_eval_dir,
        tmp_path,
        sample_suitability_report,
        sample_performance_report,
    ):
        """Test collecting report data from workflow outputs."""
        # Create mock directories
        eval_dir = tmp_path / "evaluation"
        perf_dir = tmp_path / "performance"
        workflows_dir = tmp_path / "workflows"
        
        eval_dir.mkdir()
        perf_dir.mkdir()
        workflows_dir.mkdir()
        
        mock_eval_dir.glob = lambda pattern: eval_dir.glob(pattern)
        mock_perf_dir.glob = lambda pattern: perf_dir.glob(pattern)
        mock_processed_dir.__truediv__ = lambda self, other: workflows_dir / other
        
        # Create test reports
        suitability_file = eval_dir / "spread_momentum_20241120_123456.md"
        suitability_file.write_text(sample_suitability_report)
        
        performance_file = perf_dir / "spread_momentum_balanced_20241120_123456.md"
        performance_file.write_text(sample_performance_report)
        
        # Create workflow directory
        workflow_dir = workflows_dir / "spread_momentum_balanced_20241120_123456"
        workflow_dir.mkdir()
        
        data = _collect_report_data("spread_momentum", "balanced")
        
        assert data.signal_name == "spread_momentum"
        assert data.strategy_name == "balanced"
        assert sample_suitability_report.strip() in data.suitability_report
        assert sample_performance_report.strip() in data.performance_report

    @patch("aponyx.reporting.generator.EVALUATION_DIR")
    @patch("aponyx.reporting.generator.PERFORMANCE_REPORTS_DIR")
    def test_collect_report_data_no_results(
        self,
        mock_perf_dir,
        mock_eval_dir,
        tmp_path,
    ):
        """Test error when no workflow results exist."""
        eval_dir = tmp_path / "evaluation"
        perf_dir = tmp_path / "performance"
        eval_dir.mkdir()
        perf_dir.mkdir()
        
        mock_eval_dir.glob = lambda pattern: eval_dir.glob(pattern)
        mock_perf_dir.glob = lambda pattern: perf_dir.glob(pattern)
        
        with pytest.raises(FileNotFoundError, match="No workflow results found"):
            _collect_report_data("nonexistent_signal", "nonexistent_strategy")


class TestGenerateConsoleReport:
    """Test console report generation."""

    def test_generate_console_report_basic(self):
        """Test basic console report generation."""
        data = ReportData(
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
        from aponyx.config import PROCESSED_DIR
        
        # Create mock visualization directory
        viz_dir = (
            PROCESSED_DIR / "workflows" / "visualizations" / "test_signal_test_strategy"
        )
        viz_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock visualization file
        viz_file = viz_dir / "equity_curve.html"
        viz_file.write_text("<html>chart</html>")
        
        data = ReportData(
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
            signal_name="test_signal",
            strategy_name="test_strategy",
            suitability_report=sample_suitability_report,
            performance_report=sample_performance_report,
        )
        
        report = _generate_markdown_report(data)
        
        assert "# Research Report: test_signal (test_strategy)" in report
        assert "## Suitability Evaluation" in report
        assert "## Performance Analysis" in report
        assert "**Generated:**" in report

    def test_generate_markdown_report_with_workflow_dir(self):
        """Test markdown report includes workflow directory."""
        data = ReportData(
            signal_name="test_signal",
            strategy_name="test_strategy",
            workflow_dir=Path("/test/workflows/test_signal_20241120"),
        )
        
        report = _generate_markdown_report(data)
        
        assert "## Workflow Details" in report
        assert "test_signal_20241120" in report


class TestGenerateHTMLReport:
    """Test HTML report generation."""

    def test_generate_html_report_basic(self):
        """Test basic HTML report generation."""
        data = ReportData(
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

    @patch("aponyx.reporting.generator._collect_report_data")
    def test_generate_report_console(self, mock_collect):
        """Test generating console report."""
        mock_collect.return_value = ReportData(
            signal_name="test_signal",
            strategy_name="test_strategy",
            suitability_report="Test content",
        )
        
        report = generate_report(
            "test_signal",
            "test_strategy",
            format=ReportFormat.CONSOLE,
        )
        
        assert isinstance(report, str)
        assert "test_signal" in report

    @patch("aponyx.reporting.generator._collect_report_data")
    def test_generate_report_markdown_with_file(self, mock_collect, tmp_path):
        """Test generating markdown report saves to file."""
        mock_collect.return_value = ReportData(
            signal_name="test_signal",
            strategy_name="test_strategy",
            performance_report="Test content",
        )
        
        output_path = tmp_path / "report.md"
        
        report = generate_report(
            "test_signal",
            "test_strategy",
            format=ReportFormat.MARKDOWN,
            output_path=output_path,
        )
        
        assert output_path.exists()
        assert "test_signal" in report

    @patch("aponyx.reporting.generator._collect_report_data")
    def test_generate_report_html_with_file(self, mock_collect, tmp_path):
        """Test generating HTML report saves to file."""
        mock_collect.return_value = ReportData(
            signal_name="test_signal",
            strategy_name="test_strategy",
            suitability_report="Test content",
        )
        
        output_path = tmp_path / "report.html"
        
        report = generate_report(
            "test_signal",
            "test_strategy",
            format=ReportFormat.HTML,
            output_path=output_path,
        )
        
        assert output_path.exists()
        assert "<!DOCTYPE html>" in report

    @patch("aponyx.reporting.generator._collect_report_data")
    def test_generate_report_string_format(self, mock_collect):
        """Test generate_report accepts string format."""
        mock_collect.return_value = ReportData(
            signal_name="test_signal",
            strategy_name="test_strategy",
        )
        
        report = generate_report(
            "test_signal",
            "test_strategy",
            format="markdown",
        )
        
        assert isinstance(report, str)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_generate_console_report_empty_data(self):
        """Test console report with minimal data."""
        data = ReportData(
            signal_name="test_signal",
            strategy_name="test_strategy",
        )
        
        report = _generate_console_report(data)
        
        assert "test_signal" in report
        assert "test_strategy" in report

    def test_generate_markdown_report_no_sections(self):
        """Test markdown report with no content sections."""
        data = ReportData(
            signal_name="test_signal",
            strategy_name="test_strategy",
        )
        
        report = _generate_markdown_report(data)
        
        # Should still have header
        assert "# Research Report" in report
        assert "test_signal" in report
