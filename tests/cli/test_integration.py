"""Integration tests for CLI workflow."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aponyx.cli.main import cli


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_all_registries():
    """Mock all registries for integration tests."""
    with patch("aponyx.cli.commands.list.SignalRegistry") as mock_signal_reg, \
         patch("aponyx.cli.commands.list.StrategyRegistry") as mock_strategy_reg, \
         patch("aponyx.cli.commands.list.DataRegistry") as mock_data_reg:
        
        # Configure signal registry
        mock_signal = MagicMock()
        mock_signal.list_all.return_value = {
            "spread_momentum": MagicMock(description="Spread momentum signal"),
        }
        mock_signal_reg.return_value = mock_signal
        
        # Configure strategy registry
        mock_strategy = MagicMock()
        mock_strategy.list_all.return_value = {
            "balanced": MagicMock(description="Balanced strategy"),
        }
        mock_strategy_reg.return_value = mock_strategy
        
        # Configure data registry
        mock_data = MagicMock()
        mock_data.list_datasets.return_value = ["cdx_ig_5y"]
        mock_data.get_dataset_info.return_value = {
            "metadata": {"params": {"security": "CDX.IG.5Y"}}
        }
        mock_data_reg.return_value = mock_data
        
        yield {
            "signal": mock_signal_reg,
            "strategy": mock_strategy_reg,
            "data": mock_data_reg,
        }


def test_full_workflow_integration(runner, mock_all_registries, tmp_path):
    """Test complete workflow: list -> run -> report -> clean."""
    
    # Step 1: List available signals
    result = runner.invoke(cli, ["list", "signals"])
    assert result.exit_code == 0
    assert "spread_momentum" in result.output
    
    # Step 2: List available strategies
    result = runner.invoke(cli, ["list", "strategies"])
    assert result.exit_code == 0
    assert "balanced" in result.output
    
    # Step 3: Run workflow
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 6,
            "steps_skipped": 0,
            "output_dir": str(tmp_path / "output"),
            "duration_seconds": 15.5,
            "errors": [],
        }
        mock_engine_class.return_value = mock_engine
        
        result = runner.invoke(cli, [
            "run",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        assert result.exit_code == 0
        assert "Workflow complete" in result.output
    
    # Step 4: Generate report
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.return_value = "Mock report content"
        
        result = runner.invoke(cli, [
            "report",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        assert result.exit_code == 0
        assert "Mock report content" in result.output
    
    # Step 5: Clean results
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "spread_momentum_balanced_20251120_123456"
        test_file.mkdir()
        
        result = runner.invoke(cli, ["clean", "--signal", "spread_momentum", "--dry-run"])
        assert result.exit_code == 0
        assert "Would delete" in result.output
        assert test_file.exists()  # Not deleted in dry-run


def test_workflow_with_all_data_sources(runner):
    """Test run command with different data sources."""
    data_sources = ["synthetic", "file", "bloomberg"]
    
    for source in data_sources:
        with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.execute.return_value = {
                "steps_completed": 6,
                "steps_skipped": 0,
                "output_dir": "/mock/output",
                "duration_seconds": 10.0,
                "errors": [],
            }
            mock_engine_class.return_value = mock_engine
            
            result = runner.invoke(cli, [
                "run",
                "--signal", "spread_momentum",
                "--strategy", "balanced",
                "--data", source,
            ])
            
            assert result.exit_code == 0
            assert f"Data source: {source}" in result.output


def test_workflow_with_partial_steps(runner):
    """Test run command with different step combinations."""
    step_combinations = [
        "data",
        "data,signal",
        "data,signal,backtest",
        "signal,backtest",
    ]
    
    for steps in step_combinations:
        with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
            mock_engine = MagicMock()
            step_count = len(steps.split(","))
            mock_engine.execute.return_value = {
                "steps_completed": step_count,
                "steps_skipped": 0,
                "output_dir": "/mock/output",
                "duration_seconds": 5.0 * step_count,
                "errors": [],
            }
            mock_engine_class.return_value = mock_engine
            
            result = runner.invoke(cli, [
                "run",
                "--signal", "spread_momentum",
                "--strategy", "balanced",
                "--steps", steps,
            ])
            
            assert result.exit_code == 0
            assert f"Steps completed: {step_count}" in result.output


def test_report_all_formats(runner):
    """Test report generation in all formats."""
    formats = ["console", "markdown", "html"]
    
    for format_type in formats:
        with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
            mock_generate.return_value = f"Mock {format_type} report"
            
            result = runner.invoke(cli, [
                "report",
                "--signal", "spread_momentum",
                "--strategy", "balanced",
                "--format", format_type,
            ])
            
            assert result.exit_code == 0
            assert f"{format_type} report" in result.output.lower()


def test_clean_with_different_scopes(runner, tmp_path):
    """Test clean command with different scopes."""
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        
        # Create files for multiple signals
        signals = ["spread_momentum", "cdx_vix_gap", "vix_spread"]
        for signal in signals:
            signal_dir = workflows_dir / f"{signal}_balanced_20251120_123456"
            signal_dir.mkdir()
        
        # Test cleaning specific signal
        result = runner.invoke(cli, ["clean", "--signal", "spread_momentum"])
        assert result.exit_code == 0
        
        # Test cleaning all (remaining)
        result = runner.invoke(cli, ["clean", "--all", "--dry-run"])
        assert result.exit_code == 0


def test_error_recovery_workflow(runner):
    """Test workflow error handling and recovery."""
    # Step 1: Run workflow with error
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 2,
            "steps_skipped": 0,
            "output_dir": "/mock/output",
            "duration_seconds": 5.0,
            "errors": [
                {"step": "signal", "error": "Data quality issue", "type": "ValueError"}
            ],
        }
        mock_engine_class.return_value = mock_engine
        
        result = runner.invoke(cli, [
            "run",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        assert result.exit_code != 0
        assert "Workflow failed" in result.output
    
    # Step 2: Try to generate report (should fail)
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.side_effect = FileNotFoundError("No workflow results")
        
        result = runner.invoke(cli, [
            "report",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        assert result.exit_code != 0
    
    # Step 3: Fix and re-run with force flag
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 6,
            "steps_skipped": 0,
            "output_dir": "/mock/output",
            "duration_seconds": 15.0,
            "errors": [],
        }
        mock_engine_class.return_value = mock_engine
        
        result = runner.invoke(cli, [
            "run",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
            "--force",
        ])
        assert result.exit_code == 0
        assert "Mode: Force re-run" in result.output


def test_yaml_config_workflow(runner, tmp_path):
    """Test complete workflow using YAML configuration."""
    # Create YAML config
    config_file = tmp_path / "research_workflow.yaml"
    config_content = """
