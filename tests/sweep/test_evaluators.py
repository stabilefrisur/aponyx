"""Tests for sweep evaluators module.

Verifies that parameter overrides are correctly applied during signal composition.
Regression tests for: https://github.com/aponyx/docs/bugs/sweep-parameter-overrides-not-applied.md
"""

import pandas as pd
import pytest

from aponyx.sweep.config import BaseConfig, ParameterOverride, SweepConfig
from aponyx.sweep.evaluators import _apply_parameter_overrides


class TestApplyParameterOverrides:
    """Tests for _apply_parameter_overrides helper function."""

    def test_extracts_matching_prefix(self) -> None:
        """Extracts parameters matching the given prefix."""
        combination = {
            "signal_transformation.parameters.floor": -2.0,
            "signal_transformation.parameters.cap": 2.0,
            "strategy.position_size_mm": 10.0,
        }

        result = _apply_parameter_overrides(
            {}, combination, "signal_transformation.parameters."
        )

        assert result == {"floor": -2.0, "cap": 2.0}

    def test_ignores_non_matching_prefix(self) -> None:
        """Ignores parameters not matching the prefix."""
        combination = {
            "strategy.position_size_mm": 10.0,
            "strategy.stop_loss_pct": 5.0,
        }

        result = _apply_parameter_overrides(
            {}, combination, "signal_transformation.parameters."
        )

        assert result == {}

    def test_merges_with_base_params(self) -> None:
        """Merges overrides with existing base parameters."""
        base_params = {"floor": -1.0, "cap": 1.0, "scaling": 1.0}
        combination = {
            "signal_transformation.parameters.floor": -2.0,
        }

        result = _apply_parameter_overrides(
            base_params, combination, "signal_transformation.parameters."
        )

        assert result == {"floor": -2.0, "cap": 1.0, "scaling": 1.0}

    def test_extracts_indicator_params(self) -> None:
        """Extracts indicator transformation parameters."""
        combination = {
            "indicator_transformation.parameters.lookback": 20,
            "indicator_transformation.parameters.method": "simple",
        }

        result = _apply_parameter_overrides(
            {}, combination, "indicator_transformation.parameters."
        )

        assert result == {"lookback": 20, "method": "simple"}

    def test_extracts_score_params(self) -> None:
        """Extracts score transformation parameters."""
        combination = {
            "score_transformation.parameters.window": 30,
            "score_transformation.parameters.min_periods": 15,
        }

        result = _apply_parameter_overrides(
            {}, combination, "score_transformation.parameters."
        )

        assert result == {"window": 30, "min_periods": 15}


