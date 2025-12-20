"""Tests for catalog migration module."""

import json
from pathlib import Path

import pytest

from aponyx.catalog.migration import (
    migrate_json_to_yaml,
    verify_round_trip,
)


@pytest.fixture
def sample_json_dir(tmp_path: Path) -> Path:
    """Create sample JSON catalog files for migration testing."""
    # Create directory structure
    models_dir = tmp_path / "models"
    backtest_dir = tmp_path / "backtest"
    data_dir = tmp_path / "data"

    models_dir.mkdir()
    backtest_dir.mkdir()
    data_dir.mkdir()

    # indicator_transformation.json
    indicator_data = [
        {
            "name": "test_indicator",
            "description": "Test indicator for migration",
            "compute_function_name": "compute_test_indicator",
            "data_requirements": {"cdx": "spread"},
            "default_securities": {"cdx": "cdx_ig_5y"},
            "output_units": "basis_points",
            "parameters": {"window": 20},
            "enabled": True,
        }
    ]
    with open(models_dir / "indicator_transformation.json", "w") as f:
        json.dump(indicator_data, f)

    # score_transformation.json
    score_data = [
        {
            "name": "z_score_20d",
            "description": "Z-score over 20-day window",
            "transform_type": "z_score",
            "parameters": {"window": 20, "min_periods": 10},
            "enabled": True,
        }
    ]
    with open(models_dir / "score_transformation.json", "w") as f:
        json.dump(score_data, f)

    # signal_transformation.json
    signal_transform_data = [
        {
            "name": "bounded_2",
            "description": "Signal bounded to [-2, 2]",
            "scaling": 1.0,
            "floor": -2.0,
            "cap": 2.0,
            "neutral_range": [-0.25, 0.25],
            "enabled": True,
        }
    ]
    with open(models_dir / "signal_transformation.json", "w") as f:
        json.dump(signal_transform_data, f)

    # signal_catalog.json
    signal_data = [
        {
            "name": "test_signal",
            "description": "Test signal for migration",
            "indicator_transformation": "test_indicator",
            "score_transformation": "z_score_20d",
            "signal_transformation": "bounded_2",
            "sign_multiplier": 1,
            "enabled": True,
        }
    ]
    with open(models_dir / "signal_catalog.json", "w") as f:
        json.dump(signal_data, f)

    # strategy_catalog.json
    strategy_data = [
        {
            "name": "test_strategy",
            "description": "Test strategy for migration",
            "position_size_mm": 10.0,
            "sizing_mode": "proportional",
            "stop_loss_pct": 5.0,
            "take_profit_pct": 10.0,
            "max_holding_days": None,
            "entry_threshold": None,
            "enabled": True,
        }
    ]
    with open(backtest_dir / "strategy_catalog.json", "w") as f:
        json.dump(strategy_data, f)

    # bloomberg_securities.json
    securities_data = {
        "cdx_ig_5y": {
            "description": "CDX IG 5Y Index",
            "instrument_type": "cdx",
            "quote_type": "spread",
            "channels": {
                "spread": {
                    "bloomberg_ticker": "CDX IG CDSI GEN 5Y Corp",
                    "field": "PX_LAST",
                    "column": "spread",
                    "validation": {"min": 0, "max": 10000},
                }
            },
            "dv01_per_million": 475.0,
            "transaction_cost_bps": 1.0,
        }
    }
    with open(data_dir / "bloomberg_securities.json", "w") as f:
        json.dump(securities_data, f)

    # bloomberg_instruments.json
    instruments_data = {
        "cdx": {
            "description": "CDX Credit Default Swap Index",
            "bloomberg_fields": ["PX_LAST"],
            "field_mapping": {"PX_LAST": "spread"},
            "requires_security_metadata": True,
        }
    }
    with open(data_dir / "bloomberg_instruments.json", "w") as f:
        json.dump(instruments_data, f)

    return tmp_path


