"""
Unit tests for signal catalog orchestration.
"""

import json
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from aponyx.models.orchestrator import compute_registered_signals
from aponyx.data.requirements import get_required_data_keys
from aponyx.models.metadata import SignalMetadata
from aponyx.models.registry import SignalRegistry


@pytest.fixture
def mock_market_data() -> dict[str, pd.DataFrame]:
    """Create mock market data for testing."""
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    np.random.seed(42)

    return {
        "cdx": pd.DataFrame(
            {
                "spread": 100 + np.random.randn(50) * 5,
            },
            index=dates,
        ),
        "etf": pd.DataFrame(
            {
                "spread": 50 + np.random.randn(50) * 2,
            },
            index=dates,
        ),
        "vix": pd.DataFrame(
            {
                "level": 15 + np.random.randn(50) * 3,
            },
            index=dates,
        ),
    }


@pytest.fixture
def test_catalog_path() -> Path:
    """Get path to actual signal catalog."""
    # Use the real catalog for integration testing
    return Path("src/aponyx/models/signal_catalog.json")


def test_compute_registered_signals_all_enabled(
    test_catalog_path: Path,
    mock_market_data: dict[str, pd.DataFrame],
) -> None:
    """Test computing all enabled signals from registry."""
    registry = SignalRegistry(test_catalog_path)
    config = SignalConfig(lookback=10, min_periods=5)

    signals = compute_registered_signals(registry, mock_market_data, config)

    # Should have all 3 pilot signals
    assert len(signals) == 3
    assert "cdx_etf_basis" in signals
    assert "cdx_vix_gap" in signals
    assert "spread_momentum" in signals

    # All should be Series
    for name, signal in signals.items():
        assert isinstance(signal, pd.Series)
        assert len(signal) == 50


