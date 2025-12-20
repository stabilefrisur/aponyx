"""Test raw data storage functionality."""

import pandas as pd

from aponyx.data.fetch import save_to_raw
from aponyx.data.registry import DataRegistry


def test_save_to_raw_creates_directory(tmp_path):
    """Test that save_to_raw creates provider subdirectories."""
    df = pd.DataFrame(
        {"value": [1, 2, 3]},
        index=pd.date_range("2024-01-01", periods=3),
    )

    result = save_to_raw(df, "bloomberg", "test_instrument", tmp_path)

    assert result.exists()
    assert result.parent == tmp_path / "bloomberg"
    assert result.name.startswith("test_instrument_")
    assert result.name.endswith(".parquet")


def test_save_to_raw_sanitizes_filename(tmp_path):
    """Test that instrument names are sanitized for filenames."""
    df = pd.DataFrame(
        {"value": [1, 2, 3]},
        index=pd.date_range("2024-01-01", periods=3),
    )

    result = save_to_raw(df, "bloomberg", "CDX.IG.5Y", tmp_path)

    assert result.name.startswith("CDX_IG_5Y_")
    assert result.name.endswith(".parquet")
    assert "." not in result.stem.split("_")[0]  # Dots replaced with underscores


def test_save_to_raw_handles_slashes(tmp_path):
    """Test that slashes in instrument names are sanitized."""
    df = pd.DataFrame(
        {"value": [1, 2, 3]},
        index=pd.date_range("2024-01-01", periods=3),
    )

    result = save_to_raw(df, "bloomberg", "path/to/instrument", tmp_path)

    assert result.name.startswith("path_to_instrument_")
    assert result.name.endswith(".parquet")
    assert "/" not in result.name


def test_save_to_raw_registers_dataset(tmp_path):
    """Test that save_to_raw registers dataset in registry."""
    df = pd.DataFrame(
        {"value": [1, 2, 3]},
        index=pd.date_range("2024-01-01", periods=3),
    )
    registry_path = tmp_path / "registry.json"
    registry = DataRegistry(registry_path, tmp_path)

    save_to_raw(df, "bloomberg", "test", tmp_path, registry)

    datasets = registry.list_datasets()
    # Dataset name includes hash suffix now
    matching_datasets = [d for d in datasets if d.startswith("raw_bloomberg_test_")]
    assert len(matching_datasets) == 1

    entry = registry.get_dataset_entry(matching_datasets[0])
    assert entry.instrument == "test"
    assert entry.metadata["provider"] == "bloomberg"
    assert "stored_at" in entry.metadata


def test_save_to_raw_without_registry(tmp_path):
    """Test that save_to_raw works without registry."""
    df = pd.DataFrame(
        {"value": [1, 2, 3]},
        index=pd.date_range("2024-01-01", periods=3),
    )

    result = save_to_raw(df, "synthetic", "test", tmp_path, registry=None)

    assert result.exists()
    assert result.parent == tmp_path / "synthetic"


def test_save_to_raw_multiple_providers(tmp_path):
    """Test that multiple providers can save to same raw directory."""
    df = pd.DataFrame(
        {"value": [1, 2, 3]},
        index=pd.date_range("2024-01-01", periods=3),
    )

    bloomberg_path = save_to_raw(df, "bloomberg", "cdx", tmp_path)
    synthetic_path = save_to_raw(df, "synthetic", "cdx", tmp_path)

    assert bloomberg_path != synthetic_path
    assert bloomberg_path.parent.name == "bloomberg"
    assert synthetic_path.parent.name == "synthetic"
    assert bloomberg_path.exists()
    assert synthetic_path.exists()


def test_save_to_raw_overwrites_existing(tmp_path):
    """Test that save_to_raw creates separate files for each save."""
    import time

    df1 = pd.DataFrame(
        {"value": [1, 2, 3]},
        index=pd.date_range("2024-01-01", periods=3),
    )
    df2 = pd.DataFrame(
        {"value": [4, 5, 6, 7]},
        index=pd.date_range("2024-01-01", periods=4),
    )

    path1 = save_to_raw(df1, "bloomberg", "test", tmp_path)
    # Small delay to ensure different timestamp
    time.sleep(1.1)
    path2 = save_to_raw(df2, "bloomberg", "test", tmp_path)

    # Different timestamps create different files
    assert path1 != path2
    assert path1.parent == path2.parent

    # Verify both files exist with correct data
    from aponyx.persistence import load_parquet

    loaded1 = load_parquet(path1)
    assert len(loaded1) == 3
    assert loaded1["value"].tolist() == [1, 2, 3]

    loaded2 = load_parquet(path2)
    assert len(loaded2) == 4
    assert loaded2["value"].tolist() == [4, 5, 6, 7]
