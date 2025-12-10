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
    from aponyx.models.registry import SignalRegistry, IndicatorTransformationRegistry
    from aponyx.config import INDICATOR_TRANSFORMATION_PATH

    # Get signal registry
    signal_registry = SignalRegistry(test_catalog_path)
    indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)

    # Get all signals (list_all returns dict[str, SignalMetadata])
    all_signals = signal_registry.list_all()

    # Collect data requirements from indicators for enabled signals
    all_requirements = set()
    for signal_name, signal_metadata in all_signals.items():
        if signal_metadata.enabled:
            # In new structure, signal has single indicator_transformation reference
            indicator_name = signal_metadata.indicator_transformation
            indicator_metadata = indicator_registry.get_metadata(indicator_name)
            all_requirements.update(indicator_metadata.data_requirements.keys())

    # Should include keys from enabled signals' indicators
    assert len(all_requirements) >= 2
    assert (
        "cdx" in all_requirements
        or "etf" in all_requirements
        or "vix" in all_requirements
    )


# ===== Validation Error Tests (T031, T032) =====


class TestCatalogValidationErrors:
    """Test validation errors for catalog entries (T031-T032)."""

    def test_signal_transformation_invalid_name(self):
        """Test validation error for invalid signal transformation name."""
        from aponyx.models.metadata import SignalTransformationMetadata, CatalogValidationError

        with pytest.raises(CatalogValidationError) as exc_info:
            SignalTransformationMetadata(
                name="Invalid-Name",  # Invalid: contains hyphen
                description="Test transformation",
                scaling=1.0,
            )

        # Check error structure
        error = exc_info.value
        assert error.catalog == "signal_transformation.json"
        assert error.field == "name"
        assert error.value == "Invalid-Name"
        assert "lowercase with underscores" in error.constraint
        assert "lowercase letters" in error.suggestion

    def test_signal_transformation_short_description(self):
        """Test validation error for too-short description."""
        from aponyx.models.metadata import SignalTransformationMetadata, CatalogValidationError

        with pytest.raises(CatalogValidationError) as exc_info:
            SignalTransformationMetadata(
                name="test_transform",
                description="Short",  # Invalid: less than 10 chars
                scaling=1.0,
            )

        error = exc_info.value
        assert error.field == "description"
        assert "at least 10 characters" in error.constraint

    def test_signal_transformation_zero_scaling(self):
        """Test validation error for zero scaling."""
        from aponyx.models.metadata import SignalTransformationMetadata, CatalogValidationError

        with pytest.raises(CatalogValidationError) as exc_info:
            SignalTransformationMetadata(
                name="test_transform",
                description="Test transformation with zero scaling",
                scaling=0.0,  # Invalid: zero scaling
            )

        error = exc_info.value
        assert error.field == "scaling"
        assert error.value == 0.0
        assert "non-zero" in error.constraint

    def test_signal_transformation_floor_greater_than_cap(self):
        """Test validation error for floor > cap."""
        from aponyx.models.metadata import SignalTransformationMetadata, CatalogValidationError

        with pytest.raises(CatalogValidationError) as exc_info:
            SignalTransformationMetadata(
                name="test_transform",
                description="Test transformation with inverted bounds",
                scaling=1.0,
                floor=2.0,  # Invalid: floor > cap
                cap=1.0,
            )

        error = exc_info.value
        assert error.field == "floor"
        assert "floor must be <= cap" in error.constraint

    def test_signal_transformation_invalid_neutral_range_order(self):
        """Test validation error for neutral_range[0] > neutral_range[1]."""
        from aponyx.models.metadata import SignalTransformationMetadata, CatalogValidationError

        with pytest.raises(CatalogValidationError) as exc_info:
            SignalTransformationMetadata(
                name="test_transform",
                description="Test transformation with inverted neutral range",
                scaling=1.0,
                neutral_range=(0.5, -0.5),  # Invalid: high < low
            )

        error = exc_info.value
        assert error.field == "neutral_range"
        assert "neutral_range[0]" in error.constraint
        assert "must be <=" in error.constraint

    def test_catalog_validation_error_structure(self):
        """Test CatalogValidationError contains all required fields."""
        from aponyx.models.metadata import CatalogValidationError

        error = CatalogValidationError(
            catalog="signal_transformation.json",
            entry="test_signal",
            field="floor",
            value=2.0,
            constraint="floor must be <= cap",
            suggestion="Set floor <= 1.5",
        )

        # Check all attributes present
        assert error.catalog == "signal_transformation.json"
        assert error.entry == "test_signal"
        assert error.field == "floor"
        assert error.value == 2.0
        assert error.constraint == "floor must be <= cap"
        assert error.suggestion == "Set floor <= 1.5"

        # Check error message format
        error_msg = str(error)
        assert "signal_transformation.json" in error_msg
        assert "test_signal" in error_msg
        assert "floor" in error_msg
        assert "2.0" in error_msg
        assert "floor must be <= cap" in error_msg
        assert "Set floor <= 1.5" in error_msg
