"""Unit tests for DataRegistry."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from aponyx.data.registry import DataRegistry, DatasetEntry
from aponyx.persistence.parquet_io import save_parquet


@pytest.fixture
def sample_timeseries():
    """Create sample time series data."""
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    return pd.DataFrame(
        {"spread": np.random.uniform(90, 110, 30)},
        index=dates,
    )


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directory for test data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def registry(temp_data_dir):
    """Create test registry instance."""
    registry_path = temp_data_dir / "registry.json"
    return DataRegistry(registry_path, temp_data_dir)


class TestDataRegistryInitialization:
    """Test cases for DataRegistry initialization."""

    def test_init_creates_registry_file(self, temp_data_dir):
        """Test that initialization creates registry file."""
        registry_path = temp_data_dir / "registry.json"
        registry = DataRegistry(registry_path, temp_data_dir)

        assert registry_path.exists()
        assert registry._catalog == {}

    def test_init_loads_existing_registry(self, temp_data_dir):
        """Test that initialization loads existing registry."""
        registry_path = temp_data_dir / "registry.json"

        # Create first registry and add dataset
        registry1 = DataRegistry(registry_path, temp_data_dir)
        registry1._catalog["test"] = {"instrument": "CDX.IG"}
        registry1._save()

        # Load existing registry
        registry2 = DataRegistry(registry_path, temp_data_dir)
        assert "test" in registry2._catalog
        assert registry2._catalog["test"]["instrument"] == "CDX.IG"

    def test_init_creates_data_directory(self, tmp_path):
        """Test that initialization creates data directory if needed."""
        data_dir = tmp_path / "nonexistent" / "data"
        registry_path = tmp_path / "registry.json"

        DataRegistry(registry_path, data_dir)
        assert data_dir.exists()


class TestRegisterDataset:
    """Test cases for register_dataset method."""

    def test_register_basic(self, registry, sample_timeseries, temp_data_dir):
        """Test basic dataset registration."""
        file_path = temp_data_dir / "cdx_ig_5y.parquet"
        save_parquet(sample_timeseries, file_path)

        registry.register_dataset(
            name="cdx_ig_5y",
            file_path=file_path,
            instrument="CDX.NA.IG",
            tenor="5Y",
        )

        info = registry.get_dataset_info("cdx_ig_5y")
        assert info["instrument"] == "CDX.NA.IG"
        assert info["tenor"] == "5Y"
        assert info["row_count"] == 30

    def test_register_with_metadata(self, registry, sample_timeseries, temp_data_dir):
        """Test registration with additional metadata."""
        file_path = temp_data_dir / "vix.parquet"
        save_parquet(sample_timeseries, file_path)

        metadata = {"source": "CBOE", "frequency": "daily"}
        registry.register_dataset(
            name="vix_index",
            file_path=file_path,
            instrument="VIX",
            metadata=metadata,
        )

        info = registry.get_dataset_info("vix_index")
        assert info["metadata"]["source"] == "CBOE"
        assert info["metadata"]["frequency"] == "daily"

    def test_register_extracts_date_range(self, registry, sample_timeseries, temp_data_dir):
        """Test that registration extracts date range from data."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries, file_path)

        registry.register_dataset(
            name="test",
            file_path=file_path,
            instrument="TEST",
        )

        info = registry.get_dataset_info("test")
        assert info["start_date"] == "2024-01-01T00:00:00"
        assert info["end_date"] == "2024-01-30T00:00:00"

    def test_register_nonexistent_file(self, registry, temp_data_dir):
        """Test registering non-existent file stores path but no stats."""
        file_path = temp_data_dir / "future.parquet"

        registry.register_dataset(
            name="future",
            file_path=file_path,
            instrument="FUTURE",
        )

        info = registry.get_dataset_info("future")
        assert info["instrument"] == "FUTURE"
        assert info["start_date"] is None
        assert info["end_date"] is None
        assert info["row_count"] is None

    def test_register_overwrites_existing(self, registry, sample_timeseries, temp_data_dir):
        """Test that re-registering updates existing entry."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries, file_path)

        registry.register_dataset(name="test", file_path=file_path, instrument="INST1")
        registry.register_dataset(name="test", file_path=file_path, instrument="INST2")

        info = registry.get_dataset_info("test")
        assert info["instrument"] == "INST2"


class TestGetDatasetInfo:
    """Test cases for get_dataset_info method."""

    def test_get_existing_dataset(self, registry, sample_timeseries, temp_data_dir):
        """Test retrieving existing dataset info."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries, file_path)
        registry.register_dataset(name="test", file_path=file_path, instrument="TEST")

        info = registry.get_dataset_info("test")
        assert isinstance(info, dict)
        assert info["instrument"] == "TEST"

    def test_get_nonexistent_dataset_raises(self, registry):
        """Test that getting nonexistent dataset raises KeyError."""
        with pytest.raises(KeyError, match="Dataset 'nonexistent' not found"):
            registry.get_dataset_info("nonexistent")

    def test_get_returns_copy(self, registry, sample_timeseries, temp_data_dir):
        """Test that get_dataset_info returns a copy, not reference."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries, file_path)
        registry.register_dataset(name="test", file_path=file_path, instrument="TEST")

        info1 = registry.get_dataset_info("test")
        info1["instrument"] = "MODIFIED"

        info2 = registry.get_dataset_info("test")
        assert info2["instrument"] == "TEST"  # Not modified


class TestListDatasets:
    """Test cases for list_datasets method."""

    def test_list_all_datasets(self, registry, sample_timeseries, temp_data_dir):
        """Test listing all registered datasets."""
        for name in ["cdx_ig", "cdx_hy", "vix"]:
            file_path = temp_data_dir / f"{name}.parquet"
            save_parquet(sample_timeseries, file_path)
            registry.register_dataset(name=name, file_path=file_path, instrument=name.upper())

        datasets = registry.list_datasets()
        assert len(datasets) == 3
        assert sorted(datasets) == datasets  # Verify sorted

    def test_list_filtered_by_instrument(self, registry, sample_timeseries, temp_data_dir):
        """Test filtering datasets by instrument."""
        registry.register_dataset(
            name="cdx_ig_5y",
            file_path=temp_data_dir / "cdx_ig_5y.parquet",
            instrument="CDX.NA.IG",
            tenor="5Y",
        )
        registry.register_dataset(
            name="cdx_ig_10y",
            file_path=temp_data_dir / "cdx_ig_10y.parquet",
            instrument="CDX.NA.IG",
            tenor="10Y",
        )
        registry.register_dataset(
            name="vix",
            file_path=temp_data_dir / "vix.parquet",
            instrument="VIX",
        )

        cdx_datasets = registry.list_datasets(instrument="CDX.NA.IG")
        assert len(cdx_datasets) == 2
        assert "vix" not in cdx_datasets

    def test_list_filtered_by_tenor(self, registry, temp_data_dir):
        """Test filtering datasets by tenor."""
        registry.register_dataset(
            name="cdx_ig_5y",
            file_path=temp_data_dir / "cdx_ig_5y.parquet",
            instrument="CDX.NA.IG",
            tenor="5Y",
        )
        registry.register_dataset(
            name="cdx_hy_5y",
            file_path=temp_data_dir / "cdx_hy_5y.parquet",
            instrument="CDX.NA.HY",
            tenor="5Y",
        )
        registry.register_dataset(
            name="cdx_ig_10y",
            file_path=temp_data_dir / "cdx_ig_10y.parquet",
            instrument="CDX.NA.IG",
            tenor="10Y",
        )

        datasets_5y = registry.list_datasets(tenor="5Y")
        assert len(datasets_5y) == 2
        assert "cdx_ig_10y" not in datasets_5y

    def test_list_empty_registry(self, registry):
        """Test listing datasets from empty registry."""
        datasets = registry.list_datasets()
        assert datasets == []


class TestUpdateDatasetStats:
    """Test cases for update_dataset_stats method."""

    def test_update_stats(self, registry, sample_timeseries, temp_data_dir):
        """Test updating dataset statistics."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries[:10], file_path)  # Save partial data
        registry.register_dataset(name="test", file_path=file_path, instrument="TEST")

        # Update file with more data
        save_parquet(sample_timeseries, file_path)
        registry.update_dataset_stats("test")

        info = registry.get_dataset_info("test")
        assert info["row_count"] == 30
        assert "last_updated" in info

    def test_update_nonexistent_dataset_raises(self, registry):
        """Test that updating nonexistent dataset raises KeyError."""
        with pytest.raises(KeyError, match="Dataset 'nonexistent' not found"):
            registry.update_dataset_stats("nonexistent")

    def test_update_missing_file_raises(self, registry, temp_data_dir):
        """Test that updating dataset with missing file raises FileNotFoundError."""
        file_path = temp_data_dir / "deleted.parquet"
        registry.register_dataset(name="test", file_path=file_path, instrument="TEST")

        with pytest.raises(FileNotFoundError):
            registry.update_dataset_stats("test")


