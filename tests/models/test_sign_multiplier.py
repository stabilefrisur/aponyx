"""Tests for signal sign multiplier functionality."""

import pandas as pd
import pytest

from aponyx.models.catalog import compute_registered_signals
from aponyx.models.config import SignalConfig
from aponyx.models.registry import SignalMetadata, SignalRegistry


def test_sign_multiplier_in_metadata():
    """Test that SignalMetadata accepts and validates sign_multiplier."""
    # Valid multipliers
    metadata = SignalMetadata(
        name="test_signal",
        description="Test",
        compute_function_name="compute_cdx_etf_basis",
        data_requirements={"cdx": "spread"},
        arg_mapping=["cdx"],
        enabled=True,
        sign_multiplier=1,
    )
    assert metadata.sign_multiplier == 1

    metadata_inverted = SignalMetadata(
        name="test_signal",
        description="Test",
        compute_function_name="compute_cdx_etf_basis",
        data_requirements={"cdx": "spread"},
        arg_mapping=["cdx"],
        enabled=True,
        sign_multiplier=-1,
    )
    assert metadata_inverted.sign_multiplier == -1

    # Invalid multiplier
    with pytest.raises(ValueError, match="sign_multiplier must be -1 or 1"):
        SignalMetadata(
            name="test_signal",
            description="Test",
            compute_function_name="compute_cdx_etf_basis",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            enabled=True,
            sign_multiplier=2,
        )


def test_catalog_sign_multiplier_applied(tmp_path):
    """Test that catalog-level sign_multiplier is applied during computation."""
    # Create test catalog with inverted signal
    catalog_data = [
        {
            "name": "spread_momentum",
            "description": "Test signal",
            "compute_function_name": "compute_spread_momentum",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
            "sign_multiplier": -1,  # Invert signal
        }
    ]

    catalog_path = tmp_path / "test_catalog.json"
    import json

    with open(catalog_path, "w") as f:
        json.dump(catalog_data, f)

    # Create test data
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    cdx_df = pd.DataFrame(
        {"spread": range(100, 130)},  # Widening spreads
        index=dates,
    )

    # Compute signals
    registry = SignalRegistry(catalog_path)
    config = SignalConfig(lookback=10, min_periods=5)
    market_data = {"cdx": cdx_df}

    signals = compute_registered_signals(registry, market_data, config)

    # Verify signal was inverted
    # spread_momentum with widening spreads normally gives negative signal
    # With sign_multiplier=-1, should be positive
    assert "spread_momentum" in signals
    signal = signals["spread_momentum"]

    # Check that at least some values exist and have expected sign
    valid_values = signal.dropna()
    assert len(valid_values) > 0
    # With widening spreads and inversion, expect positive values
    assert valid_values.mean() > 0


def test_registry_loads_catalog_with_sign_multiplier():
    """Test that SignalRegistry properly loads sign_multiplier from catalog JSON."""
    from aponyx.config import SIGNAL_CATALOG_PATH

    registry = SignalRegistry(SIGNAL_CATALOG_PATH)

    # All signals should have sign_multiplier field
    for name, metadata in registry.list_all().items():
        assert hasattr(metadata, "sign_multiplier")
        assert metadata.sign_multiplier in (-1, 1)
        # Default catalog should have all multipliers = 1
        assert metadata.sign_multiplier == 1
