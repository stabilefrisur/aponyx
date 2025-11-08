"""Tests for data validation functionality."""

import pandas as pd
import pytest

from aponyx.data.validation import (
    validate_cdx_schema,
    validate_vix_schema,
    validate_etf_schema,
)


def test_validate_cdx_schema_valid() -> None:
    """Test CDX schema validation with valid data."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "spread": [100.0, 105.0, 102.0, 110.0, 108.0, 115.0, 112.0, 120.0, 118.0, 125.0],
            "index": ["cdx_ig_5y"] * 10,
        }
    )

    validated = validate_cdx_schema(df)

    assert isinstance(validated.index, pd.DatetimeIndex)
    assert len(validated) == 10
    assert "spread" in validated.columns


def test_validate_cdx_schema_missing_columns() -> None:
    """Test CDX schema validation with missing required columns."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            # Missing 'spread' column
            "index": ["cdx_ig_5y"] * 10,
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_cdx_schema(df)


def test_validate_cdx_schema_invalid_spread() -> None:
    """Test CDX schema validation with invalid spread values."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "spread": [-10.0] * 10,  # Negative spreads are invalid
            "index": ["cdx_ig_5y"] * 10,
        }
    )

    with pytest.raises(ValueError, match="Spread values outside valid range"):
        validate_cdx_schema(df)


def test_validate_cdx_schema_duplicate_dates(caplog: pytest.LogCaptureFixture) -> None:
    """Test CDX schema validation with duplicate dates."""
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"] * 5 + ["2024-01-02"] * 5,
            "spread": [100.0] * 10,
            "index": ["cdx_ig_5y"] * 10,
        }
    )

    validated = validate_cdx_schema(df)

    assert "duplicate dates" in caplog.text.lower()
    assert len(validated) == 10  # Still returns data with duplicates


def test_validate_vix_schema_valid() -> None:
    """Test VIX schema validation with valid data."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "level": [15.0, 16.5, 14.8, 17.2, 16.0, 18.5, 17.8, 19.2, 18.0, 20.1],
        }
    )

    validated = validate_vix_schema(df)

    assert isinstance(validated.index, pd.DatetimeIndex)
    assert len(validated) == 10
    assert "level" in validated.columns


def test_validate_vix_schema_invalid_values() -> None:
    """Test VIX schema validation with invalid VIX values."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "level": [250.0] * 10,  # Above max_vix
        }
    )

    with pytest.raises(ValueError, match="VIX values outside valid range"):
        validate_vix_schema(df)


def test_validate_etf_schema_valid() -> None:
    """Test ETF schema validation with valid data."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "spread": [80.0, 80.5, 79.8, 81.2, 80.9, 82.1, 81.8, 83.0, 82.5, 84.2],
            "security": ["hyg"] * 10,
        }
    )

    validated = validate_etf_schema(df)

    assert isinstance(validated.index, pd.DatetimeIndex)
    assert len(validated) == 10
    assert "spread" in validated.columns


def test_validate_etf_schema_missing_columns() -> None:
    """Test ETF schema validation with missing required columns."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            # Missing 'spread' column (required)
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_etf_schema(df)


def test_validate_etf_schema_invalid_prices() -> None:
    """Test ETF schema validation with invalid price values."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "spread": [-10.0] * 10,  # Negative prices are invalid
            "ticker": ["HYG"] * 10,
        }
    )

    with pytest.raises(ValueError, match="Price values outside valid range"):
        validate_etf_schema(df)


def test_validate_cdx_schema_already_indexed() -> None:
    """Test CDX schema validation with data already having DatetimeIndex."""
    df = pd.DataFrame(
        {
            "spread": [100.0, 105.0, 102.0],
            "index": ["cdx_ig_5y"] * 3,
        },
        index=pd.date_range("2024-01-01", periods=3),
    )

    validated = validate_cdx_schema(df)

    assert isinstance(validated.index, pd.DatetimeIndex)
    assert len(validated) == 3
