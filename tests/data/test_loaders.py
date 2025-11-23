"""
Tests for data loading utilities.

Validates find_raw_file, concat_multi_security, load_instrument_from_raw,
and load_signal_required_data.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from aponyx.data.loaders import (
    find_raw_file,
    concat_multi_security,
    load_instrument_from_raw,
    load_signal_required_data,
)


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory with sample files."""
    data_dir = tmp_path / "raw" / "synthetic"
    data_dir.mkdir(parents=True)

    # Create sample parquet files with proper schemas
    dates = pd.date_range("2024-01-01", periods=3)

    # VIX file with 'level' column
    vix_df = pd.DataFrame({"level": [15.0, 16.0, 17.0]}, index=dates)
    vix_path = data_dir / "vix_abc123.parquet"
    vix_df.to_parquet(vix_path)

    # CDX security files with 'spread' and 'security' columns
    cdx_ig_df = pd.DataFrame(
        {"spread": [100.0, 101.0, 102.0], "security": ["cdx_ig_5y"] * 3}, index=dates
    )
    cdx_ig_path = data_dir / "cdx_ig_5y_def456.parquet"
    cdx_ig_df.to_parquet(cdx_ig_path)

    cdx_hy_df = pd.DataFrame(
        {"spread": [200.0, 201.0, 202.0], "security": ["cdx_hy_5y"] * 3}, index=dates
    )
    cdx_hy_path = data_dir / "cdx_hy_5y_ghi789.parquet"
    cdx_hy_df.to_parquet(cdx_hy_path)

    return data_dir


def test_find_raw_file_single_security(sample_data_dir: Path) -> None:
    """Test finding raw file for single-security instrument."""
    result = find_raw_file(sample_data_dir, "vix")

    assert result is not None
    assert result.name.startswith("vix_")
    assert result.suffix == ".parquet"


def test_find_raw_file_multi_security(sample_data_dir: Path) -> None:
    """Test finding raw file for specific security."""
    result = find_raw_file(sample_data_dir, "cdx", "cdx_ig_5y")

    assert result is not None
    assert result.name.startswith("cdx_ig_5y_")
    assert result.suffix == ".parquet"


def test_find_raw_file_not_found(sample_data_dir: Path) -> None:
    """Test finding raw file returns None when not found."""
    result = find_raw_file(sample_data_dir, "missing")

    assert result is None


def test_concat_multi_security() -> None:
    """Test concatenating multiple security DataFrames."""
    dates1 = pd.date_range("2024-01-01", periods=3)
    dates2 = pd.date_range("2024-01-02", periods=3)

    df1 = pd.DataFrame({"value": [1, 2, 3]}, index=dates1)
    df2 = pd.DataFrame({"value": [4, 5, 6]}, index=dates2)

    result = concat_multi_security([df1, df2], "CDX")

    assert len(result) == 4  # 4 unique dates (2024-01-01 through 2024-01-04)
    assert result.index.is_monotonic_increasing


def test_concat_multi_security_with_duplicates() -> None:
    """Test concatenation handles duplicates correctly."""
    dates = pd.date_range("2024-01-01", periods=3)

    df1 = pd.DataFrame({"value": [1, 2, 3]}, index=dates)
    df2 = pd.DataFrame({"value": [4, 5, 6]}, index=dates)

    result = concat_multi_security([df1, df2], "CDX")

    assert len(result) == 3  # Duplicates removed
    assert not result.index.duplicated().any()


def test_concat_multi_security_empty_list() -> None:
    """Test concatenation raises error for empty list."""
    with pytest.raises(ValueError, match="Cannot concatenate empty DataFrame list"):
        concat_multi_security([], "CDX")


def test_load_instrument_from_raw_single_security(
    sample_data_dir: Path,
) -> None:
    """Test loading single-security instrument from raw files."""
    from aponyx.data import fetch_vix

    result = load_instrument_from_raw(
        sample_data_dir,
        "vix",
        fetch_vix,
        securities=None,
    )

    assert len(result) > 0  # Validation fills in data
    assert "level" in result.columns
    assert result.index.name == "date"


