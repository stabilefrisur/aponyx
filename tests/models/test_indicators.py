"""
Tests for indicator computation functions.

Validates that indicators:
- Compute correctly from raw market data
- Output economically interpretable units (not z-scores)
- Handle caching properly
- Propagate NaN values correctly
"""

import pandas as pd
import pytest

from aponyx.models.indicators import (
    compute_cdx_etf_spread_diff,
    compute_cdx_vix_deviation_gap,
    compute_indicator,
    compute_spread_momentum,
)
from aponyx.models.metadata import IndicatorMetadata
from aponyx.config import INDICATOR_CACHE_DIR


def generate_sample_cdx(n_obs: int = 100, start_spread: float = 100.0) -> pd.DataFrame:
    """Generate sample CDX data for testing."""
    dates = pd.date_range("2024-01-01", periods=n_obs, freq="D")
    spreads = start_spread + pd.Series(range(n_obs)) * 0.1
    return pd.DataFrame({"spread": spreads.values}, index=dates)


def generate_sample_etf(n_obs: int = 100, start_spread: float = 95.0) -> pd.DataFrame:
    """Generate sample ETF data for testing."""
    dates = pd.date_range("2024-01-01", periods=n_obs, freq="D")
    spreads = start_spread + pd.Series(range(n_obs)) * 0.08
    return pd.DataFrame({"spread": spreads.values}, index=dates)


def generate_sample_vix(n_obs: int = 100, start_level: float = 15.0) -> pd.DataFrame:
    """Generate sample VIX data for testing."""
    dates = pd.date_range("2024-01-01", periods=n_obs, freq="D")
    levels = start_level + pd.Series(range(n_obs)) * 0.05
    return pd.DataFrame({"level": levels.values}, index=dates)


class TestComputeCdxEtfSpreadDiff:
    """Tests for compute_cdx_etf_spread_diff indicator."""

    def test_basic_computation(self):
        """Test basic spread difference computation."""
        cdx_df = generate_sample_cdx(n_obs=50)
        etf_df = generate_sample_etf(n_obs=50)

        result = compute_cdx_etf_spread_diff(cdx_df, etf_df, {})

        # Verify output
        assert isinstance(result, pd.Series)
        assert len(result) == len(cdx_df)
        assert result.name is None or isinstance(result.name, str)

        # Verify units: should be in basis points (raw differences, not normalized)
        # First value should be approximately 100 - 95 = 5 bps
        assert abs(result.iloc[0] - 5.0) < 1.0

        # Verify no z-score normalization (values should be in reasonable bps range)
        assert result.abs().max() < 1000  # Not normalized to z-scores

    def test_output_units_are_basis_points(self):
        """Test that output is in basis points, not z-scores."""
        cdx_df = generate_sample_cdx(n_obs=100, start_spread=120.0)
        etf_df = generate_sample_etf(n_obs=100, start_spread=110.0)

        result = compute_cdx_etf_spread_diff(cdx_df, etf_df, {})

        # Verify mean is around the expected difference (10 bps)
        assert abs(result.mean() - 10.0) < 5.0

        # Verify standard deviation is reasonable for bps (not close to 1.0 as z-scores would be)
        assert result.std() > 0.1  # Should have some variance
        assert result.std() < 100  # But not excessive

    def test_handles_missing_dates(self):
        """Test handling of misaligned dates between CDX and ETF."""
        cdx_df = generate_sample_cdx(n_obs=50)
        etf_df = generate_sample_etf(n_obs=40)  # Fewer observations

        result = compute_cdx_etf_spread_diff(cdx_df, etf_df, {})

        # Should forward-fill ETF data to match CDX dates
        assert len(result) == len(cdx_df)
        assert result.notna().sum() > 0


class TestComputeSpreadMomentum:
    """Tests for compute_spread_momentum indicator."""

    def test_basic_computation(self):
        """Test basic momentum computation."""
        cdx_df = generate_sample_cdx(n_obs=50)

        result = compute_spread_momentum(cdx_df, {"lookback": 5})

        # Verify output
        assert isinstance(result, pd.Series)
        assert len(result) == len(cdx_df)

        # First 5 values should be NaN (not enough history)
        assert result.iloc[:5].isna().all()

        # Remaining values should be valid
        assert result.iloc[5:].notna().any()

    def test_output_units_are_basis_points(self):
        """Test that output is spread change in basis points."""
        cdx_df = generate_sample_cdx(n_obs=100)

        result = compute_spread_momentum(cdx_df, {"lookback": 5})

        # Verify not z-score normalized (should have non-zero mean)
        valid_result = result.dropna()
        assert len(valid_result) > 0

        # Since we're generating increasing spreads, momentum should be positive on average
        assert valid_result.mean() > 0

        # Values should be in reasonable bps range for 5-day changes
        assert valid_result.abs().max() < 100

    def test_custom_lookback(self):
        """Test momentum with different lookback periods."""
        cdx_df = generate_sample_cdx(n_obs=100)

        result_5d = compute_spread_momentum(cdx_df, {"lookback": 5})
        result_20d = compute_spread_momentum(cdx_df, {"lookback": 20})

        # 20-day momentum should have more initial NaN values
        assert result_20d.iloc[:20].isna().all()
        assert result_5d.iloc[5:20].notna().any()

        # 20-day changes should be larger in magnitude
        assert result_20d.dropna().abs().mean() > result_5d.dropna().abs().mean()


