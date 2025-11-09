"""Tests for performance configuration."""

import pytest

from aponyx.evaluation.performance.config import PerformanceConfig


class TestPerformanceConfigCreation:
    """Test PerformanceConfig initialization and defaults."""

    def test_default_config(self) -> None:
        """Test creating config with default values."""
        config = PerformanceConfig()

        assert config.min_obs == 252
        assert config.n_subperiods == 4
        assert config.risk_free_rate == 0.0
        assert config.rolling_window == 63
        assert config.report_format == "markdown"
        assert config.attribution_quantiles == 3

    def test_custom_config(self) -> None:
        """Test creating config with custom values."""
        config = PerformanceConfig(
            min_obs=500,
            n_subperiods=6,
            risk_free_rate=0.02,
            rolling_window=126,
            report_format="json",
            attribution_quantiles=5,
        )

        assert config.min_obs == 500
        assert config.n_subperiods == 6
        assert config.risk_free_rate == 0.02
        assert config.rolling_window == 126
        assert config.report_format == "json"
        assert config.attribution_quantiles == 5


class TestPerformanceConfigValidation:
    """Test PerformanceConfig validation logic."""

    def test_min_obs_too_small_raises(self) -> None:
        """Test that min_obs < 100 raises ValueError."""
        with pytest.raises(ValueError, match="min_obs must be at least 100"):
            PerformanceConfig(min_obs=50)

    def test_n_subperiods_too_small_raises(self) -> None:
        """Test that n_subperiods < 2 raises ValueError."""
        with pytest.raises(ValueError, match="n_subperiods must be at least 2"):
            PerformanceConfig(n_subperiods=1)

        with pytest.raises(ValueError, match="n_subperiods must be at least 2"):
            PerformanceConfig(n_subperiods=0)

    def test_negative_risk_free_rate_raises(self) -> None:
        """Test that negative risk_free_rate raises ValueError."""
        with pytest.raises(ValueError, match="risk_free_rate must be non-negative"):
            PerformanceConfig(risk_free_rate=-0.05)

    def test_rolling_window_too_small_raises(self) -> None:
        """Test that rolling_window < 20 raises ValueError."""
        with pytest.raises(ValueError, match="rolling_window must be at least 20 days"):
            PerformanceConfig(rolling_window=10)

    def test_invalid_report_format_raises(self) -> None:
        """Test that invalid report_format raises ValueError."""
        with pytest.raises(ValueError, match="report_format must be one of"):
            PerformanceConfig(report_format="pdf")

        with pytest.raises(ValueError, match="report_format must be one of"):
            PerformanceConfig(report_format="xml")

    def test_attribution_quantiles_too_small_raises(self) -> None:
        """Test that attribution_quantiles < 2 raises ValueError."""
        with pytest.raises(ValueError, match="attribution_quantiles must be at least 2"):
            PerformanceConfig(attribution_quantiles=1)


class TestPerformanceConfigImmutability:
    """Test that PerformanceConfig is immutable (frozen)."""

    def test_config_is_frozen(self) -> None:
        """Test that config attributes cannot be modified."""
        config = PerformanceConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.min_obs = 1000  # type: ignore

        with pytest.raises(Exception):
            config.n_subperiods = 10  # type: ignore
