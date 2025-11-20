"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from aponyx.cli.main import cli


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


def test_cli_help(runner):
    """Test CLI shows help text."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Systematic Macro Credit Research CLI" in result.output
    assert "run" in result.output
    assert "list" in result.output
    assert "clean" in result.output
    assert "report" in result.output


def test_cli_verbose_flag(runner):
    """Test verbose flag enables DEBUG logging."""
    result = runner.invoke(cli, ["--verbose", "list", "signals"])
    assert result.exit_code == 0
    # Should include DEBUG logs with verbose
    

def test_run_command_requires_signal_and_strategy(runner):
    """Test run command validates required arguments."""
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "Missing option '--signal'" in result.output or "Error" in result.output


def test_run_command_with_mock_workflow(runner):
    """Test run command executes workflow."""
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 6,
            "steps_skipped": 0,
            "output_dir": "/mock/output",
            "duration_seconds": 12.5,
            "errors": [],
        }
        mock_engine_class.return_value = mock_engine
        
        result = runner.invoke(cli, [
            "run",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
        ])
        
        assert result.exit_code == 0
        assert "Starting workflow: spread_momentum (balanced)" in result.output
        assert "Workflow complete" in result.output
        assert "Steps completed: 6" in result.output


def test_run_command_with_workflow_error(runner):
    """Test run command handles workflow errors."""
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 2,
            "steps_skipped": 0,
            "output_dir": "/mock/output",
            "duration_seconds": 5.0,
            "errors": [
                {"step": "signal", "error": "Mock error", "type": "RuntimeError"}
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
        assert "Error in signal" in result.output


def test_run_command_with_steps_option(runner):
    """Test run command accepts steps option."""
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 2,
            "steps_skipped": 0,
            "output_dir": "/mock/output",
            "duration_seconds": 5.0,
            "errors": [],
        }
        mock_engine_class.return_value = mock_engine
        
        result = runner.invoke(cli, [
            "run",
            "--signal", "spread_momentum",
            "--strategy", "balanced",
            "--steps", "data,signal",
        ])
        
        assert result.exit_code == 0
        assert "Steps: data, signal" in result.output


def test_run_command_with_force_flag(runner):
    """Test run command accepts force flag."""
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


def test_list_signals_command(runner):
    """Test list signals command."""
    result = runner.invoke(cli, ["list", "signals"])
    assert result.exit_code == 0
    assert "Available Signals:" in result.output
    # Should show actual signals from catalog
    assert "spread_momentum" in result.output or "cdx" in result.output


def test_list_strategies_command(runner):
    """Test list strategies command."""
    result = runner.invoke(cli, ["list", "strategies"])
    assert result.exit_code == 0
    assert "Available Strategies:" in result.output
    # Should show actual strategies from catalog
    assert "balanced" in result.output or "aggressive" in result.output


def test_list_datasets_command(runner):
    """Test list datasets command."""
    result = runner.invoke(cli, ["list", "datasets"])
    assert result.exit_code == 0
    assert "Registered Datasets:" in result.output


def test_list_command_invalid_type(runner):
    """Test list command rejects invalid item type."""
    result = runner.invoke(cli, ["list", "invalid"])
    assert result.exit_code != 0


def test_clean_command_requires_signal_or_all(runner):
    """Test clean command requires --signal or --all."""
    result = runner.invoke(cli, ["clean"])
    assert result.exit_code != 0
    assert "Must specify --signal or --all" in result.output


def test_clean_command_dry_run(runner):
    """Test clean command in dry-run mode."""
    result = runner.invoke(cli, ["clean", "--all", "--dry-run"])
    assert result.exit_code == 0
    if "No cached results" not in result.output:
        assert "Would delete" in result.output or "Dry run complete" in result.output


def test_report_command_placeholder(runner):
    """Test report command shows placeholder message."""
    result = runner.invoke(cli, [
        "report",
        "--signal", "spread_momentum",
        "--strategy", "balanced",
    ])
    assert result.exit_code == 0
    assert "not yet implemented" in result.output