class TestComputeCdxVixDeviationGap:
    """Tests for compute_cdx_vix_deviation_gap indicator."""

    def test_basic_computation(self):
        """Test basic deviation gap computation."""
        cdx_df = generate_sample_cdx(n_obs=50)
        vix_df = generate_sample_vix(n_obs=50)

        result = compute_cdx_vix_deviation_gap(cdx_df, vix_df, {"lookback": 20})

        # Verify output
        assert isinstance(result, pd.Series)
        assert len(result) == len(cdx_df)

        # First 10 values (min_periods = lookback // 2) should have some NaN
        assert result.iloc[:10].isna().sum() > 0

    def test_output_units_interpretable(self):
        """Test that output represents deviation gap in interpretable units."""
        cdx_df = generate_sample_cdx(n_obs=100)
        vix_df = generate_sample_vix(n_obs=100)

        result = compute_cdx_vix_deviation_gap(cdx_df, vix_df, {"lookback": 20})

        valid_result = result.dropna()
        assert len(valid_result) > 0

        # Should not be z-score normalized
        # Mean should not be forced to zero
        # Std should not be forced to 1.0
        assert abs(valid_result.std() - 1.0) > 0.1

    def test_handles_vix_missing_dates(self):
        """Test handling when VIX has fewer dates than CDX."""
        cdx_df = generate_sample_cdx(n_obs=50)
        vix_df = generate_sample_vix(n_obs=40)

        result = compute_cdx_vix_deviation_gap(cdx_df, vix_df, {"lookback": 20})

        # Should forward-fill VIX to match CDX dates
        assert len(result) == len(cdx_df)


class TestComputeIndicatorOrchestration:
    """Tests for compute_indicator orchestration function."""

    def test_orchestration_basic(self):
        """Test basic orchestration with cache disabled."""
        metadata = IndicatorMetadata(
            name="test_indicator",
            description="Test",
            compute_function_name="compute_cdx_etf_spread_diff",
            data_requirements={"cdx": "spread", "etf": "spread"},
            default_securities={"cdx": "cdx_ig_5y", "etf": "lqd"},
            output_units="basis_points",
            parameters={},
            enabled=True,
        )

        market_data = {
            "cdx": generate_sample_cdx(50),
            "etf": generate_sample_etf(50),
        }

        result = compute_indicator(
            "test_indicator",
            market_data,
            metadata,
            use_cache=False,
        )

        assert isinstance(result, pd.Series)
        assert len(result) == 50

    def test_orchestration_with_caching(self):
        """Test orchestration with caching enabled."""
        metadata = IndicatorMetadata(
            name="cached_indicator",
            description="Test caching",
            compute_function_name="compute_spread_momentum",
            data_requirements={"cdx": "spread"},
            default_securities={"cdx": "cdx_ig_5y"},
            output_units="basis_points",
            parameters={"lookback": 5},
            enabled=True,
        )

        market_data = {"cdx": generate_sample_cdx(50)}

        # First call should compute and cache
        result1 = compute_indicator(
            "cached_indicator",
            market_data,
            metadata,
            use_cache=True,
        )

        # Second call should load from cache
        result2 = compute_indicator(
            "cached_indicator",
            market_data,
            metadata,
            use_cache=True,
        )

        # Results should be identical (check_freq=False because cached series may have different freq)
        pd.testing.assert_series_equal(result1, result2, check_freq=False)

    def test_missing_market_data(self):
        """Test error handling when required market data is missing."""
        metadata = IndicatorMetadata(
            name="test_indicator",
            description="Test",
            compute_function_name="compute_cdx_etf_spread_diff",
            data_requirements={"cdx": "spread", "etf": "spread"},
            default_securities={"cdx": "cdx_ig_5y", "etf": "lqd"},
            output_units="basis_points",
            parameters={},
            enabled=True,
        )

        market_data = {"cdx": generate_sample_cdx(50)}  # Missing 'etf'

        with pytest.raises(ValueError, match="Missing required market data"):
            compute_indicator("test_indicator", market_data, metadata, use_cache=False)

    def test_missing_compute_function(self):
        """Test error handling when compute function doesn't exist."""
        metadata = IndicatorMetadata(
            name="bad_indicator",
            description="Test",
            compute_function_name="nonexistent_function",
            data_requirements={"cdx": "spread"},
            default_securities={"cdx": "cdx_ig_5y"},
            output_units="basis_points",
            parameters={},
            enabled=True,
        )

        market_data = {"cdx": generate_sample_cdx(50)}

        with pytest.raises(ValueError, match="Compute function .* not found"):
            compute_indicator("bad_indicator", market_data, metadata, use_cache=False)


class TestIndicatorCacheInvalidation:
    """Tests for indicator cache invalidation."""

    def test_cache_invalidation_workflow(self):
        """Test that cache can be invalidated when indicator definition changes."""
        from aponyx.persistence.parquet_io import invalidate_indicator_cache

        metadata = IndicatorMetadata(
            name="invalidation_test",
            description="Test",
            compute_function_name="compute_spread_momentum",
            data_requirements={"cdx": "spread"},
            default_securities={"cdx": "cdx_ig_5y"},
            output_units="basis_points",
            parameters={"lookback": 5},
            enabled=True,
        )

        market_data = {"cdx": generate_sample_cdx(50)}

        # Compute and cache
        result1 = compute_indicator(
            "invalidation_test",
            market_data,
            metadata,
            use_cache=True,
        )

        # Invalidate cache
        invalidate_indicator_cache("invalidation_test", INDICATOR_CACHE_DIR)

        # Next computation should recompute (no error)
        result2 = compute_indicator(
            "invalidation_test",
            market_data,
            metadata,
            use_cache=True,
        )

        # Results should still be identical (same inputs)
        # check_freq=False and check_names=False for cache compatibility
        pd.testing.assert_series_equal(result1, result2, check_freq=False, check_names=False)
