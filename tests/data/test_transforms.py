"""
Tests for time series transformation functions.

Validates mathematical correctness, edge case handling, and NaN propagation.
"""

import numpy as np
import pandas as pd
import pytest

from aponyx.data.transforms import apply_transform


class TestDiff:
    """Test first difference transformation."""

    def test_basic_diff(self):
        """Test basic first difference calculation."""
        series = pd.Series(
            [100, 105, 103, 108, 110],
            index=pd.date_range("2024-01-01", periods=5),
        )
        result = apply_transform(series, "diff")

        expected = pd.Series([np.nan, 5, -2, 5, 2], index=series.index)
        pd.testing.assert_series_equal(result, expected)

    def test_diff_with_periods(self):
        """Test difference over multiple periods."""
        series = pd.Series(
            [100, 105, 103, 108, 110],
            index=pd.date_range("2024-01-01", periods=5),
        )
        result = apply_transform(series, "diff", periods=2)

        expected = pd.Series([np.nan, np.nan, 3, 3, 7], index=series.index)
        pd.testing.assert_series_equal(result, expected)

    def test_diff_handles_nans(self):
        """Test that NaN values propagate correctly."""
        series = pd.Series(
            [100, np.nan, 103, 108],
            index=pd.date_range("2024-01-01", periods=4),
        )
        result = apply_transform(series, "diff")

        assert pd.isna(result.iloc[0])  # First value always NaN
        assert pd.isna(result.iloc[1])  # NaN input
        assert pd.isna(result.iloc[2])  # Previous was NaN


class TestPctChange:
    """Test percent change transformation."""

    def test_basic_pct_change(self):
        """Test basic percent change calculation."""
        series = pd.Series(
            [100, 105, 103, 108],
            index=pd.date_range("2024-01-01", periods=4),
        )
        result = apply_transform(series, "pct_change")

        expected = pd.Series(
            [np.nan, 0.05, -0.019047619, 0.048543689],
            index=series.index,
        )
        pd.testing.assert_series_equal(result, expected, atol=1e-6)

    def test_pct_change_with_zero(self):
        """Test percent change handles division by zero."""
        series = pd.Series(
            [0, 100, 105],
            index=pd.date_range("2024-01-01", periods=3),
        )
        result = apply_transform(series, "pct_change")

        assert pd.isna(result.iloc[0])
        assert np.isinf(result.iloc[1])  # 100/0 = inf
        assert np.isclose(result.iloc[2], 0.05)

    def test_pct_change_with_periods(self):
        """Test percent change over multiple periods."""
        series = pd.Series(
            [100, 105, 103, 108],
            index=pd.date_range("2024-01-01", periods=4),
        )
        result = apply_transform(series, "pct_change", periods=2)

        expected = pd.Series(
            [np.nan, np.nan, 0.03, 0.028571429],
            index=series.index,
        )
        pd.testing.assert_series_equal(result, expected, atol=1e-6)


class TestLogReturn:
    """Test log return transformation."""

    def test_basic_log_return(self):
        """Test basic log return calculation."""
        series = pd.Series(
            [100, 105, 103, 108],
            index=pd.date_range("2024-01-01", periods=4),
        )
        result = apply_transform(series, "log_return")

        expected = pd.Series(
            [np.nan, np.log(105 / 100), np.log(103 / 105), np.log(108 / 103)],
            index=series.index,
        )
        pd.testing.assert_series_equal(result, expected)

    def test_log_return_rejects_negative(self):
        """Test log return raises on negative values."""
        series = pd.Series(
            [100, -105, 103],
            index=pd.date_range("2024-01-01", periods=3),
        )

        with pytest.raises(ValueError, match="requires positive values"):
            apply_transform(series, "log_return")

    def test_log_return_rejects_zero(self):
        """Test log return raises on zero values."""
        series = pd.Series(
            [100, 0, 103],
            index=pd.date_range("2024-01-01", periods=3),
        )

        with pytest.raises(ValueError, match="requires positive values"):
            apply_transform(series, "log_return")

    def test_log_return_allows_nan(self):
        """Test log return allows NaN values in input."""
        series = pd.Series(
            [100, np.nan, 103, 108],
            index=pd.date_range("2024-01-01", periods=4),
        )
        result = apply_transform(series, "log_return")

        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])  # Previous was NaN
        assert pd.notna(result.iloc[3])

    def test_log_return_with_periods(self):
        """Test log return over multiple periods."""
        series = pd.Series(
            [100, 105, 103, 108],
            index=pd.date_range("2024-01-01", periods=4),
        )
        result = apply_transform(series, "log_return", periods=2)

        expected = pd.Series(
            [np.nan, np.nan, np.log(103 / 100), np.log(108 / 105)],
            index=series.index,
        )
        pd.testing.assert_series_equal(result, expected)


