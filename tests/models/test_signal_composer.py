"""
Tests for signal composition functions.

Validates:
- Score transformation application (z-score, normalized_change, diff)
- Signal transformation application (floor, cap, neutral_range, scaling)
- Four-stage pipeline composition (indicator → score → signal → position)
- Stage-specific inspection functions
- Runtime overrides for all transformation stages
- Sign multiplier application
- Error handling for invalid configurations
"""

import numpy as np
import pandas as pd
import pytest

from aponyx.models.signal_composer import (
    apply_score_transformation,
    compose_signal,
    compute_indicator_stage,
    compute_score_stage,
    compute_signal_stage,
)
from aponyx.data.transforms import apply_signal_transformation


class TestApplyScoreTransformation:
    """Test score transformation application to indicator series."""

    def test_z_score_transformation(self):
        """Test z-score normalization of indicator."""
        # Create indicator series
        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        values = np.random.randn(50) * 10 + 100  # Mean ~100, std ~10
        indicator = pd.Series(values, index=dates, name="spread_diff")

        # Z-score transformation metadata
        transformation_metadata = {
            "name": "z_score_20d",
            "transform_type": "z_score",
            "parameters": {"window": 20, "min_periods": 10},
        }

        # Apply transformation
        score = apply_score_transformation(indicator, transformation_metadata)

        # Validate
        assert isinstance(score, pd.Series)
        assert len(score) == len(indicator)

        # Check z-score properties (after warmup)
        valid_score = score.dropna()
        assert len(valid_score) > 0
        # Z-scores should have roughly zero mean and unit variance
        assert abs(valid_score.mean()) < 0.5
        assert abs(valid_score.std() - 1.0) < 0.5

    def test_diff_transformation(self):
        """Test first difference transformation."""
        # Create indicator series
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        values = np.arange(20) * 5  # Linear trend: 0, 5, 10, 15, ...
        indicator = pd.Series(values, index=dates, name="spread")

        # Diff transformation metadata
        transformation_metadata = {
            "name": "diff_5d",
            "transform_type": "diff",
            "parameters": {"periods": 5},
        }

        # Apply transformation
        score = apply_score_transformation(indicator, transformation_metadata)

        # Validate
        assert isinstance(score, pd.Series)
        assert len(score) == len(indicator)

        # Check diff properties
        valid_score = score.dropna()
        # 5-day diff of linear trend should be constant 25 (5 periods * 5 per period)
        assert np.allclose(valid_score, 25.0)

    def test_volatility_adjust_transformation(self):
        """Test normalized change (volatility-adjusted) transformation."""
        # Create indicator series
        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        values = np.random.randn(50) * 10 + 100
        indicator = pd.Series(values, index=dates, name="momentum")

        # Volatility adjust transformation metadata
        transformation_metadata = {
            "name": "volatility_adjust_20d",
            "transform_type": "normalized_change",
            "parameters": {"window": 20, "min_periods": 10, "periods": 1},
        }

        # Apply transformation
        score = apply_score_transformation(indicator, transformation_metadata)

        # Validate
        assert isinstance(score, pd.Series)
        assert len(score) == len(indicator)

        # Check that values are normalized (finite, not too extreme)
        valid_score = score.dropna()
        assert len(valid_score) > 0
        assert np.all(np.isfinite(valid_score))


