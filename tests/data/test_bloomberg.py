"""
Tests for Bloomberg data provider.

Mocks xbbg module to test Bloomberg provider functionality without Terminal.
"""

import logging
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Mock xbbg module before importing bloomberg provider
mock_blp = MagicMock()
mock_xbbg = MagicMock()
mock_xbbg.blp = mock_blp
sys.modules["xbbg"] = mock_xbbg
sys.modules["xbbg.blp"] = mock_blp

from aponyx.data.providers.bloomberg import (
    fetch_from_bloomberg,
    _map_bloomberg_fields,
    _add_security_metadata,
)
from aponyx.data.bloomberg_config import (
    get_instrument_spec,
    get_security_spec,
    get_bloomberg_ticker,
    get_security_from_ticker,
    list_instrument_types,
    list_securities,
)

logger = logging.getLogger(__name__)


class TestBloombergCatalog:
    """Test Bloomberg catalog registry functions."""

    def test_get_instrument_spec_cdx(self):
        """Test getting CDX instrument specification."""
        spec = get_instrument_spec("cdx")

        assert spec.instrument_type == "cdx"
        assert spec.description == "CDX credit default swap indices"
        assert spec.bloomberg_fields == ("PX_LAST",)
        assert spec.field_mapping == {"PX_LAST": "spread"}
        assert spec.requires_security_metadata is True

    def test_get_instrument_spec_vix(self):
        """Test getting VIX instrument specification."""
        spec = get_instrument_spec("vix")

        assert spec.instrument_type == "vix"
        assert spec.bloomberg_fields == ("PX_LAST",)
        assert spec.field_mapping == {"PX_LAST": "level"}
        assert spec.requires_security_metadata is False

    def test_get_instrument_spec_etf(self):
        """Test getting ETF instrument specification."""
        spec = get_instrument_spec("etf")

        assert spec.instrument_type == "etf"
        assert spec.bloomberg_fields == ("YAS_ISPREAD",)
        assert spec.field_mapping == {"YAS_ISPREAD": "spread"}
        assert spec.requires_security_metadata is True

    def test_get_instrument_spec_invalid(self):
        """Test error on invalid instrument type."""
        with pytest.raises(ValueError, match="Unknown instrument type"):
            get_instrument_spec("invalid")

    def test_get_security_spec(self):
        """Test getting security specification."""
        spec = get_security_spec("cdx_ig_5y")

        assert spec.security_id == "cdx_ig_5y"
        assert spec.bloomberg_ticker == "CDX IG CDSI GEN 5Y Corp"
        assert spec.instrument_type == "cdx"
        assert "Investment Grade" in spec.description

    def test_get_security_spec_invalid(self):
        """Test error on invalid security ID."""
        with pytest.raises(ValueError, match="not found in catalog"):
            get_security_spec("invalid_security")

    def test_get_bloomberg_ticker(self):
        """Test getting Bloomberg ticker from security ID."""
        assert get_bloomberg_ticker("cdx_ig_5y") == "CDX IG CDSI GEN 5Y Corp"
        assert get_bloomberg_ticker("hyg") == "HYG US Equity"
        assert get_bloomberg_ticker("vix") == "VIX Index"

    def test_get_security_from_ticker(self):
        """Test reverse lookup from Bloomberg ticker."""
        assert get_security_from_ticker("CDX IG CDSI GEN 5Y Corp") == "cdx_ig_5y"
        assert get_security_from_ticker("HYG US Equity") == "hyg"
        assert get_security_from_ticker("VIX Index") == "vix"

    def test_get_security_from_ticker_invalid(self):
        """Test error on unregistered Bloomberg ticker."""
        with pytest.raises(ValueError, match="not found in catalog"):
            get_security_from_ticker("INVALID TICKER")

    def test_list_instrument_types(self):
        """Test listing all instrument types."""
        types = list_instrument_types()

        assert isinstance(types, list)
        assert "cdx" in types
        assert "vix" in types
        assert "etf" in types

    def test_list_securities_all(self):
        """Test listing all securities."""
        securities = list_securities()

        assert isinstance(securities, list)
        assert len(securities) == 8
        assert "cdx_ig_5y" in securities
        assert "hyg" in securities
        assert "vix" in securities

    def test_list_securities_by_instrument(self):
        """Test listing securities filtered by instrument type."""
        cdx_securities = list_securities(instrument_type="cdx")
        etf_securities = list_securities(instrument_type="etf")
        vix_securities = list_securities(instrument_type="vix")

        assert "cdx_ig_5y" in cdx_securities
        assert "cdx_hy_5y" in cdx_securities
        assert "hyg" in etf_securities
        assert "lqd" in etf_securities
        assert "vix" in vix_securities
        assert len(vix_securities) == 1


