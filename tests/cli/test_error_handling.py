"""Tests for CLI error handling and edge cases."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aponyx.cli.main import cli, main


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


# ============================================================================
# Main Entry Point Tests
# ============================================================================


def test_main_function_catches_exceptions():
    """Test main entry point catches and logs exceptions."""
    with patch("aponyx.cli.main.cli") as mock_cli:
        mock_cli.side_effect = RuntimeError("Mock error")
        
        with pytest.raises(SystemExit) as exc_info:
            main()
            
        assert exc_info.value.code == 1


def test_main_function_normal_exit():
    """Test main entry point exits normally on success."""
    with patch("aponyx.cli.main.cli") as mock_cli:
        mock_cli.return_value = None
        
        # Should not raise SystemExit
        main()


# ============================================================================
# Run Command Error Cases
# ============================================================================


def test_run_command_config_validation_error(runner):
    """Test run command handles WorkflowConfig validation errors."""
    with patch("aponyx.cli.commands.run.WorkflowConfig") as mock_config:
        mock_config.side_effect = ValueError("Invalid configuration")
        
        result = runner.invoke(cli, [
            "run",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        
        assert result.exit_code != 0
        assert "Configuration error" in result.output
        assert "Invalid configuration" in result.output


def test_run_command_empty_yaml_config(runner, tmp_path):
    """Test run command handles empty YAML config file."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("")
    
    result = runner.invoke(cli, [
        "run",
        "--config", str(config_file),
    ])
    
    assert result.exit_code != 0
    assert "Missing required parameters" in result.output


def test_run_command_yaml_with_null_values(runner, tmp_path):
    """Test run command handles YAML with null values."""
    config_file = tmp_path / "null.yaml"
    config_file.write_text("signal: null\nstrategy: null\n")
    
    result = runner.invoke(cli, [
        "run",
        "--config", str(config_file),
    ])
    
    assert result.exit_code != 0
    assert "Missing required parameters" in result.output


