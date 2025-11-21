"""
Tests for signal computation orchestration.

Validates compute_registered_signals, get_required_data_keys,
data requirement validation, and dynamic function resolution.
"""

import numpy as np
import pandas as pd
import pytest

from aponyx.models.orchestrator import (
    compute_registered_signals,
    get_required_data_keys,
    _compute_signal,
    _validate_data_requirements,
)
from aponyx.models.config import SignalConfig
from aponyx.models.metadata import SignalMetadata
from aponyx.models.registry import SignalRegistry


@pytest.fixture
def sample_market_data() -> dict[str, pd.DataFrame]:
    """Generate sample market data for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    
    return {
        "cdx": pd.DataFrame(
            {"spread": 100 + np.arange(100) * 0.5},
            index=dates,
        ),
        "etf": pd.DataFrame(
            {"spread": 95 + np.arange(100) * 0.4},
            index=dates,
        ),
        "vix": pd.DataFrame(
            {"level": 15 + np.arange(100) * 0.1},
            index=dates,
        ),
    }


@pytest.fixture
def signal_config() -> SignalConfig:
    """Generate signal configuration."""
    return SignalConfig(lookback=20, min_periods=10)


@pytest.fixture
def test_registry(tmp_path) -> SignalRegistry:
    """Create a test signal registry with enabled signals."""
    catalog_path = tmp_path / "test_signal_catalog.json"
    
    # Create test catalog (array format)
    catalog_data = [
        {
            "name": "cdx_etf_basis",
            "description": "CDX-ETF basis signal",
            "compute_function_name": "compute_cdx_etf_basis",
            "data_requirements": {
                "cdx": "spread",
                "etf": "spread"
            },
            "arg_mapping": ["cdx", "etf"],
            "enabled": True,
            "sign_multiplier": 1
        },
        {
            "name": "spread_momentum",
            "description": "Spread momentum signal",
            "compute_function_name": "compute_spread_momentum",
            "data_requirements": {
                "cdx": "spread"
            },
            "arg_mapping": ["cdx"],
            "enabled": True,
            "sign_multiplier": 1
        },
        {
            "name": "disabled_signal",
            "description": "Disabled signal",
            "compute_function_name": "compute_cdx_vix_gap",
            "data_requirements": {
                "cdx": "spread",
                "vix": "level"
            },
            "arg_mapping": ["cdx", "vix"],
            "enabled": False,
            "sign_multiplier": 1
        }
    ]
    
    import json
    catalog_path.write_text(json.dumps(catalog_data, indent=2))
    
    return SignalRegistry(catalog_path)


class TestGetRequiredDataKeys:
    """Test data key requirement discovery."""

    def test_get_required_data_keys_all_enabled(self, test_registry):
        """Test getting data keys from all enabled signals."""
        data_keys = get_required_data_keys(test_registry)
        
        # Should include keys from enabled signals only
        assert "cdx" in data_keys
        assert "etf" in data_keys
        # Should not include disabled signal's unique requirements
        assert len(data_keys) == 2  # Only cdx and etf

    def test_get_required_data_keys_empty_registry(self, tmp_path):
        """Test with registry that has no enabled signals."""
        catalog_path = tmp_path / "empty_catalog.json"
        catalog_data = []  # Empty array
        
        import json
        catalog_path.write_text(json.dumps(catalog_data, indent=2))
        
        registry = SignalRegistry(catalog_path)
        data_keys = get_required_data_keys(registry)
        
        assert len(data_keys) == 0

    def test_get_required_data_keys_returns_set(self, test_registry):
        """Test that returned data keys are a set."""
        data_keys = get_required_data_keys(test_registry)
        
        assert isinstance(data_keys, set)


class TestComputeRegisteredSignals:
    """Test batch signal computation."""

    def test_compute_registered_signals_success(
        self,
        test_registry,
        sample_market_data,
        signal_config,
    ):
        """Test successful computation of all enabled signals."""
        results = compute_registered_signals(
            test_registry,
            sample_market_data,
            signal_config,
        )
        
        # Should have results for enabled signals
        assert "cdx_etf_basis" in results
        assert "spread_momentum" in results
        # Should not have disabled signal
        assert "disabled_signal" not in results

    def test_compute_registered_signals_returns_series(
        self,
        test_registry,
        sample_market_data,
        signal_config,
    ):
        """Test that results are pandas Series."""
        results = compute_registered_signals(
            test_registry,
            sample_market_data,
            signal_config,
        )
        
        for signal_name, signal_series in results.items():
            assert isinstance(signal_series, pd.Series)
            assert len(signal_series) == len(sample_market_data["cdx"])

    def test_compute_registered_signals_missing_data(
        self,
        test_registry,
        signal_config,
    ):
        """Test error when required data is missing."""
        # Provide incomplete market data
        incomplete_data = {
            "cdx": pd.DataFrame(
                {"spread": [100.0] * 10},
                index=pd.date_range("2024-01-01", periods=10),
            )
        }
        
        with pytest.raises(ValueError, match="requires market data key"):
            compute_registered_signals(
                test_registry,
                incomplete_data,
                signal_config,
            )

    def test_compute_registered_signals_missing_column(
        self,
        test_registry,
        signal_config,
    ):
        """Test error when required column is missing."""
        # Provide data with wrong column names
        bad_data = {
            "cdx": pd.DataFrame(
                {"price": [100.0] * 10},  # Should be 'spread'
                index=pd.date_range("2024-01-01", periods=10),
            ),
            "etf": pd.DataFrame(
                {"spread": [95.0] * 10},
                index=pd.date_range("2024-01-01", periods=10),
            ),
        }
        
        with pytest.raises(ValueError, match="requires column"):
            compute_registered_signals(
                test_registry,
                bad_data,
                signal_config,
            )

    def test_compute_registered_signals_applies_sign_multiplier(
        self,
        tmp_path,
        sample_market_data,
        signal_config,
    ):
        """Test that sign multiplier is applied from catalog."""
        # Create registry with inverted signal
        catalog_path = tmp_path / "inverted_catalog.json"
        catalog_data = [
            {
                "name": "inverted_momentum",
                "description": "Inverted momentum",
                "compute_function_name": "compute_spread_momentum",
                "data_requirements": {"cdx": "spread"},
                "arg_mapping": ["cdx"],
                "enabled": True,
                "sign_multiplier": -1
            }
        ]
        
        import json
        catalog_path.write_text(json.dumps(catalog_data, indent=2))
        
        registry = SignalRegistry(catalog_path)
        
        # Verify the function runs with inverted signal
        results = compute_registered_signals(
            registry,
            sample_market_data,
            signal_config,
        )
        
        assert "inverted_momentum" in results


class TestComputeSignal:
    """Test individual signal computation."""

    def test_compute_signal_basic(self, sample_market_data, signal_config):
        """Test computing a single signal."""
        metadata = SignalMetadata(
            name="test_basis",
            description="Test basis signal",
            compute_function_name="compute_cdx_etf_basis",
            data_requirements={"cdx": "spread", "etf": "spread"},
            arg_mapping=["cdx", "etf"],
            enabled=True,
            sign_multiplier=1,
        )
        
        result = _compute_signal(metadata, sample_market_data, signal_config)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_market_data["cdx"])

    def test_compute_signal_applies_sign_multiplier(
        self,
        sample_market_data,
        signal_config,
    ):
        """Test sign multiplier is applied to raw signal."""
        metadata_normal = SignalMetadata(
            name="normal",
            description="Normal signal",
            compute_function_name="compute_spread_momentum",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            enabled=True,
            sign_multiplier=1,
        )
        
        metadata_inverted = SignalMetadata(
            name="inverted",
            description="Inverted signal",
            compute_function_name="compute_spread_momentum",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            enabled=True,
            sign_multiplier=-1,
        )
        
        normal_result = _compute_signal(
            metadata_normal, sample_market_data, signal_config
        )
        inverted_result = _compute_signal(
            metadata_inverted, sample_market_data, signal_config
        )
        
        # Results should be negatives of each other
        pd.testing.assert_series_equal(normal_result, -inverted_result)

    def test_compute_signal_invalid_function(
        self,
        sample_market_data,
        signal_config,
    ):
        """Test error when compute function doesn't exist."""
        metadata = SignalMetadata(
            name="bad_signal",
            description="Signal with invalid function",
            compute_function_name="nonexistent_function",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            enabled=True,
            sign_multiplier=1,
        )
        
        with pytest.raises(AttributeError):
            _compute_signal(metadata, sample_market_data, signal_config)