class TestRemoveDataset:
    """Test cases for remove_dataset method."""

    def test_remove_dataset(self, registry, sample_timeseries, temp_data_dir):
        """Test removing dataset from registry."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries, file_path)
        registry.register_dataset(name="test", file_path=file_path, instrument="TEST")

        registry.remove_dataset("test")

        with pytest.raises(KeyError):
            registry.get_dataset_info("test")
        assert file_path.exists()  # File not deleted by default

    def test_remove_dataset_with_file_deletion(self, registry, sample_timeseries, temp_data_dir):
        """Test removing dataset and deleting file."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries, file_path)
        registry.register_dataset(name="test", file_path=file_path, instrument="TEST")

        registry.remove_dataset("test", delete_file=True)

        assert not file_path.exists()

    def test_remove_nonexistent_dataset_raises(self, registry):
        """Test that removing nonexistent dataset raises KeyError."""
        with pytest.raises(KeyError, match="Dataset 'nonexistent' not found"):
            registry.remove_dataset("nonexistent")


class TestRegistryRepr:
    """Test cases for DataRegistry string representation."""

    def test_repr(self, registry, temp_data_dir):
        """Test registry string representation."""
        repr_str = repr(registry)
        assert "DataRegistry" in repr_str
        assert "datasets=0" in repr_str

        # Add dataset and check updated count
        registry.register_dataset(
            name="test",
            file_path=temp_data_dir / "test.parquet",
            instrument="TEST",
        )
        repr_str = repr(registry)
        assert "datasets=1" in repr_str


