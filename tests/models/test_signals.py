"""
Unit tests for signal generation functions.
"""

import numpy as np
import pandas as pd
import pytest

from aponyx.models.signals import (
    compute_cdx_etf_basis,
    compute_cdx_vix_gap,
    compute_spread_momentum,
)
from aponyx.models.config import SignalConfig


@pytest.fixture
def sample_cdx_data() -> pd.DataFrame:
    """Generate synthetic CDX spread data."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    np.random.seed(42)
    spreads = 100 + np.cumsum(np.random.randn(100) * 2)
    return pd.DataFrame({"spread": spreads}, index=dates)


@pytest.fixture
def sample_vix_data() -> pd.DataFrame:
    """Generate synthetic VIX data."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    np.random.seed(43)
    vix = 15 + np.cumsum(np.random.randn(100) * 0.5)
    return pd.DataFrame({"level": vix}, index=dates)


@pytest.fixture
def sample_etf_data() -> pd.DataFrame:
    """Generate synthetic ETF spread-equivalent data."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    np.random.seed(44)
    spreads = 95 + np.cumsum(np.random.randn(100) * 1.8)
    return pd.DataFrame({"spread": spreads}, index=dates)


def test_compute_cdx_etf_basis_returns_series(
    sample_cdx_data: pd.DataFrame,
    sample_etf_data: pd.DataFrame,
) -> None:
    """Test that CDX-ETF basis returns a pandas Series."""
    result = compute_cdx_etf_basis(sample_cdx_data, sample_etf_data)
    assert isinstance(result, pd.Series)
    assert len(result) == len(sample_cdx_data)


def test_compute_cdx_etf_basis_normalization(
    sample_cdx_data: pd.DataFrame,
    sample_etf_data: pd.DataFrame,
) -> None:
    """Test that basis signal is approximately z-score normalized."""
    config = SignalConfig(lookback=20, min_periods=10)
    result = compute_cdx_etf_basis(sample_cdx_data, sample_etf_data, config)

    # After sufficient observations, should have mean ~0 and std ~1
    valid_result = result.dropna()
    if len(valid_result) > 30:
        assert abs(valid_result.mean()) < 0.5
        assert 0.7 < valid_result.std() < 1.5


def test_compute_cdx_vix_gap_returns_series(
    sample_cdx_data: pd.DataFrame,
    sample_vix_data: pd.DataFrame,
) -> None:
    """Test that CDX-VIX gap returns a pandas Series."""
    result = compute_cdx_vix_gap(sample_cdx_data, sample_vix_data)
    assert isinstance(result, pd.Series)
    assert len(result) == len(sample_cdx_data)


def test_compute_cdx_vix_gap_has_nans_early(
    sample_cdx_data: pd.DataFrame,
    sample_vix_data: pd.DataFrame,
) -> None:
    """Test that CDX-VIX gap has NaNs during warmup period."""
    config = SignalConfig(lookback=20, min_periods=10)
    result = compute_cdx_vix_gap(sample_cdx_data, sample_vix_data, config)

    # First min_periods should be NaN
    assert result.iloc[: config.min_periods].isna().all()
    # Later values should be valid
    assert result.iloc[config.lookback :].notna().any()


def test_compute_spread_momentum_returns_series(
    sample_cdx_data: pd.DataFrame,
) -> None:
    """Test that spread momentum returns a pandas Series."""
    result = compute_spread_momentum(sample_cdx_data)
    assert isinstance(result, pd.Series)
    assert len(result) == len(sample_cdx_data)


def test_compute_spread_momentum_custom_config(
    sample_cdx_data: pd.DataFrame,
) -> None:
    """Test momentum computation with custom configuration."""
    config = SignalConfig(lookback=10, min_periods=5)
    result = compute_spread_momentum(sample_cdx_data, config)

    # Should have valid values after lookback period
    assert result.iloc[config.lookback :].notna().any()


def test_signals_handle_insufficient_data() -> None:
    """Test signals gracefully handle insufficient data."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    cdx_df = pd.DataFrame({"spread": [100, 101, 102, 103, 104]}, index=dates)
    vix_df = pd.DataFrame({"level": [15, 16, 15, 17, 16]}, index=dates)
    etf_df = pd.DataFrame({"spread": [95, 96, 97, 98, 99]}, index=dates)

    config = SignalConfig(lookback=20, min_periods=10)

    basis = compute_cdx_etf_basis(cdx_df, etf_df, config)
    gap = compute_cdx_vix_gap(cdx_df, vix_df, config)
    momentum = compute_spread_momentum(cdx_df, config)

    # All should be NaN with insufficient data
    assert basis.isna().all()
    assert gap.isna().all()
    assert momentum.isna().all()


def test_signals_deterministic(
    sample_cdx_data: pd.DataFrame,
    sample_vix_data: pd.DataFrame,
    sample_etf_data: pd.DataFrame,
) -> None:
    """Test that signals produce deterministic results."""
    config = SignalConfig(lookback=15, min_periods=8)

    # Compute twice
    basis1 = compute_cdx_etf_basis(sample_cdx_data, sample_etf_data, config)
    basis2 = compute_cdx_etf_basis(sample_cdx_data, sample_etf_data, config)

    gap1 = compute_cdx_vix_gap(sample_cdx_data, sample_vix_data, config)
    gap2 = compute_cdx_vix_gap(sample_cdx_data, sample_vix_data, config)

    momentum1 = compute_spread_momentum(sample_cdx_data, config)
    momentum2 = compute_spread_momentum(sample_cdx_data, config)

    # Results should be identical
    pd.testing.assert_series_equal(basis1, basis2)
    pd.testing.assert_series_equal(gap1, gap2)
    pd.testing.assert_series_equal(momentum1, momentum2)
