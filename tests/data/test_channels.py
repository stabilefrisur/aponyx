"""Tests for data channel types and resolution logic."""

import pytest

from aponyx.data.channels import (
    DataChannel,
    UsagePurpose,
    ChannelConfig,
    ChannelFetchError,
    INSTRUMENT_DEFAULTS,
)


class TestDataChannel:
    """Tests for DataChannel enum."""

    def test_spread_channel_value(self):
        """DataChannel.SPREAD has correct string value."""
        assert DataChannel.SPREAD.value == "spread"

    def test_price_channel_value(self):
        """DataChannel.PRICE has correct string value."""
        assert DataChannel.PRICE.value == "price"

    def test_level_channel_value(self):
        """DataChannel.LEVEL has correct string value."""
        assert DataChannel.LEVEL.value == "level"

    def test_channel_from_string(self):
        """Can create DataChannel from string value."""
        assert DataChannel("spread") == DataChannel.SPREAD
        assert DataChannel("price") == DataChannel.PRICE
        assert DataChannel("level") == DataChannel.LEVEL

    def test_invalid_channel_raises(self):
        """Invalid channel string raises ValueError."""
        with pytest.raises(ValueError):
            DataChannel("invalid")


class TestUsagePurpose:
    """Tests for UsagePurpose enum."""

    def test_indicator_purpose_value(self):
        """UsagePurpose.INDICATOR has correct string value."""
        assert UsagePurpose.INDICATOR.value == "indicator"

    def test_pnl_purpose_value(self):
        """UsagePurpose.PNL has correct string value."""
        assert UsagePurpose.PNL.value == "pnl"

    def test_display_purpose_value(self):
        """UsagePurpose.DISPLAY has correct string value."""
        assert UsagePurpose.DISPLAY.value == "display"

    def test_purpose_from_string(self):
        """Can create UsagePurpose from string value."""
        assert UsagePurpose("indicator") == UsagePurpose.INDICATOR
        assert UsagePurpose("pnl") == UsagePurpose.PNL
        assert UsagePurpose("display") == UsagePurpose.DISPLAY


class TestChannelConfig:
    """Tests for ChannelConfig dataclass."""

    def test_create_with_ticker_only(self):
        """Can create ChannelConfig with just ticker (default field)."""
        config = ChannelConfig(bloomberg_ticker="CDX IG CDSI GEN 5Y Corp")
        assert config.bloomberg_ticker == "CDX IG CDSI GEN 5Y Corp"
        assert config.field == "PX_LAST"

    def test_create_with_custom_field(self):
        """Can create ChannelConfig with custom field."""
        config = ChannelConfig(
            bloomberg_ticker="HYG US Equity",
            field="YAS_ISPREAD",
        )
        assert config.bloomberg_ticker == "HYG US Equity"
        assert config.field == "YAS_ISPREAD"

    def test_empty_ticker_raises(self):
        """Empty ticker string raises ValueError."""
        with pytest.raises(ValueError, match="bloomberg_ticker must not be empty"):
            ChannelConfig(bloomberg_ticker="")

    def test_empty_field_raises(self):
        """Empty field string raises ValueError."""
        with pytest.raises(ValueError, match="field must not be empty"):
            ChannelConfig(bloomberg_ticker="CDX IG", field="")

    def test_frozen_immutable(self):
        """ChannelConfig is immutable (frozen)."""
        config = ChannelConfig(bloomberg_ticker="CDX IG CDSI GEN 5Y Corp")
        with pytest.raises(AttributeError):
            config.bloomberg_ticker = "NEW TICKER"


class TestChannelFetchError:
    """Tests for ChannelFetchError exception."""

    def test_single_failure(self):
        """ChannelFetchError with single channel failure."""
        error = ChannelFetchError(
            security_id="cdx_ig_5y",
            failures={DataChannel.SPREAD: "Connection timeout"},
        )
        assert error.security_id == "cdx_ig_5y"
        assert DataChannel.SPREAD in error.failures
        assert "cdx_ig_5y" in str(error)
        assert "spread" in str(error)

    def test_multiple_failures(self):
        """ChannelFetchError with multiple channel failures."""
        error = ChannelFetchError(
            security_id="cdx_hy_5y",
            failures={
                DataChannel.SPREAD: "Connection timeout",
                DataChannel.PRICE: "Invalid ticker",
            },
        )
        assert len(error.failures) == 2
        assert "spread" in str(error)
        assert "price" in str(error)

    def test_error_is_exception(self):
        """ChannelFetchError is an Exception and can be raised/caught."""
        with pytest.raises(ChannelFetchError) as exc_info:
            raise ChannelFetchError(
                security_id="test",
                failures={DataChannel.LEVEL: "Error"},
            )
        assert exc_info.value.security_id == "test"


class TestInstrumentDefaults:
    """Tests for INSTRUMENT_DEFAULTS mapping."""

    def test_cdx_defaults(self):
        """CDX instrument type has correct defaults."""
        assert "cdx" in INSTRUMENT_DEFAULTS
        assert INSTRUMENT_DEFAULTS["cdx"]["indicator"] == DataChannel.SPREAD
        assert INSTRUMENT_DEFAULTS["cdx"]["display"] == DataChannel.SPREAD

    def test_etf_defaults(self):
        """ETF instrument type has correct defaults."""
        assert "etf" in INSTRUMENT_DEFAULTS
        assert INSTRUMENT_DEFAULTS["etf"]["indicator"] == DataChannel.SPREAD
        assert INSTRUMENT_DEFAULTS["etf"]["display"] == DataChannel.SPREAD

    def test_vix_defaults(self):
        """VIX instrument type has correct defaults."""
        assert "vix" in INSTRUMENT_DEFAULTS
        assert INSTRUMENT_DEFAULTS["vix"]["indicator"] == DataChannel.LEVEL
        assert INSTRUMENT_DEFAULTS["vix"]["display"] == DataChannel.LEVEL

    def test_all_instrument_types_have_indicator_and_display(self):
        """All instrument types have both indicator and display defaults."""
        for inst_type, defaults in INSTRUMENT_DEFAULTS.items():
            assert "indicator" in defaults, f"{inst_type} missing indicator default"
            assert "display" in defaults, f"{inst_type} missing display default"
