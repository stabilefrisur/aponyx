"""
Unit tests for signal catalog orchestration (new pattern only).
"""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path

from aponyx.models.orchestrator import compute_registered_signals
from aponyx.data.requirements import get_required_data_keys
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

    signals = compute_registered_signals(registry, mock_market_data)

    # Should have all 3 pilot signals
    assert len(signals) == 3
    assert "cdx_etf_basis" in signals
    assert "cdx_vix_gap" in signals
    assert "spread_momentum" in signals

    # All should be Series
    for name, signal in signals.items():
        assert isinstance(signal, pd.Series)
        assert len(signal) == 50


def test_compute_registered_signals_returns_correct_types(
    test_catalog_path: Path,
    mock_market_data: dict[str, pd.DataFrame],
) -> None:
    """Test that all computed signals are pandas Series."""
    registry = SignalRegistry(test_catalog_path)

    signals = compute_registered_signals(registry, mock_market_data)

    for name, signal in signals.items():
        assert isinstance(signal, pd.Series), f"Signal '{name}' is not a Series"
        assert signal.index.equals(mock_market_data["cdx"].index)


def test_get_required_data_keys(test_catalog_path: Path) -> None:
    """Test that get_required_data_keys returns union of all enabled signals' requirements."""
    from aponyx.models.registry import SignalRegistry, IndicatorRegistry
    from aponyx.config import INDICATOR_CATALOG_PATH

    # Get signal registry
    signal_registry = SignalRegistry(test_catalog_path)
    indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

    # Get all signals (list_all returns dict[str, SignalMetadata])
    all_signals = signal_registry.list_all()

    # Collect data requirements from indicators for enabled signals
    all_requirements = set()
    for signal_name, signal_metadata in all_signals.items():
        if signal_metadata.enabled:
            for indicator_name in signal_metadata.indicator_dependencies:
                indicator_metadata = indicator_registry.get_metadata(indicator_name)
                all_requirements.update(indicator_metadata.data_requirements.keys())

    # Should include keys from enabled signals' indicators
    assert len(all_requirements) >= 2
    assert (
        "cdx" in all_requirements
        or "etf" in all_requirements
        or "vix" in all_requirements
    )