class TestComposeSignalWithOverrides:
    """Tests verifying compose_signal applies parameter overrides correctly."""

    @pytest.fixture
    def sample_market_data(self) -> dict[str, pd.DataFrame]:
        """Create sample market data for testing."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        cdx_data = pd.DataFrame(
            {
                "spread": [100 + i * 0.5 for i in range(100)],
                "price": [100.0] * 100,
            },
            index=dates,
        )
        etf_data = pd.DataFrame(
            {
                "spread": [95 + i * 0.3 for i in range(100)],
                "price": [50.0] * 100,
            },
            index=dates,
        )
        return {"cdx": cdx_data, "etf": etf_data}

    def test_signal_transformation_cap_affects_output(
        self, sample_market_data: dict[str, pd.DataFrame]
    ) -> None:
        """Different cap values produce different signal values."""
        from aponyx.config import (
            INDICATOR_TRANSFORMATION_PATH,
            SCORE_TRANSFORMATION_PATH,
            SIGNAL_CATALOG_PATH,
            SIGNAL_TRANSFORMATION_PATH,
        )
        from aponyx.models.registry import (
            IndicatorTransformationRegistry,
            ScoreTransformationRegistry,
            SignalRegistry,
            SignalTransformationRegistry,
        )
        from aponyx.models.signal_composer import compose_signal

        indicator_registry = IndicatorTransformationRegistry(
            INDICATOR_TRANSFORMATION_PATH
        )
        score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
        signal_transformation_registry = SignalTransformationRegistry(
            SIGNAL_TRANSFORMATION_PATH
        )
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Compose signal with low cap
        signal_low_cap = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=indicator_registry,
            score_registry=score_registry,
            signal_transformation_registry=signal_transformation_registry,
            signal_registry=signal_registry,
            signal_transformation_params_override={"cap": 0.5},
        )

        # Compose signal with high cap
        signal_high_cap = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=indicator_registry,
            score_registry=score_registry,
            signal_transformation_registry=signal_transformation_registry,
            signal_registry=signal_registry,
            signal_transformation_params_override={"cap": 5.0},
        )

        # Low cap should constrain values more
        assert signal_low_cap.max() <= 0.5
        # High cap should allow higher values (unless signal is naturally bounded)
        # The key point is they should not be identical
        assert not signal_low_cap.equals(signal_high_cap)

    def test_signal_transformation_floor_affects_output(
        self, sample_market_data: dict[str, pd.DataFrame]
    ) -> None:
        """Different floor values produce different signal values when signal has negatives."""
        from aponyx.config import (
            INDICATOR_TRANSFORMATION_PATH,
            SCORE_TRANSFORMATION_PATH,
            SIGNAL_CATALOG_PATH,
            SIGNAL_TRANSFORMATION_PATH,
        )
        from aponyx.models.registry import (
            IndicatorTransformationRegistry,
            ScoreTransformationRegistry,
            SignalRegistry,
            SignalTransformationRegistry,
        )
        from aponyx.models.signal_composer import compose_signal

        indicator_registry = IndicatorTransformationRegistry(
            INDICATOR_TRANSFORMATION_PATH
        )
        score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
        signal_transformation_registry = SignalTransformationRegistry(
            SIGNAL_TRANSFORMATION_PATH
        )
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Compose signal with tight floor (close to 0)
        signal_tight_floor = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=indicator_registry,
            score_registry=score_registry,
            signal_transformation_registry=signal_transformation_registry,
            signal_registry=signal_registry,
            signal_transformation_params_override={"floor": 1.5},  # Floor at 1.5
        )

        # Compose signal with loose floor (well below min)
        signal_loose_floor = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=indicator_registry,
            score_registry=score_registry,
            signal_transformation_registry=signal_transformation_registry,
            signal_registry=signal_registry,
            signal_transformation_params_override={"floor": -5.0},
        )

        # Tight floor should constrain values more (all values >= 1.5)
        valid_tight = signal_tight_floor.dropna()
        assert valid_tight.min() >= 1.5
        # They should not be identical (floor at 1.5 clips values below 1.5)
        assert not signal_tight_floor.equals(signal_loose_floor)

    def test_score_transformation_window_affects_output(
        self, sample_market_data: dict[str, pd.DataFrame]
    ) -> None:
        """Different score transformation window values produce different outputs."""
        from aponyx.config import (
            INDICATOR_TRANSFORMATION_PATH,
            SCORE_TRANSFORMATION_PATH,
            SIGNAL_CATALOG_PATH,
            SIGNAL_TRANSFORMATION_PATH,
        )
        from aponyx.models.registry import (
            IndicatorTransformationRegistry,
            ScoreTransformationRegistry,
            SignalRegistry,
            SignalTransformationRegistry,
        )
        from aponyx.models.signal_composer import compose_signal

        indicator_registry = IndicatorTransformationRegistry(
            INDICATOR_TRANSFORMATION_PATH
        )
        score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
        signal_transformation_registry = SignalTransformationRegistry(
            SIGNAL_TRANSFORMATION_PATH
        )
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Compose signal with short lookback window
        signal_short_window = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=indicator_registry,
            score_registry=score_registry,
            signal_transformation_registry=signal_transformation_registry,
            signal_registry=signal_registry,
            score_params_override={"window": 10, "min_periods": 5},
        )

        # Compose signal with long lookback window
        signal_long_window = compose_signal(
            signal_name="cdx_etf_basis",
            market_data=sample_market_data,
            indicator_registry=indicator_registry,
            score_registry=score_registry,
            signal_transformation_registry=signal_transformation_registry,
            signal_registry=signal_registry,
            score_params_override={"window": 50, "min_periods": 25},
        )

        # Different windows should produce different z-scores
        # Compare at a point where both have valid values
        common_idx = signal_short_window.dropna().index.intersection(
            signal_long_window.dropna().index
        )
        assert len(common_idx) > 0
        assert not signal_short_window.loc[common_idx].equals(
            signal_long_window.loc[common_idx]
        )


class TestEvaluateBacktestWithOverrides:
    """Tests for evaluate_backtest with transformation parameter overrides.

    Note: These tests require full infrastructure (market data, catalogs).
    They are marked as integration tests.
    """

    @pytest.mark.integration
    def test_different_floor_cap_produce_different_metrics(self) -> None:
        """Verify that different floor/cap values produce different backtest metrics.

        This is the key regression test for the bug where floor/cap overrides
        were recorded but never applied.
        """
        from aponyx.sweep.evaluators import evaluate_backtest

        config = SweepConfig(
            name="test_sweep",
            description="Test sweep for floor/cap overrides",
            mode="backtest",
            base=BaseConfig(signal="cdx_etf_basis", strategy="balanced"),
            parameters=(
                ParameterOverride(
                    path="signal_transformation.parameters.cap",
                    values=(0.5, 2.0),
                ),
            ),
        )

        # Evaluate with low cap
        metrics_low_cap = evaluate_backtest(
            config,
            {"signal_transformation.parameters.cap": 0.5},
        )

        # Evaluate with high cap
        metrics_high_cap = evaluate_backtest(
            config,
            {"signal_transformation.parameters.cap": 2.0},
        )

        # The metrics should be different if cap is actually applied
        # At minimum, check that they're not identical
        assert (
            metrics_low_cap.sharpe_ratio != metrics_high_cap.sharpe_ratio
            or metrics_low_cap.total_return != metrics_high_cap.total_return
            or metrics_low_cap.max_drawdown != metrics_high_cap.max_drawdown
        ), "Different cap values should produce different backtest metrics"

    @pytest.mark.integration
    def test_strategy_overrides_still_work(self) -> None:
        """Verify that strategy parameter overrides continue to work."""
        from aponyx.sweep.evaluators import evaluate_backtest

        config = SweepConfig(
            name="test_sweep",
            description="Test sweep for strategy overrides",
            mode="backtest",
            base=BaseConfig(signal="cdx_etf_basis", strategy="balanced"),
            parameters=(
                ParameterOverride(
                    path="strategy.position_size_mm",
                    values=(5.0, 20.0),
                ),
            ),
        )

        # Evaluate with small position size
        metrics_small = evaluate_backtest(
            config,
            {"strategy.position_size_mm": 5.0},
        )

        # Evaluate with large position size
        metrics_large = evaluate_backtest(
            config,
            {"strategy.position_size_mm": 20.0},
        )

        # Larger position size should produce different (scaled) returns
        assert metrics_small.total_return != metrics_large.total_return


class TestBloombergDataSync:
    """Tests for Bloomberg data syncing behavior."""

    def test_bloomberg_fetches_all_securities(self, monkeypatch) -> None:
        """
        When using Bloomberg data source, ALL securities should be fetched
        regardless of which ones are required for the specific indicator.
        """
        from aponyx.sweep.evaluators import _load_market_data_for_signal
        from aponyx.models.registry import (
            IndicatorTransformationRegistry,
            SignalRegistry,
        )
        from aponyx.config import (
            INDICATOR_TRANSFORMATION_PATH,
            SIGNAL_CATALOG_PATH,
        )

        # Track fetch calls
        fetch_calls = []
        
        def mock_fetch(source, security_id, channels, use_cache):
            fetch_calls.append(security_id)
            return pd.DataFrame(
                {"spread": [100, 101, 102]},
                index=pd.date_range("2024-01-01", periods=3),
            )

        def mock_list_channels(security_id):
            return []  # Simplified for test

        def mock_list_securities(instrument_type=None):
            return ["cdx_ig_5y", "cdx_hy_5y", "hyg", "lqd", "vix"]

        # Patch in the aponyx.data module where they're imported from
        import aponyx.data
        import aponyx.data.bloomberg_config
        monkeypatch.setattr(
            aponyx.data, "fetch_security_data", mock_fetch
        )
        monkeypatch.setattr(
            aponyx.data, "list_security_channels", mock_list_channels
        )
        monkeypatch.setattr(
            aponyx.data.bloomberg_config, "list_securities", mock_list_securities
        )

        # Load registries
        indicator_registry = IndicatorTransformationRegistry(
            INDICATOR_TRANSFORMATION_PATH
        )
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Call with Bloomberg source
        _load_market_data_for_signal(
            signal_name="cdx_etf_basis",  # This indicator only needs cdx and etf
            indicator_registry=indicator_registry,
            signal_registry=signal_registry,
            data_source="bloomberg",
        )

        # Verify that ALL 5 securities were fetched (not just cdx and etf)
        # We expect: 5 from all_securities loop + 2 from required securities
        assert len(fetch_calls) == 7  # 5 all securities + 2 required
        
        # Verify all securities were fetched in the initial sync
        all_fetched_ids = set(fetch_calls[:5])
        assert all_fetched_ids == {"cdx_ig_5y", "cdx_hy_5y", "hyg", "lqd", "vix"}

    def test_file_source_only_fetches_required_securities(self, monkeypatch) -> None:
        """
        When using file data source, only required securities should be fetched.
        """
        from aponyx.sweep.evaluators import _load_market_data_for_signal
        from aponyx.models.registry import (
            IndicatorTransformationRegistry,
            SignalRegistry,
        )
        from aponyx.config import (
            INDICATOR_TRANSFORMATION_PATH,
            SIGNAL_CATALOG_PATH,
        )

        # Track fetch calls
        fetch_calls = []
        
        def mock_fetch(source, security_id, channels, use_cache):
            fetch_calls.append(security_id)
            return pd.DataFrame(
                {"spread": [100, 101, 102]},
                index=pd.date_range("2024-01-01", periods=3),
            )

        def mock_list_channels(security_id):
            return []  # Simplified for test

        # Patch in the aponyx.data module
        import aponyx.data
        monkeypatch.setattr(
            aponyx.data, "fetch_security_data", mock_fetch
        )
        monkeypatch.setattr(
            aponyx.data, "list_security_channels", mock_list_channels
        )

        # Load registries
        indicator_registry = IndicatorTransformationRegistry(
            INDICATOR_TRANSFORMATION_PATH
        )
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

        # Call with file source
        _load_market_data_for_signal(
            signal_name="cdx_etf_basis",  # This indicator only needs cdx and etf
            indicator_registry=indicator_registry,
            signal_registry=signal_registry,
            data_source="synthetic",
        )

        # Verify that only 2 securities were fetched (cdx and etf for the indicator)
        assert len(fetch_calls) == 2
