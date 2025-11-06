"""Tests for statistical test functions."""

import numpy as np
import pandas as pd

from aponyx.evaluation.suitability import tests


class TestComputeCorrelation:
    """Test correlation calculation."""

    def test_perfect_positive_correlation(self) -> None:
        """Test perfect positive correlation."""
        signal = pd.Series([1, 2, 3, 4, 5])
        target = pd.Series([2, 4, 6, 8, 10])

        corr = tests.compute_correlation(signal, target)

        assert abs(corr - 1.0) < 1e-6

    def test_perfect_negative_correlation(self) -> None:
        """Test perfect negative correlation."""
        signal = pd.Series([1, 2, 3, 4, 5])
        target = pd.Series([10, 8, 6, 4, 2])

        corr = tests.compute_correlation(signal, target)

        assert abs(corr - (-1.0)) < 1e-6

    def test_no_correlation(self) -> None:
        """Test uncorrelated series."""
        np.random.seed(42)
        signal = pd.Series(np.random.randn(100))
        target = pd.Series(np.random.randn(100))

        corr = tests.compute_correlation(signal, target)

        # Random series should have correlation near zero
        assert abs(corr) < 0.2

    def test_empty_series_returns_zero(self) -> None:
        """Test that empty series returns 0.0."""
        signal = pd.Series([], dtype=float)
        target = pd.Series([], dtype=float)

        corr = tests.compute_correlation(signal, target)

        assert corr == 0.0

    def test_zero_variance_returns_zero(self) -> None:
        """Test that zero variance series returns 0.0."""
        signal = pd.Series([1.0, 1.0, 1.0, 1.0])
        target = pd.Series([2.0, 3.0, 4.0, 5.0])

        corr = tests.compute_correlation(signal, target)

        assert corr == 0.0


class TestComputeRegressionStats:
    """Test OLS regression statistics."""

    def test_perfect_linear_relationship(self) -> None:
        """Test regression with perfect linear relationship."""
        signal = pd.Series([1, 2, 3, 4, 5])
        target = pd.Series([2, 4, 6, 8, 10])  # target = 2 * signal

        stats = tests.compute_regression_stats(signal, target)

        assert abs(stats["beta"] - 2.0) < 1e-6
        assert stats["r_squared"] > 0.99
        assert abs(stats["t_stat"]) > 10  # Very high t-stat for perfect fit

    def test_noisy_relationship(self) -> None:
        """Test regression with noise."""
        np.random.seed(42)
        signal = pd.Series(np.random.randn(100))
        target = signal * 1.5 + np.random.randn(100) * 0.5

        stats = tests.compute_regression_stats(signal, target)

        # Beta should be around 1.5
        assert 1.0 < stats["beta"] < 2.0
        # Should be statistically significant
        assert abs(stats["t_stat"]) > 2.0
        # R² should be moderate
        assert 0.3 < stats["r_squared"] < 0.9

    def test_insufficient_data_returns_zeros(self) -> None:
        """Test that insufficient observations returns zeros."""
        signal = pd.Series([1, 2])
        target = pd.Series([3, 4])

        stats = tests.compute_regression_stats(signal, target)

        assert stats["beta"] == 0.0
        assert stats["t_stat"] == 0.0
        assert stats["p_value"] == 1.0
        assert stats["r_squared"] == 0.0


class TestComputeSubperiodBetas:
    """Test subperiod beta calculation."""

    def test_consistent_relationship(self) -> None:
        """Test that consistent relationship returns similar betas."""
        np.random.seed(42)
        signal = pd.Series(np.random.randn(200))
        target = signal * 2.0 + np.random.randn(200) * 0.5

        betas = tests.compute_subperiod_betas(signal, target, n_splits=2)

        assert len(betas) == 2
        # Both betas should be positive and similar magnitude
        assert betas[0] > 0
        assert betas[1] > 0
        assert abs(betas[0] - betas[1]) < 1.0  # Similar magnitudes

    def test_regime_change(self) -> None:
        """Test that regime change is detected."""
        # First half: positive relationship
        signal1 = pd.Series(np.linspace(0, 10, 100))
        target1 = signal1 * 2.0

        # Second half: negative relationship
        signal2 = pd.Series(np.linspace(0, 10, 100))
        target2 = signal2 * -2.0

        signal = pd.concat([signal1, signal2], ignore_index=True)
        target = pd.concat([target1, target2], ignore_index=True)

        betas = tests.compute_subperiod_betas(signal, target, n_splits=2)

        assert len(betas) == 2
        # First beta positive, second negative
        assert betas[0] > 0
        assert betas[1] < 0

    def test_insufficient_data_returns_empty(self) -> None:
        """Test that insufficient data returns empty list."""
        signal = pd.Series([1, 2, 3])
        target = pd.Series([4, 5, 6])

        betas = tests.compute_subperiod_betas(signal, target, n_splits=2)

        assert betas == []


class TestCheckSignConsistency:
    """Test sign consistency check."""

    def test_all_positive_consistent(self) -> None:
        """Test that all positive betas are consistent."""
        betas = [1.5, 2.0, 1.8, 2.2]

        consistent = tests.check_sign_consistency(betas)

        assert consistent is True

    def test_all_negative_consistent(self) -> None:
        """Test that all negative betas are consistent."""
        betas = [-1.5, -2.0, -1.8, -2.2]

        consistent = tests.check_sign_consistency(betas)

        assert consistent is True

    def test_mixed_signs_inconsistent(self) -> None:
        """Test that mixed signs are inconsistent."""
        betas = [1.5, -0.5, 1.8]

        consistent = tests.check_sign_consistency(betas)

        assert consistent is False

    def test_zero_beta_filtered(self) -> None:
        """Test that zero beta is filtered out, consistency based on non-zero."""
        betas = [0.0, 1.5, 2.0]

        consistent = tests.check_sign_consistency(betas)

        # Zeros filtered, remaining [1.5, 2.0] are consistent (both positive)
        assert consistent is True

    def test_all_zeros_inconsistent(self) -> None:
        """Test that all zeros is treated as inconsistent."""
        betas = [0.0, 0.0, 0.0]

        consistent = tests.check_sign_consistency(betas)

        assert consistent is False

    def test_empty_list_inconsistent(self) -> None:
        """Test that empty list is inconsistent."""
        betas = []

        consistent = tests.check_sign_consistency(betas)

        assert consistent is False
