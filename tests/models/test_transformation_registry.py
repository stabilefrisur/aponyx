"""
Tests for TransformationRegistry.

Validates:
- Catalog loading and validation
- Metadata retrieval
- Transform type validation
- Parameter validation for different transform types
- Error handling for invalid catalog entries
"""

import json

import pytest

from aponyx.models.metadata import TransformationMetadata
from aponyx.models.registry import TransformationRegistry


@pytest.fixture
def temp_catalog(tmp_path):
    """Create temporary transformation catalog."""
    catalog_path = tmp_path / "transformation_catalog.json"

    catalog_data = [
        {
            "name": "z_score_20d",
            "description": "Z-score normalization over 20-day window",
            "transform_type": "z_score",
            "parameters": {"window": 20, "min_periods": 10},
            "enabled": True,
        },
        {
            "name": "diff_5d",
            "description": "5-day first difference",
            "transform_type": "diff",
            "parameters": {"periods": 5},
            "enabled": True,
        },
        {
            "name": "volatility_adjust_20d",
            "description": "Change normalized by 20-day volatility",
            "transform_type": "normalized_change",
            "parameters": {"window": 20, "min_periods": 10, "periods": 1},
            "enabled": True,
        },
    ]

    catalog_path.write_text(json.dumps(catalog_data, indent=2))
    return catalog_path


class TestTransformationRegistryLoading:
    """Test catalog loading and validation."""

    def test_load_valid_catalog(self, temp_catalog):
        """Test loading valid transformation catalog."""
        registry = TransformationRegistry(temp_catalog)

        # Validate all transformations loaded
        assert registry.transformation_exists("z_score_20d")
        assert registry.transformation_exists("diff_5d")
        assert registry.transformation_exists("volatility_adjust_20d")

        # Validate enabled transformations
        enabled = registry.get_enabled()
        assert len(enabled) == 3
        assert "z_score_20d" in enabled
        assert "diff_5d" in enabled
        assert "volatility_adjust_20d" in enabled

    def test_get_metadata(self, temp_catalog):
        """Test retrieving transformation metadata."""
        registry = TransformationRegistry(temp_catalog)

        # Get z_score metadata
        metadata = registry.get_metadata("z_score_20d")
        assert isinstance(metadata, TransformationMetadata)
        assert metadata.name == "z_score_20d"
        assert metadata.transform_type == "z_score"
        assert metadata.parameters == {"window": 20, "min_periods": 10}
        assert metadata.enabled is True

        # Get diff metadata
        metadata = registry.get_metadata("diff_5d")
        assert metadata.name == "diff_5d"
        assert metadata.transform_type == "diff"
        assert metadata.parameters == {"periods": 5}

    def test_get_nonexistent_transformation(self, temp_catalog):
        """Test error when requesting nonexistent transformation."""
        registry = TransformationRegistry(temp_catalog)

        with pytest.raises(KeyError, match="Transformation.*not found in registry"):
            registry.get_metadata("nonexistent_transform")

    def test_disabled_transformation_excluded(self, tmp_path):
        """Test that disabled transformations are excluded from enabled list."""
        catalog_path = tmp_path / "catalog.json"
        catalog_data = [
            {
                "name": "enabled_transform",
                "description": "Enabled transformation",
                "transform_type": "z_score",
                "parameters": {"window": 20, "min_periods": 10},
                "enabled": True,
            },
            {
                "name": "disabled_transform",
                "description": "Disabled transformation",
                "transform_type": "diff",
                "parameters": {"periods": 5},
                "enabled": False,
            },
        ]
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        registry = TransformationRegistry(catalog_path)

        # Both should exist
        assert registry.transformation_exists("enabled_transform")
        assert registry.transformation_exists("disabled_transform")

        # Only enabled in get_enabled()
        enabled = registry.get_enabled()
        assert len(enabled) == 1
        assert "enabled_transform" in enabled
        assert "disabled_transform" not in enabled


