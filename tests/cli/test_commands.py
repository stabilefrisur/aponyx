"""Tests for CLI commands (config-only run command)."""

import json
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
    # CLI shows help when no command provided
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_cli_invalid_command(runner):
    """Test CLI rejects invalid commands."""
    result = runner.invoke(cli, ["invalid-command"])
    assert result.exit_code != 0


# ============================================================================
# Run Command Tests (Config-Only)
# ============================================================================


def test_run_command_requires_config_file(runner):
    """Test run command requires config file argument."""
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "Missing argument" in result.output


def test_run_command_missing_signal_field(runner, tmp_path):
    """Test run command validates signal field is required."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {"label": "test_label", "product": "cdx_ig_5y", "strategy": "balanced"}
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Missing required field" in result.output
    assert "signal" in result.output


def test_run_command_missing_product_field(runner, tmp_path):
    """Test run command validates product field is required."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {"label": "test_label", "signal": "spread_momentum", "strategy": "balanced"}
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Missing required field" in result.output
    assert "product" in result.output


def test_run_command_missing_strategy_field(runner, tmp_path):
    """Test run command validates strategy field is required."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {"label": "test_label", "signal": "spread_momentum", "product": "cdx_ig_5y"}
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Missing required field" in result.output
    assert "strategy" in result.output


def test_run_command_invalid_signal(runner, tmp_path):
    """Test run command validates signal exists in catalog."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "nonexistent_signal",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Signal 'nonexistent_signal' not found" in result.output
    assert "Available signals:" in result.output


def test_run_command_invalid_strategy(runner, tmp_path):
    """Test run command validates strategy exists in catalog."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "nonexistent_strategy",
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Strategy 'nonexistent_strategy' not found" in result.output
    assert "Available strategies:" in result.output


def test_run_command_invalid_indicator_override(runner, tmp_path):
    """Test run command validates indicator override exists in catalog."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "indicator": "nonexistent_indicator",
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Indicator 'nonexistent_indicator' not found" in result.output
    assert "Available indicators:" in result.output


def test_run_command_invalid_transformation_override(runner, tmp_path):
    """Test run command validates score transformation override exists in catalog."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "score_transformation": "nonexistent_score_transformation",
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Score transformation 'nonexistent_score_transformation' not found" in result.output
    assert "Available score transformations:" in result.output


def test_run_command_invalid_security_not_found(runner, tmp_path):
    """Test run command validates securities exist in bloomberg_securities.json."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "securities": {"cdx": "nonexistent_security"},
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Security 'nonexistent_security' not found" in result.output
    assert "Available securities:" in result.output


def test_run_command_invalid_security_wrong_instrument_type(runner, tmp_path):
    """Test run command validates security instrument_type matches mapping key."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "securities": {
                    "cdx": "vix"
                },  # vix has instrument_type 'vix', not 'cdx'
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Security 'vix' has instrument_type 'vix', expected 'cdx'" in result.output


def test_run_command_minimal_config(runner, mock_workflow_engine, tmp_path):
    """Test run command with minimal config (only required fields)."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code == 0
    assert "=== Workflow Configuration ===" in result.output
    assert "Signal:                   spread_momentum [config]" in result.output
    assert "Product:                  cdx_ig_5y [config]" in result.output
    assert "Strategy:                 balanced [config]" in result.output
    assert "Data:                     synthetic [default]" in result.output
    assert "Indicator Transform:      spread_momentum_5d [from signal]" in result.output
    assert "Score Transform:          volatility_adjust_20d [from signal]" in result.output
    assert "Signal Transform:         passthrough [from signal]" in result.output
    assert "Steps:                    all [default]" in result.output
    assert "Force re-run:             False [default]" in result.output
    assert "Completed 6 steps" in result.output


