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


def test_run_command_config_validation_error(runner, tmp_path):
    """Test run command handles WorkflowConfig validation errors."""
    # Create config file with label
    config_file = tmp_path / "workflow.yaml"
    config_file.write_text(
        "label: test_label\nsignal: spread_momentum\nproduct: cdx_ig_5y\nstrategy: balanced\n"
    )

    with patch("aponyx.cli.commands.run.WorkflowConfig") as mock_config:
        mock_config.side_effect = ValueError("Invalid configuration")

        result = runner.invoke(
            cli,
            [
                "run",
                str(config_file),
            ],
        )

        assert result.exit_code != 0
        # Error message format may vary
        assert "error" in result.output.lower() or "invalid" in result.output.lower()


def test_run_command_empty_yaml_config(runner, tmp_path):
    """Test run command handles empty YAML config file."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("")

    result = runner.invoke(
        cli,
        [
            "run",
            str(config_file),
        ],
    )

    assert result.exit_code != 0
    assert "Missing" in result.output


def test_run_command_yaml_with_null_values(runner, tmp_path):
    """Test run command handles YAML with null values."""
    config_file = tmp_path / "null.yaml"
    config_file.write_text("signal: null\nproduct: null\nstrategy: null\n")

    result = runner.invoke(
        cli,
        [
            "run",
            str(config_file),
        ],
    )

    assert result.exit_code != 0
    # Null values are converted to string "None" and fail catalog validation
    assert "Signal 'None' not found" in result.output or "Missing" in result.output


def test_run_command_workflow_engine_exception(runner, tmp_path):
    """Test run command handles WorkflowEngine exceptions."""
    # Create config file
    config_file = tmp_path / "workflow.yaml"
    config_file.write_text(
        "signal: spread_momentum\nproduct: cdx_ig_5y\nstrategy: balanced\n"
    )

    with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
        mock_engine_class.side_effect = RuntimeError("Engine initialization failed")

        result = runner.invoke(
            cli,
            [
                "run",
                str(config_file),
            ],
        )

        assert result.exit_code != 0


def test_run_command_multiple_errors_in_workflow(runner, tmp_path):
    """Test run command displays multiple workflow errors."""
    # Create config file with label
    config_file = tmp_path / "workflow.yaml"
    config_file.write_text(
        "label: test_label\nsignal: spread_momentum\nproduct: cdx_ig_5y\nstrategy: balanced\n"
    )

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

        result = runner.invoke(
            cli,
            [
                "run",
                str(config_file),
            ],
        )

        assert result.exit_code != 0
        assert "data" in result.output.lower() or "error" in result.output.lower()


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
    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)

        with patch("shutil.rmtree") as mock_rmtree:
            mock_rmtree.side_effect = PermissionError("Permission denied")

            result = runner.invoke(cli, ["clean", "--workflows", "--all"])

            # Should catch and continue with remaining deletions
            # Changed behavior: clean command is now more resilient
            # The command succeeds even with permission errors
            assert result.exit_code == 0


def test_clean_command_dry_run_with_multiple_items(runner, tmp_path):
    """Test clean command dry-run shows all items."""
    workflows_dir = tmp_path
    workflows_dir.mkdir(exist_ok=True)

    # Create multiple items with metadata
    for i in range(3):
        item = workflows_dir / f"test_label_{i}_2025112{i}_123456"
        item.mkdir()
        (item / "metadata.json").write_text(
            f'{{"label": "test_label_{i}", "signal": "spread_momentum", "strategy": "balanced", "timestamp": "2025-11-2{i}T12:34:56"}}'
        )

    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", workflows_dir):
        result = runner.invoke(
            cli, ["clean", "--workflows", "--signal", "spread_momentum", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "Would delete" in result.output or "workflow" in result.output.lower()


# ============================================================================
# Report Command Error Cases
# ============================================================================


def test_report_command_file_not_found_detailed(runner, tmp_path):
    """Test report command shows helpful message for missing results."""
    # Empty workflows directory
    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        result = runner.invoke(cli, ["report", "--workflow", "test_label"])

        assert result.exit_code != 0
        assert "No workflows found" in result.output or "not found" in result.output


def test_report_command_unexpected_error(runner, tmp_path):
    """Test report command handles unexpected errors."""
    # Create mock workflow directory
    workflow_dir = tmp_path / "test_label_20241202_120000"
    workflow_dir.mkdir()
    (workflow_dir / "metadata.json").write_text(
        '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced"}'
    )

    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
            mock_generate.side_effect = Exception("Unexpected error")

            result = runner.invoke(cli, ["report", "--workflow", "test_label"])

            assert result.exit_code != 0
            assert (
                "Report generation failed" in result.output
                or "error" in result.output.lower()
            )


def test_report_command_invalid_output_path(runner):
    """Test report command handles invalid output paths."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.side_effect = PermissionError("Cannot write to path")

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
                "--output",
                "/invalid/path/report.md",
            ],
        )

        assert result.exit_code != 0


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
label: test_label
signal: spread_momentum
product: cdx_ig_5y
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
            result = runner.invoke(cli, ["run", "workflow.yaml"])
            assert result.exit_code == 0
        finally:
            os.chdir(original_cwd)


def test_report_command_with_absolute_workflow_path(runner, tmp_path):
    """Test report command handles workflows with absolute paths in output."""
    # Create mock workflow directory
    workflow_dir = tmp_path / "test_label_20241202_120000"
    workflow_dir.mkdir()
    (workflow_dir / "metadata.json").write_text(
        '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced"}'
    )
    reports_dir = workflow_dir / "reports"
    reports_dir.mkdir()
    (reports_dir / "suitability_evaluation_20241202.md").write_text("Test content")

    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
            # generate_report now returns a dict
            mock_generate.return_value = {
                "content": "Mock report",
                "output_path": workflow_dir / "reports" / "report.md",
            }

            result = runner.invoke(
                cli,
                [
                    "report",
                    "--workflow",
                    "test_label",
                    "--format",
                    "markdown",
                ],
            )

            assert result.exit_code == 0