class TestApplySignalTransformation:
    """Test signal transformation application (floor, cap, neutral_range, scaling)."""

    def test_passthrough_transformation(self):
        """Test passthrough (no transformation)."""
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        score = pd.Series(np.linspace(-2.0, 2.0, 20), index=dates, name="score")

        # Passthrough: no bounds, no scaling
        signal = apply_signal_transformation(
            score,
            scaling=1.0,
            floor=None,
            cap=None,
            neutral_range=None,
        )

        # Should be identical to input
        pd.testing.assert_series_equal(signal, score)

    def test_bounded_transformation(self):
        """Test floor and cap application."""
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        score = pd.Series(np.linspace(-3.0, 3.0, 20), index=dates, name="score")

        # Bound to [-1.5, 1.5]
        signal = apply_signal_transformation(
            score,
            scaling=1.0,
            floor=-1.5,
            cap=1.5,
            neutral_range=None,
        )

        # Check bounds
        assert signal.min() == -1.5
        assert signal.max() == 1.5

    def test_neutral_range_transformation(self):
        """Test neutral range application."""
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        score = pd.Series(np.linspace(-1.0, 1.0, 20), index=dates, name="score")

        # Neutral range: [-0.25, 0.25] → 0.0
        signal = apply_signal_transformation(
            score,
            scaling=1.0,
            floor=None,
            cap=None,
            neutral_range=(-0.25, 0.25),
        )

        # Check that values in neutral range are zero
        neutral_values = score[(score >= -0.25) & (score <= 0.25)]
        for idx in neutral_values.index:
            assert signal.loc[idx] == 0.0

        # Check that values outside neutral range are preserved
        active_values = score[(score < -0.25) | (score > 0.25)]
        for idx in active_values.index:
            assert signal.loc[idx] == score.loc[idx]

    def test_scaling_transformation(self):
        """Test scaling application."""
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        score = pd.Series(np.linspace(-1.0, 1.0, 20), index=dates, name="score")

        # Scale by 2.0
        signal = apply_signal_transformation(
            score,
            scaling=2.0,
            floor=None,
            cap=None,
            neutral_range=None,
        )

        # Should be 2x input
        pd.testing.assert_series_equal(signal, score * 2.0)

    def test_combined_transformation(self):
        """Test scaling + floor/cap + neutral range."""
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        score = pd.Series(np.linspace(-2.0, 2.0, 20), index=dates, name="score")

        # Scale by 1.5, bound to [-2.0, 2.0], neutral [-0.5, 0.5]
        signal = apply_signal_transformation(
            score,
            scaling=1.5,
            floor=-2.0,
            cap=2.0,
            neutral_range=(-0.5, 0.5),
        )

        # Check bounds
        assert signal.min() >= -2.0
        assert signal.max() <= 2.0

        # Check neutral range after scaling
        # Original score in [-0.33, 0.33] → scaled to [-0.5, 0.5] → set to 0
        neutral_after_scaling = score[(score * 1.5 >= -0.5) & (score * 1.5 <= 0.5)]
        for idx in neutral_after_scaling.index:
            assert signal.loc[idx] == 0.0