class TestZScore:
    """Test z-score normalization transformation."""

    def test_basic_z_score(self):
        """Test basic z-score calculation."""
        series = pd.Series(
            [100, 105, 103, 108, 110, 107, 112],
            index=pd.date_range("2024-01-01", periods=7),
        )
        result = apply_transform(series, "z_score", window=3, min_periods=3)

        # First two values should be NaN (insufficient data)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

        # Third value should be valid
        assert pd.notna(result.iloc[2])

        # Check that last value is normalized correctly
        last_window = series.iloc[-3:]
        expected_last = (series.iloc[-1] - last_window.mean()) / last_window.std()
        assert np.isclose(result.iloc[-1], expected_last)

    def test_z_score_requires_window(self):
        """Test z-score raises without window parameter."""
        series = pd.Series([100, 105, 103], index=pd.date_range("2024-01-01", periods=3))

        with pytest.raises(ValueError, match="window parameter required"):
            apply_transform(series, "z_score")

    def test_z_score_with_min_periods(self):
        """Test z-score with custom min_periods."""
        series = pd.Series(
            [100, 105, 103, 108],
            index=pd.date_range("2024-01-01", periods=4),
        )
        result = apply_transform(series, "z_score", window=5, min_periods=2)

        # Should have valid values starting from index 1 (min_periods=2)
        assert pd.isna(result.iloc[0])
        assert pd.notna(result.iloc[1])

    def test_z_score_handles_nans(self):
        """Test z-score with NaN values in input."""
        series = pd.Series(
            [100, np.nan, 103, 108, 110],
            index=pd.date_range("2024-01-01", periods=5),
        )
        result = apply_transform(series, "z_score", window=3, min_periods=2)

        # NaN should propagate through rolling calculation
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

    def test_z_score_zero_variance(self):
        """Test z-score with zero variance produces NaN."""
        series = pd.Series(
            [100, 100, 100, 105],
            index=pd.date_range("2024-01-01", periods=4),
        )
        result = apply_transform(series, "z_score", window=3, min_periods=3)

        # First three values have zero std, pandas produces NaN for 0/0
        assert pd.isna(result.iloc[2])


class TestNormalizedChange:
    """Test normalized change transformation."""

    def test_basic_normalized_change(self):
        """Test basic normalized change calculation."""
        series = pd.Series(
            [100, 105, 103, 108, 110, 107],
            index=pd.date_range("2024-01-01", periods=6),
        )
        result = apply_transform(series, "normalized_change", window=3, min_periods=3, periods=1)

        # First value is NaN (no prior for diff)
        assert pd.isna(result.iloc[0])

        # Check calculation for a specific point
        # result[3] = (series[3] - series[2]) / std(series[1:4])
        window_data = series.iloc[1:4]
        expected_val = (series.iloc[3] - series.iloc[2]) / window_data.std()
        assert np.isclose(result.iloc[3], expected_val)

    def test_normalized_change_requires_window(self):
        """Test normalized change raises without window parameter."""
        series = pd.Series([100, 105, 103], index=pd.date_range("2024-01-01", periods=3))

        with pytest.raises(ValueError, match="window parameter required"):
            apply_transform(series, "normalized_change")

    def test_normalized_change_with_periods(self):
        """Test normalized change over multiple periods."""
        series = pd.Series(
            [100, 105, 103, 108, 110],
            index=pd.date_range("2024-01-01", periods=5),
        )
        result = apply_transform(series, "normalized_change", window=3, min_periods=3, periods=2)

        # First two values are NaN (periods=2 for diff)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

        # Check calculation: (series[3] - series[1]) / std(series[1:4])
        window_data = series.iloc[1:4]
        expected_val = (series.iloc[3] - series.iloc[1]) / window_data.std()
        assert np.isclose(result.iloc[3], expected_val)


class TestEdgeCases:
    """Test edge cases across all transforms."""

    def test_empty_series(self):
        """Test all transforms handle empty series."""
        series = pd.Series([], dtype=float)

        for transform in ["diff", "pct_change", "log_return"]:
            result = apply_transform(series, transform)
            assert len(result) == 0

    def test_single_value(self):
        """Test transforms with single value."""
        series = pd.Series([100], index=pd.date_range("2024-01-01", periods=1))

        result = apply_transform(series, "diff")
        assert len(result) == 1
        assert pd.isna(result.iloc[0])

    def test_all_nans(self):
        """Test transforms with all NaN input."""
        series = pd.Series(
            [np.nan, np.nan, np.nan],
            index=pd.date_range("2024-01-01", periods=3),
        )

        result = apply_transform(series, "diff")
        assert result.isna().all()

        result = apply_transform(series, "pct_change")
        assert result.isna().all()

    def test_invalid_transform_type(self):
        """Test invalid transform type raises error."""
        series = pd.Series([100, 105], index=pd.date_range("2024-01-01", periods=2))

        with pytest.raises(ValueError, match="Unknown transform type"):
            apply_transform(series, "invalid_transform")  # type: ignore


class TestIntegration:
    """Integration tests matching signal use cases."""

    def test_spread_momentum_pattern(self):
        """Test normalized change pattern used in spread momentum."""
        spreads = pd.Series(
            [100, 102, 101, 103, 105, 104, 106],
            index=pd.date_range("2024-01-01", periods=7),
        )

        # Simulate spread momentum calculation
        normalized = apply_transform(
            spreads,
            "normalized_change",
            window=5,
            min_periods=3,
            periods=5,
        )
        signal = -normalized  # Negate for sign convention

        # Tightening spreads should give positive signal
        # Widening spreads should give negative signal
        assert pd.notna(signal.iloc[-1])

    def test_basis_normalization_pattern(self):
        """Test z-score pattern used in basis signals."""
        raw_basis = pd.Series(
            [1.5, 2.0, 1.8, 2.2, 2.5, 2.3],
            index=pd.date_range("2024-01-01", periods=6),
        )

        # Simulate basis normalization
        signal = apply_transform(
            raw_basis,
            "z_score",
            window=4,
            min_periods=3,
        )

        # Should produce normalized values
        assert pd.notna(signal.iloc[-1])
        # Recent values should have roughly zero mean over window
        recent_signals = signal.iloc[-4:].dropna()
        if len(recent_signals) > 0:
            assert abs(recent_signals.mean()) < 2.0  # Should be close to 0
