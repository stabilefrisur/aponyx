"""
Tests for IndicatorRegistry.

Validates that the registry:
- Loads catalog correctly
- Validates compute functions exist
- Provides metadata access
- Handles validation errors appropriately
"""

import json
from pathlib import Path

import pytest

from aponyx.models.registry import IndicatorRegistry
from aponyx.config import INDICATOR_CATALOG_PATH


class TestLoadIndicatorCatalog:
    """Tests for indicator catalog loading."""

    def test_load_production_catalog(self):
        """Test loading the production indicator catalog."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        # Should load 3 pilot indicators
        assert len(registry._indicators) == 3
        assert "cdx_etf_spread_diff" in registry._indicators
        assert "spread_momentum_5d" in registry._indicators
        assert "cdx_vix_deviation_gap_20d" in registry._indicators

    def test_get_metadata(self):
        """Test retrieving indicator metadata."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        metadata = registry.get_metadata("cdx_etf_spread_diff")

        assert metadata.name == "cdx_etf_spread_diff"
        assert metadata.compute_function_name == "compute_cdx_etf_spread_diff"
        assert metadata.output_units == "basis_points"
        assert "cdx" in metadata.data_requirements
        assert "etf" in metadata.data_requirements

    def test_get_all_indicators(self):
        """Test retrieving all indicator names."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        indicators = registry.get_all_indicators()

        assert len(indicators) == 3
        assert "cdx_etf_spread_diff" in indicators
        assert "spread_momentum_5d" in indicators
        assert "cdx_vix_deviation_gap_20d" in indicators

    def test_get_enabled_indicators(self):
        """Test retrieving only enabled indicators."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        enabled = registry.get_enabled_indicators()

        # All pilot indicators should be enabled
        assert len(enabled) == 3

    def test_nonexistent_indicator(self):
        """Test error when requesting nonexistent indicator."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        with pytest.raises(ValueError, match="Indicator .* not found"):
            registry.get_metadata("nonexistent_indicator")


class TestValidateComputeFunctionsExist:
    """Tests for compute function validation."""

    def test_all_functions_exist(self):
        """Test that all catalog compute functions exist in indicators module."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        # Validation happens in __init__, so if we get here, all functions exist
        assert len(registry._indicators) > 0

    def test_missing_function_raises_error(self, tmp_path: Path):
        """Test that missing compute function raises error during catalog load."""
        bad_catalog = [
            {
                "name": "bad_indicator",
                "description": "Test",
                "compute_function_name": "nonexistent_compute_function",
                "data_requirements": {"cdx": "spread"},
                "default_securities": {"cdx": "cdx_ig_5y"},
                "output_units": "basis_points",
                "parameters": {},
                "enabled": True,
            }
        ]

        catalog_path = tmp_path / "bad_catalog.json"
        catalog_path.write_text(json.dumps(bad_catalog, indent=2))

        with pytest.raises(ValueError, match="references non-existent compute function"):
            IndicatorRegistry(catalog_path)

    def test_duplicate_names_raises_error(self, tmp_path: Path):
        """Test that duplicate indicator names raise error during catalog load."""
        duplicate_catalog = [
            {
                "name": "duplicate",
                "description": "First",
                "compute_function_name": "compute_spread_momentum",
                "data_requirements": {"cdx": "spread"},
                "default_securities": {"cdx": "cdx_ig_5y"},
                "output_units": "basis_points",
                "parameters": {"lookback": 5},
                "enabled": True,
            },
            {
                "name": "duplicate",
                "description": "Second",
                "compute_function_name": "compute_spread_momentum",
                "data_requirements": {"cdx": "spread"},
                "default_securities": {"cdx": "cdx_ig_5y"},
                "output_units": "basis_points",
                "parameters": {"lookback": 10},
                "enabled": True,
            },
        ]

        catalog_path = tmp_path / "duplicate_catalog.json"
        catalog_path.write_text(json.dumps(duplicate_catalog, indent=2))

        with pytest.raises(ValueError, match="Duplicate indicator"):
            IndicatorRegistry(catalog_path)

    def test_missing_catalog_file(self, tmp_path: Path):
        """Test error when catalog file doesn't exist."""
        nonexistent_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            IndicatorRegistry(nonexistent_path)

    def test_malformed_json(self, tmp_path: Path):
        """Test error when catalog JSON is malformed."""
        bad_json_path = tmp_path / "malformed.json"
        bad_json_path.write_text("{this is not valid json")

        with pytest.raises(json.JSONDecodeError):
            IndicatorRegistry(bad_json_path)

    def test_missing_required_fields(self, tmp_path: Path):
        """Test error when catalog entry is missing required fields."""
        incomplete_catalog = [
            {
                "name": "incomplete",
                # Missing compute_function_name
                "data_requirements": {"cdx": "spread"},
                "output_units": "basis_points",
                "parameters": {},
                "enabled": True,
            }
        ]

        catalog_path = tmp_path / "incomplete_catalog.json"
        catalog_path.write_text(json.dumps(incomplete_catalog, indent=2))

        with pytest.raises(ValueError, match="Invalid indicator metadata"):
            IndicatorRegistry(catalog_path)