class TestComposeSignal:
    """Test signal composition via four-stage pipeline."""

    @pytest.fixture
    def mock_indicator_registry(self):
        """Mock indicator transformation registry."""

        class MockIndicatorMetadata:
            def __init__(self, name, data_reqs, default_secs, params, output_units):
                self.name = name
                self.data_requirements = data_reqs
                self.default_securities = default_secs
                self.parameters = params
                self.output_units = output_units

        class MockRegistry:
            def get_metadata(self, name):
                if name == "cdx_etf_spread_diff":
                    return MockIndicatorMetadata(
                        "cdx_etf_spread_diff",
                        {"cdx": "spread", "etf": "spread"},
                        {"cdx": "cdx_ig_5y", "etf": "lqd"},
                        {},
                        "basis_points",
                    )
                elif name == "spread_momentum_5d":
                    return MockIndicatorMetadata(
                        "spread_momentum_5d",
                        {"cdx": "spread"},
                        {"cdx": "cdx_ig_5y"},
                        {"lookback": 5},
                        "basis_points",
                    )
                raise ValueError(f"Unknown indicator: {name}")

            def indicator_exists(self, name):
                return name in ["cdx_etf_spread_diff", "spread_momentum_5d"]

            def get_all_indicators(self):
                return ["cdx_etf_spread_diff", "spread_momentum_5d"]

        return MockRegistry()

    @pytest.fixture
    def mock_score_registry(self):
        """Mock score transformation registry."""

        class MockScoreMetadata:
            def __init__(self, name, transform_type, params):
                self.name = name
                self.transform_type = transform_type
                self.parameters = params

        class MockRegistry:
            def get_metadata(self, name):
                if name == "z_score_20d":
                    return MockScoreMetadata(
                        "z_score_20d", "z_score", {"window": 20, "min_periods": 10}
                    )
                elif name == "z_score_60d":
                    return MockScoreMetadata(
                        "z_score_60d", "z_score", {"window": 60, "min_periods": 30}
                    )
                raise ValueError(f"Unknown score transformation: {name}")

            def transformation_exists(self, name):
                return name in ["z_score_20d", "z_score_60d"]

            def list_all(self):
                return {
                    "z_score_20d": None,
                    "z_score_60d": None,
                }

        return MockRegistry()

    @pytest.fixture
    def mock_signal_transformation_registry(self):
        """Mock signal transformation registry."""

        class MockSignalTransformMetadata:
            def __init__(self, name, scaling, floor, cap, neutral_range):
                self.name = name
                self.scaling = scaling
                self.floor = floor
                self.cap = cap
                self.neutral_range = neutral_range

        class MockRegistry:
            def get_metadata(self, name):
                if name == "passthrough":
                    return MockSignalTransformMetadata(
                        "passthrough", 1.0, None, None, None
                    )
                elif name == "bounded_1_5":
                    return MockSignalTransformMetadata(
                        "bounded_1_5", 1.0, -1.5, 1.5, (-0.25, 0.25)
                    )
                raise ValueError(f"Unknown signal transformation: {name}")

            def transformation_exists(self, name):
                return name in ["passthrough", "bounded_1_5"]

            def list_all(self):
                return {
                    "passthrough": None,
                    "bounded_1_5": None,
                }

        return MockRegistry()

    @pytest.fixture
    def mock_signal_registry(self):
        """Mock signal registry."""

        class MockSignalMetadata:
            def __init__(
                self,
                name,
                indicator_transformation,
                score_transformation,
                signal_transformation,
                sign_multiplier,
            ):
                self.name = name
                self.indicator_transformation = indicator_transformation
                self.score_transformation = score_transformation
                self.signal_transformation = signal_transformation
                self.sign_multiplier = sign_multiplier

        class MockRegistry:
            def get_metadata(self, name):
                if name == "cdx_etf_basis":
                    return MockSignalMetadata(
                        "cdx_etf_basis",
                        "cdx_etf_spread_diff",
                        "z_score_20d",
                        "passthrough",
                        1,
                    )
                elif name == "inverted_signal":
                    return MockSignalMetadata(
                        "inverted_signal",
                        "cdx_etf_spread_diff",
                        "z_score_20d",
                        "passthrough",
                        -1,
                    )
                raise ValueError(f"Unknown signal: {name}")

        return MockRegistry()

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)  # For reproducibility

        cdx_df = pd.DataFrame({"spread": np.random.randn(100) * 20 + 120}, index=dates)
        etf_df = pd.DataFrame({"spread": np.random.randn(100) * 15 + 110}, index=dates)
        vix_df = pd.DataFrame({"level": np.random.randn(100) * 5 + 18}, index=dates)

        return {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}

    def test_compose_signal_four_stage_pipeline(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test four-stage pipeline: indicator → score → signal → sign."""

        # Mock compute_indicator to return deterministic data
        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            # Return simple spread difference
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Compose signal via full pipeline
        signal = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
        )

        # Validate
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100

        # Check z-score properties (after warmup)
        valid_signal = signal.dropna()
        assert len(valid_signal) > 0

    def test_compose_signal_with_sign_multiplier(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test sign multiplier application in final stage."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            # Return positive values
            return pd.Series(
                np.ones(100) * 10,
                index=sample_market_data["cdx"].index,
                name="indicator",
            )

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Compose signal with negative sign multiplier
        signal = compose_signal(
            signal_name="inverted_signal",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
        )

        # Validate - signal should exist
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100

    def test_compose_signal_with_intermediates(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test include_intermediates returns all pipeline stages."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Compose with intermediates
        result = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
            include_intermediates=True,
        )

        # Validate result is dict with all stages
        assert isinstance(result, dict)
        assert "indicator" in result
        assert "score" in result
        assert "signal" in result

        # All should be Series
        assert isinstance(result["indicator"], pd.Series)
        assert isinstance(result["score"], pd.Series)
        assert isinstance(result["signal"], pd.Series)

        # All should have same length
        assert len(result["indicator"]) == 100
        assert len(result["score"]) == 100
        assert len(result["signal"]) == 100

    def test_compose_signal_with_runtime_overrides(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test runtime overrides for all transformation stages."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Override score transformation (60d instead of 20d)
        signal = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
            score_transformation_override="z_score_60d",
        )

        # Validate
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100

    def test_compose_signal_invalid_override(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
    ):
        """Test error when override doesn't exist in registry."""

        with pytest.raises(
            ValueError, match="score_transformation_override.*not found"
        ):
            compose_signal(
                signal_name="cdx_etf_basis",
                market_data=sample_market_data,
                indicator_registry=mock_indicator_registry,
                score_registry=mock_score_registry,
                signal_transformation_registry=mock_signal_transformation_registry,
                signal_registry=mock_signal_registry,
                score_transformation_override="nonexistent_transformation",
            )


class TestStageInspectionFunctions:
    """Test stage-specific inspection functions (T025)."""

    @pytest.fixture
    def mock_indicator_registry(self):
        """Mock indicator transformation registry."""

        class MockIndicatorMetadata:
            def __init__(self, name, data_reqs, default_secs, params, output_units):
                self.name = name
                self.data_requirements = data_reqs
                self.default_securities = default_secs
                self.parameters = params
                self.output_units = output_units

        class MockRegistry:
            def get_metadata(self, name):
                if name == "cdx_etf_spread_diff":
                    return MockIndicatorMetadata(
                        "cdx_etf_spread_diff",
                        {"cdx": "spread", "etf": "spread"},
                        {"cdx": "cdx_ig_5y", "etf": "lqd"},
                        {},
                        "basis_points",
                    )
                raise ValueError(f"Unknown indicator: {name}")

        return MockRegistry()

    @pytest.fixture
    def mock_score_registry(self):
        """Mock score transformation registry."""

        class MockScoreMetadata:
            def __init__(self, name, transform_type, params):
                self.name = name
                self.transform_type = transform_type
                self.parameters = params

        class MockRegistry:
            def get_metadata(self, name):
                if name == "z_score_20d":
                    return MockScoreMetadata(
                        "z_score_20d", "z_score", {"window": 20, "min_periods": 10}
                    )
                raise ValueError(f"Unknown score transformation: {name}")

        return MockRegistry()

    @pytest.fixture
    def mock_signal_transformation_registry(self):
        """Mock signal transformation registry."""

        class MockSignalTransformMetadata:
            def __init__(self, name, scaling, floor, cap, neutral_range):
                self.name = name
                self.scaling = scaling
                self.floor = floor
                self.cap = cap
                self.neutral_range = neutral_range

        class MockRegistry:
            def get_metadata(self, name):
                if name == "passthrough":
                    return MockSignalTransformMetadata(
                        "passthrough", 1.0, None, None, None
                    )
                raise ValueError(f"Unknown signal transformation: {name}")

        return MockRegistry()

    @pytest.fixture
    def mock_signal_registry(self):
        """Mock signal registry."""

        class MockSignalMetadata:
            def __init__(
                self,
                name,
                indicator_transformation,
                score_transformation,
                signal_transformation,
                sign_multiplier,
            ):
                self.name = name
                self.indicator_transformation = indicator_transformation
                self.score_transformation = score_transformation
                self.signal_transformation = signal_transformation
                self.sign_multiplier = sign_multiplier

        class MockRegistry:
            def get_metadata(self, name):
                if name == "cdx_etf_basis":
                    return MockSignalMetadata(
                        "cdx_etf_basis",
                        "cdx_etf_spread_diff",
                        "z_score_20d",
                        "passthrough",
                        1,
                    )
                raise ValueError(f"Unknown signal: {name}")

        return MockRegistry()

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        cdx_df = pd.DataFrame({"spread": np.random.randn(100) * 20 + 120}, index=dates)
        etf_df = pd.DataFrame({"spread": np.random.randn(100) * 15 + 110}, index=dates)

        return {"cdx": cdx_df, "etf": etf_df}

    def test_compute_indicator_stage(
        self,
        mock_indicator_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test computing indicator stage only."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Compute indicator stage only
        indicator = compute_indicator_stage(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            signal_registry=mock_signal_registry,
        )

        # Validate
        assert isinstance(indicator, pd.Series)
        assert len(indicator) == 100
        # Should be raw basis in bps (not normalized)
        assert indicator.notna().sum() > 0

    def test_compute_score_stage(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test computing through score stage."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Compute through score stage
        score = compute_score_stage(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_registry=mock_signal_registry,
        )

        # Validate
        assert isinstance(score, pd.Series)
        assert len(score) == 100
        # Should be normalized (z-score)
        valid_score = score.dropna()
        assert len(valid_score) > 0

    def test_compute_signal_stage(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test computing through signal stage (full pipeline)."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Compute through signal stage (full pipeline)
        signal = compute_signal_stage(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
        )

        # Validate
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100
        # Should be final signal (bounded, with sign convention)
        assert signal.notna().sum() > 0


class TestEdgeCases:
    """Test edge cases and error handling (T053-T054)."""

    def test_nan_propagation_through_stages(self):
        """Test that NaN values propagate correctly through all transformation stages."""
        dates = pd.date_range("2024-01-01", periods=50, freq="D")

        # Create indicator with some NaN values
        values = np.random.randn(50) * 10 + 100
        values[10:15] = np.nan  # Inject NaN values
        indicator = pd.Series(values, index=dates, name="indicator")

        # Apply score transformation (z-score)
        score_metadata = {
            "name": "z_score_20d",
            "transform_type": "z_score",
            "parameters": {"window": 20, "min_periods": 10},
        }
        score = apply_score_transformation(indicator, score_metadata)

        # Apply signal transformation
        signal = apply_signal_transformation(
            score,
            scaling=1.0,
            floor=-2.0,
            cap=2.0,
            neutral_range=(-0.5, 0.5),
        )

        # NaN values should propagate through all stages
        assert indicator.isna().sum() == 5  # Original NaN count
        # NaN may expand due to rolling window, but should be present
        assert score.isna().sum() >= 5
        assert signal.isna().sum() >= 5

    def test_zero_variance_score_handling(self):
        """Test handling of constant (zero-variance) indicator for z-score."""
        dates = pd.date_range("2024-01-01", periods=50, freq="D")

        # Create constant indicator (zero variance)
        indicator = pd.Series(np.ones(50) * 100.0, index=dates, name="constant")

        # Apply z-score transformation
        score_metadata = {
            "name": "z_score_20d",
            "transform_type": "z_score",
            "parameters": {"window": 20, "min_periods": 10},
        }
        score = apply_score_transformation(indicator, score_metadata)

        # Zero variance should result in NaN (division by zero in z-score)
        # After warmup period, all values should be NaN
        valid_count = score.notna().sum()
        # First min_periods will be NaN due to warmup, rest due to zero std
        assert valid_count == 0  # All NaN due to constant series

    def test_signal_transformation_with_all_nan_input(self):
        """Test signal transformation handles all-NaN input gracefully."""
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        score = pd.Series(np.full(20, np.nan), index=dates, name="score")

        # Apply signal transformation
        signal = apply_signal_transformation(
            score,
            scaling=1.0,
            floor=-1.5,
            cap=1.5,
            neutral_range=(-0.25, 0.25),
        )

        # Should return all NaN (no errors)
        assert isinstance(signal, pd.Series)
        assert len(signal) == 20
        assert signal.isna().all()

    def test_signal_transformation_preserves_index(self):
        """Test that signal transformation preserves original DatetimeIndex."""
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        score = pd.Series(np.linspace(-2.0, 2.0, 20), index=dates, name="score")

        signal = apply_signal_transformation(
            score,
            scaling=1.0,
            floor=-1.5,
            cap=1.5,
            neutral_range=None,
        )

        # Index should be preserved
        assert signal.index.equals(dates)
        assert isinstance(signal.index, pd.DatetimeIndex)


class TestRuntimeOverrides:
    """Test runtime override functionality (T039)."""

    @pytest.fixture
    def mock_indicator_registry(self):
        """Mock indicator transformation registry."""

        class MockIndicatorMetadata:
            def __init__(self, name, data_reqs, default_secs, params, output_units):
                self.name = name
                self.data_requirements = data_reqs
                self.default_securities = default_secs
                self.parameters = params
                self.output_units = output_units

        class MockRegistry:
            def get_metadata(self, name):
                if name == "cdx_etf_spread_diff":
                    return MockIndicatorMetadata(
                        "cdx_etf_spread_diff",
                        {"cdx": "spread", "etf": "spread"},
                        {"cdx": "cdx_ig_5y", "etf": "lqd"},
                        {},
                        "basis_points",
                    )
                elif name == "alternate_indicator":
                    return MockIndicatorMetadata(
                        "alternate_indicator",
                        {"cdx": "spread"},
                        {"cdx": "cdx_ig_5y"},
                        {},
                        "basis_points",
                    )
                raise ValueError(f"Unknown indicator: {name}")

            def indicator_exists(self, name):
                return name in ["cdx_etf_spread_diff", "alternate_indicator"]

            def get_all_indicators(self):
                return ["cdx_etf_spread_diff", "alternate_indicator"]

        return MockRegistry()

    @pytest.fixture
    def mock_score_registry(self):
        """Mock score transformation registry."""

        class MockScoreMetadata:
            def __init__(self, name, transform_type, params):
                self.name = name
                self.transform_type = transform_type
                self.parameters = params

        class MockRegistry:
            def get_metadata(self, name):
                if name == "z_score_20d":
                    return MockScoreMetadata(
                        "z_score_20d", "z_score", {"window": 20, "min_periods": 10}
                    )
                elif name == "z_score_60d":
                    return MockScoreMetadata(
                        "z_score_60d", "z_score", {"window": 60, "min_periods": 30}
                    )
                raise ValueError(f"Unknown score transformation: {name}")

            def transformation_exists(self, name):
                return name in ["z_score_20d", "z_score_60d"]

            def list_all(self):
                return {"z_score_20d": None, "z_score_60d": None}

        return MockRegistry()

    @pytest.fixture
    def mock_signal_transformation_registry(self):
        """Mock signal transformation registry."""

        class MockSignalTransformMetadata:
            def __init__(self, name, scaling, floor, cap, neutral_range):
                self.name = name
                self.scaling = scaling
                self.floor = floor
                self.cap = cap
                self.neutral_range = neutral_range

        class MockRegistry:
            def get_metadata(self, name):
                if name == "passthrough":
                    return MockSignalTransformMetadata(
                        "passthrough", 1.0, None, None, None
                    )
                elif name == "bounded_1_5":
                    return MockSignalTransformMetadata(
                        "bounded_1_5", 1.0, -1.5, 1.5, (-0.25, 0.25)
                    )
                raise ValueError(f"Unknown signal transformation: {name}")

            def transformation_exists(self, name):
                return name in ["passthrough", "bounded_1_5"]

            def list_all(self):
                return {"passthrough": None, "bounded_1_5": None}

        return MockRegistry()

    @pytest.fixture
    def mock_signal_registry(self):
        """Mock signal registry."""

        class MockSignalMetadata:
            def __init__(
                self,
                name,
                indicator_transformation,
                score_transformation,
                signal_transformation,
                sign_multiplier,
            ):
                self.name = name
                self.indicator_transformation = indicator_transformation
                self.score_transformation = score_transformation
                self.signal_transformation = signal_transformation
                self.sign_multiplier = sign_multiplier

        class MockRegistry:
            def get_metadata(self, name):
                if name == "cdx_etf_basis":
                    return MockSignalMetadata(
                        "cdx_etf_basis",
                        "cdx_etf_spread_diff",
                        "z_score_20d",
                        "passthrough",
                        1,
                    )
                raise ValueError(f"Unknown signal: {name}")

        return MockRegistry()

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        cdx_df = pd.DataFrame({"spread": np.random.randn(100) * 20 + 120}, index=dates)
        etf_df = pd.DataFrame({"spread": np.random.randn(100) * 15 + 110}, index=dates)

        return {"cdx": cdx_df, "etf": etf_df}

    def test_indicator_transformation_override(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test indicator transformation override."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            # Return different values based on indicator name
            if indicator_name == "alternate_indicator":
                return pd.Series(
                    np.ones(100) * 50, index=sample_market_data["cdx"].index
                )
            else:
                cdx_spread = market_data["cdx"]["spread"]
                etf_spread = market_data["etf"]["spread"]
                return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Override indicator transformation
        signal = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
            indicator_transformation_override="alternate_indicator",
        )

        assert isinstance(signal, pd.Series)
        assert len(signal) == 100

    def test_score_transformation_override(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test score transformation override."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Override score transformation (60d instead of default 20d)
        signal = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
            score_transformation_override="z_score_60d",
        )

        assert isinstance(signal, pd.Series)
        assert len(signal) == 100

    def test_signal_transformation_override(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test signal transformation override."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Override signal transformation (bounded instead of passthrough)
        signal = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
            signal_transformation_override="bounded_1_5",
        )

        assert isinstance(signal, pd.Series)
        assert len(signal) == 100
        # Bounded signal should respect bounds
        assert signal.dropna().min() >= -1.5
        assert signal.dropna().max() <= 1.5

    def test_multiple_overrides_simultaneously(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test applying multiple overrides at once."""

        def mock_compute_indicator(indicator_name, market_data, indicator_metadata):
            if indicator_name == "alternate_indicator":
                return pd.Series(
                    np.linspace(-50, 50, 100), index=sample_market_data["cdx"].index
                )
            else:
                cdx_spread = market_data["cdx"]["spread"]
                etf_spread = market_data["etf"]["spread"]
                return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Override all three stages
        signal = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=mock_indicator_registry,
            score_registry=mock_score_registry,
            signal_transformation_registry=mock_signal_transformation_registry,
            signal_registry=mock_signal_registry,
            indicator_transformation_override="alternate_indicator",
            score_transformation_override="z_score_60d",
            signal_transformation_override="bounded_1_5",
        )

        assert isinstance(signal, pd.Series)
        assert len(signal) == 100

    def test_invalid_indicator_override_raises_error(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
    ):
        """Test that invalid indicator override raises clear error."""

        with pytest.raises(
            ValueError, match="indicator_transformation_override.*not found"
        ):
            compose_signal(
                signal_name="cdx_etf_basis",
                market_data=sample_market_data,
                indicator_registry=mock_indicator_registry,
                score_registry=mock_score_registry,
                signal_transformation_registry=mock_signal_transformation_registry,
                signal_registry=mock_signal_registry,
                indicator_transformation_override="nonexistent",
            )

    def test_invalid_score_override_raises_error(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
    ):
        """Test that invalid score override raises clear error."""

        with pytest.raises(
            ValueError, match="score_transformation_override.*not found"
        ):
            compose_signal(
                signal_name="cdx_etf_basis",
                market_data=sample_market_data,
                indicator_registry=mock_indicator_registry,
                score_registry=mock_score_registry,
                signal_transformation_registry=mock_signal_transformation_registry,
                signal_registry=mock_signal_registry,
                score_transformation_override="nonexistent",
            )

    def test_invalid_signal_transformation_override_raises_error(
        self,
        mock_indicator_registry,
        mock_score_registry,
        mock_signal_transformation_registry,
        mock_signal_registry,
        sample_market_data,
    ):
        """Test that invalid signal transformation override raises clear error."""

        with pytest.raises(
            ValueError, match="signal_transformation_override.*not found"
        ):
            compose_signal(
                signal_name="cdx_etf_basis",
                market_data=sample_market_data,
                indicator_registry=mock_indicator_registry,
                score_registry=mock_score_registry,
                signal_transformation_registry=mock_signal_transformation_registry,
                signal_registry=mock_signal_registry,
                signal_transformation_override="nonexistent",
            )


class TestMigratedSignals:
    """Test migrated signals work correctly with new structure (T040-T042)."""

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for integration testing."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)

        cdx_df = pd.DataFrame(
            {"spread": 100 + np.random.randn(100) * 10, "security": "cdx_ig_5y"},
            index=dates,
        )
        etf_df = pd.DataFrame(
            {"spread": 50 + np.random.randn(100) * 5, "security": "lqd"}, index=dates
        )
        vix_df = pd.DataFrame(
            {"level": 15 + np.random.randn(100) * 3, "security": "vix"}, index=dates
        )

        return {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}

    def test_cdx_etf_basis_signal_integration(self, sample_market_data):
        """Test cdx_etf_basis signal produces valid output with new structure (T040)."""
        from aponyx.models.orchestrator import compute_registered_signals
        from aponyx.models.registry import SignalRegistry
        from aponyx.config import SIGNAL_CATALOG_PATH

        # Load real registries
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Compute all signals
        signals = compute_registered_signals(signal_registry, sample_market_data)

        # Verify cdx_etf_basis exists and is valid
        assert "cdx_etf_basis" in signals
        signal = signals["cdx_etf_basis"]

        # Check basic properties
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100
        assert signal.notna().sum() > 0

        # Check it's normalized (z-score like values)
        valid_signal = signal.dropna()
        assert len(valid_signal) > 0

    def test_cdx_vix_gap_signal_preserves_sign_convention(self, sample_market_data):
        """Test cdx_vix_gap signal preserves sign convention (T041)."""
        from aponyx.models.orchestrator import compute_registered_signals
        from aponyx.models.registry import SignalRegistry
        from aponyx.config import SIGNAL_CATALOG_PATH

        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Compute signals
        signals = compute_registered_signals(signal_registry, sample_market_data)

        # Verify cdx_vix_gap exists
        assert "cdx_vix_gap" in signals
        signal = signals["cdx_vix_gap"]

        # Check basic properties
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100

        # Sign convention: positive = long credit risk (buy CDX)
        # Signal should have both positive and negative values (directional)
        valid_signal = signal.dropna()
        if len(valid_signal) > 0:
            # Should have variation (not all zeros)
            assert valid_signal.std() > 0

    def test_spread_momentum_signal_valid_output(self, sample_market_data):
        """Test spread_momentum signal produces valid bounded output (T042)."""
        from aponyx.models.orchestrator import compute_registered_signals
        from aponyx.models.registry import SignalRegistry
        from aponyx.config import SIGNAL_CATALOG_PATH

        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Compute signals
        signals = compute_registered_signals(signal_registry, sample_market_data)

        # Verify spread_momentum exists
        assert "spread_momentum" in signals
        signal = signals["spread_momentum"]

        # Check basic properties
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100
        assert signal.notna().sum() > 0

        # Signal should be finite
        valid_signal = signal.dropna()
        assert len(valid_signal) > 0
        assert np.all(np.isfinite(valid_signal))

    def test_all_signals_use_new_catalog_structure(self):
        """Verify all signals use the new 4-stage transformation structure."""
        from aponyx.models.registry import SignalRegistry
        from aponyx.config import SIGNAL_CATALOG_PATH

        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        all_signals = signal_registry.list_all()

        # All signals should have the new structure
        for signal_name, signal_metadata in all_signals.items():
            # New structure has these fields
            assert hasattr(signal_metadata, "indicator_transformation")
            assert hasattr(signal_metadata, "score_transformation")
            assert hasattr(signal_metadata, "signal_transformation")

            # Old structure fields should not exist
            assert not hasattr(signal_metadata, "indicator_dependencies")
            assert not hasattr(signal_metadata, "transformations")
            assert not hasattr(signal_metadata, "composition_logic")

            # Values should be strings (single references)
            assert isinstance(signal_metadata.indicator_transformation, str)
            assert isinstance(signal_metadata.score_transformation, str)
            assert isinstance(signal_metadata.signal_transformation, str)
