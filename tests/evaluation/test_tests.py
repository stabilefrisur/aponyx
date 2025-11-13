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


class TestComputeRollingBetas:
    """Test rolling beta calculation."""

    def test_perfect_relationship(self) -> None:
        """Test rolling betas with perfect linear relationship."""
        signal = pd.Series(np.linspace(0, 10, 300))
        target = signal * 2.0  # Perfect relationship: beta = 2.0

        rolling_betas = tests.compute_rolling_betas(signal, target, window=100)

        # First 99 values should be NaN
        assert rolling_betas.iloc[:99].isna().all()

        # Valid betas should be close to 2.0
        valid_betas = rolling_betas.dropna()
        assert len(valid_betas) > 0
        assert np.allclose(valid_betas, 2.0, rtol=0.01)

    def test_regime_shift(self) -> None:
        """Test rolling betas with midpoint regime shift."""
        # First half: positive relationship (beta ≈ 2.0)
        signal1 = pd.Series(np.linspace(0, 10, 150))
        target1 = signal1 * 2.0

        # Second half: negative relationship (beta ≈ -2.0)
        signal2 = pd.Series(np.linspace(0, 10, 150))
        target2 = signal2 * -2.0

        signal = pd.concat([signal1, signal2], ignore_index=True)
        target = pd.concat([target1, target2], ignore_index=True)

        rolling_betas = tests.compute_rolling_betas(signal, target, window=50)

        valid_betas = rolling_betas.dropna()

        # Early betas should be positive
        early_betas = valid_betas.iloc[:50]
        assert early_betas.mean() > 0

        # Late betas should be negative
        late_betas = valid_betas.iloc[-50:]
        assert late_betas.mean() < 0

    def test_insufficient_data_returns_empty(self) -> None:
        """Test that insufficient data returns empty series."""
        signal = pd.Series([1, 2, 3])
        target = pd.Series([4, 5, 6])

        rolling_betas = tests.compute_rolling_betas(signal, target, window=100)

        assert len(rolling_betas) == 0

    def test_noisy_relationship(self) -> None:
        """Test rolling betas with noisy data."""
        np.random.seed(42)
        signal = pd.Series(np.random.randn(300))
        target = signal * 1.5 + np.random.randn(300) * 0.5

        rolling_betas = tests.compute_rolling_betas(signal, target, window=100)

        valid_betas = rolling_betas.dropna()

        # Should have some valid betas
        assert len(valid_betas) > 0

        # Mean beta should be around 1.5
        assert 1.0 < valid_betas.mean() < 2.0


class TestComputeStabilityMetrics:
    """Test stability metrics calculation."""

    def test_stable_relationship(self) -> None:
        """Test stability metrics with stable relationship."""
        # All betas positive and similar magnitude
        rolling_betas = pd.Series([1.5, 1.6, 1.4, 1.7, 1.5, 1.6])
        aggregate_beta = 1.55

        metrics = tests.compute_stability_metrics(rolling_betas, aggregate_beta)

        assert metrics["sign_consistency_ratio"] == 1.0  # All same sign
        assert metrics["beta_cv"] < 0.1  # Low variation
        assert metrics["n_windows"] == 6

    def test_regime_shift(self) -> None:
        """Test stability metrics with sign reversal."""
        # Half positive, half negative (but not perfectly symmetric)
        rolling_betas = pd.Series([2.0, 2.2, 1.8, -1.0, -1.2, -0.8])
        aggregate_beta = 1.5  # Use positive aggregate

        metrics = tests.compute_stability_metrics(rolling_betas, aggregate_beta)

        # Sign consistency should be 0.5 (half pos, half neg)
        assert metrics["sign_consistency_ratio"] == 0.5  # 3 pos, 3 neg
        # CV should be high due to variation and non-zero mean
        assert metrics["beta_cv"] > 1.0  # High variation across regime
        assert metrics["n_windows"] == 6

    def test_high_variation_stable_sign(self) -> None:
        """Test high CV with consistent sign."""
        # All positive but wide range
        rolling_betas = pd.Series([0.5, 3.0, 1.0, 2.5, 1.5, 2.0])
        aggregate_beta = 1.75

        metrics = tests.compute_stability_metrics(rolling_betas, aggregate_beta)

        assert metrics["sign_consistency_ratio"] == 1.0  # All same sign
        assert metrics["beta_cv"] > 0.5  # High variation

    def test_empty_betas_returns_zeros(self) -> None:
        """Test that empty rolling betas returns zero metrics."""
        rolling_betas = pd.Series([], dtype=float)
        aggregate_beta = 1.0

        metrics = tests.compute_stability_metrics(rolling_betas, aggregate_beta)

        assert metrics["sign_consistency_ratio"] == 0.0
        assert metrics["beta_cv"] == 0.0
        assert metrics["n_windows"] == 0

    def test_filters_near_zero_betas(self) -> None:
        """Test that near-zero betas are filtered from sign consistency."""
        # Mix of significant betas and near-zero noise
        rolling_betas = pd.Series([1.5, 0.005, 1.6, -0.008, 1.4])
        aggregate_beta = 1.5

        metrics = tests.compute_stability_metrics(rolling_betas, aggregate_beta)

        # Only significant betas [1.5, 1.6, 1.4] should count for sign consistency
        assert metrics["sign_consistency_ratio"] == 1.0  # All significant ones are positive
