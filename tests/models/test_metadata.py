"""
Tests for SignalMetadata dataclass.

Validates metadata structure, validation logic, and field constraints.
"""

import pytest

from aponyx.models.metadata import SignalMetadata


class TestSignalMetadataCreation:
    """Test SignalMetadata creation and initialization."""

    def test_signal_metadata_basic_creation(self):
        """Test creating basic SignalMetadata instance."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test signal description",
            compute_function_name="compute_test_signal",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            enabled=True,
            sign_multiplier=1,
        )

        assert metadata.name == "test_signal"
        assert metadata.description == "Test signal description"
        assert metadata.compute_function_name == "compute_test_signal"
        assert metadata.data_requirements == {"cdx": "spread"}
        assert metadata.arg_mapping == ["cdx"]
        assert metadata.enabled is True
        assert metadata.sign_multiplier == 1

    def test_signal_metadata_defaults(self):
        """Test SignalMetadata default values."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test description",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )

        # Defaults
        assert metadata.enabled is True
        assert metadata.sign_multiplier == 1

    def test_signal_metadata_frozen(self):
        """Test SignalMetadata is frozen (immutable)."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test description",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )

        with pytest.raises(AttributeError):
            metadata.name = "new_name"  # type: ignore


class TestSignalMetadataValidation:
    """Test SignalMetadata validation logic."""

    def test_signal_metadata_empty_name_error(self):
        """Test error when name is empty."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            SignalMetadata(
                name="",
                description="Test",
                compute_function_name="compute_test",
                data_requirements={"cdx": "spread"},
                arg_mapping=["cdx"],
            )

    def test_signal_metadata_empty_function_name_error(self):
        """Test error when compute function name is empty."""
        with pytest.raises(ValueError, match="function name cannot be empty"):
            SignalMetadata(
                name="test_signal",
                description="Test",
                compute_function_name="",
                data_requirements={"cdx": "spread"},
                arg_mapping=["cdx"],
            )

    def test_signal_metadata_empty_arg_mapping_error(self):
        """Test error when arg_mapping is empty."""
        with pytest.raises(ValueError, match="arg_mapping cannot be empty"):
            SignalMetadata(
                name="test_signal",
                description="Test",
                compute_function_name="compute_test",
                data_requirements={"cdx": "spread"},
                arg_mapping=[],
            )

    def test_signal_metadata_arg_mapping_mismatch_error(self):
        """Test error when arg_mapping doesn't match data_requirements."""
        with pytest.raises(ValueError, match="must contain exactly the same keys"):
            SignalMetadata(
                name="test_signal",
                description="Test",
                compute_function_name="compute_test",
                data_requirements={"cdx": "spread", "etf": "spread"},
                arg_mapping=["cdx"],  # Missing "etf"
            )

    def test_signal_metadata_extra_arg_mapping_error(self):
        """Test error when arg_mapping has extra keys."""
        with pytest.raises(ValueError, match="must contain exactly the same keys"):
            SignalMetadata(
                name="test_signal",
                description="Test",
                compute_function_name="compute_test",
                data_requirements={"cdx": "spread"},
                arg_mapping=["cdx", "etf"],  # Extra "etf"
            )

    def test_signal_metadata_invalid_sign_multiplier_error(self):
        """Test error when sign_multiplier is not ±1."""
        with pytest.raises(ValueError, match="must be -1 or 1"):
            SignalMetadata(
                name="test_signal",
                description="Test",
                compute_function_name="compute_test",
                data_requirements={"cdx": "spread"},
                arg_mapping=["cdx"],
                sign_multiplier=2,  # Invalid
            )

    def test_signal_metadata_zero_sign_multiplier_error(self):
        """Test error when sign_multiplier is zero."""
        with pytest.raises(ValueError, match="must be -1 or 1"):
            SignalMetadata(
                name="test_signal",
                description="Test",
                compute_function_name="compute_test",
                data_requirements={"cdx": "spread"},
                arg_mapping=["cdx"],
                sign_multiplier=0,
            )


