"""Tests for catalog CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from aponyx.cli.commands.catalog import catalog


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_config_dir(tmp_path: Path) -> Path:
    """Create sample config directory with YAML files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    catalogs_content = """\
indicator_transformations:
  - name: cdx_etf_spread_diff
    description: "Test"
    compute_function_name: compute_cdx_etf_spread_diff
    data_requirements:
      cdx: spread
    default_securities:
      cdx: cdx_ig_5y
    output_units: basis_points
    parameters: {}
    enabled: true

score_transformations:
  - name: z_score_20d
    description: "Z-score"
    transform_type: z_score
    parameters:
      window: 20
    enabled: true

signal_transformations:
  - name: passthrough
    description: "No transform"
    scaling: 1.0
    floor: null
    cap: null
    neutral_range: null
    enabled: true

signals:
  - name: test_signal
    description: "Test"
    indicator_transformation: cdx_etf_spread_diff
    score_transformation: z_score_20d
    signal_transformation: passthrough
    sign_multiplier: 1
    enabled: true

strategies:
  - name: balanced
    description: "Balanced"
    position_size_mm: 10.0
    sizing_mode: proportional
    enabled: true
"""
    (config_dir / "catalogs.yaml").write_text(catalogs_content, encoding="utf-8")

    securities_content = """\
securities:
  cdx_ig_5y:
    description: "CDX IG 5Y"
    instrument_type: cdx
    quote_type: spread
    channels:
      spread:
        bloomberg_ticker: "CDX IG CDSI GEN 5Y Corp"
        field: PX_LAST
    dv01_per_million: 475.0

instruments:
  cdx:
    description: "CDX"
    bloomberg_fields: [PX_LAST]
    field_mapping:
      PX_LAST: spread
    requires_security_metadata: true
"""
    (config_dir / "securities.yaml").write_text(securities_content, encoding="utf-8")

    return config_dir


class TestCatalogValidateCommand:
    """Tests for 'aponyx catalog validate' command."""

    def test_validate_help(self, runner: CliRunner) -> None:
        """Test that help is available."""
        result = runner.invoke(catalog, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate catalog YAML files" in result.output

    def test_validate_missing_config(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test validate with missing config directory."""
        # Point PROJECT_ROOT to temp directory
        monkeypatch.setattr("aponyx.cli.commands.catalog.PROJECT_ROOT", tmp_path)

        result = runner.invoke(catalog, ["validate"])
        assert result.exit_code == 1
        assert "Config directory not found" in result.output


class TestCatalogSyncCommand:
    """Tests for 'aponyx catalog sync' command."""

    def test_sync_help(self, runner: CliRunner) -> None:
        """Test that help is available."""
        result = runner.invoke(catalog, ["sync", "--help"])
        assert result.exit_code == 0
        assert "Sync YAML catalogs to JSON" in result.output
        assert "--dry-run" in result.output


class TestCatalogMigrateCommand:
    """Tests for 'aponyx catalog migrate' command."""

    def test_migrate_help(self, runner: CliRunner) -> None:
        """Test that help is available."""
        result = runner.invoke(catalog, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "Migrate JSON catalogs to YAML" in result.output
        assert "--force" in result.output

    def test_migrate_existing_files_without_force(
        self,
        runner: CliRunner,
        sample_config_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test migrate fails if YAML files exist and --force not used."""
        # Move config dir to where PROJECT_ROOT/config would be
        import shutil

        project_root = tmp_path / "project"
        project_root.mkdir()
        shutil.move(str(sample_config_dir), str(project_root / "config"))

        monkeypatch.setattr("aponyx.cli.commands.catalog.PROJECT_ROOT", project_root)

        result = runner.invoke(catalog, ["migrate"])
        assert result.exit_code == 1
        assert "YAML files already exist" in result.output
        assert "--force" in result.output
