"""Tests for catalog entry dataclasses."""

import pytest

from aponyx.catalog.entries import (
    ChannelConfig,
    IndicatorTransformationEntry,
    InstrumentEntry,
    ScoreTransformationEntry,
    SecurityEntry,
    SignalEntry,
    SignalTransformationEntry,
    StrategyEntry,
)


class TestIndicatorTransformationEntry:
    """Tests for IndicatorTransformationEntry."""

    def test_valid_entry(self) -> None:
        """Test creating a valid entry."""
        entry = IndicatorTransformationEntry(
            name="test_indicator",
            description="Test description",
            compute_function_name="compute_test",
            data_requirements={"cdx": "spread"},
            default_securities={"cdx": "cdx_ig_5y"},
            output_units="basis_points",
        )
        assert entry.name == "test_indicator"
        assert entry.enabled is True

    def test_empty_name_raises(self) -> None:
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            IndicatorTransformationEntry(
                name="",
                description="",
                compute_function_name="compute_test",
                data_requirements={"cdx": "spread"},
                default_securities={"cdx": "cdx_ig_5y"},
                output_units="basis_points",
            )

    def test_empty_compute_function_raises(self) -> None:
        """Test that empty compute_function_name raises ValueError."""
        with pytest.raises(ValueError, match="compute_function_name cannot be empty"):
            IndicatorTransformationEntry(
                name="test",
                description="",
                compute_function_name="",
                data_requirements={"cdx": "spread"},
                default_securities={"cdx": "cdx_ig_5y"},
                output_units="basis_points",
            )

    def test_empty_data_requirements_raises(self) -> None:
        """Test that empty data_requirements raises ValueError."""
        with pytest.raises(ValueError, match="data_requirements cannot be empty"):
            IndicatorTransformationEntry(
                name="test",
                description="",
                compute_function_name="compute_test",
                data_requirements={},
                default_securities={"cdx": "cdx_ig_5y"},
                output_units="basis_points",
            )


class TestScoreTransformationEntry:
    """Tests for ScoreTransformationEntry."""

    def test_valid_entry(self) -> None:
        """Test creating a valid entry."""
        entry = ScoreTransformationEntry(
            name="z_score_20d",
            description="Z-score normalization",
            transform_type="z_score",
            parameters={"window": 20, "min_periods": 10},
        )
        assert entry.name == "z_score_20d"
        assert entry.transform_type == "z_score"

    def test_empty_transform_type_raises(self) -> None:
        """Test that empty transform_type raises ValueError."""
        with pytest.raises(ValueError, match="transform_type cannot be empty"):
            ScoreTransformationEntry(
                name="test",
                description="",
                transform_type="",
            )


class TestSignalTransformationEntry:
    """Tests for SignalTransformationEntry."""

    def test_valid_entry(self) -> None:
        """Test creating a valid entry."""
        entry = SignalTransformationEntry(
            name="bounded_1_5",
            description="Bounded signal",
            scaling=1.0,
            floor=-1.5,
            cap=1.5,
            neutral_range=(-0.25, 0.25),
        )
        assert entry.name == "bounded_1_5"
        assert entry.floor == -1.5
        assert entry.cap == 1.5

    def test_floor_exceeds_cap_raises(self) -> None:
        """Test that floor > cap raises ValueError."""
        with pytest.raises(ValueError, match="floor .* cannot exceed cap"):
            SignalTransformationEntry(
                name="test",
                description="",
                floor=2.0,
                cap=1.0,
            )

    def test_invalid_neutral_range_raises(self) -> None:
        """Test that invalid neutral_range raises ValueError."""
        with pytest.raises(ValueError, match="neutral_range\\[0\\] .* cannot exceed"):
            SignalTransformationEntry(
                name="test",
                description="",
                neutral_range=(0.5, -0.5),
            )


