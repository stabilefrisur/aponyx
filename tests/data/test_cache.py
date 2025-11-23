"""
Tests for data caching layer.

Validates cache key generation, staleness tracking, hit/miss behavior,
and intraday update logic.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from aponyx.data.cache import (
    _generate_cache_key,
    get_cache_path,
    is_cache_stale,
    get_cached_data,
    save_to_cache,
    update_current_day,
)
from aponyx.data.sources import BloombergSource, APISource
from aponyx.data.registry import DataRegistry


class TestCacheKeyGeneration:
    """Test cache key generation logic."""

    def test_generate_cache_key_deterministic(self):
        """Test cache key is deterministic for same inputs."""
        source = BloombergSource()
        key1 = _generate_cache_key(source, "CDX.IG.5Y", "2024-01-01", "2024-12-31")
        key2 = _generate_cache_key(source, "CDX.IG.5Y", "2024-01-01", "2024-12-31")

        assert key1 == key2

    def test_generate_cache_key_differs_by_instrument(self):
        """Test different instruments produce different keys."""
        source = BloombergSource()
        key1 = _generate_cache_key(source, "CDX.IG.5Y", "2024-01-01", "2024-12-31")
        key2 = _generate_cache_key(source, "CDX.HY.5Y", "2024-01-01", "2024-12-31")

        assert key1 != key2

    def test_generate_cache_key_differs_by_dates(self):
        """Test different date ranges produce different keys."""
        source = BloombergSource()
        key1 = _generate_cache_key(source, "CDX.IG.5Y", "2024-01-01", "2024-12-31")
        key2 = _generate_cache_key(source, "CDX.IG.5Y", "2024-01-01", "2024-06-30")

        assert key1 != key2

    def test_generate_cache_key_differs_by_source(self):
        """Test different sources produce different keys."""
        key1 = _generate_cache_key(
            BloombergSource(), "CDX.IG.5Y", "2024-01-01", "2024-12-31"
        )
        key2 = _generate_cache_key(
            APISource("http://api.example.com"), "CDX.IG.5Y", "2024-01-01", "2024-12-31"
        )

        assert key1 != key2

    def test_generate_cache_key_handles_none_dates(self):
        """Test cache key generation with None dates."""
        source = BloombergSource()
        key1 = _generate_cache_key(source, "CDX.IG.5Y", None, None)
        key2 = _generate_cache_key(source, "CDX.IG.5Y", None, None)

        assert key1 == key2

    def test_generate_cache_key_includes_params(self):
        """Test cache key includes additional parameters."""
        source = BloombergSource()
        key1 = _generate_cache_key(source, "CDX.IG.5Y", None, None, field="PX_LAST")
        key2 = _generate_cache_key(source, "CDX.IG.5Y", None, None, field="PX_BID")

        assert key1 != key2

    def test_generate_cache_key_length(self):
        """Test cache key is 16 characters (truncated hash)."""
        source = BloombergSource()
        key = _generate_cache_key(source, "CDX.IG.5Y", "2024-01-01", "2024-12-31")

        assert len(key) == 16
        assert key.isalnum()


class TestCachePath:
    """Test cache path generation."""

    def test_get_cache_path_structure(self, tmp_path: Path):
        """Test cache path follows expected structure."""
        cache_path = get_cache_path(tmp_path, "bloomberg", "CDX.IG.5Y", "abc123")

        assert cache_path.parent == tmp_path / "bloomberg"
        assert cache_path.name == "CDX_IG_5Y_abc123.parquet"

    def test_get_cache_path_creates_provider_dir(self, tmp_path: Path):
        """Test provider directory is created."""
        cache_path = get_cache_path(tmp_path, "bloomberg", "CDX.IG.5Y", "abc123")

        assert cache_path.parent.exists()

    def test_get_cache_path_sanitizes_instrument(self, tmp_path: Path):
        """Test instrument name is sanitized for filesystem."""
        cache_path = get_cache_path(tmp_path, "bloomberg", "CDX.NA.IG.5Y", "abc123")

        assert "." not in cache_path.stem.split("_abc123")[0]
        assert cache_path.name == "CDX_NA_IG_5Y_abc123.parquet"


class TestCacheStaleness:
    """Test cache staleness detection."""

    def test_is_cache_stale_nonexistent_file(self, tmp_path: Path):
        """Test nonexistent cache is considered stale."""
        cache_path = tmp_path / "nonexistent.parquet"

        assert is_cache_stale(cache_path, ttl_days=1)

    def test_is_cache_stale_fresh_file(self, tmp_path: Path):
        """Test recently created cache is fresh."""
        cache_path = tmp_path / "fresh.parquet"
        cache_path.write_text("dummy")

        assert not is_cache_stale(cache_path, ttl_days=1)

    def test_is_cache_stale_old_file(self, tmp_path: Path):
        """Test old cache is stale."""
        cache_path = tmp_path / "old.parquet"
        cache_path.write_text("dummy")

        # Modify file timestamp to be old
        old_time = datetime.now() - timedelta(days=5)
        timestamp = old_time.timestamp()
        import os

        os.utime(cache_path, (timestamp, timestamp))

        assert is_cache_stale(cache_path, ttl_days=1)

    def test_is_cache_stale_no_ttl(self, tmp_path: Path):
        """Test cache never expires with TTL=None."""
        cache_path = tmp_path / "eternal.parquet"
        cache_path.write_text("dummy")

        # Modify to be very old
        old_time = datetime.now() - timedelta(days=365)
        timestamp = old_time.timestamp()
        import os

        os.utime(cache_path, (timestamp, timestamp))

        assert not is_cache_stale(cache_path, ttl_days=None)


class TestGetCachedData:
    """Test cache retrieval logic."""

    def test_get_cached_data_miss_nonexistent(self, tmp_path: Path):
        """Test cache miss for nonexistent file."""
        source = BloombergSource()

        result = get_cached_data(source, "CDX.IG.5Y", tmp_path, ttl_days=1)

        assert result is None

    def test_get_cached_data_hit(self, tmp_path: Path):
        """Test cache hit returns data."""
        # Create cached data
        dates = pd.date_range("2024-01-01", periods=10)
        df = pd.DataFrame({"spread": [100.0] * 10}, index=dates)

        source = BloombergSource()
        cache_key = _generate_cache_key(source, "CDX.IG.5Y", None, None)
        cache_path = get_cache_path(tmp_path, "bloomberg", "CDX.IG.5Y", cache_key)

        from aponyx.persistence import save_parquet

        save_parquet(df, cache_path)

        # Retrieve from cache
        result = get_cached_data(source, "CDX.IG.5Y", tmp_path, ttl_days=1)

        assert result is not None
        pd.testing.assert_frame_equal(result, df, check_freq=False)

    def test_get_cached_data_miss_stale(self, tmp_path: Path):
        """Test cache miss for stale data."""
        # Create old cached data
        dates = pd.date_range("2024-01-01", periods=10)
        df = pd.DataFrame({"spread": [100.0] * 10}, index=dates)

        source = BloombergSource()
        cache_key = _generate_cache_key(source, "CDX.IG.5Y", None, None)
        cache_path = get_cache_path(tmp_path, "bloomberg", "CDX.IG.5Y", cache_key)

        from aponyx.persistence import save_parquet

        save_parquet(df, cache_path)

        # Make file old
        old_time = datetime.now() - timedelta(days=5)
        timestamp = old_time.timestamp()
        import os

        os.utime(cache_path, (timestamp, timestamp))

        # Should return None (stale)
        result = get_cached_data(source, "CDX.IG.5Y", tmp_path, ttl_days=1)

        assert result is None


class TestSaveToCache:
    """Test cache saving logic."""

    def test_save_to_cache_creates_file(self, tmp_path: Path):
        """Test saving creates cache file."""
        dates = pd.date_range("2024-01-01", periods=10)
        df = pd.DataFrame({"spread": [100.0] * 10}, index=dates)

        source = BloombergSource()

        cache_path = save_to_cache(df, source, "CDX.IG.5Y", tmp_path)

        assert cache_path.exists()
        assert cache_path.suffix == ".parquet"

    def test_save_to_cache_with_registry(self, tmp_path: Path):
        """Test saving registers dataset in registry."""
        dates = pd.date_range("2024-01-01", periods=10)
        df = pd.DataFrame({"spread": [100.0] * 10}, index=dates)

        source = BloombergSource()
        registry_path = tmp_path / "registry.json"
        registry = DataRegistry(registry_path, tmp_path)

        save_to_cache(df, source, "CDX.IG.5Y", tmp_path, registry=registry)

        # Check registry was updated
        datasets = registry.list_datasets()
        assert len(datasets) > 0
        assert any("cache" in name for name in datasets)

    def test_save_to_cache_roundtrip(self, tmp_path: Path):
        """Test save and retrieve roundtrip."""
        dates = pd.date_range("2024-01-01", periods=10)
        df = pd.DataFrame({"spread": [100.0, 101.0, 102.0] * 3 + [100.0]}, index=dates)

        source = BloombergSource()

        # Save
        save_to_cache(df, source, "CDX.IG.5Y", tmp_path)

        # Retrieve
        result = get_cached_data(source, "CDX.IG.5Y", tmp_path, ttl_days=1)

        assert result is not None
        pd.testing.assert_frame_equal(result, df, check_freq=False)


class TestUpdateCurrentDay:
    """Test intraday cache update logic."""

    def test_update_current_day_appends_new_date(self):
        """Test appending data for new date."""
        cached_dates = pd.date_range("2024-01-01", periods=5)
        cached_df = pd.DataFrame(
            {"spread": [100.0, 101.0, 102.0, 103.0, 104.0]},
            index=cached_dates,
        )

        current_date = pd.DatetimeIndex(["2024-01-06"])
        current_df = pd.DataFrame({"spread": [105.0]}, index=current_date)

        result = update_current_day(cached_df, current_df)

        assert len(result) == 6
        assert result.index[-1] == current_date[0]
        assert result.iloc[-1]["spread"] == 105.0

    def test_update_current_day_replaces_existing(self):
        """Test replacing data for existing date."""
        cached_dates = pd.date_range("2024-01-01", periods=5)
        cached_df = pd.DataFrame(
            {"spread": [100.0, 101.0, 102.0, 103.0, 104.0]},
            index=cached_dates,
        )

        # Update last date with new value
        current_date = pd.DatetimeIndex(["2024-01-05"])
        current_df = pd.DataFrame({"spread": [999.0]}, index=current_date)

        result = update_current_day(cached_df, current_df)

        assert len(result) == 5
        assert result.iloc[-1]["spread"] == 999.0

    def test_update_current_day_sorts_result(self):
        """Test result is sorted by date."""
        cached_dates = pd.date_range("2024-01-01", periods=5)
        cached_df = pd.DataFrame(
            {"spread": [100.0, 101.0, 102.0, 103.0, 104.0]},
            index=cached_dates,
        )

        # Add date in the middle
        current_date = pd.DatetimeIndex(["2024-01-03"])
        current_df = pd.DataFrame({"spread": [999.0]}, index=current_date)

        result = update_current_day(cached_df, current_df)

        assert result.index.is_monotonic_increasing

    def test_update_current_day_empty_cached(self):
        """Test update with empty cached data."""
        cached_df = pd.DataFrame()

        current_date = pd.DatetimeIndex(["2024-01-01"])
        current_df = pd.DataFrame({"spread": [100.0]}, index=current_date)

        result = update_current_day(cached_df, current_df)

        pd.testing.assert_frame_equal(result, current_df)

    def test_update_current_day_empty_current(self):
        """Test update with empty current data."""
        cached_dates = pd.date_range("2024-01-01", periods=5)
        cached_df = pd.DataFrame(
            {"spread": [100.0, 101.0, 102.0, 103.0, 104.0]},
            index=cached_dates,
        )

        current_df = pd.DataFrame()

        result = update_current_day(cached_df, current_df)

        pd.testing.assert_frame_equal(result, cached_df)

    def test_update_current_day_preserves_columns(self):
        """Test all columns are preserved."""
        cached_dates = pd.date_range("2024-01-01", periods=3)
        cached_df = pd.DataFrame(
            {
                "spread": [100.0, 101.0, 102.0],
                "volume": [1000, 1100, 1200],
            },
            index=cached_dates,
        )

        current_date = pd.DatetimeIndex(["2024-01-04"])
        current_df = pd.DataFrame(
            {"spread": [103.0], "volume": [1300]},
            index=current_date,
        )

        result = update_current_day(cached_df, current_df)

        assert list(result.columns) == ["spread", "volume"]
        assert len(result) == 4
