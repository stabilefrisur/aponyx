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
    _add_metadata_columns,
)

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
                flds=["PX_LAST"],
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
            assert "close" in result.columns
            assert "security" not in result.columns  # VIX has no metadata

    def test_fetch_etf_success(self, mock_xbbg_response):
        """Test successful ETF data fetch."""
        with patch("xbbg.blp.bdh", return_value=mock_xbbg_response) as mock_bdh:
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
            assert "close" in result.columns
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
        result = _map_bloomberg_fields(df, "cdx", "CDX IG CDSI GEN 5Y Corp")

        assert "spread" in result.columns
        assert "PX_LAST" not in result.columns
        assert list(result["spread"]) == [100.0, 101.0]

    def test_map_vix_fields(self):
        """Test field mapping for VIX data."""
        df = pd.DataFrame({"PX_LAST": [20.0, 21.0]})
        result = _map_bloomberg_fields(df, "vix", "VIX Index")

        assert "close" in result.columns
        assert "PX_LAST" not in result.columns

    def test_map_etf_fields(self):
        """Test field mapping for ETF data."""
        df = pd.DataFrame({"PX_LAST": [85.0, 86.0]})
        result = _map_bloomberg_fields(df, "etf", "HYG US Equity")

        assert "close" in result.columns
        assert "PX_LAST" not in result.columns

    def test_flatten_multiindex_columns(self):
        """Test flattening xbbg multi-index columns."""
        # Create multi-index DataFrame (ticker, field)
        df = pd.DataFrame(
            {("CDX IG CDSI GEN 5Y Corp", "PX_LAST"): [100.0, 101.0]}
        )
        assert isinstance(df.columns, pd.MultiIndex)

        result = _map_bloomberg_fields(df, "cdx", "CDX IG CDSI GEN 5Y Corp")

        # Should be flattened and renamed
        assert not isinstance(result.columns, pd.MultiIndex)
        assert "spread" in result.columns


class TestAddMetadataColumns:
    """Test _add_metadata_columns function."""

    def test_add_cdx_metadata_with_security(self):
        """Test CDX metadata with security parameter."""
        df = pd.DataFrame({"spread": [100.0, 101.0]})
        result = _add_metadata_columns(df, "cdx", "CDX IG CDSI GEN 5Y Corp", security="cdx_ig_5y")

        assert "security" in result.columns
        assert result["security"].iloc[0] == "cdx_ig_5y"

    def test_add_cdx_metadata_reverse_lookup(self):
        """Test CDX metadata with reverse lookup from ticker."""
        df = pd.DataFrame({"spread": [100.0, 101.0]})
        result = _add_metadata_columns(df, "cdx", "CDX IG CDSI GEN 5Y Corp")

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
            result = _add_metadata_columns(df, "cdx", ticker)
            assert result["security"].iloc[0] == expected_security

    def test_add_etf_metadata(self):
        """Test ETF metadata with security parameter."""
        df = pd.DataFrame({"close": [85.0, 86.0]})
        result = _add_metadata_columns(df, "etf", "HYG US Equity", security="hyg")

        assert "security" in result.columns
        assert result["security"].iloc[0] == "hyg"

    def test_add_etf_metadata_reverse_lookup(self):
        """Test ETF metadata with reverse lookup."""
        df = pd.DataFrame({"close": [120.0]})
        result = _add_metadata_columns(df, "etf", "LQD US Equity")

        assert "security" in result.columns
        assert result["security"].iloc[0] == "lqd"

    def test_vix_no_metadata(self):
        """Test VIX data has no metadata columns added."""
        df = pd.DataFrame({"close": [20.0, 21.0]})
        result = _add_metadata_columns(df, "vix", "VIX Index", security="vix")

        # Should only have close column
        assert list(result.columns) == ["close"]
        assert "security" not in result.columns

    def test_unregistered_ticker(self):
        """Test error when ticker not in registry."""
        df = pd.DataFrame({"spread": [100.0]})

        with pytest.raises(ValueError, match="Cannot determine security identifier"):
            _add_metadata_columns(df, "cdx", "INVALID TICKER Corp")

    def test_etf_unregistered_ticker(self):
        """Test error when ETF ticker not in registry."""
        df = pd.DataFrame({"close": [85.0]})

        with pytest.raises(ValueError, match="Cannot determine security identifier"):
            _add_metadata_columns(df, "etf", "UNKNOWN US Equity")


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

            assert set(result.columns) == {"close"}
            assert result["close"].iloc[0] == 20.0
            assert isinstance(result.index, pd.DatetimeIndex)

    def test_full_etf_workflow(self):
        """Test complete ETF fetch with all transformations."""
        mock_response = pd.DataFrame(
            {"PX_LAST": [85.0, 86.0, 87.0]},
            index=pd.date_range("2023-01-01", periods=3, freq="D"),
        )

        with patch("xbbg.blp.bdh", return_value=mock_response):
            result = fetch_from_bloomberg(
                ticker="HYG US Equity",
                instrument="etf",
                security="hyg",
            )

            assert set(result.columns) == {"close", "security"}
            assert result["close"].iloc[0] == 85.0
            assert result["security"].iloc[0] == "hyg"
