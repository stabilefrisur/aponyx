"""Tests for catalog validation."""

import pytest

from aponyx.catalog.data import CatalogsData, SecuritiesData
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
from aponyx.catalog.validator import (
    check_duplicates,
    validate_catalogs,
    validate_field_constraints,
    validate_indicator_securities,
    validate_signal_references,
)


@pytest.fixture
def valid_indicator_transformations() -> list[IndicatorTransformationEntry]:
    """Create valid indicator transformations."""
    return [
        IndicatorTransformationEntry(
            name="cdx_etf_spread_diff",
            description="Test",
            compute_function_name="compute_cdx_etf_spread_diff",
            data_requirements={"cdx": "spread", "etf": "spread"},
            default_securities={"cdx": "cdx_ig_5y", "etf": "lqd"},
            output_units="basis_points",
        ),
    ]


@pytest.fixture
def valid_score_transformations() -> list[ScoreTransformationEntry]:
    """Create valid score transformations."""
    return [
        ScoreTransformationEntry(
            name="z_score_20d",
            description="Z-score",
            transform_type="z_score",
            parameters={"window": 20},
        ),
    ]


@pytest.fixture
def valid_signal_transformations() -> list[SignalTransformationEntry]:
    """Create valid signal transformations."""
    return [
        SignalTransformationEntry(
            name="passthrough",
            description="No transform",
        ),
    ]


@pytest.fixture
def valid_signals(
    valid_indicator_transformations: list[IndicatorTransformationEntry],
    valid_score_transformations: list[ScoreTransformationEntry],
    valid_signal_transformations: list[SignalTransformationEntry],
) -> list[SignalEntry]:
    """Create valid signals."""
    return [
        SignalEntry(
            name="cdx_etf_basis",
            description="Test signal",
            indicator_transformation="cdx_etf_spread_diff",
            score_transformation="z_score_20d",
            signal_transformation="passthrough",
        ),
    ]


@pytest.fixture
def valid_strategies() -> list[StrategyEntry]:
    """Create valid strategies."""
    return [
        StrategyEntry(
            name="balanced",
            description="Balanced",
            position_size_mm=10.0,
            sizing_mode="proportional",
        ),
    ]


@pytest.fixture
def valid_securities() -> dict[str, SecurityEntry]:
    """Create valid securities."""
    return {
        "cdx_ig_5y": SecurityEntry(
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
        ),
        "lqd": SecurityEntry(
            name="lqd",
            description="LQD ETF",
            instrument_type="etf",
            quote_type="price",
            channels={
                "price": ChannelConfig(
                    bloomberg_ticker="LQD US Equity",
                    field="PX_LAST",
                )
            },
        ),
    }


@pytest.fixture
def valid_instruments() -> dict[str, InstrumentEntry]:
    """Create valid instruments."""
    return {
        "cdx": InstrumentEntry(
            name="cdx",
            description="CDX indices",
            bloomberg_fields=("PX_LAST",),
            field_mapping={"PX_LAST": "spread"},
        ),
    }


class TestCheckDuplicates:
    """Tests for check_duplicates."""

    def test_no_duplicates(self) -> None:
        """Test with no duplicates."""
        entries = [
            SignalEntry(
                name="signal1",
                description="",
                indicator_transformation="ind",
                score_transformation="score",
                signal_transformation="sig",
            ),
            SignalEntry(
                name="signal2",
                description="",
                indicator_transformation="ind",
                score_transformation="score",
                signal_transformation="sig",
            ),
        ]
        errors = check_duplicates(entries, "signals")
        assert len(errors) == 0

    def test_with_duplicates(self) -> None:
        """Test with duplicate names."""
        entries = [
            SignalEntry(
                name="signal1",
                description="",
                indicator_transformation="ind",
                score_transformation="score",
                signal_transformation="sig",
            ),
            SignalEntry(
                name="signal1",  # Duplicate
                description="",
                indicator_transformation="ind",
                score_transformation="score",
                signal_transformation="sig",
            ),
        ]
        errors = check_duplicates(entries, "signals")
        assert len(errors) == 1
        assert "Duplicate name" in errors[0].message


