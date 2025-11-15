"""Tests for intraday cache update functionality."""

import pandas as pd
import pytest

from aponyx.data.cache import update_current_day


def test_update_current_day_basic():
    """Test basic current day update with existing date."""
    # Historical cache
    cached_df = pd.DataFrame(
        {"spread": [85.2, 87.5, 88.1]},
        index=pd.to_datetime(["2025-11-13", "2025-11-14", "2025-11-15"]),
    )
    cached_df.index.name = "date"

    # Current day update (different value for same date)
    current_df = pd.DataFrame(
        {"spread": [89.3]},
        index=pd.to_datetime(["2025-11-15"]),
    )
    current_df.index.name = "date"

    # Update
    result = update_current_day(cached_df, current_df)

    # Verify
    assert len(result) == 3
    assert result.loc["2025-11-15", "spread"] == 89.3
    assert result.loc["2025-11-14", "spread"] == 87.5
    assert result.index.is_monotonic_increasing


def test_update_current_day_new_date():
    """Test current day update with new date (append)."""
    # Historical cache (older data)
    cached_df = pd.DataFrame(
        {"spread": [85.2, 87.5]},
        index=pd.to_datetime(["2025-11-13", "2025-11-14"]),
    )
    cached_df.index.name = "date"

    # Current day (new date)
    current_df = pd.DataFrame(
        {"spread": [89.3]},
        index=pd.to_datetime(["2025-11-15"]),
    )
    current_df.index.name = "date"

    # Update
    result = update_current_day(cached_df, current_df)

    # Verify
    assert len(result) == 3
    assert result.loc["2025-11-15", "spread"] == 89.3
    assert result.index.is_monotonic_increasing


def test_update_current_day_empty_cache():
    """Test update with empty cache."""
    cached_df = pd.DataFrame()

    current_df = pd.DataFrame(
        {"spread": [89.3]},
        index=pd.to_datetime(["2025-11-15"]),
    )
    current_df.index.name = "date"

    result = update_current_day(cached_df, current_df)

    assert len(result) == 1
    assert result.loc["2025-11-15", "spread"] == 89.3


def test_update_current_day_empty_current():
    """Test update with empty current data."""
    cached_df = pd.DataFrame(
        {"spread": [85.2, 87.5]},
        index=pd.to_datetime(["2025-11-13", "2025-11-14"]),
    )
    cached_df.index.name = "date"

    current_df = pd.DataFrame()

    result = update_current_day(cached_df, current_df)

    assert len(result) == 2
    assert result.equals(cached_df)


def test_update_current_day_with_security_column():
    """Test update preserves security metadata column."""
    cached_df = pd.DataFrame(
        {
            "spread": [85.2, 87.5, 88.1],
            "security": ["cdx_ig_5y", "cdx_ig_5y", "cdx_ig_5y"],
        },
        index=pd.to_datetime(["2025-11-13", "2025-11-14", "2025-11-15"]),
    )
    cached_df.index.name = "date"

    current_df = pd.DataFrame(
        {"spread": [89.3], "security": ["cdx_ig_5y"]},
        index=pd.to_datetime(["2025-11-15"]),
    )
    current_df.index.name = "date"

    result = update_current_day(cached_df, current_df)

    assert len(result) == 3
    assert result.loc["2025-11-15", "spread"] == 89.3
    assert result.loc["2025-11-15", "security"] == "cdx_ig_5y"
    assert all(result["security"] == "cdx_ig_5y")


def test_update_current_day_sorting():
    """Test that result is properly sorted by date."""
    # Cache with dates out of order (shouldn't happen, but test anyway)
    cached_df = pd.DataFrame(
        {"spread": [87.5, 85.2]},
        index=pd.to_datetime(["2025-11-14", "2025-11-13"]),
    )
    cached_df.index.name = "date"

    current_df = pd.DataFrame(
        {"spread": [89.3]},
        index=pd.to_datetime(["2025-11-15"]),
    )
    current_df.index.name = "date"

    result = update_current_day(cached_df, current_df)

    # Should be sorted
    assert result.index.is_monotonic_increasing
    assert result.index[0] == pd.Timestamp("2025-11-13")
    assert result.index[-1] == pd.Timestamp("2025-11-15")


def test_update_current_day_handles_none_current():
    """Test that update handles None current_df (non-trading day scenario)."""
    # This tests the contract for when BDP returns None
    cached_df = pd.DataFrame(
        {"spread": [85.2, 87.5]},
        index=pd.to_datetime(["2025-11-13", "2025-11-14"]),
    )
    cached_df.index.name = "date"

    # When current is None, should return cache unchanged
    # (This behavior happens in fetch.py, but we test cache function resilience)
    result = update_current_day(cached_df, pd.DataFrame())

    assert result.equals(cached_df)
