"""
Unit tests for StrategyRegistry implementation.
"""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from aponyx.backtest.registry import StrategyRegistry, StrategyMetadata
from aponyx.backtest.config import BacktestConfig
from aponyx.config import STRATEGY_CATALOG_PATH


def test_strategy_metadata_validation() -> None:
    """Test StrategyMetadata validation in __post_init__."""
    # Valid metadata
    metadata = StrategyMetadata(
        name="test",
        description="Test strategy",
        entry_threshold=2.0,
        exit_threshold=1.0,
    )
    assert metadata.name == "test"
    assert metadata.entry_threshold == 2.0

    # Invalid: entry <= exit
    with pytest.raises(ValueError, match="entry_threshold.*must be >"):
        StrategyMetadata(
            name="invalid",
            description="Invalid",
            entry_threshold=1.0,
            exit_threshold=1.0,
        )

    # Invalid: empty name
    with pytest.raises(ValueError, match="name cannot be empty"):
        StrategyMetadata(
            name="",
            description="No name",
            entry_threshold=2.0,
            exit_threshold=1.0,
        )


def test_strategy_metadata_to_config() -> None:
    """Test converting StrategyMetadata to BacktestConfig."""
    metadata = StrategyMetadata(
        name="aggressive",
        description="Aggressive strategy",
        entry_threshold=1.0,
        exit_threshold=0.5,
    )

    # Use defaults
    config = metadata.to_config()
    assert isinstance(config, BacktestConfig)
    assert config.entry_threshold == 1.0
    assert config.exit_threshold == 0.5
    assert config.position_size == 10.0  # Default
    assert config.transaction_cost_bps == 1.0  # Default

    # Override defaults
    config = metadata.to_config(
        position_size=20.0,
        transaction_cost_bps=1.5,
        max_holding_days=10,
    )
    assert config.position_size == 20.0
    assert config.transaction_cost_bps == 1.5
    assert config.max_holding_days == 10


def test_strategy_registry_loads_catalog() -> None:
    """Test that StrategyRegistry loads catalog from actual file."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

    strategies = registry.list_all()
    assert len(strategies) >= 3  # At least conservative, balanced, aggressive

    # Check specific strategies exist
    assert "conservative" in strategies
    assert "balanced" in strategies
    assert "aggressive" in strategies


def test_strategy_registry_get_metadata() -> None:
    """Test retrieving strategy metadata."""
    registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

    metadata = registry.get_metadata("balanced")
    assert metadata.name == "balanced"
    assert metadata.entry_threshold == 1.5
    assert metadata.exit_threshold == 0.75

    # Non-existent strategy
    with pytest.raises(KeyError, match="not found"):
        registry.get_metadata("nonexistent")


def test_strategy_registry_get_enabled() -> None:
    """Test filtering enabled strategies."""
    catalog_data = [
        {
            "name": "enabled_strategy",
            "description": "Enabled",
            "entry_threshold": 2.0,
            "exit_threshold": 1.0,
            "enabled": True,
        },
        {
            "name": "disabled_strategy",
            "description": "Disabled",
            "entry_threshold": 1.5,
            "exit_threshold": 0.75,
            "enabled": False,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "test_catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        registry = StrategyRegistry(catalog_path)
        enabled = registry.get_enabled()

        assert len(enabled) == 1
        assert "enabled_strategy" in enabled
        assert "disabled_strategy" not in enabled


def test_strategy_registry_file_not_found() -> None:
    """Test that StrategyRegistry raises error for missing catalog."""
    with pytest.raises(FileNotFoundError, match="Strategy catalog not found"):
        StrategyRegistry("nonexistent_catalog.json")


def test_strategy_registry_invalid_json() -> None:
    """Test that StrategyRegistry raises error for invalid JSON."""
    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "invalid.json"

        # Not a list
        with open(catalog_path, "w") as f:
            json.dump({"not": "a list"}, f)

        with pytest.raises(ValueError, match="must be a JSON array"):
            StrategyRegistry(catalog_path)


def test_strategy_registry_duplicate_names() -> None:
    """Test that duplicate strategy names raise error."""
    catalog_data = [
        {
            "name": "duplicate",
            "description": "First",
            "entry_threshold": 2.0,
            "exit_threshold": 1.0,
        },
        {
            "name": "duplicate",
            "description": "Second",
            "entry_threshold": 1.5,
            "exit_threshold": 0.75,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "duplicates.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        with pytest.raises(ValueError, match="Duplicate strategy name"):
            StrategyRegistry(catalog_path)


def test_strategy_registry_save_catalog() -> None:
    """Test saving strategy catalog to file."""
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
        output_path = Path(tmpdir) / "output.json"

        # Create initial catalog
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        registry = StrategyRegistry(catalog_path)

        # Save to new location
        registry.save_catalog(output_path)
        assert output_path.exists()

        # Load saved catalog and verify
        with open(output_path, "r") as f:
            saved_data = json.load(f)

        assert len(saved_data) == 1
        assert saved_data[0]["name"] == "test_strategy"


def test_strategy_registry_fail_fast_validation() -> None:
    """Test that invalid thresholds fail at load time."""
    catalog_data = [
        {
            "name": "invalid",
            "description": "Invalid thresholds",
            "entry_threshold": 0.5,  # Less than exit
            "exit_threshold": 1.0,
            "enabled": True,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "invalid.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        # Should fail during registry initialization
        with pytest.raises(ValueError, match="entry_threshold.*must be >"):
            StrategyRegistry(catalog_path)
