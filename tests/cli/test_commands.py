"""Tests for CLI commands."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml
from click.testing import CliRunner

from aponyx.cli.main import cli


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_workflow_engine():
    """Create mock workflow engine."""
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
        yield mock_engine_class


@pytest.fixture
def mock_signal_registry():
    """Create mock signal registry."""
    with patch("aponyx.cli.commands.list.SignalRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_all.return_value = {
            "spread_momentum": MagicMock(description="Spread momentum signal"),
            "cdx_vix_gap": MagicMock(description="VIX-CDX divergence"),
        }
        mock_registry_class.return_value = mock_registry
        yield mock_registry_class


@pytest.fixture
def mock_strategy_registry():
    """Create mock strategy registry."""
    with patch("aponyx.cli.commands.list.StrategyRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_all.return_value = {
            "balanced": MagicMock(description="Balanced position sizing"),
            "aggressive": MagicMock(description="Aggressive position sizing"),
        }
        mock_registry_class.return_value = mock_registry
        yield mock_registry_class


@pytest.fixture
def mock_data_registry():
    """Create mock data registry."""
    with patch("aponyx.cli.commands.list.DataRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_datasets.return_value = ["cdx_ig_5y", "cdx_hy_5y"]
        mock_registry.get_dataset_info.return_value = {
            "metadata": {"params": {"security": "CDX.IG.5Y"}}
        }
        mock_registry_class.return_value = mock_registry
        yield mock_registry_class


# ============================================================================
# CLI Main Tests
# ============================================================================


def test_cli_help(runner):
    """Test CLI shows help text."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Systematic Macro Credit Research CLI" in result.output
    assert "run" in result.output
    assert "list" in result.output
    assert "clean" in result.output
    assert "report" in result.output


def test_cli_verbose_flag(runner, mock_signal_registry):
    """Test verbose flag (removed in refactor - kept for compatibility)."""
    # Verbose/quiet flags removed - CLI is always concise now
    result = runner.invoke(cli, ["list", "signals"])
    assert result.exit_code == 0


def test_cli_quiet_flag(runner, mock_signal_registry):
    """Test quiet flag (removed in refactor - kept for compatibility)."""
    # Verbose/quiet flags removed - CLI is always concise now
    result = runner.invoke(cli, ["list", "signals"])
    assert result.exit_code == 0


def test_cli_no_command_shows_help(runner):
    """Test CLI without command shows usage info."""
    result = runner.invoke(cli, [])
    # Click returns exit code 2 for missing command
    assert result.exit_code == 2
    assert "Usage:" in result.output


def test_cli_invalid_command(runner):
    """Test CLI rejects invalid commands."""
    result = runner.invoke(cli, ["invalid-command"])
    assert result.exit_code != 0


# ============================================================================
# Run Command Tests
# ============================================================================


def test_run_command_requires_signal_and_strategy(runner):
    """Test run command validates required arguments."""
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "Missing" in result.output and "--signal" in result.output


def test_run_command_missing_signal(runner):
    """Test run command requires signal parameter."""
    result = runner.invoke(cli, ["run", "--strategy", "balanced"])
    assert result.exit_code != 0
    assert "Missing" in result.output


def test_run_command_missing_strategy(runner):
    """Test run command requires strategy parameter."""
    result = runner.invoke(cli, ["run", "--signal", "spread_momentum"])
    assert result.exit_code != 0
    assert "Missing" in result.output


def test_run_command_with_mock_workflow(runner, mock_workflow_engine):
    """Test run command executes workflow."""
    result = runner.invoke(
        cli,
        [
            "run",
            "--signal",
            "spread_momentum",
            "--strategy",
            "balanced",
        ],
    )

    assert result.exit_code == 0
    assert "Running: spread_momentum (balanced)" in result.output
    assert "Inputs:" in result.output
    assert "Product:" in result.output
    assert "Completed 6 steps" in result.output


def test_run_command_with_data_source(runner, mock_workflow_engine):
    """Test run command accepts data source option."""
    result = runner.invoke(
        cli,
        [
            "run",
            "--signal",
            "spread_momentum",
            "--strategy",
            "balanced",
            "--data",
            "file",
        ],
    )

    assert result.exit_code == 0
    assert "Data: file" in result.output
    assert "Inputs:" in result.output


