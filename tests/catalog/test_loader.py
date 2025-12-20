"""Tests for YAML loader functions."""

from pathlib import Path

import pytest

from aponyx.catalog.loader import (
    load_catalogs_yaml,
    load_securities_yaml,
    save_catalogs_yaml,
    save_securities_yaml,
)


@pytest.fixture
def sample_catalogs_yaml(tmp_path: Path) -> Path:
    """Create a sample catalogs.yaml file."""
    content = """\
# Test catalogs file
indicator_transformations:
  - name: cdx_etf_spread_diff
    description: "CDX spread minus ETF spread"
    compute_function_name: compute_cdx_etf_spread_diff
    data_requirements:
      cdx: spread
      etf: spread
    default_securities:
      cdx: cdx_ig_5y
      etf: lqd
    output_units: basis_points
    parameters: {}
    enabled: true

score_transformations:
  - name: z_score_20d
    description: "Z-score 20d"
    transform_type: z_score
    parameters:
      window: 20
      min_periods: 10
    enabled: true

signal_transformations:
  - name: passthrough
    description: "No transformation"
    scaling: 1.0
    floor: null
    cap: null
    neutral_range: null
    enabled: true
  - name: bounded_1_5
    description: "Bounded signal"
    scaling: 1.0
    floor: -1.5
    cap: 1.5
    neutral_range: [-0.25, 0.25]
    enabled: true

signals:
  - name: cdx_etf_basis
    description: "Test signal"
    indicator_transformation: cdx_etf_spread_diff
    score_transformation: z_score_20d
    signal_transformation: passthrough
    sign_multiplier: 1
    enabled: true

strategies:
  - name: balanced
    description: "Balanced strategy"
    position_size_mm: 10.0
    sizing_mode: proportional
    stop_loss_pct: 5.0
    take_profit_pct: 10.0
    max_holding_days: null
    entry_threshold: 1.5
    enabled: true
"""
    yaml_path = tmp_path / "catalogs.yaml"
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


@pytest.fixture
def sample_securities_yaml(tmp_path: Path) -> Path:
    """Create a sample securities.yaml file."""
    content = """\
# Test securities file
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
    transaction_cost_bps: 1.5

  lqd:
    description: "LQD ETF"
    instrument_type: etf
    quote_type: price
    channels:
      price:
        bloomberg_ticker: "LQD US Equity"
        field: PX_LAST
      spread:
        bloomberg_ticker: "LQD US Equity"
        field: YAS_ISPREAD

instruments:
  cdx:
    description: "CDX indices"
    bloomberg_fields: [PX_LAST]
    field_mapping:
      PX_LAST: spread
    requires_security_metadata: true

  etf:
    description: "Credit ETFs"
    bloomberg_fields: [YAS_ISPREAD]
    field_mapping:
      YAS_ISPREAD: spread
    requires_security_metadata: true
"""
    yaml_path = tmp_path / "securities.yaml"
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


class TestLoadCatalogsYaml:
    """Tests for load_catalogs_yaml."""

    def test_load_valid_file(self, sample_catalogs_yaml: Path) -> None:
        """Test loading a valid catalogs.yaml file."""
        data = load_catalogs_yaml(sample_catalogs_yaml)

        assert len(data.indicator_transformations) == 1
        assert data.indicator_transformations[0].name == "cdx_etf_spread_diff"

        assert len(data.score_transformations) == 1
        assert data.score_transformations[0].name == "z_score_20d"

        assert len(data.signal_transformations) == 2
        assert data.signal_transformations[0].name == "passthrough"
        assert data.signal_transformations[1].neutral_range == (-0.25, 0.25)

        assert len(data.signals) == 1
        assert data.signals[0].name == "cdx_etf_basis"

        assert len(data.strategies) == 1
        assert data.strategies[0].name == "balanced"
        assert data.strategies[0].stop_loss_pct == 5.0

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_catalogs_yaml(tmp_path / "nonexistent.yaml")

    def test_preserves_raw_yaml(self, sample_catalogs_yaml: Path) -> None:
        """Test that raw YAML object is preserved."""
        data = load_catalogs_yaml(sample_catalogs_yaml)
        assert data.raw is not None
        assert "indicator_transformations" in data.raw


class TestLoadSecuritiesYaml:
    """Tests for load_securities_yaml."""

    def test_load_valid_file(self, sample_securities_yaml: Path) -> None:
        """Test loading a valid securities.yaml file."""
        data = load_securities_yaml(sample_securities_yaml)

        assert len(data.securities) == 2
        assert "cdx_ig_5y" in data.securities
        assert "lqd" in data.securities

        cdx = data.securities["cdx_ig_5y"]
        assert cdx.instrument_type == "cdx"
        assert cdx.dv01_per_million == 475.0
        assert "spread" in cdx.channels
        assert cdx.channels["spread"].field == "PX_LAST"

        assert len(data.instruments) == 2
        assert "cdx" in data.instruments
        assert data.instruments["cdx"].bloomberg_fields == ("PX_LAST",)


class TestSaveCatalogsYaml:
    """Tests for save_catalogs_yaml."""

    def test_round_trip(self, sample_catalogs_yaml: Path, tmp_path: Path) -> None:
        """Test that load -> save -> load produces same data."""
        # Load original
        data1 = load_catalogs_yaml(sample_catalogs_yaml)

        # Save to new file
        output_path = tmp_path / "output" / "catalogs.yaml"
        save_catalogs_yaml(data1, output_path)

        # Load again
        data2 = load_catalogs_yaml(output_path)

        # Compare
        assert len(data1.signals) == len(data2.signals)
        assert data1.signals[0].name == data2.signals[0].name
        assert len(data1.strategies) == len(data2.strategies)
        assert data1.strategies[0].stop_loss_pct == data2.strategies[0].stop_loss_pct


class TestSaveSecuritiesYaml:
    """Tests for save_securities_yaml."""

    def test_round_trip(self, sample_securities_yaml: Path, tmp_path: Path) -> None:
        """Test that load -> save -> load produces same data."""
        # Load original
        data1 = load_securities_yaml(sample_securities_yaml)

        # Save to new file
        output_path = tmp_path / "output" / "securities.yaml"
        save_securities_yaml(data1, output_path)

        # Load again
        data2 = load_securities_yaml(output_path)

        # Compare
        assert set(data1.securities.keys()) == set(data2.securities.keys())
        assert (
            data1.securities["cdx_ig_5y"].dv01_per_million
            == data2.securities["cdx_ig_5y"].dv01_per_million
        )
        assert set(data1.instruments.keys()) == set(data2.instruments.keys())