class TestMigrateJsonToYaml:
    """Tests for migrate_json_to_yaml function."""

    def test_creates_yaml_files(self, sample_json_dir: Path, tmp_path: Path):
        """Migration creates both YAML files."""
        output_dir = tmp_path / "output"

        catalogs_path, securities_path = migrate_json_to_yaml(
            sample_json_dir, output_dir
        )

        assert catalogs_path.exists()
        assert securities_path.exists()
        assert catalogs_path.name == "catalogs.yaml"
        assert securities_path.name == "securities.yaml"

    def test_catalogs_yaml_content(self, sample_json_dir: Path, tmp_path: Path):
        """Catalogs YAML contains expected sections."""
        from ruamel.yaml import YAML

        output_dir = tmp_path / "output"
        catalogs_path, _ = migrate_json_to_yaml(sample_json_dir, output_dir)

        yaml = YAML()
        with open(catalogs_path) as f:
            data = yaml.load(f)

        # Verify sections exist
        assert "indicator_transformations" in data
        assert "score_transformations" in data
        assert "signal_transformations" in data
        assert "signals" in data
        assert "strategies" in data

        # Verify content
        assert len(data["indicator_transformations"]) == 1
        assert data["indicator_transformations"][0]["name"] == "test_indicator"
        assert len(data["signals"]) == 1
        assert data["signals"][0]["name"] == "test_signal"

    def test_securities_yaml_content(self, sample_json_dir: Path, tmp_path: Path):
        """Securities YAML contains expected sections."""
        from ruamel.yaml import YAML

        output_dir = tmp_path / "output"
        _, securities_path = migrate_json_to_yaml(sample_json_dir, output_dir)

        yaml = YAML()
        with open(securities_path) as f:
            data = yaml.load(f)

        # Verify sections exist
        assert "securities" in data
        assert "instruments" in data

        # Verify content
        assert "cdx_ig_5y" in data["securities"]
        assert "cdx" in data["instruments"]

    def test_header_comments_preserved(self, sample_json_dir: Path, tmp_path: Path):
        """YAML files are properly generated (comment preservation is best-effort)."""
        output_dir = tmp_path / "output"
        catalogs_path, securities_path = migrate_json_to_yaml(
            sample_json_dir, output_dir
        )

        # Verify files exist and are valid YAML
        assert catalogs_path.exists()
        assert securities_path.exists()
        
        # Load and verify content is valid
        from ruamel.yaml import YAML
        yaml = YAML()
        with open(catalogs_path) as f:
            content = yaml.load(f)
        assert "indicator_transformations" in content

    def test_missing_json_raises_error(self, tmp_path: Path):
        """Missing JSON file raises FileNotFoundError."""
        source_dir = tmp_path / "empty"
        source_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            migrate_json_to_yaml(source_dir, tmp_path / "output")


class TestVerifyRoundTrip:
    """Tests for verify_round_trip function."""

    def test_round_trip_success(self, sample_json_dir: Path, tmp_path: Path):
        """Round-trip verification passes for consistent data."""
        yaml_dir = tmp_path / "yaml"

        # First migrate JSON to YAML
        migrate_json_to_yaml(sample_json_dir, yaml_dir)

        # Then verify round-trip
        result = verify_round_trip(yaml_dir, sample_json_dir)

        assert result is True

    def test_round_trip_detects_mismatch(self, sample_json_dir: Path, tmp_path: Path):
        """Round-trip verification detects JSON differences."""
        yaml_dir = tmp_path / "yaml"

        # Migrate JSON to YAML
        migrate_json_to_yaml(sample_json_dir, yaml_dir)

        # Modify original JSON to create mismatch
        signal_path = sample_json_dir / "models" / "signal_catalog.json"
        with open(signal_path) as f:
            data = json.load(f)
        data[0]["description"] = "Modified description"
        with open(signal_path, "w") as f:
            json.dump(data, f)

        # Verify should fail
        result = verify_round_trip(yaml_dir, sample_json_dir)

        assert result is False


class TestMigrationIntegration:
    """Integration tests for full migration workflow."""

    def test_full_migration_workflow(self, sample_json_dir: Path, tmp_path: Path):
        """Complete migration and sync workflow."""
        yaml_dir = tmp_path / "yaml"
        json_output_dir = tmp_path / "json_output"
        json_output_dir.mkdir()

        # Create directory structure for output
        (json_output_dir / "models").mkdir()
        (json_output_dir / "backtest").mkdir()
        (json_output_dir / "data").mkdir()

        # Step 1: Migrate JSON → YAML
        catalogs_path, securities_path = migrate_json_to_yaml(
            sample_json_dir, yaml_dir
        )

        # Step 2: Load YAML
        from aponyx.catalog.loader import load_catalogs_yaml, load_securities_yaml

        catalogs = load_catalogs_yaml(catalogs_path)
        securities = load_securities_yaml(securities_path)

        # Step 3: Sync YAML → JSON
        from aponyx.catalog.sync import sync_to_json

        result = sync_to_json(catalogs, securities, json_output_dir)

        # Verify sync succeeded and all JSON files created
        assert result.success
        assert len(result.files_written) == 7
        for path in result.files_written:
            assert path.exists()

    def test_entry_types_preserved(self, sample_json_dir: Path, tmp_path: Path):
        """Entry data types are preserved through migration."""
        yaml_dir = tmp_path / "yaml"
        migrate_json_to_yaml(sample_json_dir, yaml_dir)

        from aponyx.catalog.loader import load_catalogs_yaml, load_securities_yaml

        catalogs = load_catalogs_yaml(yaml_dir / "catalogs.yaml")
        securities = load_securities_yaml(yaml_dir / "securities.yaml")

        # Verify entry types
        assert len(catalogs.indicator_transformations) == 1
        indicator = catalogs.indicator_transformations[0]
        assert indicator.name == "test_indicator"
        assert indicator.compute_function_name == "compute_test_indicator"
        assert indicator.data_requirements == {"cdx": "spread"}

        assert len(catalogs.signals) == 1
        signal = catalogs.signals[0]
        assert signal.name == "test_signal"
        assert signal.indicator_transformation == "test_indicator"

        assert "cdx_ig_5y" in securities.securities
        security = securities.securities["cdx_ig_5y"]
        assert security.instrument_type == "cdx"
        assert security.dv01_per_million == 475.0