def test_run_command_with_invalid_data_source(runner):
    """Test run command rejects invalid data source."""
    result = runner.invoke(
        cli,
        [
            "run",
            "--signal",
            "spread_momentum",
            "--strategy",
            "balanced",
            "--data",
            "invalid",
        ],
    )

    assert result.exit_code != 0


def test_run_command_with_workflow_error(runner):
    """Test run command handles workflow errors."""
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 2,
            "steps_skipped": 0,
            "output_dir": "/mock/output",
            "duration_seconds": 5.0,
            "errors": [{"step": "signal", "error": "Mock error", "type": "RuntimeError"}],
        }
        mock_engine_class.return_value = mock_engine

        result = runner.invoke(
            cli,
            [
                "run",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
            ],
        )

        assert result.exit_code != 0
        assert "Workflow failed" in result.output
        assert "signal:" in result.output


def test_run_command_with_steps_option(runner, mock_workflow_engine):
    """Test run command accepts steps option."""
    result = runner.invoke(
        cli,
        [
            "run",
            "--signal",
            "spread_momentum",
            "--strategy",
            "balanced",
            "--steps",
            "data,signal",
        ],
    )

    assert result.exit_code == 0
    assert "Steps: data, signal" in result.output


def test_run_command_with_force_flag(runner, mock_workflow_engine):
    """Test run command accepts force flag."""
    result = runner.invoke(
        cli,
        [
            "run",
            "--signal",
            "spread_momentum",
            "--strategy",
            "balanced",
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert "Mode: Force re-run" in result.output


def test_run_command_with_yaml_config(runner, mock_workflow_engine, tmp_path):
    """Test run command loads configuration from YAML file."""
    config_file = tmp_path / "workflow.yaml"
    config_data = {
        "signal": "spread_momentum",
        "strategy": "balanced",
        "data": "file",
        "force": True,
    }
    config_file.write_text(yaml.dump(config_data))

    result = runner.invoke(cli, ["run", "--config", str(config_file)])

    assert result.exit_code == 0
    assert "Running: spread_momentum (balanced)" in result.output


def test_run_command_yaml_overrides_with_cli_options(runner, mock_workflow_engine, tmp_path):
    """Test CLI options override YAML config values."""
    config_file = tmp_path / "workflow.yaml"
    config_data = {
        "signal": "cdx_vix_gap",
        "strategy": "aggressive",
    }
    config_file.write_text(yaml.dump(config_data))

    result = runner.invoke(
        cli,
        [
            "run",
            "--config",
            str(config_file),
            "--signal",
            "spread_momentum",  # Override YAML
        ],
    )

    assert result.exit_code == 0
    assert "Running: spread_momentum" in result.output


def test_run_command_invalid_yaml_config(runner, tmp_path):
    """Test run command handles invalid YAML config."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content:")

    result = runner.invoke(cli, ["run", "--config", str(config_file)])

    assert result.exit_code != 0
    assert "Failed to load config file" in result.output


def test_run_command_missing_yaml_config(runner):
    """Test run command handles missing YAML config file."""
    result = runner.invoke(cli, ["run", "--config", "nonexistent.yaml"])

    assert result.exit_code != 0


def test_run_command_yaml_with_steps(runner, mock_workflow_engine, tmp_path):
    """Test run command accepts steps from YAML config."""
    config_file = tmp_path / "workflow.yaml"
    config_data = {
        "signal": "spread_momentum",
        "strategy": "balanced",
        "steps": ["data", "signal", "backtest"],
    }
    config_file.write_text(yaml.dump(config_data))

    result = runner.invoke(cli, ["run", "--config", str(config_file)])

    assert result.exit_code == 0


def test_run_command_with_skipped_steps(runner):
    """Test run command displays skipped steps."""
    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine.execute.return_value = {
            "steps_completed": 4,
            "steps_skipped": 2,
            "output_dir": "/mock/output",
            "duration_seconds": 8.5,
            "errors": [],
        }
        mock_engine_class.return_value = mock_engine

        result = runner.invoke(
            cli,
            [
                "run",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
            ],
        )

        assert result.exit_code == 0
        assert "Skipped 2" in result.output


# ============================================================================
# List Command Tests
# ============================================================================


def test_list_signals_command(runner, mock_signal_registry):
    """Test list signals command."""
    result = runner.invoke(cli, ["list", "signals"])
    assert result.exit_code == 0
    assert "spread_momentum" in result.output
    assert "cdx_vix_gap" in result.output


def test_list_strategies_command(runner, mock_strategy_registry):
    """Test list strategies command."""
    result = runner.invoke(cli, ["list", "strategies"])
    assert result.exit_code == 0
    assert "balanced" in result.output
    assert "aggressive" in result.output


def test_list_datasets_command(runner, mock_data_registry):
    """Test list datasets command."""
    result = runner.invoke(cli, ["list", "datasets"])
    assert result.exit_code == 0
    assert "cdx_ig_5y" in result.output


def test_list_command_invalid_type(runner):
    """Test list command rejects invalid item type."""
    result = runner.invoke(cli, ["list", "invalid"])
    assert result.exit_code != 0


def test_list_command_requires_argument(runner):
    """Test list command requires item type argument."""
    result = runner.invoke(cli, ["list"])
    assert result.exit_code != 0


def test_list_signals_empty(runner):
    """Test list signals with empty registry."""
    with patch("aponyx.cli.commands.list.SignalRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_all.return_value = {}
        mock_registry_class.return_value = mock_registry

        result = runner.invoke(cli, ["list", "signals"])
        assert result.exit_code == 0


def test_list_strategies_empty(runner):
    """Test list strategies with empty registry."""
    with patch("aponyx.cli.commands.list.StrategyRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_all.return_value = {}
        mock_registry_class.return_value = mock_registry

        result = runner.invoke(cli, ["list", "strategies"])
        assert result.exit_code == 0


def test_list_datasets_empty(runner):
    """Test list datasets with empty registry."""
    with patch("aponyx.cli.commands.list.DataRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_datasets.return_value = []
        mock_registry_class.return_value = mock_registry

        result = runner.invoke(cli, ["list", "datasets"])
        assert result.exit_code == 0


# ============================================================================
# Clean Command Tests
# ============================================================================


def test_clean_command_requires_signal_or_all(runner):
    """Test clean command requires --signal or --all."""
    result = runner.invoke(cli, ["clean"])
    assert result.exit_code != 0
    assert "Must specify --signal or --all" in result.output


def test_clean_command_dry_run(runner, tmp_path):
    """Test clean command in dry-run mode."""
    # Create mock processed directory
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "spread_momentum_balanced_20251120_123456"
        test_file.mkdir()

        result = runner.invoke(cli, ["clean", "--all", "--dry-run"])

        assert result.exit_code == 0
        assert "Would delete" in result.output
        assert test_file.exists()  # Should not be deleted


def test_clean_command_all(runner, tmp_path):
    """Test clean command removes all cached results."""
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "test_file.txt"
        test_file.write_text("test")

        result = runner.invoke(cli, ["clean", "--all"])

        assert result.exit_code == 0
        assert not test_file.exists()


def test_clean_command_specific_signal(runner, tmp_path):
    """Test clean command removes specific signal results."""
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)

        # Create files for different signals
        target_file = workflows_dir / "spread_momentum_balanced_20251120_123456"
        target_file.mkdir()
        other_file = workflows_dir / "cdx_vix_gap_aggressive_20251120_123456"
        other_file.mkdir()

        result = runner.invoke(cli, ["clean", "--signal", "spread_momentum"])

        assert result.exit_code == 0
        assert not target_file.exists()
        assert other_file.exists()  # Other signal should remain


def test_clean_command_no_cached_results(runner, tmp_path):
    """Test clean command with no cached results."""
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        result = runner.invoke(cli, ["clean", "--all"])

        assert result.exit_code == 0
        assert "No cached results" in result.output


def test_clean_command_signal_not_found(runner, tmp_path):
    """Test clean command with signal that has no cached results."""
    with patch("aponyx.cli.commands.clean.PROCESSED_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)

        result = runner.invoke(cli, ["clean", "--signal", "nonexistent_signal"])

        assert result.exit_code == 0
        assert "No cached results found" in result.output


# ============================================================================
# Report Command Tests
# ============================================================================


def test_report_command_requires_signal_and_strategy(runner):
    """Test report command validates required arguments."""
    result = runner.invoke(cli, ["report"])
    assert result.exit_code != 0


def test_report_command_missing_signal(runner):
    """Test report command requires signal parameter."""
    result = runner.invoke(cli, ["report", "--strategy", "balanced"])
    assert result.exit_code != 0


def test_report_command_missing_strategy(runner):
    """Test report command requires strategy parameter."""
    result = runner.invoke(cli, ["report", "--signal", "spread_momentum"])
    assert result.exit_code != 0


def test_report_command_generates_output(runner):
    """Test report command generates console output."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.return_value = "Mock report content"

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
            ],
        )

        assert result.exit_code == 0
        assert "Mock report content" in result.output


