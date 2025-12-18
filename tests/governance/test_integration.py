"""
Integration tests for governance spine pattern across all pillars.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from aponyx.config import (
    SIGNAL_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
    REGISTRY_PATH,
    DATA_DIR,
)
from aponyx.data.registry import DataRegistry
from aponyx.models.registry import SignalRegistry
from aponyx.backtest.registry import StrategyRegistry


# Test helper for creating complete strategy metadata
def _make_test_metadata(**overrides) -> dict:
    """Create a complete strategy metadata dict for testing.
    
    Note: StrategyMetadata no longer contains microstructure fields
    (transaction_cost_bps, dv01_per_million). These are now loaded from
    bloomberg_securities.json at runtime.
    """
    defaults = {
        "name": "test_strategy",
        "description": "Test strategy",
        "position_size_mm": 10.0,
        "sizing_mode": "proportional",
        "stop_loss_pct": None,
        "take_profit_pct": None,
        "max_holding_days": None,
        "enabled": True,
    }
    defaults.update(overrides)
    return defaults


def test_all_registries_follow_governance_spine() -> None:
    """
    Test that all registries follow the governance spine lifecycle:
    1. Load from JSON
    2. Inspect/query
    3. Use in operations
    4. Optionally save
    """
    # DataRegistry
    data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
    datasets = data_registry.list_datasets()  # Inspect
    assert isinstance(datasets, list)

    # SignalRegistry
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    enabled_signals = signal_registry.get_enabled()  # Inspect
    assert isinstance(enabled_signals, dict)

    # StrategyRegistry
    strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    enabled_strategies = strategy_registry.get_enabled()  # Inspect
    assert isinstance(enabled_strategies, dict)


def test_registries_enforce_deterministic_loading() -> None:
    """Test that loading same JSON twice yields identical structures."""
    # Create test catalog with complete metadata
    catalog_data = [
        _make_test_metadata(
            name="test_strategy",
            description="Test",
            sizing_mode="binary",
            enabled=True,
        ),
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        # Load twice
        registry1 = StrategyRegistry(catalog_path)
        registry2 = StrategyRegistry(catalog_path)

        # Should have identical content
        strategies1 = registry1.list_all()
        strategies2 = registry2.list_all()

        assert len(strategies1) == len(strategies2)
        assert set(strategies1.keys()) == set(strategies2.keys())

        for name in strategies1.keys():
            meta1 = strategies1[name]
            meta2 = strategies2[name]
            assert meta1.position_size_mm == meta2.position_size_mm
            assert meta1.sizing_mode == meta2.sizing_mode


def test_catalog_validation_prevents_invalid_state() -> None:
    """Test that fail-fast validation prevents invalid catalogs."""
    # Invalid signal catalog (missing required fields)
    signal_catalog = [
        {
            "name": "invalid_signal",
            "description": "Invalid",
            "enabled": True,
            # Missing required fields: indicator_dependencies, transformations
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "signals.json"
        with open(catalog_path, "w") as f:
            json.dump(signal_catalog, f)

        # Should fail at load time
        try:
            SignalRegistry(catalog_path)
            assert False, "Expected ValueError for missing required fields"
        except ValueError as e:
            assert "Invalid signal metadata" in str(e)

    # Invalid strategy catalog (bad position size)
    strategy_catalog = [
        _make_test_metadata(
            name="invalid_strategy",
            description="Invalid",
            position_size_mm=-5.0,
            sizing_mode="binary",
            enabled=True,
        ),
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "strategies.json"
        with open(catalog_path, "w") as f:
            json.dump(strategy_catalog, f)

        # Should fail at load time
        try:
            StrategyRegistry(catalog_path)
            assert False, "Expected ValueError for invalid position size"
        except ValueError as e:
            assert "position_size_mm must be positive" in str(e)


def test_cross_layer_integration() -> None:
    """Test that governance enables clean cross-layer integration."""
    # Signal catalog references exactly one transformation from each stage
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    signal_metadata = signal_registry.get_metadata("cdx_etf_basis")

    # Verify signal references transformations from all three stages
    assert signal_metadata.indicator_transformation is not None
    assert signal_metadata.score_transformation is not None
    assert signal_metadata.signal_transformation is not None
    assert signal_metadata.indicator_transformation == "cdx_etf_spread_diff"

    # Strategy catalog produces configs for backtest layer
    # Now requires product microstructure params to be passed
    strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    strategy_metadata = strategy_registry.get_metadata("balanced")

    # Verify conversion to BacktestConfig with product params
    config = strategy_metadata.to_config(
        dv01_per_million=475.0,
        transaction_cost_bps=1.5,
    )
    assert config.position_size_mm == strategy_metadata.position_size_mm
    assert config.stop_loss_pct == strategy_metadata.stop_loss_pct
    assert config.dv01_per_million == 475.0
    assert config.transaction_cost_bps == 1.5


def test_json_persistence_roundtrip() -> None:
    """Test that save/load roundtrip preserves data exactly."""
    original_data = [
        _make_test_metadata(
            name="roundtrip_test",
            description="Test roundtrip",
            position_size_mm=12.5,
            sizing_mode="binary",
            stop_loss_pct=5.0,
            enabled=True,
        ),
    ]

    with TemporaryDirectory() as tmpdir:
        original_path = Path(tmpdir) / "original.json"
        saved_path = Path(tmpdir) / "saved.json"

        # Write original
        with open(original_path, "w") as f:
            json.dump(original_data, f, indent=2)

        # Load and save
        registry = StrategyRegistry(original_path)
        registry.save_catalog(saved_path)

        # Load saved and compare
        with open(saved_path, "r") as f:
            saved_data = json.load(f)

        assert len(saved_data) == len(original_data)
        assert saved_data[0]["name"] == original_data[0]["name"]
        assert saved_data[0]["position_size_mm"] == original_data[0]["position_size_mm"]
        assert saved_data[0]["stop_loss_pct"] == original_data[0]["stop_loss_pct"]
