"""
Unit tests for signal registry and metadata.
"""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

from aponyx.models.registry import SignalRegistry, SignalMetadata


@pytest.fixture
def sample_catalog_data() -> list[dict]:
    """Sample signal catalog data using real compute functions."""
    return [
        {
            "name": "test_signal_a",
            "description": "Test signal A",
            "compute_function_name": "compute_spread_momentum",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
        },
        {
            "name": "test_signal_b",
            "description": "Test signal B",
            "compute_function_name": "compute_cdx_vix_gap",
            "data_requirements": {"cdx": "spread", "vix": "level"},
            "arg_mapping": ["cdx", "vix"],
            "enabled": True,
        },
    ]


@pytest.fixture
def temp_catalog_file(sample_catalog_data: list[dict]):
    """Create temporary catalog file."""
    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "test_catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(sample_catalog_data, f)
        yield catalog_path


def test_signal_metadata_creation() -> None:
    """Test creating SignalMetadata."""
    metadata = SignalMetadata(
        name="test_signal",
        description="Test signal",
        compute_function_name="compute_test",
        data_requirements={"cdx": "spread"},
        arg_mapping=["cdx"],
        enabled=True,
    )

    assert metadata.name == "test_signal"
    assert metadata.compute_function_name == "compute_test"
    assert metadata.enabled is True


def test_signal_metadata_validates_name() -> None:
    """Test that SignalMetadata validates name."""
    with pytest.raises(ValueError, match="Signal name cannot be empty"):
        SignalMetadata(
            name="",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )


def test_signal_metadata_validates_function_name() -> None:
    """Test that SignalMetadata validates compute function name."""
    with pytest.raises(ValueError, match="Compute function name cannot be empty"):
        SignalMetadata(
            name="test",
            description="Test",
            compute_function_name="",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )


def test_signal_metadata_validates_arg_mapping() -> None:
    """Test that SignalMetadata validates arg_mapping."""
    # Empty arg_mapping
    with pytest.raises(ValueError, match="arg_mapping cannot be empty"):
        SignalMetadata(
            name="test",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=[],
        )

    # arg_mapping contains key not in data_requirements
    with pytest.raises(ValueError, match="arg_mapping contains keys not in data_requirements"):
        SignalMetadata(
            name="test",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx", "vix"],  # vix not in data_requirements
        )


def test_signal_registry_loads_catalog(temp_catalog_file: Path) -> None:
    """Test that SignalRegistry loads catalog on initialization."""
    registry = SignalRegistry(temp_catalog_file)

    signals = registry.list_all()
    assert len(signals) == 2
    assert "test_signal_a" in signals
    assert "test_signal_b" in signals


def test_signal_registry_file_not_found() -> None:
    """Test that SignalRegistry raises error for missing catalog."""
    with pytest.raises(FileNotFoundError, match="Signal catalog not found"):
        SignalRegistry("nonexistent_catalog.json")


def test_signal_registry_get_metadata(temp_catalog_file: Path) -> None:
    """Test retrieving signal metadata."""
    registry = SignalRegistry(temp_catalog_file)

    metadata = registry.get_metadata("test_signal_a")
    assert metadata.name == "test_signal_a"
    assert metadata.compute_function_name == "compute_spread_momentum"
    assert metadata.data_requirements == {"cdx": "spread"}
    assert metadata.arg_mapping == ["cdx"]


def test_signal_registry_get_metadata_not_found(temp_catalog_file: Path) -> None:
    """Test that get_metadata raises KeyError for unknown signal."""
    registry = SignalRegistry(temp_catalog_file)

    with pytest.raises(KeyError, match="Signal 'nonexistent' not found"):
        registry.get_metadata("nonexistent")


def test_signal_registry_get_enabled(temp_catalog_file: Path) -> None:
    """Test retrieving enabled signals."""
    registry = SignalRegistry(temp_catalog_file)

    enabled = registry.get_enabled()
    assert len(enabled) == 2
    assert all(meta.enabled for meta in enabled.values())


def test_signal_registry_get_enabled_filters_disabled() -> None:
    """Test that get_enabled filters out disabled signals."""
    catalog_data = [
        {
            "name": "enabled_signal",
            "description": "Enabled",
            "compute_function_name": "compute_spread_momentum",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
        },
        {
            "name": "disabled_signal",
            "description": "Disabled",
            "compute_function_name": "compute_cdx_etf_basis",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": False,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        registry = SignalRegistry(catalog_path)
        enabled = registry.get_enabled()

        assert len(enabled) == 1
        assert "enabled_signal" in enabled
        assert "disabled_signal" not in enabled


def test_signal_registry_save_catalog(temp_catalog_file: Path) -> None:
    """Test saving catalog to file."""
    registry = SignalRegistry(temp_catalog_file)

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output_catalog.json"
        registry.save_catalog(output_path)

        assert output_path.exists()

        # Verify content
        with open(output_path) as f:
            saved_data = json.load(f)

        assert len(saved_data) == 2
        assert saved_data[0]["name"] == "test_signal_a"
        assert saved_data[1]["name"] == "test_signal_b"


def test_signal_registry_duplicate_names_raises_error() -> None:
    """Test that duplicate signal names in catalog raise error."""
    catalog_data = [
        {
            "name": "duplicate",
            "description": "First",
            "compute_function_name": "compute_a",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
        },
        {
            "name": "duplicate",  # Same name
            "description": "Second",
            "compute_function_name": "compute_b",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        with pytest.raises(ValueError, match="Duplicate signal name"):
            SignalRegistry(catalog_path)


def test_signal_registry_invalid_catalog_format() -> None:
    """Test that invalid catalog format raises error."""
    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"

        # Write dict instead of list
        with open(catalog_path, "w") as f:
            json.dump({"not": "a list"}, f)

        with pytest.raises(ValueError, match="Signal catalog must be a JSON array"):
            SignalRegistry(catalog_path)


def test_signal_registry_invalid_metadata_entry() -> None:
    """Test that invalid metadata entry raises error."""
    catalog_data = [
        {
            "name": "missing_fields",
            # Missing required fields
        }
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        with pytest.raises(ValueError, match="Invalid signal metadata"):
            SignalRegistry(catalog_path)
