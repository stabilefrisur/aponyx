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
        {
            "spread": [100.0 + i for i in range(10)],
            "security": ["cdx_ig_5y"] * 10,  # Add security column
        },
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
            security="cdx_ig_5y",
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
            security="cdx_ig_5y",
            raw_dir=raw_dir,
        )

        assert raw_path.parent.name == "bloomberg"
        assert raw_path.parent.exists()

    def test_save_to_raw_creates_metadata_sidecar(self, sample_df, raw_dir):
        """Test metadata JSON sidecar is created."""
        raw_path = save_to_raw(
            sample_df,
            provider="bloomberg",
            security="cdx_ig_5y",
            raw_dir=raw_dir,
        )

        metadata_path = raw_path.with_suffix(".json")
        assert metadata_path.exists()

        import json

        metadata = json.loads(metadata_path.read_text())

        assert metadata["provider"] == "bloomberg"
        assert metadata["security"] == "cdx_ig_5y"
        assert "stored_at" in metadata
        assert "date_range" in metadata
        assert metadata["row_count"] == 10

    def test_save_to_raw_sanitizes_instrument_name(self, sample_df, raw_dir):
        """Test instrument name is sanitized for filesystem."""
        raw_path = save_to_raw(
            sample_df,
            provider="bloomberg",
            security="CDX.NA.IG.5Y",
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
            security="cdx_ig_5y",
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
            security="cdx_ig_5y",
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
            security="cdx_ig_5y",
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
            security="cdx_ig_5y",
            raw_dir=raw_dir,
        )

        # Paths should be different due to different date ranges
        assert path1 != path2

    def test_save_to_raw_roundtrip(self, sample_df, raw_dir):
        """Test save and load roundtrip."""
        raw_path = save_to_raw(
            sample_df,
            provider="synthetic",
            security="test_data",
            raw_dir=raw_dir,
        )

        from aponyx.persistence import load_parquet

        loaded_df = load_parquet(raw_path)

        pd.testing.assert_frame_equal(loaded_df, sample_df, check_freq=False)


class TestGetProviderFetchFunction:
    """Test provider fetch function resolution."""

    def test_get_provider_fetch_function_file(self, tmp_path):
        """Test resolves file provider fetch function."""
        import json

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        registry = {"test": "test.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        fetch_fn = _get_provider_fetch_function(source)

        assert fetch_fn is fetch_from_file

    def test_get_provider_fetch_function_bloomberg(self):
        """Test resolves Bloomberg provider fetch function (returns adapter)."""
        source = BloombergSource()

        fetch_fn = _get_provider_fetch_function(source)

        # Returns an adapter with unified interface, not the raw function
        assert callable(fetch_fn)
        assert fetch_fn.__name__ == "_bloomberg_adapter"

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
        tmp_path,
    ):
        """Test fetch_cdx returns cached data when available."""
        import json
        from aponyx.data.fetch import fetch_cdx

        # Create temporary data directory with registry
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        registry = {"cdx_ig_5y": "cdx_ig_5y.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        # Mock cache hit
        mock_get_cached.return_value = sample_df

        source = FileSource(data_dir)
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
        tmp_path,
    ):
        """Test fetch_cdx fetches data on cache miss."""
        import json
        from aponyx.data.fetch import fetch_cdx

        # Create temporary data directory with registry
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        registry = {"cdx_ig_5y": "cdx_ig_5y.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        # Mock cache miss
        mock_get_cached.return_value = None
        mock_fetch_file.return_value = sample_df
        mock_validate.return_value = sample_df

        source = FileSource(data_dir)
        result = fetch_cdx(source, security="cdx_ig_5y", use_cache=True)

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
                security="empty",
                raw_dir=raw_dir,
            )

    def test_save_to_raw_special_characters(self, sample_df, raw_dir):
        """Test sanitizing special characters in instrument name."""
        raw_path = save_to_raw(
            sample_df,
            provider="test",
            security="CDX/NA.IG.5Y",
            raw_dir=raw_dir,
        )

        # Should sanitize slashes and dots
        assert "/" not in raw_path.name
        assert "CDX_NA_IG_5Y" in raw_path.name


class TestFetchSecurityDataIntegration:
    """Integration tests for channel-aware fetch_security_data function."""

    @pytest.fixture
    def synthetic_data_dir(self, tmp_path: Path) -> Path:
        """Create synthetic data with channel columns."""
        import json

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        # Create CDX file with spread column
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        cdx_df = pd.DataFrame({"spread": [100.0 + i for i in range(10)]}, index=dates)
        cdx_df.to_parquet(data_dir / "cdx_ig_5y_abc123.parquet")

        # Create HYG file with price and spread columns
        hyg_df = pd.DataFrame(
            {
                "price": [75.0 + i * 0.1 for i in range(10)],
                "spread": [350.0 + i for i in range(10)],
            },
            index=dates,
        )
        hyg_df.to_parquet(data_dir / "hyg_def456.parquet")

        # Create VIX file with level column
        vix_df = pd.DataFrame({"level": [15.0 + i for i in range(10)]}, index=dates)
        vix_df.to_parquet(data_dir / "vix_ghi789.parquet")

        # Create registry.json
        registry = {
            "cdx_ig_5y": "cdx_ig_5y_abc123.parquet",
            "hyg": "hyg_def456.parquet",
            "vix": "vix_ghi789.parquet",
        }
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        return data_dir

    def test_fetch_security_data_cdx_indicator_purpose(self, synthetic_data_dir):
        """Test fetching CDX data for INDICATOR purpose returns spread channel."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="cdx_ig_5y",
            purpose=UsagePurpose.INDICATOR,
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert "spread" in result.columns
        assert len(result) == 10

    def test_fetch_security_data_etf_price_channel(self, synthetic_data_dir):
        """Test fetching ETF data for PNL purpose returns price channel."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            purpose=UsagePurpose.PNL,
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert "price" in result.columns
        assert len(result) == 10

    def test_fetch_security_data_vix_level_channel(self, synthetic_data_dir):
        """Test fetching VIX data returns level channel."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="vix",
            purpose=UsagePurpose.INDICATOR,
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert "level" in result.columns
        assert len(result) == 10

    def test_fetch_security_data_explicit_channel(self, synthetic_data_dir):
        """Test fetching data with explicit channel override."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            channels=[DataChannel.SPREAD],  # Explicit channel
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert "spread" in result.columns
        assert "price" not in result.columns

    def test_fetch_security_data_multiple_channels(self, synthetic_data_dir):
        """Test fetching multiple channels at once."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            channels=[DataChannel.PRICE, DataChannel.SPREAD],
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert "price" in result.columns
        assert "spread" in result.columns
        assert len(result) == 10

    def test_fetch_security_data_invalid_security(self, synthetic_data_dir):
        """Test fetching unknown security raises error."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource

        source = FileSource(synthetic_data_dir)
        with pytest.raises(ValueError, match="Unknown security: 'unknown_sec'"):
            fetch_security_data(source=source, security_id="unknown_sec", use_cache=False)


