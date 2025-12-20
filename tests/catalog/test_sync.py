"""Tests for YAML to JSON sync."""

from pathlib import Path

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
from aponyx.catalog.sync import (
    generate_indicator_json,
    generate_instruments_json,
    generate_score_json,
    generate_securities_json,
    generate_signal_json,
    generate_signal_transformation_json,
    generate_strategy_json,
    sync_to_json,
)


@pytest.fixture
def sample_catalogs_data() -> CatalogsData:
    """Create sample catalogs data."""
    from ruamel.yaml import CommentedMap

    return CatalogsData(
        raw=CommentedMap(),
        indicator_transformations=[
            IndicatorTransformationEntry(
                name="cdx_etf_spread_diff",
                description="Test",
                compute_function_name="compute_cdx_etf_spread_diff",
                data_requirements={"cdx": "spread"},
                default_securities={"cdx": "cdx_ig_5y"},
                output_units="basis_points",
                parameters={"window": 20},
            ),
        ],
        score_transformations=[
            ScoreTransformationEntry(
                name="z_score_20d",
                description="Z-score",
                transform_type="z_score",
                parameters={"window": 20},
            ),
        ],
        signal_transformations=[
            SignalTransformationEntry(
                name="passthrough",
                description="No transform",
            ),
            SignalTransformationEntry(
                name="bounded",
                description="Bounded",
                floor=-1.5,
                cap=1.5,
                neutral_range=(-0.25, 0.25),
            ),
        ],
        signals=[
            SignalEntry(
                name="test_signal",
                description="Test",
                indicator_transformation="cdx_etf_spread_diff",
                score_transformation="z_score_20d",
                signal_transformation="passthrough",
            ),
        ],
        strategies=[
            StrategyEntry(
                name="balanced",
                description="Balanced",
                position_size_mm=10.0,
                stop_loss_pct=5.0,
            ),
        ],
    )


@pytest.fixture
def sample_securities_data() -> SecuritiesData:
    """Create sample securities data."""
    from ruamel.yaml import CommentedMap

    return SecuritiesData(
        raw=CommentedMap(),
        securities={
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
                dv01_per_million=475.0,
            ),
        },
        instruments={
            "cdx": InstrumentEntry(
                name="cdx",
                description="CDX",
                bloomberg_fields=("PX_LAST",),
                field_mapping={"PX_LAST": "spread"},
            ),
        },
    )


class TestGenerateIndicatorJson:
    """Tests for generate_indicator_json."""

    def test_generates_correct_structure(
        self, sample_catalogs_data: CatalogsData
    ) -> None:
        """Test that output has correct structure."""
        result = generate_indicator_json(sample_catalogs_data.indicator_transformations)
        assert len(result) == 1
        assert result[0]["name"] == "cdx_etf_spread_diff"
        assert result[0]["compute_function_name"] == "compute_cdx_etf_spread_diff"
        assert result[0]["parameters"] == {"window": 20}


class TestGenerateScoreJson:
    """Tests for generate_score_json."""

    def test_generates_correct_structure(
        self, sample_catalogs_data: CatalogsData
    ) -> None:
        """Test that output has correct structure."""
        result = generate_score_json(sample_catalogs_data.score_transformations)
        assert len(result) == 1
        assert result[0]["name"] == "z_score_20d"
        assert result[0]["transform_type"] == "z_score"


class TestGenerateSignalTransformationJson:
    """Tests for generate_signal_transformation_json."""

    def test_generates_correct_structure(
        self, sample_catalogs_data: CatalogsData
    ) -> None:
        """Test that output has correct structure."""
        result = generate_signal_transformation_json(
            sample_catalogs_data.signal_transformations
        )
        assert len(result) == 2
        assert result[0]["name"] == "passthrough"
        assert result[0]["neutral_range"] is None
        assert result[1]["name"] == "bounded"
        assert result[1]["neutral_range"] == [-0.25, 0.25]