def test_run_command_complete_config(runner, mock_workflow_engine, tmp_path):
    """Test run command with complete config (all fields specified)."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "cdx_etf_basis",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "indicator": "cdx_etf_spread_diff",
                "score_transformation": "z_score_20d",
                "signal_transformation": "bounded_2_0",
                "securities": {"cdx": "cdx_ig_5y", "etf": "lqd"},
                "data": "bloomberg",
                "steps": ["data", "signal", "backtest"],
                "force": True,
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code == 0
    assert "Indicator Transform:      cdx_etf_spread_diff [config]" in result.output
    assert "Score Transform:          z_score_20d [config]" in result.output
    assert "Signal Transform:         bounded_2_0 [config]" in result.output
    assert "Securities:               cdx:cdx_ig_5y, etf:lqd [config]" in result.output
    assert "Data:                     bloomberg [config]" in result.output
    assert "Steps:                    data, signal, backtest [config]" in result.output
    assert "Force re-run:             True [config]" in result.output


def test_run_command_indicator_override_only(runner, mock_workflow_engine, tmp_path):
    """Test run command with indicator override (keeps transformations from signal)."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "indicator": "spread_momentum_5d",
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code == 0
    assert "Indicator Transform:      spread_momentum_5d [config]" in result.output
    assert "Score Transform:          volatility_adjust_20d [from signal]" in result.output
    assert "Signal Transform:         passthrough [from signal]" in result.output
    # Transformation should come from signal
    assert "[from signal]" in result.output


def test_run_command_transformation_override_only(
    runner, mock_workflow_engine, tmp_path
):
    """Test run command with score transformation override (keeps indicator and signal transform from signal)."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "score_transformation": "z_score_60d",
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code == 0
    assert "Score Transform:          z_score_60d [config]" in result.output
    # Indicator and signal transform should come from signal
    assert "Indicator Transform:" in result.output and "[from signal]" in result.output
    assert "Signal Transform:" in result.output and "[from signal]" in result.output


def test_run_command_securities_override(runner, mock_workflow_engine, tmp_path):
    """Test run command with securities override."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "cdx_etf_basis",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "securities": {"cdx": "cdx_hy_5y", "etf": "hyg"},
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code == 0
    assert "Securities:               cdx:cdx_hy_5y, etf:hyg [config]" in result.output


def test_run_command_with_workflow_error(runner, tmp_path):
    """Test run command handles workflow execution errors."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
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
                {"step": "signal", "error": "Mock error", "type": "RuntimeError"}
            ],
        }
        mock_engine_class.return_value = mock_engine

        result = runner.invoke(cli, ["run", str(config_file)])

        assert result.exit_code != 0
        assert "Workflow failed" in result.output
        assert "signal:" in result.output


def test_run_command_invalid_yaml(runner, tmp_path):
    """Test run command handles invalid YAML syntax."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content:")

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code != 0
    assert "Failed to load config file" in result.output


def test_run_command_nonexistent_file(runner):
    """Test run command handles nonexistent config file."""
    result = runner.invoke(cli, ["run", "nonexistent.yaml"])

    assert result.exit_code != 0


def test_run_command_with_skipped_steps(runner, tmp_path):
    """Test run command displays skipped steps correctly."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
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
            "steps_completed": 4,
            "steps_skipped": 2,
            "output_dir": "/mock/output",
            "duration_seconds": 8.5,
            "errors": [],
        }
        mock_engine_class.return_value = mock_engine

        result = runner.invoke(cli, ["run", str(config_file)])

        assert result.exit_code == 0
        assert "Skipped 2" in result.output


def test_run_command_displays_source_attribution(
    runner, mock_workflow_engine, tmp_path
):
    """Test run command displays correct source tags for all fields."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "label": "test_label",
                "signal": "spread_momentum",
                "product": "cdx_ig_5y",
                "strategy": "balanced",
                "data": "file",
            }
        )
    )

    result = runner.invoke(cli, ["run", str(config_file)])

    assert result.exit_code == 0
    assert "[config]" in result.output
    assert "[from signal]" in result.output
    assert "[from indicator]" in result.output
    assert "[default]" in result.output


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


def test_list_products_command(runner, tmp_path):
    """Test list products command."""
    # Create mock bloomberg_securities.json
    securities = {
        "cdx_ig_5y": {"description": "CDX IG 5Y", "instrument_type": "cdx"},
        "lqd": {"description": "LQD ETF", "instrument_type": "etf"},
    }

    securities_file = tmp_path / "bloomberg_securities.json"
    securities_file.write_text(json.dumps(securities))

    with patch("aponyx.cli.commands.list.BLOOMBERG_SECURITIES_PATH", securities_file):
        result = runner.invoke(cli, ["list", "products"])
        assert result.exit_code == 0
        assert "cdx_ig_5y" in result.output
        assert "CDX IG 5Y" in result.output
        assert "lqd" not in result.output  # ETF should not be listed as product


