"""Tests for signal sign multiplier functionality."""

import pandas as pd
import pytest

from aponyx.models.orchestrator import compute_registered_signals
from aponyx.models.config import SignalConfig
from aponyx.models.metadata import SignalMetadata
from aponyx.models.registry import SignalRegistry


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
    """
    Test that catalog-level sign_multiplier is loaded and accessible.
    
    Note: Full integration testing of sign_multiplier application is done in
    test_orchestrator.py::test_compute_registered_signals_applies_sign_multiplier
    """
    # Create test catalog with inverted signal
    catalog_data = [
        {
            "name": "test_signal",
            "description": "Test signal with inverted multiplier",
            "compute_function_name": "compute_spread_momentum",  
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "default_securities": {"cdx": "cdx_ig_5y"},
            "enabled": True,
            "sign_multiplier": -1,  # Invert signal
        }
    ]

    catalog_path = tmp_path / "test_catalog.json"
    import json

    with open(catalog_path, "w") as f:
        json.dump(catalog_data, f)

    # Load registry and verify sign_multiplier is accessible
    registry = SignalRegistry(catalog_path)
    
    # Verify signal loaded correctly
    assert "test_signal" in registry.list_all()
    metadata = registry.get_metadata("test_signal")
    
    # Verify sign_multiplier was loaded correctly
    assert metadata.sign_multiplier == -1, "Sign multiplier should be -1"


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
