"""Tests for security catalog registry."""

import json
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from aponyx.data.channels import DataChannel, UsagePurpose, ChannelConfig
from aponyx.data.security_catalog import SecuritySpec, SecurityCatalog
from aponyx.config import BLOOMBERG_SECURITIES_PATH


class TestSecuritySpec:
    """Tests for SecuritySpec dataclass."""

    def test_create_valid_spread_security(self):
        """Can create valid spread-quoted security."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("CDX IG CDSI GEN 5Y Corp"),
        }
        spec = SecuritySpec(
            security_id="cdx_ig_5y",
            description="CDX NA IG 5Y",
            instrument_type="cdx",
            quote_type="spread",
            channels=channels,
            dv01_per_million=475.0,
        )
        assert spec.security_id == "cdx_ig_5y"
        assert spec.quote_type == "spread"
        assert spec.dv01_per_million == 475.0

    def test_create_valid_price_security(self):
        """Can create valid price-quoted security."""
        channels = {
            DataChannel.PRICE: ChannelConfig("HYG US Equity"),
        }
        spec = SecuritySpec(
            security_id="hyg",
            description="HYG ETF",
            instrument_type="etf",
            quote_type="price",
            channels=channels,
        )
        assert spec.security_id == "hyg"
        assert spec.quote_type == "price"
        assert spec.dv01_per_million is None

    def test_spread_quote_requires_dv01(self):
        """Spread quote_type requires dv01_per_million."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("CDX IG CDSI GEN 5Y Corp"),
        }
        with pytest.raises(ValueError, match="missing dv01_per_million"):
            SecuritySpec(
                security_id="cdx_ig_5y",
                description="CDX NA IG 5Y",
                instrument_type="cdx",
                quote_type="spread",
                channels=channels,
            )

    def test_at_least_one_channel_required(self):
        """At least one channel must be defined."""
        with pytest.raises(ValueError, match="must define at least one channel"):
            SecuritySpec(
                security_id="test",
                description="Test",
                instrument_type="cdx",
                quote_type="price",
                channels={},
            )

    def test_invalid_quote_type_raises(self):
        """Invalid quote_type raises ValueError."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("TICKER"),
        }
        with pytest.raises(ValueError, match="invalid quote_type"):
            SecuritySpec(
                security_id="test",
                description="Test",
                instrument_type="cdx",
                quote_type="invalid",
                channels=channels,
                dv01_per_million=100.0,
            )

    def test_invalid_instrument_type_raises(self):
        """Invalid instrument_type raises ValueError."""
        channels = {
            DataChannel.PRICE: ChannelConfig("TICKER"),
        }
        with pytest.raises(ValueError, match="unknown instrument_type"):
            SecuritySpec(
                security_id="test",
                description="Test",
                instrument_type="unknown",
                quote_type="price",
                channels=channels,
            )

    def test_has_channel(self):
        """has_channel correctly checks channel availability."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("CDX TICKER"),
            DataChannel.PRICE: ChannelConfig("CDX PRICE TICKER"),
        }
        spec = SecuritySpec(
            security_id="cdx_hy_5y",
            description="CDX HY",
            instrument_type="cdx",
            quote_type="spread",
            channels=channels,
            dv01_per_million=425.0,
        )
        assert spec.has_channel(DataChannel.SPREAD)
        assert spec.has_channel(DataChannel.PRICE)
        assert not spec.has_channel(DataChannel.LEVEL)

    def test_get_channel_config(self):
        """get_channel_config returns correct config."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("CDX TICKER", "PX_LAST"),
        }
        spec = SecuritySpec(
            security_id="cdx_ig_5y",
            description="CDX IG",
            instrument_type="cdx",
            quote_type="spread",
            channels=channels,
            dv01_per_million=475.0,
        )
        config = spec.get_channel_config(DataChannel.SPREAD)
        assert config.bloomberg_ticker == "CDX TICKER"
        assert config.field == "PX_LAST"

    def test_get_channel_config_unavailable_raises(self):
        """get_channel_config raises for unavailable channel."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("CDX TICKER"),
        }
        spec = SecuritySpec(
            security_id="cdx_ig_5y",
            description="CDX IG",
            instrument_type="cdx",
            quote_type="spread",
            channels=channels,
            dv01_per_million=475.0,
        )
        with pytest.raises(ValueError, match="not available"):
            spec.get_channel_config(DataChannel.LEVEL)

    def test_list_channels(self):
        """list_channels returns all available channels."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("SPREAD TICKER"),
            DataChannel.PRICE: ChannelConfig("PRICE TICKER"),
        }
        spec = SecuritySpec(
            security_id="cdx_hy_5y",
            description="CDX HY",
            instrument_type="cdx",
            quote_type="spread",
            channels=channels,
            dv01_per_million=425.0,
        )
        available = spec.list_channels()
        assert DataChannel.SPREAD in available
        assert DataChannel.PRICE in available
        assert len(available) == 2


class TestSecurityCatalog:
    """Tests for SecurityCatalog registry."""

    def test_load_from_bloomberg_securities(self):
        """Can load catalog from bloomberg_securities.json."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        assert len(catalog) > 0
        assert "cdx_ig_5y" in catalog
        assert "vix" in catalog

    def test_get_spec_existing(self):
        """get_spec returns spec for existing security."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        spec = catalog.get_spec("cdx_ig_5y")
        assert spec.security_id == "cdx_ig_5y"
        assert spec.instrument_type == "cdx"

    def test_get_spec_unknown_raises(self):
        """get_spec raises for unknown security."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        with pytest.raises(ValueError, match="Unknown security"):
            catalog.get_spec("nonexistent")

    def test_list_securities_all(self):
        """list_securities returns all securities."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        securities = catalog.list_securities()
        assert "cdx_ig_5y" in securities
        assert "hyg" in securities
        assert "vix" in securities

    def test_list_securities_filtered(self):
        """list_securities filters by instrument type."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)

        cdx_securities = catalog.list_securities(instrument_type="cdx")
        assert "cdx_ig_5y" in cdx_securities
        assert "hyg" not in cdx_securities

        etf_securities = catalog.list_securities(instrument_type="etf")
        assert "hyg" in etf_securities
        assert "cdx_ig_5y" not in etf_securities

    def test_resolve_channel_indicator_cdx(self):
        """resolve_channel returns spread for CDX indicator purpose."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        channel = catalog.resolve_channel("cdx_ig_5y", UsagePurpose.INDICATOR)
        assert channel == DataChannel.SPREAD

    def test_resolve_channel_indicator_vix(self):
        """resolve_channel returns level for VIX indicator purpose."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        channel = catalog.resolve_channel("vix", UsagePurpose.INDICATOR)
        assert channel == DataChannel.LEVEL

    def test_resolve_channel_pnl_spread_product(self):
        """resolve_channel returns spread for spread-quoted product P&L."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        channel = catalog.resolve_channel("cdx_ig_5y", UsagePurpose.PNL)
        assert channel == DataChannel.SPREAD

    def test_resolve_channel_pnl_price_product(self):
        """resolve_channel returns price for price-quoted product P&L."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        channel = catalog.resolve_channel("hyg", UsagePurpose.PNL)
        assert channel == DataChannel.PRICE

    def test_resolve_channel_with_override(self):
        """resolve_channel respects override parameter."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        # CDX HY has both spread and price channels
        channel = catalog.resolve_channel(
            "cdx_hy_5y",
            UsagePurpose.INDICATOR,
            override=DataChannel.PRICE,
        )
        assert channel == DataChannel.PRICE

    def test_resolve_channel_invalid_override_raises(self):
        """resolve_channel raises for unavailable override channel."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        # VIX only has LEVEL channel
        with pytest.raises(ValueError, match="not available"):
            catalog.resolve_channel(
                "vix",
                UsagePurpose.DISPLAY,
                override=DataChannel.SPREAD,
            )

    def test_contains(self):
        """Catalog supports 'in' operator."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        assert "cdx_ig_5y" in catalog
        assert "nonexistent" not in catalog


class TestSecurityCatalogValidation:
    """Tests for catalog validation."""

    def test_invalid_channel_name_raises(self):
        """Invalid channel name in JSON raises ValueError."""
        invalid_catalog = {
            "test_security": {
                "description": "Test",
                "instrument_type": "cdx",
                "quote_type": "spread",
                "channels": {
                    "invalid_channel": {
                        "bloomberg_ticker": "TICKER",
                    },
                },
                "dv01_per_million": 100.0,
            },
        }
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_catalog, f)
            f.flush()
            with pytest.raises(ValueError, match="invalid channel name"):
                SecurityCatalog(Path(f.name))

    def test_missing_file_raises(self):
        """Missing catalog file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SecurityCatalog(Path("/nonexistent/path.json"))

    def test_spread_product_without_spread_channel_raises(self):
        """Spread-quoted product without spread channel fails validation."""
        invalid_catalog = {
            "test_security": {
                "description": "Test",
                "instrument_type": "cdx",
                "quote_type": "spread",
                "channels": {
                    "price": {
                        "bloomberg_ticker": "TICKER",
                    },
                },
                "dv01_per_million": 100.0,
            },
        }
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_catalog, f)
            f.flush()
            with pytest.raises(ValueError, match="no SPREAD channel"):
                SecurityCatalog(Path(f.name))

    def test_price_product_without_price_channel_raises(self):
        """Price-quoted product without price channel fails validation."""
        invalid_catalog = {
            "test_security": {
                "description": "Test",
                "instrument_type": "etf",
                "quote_type": "price",
                "channels": {
                    "spread": {
                        "bloomberg_ticker": "TICKER",
                    },
                },
            },
        }
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_catalog, f)
            f.flush()
            with pytest.raises(ValueError, match="no PRICE channel"):
                SecurityCatalog(Path(f.name))