class TestIndicatorMetadataProperties:
    """Tests for indicator metadata properties and validation."""

    def test_output_units_values(self):
        """Test that all indicators have valid output_units."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        valid_units = {"basis_points", "ratio", "percentage", "index_points"}

        for indicator_name in registry.get_all_indicators():
            metadata = registry.get_metadata(indicator_name)
            assert metadata.output_units in valid_units

    def test_data_requirements_structure(self):
        """Test that data_requirements are properly structured."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        for indicator_name in registry.get_all_indicators():
            metadata = registry.get_metadata(indicator_name)

            # Should be a dict
            assert isinstance(metadata.data_requirements, dict)

            # Should have at least one requirement
            assert len(metadata.data_requirements) > 0

            # Each requirement should have a column name
            for key, column in metadata.data_requirements.items():
                assert isinstance(key, str)
                assert isinstance(column, str)

    def test_default_securities_align_with_requirements(self):
        """Test that default_securities keys match data_requirements keys."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        for indicator_name in registry.get_all_indicators():
            metadata = registry.get_metadata(indicator_name)

            # default_securities keys should match data_requirements keys
            assert set(metadata.default_securities.keys()) == set(
                metadata.data_requirements.keys()
            )

    def test_parameters_structure(self):
        """Test that parameters are properly structured."""
        registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)

        for indicator_name in registry.get_all_indicators():
            metadata = registry.get_metadata(indicator_name)

            # Should be a dict
            assert isinstance(metadata.parameters, dict)

            # If parameters exist, they should have valid types
            for key, value in metadata.parameters.items():
                assert isinstance(key, str)
                # Common parameter types
                assert isinstance(value, (int, float, str, bool))


class TestDependencyTracking:
    """Tests for indicator-signal dependency tracking (User Story 3)."""

    def test_get_dependent_signals(self):
        """Test querying which signals depend on a specific indicator."""
        from aponyx.config import SIGNAL_CATALOG_PATH
        from aponyx.models.registry import SignalRegistry

        indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Build dependency index
        indicator_registry._build_dependency_index(signal_registry)

        # Check cdx_etf_spread_diff indicator
        # Should be used by cdx_etf_basis signal
        dependent_signals = indicator_registry.get_dependent_signals(
            "cdx_etf_spread_diff"
        )

        assert isinstance(dependent_signals, list)
        # At least one signal should depend on this indicator
        assert len(dependent_signals) > 0
        assert "cdx_etf_basis" in dependent_signals

    def test_get_all_dependencies(self):
        """Test retrieving complete dependency graph."""
        from aponyx.config import SIGNAL_CATALOG_PATH
        from aponyx.models.registry import SignalRegistry

        indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Build dependency index
        indicator_registry._build_dependency_index(signal_registry)

        # Get all dependencies
        all_deps = indicator_registry.get_all_dependencies()

        assert isinstance(all_deps, dict)

        # Should have dependencies for our pilot indicators
        assert len(all_deps) > 0

        # Each entry should be indicator_name -> list of signal names
        for indicator_name, signal_names in all_deps.items():
            assert isinstance(indicator_name, str)
            assert isinstance(signal_names, list)
            for signal_name in signal_names:
                assert isinstance(signal_name, str)

    def test_dependency_index_updates(self):
        """Test that dependency index correctly reflects catalog contents."""
        from aponyx.config import SIGNAL_CATALOG_PATH
        from aponyx.models.registry import SignalRegistry

        indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Build dependency index
        indicator_registry._build_dependency_index(signal_registry)

        # Verify each signal's dependencies are tracked
        for signal_name, signal_meta in signal_registry.list_all().items():
            if signal_meta.indicator_dependencies:
                for indicator_name in signal_meta.indicator_dependencies:
                    # This indicator should list the signal as dependent
                    dependent_signals = indicator_registry.get_dependent_signals(
                        indicator_name
                    )
                    assert (
                        signal_name in dependent_signals
                    ), f"Signal {signal_name} should be in dependencies for {indicator_name}"

    def test_nonexistent_indicator_returns_empty_list(self):
        """Test that querying dependencies for nonexistent indicator returns empty list."""
        from aponyx.config import SIGNAL_CATALOG_PATH
        from aponyx.models.registry import SignalRegistry

        indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Build dependency index
        indicator_registry._build_dependency_index(signal_registry)

        # Query nonexistent indicator
        dependent_signals = indicator_registry.get_dependent_signals(
            "nonexistent_indicator"
        )

        assert dependent_signals == []

    def test_indicator_with_no_dependencies(self):
        """Test indicators that are not used by any signals."""
        from aponyx.config import SIGNAL_CATALOG_PATH
        from aponyx.models.registry import SignalRegistry
        import json
        from pathlib import Path

        # Create temporary indicator catalog with unused indicator
        temp_indicator_catalog = [
            {
                "name": "unused_indicator",
                "description": "An indicator not used by any signal",
                "compute_function_name": "compute_spread_momentum",
                "data_requirements": {"cdx": "spread"},
                "default_securities": {"cdx": "cdx_ig_5y"},
                "output_units": "basis_points",
                "parameters": {"lookback": 5},
                "enabled": True,
            }
        ]

        temp_path = Path("temp_indicator_catalog.json")
        try:
            temp_path.write_text(json.dumps(temp_indicator_catalog, indent=2))

            indicator_registry = IndicatorRegistry(temp_path)
            signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

            # Build dependency index
            indicator_registry._build_dependency_index(signal_registry)

            # Unused indicator should have no dependencies
            dependent_signals = indicator_registry.get_dependent_signals(
                "unused_indicator"
            )
            assert dependent_signals == []

        finally:
            if temp_path.exists():
                temp_path.unlink()