def test_run_command_workflow_engine_exception(runner):
    """Test run command handles WorkflowEngine exceptions."""
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine_class.side_effect = RuntimeError("Engine initialization failed")
        
        result = runner.invoke(cli, [
            "run",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        
        assert result.exit_code != 0


def test_run_command_multiple_errors_in_workflow(runner):
    """Test run command displays multiple workflow errors."""
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 1,
            "steps_skipped": 0,
            "output_dir": "/mock/output",
            "duration_seconds": 2.5,
            "errors": [
                {"step": "data", "error": "Data error", "type": "ValueError"},
                {"step": "signal", "error": "Signal error", "type": "RuntimeError"},
            ],
        }
        mock_engine_class.return_value = mock_engine
        
        result = runner.invoke(cli, [
            "run",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        
        assert result.exit_code != 0
        assert "Error in data" in result.output
        assert "Error in signal" in result.output


# ============================================================================
# List Command Error Cases
# ============================================================================


def test_list_signals_registry_error(runner):
    """Test list signals handles registry initialization errors."""
    with patch("aponyx.cli.commands.list.SignalRegistry") as mock_registry_class:
        mock_registry_class.side_effect = FileNotFoundError("Catalog not found")
        
        result = runner.invoke(cli, ["list", "signals"])
        
        assert result.exit_code != 0


def test_list_strategies_registry_error(runner):
    """Test list strategies handles registry initialization errors."""
    with patch("aponyx.cli.commands.list.StrategyRegistry") as mock_registry_class:
        mock_registry_class.side_effect = FileNotFoundError("Catalog not found")
        
        result = runner.invoke(cli, ["list", "strategies"])
        
        assert result.exit_code != 0


def test_list_datasets_registry_error(runner):
    """Test list datasets handles registry initialization errors."""
    with patch("aponyx.cli.commands.list.DataRegistry") as mock_registry_class:
        mock_registry_class.side_effect = FileNotFoundError("Registry not found")
        
        result = runner.invoke(cli, ["list", "datasets"])
        
        assert result.exit_code != 0


def test_list_datasets_missing_metadata(runner):
    """Test list datasets handles missing metadata gracefully."""
    with patch("aponyx.cli.commands.list.DataRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_datasets.return_value = ["cdx_ig_5y"]
        mock_registry.get_dataset_info.return_value = {}  # Empty metadata
        mock_registry_class.return_value = mock_registry
        
        result = runner.invoke(cli, ["list", "datasets"])
        
        assert result.exit_code == 0
        assert "unknown" in result.output


# ============================================================================
# Clean Command Error Cases
# ============================================================================


def test_clean_command_permission_error(runner, tmp_path):
    """Test clean command handles permission errors."""
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        
        with patch("shutil.rmtree") as mock_rmtree:
            mock_rmtree.side_effect = PermissionError("Permission denied")
            
            result = runner.invoke(cli, ["clean", "--all"])
            
            # Should propagate the error
            assert result.exit_code != 0


def test_clean_command_with_files_and_directories(runner, tmp_path):
    """Test clean command handles both files and directories."""
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        
        # Create both file and directory
        test_dir = workflows_dir / "spread_momentum_balanced_20251120_123456"
        test_dir.mkdir()
        test_file = workflows_dir / "spread_momentum_metadata.json"
        test_file.write_text("{}")
        
        result = runner.invoke(cli, ["clean", "--signal", "spread_momentum"])
        
        assert result.exit_code == 0
        assert not test_dir.exists()
        # File might or might not match the glob pattern


def test_clean_command_dry_run_with_multiple_items(runner, tmp_path):
    """Test clean command dry-run shows all items."""
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        
        # Create multiple items
        for i in range(3):
            item = workflows_dir / f"spread_momentum_balanced_2025112{i}_123456"
            item.mkdir()
        
        result = runner.invoke(cli, ["clean", "--signal", "spread_momentum", "--dry-run"])
        
        assert result.exit_code == 0
        assert result.output.count("Would delete") >= 3


# ============================================================================
# Report Command Error Cases
# ============================================================================


def test_report_command_file_not_found_detailed(runner):
    """Test report command shows helpful message for missing results."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.side_effect = FileNotFoundError(
            "No workflow results found for spread_momentum (balanced). "
            "Run workflow first: aponyx run --signal spread_momentum --strategy balanced"
        )
        
        result = runner.invoke(cli, [
            "report",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        
        assert result.exit_code != 0
        assert "No workflow results" in result.output
        assert "Run workflow first" in result.output


def test_report_command_unexpected_error(runner):
    """Test report command handles unexpected errors."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.side_effect = Exception("Unexpected error")
        
        result = runner.invoke(cli, [
            "report",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        
        assert result.exit_code != 0
        assert "Report generation failed" in result.output


def test_report_command_invalid_output_path(runner):
    """Test report command handles invalid output paths."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.side_effect = PermissionError("Cannot write to path")
        
        result = runner.invoke(cli, [
            "report",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
            "--output", "/invalid/path/report.md",
        ])
        
        assert result.exit_code != 0


# ============================================================================
# Logging Configuration Tests
# ============================================================================


def test_verbose_logging_configuration(runner):
    """Test verbose flag configures DEBUG level logging."""
    with patch("logging.basicConfig") as mock_config:
        with patch("aponyx.cli.commands.list.SignalRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.list_all.return_value = {}
            mock_registry_class.return_value = mock_registry
            
            runner.invoke(cli, ["--verbose", "list", "signals"])
            
            # Verify basicConfig was called with DEBUG level
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == pytest.approx(10)  # DEBUG level


def test_quiet_logging_configuration(runner):
    """Test quiet flag configures ERROR level logging."""
    with patch("logging.basicConfig") as mock_config:
        with patch("aponyx.cli.commands.list.SignalRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.list_all.return_value = {}
            mock_registry_class.return_value = mock_registry
            
            runner.invoke(cli, ["--quiet", "list", "signals"])
            
            # Verify basicConfig was called with ERROR level
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == pytest.approx(40)  # ERROR level


def test_default_logging_configuration(runner):
    """Test default logging uses INFO level."""
    with patch("logging.basicConfig") as mock_config:
        with patch("aponyx.cli.commands.list.SignalRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.list_all.return_value = {}
            mock_registry_class.return_value = mock_registry
            
            runner.invoke(cli, ["list", "signals"])
            
            # Verify basicConfig was called with INFO level
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == pytest.approx(20)  # INFO level


# ============================================================================
# Command Invocation Tests
# ============================================================================


def test_run_command_callable_directly():
    """Test run command can be imported and tested directly."""
    from aponyx.cli.commands import run
    
    assert callable(run)
    assert hasattr(run, "name")


def test_list_command_callable_directly():
    """Test list command can be imported and tested directly."""
    from aponyx.cli.commands import list_items
    
    assert callable(list_items)
    assert hasattr(list_items, "name")


def test_clean_command_callable_directly():
    """Test clean command can be imported and tested directly."""
    from aponyx.cli.commands import clean
    
    assert callable(clean)
    assert hasattr(clean, "name")


def test_report_command_callable_directly():
    """Test report command can be imported and tested directly."""
    from aponyx.cli.commands import report
    
    assert callable(report)
    assert hasattr(report, "name")


# ============================================================================
# Path Handling Tests
# ============================================================================


def test_run_command_config_with_relative_path(runner, tmp_path):
    """Test run command handles relative config paths."""
    # Create config file
    config_file = tmp_path / "workflow.yaml"
    config_data = """
signal: spread_momentum
strategy: balanced
"""
    config_file.write_text(config_data)
    
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
        
        # Use relative path by changing to tmp directory
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["run", "--config", "workflow.yaml"])
            assert result.exit_code == 0
        finally:
            os.chdir(original_cwd)


def test_report_command_output_with_absolute_path(runner, tmp_path):
    """Test report command handles absolute output paths."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.return_value = "Mock report"
        output_file = tmp_path / "reports" / "test_report.md"
        
        result = runner.invoke(cli, [
            "report",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
            "--format", "markdown",
            "--output", str(output_file.resolve()),
        ])
        
        assert result.exit_code == 0