def test_load_instrument_from_raw_multi_security(
    sample_data_dir: Path,
) -> None:
    """Test loading multi-security instrument from raw files."""
    from aponyx.data import fetch_cdx

    result = load_instrument_from_raw(
        sample_data_dir,
        "cdx",
        fetch_cdx,
        securities=["cdx_ig_5y", "cdx_hy_5y"],
    )

    assert len(result) > 0  # Validation fills in data
    assert "spread" in result.columns
    assert result.index.name == "date"


def test_load_instrument_from_raw_file_not_found(tmp_path: Path) -> None:
    """Test loading raises error when no files found."""
    from aponyx.data import fetch_vix

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(ValueError, match="No VIX data file found"):
        load_instrument_from_raw(
            empty_dir,
            "vix",
            fetch_vix,
            securities=None,
        )


def test_load_signal_required_data_default_securities() -> None:
    """Test loading signal data using default securities from catalog."""
    # Mock signal registry with enabled signals
    mock_signal_metadata = MagicMock()
    mock_signal_metadata.default_securities = {"cdx": "cdx_ig_5y", "etf": "lqd"}

    mock_signal_registry = MagicMock()
    mock_signal_registry.get_enabled.return_value = {
        "test_signal": mock_signal_metadata
    }

    # Mock data registry
    mock_df = pd.DataFrame(
        {"spread": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3)
    )
    mock_data_registry = MagicMock()
    mock_data_registry.load_dataset_by_security.return_value = mock_df

    # Execute
    result = load_signal_required_data(mock_signal_registry, mock_data_registry)

    # Verify
    assert "cdx" in result
    assert "etf" in result
    assert len(result) == 2
    assert mock_data_registry.load_dataset_by_security.call_count == 2


def test_load_signal_required_data_with_overrides() -> None:
    """Test loading signal data with security mapping overrides."""
    # Mock signal registry with enabled signals
    mock_signal_metadata = MagicMock()
    mock_signal_metadata.default_securities = {"cdx": "cdx_ig_5y", "etf": "lqd"}

    mock_signal_registry = MagicMock()
    mock_signal_registry.get_enabled.return_value = {
        "test_signal": mock_signal_metadata
    }

    # Mock data registry
    mock_df = pd.DataFrame(
        {"spread": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3)
    )
    mock_data_registry = MagicMock()
    mock_data_registry.load_dataset_by_security.return_value = mock_df

    # Execute with overrides
    security_mapping = {"cdx": "cdx_hy_5y", "etf": "hyg"}
    result = load_signal_required_data(
        mock_signal_registry, mock_data_registry, security_mapping=security_mapping
    )

    # Verify overrides were used
    assert "cdx" in result
    assert "etf" in result
    calls = mock_data_registry.load_dataset_by_security.call_args_list
    called_securities = [call[0][0] for call in calls]
    assert "cdx_hy_5y" in called_securities
    assert "hyg" in called_securities


def test_load_signal_required_data_multiple_signals() -> None:
    """Test loading data required by multiple enabled signals."""
    # Mock signal registry with multiple enabled signals
    signal1_metadata = MagicMock()
    signal1_metadata.default_securities = {"cdx": "cdx_ig_5y", "etf": "lqd"}

    signal2_metadata = MagicMock()
    signal2_metadata.default_securities = {"cdx": "cdx_ig_5y", "vix": "vix"}

    mock_signal_registry = MagicMock()
    mock_signal_registry.get_enabled.return_value = {
        "signal1": signal1_metadata,
        "signal2": signal2_metadata,
    }

    # Mock data registry
    mock_df = pd.DataFrame(
        {"value": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3)
    )
    mock_data_registry = MagicMock()
    mock_data_registry.load_dataset_by_security.return_value = mock_df

    # Execute
    result = load_signal_required_data(mock_signal_registry, mock_data_registry)

    # Verify all unique instruments loaded
    assert "cdx" in result
    assert "etf" in result
    assert "vix" in result
    assert len(result) == 3
