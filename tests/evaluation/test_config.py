"""Tests for suitability configuration."""

import pytest

from aponyx.evaluation.suitability.config import SuitabilityConfig


class TestSuitabilityConfigCreation:
    """Test SuitabilityConfig initialization and defaults."""

    def test_default_config(self) -> None:
        """Test creating config with default values."""
        config = SuitabilityConfig()

        assert config.lags == [1, 3, 5]
        assert config.min_obs == 500
        assert config.rolling_window == 252
        assert config.pass_threshold == 0.7
        assert config.hold_threshold == 0.4
        assert config.data_health_weight == 0.2
        assert config.predictive_weight == 0.4
        assert config.economic_weight == 0.2
        assert config.stability_weight == 0.2

    def test_custom_config(self) -> None:
        """Test creating config with custom values."""
        config = SuitabilityConfig(
            lags=[1, 5, 10],
            min_obs=1000,
            pass_threshold=0.75,
            hold_threshold=0.5,
            data_health_weight=0.1,
            predictive_weight=0.5,
            economic_weight=0.3,
            stability_weight=0.1,
        )

        assert config.lags == [1, 5, 10]
        assert config.min_obs == 1000
        assert config.pass_threshold == 0.75
        assert config.hold_threshold == 0.5
        assert config.data_health_weight == 0.1
        assert config.predictive_weight == 0.5
        assert config.economic_weight == 0.3
        assert config.stability_weight == 0.1


class TestSuitabilityConfigValidation:
    """Test SuitabilityConfig validation logic."""

    def test_empty_lags_raises(self) -> None:
        """Test that empty lags list raises ValueError."""
        with pytest.raises(ValueError, match="lags must be a non-empty list"):
            SuitabilityConfig(lags=[])

    def test_non_positive_lags_raise(self) -> None:
        """Test that non-positive lags raise ValueError."""
        with pytest.raises(ValueError, match="All lags must be positive integers"):
            SuitabilityConfig(lags=[1, -3, 5])

        with pytest.raises(ValueError, match="All lags must be positive integers"):
            SuitabilityConfig(lags=[0, 1, 2])

    def test_invalid_threshold_ordering_raises(self) -> None:
        """Test that invalid threshold ordering raises ValueError."""
        # hold >= pass
        with pytest.raises(ValueError, match="Thresholds must satisfy"):
            SuitabilityConfig(pass_threshold=0.5, hold_threshold=0.6)

        # hold == pass
        with pytest.raises(ValueError, match="Thresholds must satisfy"):
            SuitabilityConfig(pass_threshold=0.5, hold_threshold=0.5)

        # pass >= 1
        with pytest.raises(ValueError, match="Thresholds must satisfy"):
            SuitabilityConfig(pass_threshold=1.0, hold_threshold=0.5)

        # hold <= 0
        with pytest.raises(ValueError, match="Thresholds must satisfy"):
            SuitabilityConfig(pass_threshold=0.7, hold_threshold=0.0)

    def test_negative_weights_raise(self) -> None:
        """Test that negative weights raise ValueError."""
        with pytest.raises(ValueError, match="All weights must be non-negative"):
            SuitabilityConfig(data_health_weight=-0.1)

        with pytest.raises(ValueError, match="All weights must be non-negative"):
            SuitabilityConfig(predictive_weight=-0.2)

    def test_weights_not_sum_to_one_raise(self) -> None:
        """Test that weights not summing to 1.0 raise ValueError."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            SuitabilityConfig(
                data_health_weight=0.3,
                predictive_weight=0.3,
                economic_weight=0.3,
                stability_weight=0.3,  # Sum = 1.2
            )

        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            SuitabilityConfig(
                data_health_weight=0.1,
                predictive_weight=0.2,
                economic_weight=0.1,
                stability_weight=0.1,  # Sum = 0.5
            )

    def test_min_obs_too_small_raises(self) -> None:
        """Test that min_obs < 100 raises ValueError."""
        with pytest.raises(ValueError, match="min_obs must be at least 100 for reliable inference"):
            SuitabilityConfig(min_obs=50)

        with pytest.raises(ValueError, match="min_obs must be at least 100 for reliable inference"):
            SuitabilityConfig(min_obs=0)

    def test_rolling_window_too_small_raises(self) -> None:
        """Test that rolling_window < 50 raises ValueError."""
        with pytest.raises(ValueError, match="rolling_window must be at least 50 for meaningful statistics"):
            SuitabilityConfig(rolling_window=30)

        with pytest.raises(ValueError, match="rolling_window must be at least 50 for meaningful statistics"):
            SuitabilityConfig(rolling_window=0)


class TestSuitabilityConfigImmutability:
    """Test that SuitabilityConfig is immutable (frozen)."""

    def test_config_is_frozen(self) -> None:
        """Test that config attributes cannot be modified."""
        config = SuitabilityConfig()

        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.12
            config.lags = [1, 2, 3]  # type: ignore

        with pytest.raises(Exception):
            config.pass_threshold = 0.8  # type: ignore