logger = logging.getLogger(__name__)


@pytest.fixture
def mock_xbbg_response():
    """Create mock xbbg response DataFrame."""
    dates = pd.date_range("2023-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"PX_LAST": [100.0, 101.0, 102.0, 103.0, 104.0]},
        index=dates,
    )
    return df


@pytest.fixture
def mock_xbbg_etf_response():
    """Create mock xbbg response DataFrame for ETF data."""
    dates = pd.date_range("2023-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {"YAS_ISPREAD": [85.0, 86.0, 87.0, 88.0, 89.0]},
        index=dates,
    )
    return df


@pytest.fixture
def mock_xbbg_multiindex_response():
    """Create mock xbbg response with multi-index columns."""
    dates = pd.date_range("2023-01-01", periods=5, freq="D")
    df = pd.DataFrame(
        {("CDX IG CDSI GEN 5Y Corp", "PX_LAST"): [100.0, 101.0, 102.0, 103.0, 104.0]},
        index=dates,
    )
    return df


class TestFetchFromBloomberg:
    """Test main fetch_from_bloomberg function."""

    def test_fetch_cdx_success(self, mock_xbbg_response):
        """Test successful CDX data fetch."""
        # Patch both the module and bdh method to ensure mock works
        with patch("xbbg.blp.bdh", return_value=mock_xbbg_response) as mock_bdh:
            result = fetch_from_bloomberg(
                ticker="CDX IG CDSI GEN 5Y Corp",
                instrument="cdx",
                start_date="2023-01-01",
                end_date="2023-01-05",
                security="cdx_ig_5y",
            )

            # Verify blp.bdh called with correct arguments
            mock_bdh.assert_called_once_with(
                tickers="CDX IG CDSI GEN 5Y Corp",
                flds=("PX_LAST",),
                start_date="20230101",
                end_date="20230105",
            )

            # Verify DataFrame structure
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 5
            assert "spread" in result.columns
            assert "security" in result.columns
            assert result["security"].iloc[0] == "cdx_ig_5y"

    def test_fetch_vix_success(self, mock_xbbg_response):
        """Test successful VIX data fetch."""
        with patch("xbbg.blp.bdh", return_value=mock_xbbg_response) as mock_bdh:
            result = fetch_from_bloomberg(
                ticker="VIX Index",
                instrument="vix",
                start_date="2023-01-01",
                end_date="2023-01-05",
                security="vix",
            )

            # Verify DataFrame structure
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 5
            assert "level" in result.columns
            assert "security" not in result.columns  # VIX has no metadata

    def test_fetch_etf_success(self, mock_xbbg_etf_response):
        """Test successful ETF data fetch."""
        with patch("xbbg.blp.bdh", return_value=mock_xbbg_etf_response) as mock_bdh:
            result = fetch_from_bloomberg(
                ticker="HYG US Equity",
                instrument="etf",
                start_date="2023-01-01",
                end_date="2023-01-05",
                security="hyg",
            )

            # Verify DataFrame structure
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 5
            assert "spread" in result.columns
            assert "security" in result.columns
            assert result["security"].iloc[0] == "hyg"

    def test_default_date_range(self, mock_xbbg_response):
        """Test default 5-year date range when dates not provided."""
        with patch("xbbg.blp.bdh", return_value=mock_xbbg_response) as mock_bdh:
            fetch_from_bloomberg(
                ticker="VIX Index",
                instrument="vix",
                security="vix",
            )

            # Verify blp.bdh called with date strings (not None)
            call_kwargs = mock_bdh.call_args[1]
            assert "start_date" in call_kwargs
            assert "end_date" in call_kwargs
            assert len(call_kwargs["start_date"]) == 8  # YYYYMMDD format
            assert len(call_kwargs["end_date"]) == 8

    def test_date_format_conversion(self, mock_xbbg_response):
        """Test date conversion from YYYY-MM-DD to YYYYMMDD."""
        with patch("xbbg.blp.bdh", return_value=mock_xbbg_response) as mock_bdh:
            fetch_from_bloomberg(
                ticker="VIX Index",
                instrument="vix",
                start_date="2023-01-01",
                end_date="2023-12-31",
                security="vix",
            )

            call_kwargs = mock_bdh.call_args[1]
            assert call_kwargs["start_date"] == "20230101"
            assert call_kwargs["end_date"] == "20231231"

    def test_invalid_instrument_type(self):
        """Test error on unknown instrument type."""
        with pytest.raises(ValueError, match="Unknown instrument type"):
            fetch_from_bloomberg(
                ticker="AAPL US Equity",
                instrument="equity",  # Not supported
            )

    def test_bloomberg_request_failure(self):
        """Test error handling when Bloomberg request fails."""
        with patch("xbbg.blp.bdh", return_value=pd.DataFrame()):  # Return empty, not exception
            with pytest.raises(RuntimeError, match="Bloomberg returned empty data"):
                fetch_from_bloomberg(
                    ticker="VIX Index",
                    instrument="vix",
                    security="vix",
                )

    def test_empty_response(self):
        """Test error when Bloomberg returns empty data."""
        with patch("xbbg.blp.bdh", return_value=pd.DataFrame()):
            with pytest.raises(RuntimeError, match="Bloomberg returned empty data"):
                fetch_from_bloomberg(
                    ticker="INVALID Index",
                    instrument="vix",
                    security="vix",
                )

    def test_none_response(self):
        """Test error when Bloomberg returns None."""
        with patch("xbbg.blp.bdh", return_value=None):
            with pytest.raises(RuntimeError, match="Bloomberg returned empty data"):
                fetch_from_bloomberg(
                    ticker="INVALID Index",
                    instrument="vix",
                    security="vix",
                )

    def test_additional_params_passed_through(self, mock_xbbg_response):
        """Test that additional **params are passed to xbbg."""
        with patch("xbbg.blp.bdh", return_value=mock_xbbg_response) as mock_bdh:
            fetch_from_bloomberg(
                ticker="VIX Index",
                instrument="vix",
                start_date="2023-01-01",
                end_date="2023-01-05",
                security="vix",
                adjustment="all",  # Extra Bloomberg parameter
            )

            call_kwargs = mock_bdh.call_args[1]
            assert "adjustment" in call_kwargs
            assert call_kwargs["adjustment"] == "all"