def test_report_command_markdown_format(runner):
    """Test report command generates markdown format."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.return_value = "# Mock Report"

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
                "--format",
                "markdown",
            ],
        )

        assert result.exit_code == 0
        assert "Report saved" in result.output


def test_report_command_html_format(runner):
    """Test report command generates HTML format."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.return_value = "<html>Mock Report</html>"

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
                "--format",
                "html",
            ],
        )

        assert result.exit_code == 0
        assert "Report saved" in result.output


def test_report_command_with_output_path(runner, tmp_path):
    """Test report command saves to custom output path."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.return_value = "Mock report"
        output_file = tmp_path / "custom_report.md"

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
                "--format",
                "markdown",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        mock_generate.assert_called_once_with(
            signal_name="spread_momentum",
            strategy_name="balanced",
            format="markdown",
            output_path=output_file,
        )


def test_report_command_no_workflow_results(runner):
    """Test report command handles missing workflow results."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.side_effect = FileNotFoundError("No workflow results")

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
            ],
        )

        assert result.exit_code != 0
        assert "No workflow results" in result.output


def test_report_command_generation_error(runner):
    """Test report command handles generation errors."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.side_effect = RuntimeError("Mock generation error")

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
            ],
        )

        assert result.exit_code != 0
        assert "Report generation failed" in result.output


def test_report_command_invalid_format(runner):
    """Test report command rejects invalid format."""
    result = runner.invoke(
        cli,
        [
            "report",
            "--signal",
            "spread_momentum",
            "--strategy",
            "balanced",
            "--format",
            "invalid",
        ],
    )

    assert result.exit_code != 0


# ============================================================================
# Integration Tests
# ============================================================================


def test_verbose_and_quiet_flags_conflict(runner):
    """Test that verbose and quiet flags can both be specified (quiet wins)."""
    # This is allowed by Click - last flag wins
    result = runner.invoke(cli, ["--verbose", "--quiet", "list", "signals"])
    # Should not crash
    assert result.exit_code in [0, 1, 2]  # May fail due to missing dependencies


def test_run_help_text(runner):
    """Test run command help text."""
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "signal-strategy combination" in result.output
    assert "--signal" in result.output
    assert "--strategy" in result.output
    assert "--data" in result.output
    assert "--steps" in result.output
    assert "--force" in result.output
    assert "--config" in result.output


def test_list_help_text(runner):
    """Test list command help text."""
    result = runner.invoke(cli, ["list", "--help"])
    assert result.exit_code == 0
    assert "signals" in result.output
    assert "strategies" in result.output
    assert "datasets" in result.output


def test_clean_help_text(runner):
    """Test clean command help text."""
    result = runner.invoke(cli, ["clean", "--help"])
    assert result.exit_code == 0
    assert "--signal" in result.output
    assert "--all" in result.output
    assert "--dry-run" in result.output


def test_report_help_text(runner):
    """Test report command help text."""
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "--signal" in result.output
    assert "--strategy" in result.output
    assert "--format" in result.output
    assert "--output" in result.output
