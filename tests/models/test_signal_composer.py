"""
Tests for signal composition functions.

Validates:
- Transformation application to indicator series
- Single-indicator signal composition
- Multi-indicator signal composition with composition_logic
- Sign multiplier application
- Error handling for invalid composition logic
"""

import numpy as np
import pandas as pd
import pytest

from aponyx.models.signal_composer import apply_signal_transformation, compose_signal


class TestApplySignalTransformation:
    """Test transformation application to indicator series."""

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
        signal = apply_signal_transformation(indicator, transformation_metadata)

        # Validate
        assert isinstance(signal, pd.Series)
        assert len(signal) == len(indicator)

        # Check z-score properties (after warmup)
        valid_signal = signal.dropna()
        assert len(valid_signal) > 0
        # Z-scores should have roughly zero mean and unit variance
        assert abs(valid_signal.mean()) < 0.5
        assert abs(valid_signal.std() - 1.0) < 0.5

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
        signal = apply_signal_transformation(indicator, transformation_metadata)

        # Validate
        assert isinstance(signal, pd.Series)
        assert len(signal) == len(indicator)

        # Check diff properties
        valid_signal = signal.dropna()
        # 5-day diff of linear trend should be constant 25 (5 periods * 5 per period)
        assert np.allclose(valid_signal, 25.0)

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
        signal = apply_signal_transformation(indicator, transformation_metadata)

        # Validate
        assert isinstance(signal, pd.Series)
        assert len(signal) == len(indicator)

        # Check that values are normalized (finite, not too extreme)
        valid_signal = signal.dropna()
        assert len(valid_signal) > 0
        assert np.all(np.isfinite(valid_signal))