class TestMapBloombergFields:
    """Test _map_bloomberg_fields function."""

    def test_map_cdx_fields(self):
        """Test field mapping for CDX data."""
        df = pd.DataFrame({"PX_LAST": [100.0, 101.0]})
        spec = get_instrument_spec("cdx")
        result = _map_bloomberg_fields(df, spec)

        assert "spread" in result.columns
        assert "PX_LAST" not in result.columns
        assert list(result["spread"]) == [100.0, 101.0]

    def test_map_vix_fields(self):
        """Test field mapping for VIX data."""
        df = pd.DataFrame({"PX_LAST": [20.0, 21.0]})
        spec = get_instrument_spec("vix")
        result = _map_bloomberg_fields(df, spec)

        assert "level" in result.columns
        assert "PX_LAST" not in result.columns

    def test_map_etf_fields(self):
        """Test field mapping for ETF data."""
        df = pd.DataFrame({"YAS_ISPREAD": [85.0, 86.0]})
        spec = get_instrument_spec("etf")
        result = _map_bloomberg_fields(df, spec)

        assert "spread" in result.columns
        assert "YAS_ISPREAD" not in result.columns

    def test_flatten_multiindex_columns(self):
        """Test flattening xbbg multi-index columns."""
        # Create multi-index DataFrame (ticker, field)
        df = pd.DataFrame(
            {("CDX IG CDSI GEN 5Y Corp", "PX_LAST"): [100.0, 101.0]}
        )
        assert isinstance(df.columns, pd.MultiIndex)

        spec = get_instrument_spec("cdx")
        result = _map_bloomberg_fields(df, spec)

        # Should be flattened and renamed
        assert not isinstance(result.columns, pd.MultiIndex)
        assert "spread" in result.columns