class TestSignalEntry:
    """Tests for SignalEntry."""

    def test_valid_entry(self) -> None:
        """Test creating a valid entry."""
        entry = SignalEntry(
            name="cdx_etf_basis",
            description="Test signal",
            indicator_transformation="cdx_etf_spread_diff",
            score_transformation="z_score_20d",
            signal_transformation="passthrough",
            sign_multiplier=1,
        )
        assert entry.name == "cdx_etf_basis"
        assert entry.sign_multiplier == 1

    def test_invalid_sign_multiplier_raises(self) -> None:
        """Test that invalid sign_multiplier raises ValueError."""
        with pytest.raises(ValueError, match="sign_multiplier must be 1 or -1"):
            SignalEntry(
                name="test",
                description="",
                indicator_transformation="ind",
                score_transformation="score",
                signal_transformation="sig",
                sign_multiplier=0,
            )

    def test_sign_multiplier_negative_one(self) -> None:
        """Test that -1 is a valid sign_multiplier."""
        entry = SignalEntry(
            name="test",
            description="",
            indicator_transformation="ind",
            score_transformation="score",
            signal_transformation="sig",
            sign_multiplier=-1,
        )
        assert entry.sign_multiplier == -1


class TestStrategyEntry:
    """Tests for StrategyEntry."""

    def test_valid_entry(self) -> None:
        """Test creating a valid entry."""
        entry = StrategyEntry(
            name="balanced",
            description="Balanced strategy",
            position_size_mm=10.0,
            sizing_mode="proportional",
            stop_loss_pct=5.0,
        )
        assert entry.name == "balanced"
        assert entry.sizing_mode == "proportional"

    def test_invalid_position_size_raises(self) -> None:
        """Test that non-positive position_size_mm raises ValueError."""
        with pytest.raises(ValueError, match="position_size_mm must be positive"):
            StrategyEntry(name="test", description="", position_size_mm=0)

    def test_invalid_sizing_mode_raises(self) -> None:
        """Test that invalid sizing_mode raises ValueError."""
        with pytest.raises(ValueError, match="sizing_mode must be"):
            StrategyEntry(name="test", description="", sizing_mode="invalid")

    def test_invalid_stop_loss_raises(self) -> None:
        """Test that invalid stop_loss_pct raises ValueError."""
        with pytest.raises(ValueError, match="stop_loss_pct must be in"):
            StrategyEntry(name="test", description="", stop_loss_pct=0)

        with pytest.raises(ValueError, match="stop_loss_pct must be in"):
            StrategyEntry(name="test", description="", stop_loss_pct=101)


class TestChannelConfig:
    """Tests for ChannelConfig."""

    def test_valid_entry(self) -> None:
        """Test creating a valid entry."""
        cfg = ChannelConfig(
            bloomberg_ticker="CDX IG CDSI GEN 5Y Corp",
            field="PX_LAST",
        )
        assert cfg.bloomberg_ticker == "CDX IG CDSI GEN 5Y Corp"

    def test_empty_ticker_raises(self) -> None:
        """Test that empty bloomberg_ticker raises ValueError."""
        with pytest.raises(ValueError, match="bloomberg_ticker cannot be empty"):
            ChannelConfig(bloomberg_ticker="", field="PX_LAST")


class TestSecurityEntry:
    """Tests for SecurityEntry."""

    def test_valid_entry(self) -> None:
        """Test creating a valid entry."""
        entry = SecurityEntry(
            name="cdx_ig_5y",
            description="CDX IG 5Y",
            instrument_type="cdx",
            quote_type="spread",
            channels={
                "spread": ChannelConfig(
                    bloomberg_ticker="CDX IG CDSI GEN 5Y Corp",
                    field="PX_LAST",
                )
            },
            dv01_per_million=475.0,
        )
        assert entry.name == "cdx_ig_5y"
        assert entry.instrument_type == "cdx"

    def test_empty_channels_raises(self) -> None:
        """Test that empty channels raises ValueError."""
        with pytest.raises(ValueError, match="channels cannot be empty"):
            SecurityEntry(
                name="test",
                description="",
                instrument_type="cdx",
                quote_type="spread",
                channels={},
            )


class TestInstrumentEntry:
    """Tests for InstrumentEntry."""

    def test_valid_entry(self) -> None:
        """Test creating a valid entry."""
        entry = InstrumentEntry(
            name="cdx",
            description="CDX indices",
            bloomberg_fields=("PX_LAST",),
            field_mapping={"PX_LAST": "spread"},
        )
        assert entry.name == "cdx"
        assert entry.bloomberg_fields == ("PX_LAST",)

    def test_empty_bloomberg_fields_raises(self) -> None:
        """Test that empty bloomberg_fields raises ValueError."""
        with pytest.raises(ValueError, match="bloomberg_fields cannot be empty"):
            InstrumentEntry(
                name="test",
                description="",
                bloomberg_fields=(),
                field_mapping={"PX_LAST": "spread"},
            )