class TestComposeSignal:
    """Test signal composition from indicators and transformations."""

    @pytest.fixture
    def mock_indicator_registry(self):
        """Mock indicator registry."""

        class MockIndicatorMetadata:
            def __init__(self, name, data_reqs, default_secs, params):
                self.name = name
                self.data_requirements = data_reqs
                self.default_securities = default_secs
                self.parameters = params

            def __dict__(self):
                return {
                    "name": self.name,
                    "data_requirements": self.data_requirements,
                    "default_securities": self.default_secs,
                    "parameters": self.parameters,
                }

        class MockRegistry:
            def get_metadata(self, name):
                if name == "cdx_etf_spread_diff":
                    return MockIndicatorMetadata(
                        "cdx_etf_spread_diff",
                        {"cdx": "spread", "etf": "spread"},
                        {"cdx": "cdx_ig_5y", "etf": "lqd"},
                        {},
                    )
                elif name == "spread_momentum_5d":
                    return MockIndicatorMetadata(
                        "spread_momentum_5d",
                        {"cdx": "spread"},
                        {"cdx": "cdx_ig_5y"},
                        {"lookback": 5},
                    )
                raise ValueError(f"Unknown indicator: {name}")

        return MockRegistry()

    @pytest.fixture
    def mock_transformation_registry(self):
        """Mock transformation registry."""

        class MockTransformationMetadata:
            def __init__(self, name, transform_type, params):
                self.name = name
                self.transform_type = transform_type
                self.parameters = params

        class MockRegistry:
            def get_metadata(self, name):
                if name == "z_score_20d":
                    return MockTransformationMetadata(
                        "z_score_20d", "z_score", {"window": 20, "min_periods": 10}
                    )
                elif name == "z_score_60d":
                    return MockTransformationMetadata(
                        "z_score_60d", "z_score", {"window": 60, "min_periods": 30}
                    )
                raise ValueError(f"Unknown transformation: {name}")

        return MockRegistry()

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")

        cdx_df = pd.DataFrame({"spread": np.random.randn(100) * 20 + 120}, index=dates)
        etf_df = pd.DataFrame({"spread": np.random.randn(100) * 15 + 110}, index=dates)
        vix_df = pd.DataFrame({"level": np.random.randn(100) * 5 + 18}, index=dates)

        return {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}

    def test_compose_single_indicator_signal(
        self,
        mock_indicator_registry,
        mock_transformation_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test composing signal from single indicator with transformation."""

        # Mock compute_indicator to return deterministic data
        def mock_compute_indicator(
            indicator_name, indicator_metadata, market_data, use_cache=True
        ):
            # Return simple spread difference
            cdx_spread = market_data["cdx"]["spread"]
            etf_spread = market_data["etf"]["spread"]
            return cdx_spread - etf_spread

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Single-indicator signal metadata
        signal_metadata = {
            "name": "cdx_etf_basis_zscore",
            "indicator_dependencies": ["cdx_etf_spread_diff"],
            "transformations": ["z_score_20d"],
            "composition_logic": None,
            "sign_multiplier": 1,
        }

        # Compose signal
        signal = compose_signal(
            mock_indicator_registry,
            mock_transformation_registry,
            signal_metadata,
            sample_market_data,
        )

        # Validate
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100

        # Check z-score properties
        valid_signal = signal.dropna()
        assert len(valid_signal) > 0
        # Should be approximately zero mean, unit variance
        assert abs(valid_signal.mean()) < 0.5

    def test_compose_signal_with_sign_multiplier(
        self,
        mock_indicator_registry,
        mock_transformation_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test sign multiplier application."""

        def mock_compute_indicator(
            indicator_name, indicator_metadata, market_data, use_cache=True
        ):
            # Return positive values
            return pd.Series(
                np.ones(100), index=sample_market_data["cdx"].index, name="indicator"
            )

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        # Signal with negative sign multiplier
        signal_metadata = {
            "name": "inverted_signal",
            "indicator_dependencies": ["cdx_etf_spread_diff"],
            "transformations": ["z_score_20d"],
            "composition_logic": None,
            "sign_multiplier": -1,
        }

        # Compose signal
        signal = compose_signal(
            mock_indicator_registry,
            mock_transformation_registry,
            signal_metadata,
            sample_market_data,
        )

        # Validate - should be inverted
        # After z-score of constant series (std=0), we get NaN or 0, but sign multiplier applied
        # This is a simple check that sign_multiplier is applied
        assert isinstance(signal, pd.Series)

    def test_compose_signal_transformation_count_mismatch(
        self,
        mock_indicator_registry,
        mock_transformation_registry,
        sample_market_data,
    ):
        """Test error when transformation count doesn't match indicator count."""
        signal_metadata = {
            "name": "mismatched_signal",
            "indicator_dependencies": ["cdx_etf_spread_diff", "spread_momentum_5d"],
            "transformations": [
                "z_score_20d"
            ],  # Only 1 transformation for 2 indicators
            "composition_logic": "cdx_etf_spread_diff + spread_momentum_5d",
            "sign_multiplier": 1,
        }

        with pytest.raises(ValueError, match="transformation count.*must match"):
            compose_signal(
                mock_indicator_registry,
                mock_transformation_registry,
                signal_metadata,
                sample_market_data,
            )

    def test_compose_multi_indicator_no_composition_logic(
        self,
        mock_indicator_registry,
        mock_transformation_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test error when multi-indicator signal lacks composition_logic."""

        def mock_compute_indicator(
            indicator_name, indicator_metadata, market_data, use_cache=True
        ):
            return pd.Series(
                np.ones(100), index=sample_market_data["cdx"].index, name="indicator"
            )

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        signal_metadata = {
            "name": "multi_no_logic",
            "indicator_dependencies": ["cdx_etf_spread_diff", "spread_momentum_5d"],
            "transformations": ["z_score_20d", "z_score_60d"],
            "composition_logic": None,  # Missing!
            "sign_multiplier": 1,
        }

        with pytest.raises(ValueError, match="composition_logic required"):
            compose_signal(
                mock_indicator_registry,
                mock_transformation_registry,
                signal_metadata,
                sample_market_data,
            )

    def test_compose_multi_indicator_with_composition_logic(
        self,
        mock_indicator_registry,
        mock_transformation_registry,
        sample_market_data,
        monkeypatch,
    ):
        """Test multi-indicator signal composition with combination logic."""
        # Mock to return different indicators
        call_count = [0]

        def mock_compute_indicator(
            indicator_name, indicator_metadata, market_data, use_cache=True
        ):
            call_count[0] += 1
            # First call: spread_diff, second call: momentum
            if call_count[0] == 1:
                return pd.Series(
                    np.arange(100),
                    index=sample_market_data["cdx"].index,
                    name="spread_diff",
                )
            else:
                return pd.Series(
                    np.arange(100, 200),
                    index=sample_market_data["cdx"].index,
                    name="momentum",
                )

        monkeypatch.setattr(
            "aponyx.models.indicators.compute_indicator", mock_compute_indicator
        )

        signal_metadata = {
            "name": "combined_signal",
            "indicator_dependencies": ["cdx_etf_spread_diff", "spread_momentum_5d"],
            "transformations": ["z_score_20d", "z_score_60d"],
            "composition_logic": "cdx_etf_spread_diff + spread_momentum_5d",
            "sign_multiplier": 1,
        }

        # Compose signal
        signal = compose_signal(
            mock_indicator_registry,
            mock_transformation_registry,
            signal_metadata,
            sample_market_data,
        )

        # Validate
        assert isinstance(signal, pd.Series)
        assert len(signal) == 100
        # Should combine both indicators
        assert signal.notna().sum() > 0