class TestValidateSignalReferences:
    """Tests for validate_signal_references."""

    def test_valid_references(
        self,
        valid_signals: list[SignalEntry],
        valid_indicator_transformations: list[IndicatorTransformationEntry],
        valid_score_transformations: list[ScoreTransformationEntry],
        valid_signal_transformations: list[SignalTransformationEntry],
    ) -> None:
        """Test with all valid references."""
        errors = validate_signal_references(
            valid_signals,
            valid_indicator_transformations,
            valid_score_transformations,
            valid_signal_transformations,
        )
        assert len(errors) == 0

    def test_invalid_indicator_reference(
        self,
        valid_score_transformations: list[ScoreTransformationEntry],
        valid_signal_transformations: list[SignalTransformationEntry],
    ) -> None:
        """Test with invalid indicator_transformation reference."""
        signals = [
            SignalEntry(
                name="bad_signal",
                description="",
                indicator_transformation="nonexistent",
                score_transformation="z_score_20d",
                signal_transformation="passthrough",
            ),
        ]
        errors = validate_signal_references(
            signals,
            [],  # Empty indicator list
            valid_score_transformations,
            valid_signal_transformations,
        )
        assert len(errors) == 1
        assert "indicator_transformation" in errors[0].field
        assert "nonexistent" in errors[0].message


class TestValidateIndicatorSecurities:
    """Tests for validate_indicator_securities."""

    def test_valid_securities(
        self,
        valid_indicator_transformations: list[IndicatorTransformationEntry],
        valid_securities: dict[str, SecurityEntry],
    ) -> None:
        """Test with valid security references."""
        warnings = validate_indicator_securities(
            valid_indicator_transformations,
            valid_securities,
        )
        assert len(warnings) == 0

    def test_missing_security(
        self,
        valid_indicator_transformations: list[IndicatorTransformationEntry],
    ) -> None:
        """Test with missing security reference."""
        warnings = validate_indicator_securities(
            valid_indicator_transformations,
            {},  # Empty securities
        )
        assert len(warnings) == 2  # cdx and etf both missing


class TestValidateFieldConstraints:
    """Tests for validate_field_constraints."""

    def test_valid_constraints(
        self,
        valid_signals: list[SignalEntry],
        valid_strategies: list[StrategyEntry],
        valid_signal_transformations: list[SignalTransformationEntry],
    ) -> None:
        """Test with valid constraints."""
        errors = validate_field_constraints(
            valid_signals,
            valid_strategies,
            valid_signal_transformations,
        )
        assert len(errors) == 0


class TestValidateCatalogs:
    """Tests for validate_catalogs."""

    def test_valid_catalogs(
        self,
        valid_indicator_transformations: list[IndicatorTransformationEntry],
        valid_score_transformations: list[ScoreTransformationEntry],
        valid_signal_transformations: list[SignalTransformationEntry],
        valid_signals: list[SignalEntry],
        valid_strategies: list[StrategyEntry],
        valid_securities: dict[str, SecurityEntry],
        valid_instruments: dict[str, InstrumentEntry],
    ) -> None:
        """Test with all valid data."""
        from ruamel.yaml import CommentedMap

        catalogs = CatalogsData(
            raw=CommentedMap(),
            indicator_transformations=valid_indicator_transformations,
            score_transformations=valid_score_transformations,
            signal_transformations=valid_signal_transformations,
            signals=valid_signals,
            strategies=valid_strategies,
        )

        securities = SecuritiesData(
            raw=CommentedMap(),
            securities=valid_securities,
            instruments=valid_instruments,
        )

        result = validate_catalogs(catalogs, securities)
        assert result.passed
        assert len(result.errors) == 0
        assert result.summary is not None
        assert result.summary.total_entries > 0

    def test_invalid_signal_reference(
        self,
        valid_indicator_transformations: list[IndicatorTransformationEntry],
        valid_score_transformations: list[ScoreTransformationEntry],
        valid_signal_transformations: list[SignalTransformationEntry],
        valid_strategies: list[StrategyEntry],
        valid_securities: dict[str, SecurityEntry],
        valid_instruments: dict[str, InstrumentEntry],
    ) -> None:
        """Test with invalid signal reference."""
        from ruamel.yaml import CommentedMap

        bad_signals = [
            SignalEntry(
                name="bad_signal",
                description="",
                indicator_transformation="nonexistent",
                score_transformation="z_score_20d",
                signal_transformation="passthrough",
            ),
        ]

        catalogs = CatalogsData(
            raw=CommentedMap(),
            indicator_transformations=valid_indicator_transformations,
            score_transformations=valid_score_transformations,
            signal_transformations=valid_signal_transformations,
            signals=bad_signals,
            strategies=valid_strategies,
        )

        securities = SecuritiesData(
            raw=CommentedMap(),
            securities=valid_securities,
            instruments=valid_instruments,
        )

        result = validate_catalogs(catalogs, securities)
        assert not result.passed
        assert len(result.errors) == 1