class TestTransformationRegistryValidation:
    """Test catalog validation rules."""

    def test_invalid_transform_type(self, tmp_path):
        """Test error on invalid transform_type."""
        catalog_path = tmp_path / "catalog.json"
        catalog_data = [
            {
                "name": "invalid_transform",
                "description": "Invalid transformation type",
                "transform_type": "invalid_type",  # Not in TransformType
                "parameters": {},
                "enabled": True,
            }
        ]
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        with pytest.raises(ValueError, match="Invalid transform_type"):
            TransformationRegistry(catalog_path)

    def test_z_score_missing_window(self, tmp_path):
        """Test error when z_score lacks window parameter."""
        catalog_path = tmp_path / "catalog.json"
        catalog_data = [
            {
                "name": "bad_z_score",
                "description": "Z-score without window",
                "transform_type": "z_score",
                "parameters": {},  # Missing window!
                "enabled": True,
            }
        ]
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        with pytest.raises(ValueError, match="requires 'window' parameter"):
            TransformationRegistry(catalog_path)

    def test_normalized_change_missing_window(self, tmp_path):
        """Test error when normalized_change lacks window parameter."""
        catalog_path = tmp_path / "catalog.json"
        catalog_data = [
            {
                "name": "bad_normalized_change",
                "description": "Normalized change without window",
                "transform_type": "normalized_change",
                "parameters": {"periods": 1},  # Missing window!
                "enabled": True,
            }
        ]
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        with pytest.raises(ValueError, match="requires 'window' parameter"):
            TransformationRegistry(catalog_path)

    def test_duplicate_transformation_names(self, tmp_path):
        """Test error on duplicate transformation names."""
        catalog_path = tmp_path / "catalog.json"
        catalog_data = [
            {
                "name": "duplicate_name",
                "description": "First transformation",
                "transform_type": "z_score",
                "parameters": {"window": 20, "min_periods": 10},
                "enabled": True,
            },
            {
                "name": "duplicate_name",  # Duplicate!
                "description": "Second transformation",
                "transform_type": "diff",
                "parameters": {"periods": 5},
                "enabled": True,
            },
        ]
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        with pytest.raises(ValueError, match="Duplicate transformation name"):
            TransformationRegistry(catalog_path)

    def test_invalid_transformation_name(self, tmp_path):
        """Test error on invalid transformation name (uppercase, spaces)."""
        catalog_path = tmp_path / "catalog.json"
        catalog_data = [
            {
                "name": "Invalid Name",  # Has space and uppercase!
                "description": "Invalid name",
                "transform_type": "diff",
                "parameters": {"periods": 5},
                "enabled": True,
            }
        ]
        catalog_path.write_text(json.dumps(catalog_data, indent=2))

        with pytest.raises(ValueError, match="Transformation name must be lowercase"):
            TransformationRegistry(catalog_path)

    def test_empty_catalog(self, tmp_path):
        """Test handling of empty catalog."""
        catalog_path = tmp_path / "catalog.json"
        catalog_path.write_text("[]")

        registry = TransformationRegistry(catalog_path)

        # Should work but have no transformations
        enabled = registry.get_enabled()
        assert len(enabled) == 0

    def test_missing_catalog_file(self, tmp_path):
        """Test error when catalog file doesn't exist."""
        nonexistent_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            TransformationRegistry(nonexistent_path)


class TestTransformationMetadata:
    """Test TransformationMetadata validation."""

    def test_valid_z_score_metadata(self):
        """Test valid z_score transformation metadata."""
        metadata = TransformationMetadata(
            name="z_score_20d",
            description="Z-score over 20 days",
            transform_type="z_score",
            parameters={"window": 20, "min_periods": 10},
            enabled=True,
        )

        assert metadata.name == "z_score_20d"
        assert metadata.transform_type == "z_score"
        assert metadata.parameters["window"] == 20

    def test_valid_diff_metadata(self):
        """Test valid diff transformation metadata."""
        metadata = TransformationMetadata(
            name="diff_5d",
            description="5-day difference",
            transform_type="diff",
            parameters={"periods": 5},
            enabled=True,
        )

        assert metadata.name == "diff_5d"
        assert metadata.transform_type == "diff"

    def test_invalid_name_with_uppercase(self):
        """Test validation rejects uppercase in name."""
        with pytest.raises(ValueError, match="Transformation name must be lowercase"):
            TransformationMetadata(
                name="Invalid_Name",  # Uppercase!
                description="Invalid",
                transform_type="diff",
                parameters={"periods": 5},
                enabled=True,
            )

    def test_invalid_name_with_space(self):
        """Test validation rejects space in name."""
        with pytest.raises(ValueError, match="Transformation name must be lowercase"):
            TransformationMetadata(
                name="invalid name",  # Space!
                description="Invalid",
                transform_type="diff",
                parameters={"periods": 5},
                enabled=True,
            )

    def test_z_score_without_window(self):
        """Test validation rejects z_score without window."""
        with pytest.raises(ValueError, match="requires 'window' parameter"):
            TransformationMetadata(
                name="bad_z_score",
                description="Bad z-score",
                transform_type="z_score",
                parameters={},  # Missing window!
                enabled=True,
            )

    def test_normalized_change_without_window(self):
        """Test validation rejects normalized_change without window."""
        with pytest.raises(ValueError, match="requires 'window' parameter"):
            TransformationMetadata(
                name="bad_normalized",
                description="Bad normalized change",
                transform_type="normalized_change",
                parameters={"periods": 1},  # Missing window!
                enabled=True,
            )