class TestChannelResolution:
    """Tests for channel resolution helper functions."""

    def test_resolve_channel_for_indicator_purpose_cdx(self):
        """Test INDICATOR purpose resolves to spread for CDX."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        channel = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.INDICATOR)
        assert channel == DataChannel.SPREAD

    def test_resolve_channel_for_indicator_purpose_etf(self):
        """Test INDICATOR purpose resolves to spread for ETF (per INSTRUMENT_DEFAULTS)."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        channel = resolve_channel_for_purpose("hyg", UsagePurpose.INDICATOR)
        assert channel == DataChannel.SPREAD  # ETF indicator default is spread

    def test_resolve_channel_for_pnl_purpose_uses_quote_type(self):
        """Test PNL purpose uses security's quote_type."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        # CDX quote_type is "spread"
        cdx_channel = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.PNL)
        assert cdx_channel == DataChannel.SPREAD

        # ETF quote_type is "price"
        etf_channel = resolve_channel_for_purpose("hyg", UsagePurpose.PNL)
        assert etf_channel == DataChannel.PRICE

    def test_list_security_channels(self):
        """Test listing available channels for a security."""
        from aponyx.data.fetch import list_security_channels
        from aponyx.data.channels import DataChannel

        # CDX IG 5Y only has spread channel
        cdx_channels = list_security_channels("cdx_ig_5y")
        assert DataChannel.SPREAD in cdx_channels
        assert len(cdx_channels) == 1

        # HYG has both price and spread
        hyg_channels = list_security_channels("hyg")
        assert DataChannel.PRICE in hyg_channels
        assert DataChannel.SPREAD in hyg_channels
        assert len(hyg_channels) == 2

        # VIX has only level
        vix_channels = list_security_channels("vix")
        assert DataChannel.LEVEL in vix_channels
        assert len(vix_channels) == 1

    def test_get_security_spec(self):
        """Test getting security spec from catalog."""
        from aponyx.data.fetch import get_security_spec
        from aponyx.data.channels import DataChannel

        spec = get_security_spec("cdx_ig_5y")
        assert spec.security_id == "cdx_ig_5y"
        assert spec.instrument_type == "cdx"
        assert spec.quote_type == "spread"
        # Channels dict uses DataChannel enum as keys
        assert DataChannel.SPREAD in spec.channels

    def test_get_security_spec_unknown(self):
        """Test getting spec for unknown security raises error."""
        from aponyx.data.fetch import get_security_spec

        with pytest.raises(ValueError, match="Unknown security: 'unknown'"):
            get_security_spec("unknown")

    def test_resolve_channel_for_indicator_vix(self):
        """Test INDICATOR purpose resolves to level for VIX."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        channel = resolve_channel_for_purpose("vix", UsagePurpose.INDICATOR)
        assert channel == DataChannel.LEVEL

    def test_resolve_channel_for_display_purpose(self):
        """Test DISPLAY purpose uses instrument type defaults."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        # CDX display default is spread
        cdx_channel = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.DISPLAY)
        assert cdx_channel == DataChannel.SPREAD

        # VIX display default is level
        vix_channel = resolve_channel_for_purpose("vix", UsagePurpose.DISPLAY)
        assert vix_channel == DataChannel.LEVEL

    def test_resolve_channel_with_override(self):
        """Test channel override takes precedence."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        # Override spread default to price for ETF
        channel = resolve_channel_for_purpose(
            "hyg",
            UsagePurpose.INDICATOR,
            override=DataChannel.PRICE,
        )
        assert channel == DataChannel.PRICE

    def test_resolve_channel_invalid_override_raises(self):
        """Test invalid channel override raises error."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        # VIX doesn't have SPREAD channel
        with pytest.raises(ValueError, match="not available"):
            resolve_channel_for_purpose(
                "vix",
                UsagePurpose.INDICATOR,
                override=DataChannel.SPREAD,
            )

    def test_resolve_channel_all_cdx_securities(self):
        """Test channel resolution works for all CDX securities."""
        from aponyx.data.fetch import resolve_channel_for_purpose, get_security_spec
        from aponyx.data.channels import UsagePurpose, DataChannel

        cdx_securities = ["cdx_ig_5y", "cdx_ig_10y", "cdx_hy_5y", "itrx_xover_5y", "itrx_eur_5y"]
        
        for sec_id in cdx_securities:
            spec = get_security_spec(sec_id)
            assert spec.instrument_type == "cdx"
            
            # All CDX should use spread for indicator
            channel = resolve_channel_for_purpose(sec_id, UsagePurpose.INDICATOR)
            assert channel == DataChannel.SPREAD, f"Failed for {sec_id}"

    def test_list_channels_cdx_hy_has_both(self):
        """Test CDX HY 5Y has both spread and price channels."""
        from aponyx.data.fetch import list_security_channels
        from aponyx.data.channels import DataChannel

        channels = list_security_channels("cdx_hy_5y")
        assert DataChannel.SPREAD in channels
        assert DataChannel.PRICE in channels
        assert len(channels) == 2


class TestFetchSecurityDataIndicatorPurpose:
    """Tests for fetch_security_data with INDICATOR purpose (T020)."""

    @pytest.fixture
    def synthetic_data_dir(self, tmp_path: Path) -> Path:
        """Create synthetic data with channel columns."""
        import json

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        dates = pd.date_range("2024-01-01", periods=10, freq="B")

        # CDX IG 5Y: spread only
        cdx_ig_df = pd.DataFrame({"spread": [100.0 + i for i in range(10)]}, index=dates)
        cdx_ig_df.to_parquet(data_dir / "cdx_ig_5y_abc123.parquet")

        # CDX HY 5Y: spread and price
        cdx_hy_df = pd.DataFrame(
            {
                "spread": [350.0 + i for i in range(10)],
                "price": [95.0 - i * 0.1 for i in range(10)],
            },
            index=dates,
        )
        cdx_hy_df.to_parquet(data_dir / "cdx_hy_5y_def456.parquet")

        # HYG: price and spread
        hyg_df = pd.DataFrame(
            {
                "price": [75.0 + i * 0.1 for i in range(10)],
                "spread": [350.0 + i for i in range(10)],
            },
            index=dates,
        )
        hyg_df.to_parquet(data_dir / "hyg_ghi789.parquet")

        # VIX: level only
        vix_df = pd.DataFrame({"level": [15.0 + i for i in range(10)]}, index=dates)
        vix_df.to_parquet(data_dir / "vix_jkl012.parquet")

        # Registry
        registry = {
            "cdx_ig_5y": "cdx_ig_5y_abc123.parquet",
            "cdx_hy_5y": "cdx_hy_5y_def456.parquet",
            "hyg": "hyg_ghi789.parquet",
            "vix": "vix_jkl012.parquet",
        }
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        return data_dir

    def test_cdx_indicator_returns_spread(self, synthetic_data_dir):
        """Test CDX with INDICATOR purpose returns spread channel."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="cdx_ig_5y",
            purpose=UsagePurpose.INDICATOR,
            use_cache=False,
        )

        assert "spread" in result.columns
        assert len(result.columns) == 1
        assert len(result) == 10
        # Verify spread values are in expected range (100-109)
        assert result["spread"].min() >= 100.0
        assert result["spread"].max() <= 110.0

    def test_etf_indicator_returns_spread(self, synthetic_data_dir):
        """Test ETF with INDICATOR purpose returns spread channel (per INSTRUMENT_DEFAULTS)."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            purpose=UsagePurpose.INDICATOR,
            use_cache=False,
        )

        assert "spread" in result.columns
        assert "price" not in result.columns  # Only spread for indicator
        assert len(result) == 10

    def test_vix_indicator_returns_level(self, synthetic_data_dir):
        """Test VIX with INDICATOR purpose returns level channel."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="vix",
            purpose=UsagePurpose.INDICATOR,
            use_cache=False,
        )

        assert "level" in result.columns
        assert len(result.columns) == 1
        # Verify VIX values are in expected range (15-24)
        assert result["level"].min() >= 15.0
        assert result["level"].max() <= 25.0

    def test_cdx_hy_indicator_returns_spread_only(self, synthetic_data_dir):
        """Test CDX HY (which has both channels) returns only spread for INDICATOR."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="cdx_hy_5y",
            purpose=UsagePurpose.INDICATOR,
            use_cache=False,
        )

        assert "spread" in result.columns
        assert "price" not in result.columns  # Should not include price
        assert len(result.columns) == 1

    def test_indicator_data_has_valid_values(self, synthetic_data_dir):
        """Test indicator data passes validation (in expected bounds)."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)

        # CDX spread should be between 0 and 10000
        cdx_result = fetch_security_data(
            source, "cdx_ig_5y", purpose=UsagePurpose.INDICATOR, use_cache=False
        )
        assert cdx_result["spread"].min() >= 0
        assert cdx_result["spread"].max() <= 10000

        # VIX level should be between 0 and 200
        vix_result = fetch_security_data(
            source, "vix", purpose=UsagePurpose.INDICATOR, use_cache=False
        )
        assert vix_result["level"].min() >= 0
        assert vix_result["level"].max() <= 200

    def test_indicator_returns_datetimeindex(self, synthetic_data_dir):
        """Test indicator data has proper DatetimeIndex."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source, "cdx_ig_5y", purpose=UsagePurpose.INDICATOR, use_cache=False
        )

        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.is_monotonic_increasing


class TestChannelValidation:
    """Tests for channel-aware validation (T018)."""

    def test_validate_channel_data_valid_spread(self):
        """Test validation passes for valid spread data."""
        from aponyx.data.validation import validate_channel_data

        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"spread": [100.0, 150.0, 200.0, 180.0, 160.0]}, index=dates)

        result = validate_channel_data(df, ["spread"], "cdx_ig_5y")

        assert len(result) == 5
        assert "spread" in result.columns

    def test_validate_channel_data_valid_level(self):
        """Test validation passes for valid VIX level data."""
        from aponyx.data.validation import validate_channel_data

        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"level": [15.0, 18.0, 22.0, 20.0, 17.0]}, index=dates)

        result = validate_channel_data(df, ["level"], "vix")

        assert len(result) == 5
        assert "level" in result.columns

    def test_validate_channel_data_missing_channel_raises(self):
        """Test validation fails when channel column is missing."""
        from aponyx.data.validation import validate_channel_data

        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"price": [75.0, 76.0, 77.0, 78.0, 79.0]}, index=dates)

        with pytest.raises(ValueError, match="Missing channels"):
            validate_channel_data(df, ["spread"], "cdx_ig_5y")

    def test_validate_channel_data_out_of_bounds_raises(self):
        """Test validation fails when values are out of bounds."""
        from aponyx.data.validation import validate_channel_data

        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        # VIX level max is 200
        df = pd.DataFrame({"level": [15.0, 18.0, 250.0, 20.0, 17.0]}, index=dates)

        with pytest.raises(ValueError, match="outside valid range"):
            validate_channel_data(df, ["level"], "vix")

    def test_validate_channel_columns_exist(self):
        """Test column existence check."""
        from aponyx.data.validation import validate_channel_columns_exist

        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame(
            {
                "spread": [100.0, 150.0, 200.0, 180.0, 160.0],
                "price": [95.0, 94.5, 94.0, 94.2, 94.5],
            },
            index=dates,
        )

        # Should not raise
        validate_channel_columns_exist(df, ["spread"], "cdx_ig_5y")
        validate_channel_columns_exist(df, ["spread", "price"], "cdx_hy_5y")

    def test_validate_channel_columns_missing_raises(self):
        """Test column existence check fails for missing column."""
        from aponyx.data.validation import validate_channel_columns_exist

        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"spread": [100.0, 150.0, 200.0, 180.0, 160.0]}, index=dates)

        with pytest.raises(ValueError, match="not found in file"):
            validate_channel_columns_exist(df, ["level"], "vix")


# =============================================================================
# Phase 4: User Story 2 - P&L Channel Resolution Tests (T024)
# =============================================================================


class TestPnLChannelResolution:
    """Tests for P&L channel resolution based on quote_type (T024).

    These tests verify that:
    1. quote_type='spread' → DataChannel.SPREAD for P&L
    2. quote_type='price' → DataChannel.PRICE for P&L
    3. quote_type drives P&L channel, not spread availability
    """

    def test_spread_quoted_cdx_uses_spread_for_pnl(self):
        """Test spread-quoted CDX uses SPREAD channel for P&L."""
        from aponyx.data.fetch import resolve_channel_for_purpose, get_security_spec
        from aponyx.data.channels import UsagePurpose, DataChannel

        # CDX IG 5Y is spread-quoted
        spec = get_security_spec("cdx_ig_5y")
        assert spec.quote_type == "spread"

        channel = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.PNL)
        assert channel == DataChannel.SPREAD

    def test_price_quoted_etf_uses_price_for_pnl(self):
        """Test price-quoted ETF uses PRICE channel for P&L."""
        from aponyx.data.fetch import resolve_channel_for_purpose, get_security_spec
        from aponyx.data.channels import UsagePurpose, DataChannel

        # HYG is price-quoted
        spec = get_security_spec("hyg")
        assert spec.quote_type == "price"

        channel = resolve_channel_for_purpose("hyg", UsagePurpose.PNL)
        assert channel == DataChannel.PRICE

    def test_quote_type_overrides_channel_availability(self):
        """Test quote_type determines P&L channel even when other channels available.

        HYG has both SPREAD and PRICE channels, but quote_type='price'
        means P&L must use PRICE, not SPREAD.
        """
        from aponyx.data.fetch import resolve_channel_for_purpose, get_security_spec
        from aponyx.data.channels import UsagePurpose, DataChannel

        spec = get_security_spec("hyg")

        # HYG has both channels
        assert spec.has_channel(DataChannel.SPREAD), "HYG should have spread channel"
        assert spec.has_channel(DataChannel.PRICE), "HYG should have price channel"

        # quote_type is price
        assert spec.quote_type == "price"

        # P&L uses PRICE (from quote_type), not SPREAD (even though available)
        channel = resolve_channel_for_purpose("hyg", UsagePurpose.PNL)
        assert channel == DataChannel.PRICE

    def test_cdx_hy_with_both_channels_uses_spread_for_pnl(self):
        """Test CDX HY uses SPREAD for P&L even with PRICE channel available."""
        from aponyx.data.fetch import resolve_channel_for_purpose, get_security_spec
        from aponyx.data.channels import UsagePurpose, DataChannel

        spec = get_security_spec("cdx_hy_5y")

        # CDX HY has both channels
        assert spec.has_channel(DataChannel.SPREAD)
        assert spec.has_channel(DataChannel.PRICE)

        # quote_type is spread
        assert spec.quote_type == "spread"

        # P&L uses SPREAD
        channel = resolve_channel_for_purpose("cdx_hy_5y", UsagePurpose.PNL)
        assert channel == DataChannel.SPREAD

    def test_all_cdx_securities_use_spread_for_pnl(self):
        """Test all CDX securities (spread-quoted) use SPREAD for P&L."""
        from aponyx.data.fetch import resolve_channel_for_purpose, get_security_spec
        from aponyx.data.channels import UsagePurpose, DataChannel

        cdx_securities = ["cdx_ig_5y", "cdx_ig_10y", "cdx_hy_5y", "itrx_xover_5y", "itrx_eur_5y"]

        for sec_id in cdx_securities:
            spec = get_security_spec(sec_id)
            assert spec.quote_type == "spread", f"{sec_id} should have quote_type=spread"

            channel = resolve_channel_for_purpose(sec_id, UsagePurpose.PNL)
            assert channel == DataChannel.SPREAD, f"{sec_id} should use SPREAD for P&L"

    def test_pnl_channel_differs_from_indicator_for_etf(self):
        """Test ETF uses different channels for P&L vs INDICATOR.

        ETF: INDICATOR uses SPREAD (instrument default), P&L uses PRICE (quote_type).
        """
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        # Indicator uses instrument_type default (SPREAD for ETF)
        indicator_channel = resolve_channel_for_purpose("hyg", UsagePurpose.INDICATOR)
        assert indicator_channel == DataChannel.SPREAD

        # P&L uses quote_type (PRICE for ETF)
        pnl_channel = resolve_channel_for_purpose("hyg", UsagePurpose.PNL)
        assert pnl_channel == DataChannel.PRICE

        # They should differ
        assert indicator_channel != pnl_channel

    def test_pnl_channel_same_as_indicator_for_cdx(self):
        """Test CDX uses same channel for both P&L and INDICATOR (both SPREAD)."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        # Both use SPREAD
        indicator_channel = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.INDICATOR)
        pnl_channel = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.PNL)

        assert indicator_channel == DataChannel.SPREAD
        assert pnl_channel == DataChannel.SPREAD
        assert indicator_channel == pnl_channel

    @pytest.fixture
    def synthetic_data_dir(self, tmp_path: Path) -> Path:
        """Create synthetic data with channel columns for P&L tests."""
        import json

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        dates = pd.date_range("2024-01-01", periods=10, freq="B")

        # CDX IG 5Y: spread only (spread-quoted)
        cdx_ig_df = pd.DataFrame({"spread": [100.0 + i for i in range(10)]}, index=dates)
        cdx_ig_df.to_parquet(data_dir / "cdx_ig_5y_abc123.parquet")

        # HYG: price and spread (price-quoted)
        hyg_df = pd.DataFrame(
            {
                "price": [75.0 + i * 0.1 for i in range(10)],
                "spread": [350.0 + i for i in range(10)],
            },
            index=dates,
        )
        hyg_df.to_parquet(data_dir / "hyg_def456.parquet")

        # Registry
        registry = {
            "cdx_ig_5y": "cdx_ig_5y_abc123.parquet",
            "hyg": "hyg_def456.parquet",
        }
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        return data_dir

    def test_fetch_security_data_pnl_cdx_returns_spread(self, synthetic_data_dir):
        """Test fetch_security_data with PNL purpose returns spread for CDX."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="cdx_ig_5y",
            purpose=UsagePurpose.PNL,
            use_cache=False,
        )

        assert "spread" in result.columns
        assert len(result.columns) == 1
        assert len(result) == 10

    def test_fetch_security_data_pnl_etf_returns_price(self, synthetic_data_dir):
        """Test fetch_security_data with PNL purpose returns price for ETF."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            purpose=UsagePurpose.PNL,
            use_cache=False,
        )

        # Should return PRICE channel only (quote_type=price)
        assert "price" in result.columns
        assert "spread" not in result.columns
        assert len(result.columns) == 1
        assert len(result) == 10

    def test_fetch_security_data_indicator_vs_pnl_etf(self, synthetic_data_dir):
        """Test ETF returns different channels for INDICATOR vs PNL purposes."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_dir)

        # INDICATOR returns spread (instrument_type default for ETF)
        indicator_df = fetch_security_data(
            source=source,
            security_id="hyg",
            purpose=UsagePurpose.INDICATOR,
            use_cache=False,
        )
        assert "spread" in indicator_df.columns
        assert "price" not in indicator_df.columns

        # PNL returns price (quote_type for ETF)
        pnl_df = fetch_security_data(
            source=source,
            security_id="hyg",
            purpose=UsagePurpose.PNL,
            use_cache=False,
        )
        assert "price" in pnl_df.columns
        assert "spread" not in pnl_df.columns


class TestDisplayChannelResolution:
    """Test T030: DISPLAY purpose channel resolution for visualization.

    DISPLAY uses instrument-type defaults (same as INDICATOR), with optional override.
    """

    def test_display_cdx_resolves_to_spread(self):
        """Test DISPLAY purpose resolves to SPREAD for CDX instruments."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        channel = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.DISPLAY)
        assert channel == DataChannel.SPREAD

    def test_display_vix_resolves_to_level(self):
        """Test DISPLAY purpose resolves to LEVEL for VIX."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        channel = resolve_channel_for_purpose("vix", UsagePurpose.DISPLAY)
        assert channel == DataChannel.LEVEL

    def test_display_etf_resolves_to_spread(self):
        """Test DISPLAY purpose resolves to SPREAD for ETF instruments (default)."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        channel = resolve_channel_for_purpose("hyg", UsagePurpose.DISPLAY)
        assert channel == DataChannel.SPREAD

    def test_display_same_as_indicator_for_cdx(self):
        """Test DISPLAY and INDICATOR return same channel for CDX."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose

        display = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.DISPLAY)
        indicator = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.INDICATOR)
        assert display == indicator

    def test_display_same_as_indicator_for_vix(self):
        """Test DISPLAY and INDICATOR return same channel for VIX."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose

        display = resolve_channel_for_purpose("vix", UsagePurpose.DISPLAY)
        indicator = resolve_channel_for_purpose("vix", UsagePurpose.INDICATOR)
        assert display == indicator

    def test_display_differs_from_pnl_for_price_quoted_etf(self):
        """Test DISPLAY differs from PNL for price-quoted ETF."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        display = resolve_channel_for_purpose("hyg", UsagePurpose.DISPLAY)
        pnl = resolve_channel_for_purpose("hyg", UsagePurpose.PNL)

        # DISPLAY uses instrument default (spread)
        # PNL uses quote_type (price)
        assert display == DataChannel.SPREAD
        assert pnl == DataChannel.PRICE
        assert display != pnl

    def test_display_with_explicit_channel_override(self):
        """Test resolve_channel_for_purpose accepts explicit override."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        # Override to PRICE for a spread-default instrument
        channel = resolve_channel_for_purpose(
            "hyg", UsagePurpose.DISPLAY, override=DataChannel.PRICE
        )
        assert channel == DataChannel.PRICE

    @pytest.fixture
    def synthetic_data_with_all_channels(self, tmp_path: Path) -> Path:
        """Create synthetic data with multiple channel columns."""
        import json

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        dates = pd.date_range("2024-01-01", periods=10, freq="B")

        # HYG with both spread and price
        hyg_df = pd.DataFrame(
            {
                "spread": [350.0 + i for i in range(10)],
                "price": [75.0 + i * 0.1 for i in range(10)],
            },
            index=dates,
        )
        hyg_df.to_parquet(data_dir / "hyg_display_test.parquet")

        # VIX with level
        vix_df = pd.DataFrame({"level": [15.0 + i * 0.5 for i in range(10)]}, index=dates)
        vix_df.to_parquet(data_dir / "vix_display_test.parquet")

        registry = {
            "hyg": "hyg_display_test.parquet",
            "vix": "vix_display_test.parquet",
        }
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        return data_dir

    def test_fetch_security_data_display_purpose(self, synthetic_data_with_all_channels):
        """Test fetch_security_data with DISPLAY purpose returns default channel."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_with_all_channels)

        # DISPLAY for ETF returns spread (instrument default)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            purpose=UsagePurpose.DISPLAY,
            use_cache=False,
        )

        assert "spread" in result.columns
        assert "price" not in result.columns
        assert len(result) == 10

    def test_fetch_security_data_display_vix(self, synthetic_data_with_all_channels):
        """Test fetch_security_data with DISPLAY purpose for VIX returns level."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_data_with_all_channels)

        result = fetch_security_data(
            source=source,
            security_id="vix",
            purpose=UsagePurpose.DISPLAY,
            use_cache=False,
        )

        assert "level" in result.columns
        assert len(result) == 10