class TestDatasetEntry:
    """Test cases for DatasetEntry dataclass."""

    def test_dataclass_creation(self):
        """Test creating DatasetEntry with all fields."""
        entry = DatasetEntry(
            instrument="CDX.NA.IG",
            file_path="data/cdx_ig_5y.parquet",
            registered_at="2024-10-25T14:30:00",
            tenor="5Y",
            start_date="2024-01-01T00:00:00",
            end_date="2024-10-25T00:00:00",
            row_count=215,
            metadata={"source": "Bloomberg"},
        )

        assert entry.instrument == "CDX.NA.IG"
        assert entry.tenor == "5Y"
        assert entry.row_count == 215
        assert entry.metadata["source"] == "Bloomberg"

    def test_dataclass_defaults(self):
        """Test DatasetEntry with default values."""
        entry = DatasetEntry(
            instrument="VIX",
            file_path="data/vix.parquet",
            registered_at="2024-10-25T14:30:00",
        )

        assert entry.instrument == "VIX"
        assert entry.tenor is None
        assert entry.start_date is None
        assert entry.end_date is None
        assert entry.row_count is None
        assert entry.last_updated is None
        assert entry.metadata == {}

    def test_to_dict(self):
        """Test converting DatasetEntry to dictionary."""
        entry = DatasetEntry(
            instrument="CDX.NA.IG",
            file_path="data/test.parquet",
            registered_at="2024-10-25T14:30:00",
            tenor="5Y",
            row_count=100,
        )

        data = entry.to_dict()

        assert isinstance(data, dict)
        assert data["instrument"] == "CDX.NA.IG"
        assert data["tenor"] == "5Y"
        assert data["row_count"] == 100
        assert data["start_date"] is None

    def test_from_dict(self):
        """Test creating DatasetEntry from dictionary."""
        data = {
            "instrument": "CDX.NA.HY",
            "file_path": "data/cdx_hy.parquet",
            "registered_at": "2024-10-25T14:30:00",
            "tenor": "5Y",
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-10-25T00:00:00",
            "row_count": 200,
            "last_updated": None,
            "metadata": {"frequency": "daily"},
        }

        entry = DatasetEntry.from_dict(data)

        assert entry.instrument == "CDX.NA.HY"
        assert entry.tenor == "5Y"
        assert entry.row_count == 200
        assert entry.metadata["frequency"] == "daily"

    def test_roundtrip_dict_conversion(self):
        """Test converting to dict and back preserves data."""
        original = DatasetEntry(
            instrument="VIX",
            file_path="data/vix.parquet",
            registered_at="2024-10-25T14:30:00",
            row_count=500,
            metadata={"source": "CBOE", "type": "index"},
        )

        data = original.to_dict()
        restored = DatasetEntry.from_dict(data)

        assert restored.instrument == original.instrument
        assert restored.file_path == original.file_path
        assert restored.row_count == original.row_count
        assert restored.metadata == original.metadata