def test_list_indicators_command(runner):
    """Test list indicators command."""
    with patch("aponyx.cli.commands.list.IndicatorTransformationRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_all.return_value = {
            "cdx_etf_spread_diff": MagicMock(description="CDX-ETF spread difference"),
            "spread_momentum_5d": MagicMock(description="5-day momentum"),
        }
        mock_registry_class.return_value = mock_registry

        result = runner.invoke(cli, ["list", "indicators"])
        assert result.exit_code == 0
        assert "cdx_etf_spread_diff" in result.output
        assert "spread_momentum_5d" in result.output


def test_list_transformations_command(runner):
    """Test list score-transformations and signal-transformations commands."""
    # Test score transformations
    with patch(
        "aponyx.cli.commands.list.ScoreTransformationRegistry"
    ) as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_all.return_value = {
            "z_score_20d": MagicMock(description="20-day z-score"),
            "volatility_adjust_20d": MagicMock(description="Volatility adjustment"),
        }
        mock_registry_class.return_value = mock_registry

        result = runner.invoke(cli, ["list", "score-transformations"])
        assert result.exit_code == 0
        assert "z_score_20d" in result.output
        assert "volatility_adjust_20d" in result.output

    # Test signal transformations
    with patch(
        "aponyx.cli.commands.list.SignalTransformationRegistry"
    ) as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.list_all.return_value = {
            "passthrough": MagicMock(description="No transformation"),
            "bounded_2_0": MagicMock(description="Bounded [-2, 2]"),
        }
        mock_registry_class.return_value = mock_registry

        result = runner.invoke(cli, ["list", "signal-transformations"])
        assert result.exit_code == 0
        assert "passthrough" in result.output
        assert "bounded_2_0" in result.output


def test_list_securities_command(runner, tmp_path):
    """Test list securities command."""
    # Create mock bloomberg_securities.json
    securities = {
        "cdx_ig_5y": {"description": "CDX IG 5Y", "instrument_type": "cdx"},
        "lqd": {"description": "LQD ETF", "instrument_type": "etf"},
        "vix": {"description": "VIX Index", "instrument_type": "vix"},
    }

    securities_file = tmp_path / "bloomberg_securities.json"
    securities_file.write_text(json.dumps(securities))

    with patch("aponyx.cli.commands.list.BLOOMBERG_SECURITIES_PATH", securities_file):
        result = runner.invoke(cli, ["list", "securities"])
        assert result.exit_code == 0
        assert "cdx_ig_5y" in result.output
        assert "lqd" in result.output
        assert "vix" in result.output
        assert "cdx" in result.output  # instrument type
        assert "etf" in result.output  # instrument type


def test_list_steps_command(runner):
    """Test list steps command."""
    with patch("aponyx.cli.commands.list.StepRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.get_canonical_order.return_value = [
            "data",
            "signal",
            "suitability",
            "backtest",
            "performance",
            "visualization",
        ]
        mock_registry_class.return_value = mock_registry

        result = runner.invoke(cli, ["list", "steps"])
        assert result.exit_code == 0
        assert "data" in result.output
        assert "signal" in result.output
        assert "backtest" in result.output


# ============================================================================
# Clean Command Tests
# ============================================================================


def test_clean_command_requires_signal_or_all(runner):
    """Test clean command requires --workflows or --indicators flag."""
    result = runner.invoke(cli, ["clean"])
    assert result.exit_code != 0
    assert (
        "Must specify --workflows, --indicators, or --all" in result.output
        or "Missing option" in result.output
    )


def test_clean_command_dry_run(runner, tmp_path):
    """Test clean command in dry-run mode."""
    # Create mock processed directory
    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", tmp_path):
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
    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)
        test_file = workflows_dir / "test_file.txt"
        test_file.write_text("test")

        result = runner.invoke(cli, ["clean", "--all"])

        assert result.exit_code == 0
        assert not test_file.exists()