signal: spread_momentum
strategy: balanced
data: synthetic
steps:
  - data
  - signal
  - backtest
  - visualization
force: false
"""
    config_file.write_text(config_content)
    
    # Run workflow from config
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 4,
            "steps_skipped": 0,
            "output_dir": "/mock/output",
            "duration_seconds": 20.0,
            "errors": [],
        }
        mock_engine_class.return_value = mock_engine
        
        result = runner.invoke(cli, ["run", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "spread_momentum" in result.output


def test_verbose_quiet_logging_integration(runner, mock_all_registries):
    """Test logging configuration across different commands."""
    # Test verbose mode
    result = runner.invoke(cli, ["--verbose", "list", "signals"])
    assert result.exit_code == 0
    
    # Test quiet mode
    result = runner.invoke(cli, ["--quiet", "list", "strategies"])
    assert result.exit_code == 0
    
    # Test default (info) mode
    result = runner.invoke(cli, ["list", "datasets"])
    assert result.exit_code == 0


def test_concurrent_command_safety(runner, tmp_path):
    """Test that commands handle concurrent execution safely."""
    # This tests that commands don't interfere with each other
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        
        # Simulate multiple clean operations
        for i in range(3):
            test_dir = workflows_dir / f"test_signal_{i}_20251120_123456"
            test_dir.mkdir()
        
        # Run clean in dry-run mode
        result1 = runner.invoke(cli, ["clean", "--all", "--dry-run"])
        result2 = runner.invoke(cli, ["clean", "--signal", "test_signal_0", "--dry-run"])
        
        assert result1.exit_code == 0
        assert result2.exit_code == 0


def test_command_help_consistency(runner):
    """Test that all commands have consistent help text."""
    commands = ["run", "list", "clean", "report"]
    
    for cmd in commands:
        result = runner.invoke(cli, [cmd, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Options:" in result.output or "Arguments:" in result.output


def test_invalid_command_suggestions(runner):
    """Test CLI provides helpful error for invalid commands."""
    result = runner.invoke(cli, ["rnu"])  # Typo
    assert result.exit_code != 0
    # Click may provide "Did you mean?" suggestions


def test_empty_registry_workflow(runner):
    """Test workflow with empty registries."""
    with patch("aponyx.cli.commands.list.SignalRegistry") as mock_signal_reg:
        mock_signal = MagicMock()
        mock_signal.list_all.return_value = {}
        mock_signal_reg.return_value = mock_signal
        
        result = runner.invoke(cli, ["list", "signals"])
        assert result.exit_code == 0
        assert "Available Signals:" in result.output
