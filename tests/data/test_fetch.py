"""
Tests for unified data fetch interface.

Validates provider resolution, validation integration, cache integration,
and raw storage functionality.
"""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from aponyx.data.fetch import (
    save_to_raw,
    _get_provider_fetch_function,
)
from aponyx.data.sources import FileSource, BloombergSource
from aponyx.data.registry import DataRegistry
from aponyx.data.providers.file import fetch_from_file
from aponyx.data.providers.bloomberg import fetch_from_bloomberg


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Generate sample DataFrame for testing."""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    return pd.DataFrame(
        {"spread": [100.0 + i for i in range(10)]},
        index=dates,
    )


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """Create temporary raw data directory."""
    raw = tmp_path / "raw"
    raw.mkdir()
    return raw


class TestSaveToRaw:
    """Test raw data storage functionality."""

    def test_save_to_raw_creates_file(self, sample_df, raw_dir):
        """Test saving creates Parquet file."""
        raw_path = save_to_raw(
            sample_df,
            provider="bloomberg",
            instrument="cdx_ig_5y",
            raw_dir=raw_dir,
        )

        assert raw_path.exists()
        assert raw_path.suffix == ".parquet"
        assert "bloomberg" in str(raw_path)

    def test_save_to_raw_creates_provider_dir(self, sample_df, raw_dir):
        """Test provider subdirectory is created."""
        raw_path = save_to_raw(
            sample_df,
            provider="bloomberg",
            instrument="cdx_ig_5y",
            raw_dir=raw_dir,
        )

        assert raw_path.parent.name == "bloomberg"
        assert raw_path.parent.exists()

    def test_save_to_raw_creates_metadata_sidecar(self, sample_df, raw_dir):
        """Test metadata JSON sidecar is created."""
        raw_path = save_to_raw(
            sample_df,
            provider="bloomberg",
            instrument="cdx_ig_5y",
            raw_dir=raw_dir,
        )

        metadata_path = raw_path.with_suffix(".json")
        assert metadata_path.exists()

        import json

        metadata = json.loads(metadata_path.read_text())

        assert metadata["provider"] == "bloomberg"
        assert metadata["instrument"] == "cdx_ig_5y"
        assert "stored_at" in metadata
        assert "date_range" in metadata
        assert metadata["row_count"] == 10

    def test_save_to_raw_sanitizes_instrument_name(self, sample_df, raw_dir):
        """Test instrument name is sanitized for filesystem."""
        raw_path = save_to_raw(
            sample_df,
            provider="bloomberg",
            instrument="CDX.NA.IG.5Y",
            raw_dir=raw_dir,
        )

        # Should replace dots and slashes
        assert "." not in raw_path.stem.split("_")[0]
        assert "CDX_NA_IG_5Y" in raw_path.name

    def test_save_to_raw_with_registry(self, sample_df, raw_dir, tmp_path):
        """Test saving registers dataset in registry."""
        registry_path = tmp_path / "registry.json"
        registry = DataRegistry(registry_path, tmp_path)

        save_to_raw(
            sample_df,
            provider="bloomberg",
            instrument="cdx_ig_5y",
            raw_dir=raw_dir,
            registry=registry,
        )

        datasets = registry.list_datasets()
        assert len(datasets) > 0
        assert any("raw_bloomberg" in name for name in datasets)

    def test_save_to_raw_with_metadata_params(self, sample_df, raw_dir):
        """Test additional metadata parameters are saved."""
        raw_path = save_to_raw(
            sample_df,
            provider="bloomberg",
            instrument="cdx_ig_5y",
            raw_dir=raw_dir,
            source_type="terminal",
            fetch_method="historical",
        )

        metadata_path = raw_path.with_suffix(".json")

        import json

        metadata = json.loads(metadata_path.read_text())

        assert metadata["source_type"] == "terminal"
        assert metadata["fetch_method"] == "historical"

    def test_save_to_raw_hash_uniqueness(self, sample_df, raw_dir):
        """Test different date ranges produce different hashes."""
        # Save first dataset
        path1 = save_to_raw(
            sample_df,
            provider="bloomberg",
            instrument="cdx_ig_5y",
            raw_dir=raw_dir,
        )

        # Save dataset with different date range
        different_dates = pd.date_range("2024-02-01", periods=10, freq="D")
        different_df = pd.DataFrame(
            {"spread": [100.0 + i for i in range(10)]},
            index=different_dates,
        )

        path2 = save_to_raw(
            different_df,
            provider="bloomberg",
            instrument="cdx_ig_5y",
            raw_dir=raw_dir,
        )

        # Paths should be different due to different date ranges
        assert path1 != path2

    def test_save_to_raw_roundtrip(self, sample_df, raw_dir):
        """Test save and load roundtrip."""
        raw_path = save_to_raw(
            sample_df,
            provider="synthetic",
            instrument="test_data",
            raw_dir=raw_dir,
        )

        from aponyx.persistence import load_parquet

        loaded_df = load_parquet(raw_path)

        pd.testing.assert_frame_equal(loaded_df, sample_df, check_freq=False)


class TestGetProviderFetchFunction:
    """Test provider fetch function resolution."""

    def test_get_provider_fetch_function_file(self):
        """Test resolves file provider fetch function."""
        source = FileSource(Path("dummy.parquet"))

        fetch_fn = _get_provider_fetch_function(source)

        assert fetch_fn is fetch_from_file

    def test_get_provider_fetch_function_bloomberg(self):
        """Test resolves Bloomberg provider fetch function."""
        source = BloombergSource()

        fetch_fn = _get_provider_fetch_function(source)

        assert fetch_fn is fetch_from_bloomberg

    def test_get_provider_fetch_function_unsupported(self):
        """Test error for unsupported provider."""
        from aponyx.data.sources import APISource

        source = APISource(endpoint="http://api.example.com")

        with pytest.raises(ValueError, match="Unsupported provider"):
            _get_provider_fetch_function(source)


class TestFetchCDXIntegration:
    """Integration tests for fetch_cdx function."""

    @patch("aponyx.data.fetch.get_cached_data")
    @patch("aponyx.data.fetch.fetch_from_file")
    def test_fetch_cdx_uses_cache(
        self,
        mock_fetch_file,
        mock_get_cached,
        sample_df,
    ):
        """Test fetch_cdx returns cached data when available."""
        from aponyx.data.fetch import fetch_cdx

        # Mock cache hit
        mock_get_cached.return_value = sample_df

        source = FileSource(Path("dummy.parquet"))
        result = fetch_cdx(source, security="cdx_ig_5y", use_cache=True)

        # Should return cached data without calling fetch
        pd.testing.assert_frame_equal(result, sample_df)
        mock_fetch_file.assert_not_called()

    @patch("aponyx.data.fetch.get_cached_data")
    @patch("aponyx.data.fetch.fetch_from_file")
    @patch("aponyx.data.fetch.validate_cdx_schema")
    @patch("aponyx.data.fetch.save_to_cache")
    def test_fetch_cdx_fetches_on_cache_miss(
        self,
        mock_save_cache,
        mock_validate,
        mock_fetch_file,
        mock_get_cached,
        sample_df,
    ):
        """Test fetch_cdx fetches data on cache miss."""
        from aponyx.data.fetch import fetch_cdx

        # Mock cache miss
        mock_get_cached.return_value = None
        mock_fetch_file.return_value = sample_df
        mock_validate.return_value = sample_df

        source = FileSource(Path("dummy.parquet"))
        result = fetch_cdx(source, use_cache=True)

        # Should fetch and cache
        mock_fetch_file.assert_called_once()
        mock_save_cache.assert_called_once()
        pd.testing.assert_frame_equal(result, sample_df)

    def test_fetch_cdx_requires_source(self):
        """Test fetch_cdx raises error without source."""
        from aponyx.data.fetch import fetch_cdx

        with pytest.raises(ValueError, match="Data source must be specified"):
            fetch_cdx(source=None, security="cdx_ig_5y")


class TestFetchVIXIntegration:
    """Integration tests for fetch_vix function."""

    @patch("aponyx.data.fetch.get_cached_data")
    @patch("aponyx.data.fetch.fetch_from_bloomberg")
    def test_fetch_vix_uses_cache(
        self,
        mock_fetch_bbg,
        mock_get_cached,
    ):
        """Test fetch_vix returns cached data when available."""
        from aponyx.data.fetch import fetch_vix

        dates = pd.date_range("2024-01-01", periods=10)
        vix_df = pd.DataFrame({"level": [15.0] * 10}, index=dates)

        mock_get_cached.return_value = vix_df

        source = BloombergSource()
        result = fetch_vix(source, use_cache=True)

        pd.testing.assert_frame_equal(result, vix_df)
        mock_fetch_bbg.assert_not_called()


class TestFetchETFIntegration:
    """Integration tests for fetch_etf function."""

    @patch("aponyx.data.fetch.get_cached_data")
    def test_fetch_etf_uses_cache(self, mock_get_cached):
        """Test fetch_etf returns cached data when available."""
        from aponyx.data.fetch import fetch_etf

        dates = pd.date_range("2024-01-01", periods=10)
        etf_df = pd.DataFrame({"spread": [200.0] * 10}, index=dates)

        mock_get_cached.return_value = etf_df

        source = BloombergSource()
        result = fetch_etf(source, security="hyg", use_cache=True)

        pd.testing.assert_frame_equal(result, etf_df)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_save_to_raw_empty_dataframe(self, raw_dir):
        """Test saving empty DataFrame raises error."""
        empty_df = pd.DataFrame()

        with pytest.raises(ValueError, match="Cannot save empty DataFrame"):
            save_to_raw(
                empty_df,
                provider="test",
                instrument="empty",
                raw_dir=raw_dir,
            )

    def test_save_to_raw_special_characters(self, sample_df, raw_dir):
        """Test sanitizing special characters in instrument name."""
        raw_path = save_to_raw(
            sample_df,
            provider="test",
            instrument="CDX/NA.IG.5Y",
            raw_dir=raw_dir,
        )

        # Should sanitize slashes and dots
        assert "/" not in raw_path.name
        assert "CDX_NA_IG_5Y" in raw_path.name
