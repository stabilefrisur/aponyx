"""
Tests for file data provider.

Validates Parquet and CSV file loading with proper schema validation.
"""

from pathlib import Path

import pandas as pd
import pytest

from aponyx.data.providers.file import fetch_from_file
from aponyx.data.sources import FileSource


@pytest.fixture
def sample_parquet_file(tmp_path: Path) -> Path:
    """Create sample Parquet file."""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {"spread": [100.0 + i for i in range(10)]},
        index=dates,
    )
    
    file_path = tmp_path / "sample.parquet"
    df.to_parquet(file_path)
    return file_path


@pytest.fixture
def sample_csv_file(tmp_path: Path) -> Path:
    """Create sample CSV file."""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "spread": [100.0 + i for i in range(10)],
        }
    )
    
    file_path = tmp_path / "sample.csv"
    df.to_csv(file_path, index=False)
    return file_path


class TestFetchFromFile:
    """Test file provider fetch function."""

    def test_fetch_from_file_parquet(self, sample_parquet_file):
        """Test loading Parquet file."""
        source = FileSource(sample_parquet_file)
        
        df = fetch_from_file(
            source=source,
            instrument="test",
        )
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "spread" in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_fetch_from_file_csv(self, sample_csv_file):
        """Test loading CSV file."""
        source = FileSource(sample_csv_file)
        
        df = fetch_from_file(
            source=source,
            instrument="test",
        )
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "spread" in df.columns

    def test_fetch_from_file_csv_with_date_column(self, tmp_path):
        """Test CSV parsing with date column."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "spread": [100.0 + i for i in range(10)],
            }
        )
        
        file_path = tmp_path / "with_dates.csv"
        df.to_csv(file_path, index=False)
        
        source = FileSource(file_path)
        result = fetch_from_file(source=source, instrument="test")
        
        # Should parse date column as index
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_fetch_from_file_nonexistent(self, tmp_path):
        """Test error when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.parquet"
        source = FileSource(nonexistent)
        
        with pytest.raises(FileNotFoundError):
            fetch_from_file(source=source, instrument="test")

    def test_fetch_from_file_unsupported_format(self, tmp_path):
        """Test error for unsupported file format."""
        unsupported = tmp_path / "data.xlsx"
        unsupported.write_text("dummy")
        source = FileSource(unsupported)
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            fetch_from_file(source=source, instrument="test")

    def test_fetch_from_file_with_date_range(self, sample_parquet_file):
        """Test filtering by date range."""
        source = FileSource(sample_parquet_file)
        
        df = fetch_from_file(
            source=source,
            instrument="test",
            start_date="2024-01-03",
            end_date="2024-01-07",
        )
        
        # Should filter to date range
        assert len(df) == 5
        assert df.index.min() >= pd.Timestamp("2024-01-03")
        assert df.index.max() <= pd.Timestamp("2024-01-07")

    def test_fetch_from_file_with_start_date_only(self, sample_parquet_file):
        """Test filtering with only start date."""
        source = FileSource(sample_parquet_file)
        
        df = fetch_from_file(
            source=source,
            instrument="test",
            start_date="2024-01-05",
        )
        
        assert len(df) == 6  # Days 5-10
        assert df.index.min() >= pd.Timestamp("2024-01-05")

    def test_fetch_from_file_with_end_date_only(self, sample_parquet_file):
        """Test filtering with only end date."""
        source = FileSource(sample_parquet_file)
        
        df = fetch_from_file(
            source=source,
            instrument="test",
            end_date="2024-01-05",
        )
        
        assert len(df) == 5  # Days 1-5
        assert df.index.max() <= pd.Timestamp("2024-01-05")

    def test_fetch_from_file_preserves_columns(self, tmp_path):
        """Test all columns are preserved."""
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "spread": [100.0] * 5,
                "volume": [1000] * 5,
                "open_interest": [500] * 5,
            },
            index=dates,
        )
        
        file_path = tmp_path / "multi_column.parquet"
        df.to_parquet(file_path)
        
        source = FileSource(file_path)
        result = fetch_from_file(source=source, instrument="test")
        
        assert list(result.columns) == ["spread", "volume", "open_interest"]

    def test_fetch_from_file_empty_file(self, tmp_path):
        """Test handling empty Parquet file."""
        empty_df = pd.DataFrame()
        file_path = tmp_path / "empty.parquet"
        empty_df.to_parquet(file_path)
        
        source = FileSource(file_path)
        result = fetch_from_file(source=source, instrument="test")
        
        assert len(result) == 0

    def test_fetch_from_file_csv_with_index(self, tmp_path):
        """Test CSV with explicit index column."""
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {"spread": [100.0] * 5},
            index=dates,
        )
        df.index.name = "date"
        
        file_path = tmp_path / "indexed.csv"
        df.to_csv(file_path)
        
        source = FileSource(file_path)
        result = fetch_from_file(source=source, instrument="test")
        
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 5


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_fetch_from_file_malformed_csv(self, tmp_path):
        """Test that pandas-parseable CSV succeeds even if irregular."""
        file_path = tmp_path / "malformed.csv"
        file_path.write_text("not,valid,csv\ndata")
        
        source = FileSource(file_path)
        
        # Pandas is forgiving - this will parse successfully
        result = fetch_from_file(source=source, instrument="test")
        
        # Should have loaded something (even if irregular)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_fetch_from_file_date_range_no_match(self, sample_parquet_file):
        """Test date range filter with no matching data."""
        source = FileSource(sample_parquet_file)
        
        df = fetch_from_file(
            source=source,
            instrument="test",
            start_date="2025-01-01",  # Future date
            end_date="2025-12-31",
        )
        
        # Should return empty DataFrame
        assert len(df) == 0

    def test_fetch_from_file_path_as_string(self, sample_parquet_file):
        """Test FileSource accepts string path."""
        source = FileSource(str(sample_parquet_file))
        
        df = fetch_from_file(source=source, instrument="test")
        
        assert len(df) == 10
