"""
Tests for data loading utilities.

Validates load_instrument_from_raw and load_signal_required_data.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from aponyx.data.loaders import (
    load_instrument_from_raw,
    load_signal_required_data,
)


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory with sample files and registry."""
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

    # Create registry.json with security-to-file mappings
    registry = {
        "vix": "vix_abc123.parquet",
        "cdx_ig_5y": "cdx_ig_5y_def456.parquet",
        "cdx_hy_5y": "cdx_hy_5y_ghi789.parquet",
    }
    registry_path = data_dir / "registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    return data_dir


def test_load_instrument_from_raw_single_security(
    sample_data_dir: Path,
) -> None:
    """Test loading single-security instrument from raw files."""
    from aponyx.data import fetch_security_data, UsagePurpose

    def fetch_vix_wrapper(source, security=None, **kwargs):
        """Wrapper to match old function signature."""
        # Ignore security param, always use "vix"
        kwargs.pop('security', None)
        return fetch_security_data(source, "vix", purpose=UsagePurpose.INDICATOR, **kwargs)

    result = load_instrument_from_raw(
        sample_data_dir,
        "vix",
        fetch_vix_wrapper,
        securities=None,
    )

    assert len(result) > 0  # Validation fills in data
    assert "level" in result.columns
    assert isinstance(result.index, pd.DatetimeIndex)


def test_load_instrument_from_raw_multi_security(
    sample_data_dir: Path,
) -> None:
    """Test loading multi-security instrument from raw files."""
    from aponyx.data import fetch_security_data, UsagePurpose

    def fetch_cdx_wrapper(source, security=None, **kwargs):
        """Wrapper to match old function signature."""
        return fetch_security_data(source, security, purpose=UsagePurpose.INDICATOR, **kwargs)

    result = load_instrument_from_raw(
        sample_data_dir,
        "cdx",
        fetch_cdx_wrapper,
        securities=["cdx_ig_5y", "cdx_hy_5y"],
    )

    assert len(result) > 0  # Validation fills in data
    assert "spread" in result.columns
    assert isinstance(result.index, pd.DatetimeIndex)


def test_load_instrument_from_raw_file_not_found(tmp_path: Path) -> None:
    """Test loading raises error when registry doesn't exist."""
    from aponyx.data import fetch_security_data, UsagePurpose

    def fetch_vix_wrapper(source, **kwargs):
        """Wrapper to match old function signature."""
        return fetch_security_data(source, "vix", purpose=UsagePurpose.INDICATOR, **kwargs)

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="registry.json"):
        load_instrument_from_raw(
            empty_dir,
            "vix",
            fetch_vix_wrapper,
            securities=None,
        )


def test_load_signal_required_data_default_securities() -> None:
    """Test loading signal data using default securities from indicator catalog."""
    # Mock signal metadata (references indicator transformation)
    mock_signal_metadata = MagicMock()
    mock_signal_metadata.indicator_transformation = "test_indicator"

    mock_signal_registry = MagicMock()
    mock_signal_registry.get_enabled.return_value = {
        "test_signal": mock_signal_metadata
    }

    # Mock indicator metadata (has default_securities)
    mock_indicator_metadata = MagicMock()
    mock_indicator_metadata.default_securities = {"cdx": "cdx_ig_5y", "etf": "lqd"}

    mock_indicator_registry = MagicMock()
    mock_indicator_registry.get_metadata.return_value = mock_indicator_metadata

    # Mock data registry
    mock_df = pd.DataFrame(
        {"spread": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3)
    )
    mock_data_registry = MagicMock()
    mock_data_registry.load_dataset_by_security.return_value = mock_df

    # Execute
    result = load_signal_required_data(
        mock_signal_registry, mock_data_registry, mock_indicator_registry
    )

    # Verify
    assert "cdx" in result
    assert "etf" in result
    assert len(result) == 2
    assert mock_data_registry.load_dataset_by_security.call_count == 2


def test_load_signal_required_data_with_overrides() -> None:
    """Test loading signal data with security mapping overrides."""
    # Mock signal metadata (references indicator transformation)
    mock_signal_metadata = MagicMock()
    mock_signal_metadata.indicator_transformation = "test_indicator"

    mock_signal_registry = MagicMock()
    mock_signal_registry.get_enabled.return_value = {
        "test_signal": mock_signal_metadata
    }

    # Mock indicator metadata (has default_securities)
    mock_indicator_metadata = MagicMock()
    mock_indicator_metadata.default_securities = {"cdx": "cdx_ig_5y", "etf": "lqd"}

    mock_indicator_registry = MagicMock()
    mock_indicator_registry.get_metadata.return_value = mock_indicator_metadata

    # Mock data registry
    mock_df = pd.DataFrame(
        {"spread": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3)
    )
    mock_data_registry = MagicMock()
    mock_data_registry.load_dataset_by_security.return_value = mock_df

    # Execute with overrides
    security_mapping = {"cdx": "cdx_hy_5y", "etf": "hyg"}
    result = load_signal_required_data(
        mock_signal_registry,
        mock_data_registry,
        mock_indicator_registry,
        security_mapping=security_mapping,
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
    # Mock signal metadata (references different indicator transformations)
    signal1_metadata = MagicMock()
    signal1_metadata.indicator_transformation = "indicator1"

    signal2_metadata = MagicMock()
    signal2_metadata.indicator_transformation = "indicator2"

    mock_signal_registry = MagicMock()
    mock_signal_registry.get_enabled.return_value = {
        "signal1": signal1_metadata,
        "signal2": signal2_metadata,
    }

    # Mock indicator metadata (each has different default_securities)
    indicator1_metadata = MagicMock()
    indicator1_metadata.default_securities = {"cdx": "cdx_ig_5y", "etf": "lqd"}

    indicator2_metadata = MagicMock()
    indicator2_metadata.default_securities = {"cdx": "cdx_ig_5y", "vix": "vix"}

    mock_indicator_registry = MagicMock()
    mock_indicator_registry.get_metadata.side_effect = lambda name: (
        indicator1_metadata if name == "indicator1" else indicator2_metadata
    )

    # Mock data registry
    mock_df = pd.DataFrame(
        {"value": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3)
    )
    mock_data_registry = MagicMock()
    mock_data_registry.load_dataset_by_security.return_value = mock_df

    # Execute
    result = load_signal_required_data(
        mock_signal_registry, mock_data_registry, mock_indicator_registry
    )

    # Verify all unique instruments loaded
    assert "cdx" in result
    assert "etf" in result
    assert "vix" in result
    assert len(result) == 3