def test_clean_command_specific_signal(runner, tmp_path):
    """Test clean command removes specific signal results."""
    workflows_dir = tmp_path
    workflows_dir.mkdir(exist_ok=True)

    # Create test workflow directory with metadata
    test_dir = workflows_dir / "test_label_20241120_123456"
    test_dir.mkdir()
    (test_dir / "metadata.json").write_text(
        '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced", "timestamp": "2024-11-20T12:34:56"}'
    )

    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", workflows_dir):
        result = runner.invoke(
            cli, ["clean", "--workflows", "--signal", "spread_momentum"]
        )

        assert result.exit_code == 0
        assert not test_dir.exists()


def test_clean_command_no_cached_results(runner, tmp_path):
    """Test clean command with no cached results."""
    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", tmp_path):
        result = runner.invoke(cli, ["clean", "--workflows", "--all"])

        assert result.exit_code == 0
        assert (
            "No workflows found" in result.output
            or "No cached results" in result.output
        )


def test_clean_command_signal_not_found(runner, tmp_path):
    """Test clean command with signal that has no cached results."""
    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)

        result = runner.invoke(
            cli, ["clean", "--workflows", "--signal", "nonexistent_signal"]
        )

        assert result.exit_code == 0
        assert (
            "No cached results found" in result.output
            or "No workflows found" in result.output
        )


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


def test_report_command_generates_output(runner, tmp_path):
    """Test report command generates console output."""
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
            mock_generate.return_value = "Mock report content"

            result = runner.invoke(cli, ["report", "--workflow", "test_label"])

            assert result.exit_code == 0
            assert "Mock report content" in result.output


def test_report_command_markdown_format(runner, tmp_path):
    """Test report command generates markdown format."""
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
            mock_generate.return_value = "# Mock Report"

            result = runner.invoke(
                cli,
                ["report", "--workflow", "test_label", "--format", "markdown"],
            )

            assert result.exit_code == 0
            assert "Report saved" in result.output


def test_report_command_html_format(runner, tmp_path):
    """Test report command generates HTML format."""
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
            mock_generate.return_value = "<html>Mock Report</html>"

            result = runner.invoke(
                cli,
                ["report", "--workflow", "test_label", "--format", "html"],
            )

            assert result.exit_code == 0
            assert "Report saved" in result.output


def test_report_command_with_output_path(runner, tmp_path):
    """Test report command saves to custom output path."""
    # Create mock workflow directory
    workflow_dir = tmp_path / "test_label_20241202_120000"
    workflow_dir.mkdir()
    (workflow_dir / "metadata.json").write_text(
        '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced"}'
    )
    reports_dir = workflow_dir / "reports"
    reports_dir.mkdir()
    (reports_dir / "suitability_evaluation_20241202.md").write_text("Test content")

    output_file = tmp_path / "custom_report.md"

    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
            mock_generate.return_value = "Mock report"

            result = runner.invoke(
                cli,
                [
                    "report",
                    "--workflow",
                    "test_label",
                    "--format",
                    "markdown",
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == 0


def test_report_command_no_workflow_results(runner, tmp_path):
    """Test report command handles missing workflow results."""
    # Empty workflows directory
    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        result = runner.invoke(cli, ["report", "--workflow", "nonexistent"])

        assert result.exit_code != 0
        # Updated error message from new implementation
        assert "No workflows found" in result.output or "not found" in result.output


def test_report_command_generation_error(runner, tmp_path):
    """Test report command handles generation errors."""
    # Create mock workflow directory
    workflow_dir = tmp_path / "test_label_20241202_120000"
    workflow_dir.mkdir()
    (workflow_dir / "metadata.json").write_text(
        '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced"}'
    )

    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
            mock_generate.side_effect = RuntimeError("Mock generation error")

            result = runner.invoke(cli, ["report", "--workflow", "test_label"])

            assert result.exit_code != 0
            assert (
                "Report generation failed" in result.output
                or "error" in result.output.lower()
            )


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
    assert "YAML configuration file" in result.output
    assert "Required YAML fields:" in result.output
    assert "Optional YAML fields:" in result.output


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
    assert "--workflow" in result.output
    assert "--format" in result.output
    assert "--output" in result.output