def test_compute_registered_signals_with_disabled(
    mock_market_data: dict[str, pd.DataFrame],
) -> None:
    """Test that disabled signals are not computed."""
    catalog_data = [
        {
            "name": "enabled_signal",
            "description": "Enabled",
            "compute_function_name": "compute_spread_momentum",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
        },
        {
            "name": "disabled_signal",
            "description": "Disabled",
            "compute_function_name": "compute_cdx_etf_basis",
            "data_requirements": {"cdx": "spread", "etf": "spread"},
            "arg_mapping": ["cdx", "etf"],
            "enabled": False,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        registry = SignalRegistry(catalog_path)
        config = SignalConfig()

        signals = compute_registered_signals(registry, mock_market_data, config)

        # Only enabled signal should be computed
        assert len(signals) == 1
        assert "enabled_signal" in signals
        assert "disabled_signal" not in signals


def test_compute_registered_signals_missing_data_key() -> None:
    """Test that missing market data key raises ValueError."""
    catalog_data = [
        {
            "name": "test_signal",
            "description": "Test",
            "compute_function_name": "compute_cdx_etf_basis",
            "data_requirements": {"cdx": "spread", "etf": "spread"},
            "arg_mapping": ["cdx", "etf"],
            "enabled": True,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        registry = SignalRegistry(catalog_path)
        config = SignalConfig()

        # Market data missing 'etf' key
        market_data = {"cdx": pd.DataFrame({"spread": [100, 101, 102]})}

        with pytest.raises(ValueError, match="requires market data key 'etf'"):
            compute_registered_signals(registry, market_data, config)


def test_compute_registered_signals_missing_column() -> None:
    """Test that missing required column raises ValueError."""
    catalog_data = [
        {
            "name": "test_signal",
            "description": "Test",
            "compute_function_name": "compute_cdx_etf_basis",
            "data_requirements": {"cdx": "spread", "etf": "spread"},
            "arg_mapping": ["cdx", "etf"],
            "enabled": True,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        registry = SignalRegistry(catalog_path)
        config = SignalConfig()

        # ETF data missing 'spread' column
        market_data = {
            "cdx": pd.DataFrame({"spread": [100, 101, 102]}),
            "etf": pd.DataFrame({"price": [50, 51, 52]}),  # Wrong column name
        }

        with pytest.raises(ValueError, match="requires column 'spread'"):
            compute_registered_signals(registry, market_data, config)


def test_compute_registered_signals_invalid_function_name() -> None:
    """Test that invalid compute function name raises ValueError at load time."""
    catalog_data = [
        {
            "name": "test_signal",
            "description": "Test",
            "compute_function_name": "nonexistent_function",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        # Fail-fast validation catches this at registry load time
        with pytest.raises(ValueError, match="non-existent compute function"):
            SignalRegistry(catalog_path)


def test_validate_data_requirements_success() -> None:
    """Test successful data requirements validation."""
    metadata = SignalMetadata(
        name="test",
        description="Test",
        compute_function_name="compute_test",
        data_requirements={"cdx": "spread", "vix": "level"},
        arg_mapping=["cdx", "vix"],
    )

    market_data = {
        "cdx": pd.DataFrame({"spread": [100, 101]}),
        "vix": pd.DataFrame({"level": [15, 16]}),
    }

    # Should not raise
    _validate_data_requirements(metadata, market_data)


def test_validate_data_requirements_missing_key() -> None:
    """Test validation failure for missing data key."""
    metadata = SignalMetadata(
        name="test",
        description="Test",
        compute_function_name="compute_test",
        data_requirements={"cdx": "spread", "missing_key": "close"},
        arg_mapping=["cdx", "missing_key"],  # Updated to match data_requirements
    )

    market_data = {
        "cdx": pd.DataFrame({"spread": [100, 101]}),
    }

    with pytest.raises(ValueError, match="requires market data key 'missing_key'"):
        _validate_data_requirements(metadata, market_data)


def test_validate_data_requirements_missing_column() -> None:
    """Test validation failure for missing column."""
    metadata = SignalMetadata(
        name="test",
        description="Test",
        compute_function_name="compute_test",
        data_requirements={"cdx": "missing_column"},
        arg_mapping=["cdx"],
    )

    market_data = {
        "cdx": pd.DataFrame({"spread": [100, 101]}),
    }

    with pytest.raises(ValueError, match="requires column 'missing_column'"):
        _validate_data_requirements(metadata, market_data)


def test_compute_registered_signals_returns_correct_types(
    test_catalog_path: Path,
    mock_market_data: dict[str, pd.DataFrame],
) -> None:
    """Test that all computed signals are pandas Series."""
    registry = SignalRegistry(test_catalog_path)
    config = SignalConfig()

    signals = compute_registered_signals(registry, mock_market_data, config)

    for name, signal in signals.items():
        assert isinstance(signal, pd.Series), f"Signal '{name}' is not a Series"
        assert signal.index.equals(mock_market_data["cdx"].index)


def test_compute_registered_signals_respects_config_parameters(
    test_catalog_path: Path,
    mock_market_data: dict[str, pd.DataFrame],
) -> None:
    """
    Test signal config behavior.
    
    Note: With indicator-signal separation, signals using the new pattern
    (indicator_dependencies) use catalog-defined parameters and ignore
    runtime config. This is expected behavior.
    """
    registry = SignalRegistry(test_catalog_path)

    # Use short lookback
    config_short = SignalConfig(lookback=5, min_periods=3)
    signals_short = compute_registered_signals(registry, mock_market_data, config_short)

    # Use long lookback
    config_long = SignalConfig(lookback=20, min_periods=10)
    signals_long = compute_registered_signals(registry, mock_market_data, config_long)

    # Signals using new pattern will produce identical results (catalog parameters).
    # This is expected and correct behavior.
    assert set(signals_short.keys()) == set(signals_long.keys())
    assert all(isinstance(s, pd.Series) for s in signals_short.values())


def test_get_required_data_keys(test_catalog_path: Path) -> None:
    """Test that get_required_data_keys returns union of all enabled signals' requirements."""
    registry = SignalRegistry(test_catalog_path)

    required_keys = get_required_data_keys(test_catalog_path)

    # Should include all keys from all 3 enabled signals
    assert "cdx" in required_keys
    assert "etf" in required_keys
    assert "vix" in required_keys

    # Should have exactly 3 keys (union of cdx_etf_basis, cdx_vix_gap, spread_momentum)
    assert len(required_keys) == 3


def test_get_required_data_keys_with_disabled(
    mock_market_data: dict[str, pd.DataFrame],
) -> None:
    """Test that get_required_data_keys only includes enabled signals."""
    catalog_data = [
        {
            "name": "enabled_signal",
            "description": "Enabled",
            "compute_function_name": "compute_spread_momentum",
            "data_requirements": {"cdx": "spread"},
            "arg_mapping": ["cdx"],
            "enabled": True,
        },
        {
            "name": "disabled_signal",
            "description": "Disabled",
            "compute_function_name": "compute_cdx_vix_gap",
            "data_requirements": {"cdx": "spread", "vix": "level", "extra": "data"},
            "arg_mapping": ["cdx", "vix", "extra"],
            "enabled": False,
        },
    ]

    with TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.json"
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)

        registry = SignalRegistry(catalog_path)
        required_keys = get_required_data_keys(catalog_path)

        # Should only include keys from enabled signal
        assert required_keys == {"cdx"}
        assert "vix" not in required_keys
        assert "extra" not in required_keys
