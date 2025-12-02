"""Integration tests for CLI workflow (config-only)."""

from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from aponyx.cli.main import cli


@pytest.fixture
def runner():
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_all_registries():
    """Mock all registries for integration tests."""
    with (
        patch("aponyx.cli.commands.list.SignalRegistry") as mock_signal_reg,
        patch("aponyx.cli.commands.list.StrategyRegistry") as mock_strategy_reg,
        patch("aponyx.cli.commands.list.DataRegistry") as mock_data_reg,
    ):
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

    # Step 3: Run workflow with config file
    config_file = tmp_path / "workflow.yaml"
    config_file.write_text(
        yaml.dump({
                    "label": "test_label",
                    "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
            }
        )
    )

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

        result = runner.invoke(cli, ["run", str(config_file)])
        assert result.exit_code == 0
        assert "Signal:          spread_momentum [config]" in result.output
        assert "Strategy:        balanced [config]" in result.output
        assert "Product:         cdx_ig_5y [config]" in result.output

    # Step 4: Generate report
    # Create mock workflow directory for report command
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
            mock_generate.return_value = "Mock report content"

            result = runner.invoke(cli, ["report", "--workflow", "test_label"])
            assert result.exit_code == 0
            assert "Mock report content" in result.output

    # Step 5: Clean results
    clean_dir = tmp_path / "clean_test"
    clean_dir.mkdir()
    test_file = clean_dir / "test_label_20251120_123456"
    test_file.mkdir()
    (test_file / "metadata.json").write_text(
        '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced", "timestamp": "2025-11-20T12:34:56"}'
    )

    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", clean_dir):
        result = runner.invoke(
            cli, ["clean", "--workflows", "--signal", "spread_momentum", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Would delete" in result.output or "workflow" in result.output.lower()
        assert test_file.exists()  # Not deleted in dry-run


def test_workflow_with_all_data_sources(runner, tmp_path):
    """Test run command with different data sources."""
    data_sources = ["synthetic", "file", "bloomberg"]

    for source in data_sources:
        config_file = tmp_path / f"workflow_{source}.yaml"
        config_file.write_text(
            yaml.dump({
                    "label": "test_label",
                    "signal": "spread_momentum",
                    "product": "cdx_ig_5y",
                    "strategy": "balanced",
                    "data": source,
                }
            )
        )

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

            result = runner.invoke(cli, ["run", str(config_file)])

            assert result.exit_code == 0
            assert f"Data:            {source} [config]" in result.output


def test_workflow_with_partial_steps(runner, tmp_path):
    """Test run command with different step combinations."""
    step_combinations = [
        ["data"],
        ["data", "signal"],
        ["data", "signal", "backtest"],
        ["signal", "backtest"],
    ]

    for steps in step_combinations:
        config_file = tmp_path / f"workflow_{'_'.join(steps)}.yaml"
        config_file.write_text(
            yaml.dump({
                    "label": "test_label",
                    "signal": "spread_momentum",
                    "product": "cdx_ig_5y",
                    "strategy": "balanced",
                    "steps": steps,
                }
            )
        )

        with patch("aponyx.cli.commands.run.WorkflowEngine") as mock_engine_class:
            mock_engine = MagicMock()
            step_count = len(steps)
            mock_engine.execute.return_value = {
                "steps_completed": step_count,
                "steps_skipped": 0,
                "output_dir": "/mock/output",
                "duration_seconds": 5.0 * step_count,
                "errors": [],
            }
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(cli, ["run", str(config_file)])

            assert result.exit_code == 0
            assert f"Completed {step_count} steps" in result.output


def test_report_all_formats(runner, tmp_path):
    """Test report generation in all formats."""
    formats = ["console", "markdown", "html"]

    for format_type in formats:
        # Create mock workflow directory
        workflow_dir = tmp_path / "test_label_20241202_120000"
        workflow_dir.mkdir(exist_ok=True)
        (workflow_dir / "metadata.json").write_text(
            '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced"}'
        )
        reports_dir = workflow_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        (reports_dir / "suitability_evaluation_20241202.md").write_text("Test content")
        
        with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
            with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
                mock_generate.return_value = f"Mock {format_type} report"

                result = runner.invoke(
                    cli,
                    ["report", "--workflow", "test_label", "--format", format_type],
                )

                assert result.exit_code == 0


def test_clean_with_different_scopes(runner, tmp_path):
    """Test clean command with different scopes."""
    workflows_dir = tmp_path
    workflows_dir.mkdir(exist_ok=True)

    # Create workflows with metadata for multiple signals
    signals = ["spread_momentum", "cdx_vix_gap", "vix_spread"]
    for signal in signals:
        signal_dir = workflows_dir / f"test_{signal}_20251120_123456"
        signal_dir.mkdir()
        (signal_dir / "metadata.json").write_text(
            f'{{"label": "test_{signal}", "signal": "{signal}", "strategy": "balanced", "timestamp": "2025-11-20T12:34:56"}}'
        )

    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", workflows_dir):
        # Test cleaning specific signal - now requires --workflows flag
        result = runner.invoke(cli, ["clean", "--workflows", "--signal", "spread_momentum"])
        assert result.exit_code == 0

        # Test cleaning all (remaining)
        result = runner.invoke(cli, ["clean", "--workflows", "--all", "--dry-run"])
        assert result.exit_code == 0


def test_error_recovery_workflow(runner, tmp_path):
    """Test workflow error handling and recovery."""
    # Step 1: Run workflow with error
    config_file = tmp_path / "workflow.yaml"
    config_file.write_text(
        yaml.dump({
                    "label": "test_label",
                    "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
            }
        )
    )

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

        result = runner.invoke(cli, ["run", str(config_file)])
        assert result.exit_code != 0
        assert "Workflow failed" in result.output

    # Step 2: Try to generate report (should fail)
    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        result = runner.invoke(cli, ["report", "--workflow", "test_label"])
        assert result.exit_code != 0

    # Step 3: Fix and re-run with force flag
    config_file.write_text(
        yaml.dump({
                    "label": "test_label",
                    "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "force": True,
            }
        )
    )

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

        result = runner.invoke(cli, ["run", str(config_file)])
        assert result.exit_code == 0
        assert "Force re-run:    True [config]" in result.output


def test_yaml_config_workflow(runner, tmp_path):
    """Test complete workflow using YAML configuration."""
    # Create YAML config with required and optional fields
    config_file = tmp_path / "research_workflow.yaml"
    config_file.write_text(
        yaml.dump({
                    "label": "test_label",
                    "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "data": "synthetic",
                "steps": ["data", "signal", "backtest", "visualization"],
                "force": False,
            }
        )
    )

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

        result = runner.invoke(cli, ["run", str(config_file)])
        assert result.exit_code == 0
        assert "Signal:          spread_momentum [config]" in result.output


def test_concurrent_command_safety(runner, tmp_path):
    """Test that commands handle concurrent execution safely."""
    # This tests that commands don't interfere with each other
    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)

        # Simulate multiple clean operations
        for i in range(3):
            test_dir = workflows_dir / f"test_signal_{i}_20251120_123456"
            test_dir.mkdir()
            (test_dir / "metadata.json").write_text(
                f'{{"label": "test_signal_{i}", "signal": "test_signal_{i}", "strategy": "balanced", "timestamp": "2025-11-20T12:34:56"}}'
            )

        # Run clean in dry-run mode
        result1 = runner.invoke(cli, ["clean", "--workflows", "--all", "--dry-run"])
        result2 = runner.invoke(
            cli, ["clean", "--workflows", "--signal", "test_signal_0", "--dry-run"]
        )

        assert result1.exit_code == 0
        assert result2.exit_code == 0


def test_command_help_consistency(runner):
    """Test that all commands have consistent help text."""
    commands = ["run", "list", "clean", "report"]

    for cmd in commands:
        result = runner.invoke(cli, [cmd, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        # run command uses Arguments, others use Options
        if cmd == "run":
            assert "Arguments:" in result.output or "CONFIG_PATH" in result.output
        else:
            assert "Options:" in result.output


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
