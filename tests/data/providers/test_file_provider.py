"""
Tests for file data provider.

Validates Parquet and CSV file loading with proper schema validation using
registry-based FileSource pattern.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from aponyx.data.providers.file import fetch_from_file
from aponyx.data.sources import FileSource


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    """Create sample data directory with Parquet/CSV files and registry."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create sample Parquet file
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df_parquet = pd.DataFrame(
        {"spread": [100.0 + i for i in range(10)]},
        index=dates,
    )
    parquet_file = data_dir / "sample_abc123.parquet"
    df_parquet.to_parquet(parquet_file)
    
    # Create sample CSV file
    df_csv = pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "level": [15.0 + i for i in range(10)],
        }
    )
    csv_file = data_dir / "sample_csv_def456.csv"
    df_csv.to_csv(csv_file, index=False)
    
    # Create registry mapping
    registry = {
        "test_security": "sample_abc123.parquet",
        "test_csv": "sample_csv_def456.csv",
    }
    registry_path = data_dir / "registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    
    return data_dir


class TestFetchFromFile:
    """Test file provider fetch function."""

    def test_fetch_from_file_parquet(self, sample_data_dir: Path):
        """Test loading Parquet file via registry."""
        source = FileSource(sample_data_dir)

        df = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test_security",
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "spread" in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)
        # Should have security column added for multi-security instruments
        assert "security" in df.columns

    def test_fetch_from_file_csv(self, sample_data_dir: Path):
        """Test loading CSV file via registry."""
        source = FileSource(sample_data_dir)

        df = fetch_from_file(
            source=source,
            ticker=None,
            instrument="vix",
            security="test_csv",
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "level" in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_fetch_from_file_csv_with_date_column(self, tmp_path: Path):
        """Test CSV parsing with date column."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "spread": [100.0 + i for i in range(10)],
            }
        )

        csv_file = data_dir / "with_dates.csv"
        df.to_csv(csv_file, index=False)
        
        # Create registry
        registry = {"test_csv": "with_dates.csv"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)
        result = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test_csv",
        )

        # Should parse date column as index
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_fetch_from_file_nonexistent(self, tmp_path: Path):
        """Test error when security not in registry."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create empty registry
        registry = {"existing": "existing.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        with pytest.raises(ValueError, match="Security 'nonexistent' not found"):
            fetch_from_file(
                source=source,
                ticker=None,
                instrument="test",
                security="nonexistent",
            )

    def test_fetch_from_file_unsupported_format(self, tmp_path: Path):
        """Test error for unsupported file format."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        # Create unsupported file
        unsupported_file = data_dir / "data.xlsx"
        unsupported_file.write_text("dummy")
        
        # Create registry
        registry = {"test": "data.xlsx"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        with pytest.raises(ValueError, match="Unsupported file format"):
            fetch_from_file(
                source=source,
                ticker=None,
                instrument="test",
                security="test",
            )

    def test_fetch_from_file_with_date_range(self, sample_data_dir: Path):
        """Test that date range parameters are accepted (not filtered by provider)."""
        source = FileSource(sample_data_dir)

        # Provider accepts date range params but doesn't filter
        # (filtering happens at fetch layer after validation)
        df = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test_security",
            start_date="2024-01-03",
            end_date="2024-01-07",
        )

        # Full dataset returned (no filtering in provider)
        assert len(df) == 10

    def test_fetch_from_file_with_start_date_only(self, sample_data_dir: Path):
        """Test with only start date parameter."""
        source = FileSource(sample_data_dir)

        df = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test_security",
            start_date="2024-01-05",
        )

        # Full dataset returned (no filtering in provider)
        assert len(df) == 10

    def test_fetch_from_file_with_end_date_only(self, sample_data_dir: Path):
        """Test with only end date parameter."""
        source = FileSource(sample_data_dir)

        df = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test_security",
            end_date="2024-01-05",
        )

        # Full dataset returned (no filtering in provider)
        assert len(df) == 10

    def test_fetch_from_file_preserves_columns(self, tmp_path: Path):
        """Test all columns are preserved."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "spread": [100.0] * 5,
                "volume": [1000] * 5,
                "open_interest": [500] * 5,
            },
            index=dates,
        )

        file_path = data_dir / "multi_column.parquet"
        df.to_parquet(file_path)
        
        # Create registry
        registry = {"test": "multi_column.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)
        result = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test",
        )

        # Security column added for multi-security instruments
        assert "spread" in result.columns
        assert "volume" in result.columns
        assert "open_interest" in result.columns
        assert "security" in result.columns

    def test_fetch_from_file_empty_file(self, tmp_path: Path):
        """Test handling empty Parquet file."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        empty_df = pd.DataFrame()
        file_path = data_dir / "empty.parquet"
        empty_df.to_parquet(file_path)
        
        # Create registry
        registry = {"test": "empty.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)
        result = fetch_from_file(
            source=source,
            ticker=None,
            instrument="vix",
            security="test",
        )

        assert len(result) == 0

    def test_fetch_from_file_csv_with_index(self, tmp_path: Path):
        """Test CSV with explicit index column."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {"spread": [100.0] * 5},
            index=dates,
        )
        df.index.name = "date"

        file_path = data_dir / "indexed.csv"
        df.to_csv(file_path)
        
        # Create registry
        registry = {"test": "indexed.csv"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)
        result = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test",
        )

        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 5


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_fetch_from_file_malformed_csv(self, tmp_path: Path):
        """Test that pandas-parseable CSV succeeds even if irregular."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        file_path = data_dir / "malformed.csv"
        file_path.write_text("not,valid,csv\ndata")
        
        # Create registry
        registry = {"test": "malformed.csv"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        # Pandas is forgiving - this will parse successfully
        result = fetch_from_file(
            source=source,
            ticker=None,
            instrument="vix",
            security="test",
        )

        # Should have loaded something (even if irregular)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_fetch_from_file_date_range_no_match(self, sample_data_dir: Path):
        """Test date range parameters don't cause errors."""
        source = FileSource(sample_data_dir)

        # Provider doesn't filter, just returns full dataset
        df = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test_security",
            start_date="2025-01-01",  # Future date
            end_date="2025-12-31",
        )

        # Full dataset returned (filtering happens at fetch layer)
        assert len(df) == 10

    def test_fetch_from_file_path_as_string(self, tmp_path: Path):
        """Test FileSource accepts string path for base_dir."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({"spread": [100.0] * 5}, index=dates)
        
        file_path = data_dir / "test.parquet"
        df.to_parquet(file_path)
        
        # Create registry
        registry = {"test": "test.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(str(data_dir))

        df_result = fetch_from_file(
            source=source,
            ticker=None,
            instrument="cdx",
            security="test",
        )

        assert len(df_result) == 5
