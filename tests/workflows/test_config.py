"""
Tests for WorkflowConfig validation.

Tests T031: display_channel validation in WorkflowConfig.__post_init__.
"""

import pytest

from aponyx.workflows.config import WorkflowConfig


class TestWorkflowConfigDisplayChannel:
    """Test T031: WorkflowConfig display_channel validation."""

    def test_valid_display_channel_spread(self):
        """Test display_channel='spread' is valid."""
        config = WorkflowConfig(
            label="test_config",
            signal_name="cdx_etf_basis",
            strategy_name="balanced",
            product="cdx_ig_5y",
            display_channel="spread",
        )
        assert config.display_channel == "spread"

    def test_valid_display_channel_price(self):
        """Test display_channel='price' is valid."""
        config = WorkflowConfig(
            label="test_config",
            signal_name="cdx_etf_basis",
            strategy_name="balanced",
            product="cdx_ig_5y",
            display_channel="price",
        )
        assert config.display_channel == "price"

    def test_valid_display_channel_level(self):
        """Test display_channel='level' is valid."""
        config = WorkflowConfig(
            label="test_config",
            signal_name="cdx_etf_basis",
            strategy_name="balanced",
            product="cdx_ig_5y",
            display_channel="level",
        )
        assert config.display_channel == "level"

    def test_display_channel_none_is_valid(self):
        """Test display_channel=None (default) is valid."""
        config = WorkflowConfig(
            label="test_config",
            signal_name="cdx_etf_basis",
            strategy_name="balanced",
            product="cdx_ig_5y",
        )
        assert config.display_channel is None

    def test_invalid_display_channel_raises(self):
        """Test invalid display_channel raises ValueError."""
        with pytest.raises(ValueError, match="Invalid display_channel"):
            WorkflowConfig(
                label="test_config",
                signal_name="cdx_etf_basis",
                strategy_name="balanced",
                product="cdx_ig_5y",
                display_channel="invalid_channel",
            )

    def test_invalid_display_channel_error_message(self):
        """Test error message includes valid channel names."""
        with pytest.raises(ValueError) as exc_info:
            WorkflowConfig(
                label="test_config",
                signal_name="cdx_etf_basis",
                strategy_name="balanced",
                product="cdx_ig_5y",
                display_channel="unknown",
            )
        error_msg = str(exc_info.value)
        assert "level" in error_msg
        assert "price" in error_msg
        assert "spread" in error_msg

    def test_display_channel_case_sensitive(self):
        """Test display_channel validation is case-sensitive."""
        with pytest.raises(ValueError, match="Invalid display_channel"):
            WorkflowConfig(
                label="test_config",
                signal_name="cdx_etf_basis",
                strategy_name="balanced",
                product="cdx_ig_5y",
                display_channel="SPREAD",  # Uppercase should fail
            )

    def test_display_channel_with_other_overrides(self):
        """Test display_channel works with other override fields."""
        config = WorkflowConfig(
            label="test_config",
            signal_name="cdx_etf_basis",
            strategy_name="balanced",
            product="cdx_ig_5y",
            display_channel="spread",
            dv01_per_million_override=500.0,
            transaction_cost_bps_override=2.0,
        )
        assert config.display_channel == "spread"
        assert config.dv01_per_million_override == 500.0
        assert config.transaction_cost_bps_override == 2.0


class TestWorkflowConfigExistingValidation:
    """Ensure existing validation still works after display_channel addition."""

    def test_label_validation_still_works(self):
        """Test label format validation is still enforced."""
        with pytest.raises(ValueError, match="invalid"):
            WorkflowConfig(
                label="Invalid-Label",  # Invalid format
                signal_name="cdx_etf_basis",
                strategy_name="balanced",
                product="cdx_ig_5y",
            )

    def test_transaction_cost_mutual_exclusivity(self):
        """Test transaction cost mutual exclusivity still enforced."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            WorkflowConfig(
                label="test_config",
                signal_name="cdx_etf_basis",
                strategy_name="balanced",
                product="cdx_ig_5y",
                transaction_cost_bps_override=1.0,
                transaction_cost_pct_override=0.025,
            )

    def test_invalid_steps_still_caught(self):
        """Test invalid steps validation still works."""
        with pytest.raises(ValueError, match="Invalid steps"):
            WorkflowConfig(
                label="test_config",
                signal_name="cdx_etf_basis",
                strategy_name="balanced",
                product="cdx_ig_5y",
                steps=["invalid_step"],
            )
