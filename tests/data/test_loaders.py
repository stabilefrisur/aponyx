"""
Tests for data loading utilities.

Validates find_raw_file, concat_multi_security, and load_instrument_from_raw.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from aponyx.data.loaders import (
    find_raw_file,
    concat_multi_security,
    load_instrument_from_raw,
)


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory with sample files."""
    data_dir = tmp_path / "raw" / "synthetic"
    data_dir.mkdir(parents=True)

    # Create sample parquet files
    df = pd.DataFrame({"value": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3))

    # VIX file
    vix_path = data_dir / "vix_abc123.parquet"
    df.to_parquet(vix_path)

    # CDX security files
    cdx_ig_path = data_dir / "cdx_ig_5y_def456.parquet"
    df.to_parquet(cdx_ig_path)

    cdx_hy_path = data_dir / "cdx_hy_5y_ghi789.parquet"
    df.to_parquet(cdx_hy_path)

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


@patch("aponyx.data.loaders.handle_duplicate_index", side_effect=lambda df, **kwargs: df)
def test_load_instrument_from_raw_single_security(
    mock_handle_dup: Mock,
    sample_data_dir: Path,
) -> None:
    """Test loading single-security instrument from raw files."""
    # Mock fetch function
    mock_fetch_fn = Mock(
        return_value=pd.DataFrame(
            {"value": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3)
        )
    )

    result = load_instrument_from_raw(
        sample_data_dir,
        "vix",
        mock_fetch_fn,
        securities=None,
    )

    assert len(result) == 3
    mock_fetch_fn.assert_called_once()


@patch("aponyx.data.loaders.handle_duplicate_index", side_effect=lambda df, **kwargs: df)
def test_load_instrument_from_raw_multi_security(
    mock_handle_dup: Mock,
    sample_data_dir: Path,
) -> None:
    """Test loading multi-security instrument from raw files."""
    # Mock fetch function
    mock_fetch_fn = Mock(
        return_value=pd.DataFrame(
            {"value": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3)
        )
    )

    result = load_instrument_from_raw(
        sample_data_dir,
        "cdx",
        mock_fetch_fn,
        securities=["cdx_ig_5y", "cdx_hy_5y"],
    )

    assert len(result) >= 3
    assert mock_fetch_fn.call_count == 2


def test_load_instrument_from_raw_file_not_found(tmp_path: Path) -> None:
    """Test loading raises error when no files found."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    mock_fetch_fn = Mock()

    with pytest.raises(ValueError, match="No VIX data file found"):
        load_instrument_from_raw(
            empty_dir,
            "vix",
            mock_fetch_fn,
            securities=None,
        )