class TestSignalMetadataWithMultipleDataSources:
    """Test SignalMetadata with multiple data requirements."""

    def test_signal_metadata_two_data_sources(self):
        """Test metadata with two data sources."""
        metadata = SignalMetadata(
            name="basis_signal",
            description="Basis between CDX and ETF",
            compute_function_name="compute_cdx_etf_basis",
            data_requirements={"cdx": "spread", "etf": "spread"},
            arg_mapping=["cdx", "etf"],
        )

        assert len(metadata.data_requirements) == 2
        assert len(metadata.arg_mapping) == 2
        assert "cdx" in metadata.data_requirements
        assert "etf" in metadata.data_requirements

    def test_signal_metadata_three_data_sources(self):
        """Test metadata with three data sources."""
        metadata = SignalMetadata(
            name="complex_signal",
            description="Signal using multiple data sources",
            compute_function_name="compute_complex",
            data_requirements={
                "cdx": "spread",
                "etf": "spread",
                "vix": "level",
            },
            arg_mapping=["cdx", "etf", "vix"],
        )

        assert len(metadata.data_requirements) == 3
        assert len(metadata.arg_mapping) == 3

    def test_signal_metadata_arg_order_preserved(self):
        """Test arg_mapping order is preserved."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"a": "col1", "b": "col2", "c": "col3"},
            arg_mapping=["c", "a", "b"],  # Different order
        )

        # Order should be preserved as specified
        assert metadata.arg_mapping == ["c", "a", "b"]


class TestSignalMetadataSignMultiplier:
    """Test sign multiplier functionality."""

    def test_signal_metadata_positive_multiplier(self):
        """Test metadata with positive sign multiplier."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            sign_multiplier=1,
        )

        assert metadata.sign_multiplier == 1

    def test_signal_metadata_negative_multiplier(self):
        """Test metadata with negative sign multiplier."""
        metadata = SignalMetadata(
            name="inverted_signal",
            description="Inverted signal",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            sign_multiplier=-1,
        )

        assert metadata.sign_multiplier == -1


class TestSignalMetadataEquality:
    """Test SignalMetadata equality comparison."""

    def test_signal_metadata_equality(self):
        """Test identical metadata instances are equal."""
        metadata1 = SignalMetadata(
            name="test_signal",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )

        metadata2 = SignalMetadata(
            name="test_signal",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )

        assert metadata1 == metadata2

    def test_signal_metadata_inequality_name(self):
        """Test metadata with different names are not equal."""
        metadata1 = SignalMetadata(
            name="signal1",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )

        metadata2 = SignalMetadata(
            name="signal2",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )

        assert metadata1 != metadata2

    def test_signal_metadata_inequality_multiplier(self):
        """Test metadata with different sign multipliers are not equal."""
        metadata1 = SignalMetadata(
            name="test_signal",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            sign_multiplier=1,
        )

        metadata2 = SignalMetadata(
            name="test_signal",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            sign_multiplier=-1,
        )

        assert metadata1 != metadata2


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_signal_metadata_with_unicode_description(self):
        """Test metadata with Unicode characters in description."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Signal using μ (mu) and σ (sigma) calculations",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
        )

        assert "μ" in metadata.description
        assert "σ" in metadata.description

    def test_signal_metadata_with_complex_data_requirements(self):
        """Test metadata with different column names per source."""
        metadata = SignalMetadata(
            name="test_signal",
            description="Test",
            compute_function_name="compute_test",
            data_requirements={
                "cdx": "spread",
                "vix": "level",
                "etf": "price",
            },
            arg_mapping=["cdx", "vix", "etf"],
        )

        # Each source can require different column
        assert metadata.data_requirements["cdx"] == "spread"
        assert metadata.data_requirements["vix"] == "level"
        assert metadata.data_requirements["etf"] == "price"

    def test_signal_metadata_disabled_signal(self):
        """Test metadata for disabled signal."""
        metadata = SignalMetadata(
            name="disabled_signal",
            description="Disabled signal",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            arg_mapping=["cdx"],
            enabled=False,
        )

        assert metadata.enabled is False