class TestGenerateSignalJson:
    """Tests for generate_signal_json."""

    def test_generates_correct_structure(
        self, sample_catalogs_data: CatalogsData
    ) -> None:
        """Test that output has correct structure."""
        result = generate_signal_json(sample_catalogs_data.signals)
        assert len(result) == 1
        assert result[0]["name"] == "test_signal"
        assert result[0]["indicator_transformation"] == "cdx_etf_spread_diff"


class TestGenerateStrategyJson:
    """Tests for generate_strategy_json."""

    def test_generates_correct_structure(
        self, sample_catalogs_data: CatalogsData
    ) -> None:
        """Test that output has correct structure."""
        result = generate_strategy_json(sample_catalogs_data.strategies)
        assert len(result) == 1
        assert result[0]["name"] == "balanced"
        assert result[0]["position_size_mm"] == 10.0
        assert result[0]["stop_loss_pct"] == 5.0


class TestGenerateSecuritiesJson:
    """Tests for generate_securities_json."""

    def test_generates_correct_structure(
        self, sample_securities_data: SecuritiesData
    ) -> None:
        """Test that output has correct structure."""
        result = generate_securities_json(sample_securities_data.securities)
        assert "cdx_ig_5y" in result
        assert result["cdx_ig_5y"]["instrument_type"] == "cdx"
        assert "spread" in result["cdx_ig_5y"]["channels"]


class TestGenerateInstrumentsJson:
    """Tests for generate_instruments_json."""

    def test_generates_correct_structure(
        self, sample_securities_data: SecuritiesData
    ) -> None:
        """Test that output has correct structure."""
        result = generate_instruments_json(sample_securities_data.instruments)
        assert "cdx" in result
        assert result["cdx"]["bloomberg_fields"] == ["PX_LAST"]


class TestSyncToJson:
    """Tests for sync_to_json."""

    def test_sync_creates_files(
        self,
        sample_catalogs_data: CatalogsData,
        sample_securities_data: SecuritiesData,
        tmp_path: Path,
    ) -> None:
        """Test that sync creates all expected files."""
        result = sync_to_json(
            sample_catalogs_data,
            sample_securities_data,
            tmp_path,
            dry_run=False,
        )

        assert result.success
        assert len(result.files_written) == 7
        assert len(result.errors) == 0

        # Check files exist
        assert (tmp_path / "models" / "indicator_transformation.json").exists()
        assert (tmp_path / "models" / "signal_catalog.json").exists()
        assert (tmp_path / "backtest" / "strategy_catalog.json").exists()
        assert (tmp_path / "data" / "bloomberg_securities.json").exists()

    def test_dry_run_does_not_create_files(
        self,
        sample_catalogs_data: CatalogsData,
        sample_securities_data: SecuritiesData,
        tmp_path: Path,
    ) -> None:
        """Test that dry_run doesn't create files."""
        result = sync_to_json(
            sample_catalogs_data,
            sample_securities_data,
            tmp_path,
            dry_run=True,
        )

        assert result.success
        assert result.dry_run
        assert len(result.files_written) == 7  # Would write 7 files
        assert not (tmp_path / "models" / "indicator_transformation.json").exists()

    def test_unchanged_files_not_rewritten(
        self,
        sample_catalogs_data: CatalogsData,
        sample_securities_data: SecuritiesData,
        tmp_path: Path,
    ) -> None:
        """Test that unchanged files are detected."""
        # First sync
        result1 = sync_to_json(
            sample_catalogs_data,
            sample_securities_data,
            tmp_path,
            dry_run=False,
        )
        assert len(result1.files_written) == 7

        # Second sync (no changes)
        result2 = sync_to_json(
            sample_catalogs_data,
            sample_securities_data,
            tmp_path,
            dry_run=False,
        )
        assert len(result2.files_written) == 0
        assert len(result2.files_unchanged) == 7