# =============================================================================
# Phase 7: User Story 5 - Security Configuration Validation Tests (T040)
# =============================================================================


class TestSecuritySpecEnhancedValidation:
    """Tests for enhanced SecuritySpec validation (T037).

    These tests verify:
    1. quote_type='spread' requires dv01_per_million
    2. dv01_per_million must be positive
    3. quote_type must have corresponding channel
    4. Clear error messages for all validation failures
    """

    def test_spread_quote_requires_positive_dv01(self):
        """quote_type='spread' requires positive dv01_per_million."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("CDX TICKER"),
        }
        # Zero DV01 should fail
        with pytest.raises(ValueError, match="DV01 must be a positive value"):
            SecuritySpec(
                security_id="test",
                description="Test",
                instrument_type="cdx",
                quote_type="spread",
                channels=channels,
                dv01_per_million=0.0,
            )

        # Negative DV01 should fail
        with pytest.raises(ValueError, match="DV01 must be a positive value"):
            SecuritySpec(
                security_id="test",
                description="Test",
                instrument_type="cdx",
                quote_type="spread",
                channels=channels,
                dv01_per_million=-100.0,
            )

    def test_spread_quote_dv01_missing_error_message(self):
        """Error message for missing DV01 is clear and actionable."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("CDX TICKER"),
        }
        with pytest.raises(ValueError) as exc_info:
            SecuritySpec(
                security_id="cdx_test",
                description="Test",
                instrument_type="cdx",
                quote_type="spread",
                channels=channels,
            )
        
        error_msg = str(exc_info.value)
        assert "cdx_test" in error_msg
        assert "quote_type='spread'" in error_msg
        assert "dv01_per_million" in error_msg
        assert "P&L calculation" in error_msg

    def test_spread_quote_without_spread_channel_error_message(self):
        """Error message for missing spread channel includes available channels."""
        channels = {
            DataChannel.PRICE: ChannelConfig("PRICE TICKER"),
        }
        with pytest.raises(ValueError) as exc_info:
            SecuritySpec(
                security_id="cdx_test",
                description="Test",
                instrument_type="cdx",
                quote_type="spread",
                channels=channels,
                dv01_per_million=475.0,
            )
        
        error_msg = str(exc_info.value)
        assert "cdx_test" in error_msg
        assert "no SPREAD channel" in error_msg
        assert "price" in error_msg.lower()  # Available channels mentioned
        assert "P&L" in error_msg

    def test_price_quote_without_price_channel_error_message(self):
        """Error message for missing price channel is clear."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("SPREAD TICKER"),
        }
        with pytest.raises(ValueError) as exc_info:
            SecuritySpec(
                security_id="etf_test",
                description="Test",
                instrument_type="etf",
                quote_type="price",
                channels=channels,
            )
        
        error_msg = str(exc_info.value)
        assert "etf_test" in error_msg
        assert "no PRICE channel" in error_msg
        assert "spread" in error_msg.lower()  # Available channels mentioned

    def test_get_channel_config_error_includes_guidance(self):
        """get_channel_config error message includes guidance."""
        channels = {
            DataChannel.SPREAD: ChannelConfig("SPREAD TICKER"),
        }
        spec = SecuritySpec(
            security_id="cdx_test",
            description="Test",
            instrument_type="cdx",
            quote_type="spread",
            channels=channels,
            dv01_per_million=475.0,
        )
        
        with pytest.raises(ValueError) as exc_info:
            spec.get_channel_config(DataChannel.PRICE)
        
        error_msg = str(exc_info.value)
        assert "price" in error_msg.lower()
        assert "cdx_test" in error_msg
        assert "bloomberg_securities.json" in error_msg


class TestSecurityCatalogResolveChannelValidation:
    """Tests for channel resolution validation (T038).

    These tests verify clear error messages for:
    1. Invalid channel override
    2. Missing default channel for purpose
    3. P&L channel mismatch
    """

    def test_resolve_channel_invalid_override_error_message(self):
        """Invalid channel override error includes available channels."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        
        with pytest.raises(ValueError) as exc_info:
            catalog.resolve_channel(
                "vix",
                UsagePurpose.INDICATOR,
                override=DataChannel.SPREAD,
            )
        
        error_msg = str(exc_info.value)
        assert "vix" in error_msg
        assert "spread" in error_msg.lower()
        assert "level" in error_msg.lower()  # Available channel
        assert "bloomberg_securities.json" in error_msg

    def test_resolve_channel_error_includes_purpose(self):
        """Channel resolution error includes purpose context."""
        # Create a custom catalog with missing channel
        invalid_catalog = {
            "test_security": {
                "description": "Test",
                "instrument_type": "etf",  # ETF defaults to spread for indicator
                "quote_type": "price",
                "channels": {
                    "price": {"bloomberg_ticker": "TICKER"},
                    # Missing spread channel - indicator won't work
                },
            },
        }
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_catalog, f)
            f.flush()
            catalog = SecurityCatalog(Path(f.name))
            
            with pytest.raises(ValueError) as exc_info:
                catalog.resolve_channel("test_security", UsagePurpose.INDICATOR)
            
            error_msg = str(exc_info.value)
            assert "indicator" in error_msg.lower()
            assert "spread" in error_msg.lower()  # Default channel for ETF indicator

    def test_catalog_get_spec_unknown_error_message(self):
        """get_spec for unknown security shows available securities."""
        catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
        
        with pytest.raises(ValueError) as exc_info:
            catalog.get_spec("nonexistent_security")
        
        error_msg = str(exc_info.value)
        assert "nonexistent_security" in error_msg
        assert "cdx_ig_5y" in error_msg  # Shows available securities


class TestSecuritySpecDv01Warning:
    """Tests for DV01 warning on price-quoted products."""

    def test_dv01_on_price_product_logs_warning(self, caplog):
        """DV01 provided for price-quoted product logs warning."""
        import logging
        
        channels = {
            DataChannel.PRICE: ChannelConfig("HYG US Equity"),
        }
        
        with caplog.at_level(logging.WARNING):
            spec = SecuritySpec(
                security_id="hyg_test",
                description="Test",
                instrument_type="etf",
                quote_type="price",
                channels=channels,
                dv01_per_million=100.0,  # Not needed for price products
            )
        
        # Spec should be created successfully
        assert spec.dv01_per_million == 100.0
        
        # Warning should be logged
        assert any("hyg_test" in record.message for record in caplog.records)
        assert any("price" in record.message for record in caplog.records)