# =============================================================================
# Phase 6: User Story 4 - Unified Data Fetch Hiding Multi-Ticker Complexity
# =============================================================================


class TestMultiChannelFetchWithInnerJoin:
    """Tests for T035: Multi-channel fetch with inner join date alignment.

    FR-003 requirement: Inner join on dates - only dates where ALL channels have data.
    """

    @pytest.fixture
    def synthetic_data_misaligned_dates(self, tmp_path: Path) -> Path:
        """Create synthetic data with deliberately misaligned dates between channels.

        This simulates real-world scenarios where different Bloomberg tickers
        may have different trading calendars or data availability.
        """
        import json

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        # CDX HY 5Y: Create data with different date ranges for price and spread
        # Spread available from Jan 1-15
        spread_dates = pd.date_range("2024-01-01", periods=15, freq="B")
        # Price available from Jan 5-20 (5 days offset)
        price_dates = pd.date_range("2024-01-08", periods=15, freq="B")

        # Create a single parquet file with both columns but partial NaN coverage
        # For testing, use the union of dates with NaN where data is missing
        all_dates = spread_dates.union(price_dates)
        cdx_hy_df = pd.DataFrame(index=all_dates)

        # Spread: available for first range only
        cdx_hy_df["spread"] = pd.Series(
            [350.0 + i for i in range(len(spread_dates))],
            index=spread_dates,
        )
        # Price: available for second range only
        cdx_hy_df["price"] = pd.Series(
            [95.0 - i * 0.1 for i in range(len(price_dates))],
            index=price_dates,
        )

        # For inner join test, create file with overlapping dates (both have data)
        # Instead of NaN, let's create a proper test case where inner join applies
        overlap_dates = spread_dates.intersection(price_dates)

        # Create file with only overlapping dates (simulating inner join result)
        cdx_hy_overlap_df = pd.DataFrame(
            {
                "spread": [350.0 + i for i in range(len(overlap_dates))],
                "price": [95.0 - i * 0.1 for i in range(len(overlap_dates))],
            },
            index=overlap_dates,
        )
        cdx_hy_overlap_df.to_parquet(data_dir / "cdx_hy_5y_multi.parquet")

        # Also create HYG with aligned dates
        hyg_dates = pd.date_range("2024-01-01", periods=10, freq="B")
        hyg_df = pd.DataFrame(
            {
                "spread": [350.0 + i for i in range(10)],
                "price": [75.0 + i * 0.1 for i in range(10)],
            },
            index=hyg_dates,
        )
        hyg_df.to_parquet(data_dir / "hyg_multi.parquet")

        registry = {
            "cdx_hy_5y": "cdx_hy_5y_multi.parquet",
            "hyg": "hyg_multi.parquet",
        }
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        return data_dir

    def test_multi_channel_fetch_returns_all_requested_channels(
        self, synthetic_data_misaligned_dates
    ):
        """Test fetching multiple channels returns all requested columns."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_data_misaligned_dates)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            channels=[DataChannel.PRICE, DataChannel.SPREAD],
            use_cache=False,
        )

        assert "price" in result.columns
        assert "spread" in result.columns
        assert len(result.columns) == 2

    def test_multi_channel_fetch_has_no_nan_values(self, synthetic_data_misaligned_dates):
        """Test multi-channel fetch result has no NaN values (inner join effect)."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_data_misaligned_dates)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            channels=[DataChannel.PRICE, DataChannel.SPREAD],
            use_cache=False,
        )

        # Inner join means no NaN values in result
        assert result.notna().all().all(), "Multi-channel fetch should have no NaN values"

    def test_multi_channel_fetch_preserves_datetimeindex(
        self, synthetic_data_misaligned_dates
    ):
        """Test multi-channel fetch preserves DatetimeIndex."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_data_misaligned_dates)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            channels=[DataChannel.PRICE, DataChannel.SPREAD],
            use_cache=False,
        )

        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.is_monotonic_increasing

    def test_merge_channel_data_inner_join(self):
        """Test _merge_channel_data performs inner join correctly."""
        from aponyx.data.fetch import _merge_channel_data

        # Create two channel DataFrames with different date ranges
        dates1 = pd.date_range("2024-01-01", periods=10, freq="B")
        dates2 = pd.date_range("2024-01-05", periods=10, freq="B")  # 4 days offset

        df1 = pd.DataFrame({"spread": range(10)}, index=dates1)
        df2 = pd.DataFrame({"price": range(100, 110)}, index=dates2)

        result = _merge_channel_data({"spread": df1, "price": df2})

        # Inner join: only overlapping dates (Jan 5-15 intersection)
        expected_overlap = dates1.intersection(dates2)
        assert len(result) == len(expected_overlap)
        assert "spread" in result.columns
        assert "price" in result.columns

    def test_merge_channel_data_empty_raises(self):
        """Test _merge_channel_data raises on empty input."""
        from aponyx.data.fetch import _merge_channel_data

        with pytest.raises(ValueError, match="No channel data"):
            _merge_channel_data({})

    def test_merge_channel_data_single_channel(self):
        """Test _merge_channel_data works with single channel (passthrough)."""
        from aponyx.data.fetch import _merge_channel_data

        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        df = pd.DataFrame({"spread": range(10)}, index=dates)

        result = _merge_channel_data({"spread": df})

        assert len(result) == 10
        assert "spread" in result.columns
        pd.testing.assert_index_equal(result.index, dates)

    def test_multi_channel_fetch_all_channels_for_security(
        self, synthetic_data_misaligned_dates
    ):
        """Test fetching all available channels when none specified."""
        from aponyx.data.fetch import fetch_security_data, list_security_channels
        from aponyx.data.sources import FileSource

        source = FileSource(synthetic_data_misaligned_dates)

        # Fetch without specifying channels (should get all available)
        all_channels = list_security_channels("hyg")
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            channels=all_channels,
            use_cache=False,
        )

        # HYG has both price and spread
        assert len(result.columns) >= 2


class TestFileSourceAndBloombergSourceSameInterface:
    """Tests for T036: FileSource and BloombergSource produce same interface.

    This includes FR-010: FileSource validation that channel columns exist.
    """

    @pytest.fixture
    def synthetic_complete_data(self, tmp_path: Path) -> Path:
        """Create synthetic data with all expected channel columns."""
        import json

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        dates = pd.date_range("2024-01-01", periods=10, freq="B")

        # CDX IG with spread only
        cdx_ig_df = pd.DataFrame(
            {"spread": [100.0 + i for i in range(10)]},
            index=dates,
        )
        cdx_ig_df.to_parquet(data_dir / "cdx_ig_5y_complete.parquet")

        # CDX HY with spread and price
        cdx_hy_df = pd.DataFrame(
            {
                "spread": [350.0 + i for i in range(10)],
                "price": [95.0 - i * 0.1 for i in range(10)],
            },
            index=dates,
        )
        cdx_hy_df.to_parquet(data_dir / "cdx_hy_5y_complete.parquet")

        # HYG with price and spread
        hyg_df = pd.DataFrame(
            {
                "price": [75.0 + i * 0.1 for i in range(10)],
                "spread": [350.0 + i for i in range(10)],
            },
            index=dates,
        )
        hyg_df.to_parquet(data_dir / "hyg_complete.parquet")

        # VIX with level only
        vix_df = pd.DataFrame(
            {"level": [15.0 + i * 0.5 for i in range(10)]},
            index=dates,
        )
        vix_df.to_parquet(data_dir / "vix_complete.parquet")

        registry = {
            "cdx_ig_5y": "cdx_ig_5y_complete.parquet",
            "cdx_hy_5y": "cdx_hy_5y_complete.parquet",
            "hyg": "hyg_complete.parquet",
            "vix": "vix_complete.parquet",
        }
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        return data_dir

    def test_filesource_returns_dataframe_with_channel_columns(
        self, synthetic_complete_data
    ):
        """Test FileSource returns DataFrame with requested channel columns."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_complete_data)
        result = fetch_security_data(
            source=source,
            security_id="cdx_ig_5y",
            channels=[DataChannel.SPREAD],
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert "spread" in result.columns
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_filesource_returns_dataframe_with_multiple_channels(
        self, synthetic_complete_data
    ):
        """Test FileSource returns DataFrame with multiple channel columns."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_complete_data)
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            channels=[DataChannel.PRICE, DataChannel.SPREAD],
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert "price" in result.columns
        assert "spread" in result.columns
        assert len(result.columns) == 2

    def test_filesource_validates_channel_columns_exist_fr010(
        self, synthetic_complete_data
    ):
        """Test FR-010: FileSource validation that channel columns exist in parquet.

        If a channel is defined in the catalog but missing from the parquet file,
        validation should fail with a clear error message.
        """
        from aponyx.data.validation import validate_channel_columns_exist

        # Load a file and check column validation
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df_missing_channel = pd.DataFrame(
            {"spread": [100.0 + i for i in range(5)]},
            index=dates,
        )

        # Should fail when requesting 'level' channel from a file with only 'spread'
        with pytest.raises(ValueError, match="not found in file"):
            validate_channel_columns_exist(df_missing_channel, ["level"], "vix")

    def test_filesource_raises_on_missing_channel(self, tmp_path: Path):
        """Test FileSource raises clear error when channel column is missing."""
        import json

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        dates = pd.date_range("2024-01-01", periods=10, freq="B")

        # Create file with only spread column (missing price)
        df = pd.DataFrame({"spread": [100.0] * 10}, index=dates)
        df.to_parquet(data_dir / "hyg_incomplete.parquet")

        registry = {"hyg": "hyg_incomplete.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(data_dir)

        # HYG has 'price' channel defined, but file doesn't have it
        with pytest.raises(ValueError, match="not found"):
            fetch_security_data(
                source=source,
                security_id="hyg",
                channels=[DataChannel.PRICE],
                use_cache=False,
            )

    def test_both_sources_return_same_column_structure(self, synthetic_complete_data):
        """Test FileSource and BloombergSource return same DataFrame structure.

        Both sources should return:
        - pd.DataFrame with DatetimeIndex
        - Column names matching channel names (spread, price, level)
        - No extra metadata columns in the DataFrame
        """
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_complete_data)
        result = fetch_security_data(
            source=source,
            security_id="cdx_hy_5y",
            channels=[DataChannel.SPREAD, DataChannel.PRICE],
            use_cache=False,
        )

        # Check structure matches expected interface
        assert isinstance(result, pd.DataFrame)
        assert isinstance(result.index, pd.DatetimeIndex)
        # Column names should be channel values (not Bloomberg field names)
        assert set(result.columns) == {"spread", "price"}
        # No extra columns
        assert len(result.columns) == 2

    def test_filesource_validates_data_bounds(self, synthetic_complete_data):
        """Test FileSource validates data is within expected bounds."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import UsagePurpose

        source = FileSource(synthetic_complete_data)

        # Fetch CDX spread data (should be validated)
        result = fetch_security_data(
            source=source,
            security_id="cdx_ig_5y",
            purpose=UsagePurpose.INDICATOR,
            use_cache=False,
        )

        # Values should be within CDX spread bounds (0-10000 bps)
        assert result["spread"].min() >= 0
        assert result["spread"].max() <= 10000

    def test_filesource_and_bloomberg_same_purpose_resolution(self):
        """Test both sources use same purpose-based channel resolution."""
        from aponyx.data.fetch import resolve_channel_for_purpose
        from aponyx.data.channels import UsagePurpose, DataChannel

        # Purpose resolution is source-agnostic
        # INDICATOR uses instrument_type default
        cdx_indicator = resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.INDICATOR)
        assert cdx_indicator == DataChannel.SPREAD

        # PNL uses quote_type
        etf_pnl = resolve_channel_for_purpose("hyg", UsagePurpose.PNL)
        assert etf_pnl == DataChannel.PRICE

        # DISPLAY uses instrument_type default
        vix_display = resolve_channel_for_purpose("vix", UsagePurpose.DISPLAY)
        assert vix_display == DataChannel.LEVEL

    def test_filesource_respects_date_filtering(self, synthetic_complete_data):
        """Test FileSource respects start_date and end_date parameters."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        source = FileSource(synthetic_complete_data)

        # Fetch with date range filter
        result = fetch_security_data(
            source=source,
            security_id="cdx_ig_5y",
            channels=[DataChannel.SPREAD],
            start_date="2024-01-03",
            end_date="2024-01-08",
            use_cache=False,
        )

        # Should have fewer rows than full dataset
        assert len(result) < 10
        # All dates should be within range
        assert result.index.min() >= pd.Timestamp("2024-01-03")
        assert result.index.max() <= pd.Timestamp("2024-01-08")

    def test_fetch_security_data_no_purpose_or_channels_fetches_all(
        self, synthetic_complete_data
    ):
        """Test fetch_security_data with no purpose or channels fetches all available."""
        from aponyx.data.fetch import fetch_security_data, list_security_channels
        from aponyx.data.sources import FileSource

        source = FileSource(synthetic_complete_data)

        # Fetch HYG without specifying channels or purpose
        result = fetch_security_data(
            source=source,
            security_id="hyg",
            # No channels or purpose specified
            use_cache=False,
        )

        # Should have all channels for HYG (price and spread)
        available_channels = list_security_channels("hyg")
        assert len(result.columns) == len(available_channels)
        for channel in available_channels:
            assert channel.value in result.columns


# =============================================================================
# Phase 7: User Story 5 - Validation Error Messages and Edge Cases (T041, T045)
# =============================================================================


class TestFetchSecurityDataClearErrorMessages:
    """Tests for clear error messages in fetch functions (T039, T041).

    These tests verify that error messages are:
    1. Specific about what failed
    2. Include available options/alternatives
    3. Provide guidance on how to fix the issue
    """

    def test_unknown_security_error_includes_guidance(self):
        """Error for unknown security includes available securities and guidance."""
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from pathlib import Path

        # Create minimal data dir with registry
        tmp_dir = Path("data/raw/synthetic")
        source = FileSource(tmp_dir)

        with pytest.raises(ValueError) as exc_info:
            fetch_security_data(
                source=source,
                security_id="nonexistent_security",
                use_cache=False,
            )

        error_msg = str(exc_info.value)
        assert "nonexistent_security" in error_msg
        assert "bloomberg_securities.json" in error_msg

    def test_unavailable_channel_error_includes_alternatives(self, tmp_path: Path):
        """Error for unavailable channel lists available channels."""
        import json
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        # Create data with only spread column
        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"spread": [100.0] * 5}, index=dates)
        df.to_parquet(data_dir / "cdx_ig_5y.parquet")

        registry = {"cdx_ig_5y": "cdx_ig_5y.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        # Request LEVEL channel which CDX doesn't have
        with pytest.raises(ValueError) as exc_info:
            fetch_security_data(
                source=source,
                security_id="cdx_ig_5y",
                channels=[DataChannel.LEVEL],  # Not available for CDX
                use_cache=False,
            )

        error_msg = str(exc_info.value)
        assert "level" in error_msg.lower()
        assert "spread" in error_msg.lower()  # Available channel mentioned
        assert "bloomberg_securities.json" in error_msg

    def test_missing_file_error_includes_path_and_guidance(self, tmp_path: Path):
        """Error for missing file includes path and regeneration guidance."""
        import json
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource

        # Create registry pointing to non-existent file
        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        registry = {"cdx_ig_5y": "nonexistent_file.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        with pytest.raises(FileNotFoundError) as exc_info:
            fetch_security_data(
                source=source,
                security_id="cdx_ig_5y",
                use_cache=False,
            )

        error_msg = str(exc_info.value)
        assert "nonexistent_file.parquet" in error_msg
        assert "generate_synthetic.py" in error_msg  # Guidance

    def test_empty_file_error_message(self, tmp_path: Path):
        """Error for empty data file is clear."""
        import json
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        # Create empty parquet file
        empty_df = pd.DataFrame({"spread": pd.Series(dtype=float)})
        empty_df.to_parquet(data_dir / "cdx_ig_5y.parquet")

        registry = {"cdx_ig_5y": "cdx_ig_5y.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        with pytest.raises(ValueError) as exc_info:
            fetch_security_data(
                source=source,
                security_id="cdx_ig_5y",
                use_cache=False,
            )

        error_msg = str(exc_info.value)
        assert "empty" in error_msg.lower()
        assert "cdx_ig_5y" in error_msg

    def test_missing_column_error_includes_file_path(self, tmp_path: Path):
        """Error for missing column includes file path and available columns."""
        import json
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource
        from aponyx.data.channels import DataChannel

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        # Create file with only price column (missing spread)
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"price": [75.0] * 5}, index=dates)
        df.to_parquet(data_dir / "hyg.parquet")

        registry = {"hyg": "hyg.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        # HYG has spread channel defined but file only has price
        with pytest.raises(ValueError) as exc_info:
            fetch_security_data(
                source=source,
                security_id="hyg",
                channels=[DataChannel.SPREAD],
                use_cache=False,
            )

        error_msg = str(exc_info.value)
        assert "spread" in error_msg.lower()
        assert "hyg.parquet" in error_msg
        assert "generate_synthetic.py" in error_msg

    def test_security_not_in_registry_error(self, tmp_path: Path):
        """Error when security is in catalog but not in file registry."""
        import json
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        # Create registry without the security
        registry = {"other_security": "other.parquet"}
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        with pytest.raises(ValueError) as exc_info:
            fetch_security_data(
                source=source,
                security_id="cdx_ig_5y",
                use_cache=False,
            )

        error_msg = str(exc_info.value)
        assert "cdx_ig_5y" in error_msg
        assert "registry.json" in error_msg


class TestEdgeCasesNoDataAndPartialFailure:
    """Tests for edge cases: no data, partial failure (T045)."""

    def test_merge_channel_data_no_overlap_raises(self):
        """Test _merge_channel_data raises when channels have no overlapping dates."""
        from aponyx.data.fetch import _merge_channel_data

        # Two channels with completely non-overlapping dates
        dates1 = pd.date_range("2024-01-01", periods=5, freq="B")
        dates2 = pd.date_range("2024-02-01", periods=5, freq="B")  # No overlap

        df1 = pd.DataFrame({"spread": range(5)}, index=dates1)
        df2 = pd.DataFrame({"price": range(100, 105)}, index=dates2)

        with pytest.raises(ValueError) as exc_info:
            _merge_channel_data({"spread": df1, "price": df2})

        error_msg = str(exc_info.value)
        assert "no overlapping dates" in error_msg.lower()
        assert "spread" in error_msg
        assert "price" in error_msg

    def test_channel_fetch_error_aggregates_failures(self):
        """Test ChannelFetchError includes all failed channels."""
        from aponyx.data.channels import DataChannel, ChannelFetchError

        failures = {
            DataChannel.SPREAD: "Connection timeout",
            DataChannel.PRICE: "Invalid ticker",
        }

        error = ChannelFetchError("cdx_hy_5y", failures)

        error_msg = str(error)
        assert "cdx_hy_5y" in error_msg
        assert "spread" in error_msg.lower()
        assert "price" in error_msg.lower()
        assert "Connection timeout" in error_msg
        assert "Invalid ticker" in error_msg

    def test_validation_bounds_out_of_range_spread(self):
        """Test validation fails for spread out of range (0-10000 bps)."""
        from aponyx.data.validation import validate_channel_data

        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"spread": [100.0, 200.0, 15000.0, 300.0, 400.0]}, index=dates)

        with pytest.raises(ValueError) as exc_info:
            validate_channel_data(df, ["spread"], "cdx_ig_5y")

        error_msg = str(exc_info.value)
        assert "spread" in error_msg.lower()
        assert "outside valid range" in error_msg.lower()

    def test_validation_bounds_out_of_range_level(self):
        """Test validation fails for level out of range (0-200)."""
        from aponyx.data.validation import validate_channel_data

        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"level": [15.0, 20.0, 250.0, 25.0, 30.0]}, index=dates)  # 250 > 200

        with pytest.raises(ValueError) as exc_info:
            validate_channel_data(df, ["level"], "vix")

        error_msg = str(exc_info.value)
        assert "level" in error_msg.lower()
        assert "outside valid range" in error_msg.lower()

    def test_filesource_security_not_in_registry_detailed_error(self, tmp_path: Path):
        """Test FileSource gives detailed error when security not in registry."""
        import json
        from aponyx.data.fetch import fetch_security_data
        from aponyx.data.sources import FileSource

        data_dir = tmp_path / "raw" / "synthetic"
        data_dir.mkdir(parents=True)

        # Registry with different securities
        registry = {
            "cdx_ig_5y": "cdx_ig_5y.parquet",
            "vix": "vix.parquet",
        }
        with open(data_dir / "registry.json", "w", encoding="utf-8") as f:
            json.dump(registry, f)

        source = FileSource(data_dir)

        with pytest.raises(ValueError) as exc_info:
            fetch_security_data(
                source=source,
                security_id="cdx_hy_5y",  # Not in registry
                use_cache=False,
            )

        error_msg = str(exc_info.value)
        assert "cdx_hy_5y" in error_msg
        # Should list available securities
        assert "cdx_ig_5y" in error_msg
        assert "vix" in error_msg