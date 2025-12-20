"""Tests for CatalogManager."""

from pathlib import Path

import pytest

from aponyx.catalog.entries import SignalEntry
from aponyx.catalog.manager import CatalogManager


@pytest.fixture
def sample_yaml_files(tmp_path: Path) -> Path:
    """Create sample YAML files in a temporary directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    catalogs_content = """\
# Test catalogs
indicator_transformations:
  - name: cdx_etf_spread_diff
    description: "Test indicator"
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
    stop_loss_pct: 5.0
    take_profit_pct: 10.0
    max_holding_days: null
    entry_threshold: 1.5
    enabled: true
"""
    (config_dir / "catalogs.yaml").write_text(catalogs_content, encoding="utf-8")

    securities_content = """\
# Test securities
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


class TestCatalogManagerInit:
    """Tests for CatalogManager initialization."""

    def test_init_with_valid_dir(self, sample_yaml_files: Path) -> None:
        """Test initialization with valid config directory."""
        manager = CatalogManager(sample_yaml_files)
        assert manager.config_dir == sample_yaml_files

    def test_init_with_missing_dir(self, tmp_path: Path) -> None:
        """Test initialization with missing directory."""
        with pytest.raises(FileNotFoundError):
            CatalogManager(tmp_path / "nonexistent")


class TestCatalogManagerLoad:
    """Tests for CatalogManager.load()."""

    def test_load_success(self, sample_yaml_files: Path) -> None:
        """Test successful loading."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        assert manager.catalogs_data is not None
        assert manager.securities_data is not None
        assert len(manager.catalogs_data.signals) == 1

    def test_operations_before_load_raise(self, sample_yaml_files: Path) -> None:
        """Test that operations before load() raise RuntimeError."""
        manager = CatalogManager(sample_yaml_files)

        with pytest.raises(RuntimeError, match="load\\(\\) must be called"):
            manager.validate()


class TestCatalogManagerGet:
    """Tests for CatalogManager.get()."""

    def test_get_signal(self, sample_yaml_files: Path) -> None:
        """Test getting a signal."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        signal = manager.get("signals", "test_signal")
        assert signal.name == "test_signal"

    def test_get_security(self, sample_yaml_files: Path) -> None:
        """Test getting a security."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        security = manager.get("securities", "cdx_ig_5y")
        assert security.name == "cdx_ig_5y"
        assert security.dv01_per_million == 475.0

    def test_get_unknown_category(self, sample_yaml_files: Path) -> None:
        """Test getting from unknown category."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        with pytest.raises(KeyError, match="Unknown category"):
            manager.get("unknown", "test")

    def test_get_unknown_name(self, sample_yaml_files: Path) -> None:
        """Test getting unknown entry."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        with pytest.raises(KeyError, match="not found"):
            manager.get("signals", "nonexistent")


class TestCatalogManagerListItems:
    """Tests for CatalogManager.list_items()."""

    def test_list_signals(self, sample_yaml_files: Path) -> None:
        """Test listing signals."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        items = manager.list_items("signals")
        assert "test_signal" in items

    def test_list_securities(self, sample_yaml_files: Path) -> None:
        """Test listing securities."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        items = manager.list_items("securities")
        assert "cdx_ig_5y" in items
        assert "lqd" in items


class TestCatalogManagerAddRemove:
    """Tests for CatalogManager.add() and remove()."""

    def test_add_signal(self, sample_yaml_files: Path) -> None:
        """Test adding a signal."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        new_signal = SignalEntry(
            name="new_signal",
            description="New",
            indicator_transformation="cdx_etf_spread_diff",
            score_transformation="z_score_20d",
            signal_transformation="passthrough",
        )

        manager.add("signals", new_signal)
        assert "new_signal" in manager.list_items("signals")

    def test_add_duplicate_raises(self, sample_yaml_files: Path) -> None:
        """Test adding duplicate raises ValueError."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        new_signal = SignalEntry(
            name="test_signal",  # Already exists
            description="Duplicate",
            indicator_transformation="cdx_etf_spread_diff",
            score_transformation="z_score_20d",
            signal_transformation="passthrough",
        )

        with pytest.raises(ValueError, match="already exists"):
            manager.add("signals", new_signal)

    def test_remove_signal(self, sample_yaml_files: Path) -> None:
        """Test removing a signal."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        manager.remove("signals", "test_signal")
        assert "test_signal" not in manager.list_items("signals")

    def test_remove_nonexistent_raises(self, sample_yaml_files: Path) -> None:
        """Test removing nonexistent entry raises KeyError."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        with pytest.raises(KeyError, match="not found"):
            manager.remove("signals", "nonexistent")


class TestCatalogManagerValidate:
    """Tests for CatalogManager.validate()."""

    def test_validate_passes(self, sample_yaml_files: Path) -> None:
        """Test validation passes for valid data."""
        manager = CatalogManager(sample_yaml_files)
        manager.load()

        result = manager.validate()
        assert result.passed
        assert result.summary is not None


class TestCatalogManagerSave:
    """Tests for CatalogManager.save()."""

    def test_save_round_trip(self, sample_yaml_files: Path) -> None:
        """Test save preserves data on round-trip."""
        manager1 = CatalogManager(sample_yaml_files)
        manager1.load()

        # Add a new signal
        new_signal = SignalEntry(
            name="added_signal",
            description="Added",
            indicator_transformation="cdx_etf_spread_diff",
            score_transformation="z_score_20d",
            signal_transformation="passthrough",
        )
        manager1.add("signals", new_signal)
        manager1.save()

        # Load again and verify
        manager2 = CatalogManager(sample_yaml_files)
        manager2.load()

        assert "added_signal" in manager2.list_items("signals")
        assert "test_signal" in manager2.list_items("signals")  # Original still there
