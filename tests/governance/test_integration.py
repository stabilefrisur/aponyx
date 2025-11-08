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
    # Create test catalog
    catalog_data = [
        {
            "name": "test_strategy",
            "description": "Test",
            "entry_threshold": 2.0,
            "exit_threshold": 1.0,
            "enabled": True,
        },
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
            assert meta1.entry_threshold == meta2.entry_threshold
            assert meta1.exit_threshold == meta2.exit_threshold


def test_catalog_validation_prevents_invalid_state() -> None:
    """Test that fail-fast validation prevents invalid catalogs."""
    # Invalid signal catalog (non-existent function)
    signal_catalog = [
        {
            "name": "invalid_signal",
            "description": "Invalid",
            "compute_function_name": "nonexistent_function",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "signals.json"
        with open(catalog_path, "w") as f:
            json.dump(signal_catalog, f)

        # Should fail at load time
        try:
            SignalRegistry(catalog_path)
            assert False, "Expected ValueError for invalid compute function"
        except ValueError as e:
            assert "non-existent compute function" in str(e)

    # Invalid strategy catalog (bad thresholds)
    strategy_catalog = [
        {
            "name": "invalid_strategy",
            "description": "Invalid",
            "entry_threshold": 0.5,
            "exit_threshold": 1.0,
            "enabled": True,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "strategies.json"
        with open(catalog_path, "w") as f:
            json.dump(strategy_catalog, f)

        # Should fail at load time
        try:
            StrategyRegistry(catalog_path)
            assert False, "Expected ValueError for invalid thresholds"
        except ValueError as e:
            assert "entry_threshold" in str(e) and "must be >" in str(e)


def test_cross_layer_integration() -> None:
    """Test that governance enables clean cross-layer integration."""
    # Signal catalog references compute functions in models layer
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    signal_metadata = signal_registry.get_metadata("cdx_etf_basis")

    # Verify compute function name follows convention
    assert signal_metadata.compute_function_name.startswith("compute_")
    assert signal_metadata.compute_function_name == "compute_cdx_etf_basis"

    # Strategy catalog produces configs for backtest layer
    strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
    strategy_metadata = strategy_registry.get_metadata("balanced")

    # Verify conversion to BacktestConfig
    config = strategy_metadata.to_config()
    assert config.entry_threshold == strategy_metadata.entry_threshold
    assert config.exit_threshold == strategy_metadata.exit_threshold


def test_json_persistence_roundtrip() -> None:
    """Test that save/load roundtrip preserves data exactly."""
    original_data = [
        {
            "name": "roundtrip_test",
            "description": "Test roundtrip",
            "entry_threshold": 1.234,
            "exit_threshold": 0.567,
            "enabled": True,
        },
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
        assert saved_data[0]["entry_threshold"] == original_data[0]["entry_threshold"]
        assert saved_data[0]["exit_threshold"] == original_data[0]["exit_threshold"]
