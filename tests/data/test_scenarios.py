"""
Tests for deterministic test scenarios module.

Validates that each scenario produces expected outcomes when used with
backtest engine and evaluation functions.
"""

import numpy as np
import pandas as pd
import pytest

from aponyx.data.test_scenarios import (
    TestScenario,
    get_all_scenarios,
    get_scenario,
    list_scenarios,
)


class TestScenarioRegistry:
    """Test scenario registry functions."""

    def test_list_scenarios_returns_all(self) -> None:
        """Test that list_scenarios returns all registered scenarios."""
        scenarios = list_scenarios()
        assert len(scenarios) >= 18
        assert "profitable_long" in scenarios
        assert "high_correlation" in scenarios
        assert "many_trades" in scenarios

    def test_get_scenario_valid_name(self) -> None:
        """Test getting a scenario by valid name."""
        scenario = get_scenario("profitable_long")
        assert isinstance(scenario, TestScenario)
        assert scenario.name == "profitable_long"

    def test_get_scenario_invalid_name(self) -> None:
        """Test that invalid name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown scenario"):
            get_scenario("nonexistent_scenario")

    def test_get_scenario_with_kwargs(self) -> None:
        """Test passing kwargs to scenario factory."""
        scenario = get_scenario("profitable_long", n_days=50)
        assert len(scenario.signal) == 50
        assert len(scenario.spread) == 50

    def test_get_all_scenarios(self) -> None:
        """Test getting all scenarios at once."""
        all_scenarios = get_all_scenarios()
        assert len(all_scenarios) >= 18
        assert all(isinstance(s, TestScenario) for s in all_scenarios.values())


class TestScenarioStructure:
    """Test that all scenarios have correct structure."""

    @pytest.fixture
    def all_scenario_names(self) -> list[str]:
        return list_scenarios()

    def test_all_scenarios_have_required_fields(
        self, all_scenario_names: list[str]
    ) -> None:
        """Test that all scenarios have required fields."""
        for name in all_scenario_names:
            scenario = get_scenario(name)
            assert scenario.name == name
            assert isinstance(scenario.description, str)
            assert len(scenario.description) > 10
            assert isinstance(scenario.signal, pd.Series)
            assert isinstance(scenario.spread, pd.Series)
            assert isinstance(scenario.expected, dict)

    def test_all_scenarios_have_datetime_index(
        self, all_scenario_names: list[str]
    ) -> None:
        """Test that all scenarios use DatetimeIndex."""
        for name in all_scenario_names:
            scenario = get_scenario(name)
            assert isinstance(scenario.signal.index, pd.DatetimeIndex)
            assert isinstance(scenario.spread.index, pd.DatetimeIndex)

    def test_all_scenarios_have_aligned_dates(
        self, all_scenario_names: list[str]
    ) -> None:
        """Test that signal and spread have same index."""
        for name in all_scenario_names:
            scenario = get_scenario(name)
            pd.testing.assert_index_equal(scenario.signal.index, scenario.spread.index)


class TestProfitabilityScenarios:
    """Test P&L-related scenarios."""

    def test_profitable_long_signal_positive(self) -> None:
        """Test profitable_long has positive signal values."""
        scenario = get_scenario("profitable_long")
        assert (scenario.signal > 0).all()

    def test_profitable_long_spread_decreasing(self) -> None:
        """Test profitable_long has decreasing spread."""
        scenario = get_scenario("profitable_long")
        assert scenario.spread.iloc[-1] < scenario.spread.iloc[0]

    def test_profitable_short_signal_negative(self) -> None:
        """Test profitable_short has negative signal values."""
        scenario = get_scenario("profitable_short")
        assert (scenario.signal < 0).all()

    def test_profitable_short_spread_increasing(self) -> None:
        """Test profitable_short has increasing spread."""
        scenario = get_scenario("profitable_short")
        assert scenario.spread.iloc[-1] > scenario.spread.iloc[0]

    def test_unprofitable_scenarios_have_opposite_dynamics(self) -> None:
        """Test unprofitable scenarios have wrong signal for spread direction."""
        # Unprofitable long: long signal with widening spread
        unprofitable_long = get_scenario("unprofitable_long")
        assert (unprofitable_long.signal > 0).all()
        assert unprofitable_long.spread.iloc[-1] > unprofitable_long.spread.iloc[0]

        # Unprofitable short: short signal with tightening spread
        unprofitable_short = get_scenario("unprofitable_short")
        assert (unprofitable_short.signal < 0).all()
        assert unprofitable_short.spread.iloc[-1] < unprofitable_short.spread.iloc[0]


class TestCorrelationScenarios:
    """Test correlation-related scenarios."""

    def test_high_correlation_scenario(self) -> None:
        """Test high_correlation produces high correlation."""
        scenario = get_scenario("high_correlation")
        assert scenario.target is not None
        corr = scenario.signal.corr(scenario.target)
        assert corr > 0.95

    def test_low_correlation_scenario(self) -> None:
        """Test low_correlation produces near-zero correlation."""
        scenario = get_scenario("low_correlation")
        assert scenario.target is not None
        corr = scenario.signal.corr(scenario.target)
        assert abs(corr) < 0.15

    def test_negative_correlation_scenario(self) -> None:
        """Test negative_correlation produces strong negative correlation."""
        scenario = get_scenario("negative_correlation")
        assert scenario.target is not None
        corr = scenario.signal.corr(scenario.target)
        assert corr < -0.95


class TestStabilityScenarios:
    """Test stability-related scenarios."""

    def test_stable_beta_produces_consistent_relationship(self) -> None:
        """Test stable_beta has consistent signal-target relationship."""
        import statsmodels.api as sm

        scenario = get_scenario("stable_beta")
        assert scenario.target is not None

        # Full-sample beta
        X = sm.add_constant(scenario.signal.values)
        model = sm.OLS(scenario.target.values, X).fit()
        full_beta = model.params[1]

        # Rolling betas (252-day windows)
        window = 252
        betas = []
        for i in range(window, len(scenario.signal)):
            X_window = sm.add_constant(scenario.signal.iloc[i - window : i].values)
            y_window = scenario.target.iloc[i - window : i].values
            window_model = sm.OLS(y_window, X_window).fit()
            betas.append(window_model.params[1])

        # Sign consistency should be high
        same_sign = sum(1 for b in betas if np.sign(b) == np.sign(full_beta))
        sign_consistency = same_sign / len(betas)
        assert sign_consistency > 0.9

    def test_unstable_beta_produces_varying_relationship(self) -> None:
        """Test unstable_beta has varying signal-target relationship."""
        import statsmodels.api as sm

        scenario = get_scenario("unstable_beta")
        assert scenario.target is not None

        # Rolling betas
        window = 252
        betas = []
        for i in range(window, len(scenario.signal)):
            X_window = sm.add_constant(scenario.signal.iloc[i - window : i].values)
            y_window = scenario.target.iloc[i - window : i].values
            window_model = sm.OLS(y_window, X_window).fit()
            betas.append(window_model.params[1])

        # Should have both positive and negative betas
        has_positive = any(b > 0.5 for b in betas)
        has_negative = any(b < -0.5 for b in betas)
        assert has_positive and has_negative


class TestTradeFrequencyScenarios:
    """Test trade frequency scenarios."""

    def test_few_trades_is_mostly_zero(self) -> None:
        """Test few_trades signal is mostly zero."""
        scenario = get_scenario("few_trades")
        zero_ratio = (scenario.signal == 0).sum() / len(scenario.signal)
        assert zero_ratio > 0.8

    def test_few_trades_has_expected_pattern(self) -> None:
        """Test few_trades has sparse signal bursts."""
        scenario = get_scenario("few_trades")
        # Count zero-to-nonzero transitions
        signal_changes = (scenario.signal != 0) & (scenario.signal.shift(1) == 0)
        n_entries = signal_changes.sum()
        assert n_entries <= 5

    def test_many_trades_oscillates(self) -> None:
        """Test many_trades signal oscillates frequently."""
        scenario = get_scenario("many_trades")
        # Count position changes (entry/exit transitions)
        position_changes = np.sign(scenario.signal) != np.sign(scenario.signal.shift(1))
        n_position_changes = position_changes.sum()
        # Should have at least 20 position changes for "many trades"
        assert n_position_changes > 20


class TestLagScenarios:
    """Test signal lag scenarios."""

    def test_short_lag_correlation(self) -> None:
        """Test short_lag signal leads target by 1 day."""
        scenario = get_scenario("short_lag")
        assert scenario.target is not None

        # Correlation with 1-day lagged target should be high
        target_lagged = scenario.target.shift(-1).dropna()
        signal_trimmed = scenario.signal.iloc[:-1]
        corr_lagged = signal_trimmed.corr(target_lagged)
        assert corr_lagged > 0.9

    def test_long_lag_correlation(self) -> None:
        """Test long_lag signal leads target by 5 days."""
        scenario = get_scenario("long_lag")
        assert scenario.target is not None

        # Correlation with 5-day lagged target should be high
        target_lagged = scenario.target.shift(-5).dropna()
        signal_trimmed = scenario.signal.iloc[:-5]
        # Need to align indexes
        common_idx = signal_trimmed.index.intersection(target_lagged.index)
        corr_lagged = signal_trimmed.loc[common_idx].corr(target_lagged.loc[common_idx])
        assert corr_lagged > 0.9


class TestRiskManagementScenarios:
    """Test risk management trigger scenarios."""

    def test_stop_loss_trigger_has_sharp_widening(self) -> None:
        """Test stop_loss_trigger spread widens sharply."""
        scenario = get_scenario("stop_loss_trigger")
        # Signal is long
        assert (scenario.signal > 0).all()
        # Spread widens significantly
        spread_change = scenario.spread.iloc[-1] - scenario.spread.iloc[0]
        assert spread_change > 50  # At least 50 bps widening

    def test_take_profit_trigger_has_sharp_tightening(self) -> None:
        """Test take_profit_trigger spread tightens sharply."""
        scenario = get_scenario("take_profit_trigger")
        # Signal is long
        assert (scenario.signal > 0).all()
        # Spread tightens significantly
        spread_change = scenario.spread.iloc[-1] - scenario.spread.iloc[0]
        assert spread_change < -50  # At least 50 bps tightening

    def test_max_holding_trigger_flat_spread(self) -> None:
        """Test max_holding_trigger has flat spread."""
        scenario = get_scenario("max_holding_trigger")
        # Spread should be constant
        spread_std = scenario.spread.std()
        assert spread_std < 0.01
        # Signal should be constant non-zero
        assert (scenario.signal != 0).all()


class TestMixedOutcomeScenarios:
    """Test mixed outcome scenarios."""

    def test_alternating_outcomes_structure(self) -> None:
        """Test alternating_outcomes has correct structure."""
        scenario = get_scenario("alternating_outcomes")
        # Should have 4 distinct signal periods
        signal_active = scenario.signal != 0
        transitions = signal_active.astype(int).diff().fillna(0) != 0
        # Transitions include both entry and exit
        n_transitions = transitions.sum()
        assert n_transitions >= 8  # 4 entries + 4 exits

    def test_high_hit_rate_mostly_profitable(self) -> None:
        """Test high_hit_rate has mostly profitable trades."""
        scenario = get_scenario("high_hit_rate")
        # Should have multiple signal periods
        signal_active = scenario.signal != 0
        assert signal_active.any()
        # Spread should generally trend down (for long positions = profitable)
        # Overall trend should be down
        assert scenario.spread.iloc[-1] < scenario.spread.iloc[0]


class TestBacktestIntegration:
    """Integration tests using actual backtest engine."""

    @pytest.fixture
    def make_config(self):
        """Create backtest config for testing."""
        from aponyx.backtest.config import BacktestConfig

        def _make_config(**kwargs):
            defaults = {
                "position_size_mm": 10.0,
                "sizing_mode": "binary",
                "signal_lag": 0,
                "transaction_cost_bps": 0.0,
                "stop_loss_pct": None,
                "take_profit_pct": None,
                "max_holding_days": None,
                "entry_threshold": None,
            }
            defaults.update(kwargs)
            return BacktestConfig(**defaults)

        return _make_config

    @pytest.fixture
    def make_calculator(self):
        """Create spread return calculator for testing."""
        from aponyx.backtest.calculators import SpreadReturnCalculator

        def _make_calculator(dv01_per_million: float = 475.0):
            return SpreadReturnCalculator(dv01_per_million=dv01_per_million)

        return _make_calculator

    def test_profitable_long_produces_positive_pnl(
        self, make_config, make_calculator
    ) -> None:
        """Test profitable_long scenario produces positive P&L."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("profitable_long")
        config = make_config()

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.pnl["cumulative_pnl"].iloc[-1] > 0

    def test_profitable_short_produces_positive_pnl(
        self, make_config, make_calculator
    ) -> None:
        """Test profitable_short scenario produces positive P&L."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("profitable_short")
        config = make_config()

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.pnl["cumulative_pnl"].iloc[-1] > 0

    def test_unprofitable_long_produces_negative_pnl(
        self, make_config, make_calculator
    ) -> None:
        """Test unprofitable_long scenario produces negative P&L."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("unprofitable_long")
        config = make_config()

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.pnl["cumulative_pnl"].iloc[-1] < 0

    def test_unprofitable_short_produces_negative_pnl(
        self, make_config, make_calculator
    ) -> None:
        """Test unprofitable_short scenario produces negative P&L."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("unprofitable_short")
        config = make_config()

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.pnl["cumulative_pnl"].iloc[-1] < 0

    def test_few_trades_produces_few_trades(self, make_config, make_calculator) -> None:
        """Test few_trades scenario produces < 5 trades."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("few_trades")
        config = make_config()

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.metadata["summary"]["n_trades"] <= 5

    def test_many_trades_produces_many_trades(
        self, make_config, make_calculator
    ) -> None:
        """Test many_trades scenario produces > 20 trades."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("many_trades")
        config = make_config()

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.metadata["summary"]["n_trades"] >= 20

    def test_stop_loss_triggers_exit(self, make_config, make_calculator) -> None:
        """Test stop_loss_trigger scenario triggers stop loss exit."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("stop_loss_trigger")
        config = make_config(stop_loss_pct=5.0)

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.metadata["summary"]["exit_counts"]["stop_loss"] > 0

    def test_take_profit_triggers_exit(self, make_config, make_calculator) -> None:
        """Test take_profit_trigger scenario triggers take profit exit."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("take_profit_trigger")
        config = make_config(take_profit_pct=10.0)

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.metadata["summary"]["exit_counts"]["take_profit"] > 0

    def test_max_holding_triggers_exit(self, make_config, make_calculator) -> None:
        """Test max_holding_trigger scenario triggers max holding days exit."""
        from aponyx.backtest.engine import run_backtest

        scenario = get_scenario("max_holding_trigger")
        config = make_config(max_holding_days=10)

        result = run_backtest(
            scenario.signal, scenario.spread, config, make_calculator()
        )

        assert result.metadata["summary"]["exit_counts"]["max_holding_days"] > 0


class TestSuitabilityIntegration:
    """Integration tests using evaluation functions."""

    def test_high_correlation_evaluation(self) -> None:
        """Test high_correlation passes suitability correlation check."""
        from aponyx.evaluation.suitability.tests import compute_correlation

        scenario = get_scenario("high_correlation")
        corr = compute_correlation(scenario.signal, scenario.target)

        assert corr > 0.9

    def test_low_correlation_evaluation(self) -> None:
        """Test low_correlation fails suitability correlation check."""
        from aponyx.evaluation.suitability.tests import compute_correlation

        scenario = get_scenario("low_correlation")
        corr = compute_correlation(scenario.signal, scenario.target)

        assert abs(corr) < 0.2

    def test_stable_beta_regression_stats(self) -> None:
        """Test stable_beta produces significant regression stats."""
        from aponyx.evaluation.suitability.tests import compute_regression_stats

        scenario = get_scenario("stable_beta")
        stats = compute_regression_stats(scenario.signal, scenario.target)

        assert stats["r_squared"] > 0.8
        assert stats["p_value"] < 0.01
