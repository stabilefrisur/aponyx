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


# Test helper for creating complete strategy metadata
def _make_test_metadata(**overrides) -> dict:
    """Create a complete strategy metadata dict for testing."""
    defaults = {
        "name": "test_strategy",
        "description": "Test strategy",
        "position_size_mm": 10.0,
        "sizing_mode": "proportional",
        "stop_loss_pct": None,
        "take_profit_pct": None,
        "max_holding_days": None,
        "transaction_cost_bps": 1.0,
        "dv01_per_million": 475.0,
        "enabled": True,
    }
    defaults.update(overrides)
    return defaults


def test_strategy_metadata_validation() -> None:
    """Test StrategyMetadata validation in __post_init__."""
    # Valid metadata
    metadata = StrategyMetadata(**_make_test_metadata(
        name="test",
        description="Test strategy",
        position_size_mm=10.0,
        sizing_mode="binary",
    ))
    assert metadata.name == "test"
    assert metadata.position_size_mm == 10.0

    # Invalid: negative position size
    with pytest.raises(ValueError, match="position_size_mm must be positive"):
        StrategyMetadata(**_make_test_metadata(
            name="invalid",
            description="Invalid",
            position_size_mm=-1.0,
        ))

    # Invalid: empty name
    with pytest.raises(ValueError, match="name cannot be empty"):
        StrategyMetadata(**_make_test_metadata(
            name="",
            description="No name",
            position_size_mm=10.0,
        ))


def test_strategy_metadata_to_config() -> None:
    """Test converting StrategyMetadata to BacktestConfig."""
    metadata = StrategyMetadata(**_make_test_metadata(
        name="aggressive",
        description="Aggressive strategy",
        position_size_mm=15.0,
        stop_loss_pct=10.0,
    ))

    # Use defaults
    config = metadata.to_config()
    assert isinstance(config, BacktestConfig)
    assert config.position_size_mm == 15.0
    assert config.stop_loss_pct == 10.0
    assert config.transaction_cost_bps == 1.0  # From metadata

    # Override defaults
    config = metadata.to_config(
        position_size_mm_override=20.0,
        stop_loss_pct_override=5.0,
    )
    assert config.position_size_mm == 20.0
    assert config.stop_loss_pct == 5.0


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
    assert metadata.position_size_mm == 10.0
    assert metadata.stop_loss_pct == 5.0

    # Non-existent strategy
    with pytest.raises(KeyError, match="not found"):
        registry.get_metadata("nonexistent")


def test_strategy_registry_get_enabled() -> None:
    """Test filtering enabled strategies."""
    catalog_data = [
        _make_test_metadata(
            name="enabled_strategy",
            description="Enabled",
            sizing_mode="binary",
            enabled=True,
        ),
        _make_test_metadata(
            name="disabled_strategy",
            description="Disabled",
            sizing_mode="binary",
            enabled=False,
        ),
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
        _make_test_metadata(
            name="duplicate",
            description="First",
            sizing_mode="binary",
        ),
        _make_test_metadata(
            name="duplicate",
            description="Second",
            sizing_mode="binary",
        ),
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
        _make_test_metadata(
            name="test_strategy",
            description="Test",
            sizing_mode="binary",
            enabled=True,
        ),
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
    """Test that invalid position size fails at load time."""
    catalog_data = [
        _make_test_metadata(
            name="invalid",
            description="Invalid position size",
            position_size_mm=-5.0,  # Negative
            sizing_mode="binary",
            enabled=True,
        ),
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "invalid.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        # Should fail during registry initialization
        with pytest.raises(ValueError, match="position_size_mm must be positive"):
            StrategyRegistry(catalog_path)