class TestValidateDataRequirements:
    """Test data requirement validation."""

    def test_validate_data_requirements_success(self, sample_market_data):
        """Test validation succeeds with correct data."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test signal",
            compute_function_name="compute_cdx_etf_basis",
            data_requirements={"cdx": "spread", "etf": "spread"},
            arg_mapping=["cdx", "etf"],
            enabled=True,
            sign_multiplier=1,
        )
        
        # Should not raise
        _validate_data_requirements(metadata, sample_market_data)

    def test_validate_data_requirements_missing_key(self):
        """Test error when data key is missing."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test signal",
            compute_function_name="compute_cdx_vix_gap",
            data_requirements={"cdx": "spread", "vix": "level"},
            arg_mapping=["cdx", "vix"],
            enabled=True,
            sign_multiplier=1,
        )
        
        incomplete_data = {
            "cdx": pd.DataFrame(
                {"spread": [100.0]},
                index=pd.date_range("2024-01-01", periods=1),
            )
        }
        
        with pytest.raises(ValueError, match="requires market data key 'vix'"):
            _validate_data_requirements(metadata, incomplete_data)

    def test_validate_data_requirements_missing_column(self):
        """Test error when required column is missing."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test signal",
            compute_function_name="compute_cdx_etf_basis",
            data_requirements={"cdx": "spread", "etf": "spread"},
            arg_mapping=["cdx", "etf"],
            enabled=True,
            sign_multiplier=1,
        )
        
        bad_data = {
            "cdx": pd.DataFrame(
                {"price": [100.0]},  # Wrong column name
                index=pd.date_range("2024-01-01", periods=1),
            ),
            "etf": pd.DataFrame(
                {"spread": [95.0]},
                index=pd.date_range("2024-01-01", periods=1),
            ),
        }
        
        with pytest.raises(ValueError, match="requires column 'spread'"):
            _validate_data_requirements(metadata, bad_data)


class TestIntegration:
    """Integration tests for orchestration workflow."""

    def test_full_orchestration_workflow(
        self,
        test_registry,
        sample_market_data,
        signal_config,
    ):
        """Test complete workflow: discover data, compute signals."""
        # Step 1: Get required data keys
        data_keys = get_required_data_keys(test_registry)
        
        # Step 2: Verify we have all required data
        for key in data_keys:
            assert key in sample_market_data
        
        # Step 3: Compute all signals
        results = compute_registered_signals(
            test_registry,
            sample_market_data,
            signal_config,
        )
        
        # Step 4: Verify results
        enabled_signals = test_registry.get_enabled()
        assert len(results) == len(enabled_signals)
        
        for signal_name in enabled_signals:
            assert signal_name in results
            assert isinstance(results[signal_name], pd.Series)

    def test_orchestration_with_custom_config(
        self,
        test_registry,
        sample_market_data,
    ):
        """Test orchestration with different configurations."""
        # Short lookback
        short_config = SignalConfig(lookback=5, min_periods=3)
        short_results = compute_registered_signals(
            test_registry,
            sample_market_data,
            short_config,
        )
        
        # Long lookback
        long_config = SignalConfig(lookback=50, min_periods=25)
        long_results = compute_registered_signals(
            test_registry,
            sample_market_data,
            long_config,
        )
        
        # Should have same signals but different values
        assert set(short_results.keys()) == set(long_results.keys())
        
        # Check that at least one signal has valid (non-NaN) values
        # If both produce all NaN, the signal functions aren't working
        has_valid_short = any(s.notna().any() for s in short_results.values())
        has_valid_long = any(s.notna().any() for s in long_results.values())
        
        # At least the short config should produce some valid values
        assert has_valid_short, "Short config produced no valid signal values"
        
        # If both have valid values, they should differ
        # If long config produces all NaN (due to insufficient data), that's acceptable
        if has_valid_short and has_valid_long:
            for signal_name in short_results:
                # Values should differ due to different lookbacks
                assert not short_results[signal_name].equals(
                    long_results[signal_name]
                ), f"Signal {signal_name} is identical for different configs"