class TestAddMetadataColumns:
    """Test _add_security_metadata function."""

    def test_add_cdx_metadata_with_security(self):
        """Test CDX metadata with security parameter."""
        df = pd.DataFrame({"spread": [100.0, 101.0]})
        result = _add_security_metadata(df, "CDX IG CDSI GEN 5Y Corp", security="cdx_ig_5y")

        assert "security" in result.columns
        assert result["security"].iloc[0] == "cdx_ig_5y"

    def test_add_cdx_metadata_reverse_lookup(self):
        """Test CDX metadata with reverse lookup from ticker."""
        df = pd.DataFrame({"spread": [100.0, 101.0]})
        result = _add_security_metadata(df, "CDX IG CDSI GEN 5Y Corp")

        assert "security" in result.columns
        assert result["security"].iloc[0] == "cdx_ig_5y"

    def test_add_cdx_metadata_multiple_securities(self):
        """Test CDX metadata with different securities."""
        df = pd.DataFrame({"spread": [100.0]})

        test_cases = [
            ("CDX IG CDSI GEN 5Y Corp", "cdx_ig_5y"),
            ("CDX IG CDSI GEN 10Y Corp", "cdx_ig_10y"),
            ("CDX HY CDSI GEN 5Y SPRD Corp", "cdx_hy_5y"),
        ]

        for ticker, expected_security in test_cases:
            result = _add_security_metadata(df, ticker)
            assert result["security"].iloc[0] == expected_security

    def test_add_etf_metadata(self):
        """Test ETF metadata with security parameter."""
        df = pd.DataFrame({"spread": [85.0, 86.0]})
        result = _add_security_metadata(df, "HYG US Equity", security="hyg")

        assert "security" in result.columns
        assert result["security"].iloc[0] == "hyg"

    def test_add_etf_metadata_reverse_lookup(self):
        """Test ETF metadata with reverse lookup."""
        df = pd.DataFrame({"spread": [120.0]})
        result = _add_security_metadata(df, "LQD US Equity")

        assert "security" in result.columns
        assert result["security"].iloc[0] == "lqd"

    def test_unregistered_ticker(self):
        """Test error when ticker not in registry."""
        df = pd.DataFrame({"spread": [100.0]})

        with pytest.raises(ValueError, match="Cannot determine security identifier"):
            _add_security_metadata(df, "INVALID TICKER Corp")

    def test_etf_unregistered_ticker(self):
        """Test error when ETF ticker not in registry."""
        df = pd.DataFrame({"spread": [85.0]})

        with pytest.raises(ValueError, match="Cannot determine security identifier"):
            _add_security_metadata(df, "UNKNOWN US Equity")


class TestIntegration:
    """Integration tests for complete fetch workflow."""

    def test_full_cdx_workflow(self):
        """Test complete CDX fetch with all transformations."""
        mock_response = pd.DataFrame(
            {("CDX IG CDSI GEN 5Y Corp", "PX_LAST"): [100.0, 101.0, 102.0]},
            index=pd.date_range("2023-01-01", periods=3, freq="D"),
        )

        with patch("xbbg.blp.bdh", return_value=mock_response):
            result = fetch_from_bloomberg(
                ticker="CDX IG CDSI GEN 5Y Corp",
                instrument="cdx",
                start_date="2023-01-01",
                end_date="2023-01-03",
                security="cdx_ig_5y",
            )

            # Verify complete transformation chain
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 3
            assert set(result.columns) == {"spread", "security"}
            assert result["spread"].iloc[0] == 100.0
            assert result["security"].iloc[0] == "cdx_ig_5y"
            assert isinstance(result.index, pd.DatetimeIndex)

    def test_full_vix_workflow(self):
        """Test complete VIX fetch with all transformations."""
        mock_response = pd.DataFrame(
            {"PX_LAST": [20.0, 21.0]},
            index=pd.date_range("2023-01-01", periods=2, freq="D"),
        )

        with patch("xbbg.blp.bdh", return_value=mock_response):
            result = fetch_from_bloomberg(
                ticker="VIX Index",
                instrument="vix",
                security="vix",
            )

            assert set(result.columns) == {"level"}
            assert result["level"].iloc[0] == 20.0
            assert isinstance(result.index, pd.DatetimeIndex)

    def test_full_etf_workflow(self):
        """Test complete ETF fetch with all transformations."""
        mock_response = pd.DataFrame(
            {"YAS_ISPREAD": [85.0, 86.0, 87.0]},
            index=pd.date_range("2023-01-01", periods=3, freq="D"),
        )

        with patch("xbbg.blp.bdh", return_value=mock_response):
            result = fetch_from_bloomberg(
                ticker="HYG US Equity",
                instrument="etf",
                security="hyg",
            )

            assert set(result.columns) == {"spread", "security"}
            assert result["spread"].iloc[0] == 85.0
            assert result["security"].iloc[0] == "hyg"
