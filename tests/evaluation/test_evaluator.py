"""Tests for core evaluator functionality."""

import numpy as np
import pandas as pd
import pytest

from aponyx.evaluation.suitability import (
    evaluate_signal_suitability,
    compute_forward_returns,
    SuitabilityConfig,
)


class TestComputeForwardReturns:
    """Test forward returns computation."""

    def test_single_lag(self):
        """Test computing forward returns for single lag."""
        spreads = pd.Series(
            [100, 102, 98, 101, 105],
            index=pd.date_range("2020-01-01", periods=5),
        )

        forward_returns = compute_forward_returns(spreads, [1])

        expected = pd.Series([2.0, -4.0, 3.0, 4.0, np.nan], index=spreads.index)
        pd.testing.assert_series_equal(forward_returns[1], expected)

    def test_multiple_lags(self):
        """Test computing forward returns for multiple lags."""
        spreads = pd.Series(
            [100, 102, 98, 101, 105],
            index=pd.date_range("2020-01-01", periods=5),
        )

        forward_returns = compute_forward_returns(spreads, [1, 2])

        assert 1 in forward_returns
        assert 2 in forward_returns
        assert forward_returns[1].iloc[0] == 2.0  # 102 - 100
        assert forward_returns[2].iloc[0] == -2.0  # 98 - 100


class TestEvaluateSignalSuitability:
    """Test end-to-end evaluation."""

    def test_perfect_correlation_passes(self):
        """Test that strong predictive relationship results in PASS."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=600)

        # Create signal that predicts future target movements
        signal = pd.Series(np.random.randn(600), index=dates, name="strong_signal")
        
        # Target is cumulative sum of (signal + noise), so current signal predicts future changes
        target_changes = signal * 5.0 + np.random.randn(600) * 0.1
        target = target_changes.cumsum() + 100.0  # Start at 100

        result = evaluate_signal_suitability(signal, target)

        assert result.decision == "PASS"
        assert result.composite_score > 0.7
        assert result.data_health_score == 1.0
        assert result.predictive_score > 0.5  # Multi-lag mean t-stat
        assert result.stability_score == 1.0

    def test_no_correlation_fails(self):
        """Test that no correlation results in FAIL."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=600)

        signal = pd.Series(np.random.randn(600), index=dates, name="random_signal")
        target = pd.Series(np.random.randn(600), index=dates)  # Independent

        result = evaluate_signal_suitability(signal, target)

        # No correlation should produce low predictive score
        assert result.composite_score < 0.7
        assert result.decision in ["HOLD", "FAIL"]
        assert result.predictive_score < 0.4  # Low but not zero due to random noise

    def test_insufficient_data_fails(self):
        """Test that insufficient data is flagged in data health."""
        dates = pd.date_range("2020-01-01", periods=50)

        signal = pd.Series(np.random.randn(50), index=dates, name="small_signal")
        target = signal * 2.0

        config = SuitabilityConfig(min_obs=500)
        result = evaluate_signal_suitability(signal, target, config)

        # Should penalize data health score
        assert result.data_health_score < 1.0
        assert result.valid_obs < 500

    def test_regime_change_fails_stability(self):
        """Test that regime change fails stability test."""
        dates = pd.date_range("2020-01-01", periods=600)

        # First half: positive relationship
        signal1 = pd.Series(np.linspace(0, 10, 300))
        target1 = signal1 * 2.0

        # Second half: negative relationship
        signal2 = pd.Series(np.linspace(0, 10, 300))
        target2 = signal2 * -2.0

        signal = pd.concat([signal1, signal2], ignore_index=True)
        signal.index = dates
        signal.name = "regime_change_signal"

        target = pd.concat([target1, target2], ignore_index=True)
        target.index = dates

        result = evaluate_signal_suitability(signal, target)

        # Should have good predictive score but fail stability
        assert result.stability_score == 0.0
        assert len(result.subperiod_betas) == 2
        assert result.subperiod_betas[0] > 0
        assert result.subperiod_betas[1] < 0

    def test_result_to_dict(self):
        """Test that result can be serialized to dict."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=600, freq="D")
        signal = pd.Series(np.random.randn(600), index=dates, name="test_signal")
        target = signal * 2.0 + np.random.randn(600) * 0.5

        result = evaluate_signal_suitability(signal, target)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "decision" in result_dict
        assert "composite_score" in result_dict
        assert "component_scores" in result_dict
        assert "metrics" in result_dict
        assert "timestamp" in result_dict
        assert "config" in result_dict

    def test_custom_config(self):
        """Test evaluation with custom configuration."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=600, freq="D")
        signal = pd.Series(np.random.randn(600), index=dates, name="test_signal")
        target = signal * 2.0 + np.random.randn(600) * 0.5

        config = SuitabilityConfig(
            pass_threshold=0.8,
            hold_threshold=0.5,
            predictive_weight=0.5,
            economic_weight=0.3,
            data_health_weight=0.1,
            stability_weight=0.1,
        )

        result = evaluate_signal_suitability(signal, target, config)

        assert result.config == config

    def test_validates_datetime_index(self):
        """Test that non-DatetimeIndex raises ValueError."""
        signal = pd.Series([1, 2, 3], name="bad_signal")
        target = pd.Series([2, 4, 6])

        with pytest.raises(ValueError, match="Signal must have DatetimeIndex"):
            evaluate_signal_suitability(signal, target)

    def test_handles_missing_data(self):
        """Test that missing data is handled correctly."""
        dates = pd.date_range("2020-01-01", periods=600)

        signal = pd.Series(np.random.randn(600), index=dates, name="signal_with_na")
        target = pd.Series(np.random.randn(600), index=dates)

        # Add some NaN values
        signal.iloc[10:20] = np.nan
        target.iloc[50:60] = np.nan

        result = evaluate_signal_suitability(signal, target)

        # Should have fewer valid obs
        assert result.valid_obs < 600
        assert result.missing_pct > 0