class TestGetDatasetEntry:
    """Test cases for get_dataset_entry method."""

    def test_get_dataset_entry_basic(self, registry, sample_timeseries, temp_data_dir):
        """Test retrieving dataset as DatasetEntry object."""
        file_path = temp_data_dir / "cdx_ig_5y.parquet"
        save_parquet(sample_timeseries, file_path)

        registry.register_dataset(
            name="cdx_ig_5y",
            file_path=file_path,
            instrument="CDX.NA.IG",
            tenor="5Y",
        )

        entry = registry.get_dataset_entry("cdx_ig_5y")

        assert isinstance(entry, DatasetEntry)
        assert entry.instrument == "CDX.NA.IG"
        assert entry.tenor == "5Y"
        assert entry.row_count == 30

    def test_get_dataset_entry_with_metadata(self, registry, sample_timeseries, temp_data_dir):
        """Test retrieving dataset with metadata."""
        file_path = temp_data_dir / "vix.parquet"
        save_parquet(sample_timeseries, file_path)

        metadata = {"source": "CBOE", "frequency": "daily"}
        registry.register_dataset(
            name="vix_index",
            file_path=file_path,
            instrument="VIX",
            metadata=metadata,
        )

        entry = registry.get_dataset_entry("vix_index")

        assert entry.instrument == "VIX"
        assert entry.tenor is None
        assert entry.metadata["source"] == "CBOE"
        assert entry.metadata["frequency"] == "daily"

    def test_get_dataset_entry_nonexistent_raises(self, registry):
        """Test that getting nonexistent entry raises KeyError."""
        with pytest.raises(KeyError, match="Dataset 'nonexistent' not found"):
            registry.get_dataset_entry("nonexistent")

    def test_get_dataset_entry_type_safety(self, registry, sample_timeseries, temp_data_dir):
        """Test that DatasetEntry provides type-safe attribute access."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries, file_path)

        registry.register_dataset(
            name="test",
            file_path=file_path,
            instrument="TEST",
            tenor="5Y",
        )

        entry = registry.get_dataset_entry("test")

        # Test attribute access (would give IDE autocomplete)
        assert hasattr(entry, "instrument")
        assert hasattr(entry, "tenor")
        assert hasattr(entry, "file_path")
        assert hasattr(entry, "row_count")
        assert hasattr(entry, "metadata")

    def test_get_dataset_entry_vs_get_dataset_info(
        self, registry, sample_timeseries, temp_data_dir
    ):
        """Test that both methods return equivalent data."""
        file_path = temp_data_dir / "test.parquet"
        save_parquet(sample_timeseries, file_path)

        registry.register_dataset(
            name="test",
            file_path=file_path,
            instrument="TEST",
            tenor="5Y",
        )

        entry = registry.get_dataset_entry("test")
        info = registry.get_dataset_info("test")

        # Convert entry to dict and compare
        assert entry.to_dict() == info
