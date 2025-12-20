"""Deterministic test scenarios with predictable evaluation properties.

Generates synthetic signal and spread data designed to produce known outcomes
in backtest and evaluation metrics. Each scenario is labeled with its expected
behavior for verification in tests.

Usage
-----
For backtest testing:
    >>> from aponyx.data.test_scenarios import get_scenario
    >>> scenario = get_scenario("profitable_long")
    >>> result = run_backtest(scenario.signal, scenario.spread, config)
    >>> assert result.pnl["cumulative_pnl"].iloc[-1] > 0

For evaluation testing:
    >>> scenario = get_scenario("high_correlation")
    >>> correlation = compute_correlation(scenario.signal, scenario.target)
    >>> assert correlation > 0.9

Available scenarios:
    - profitable_long: Long signal with tightening spreads (positive P&L)
    - profitable_short: Short signal with widening spreads (positive P&L)
    - unprofitable_long: Long signal with widening spreads (negative P&L)
    - unprofitable_short: Short signal with tightening spreads (negative P&L)
    - high_correlation: Signal highly correlated with target
    - low_correlation: Signal uncorrelated with target
    - negative_correlation: Signal negatively correlated with target
    - stable_beta: Consistent signal-target relationship over time
    - unstable_beta: Varying signal-target relationship over time
    - few_trades: Sparse signal triggers (< 5 trades)
    - many_trades: Frequent signal triggers (> 20 trades)
    - short_lag: Signal leads target by 1 day
    - long_lag: Signal leads target by 5 days
    - stop_loss_trigger: Signal/spread combo that triggers stop loss
    - take_profit_trigger: Signal/spread combo that triggers take profit
    - max_holding_trigger: Long continuous signal for max_holding_days exit
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TestScenario:
    """Container for deterministic test scenario data.

    Attributes
    ----------
    name : str
        Scenario identifier.
    description : str
        Human-readable description of expected behavior.
    signal : pd.Series
        Signal time series with DatetimeIndex.
    spread : pd.Series
        CDX spread time series with DatetimeIndex.
    target : pd.Series | None
        Target time series for suitability evaluation.
        Same as -spread.diff() if not specified (spread tightening = positive).
    expected : dict[str, Any]
        Dictionary of expected outcomes for verification.
        Keys vary by scenario type (e.g., "pnl_positive", "correlation_range").
    """

    name: str
    description: str
    signal: pd.Series
    spread: pd.Series
    target: pd.Series | None
    expected: dict[str, Any]


def _make_dates(n_days: int, start: str = "2024-01-01") -> pd.DatetimeIndex:
    """Create business day date range."""
    return pd.bdate_range(start=start, periods=n_days)


# =============================================================================
# Backtest P&L Scenarios
# =============================================================================


def make_profitable_long(n_days: int = 100) -> TestScenario:
    """Long signal with consistent spread tightening → positive P&L.

    Signal is positive (long) throughout, and spreads tighten steadily.
    Expected: Large positive cumulative P&L.
    """
    dates = _make_dates(n_days)

    # Constant positive signal (long position)
    signal = pd.Series([1.0] * n_days, index=dates, name="signal")

    # Spreads tighten from 100 to 80 over the period
    spread = pd.Series(
        np.linspace(100.0, 80.0, n_days),
        index=dates,
        name="spread",
    )

    # Target = negative spread change (tightening is positive)
    target = -spread.diff().fillna(0)

    return TestScenario(
        name="profitable_long",
        description="Long signal with tightening spreads produces positive P&L",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "pnl_positive": True,
            "min_cumulative_pnl": 5000,  # Depends on config
            "final_position": 1,  # Still long at end
        },
    )


def make_profitable_short(n_days: int = 100) -> TestScenario:
    """Short signal with consistent spread widening → positive P&L.

    Signal is negative (short) throughout, and spreads widen steadily.
    Expected: Large positive cumulative P&L.
    """
    dates = _make_dates(n_days)

    # Constant negative signal (short position)
    signal = pd.Series([-1.0] * n_days, index=dates, name="signal")

    # Spreads widen from 100 to 120 over the period
    spread = pd.Series(
        np.linspace(100.0, 120.0, n_days),
        index=dates,
        name="spread",
    )

    # Target = negative spread change (widening is negative)
    target = -spread.diff().fillna(0)

    return TestScenario(
        name="profitable_short",
        description="Short signal with widening spreads produces positive P&L",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "pnl_positive": True,
            "min_cumulative_pnl": 5000,
            "final_position": -1,
        },
    )


def make_unprofitable_long(n_days: int = 100) -> TestScenario:
    """Long signal with consistent spread widening → negative P&L.

    Signal is positive (long) throughout, but spreads widen (bad for long).
    Expected: Large negative cumulative P&L.
    """
    dates = _make_dates(n_days)

    signal = pd.Series([1.0] * n_days, index=dates, name="signal")

    # Spreads widen from 100 to 120
    spread = pd.Series(
        np.linspace(100.0, 120.0, n_days),
        index=dates,
        name="spread",
    )

    target = -spread.diff().fillna(0)

    return TestScenario(
        name="unprofitable_long",
        description="Long signal with widening spreads produces negative P&L",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "pnl_positive": False,
            "max_cumulative_pnl": -5000,
        },
    )


def make_unprofitable_short(n_days: int = 100) -> TestScenario:
    """Short signal with consistent spread tightening → negative P&L.

    Signal is negative (short) throughout, but spreads tighten (bad for short).
    Expected: Large negative cumulative P&L.
    """
    dates = _make_dates(n_days)

    signal = pd.Series([-1.0] * n_days, index=dates, name="signal")

    # Spreads tighten from 100 to 80
    spread = pd.Series(
        np.linspace(100.0, 80.0, n_days),
        index=dates,
        name="spread",
    )

    target = -spread.diff().fillna(0)

    return TestScenario(
        name="unprofitable_short",
        description="Short signal with tightening spreads produces negative P&L",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "pnl_positive": False,
            "max_cumulative_pnl": -5000,
        },
    )


# =============================================================================
# Correlation/Suitability Scenarios
# =============================================================================


def make_high_correlation(n_days: int = 252) -> TestScenario:
    """Signal perfectly tracks target → correlation ≈ 1.0.

    Signal is constructed as target + small noise for near-perfect correlation.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    # Create target as random walk changes
    target_values = rng.normal(0, 1, n_days)
    target = pd.Series(target_values, index=dates, name="target")

    # Signal is target with minimal noise (correlation > 0.95)
    noise = rng.normal(0, 0.1, n_days)
    signal = pd.Series(target_values + noise, index=dates, name="signal")

    # Spread from cumulative target (for backtest compatibility)
    spread = pd.Series(100 - target.cumsum(), index=dates, name="spread")

    return TestScenario(
        name="high_correlation",
        description="Signal highly correlated with target (r > 0.95)",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "correlation_min": 0.95,
            "correlation_max": 1.0,
            "r_squared_min": 0.9,
        },
    )


def make_low_correlation(n_days: int = 252) -> TestScenario:
    """Signal independent of target → correlation ≈ 0.0.

    Signal and target are independent random series.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    # Independent random series
    target = pd.Series(rng.normal(0, 1, n_days), index=dates, name="target")
    signal = pd.Series(rng.normal(0, 1, n_days), index=dates, name="signal")

    spread = pd.Series(100 - target.cumsum(), index=dates, name="spread")

    return TestScenario(
        name="low_correlation",
        description="Signal uncorrelated with target (|r| < 0.1)",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "correlation_min": -0.15,
            "correlation_max": 0.15,
        },
    )


def make_negative_correlation(n_days: int = 252) -> TestScenario:
    """Signal inversely tracks target → correlation ≈ -1.0.

    Signal is negative of target + small noise.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    target_values = rng.normal(0, 1, n_days)
    target = pd.Series(target_values, index=dates, name="target")

    # Signal is negative of target
    noise = rng.normal(0, 0.1, n_days)
    signal = pd.Series(-target_values + noise, index=dates, name="signal")

    spread = pd.Series(100 - target.cumsum(), index=dates, name="spread")

    return TestScenario(
        name="negative_correlation",
        description="Signal negatively correlated with target (r < -0.95)",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "correlation_min": -1.0,
            "correlation_max": -0.95,
        },
    )


# =============================================================================
# Stability Scenarios
# =============================================================================


def make_stable_beta(n_days: int = 504) -> TestScenario:
    """Signal-target relationship stable over time → high sign consistency.

    Beta coefficient remains positive and stable across rolling windows.
    Uses 2 years of data for meaningful rolling window analysis.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    # Create stable relationship: target = 2 * signal + noise
    signal_values = rng.normal(0, 1, n_days)
    signal = pd.Series(signal_values, index=dates, name="signal")

    # Stable beta of ~2.0 with moderate noise
    noise = rng.normal(0, 0.5, n_days)
    target = pd.Series(2.0 * signal_values + noise, index=dates, name="target")

    spread = pd.Series(100 - target.cumsum() / 10, index=dates, name="spread")

    return TestScenario(
        name="stable_beta",
        description="Consistent signal-target beta over time (sign consistency > 0.9)",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "sign_consistency_min": 0.9,
            "beta_cv_max": 0.3,
            "beta_positive": True,
        },
    )


def make_unstable_beta(n_days: int = 504) -> TestScenario:
    """Signal-target relationship varies over time → low sign consistency.

    Beta coefficient changes sign periodically across the sample.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    signal_values = rng.normal(0, 1, n_days)
    signal = pd.Series(signal_values, index=dates, name="signal")

    # Time-varying beta: positive in first half, negative in second half
    beta = np.where(np.arange(n_days) < n_days // 2, 2.0, -2.0)
    noise = rng.normal(0, 0.3, n_days)
    target_values = beta * signal_values + noise
    target = pd.Series(target_values, index=dates, name="target")

    spread = pd.Series(100 - target.cumsum() / 10, index=dates, name="spread")

    return TestScenario(
        name="unstable_beta",
        description="Varying signal-target relationship (sign consistency < 0.6)",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "sign_consistency_max": 0.6,
            "beta_cv_min": 1.0,
        },
    )


# =============================================================================
# Trade Frequency Scenarios
# =============================================================================


def make_few_trades(n_days: int = 252) -> TestScenario:
    """Sparse signal triggers → few trades.

    Signal is zero most of the time with only 3 short bursts of activity.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    # Signal is zero except for 3 short periods
    signal_values = np.zeros(n_days)
    # Trade 1: days 20-30
    signal_values[20:30] = 1.0
    # Trade 2: days 80-90
    signal_values[80:90] = -1.0
    # Trade 3: days 180-190
    signal_values[180:190] = 0.5

    signal = pd.Series(signal_values, index=dates, name="signal")

    # Random walk spread
    spread_changes = rng.normal(0, 0.5, n_days)
    spread = pd.Series(100 + np.cumsum(spread_changes), index=dates, name="spread")

    target = -spread.diff().fillna(0)

    return TestScenario(
        name="few_trades",
        description="Sparse signal triggers producing < 5 trades",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "n_trades_min": 1,
            "n_trades_max": 5,
            "mostly_flat": True,
        },
    )


def make_many_trades(n_days: int = 252) -> TestScenario:
    """Frequent signal triggers → many trades.

    Signal oscillates between long, flat, and short with short holding periods.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    # Create oscillating pattern: 5 days long, 3 days flat, 5 days short, 3 days flat
    cycle_length = 16
    n_cycles = n_days // cycle_length + 1
    pattern = [1.0] * 5 + [0.0] * 3 + [-1.0] * 5 + [0.0] * 3
    signal_values = (pattern * n_cycles)[:n_days]

    # Add small variation to signal magnitude
    signal_values = np.array(signal_values) * (1 + rng.uniform(-0.1, 0.1, n_days))

    signal = pd.Series(signal_values, index=dates, name="signal")

    spread_changes = rng.normal(0, 0.5, n_days)
    spread = pd.Series(100 + np.cumsum(spread_changes), index=dates, name="spread")

    target = -spread.diff().fillna(0)

    return TestScenario(
        name="many_trades",
        description="Frequent signal triggers producing > 20 trades",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "n_trades_min": 20,
            "high_turnover": True,
        },
    )


# =============================================================================
# Signal Lag Scenarios
# =============================================================================


def make_short_lag(n_days: int = 100) -> TestScenario:
    """Signal leads target by 1 day → predictive with short lag.

    Target is lagged version of signal, demonstrating 1-day predictability.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    signal_values = rng.normal(0, 1, n_days)
    signal = pd.Series(signal_values, index=dates, name="signal")

    # Target is signal shifted forward by 1 day (signal leads)
    target_values = np.concatenate([[0], signal_values[:-1]])
    noise = rng.normal(0, 0.1, n_days)
    target = pd.Series(target_values + noise, index=dates, name="target")

    # Spread follows signal with 1-day lag
    spread_changes = -signal_values * 0.5  # Positive signal → tightening
    spread = pd.Series(100 + np.cumsum(spread_changes), index=dates, name="spread")

    return TestScenario(
        name="short_lag",
        description="Signal leads target by 1 day (optimal signal_lag=1)",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "optimal_lag": 1,
            "lagged_correlation_min": 0.9,
        },
    )


def make_long_lag(n_days: int = 100) -> TestScenario:
    """Signal leads target by 5 days → predictive with longer lag.

    Target is lagged version of signal, demonstrating 5-day predictability.
    """
    dates = _make_dates(n_days)
    rng = np.random.default_rng(42)

    signal_values = rng.normal(0, 1, n_days)
    signal = pd.Series(signal_values, index=dates, name="signal")

    # Target is signal shifted forward by 5 days
    lag = 5
    target_values = np.concatenate([np.zeros(lag), signal_values[:-lag]])
    noise = rng.normal(0, 0.1, n_days)
    target = pd.Series(target_values + noise, index=dates, name="target")

    # Spread follows signal with 5-day lag
    spread_changes = np.concatenate([np.zeros(lag), -signal_values[:-lag] * 0.5])
    spread = pd.Series(100 + np.cumsum(spread_changes), index=dates, name="spread")

    return TestScenario(
        name="long_lag",
        description="Signal leads target by 5 days (optimal signal_lag=5)",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "optimal_lag": 5,
            "lagged_correlation_min": 0.9,
        },
    )


# =============================================================================
# Risk Management Trigger Scenarios
# =============================================================================


def make_stop_loss_trigger(n_days: int = 50) -> TestScenario:
    """Signal and spread designed to trigger stop loss.

    Long signal with sharp spread widening to exceed stop loss threshold.
    Configured for 5% stop loss with 10MM position and 475 DV01.
    """
    dates = _make_dates(n_days)

    # Long signal throughout
    signal = pd.Series([1.0] * n_days, index=dates, name="signal")

    # Sharp spread widening to trigger 5% stop loss
    # P&L = -position * spread_change * DV01 = -10MM * delta_spread * 475
    # For 5% loss on $10MM × $475 = $4,750,000 exposure: need loss of $237,500
    # That requires spread widening of 237,500 / (10 × 475) = ~50 bps
    spread_values = np.concatenate(
        [
            np.full(10, 100.0),  # Flat for entry
            np.linspace(100.0, 160.0, 30),  # Sharp widening (60 bps)
            np.full(10, 160.0),  # Flat after
        ]
    )

    spread = pd.Series(spread_values, index=dates, name="spread")
    target = -spread.diff().fillna(0)

    return TestScenario(
        name="stop_loss_trigger",
        description="Spread widening triggers stop loss exit",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "stop_loss_triggered": True,
            "exit_before_end": True,
        },
    )


def make_take_profit_trigger(n_days: int = 50) -> TestScenario:
    """Signal and spread designed to trigger take profit.

    Long signal with sharp spread tightening to exceed take profit threshold.
    """
    dates = _make_dates(n_days)

    signal = pd.Series([1.0] * n_days, index=dates, name="signal")

    # Sharp spread tightening to trigger take profit
    spread_values = np.concatenate(
        [
            np.full(10, 100.0),  # Flat for entry
            np.linspace(100.0, 40.0, 30),  # Sharp tightening (60 bps)
            np.full(10, 40.0),  # Flat after
        ]
    )

    spread = pd.Series(spread_values, index=dates, name="spread")
    target = -spread.diff().fillna(0)

    return TestScenario(
        name="take_profit_trigger",
        description="Spread tightening triggers take profit exit",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "take_profit_triggered": True,
            "exit_before_end": True,
            "pnl_positive": True,
        },
    )


def make_max_holding_trigger(n_days: int = 50) -> TestScenario:
    """Long continuous signal to trigger max_holding_days exit.

    Flat spread so no P&L-based exits, only max holding days.
    """
    dates = _make_dates(n_days)

    # Continuous non-zero signal
    signal = pd.Series([0.8] * n_days, index=dates, name="signal")

    # Flat spread (no P&L triggers)
    spread = pd.Series([100.0] * n_days, index=dates, name="spread")

    target = pd.Series([0.0] * n_days, index=dates, name="target")

    return TestScenario(
        name="max_holding_trigger",
        description="Continuous signal triggers max_holding_days exit",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "max_holding_triggered": True,
            "spread_pnl_zero": True,
        },
    )


# =============================================================================
# Mixed Outcome Scenarios
# =============================================================================


def make_alternating_outcomes(n_days: int = 200) -> TestScenario:
    """Mix of winning and losing trades for hit rate testing.

    Signal alternates between profitable and unprofitable regimes.
    Expected: ~50% hit rate.
    """
    dates = _make_dates(n_days)

    # 4 trades: win, loss, win, loss
    signal_values = np.concatenate(
        [
            np.zeros(10),  # Flat
            np.ones(20),  # Trade 1: Long
            np.zeros(10),  # Flat
            np.ones(20),  # Trade 2: Long
            np.zeros(10),  # Flat
            np.ones(20),  # Trade 3: Long
            np.zeros(10),  # Flat
            np.ones(20),  # Trade 4: Long
            np.zeros(80),  # Remaining flat
        ]
    )[:n_days]

    signal = pd.Series(signal_values, index=dates, name="signal")

    # Spread: tighten for trades 1,3 (wins), widen for trades 2,4 (losses)
    spread_values = np.concatenate(
        [
            np.full(10, 100.0),  # Flat before trade 1
            np.linspace(100.0, 90.0, 20),  # Trade 1: tighten (win)
            np.full(10, 90.0),  # Flat
            np.linspace(90.0, 105.0, 20),  # Trade 2: widen (loss)
            np.full(10, 105.0),  # Flat
            np.linspace(105.0, 95.0, 20),  # Trade 3: tighten (win)
            np.full(10, 95.0),  # Flat
            np.linspace(95.0, 110.0, 20),  # Trade 4: widen (loss)
            np.full(80, 110.0),  # Remaining flat
        ]
    )[:n_days]

    spread = pd.Series(spread_values, index=dates, name="spread")
    target = -spread.diff().fillna(0)

    return TestScenario(
        name="alternating_outcomes",
        description="Alternating win/loss trades for ~50% hit rate",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "hit_rate_min": 0.4,
            "hit_rate_max": 0.6,
            "n_trades": 4,
        },
    )


def make_high_hit_rate(n_days: int = 200) -> TestScenario:
    """Mostly winning trades for high hit rate testing.

    Most trades are winners, few losers.
    Expected: ~80% hit rate.
    """
    dates = _make_dates(n_days)

    # 5 trades: 4 wins, 1 loss
    n_days // 10
    signal_values = np.zeros(n_days)

    # 5 trades of ~20 days each with gaps
    for i, start in enumerate([10, 50, 90, 130, 170]):
        end = min(start + 15, n_days)
        signal_values[start:end] = 1.0

    signal = pd.Series(signal_values, index=dates, name="signal")

    # Spread: tighten for 4 trades, widen for 1
    spread_values = np.full(n_days, 100.0)
    # Trade 1: win (tighten)
    spread_values[10:25] = np.linspace(100, 92, 15)
    spread_values[25:50] = 92
    # Trade 2: win
    spread_values[50:65] = np.linspace(92, 85, 15)
    spread_values[65:90] = 85
    # Trade 3: loss (widen)
    spread_values[90:105] = np.linspace(85, 98, 15)
    spread_values[105:130] = 98
    # Trade 4: win
    spread_values[130:145] = np.linspace(98, 90, 15)
    spread_values[145:170] = 90
    # Trade 5: win
    spread_values[170:185] = np.linspace(90, 82, 15)
    spread_values[185:] = 82

    spread = pd.Series(spread_values, index=dates, name="spread")
    target = -spread.diff().fillna(0)

    return TestScenario(
        name="high_hit_rate",
        description="Mostly winning trades for ~80% hit rate",
        signal=signal,
        spread=spread,
        target=target,
        expected={
            "hit_rate_min": 0.75,
            "hit_rate_max": 0.9,
            "n_trades_min": 4,
        },
    )


# =============================================================================
# Registry and Access Functions
# =============================================================================


_SCENARIO_REGISTRY: dict[str, Callable[..., TestScenario]] = {
    # P&L scenarios
    "profitable_long": make_profitable_long,
    "profitable_short": make_profitable_short,
    "unprofitable_long": make_unprofitable_long,
    "unprofitable_short": make_unprofitable_short,
    # Correlation scenarios
    "high_correlation": make_high_correlation,
    "low_correlation": make_low_correlation,
    "negative_correlation": make_negative_correlation,
    # Stability scenarios
    "stable_beta": make_stable_beta,
    "unstable_beta": make_unstable_beta,
    # Trade frequency scenarios
    "few_trades": make_few_trades,
    "many_trades": make_many_trades,
    # Lag scenarios
    "short_lag": make_short_lag,
    "long_lag": make_long_lag,
    # Risk management scenarios
    "stop_loss_trigger": make_stop_loss_trigger,
    "take_profit_trigger": make_take_profit_trigger,
    "max_holding_trigger": make_max_holding_trigger,
    # Mixed outcome scenarios
    "alternating_outcomes": make_alternating_outcomes,
    "high_hit_rate": make_high_hit_rate,
}


def get_scenario(name: str, **kwargs) -> TestScenario:
    """Get a test scenario by name.

    Parameters
    ----------
    name : str
        Scenario name from the registry.
    **kwargs
        Additional arguments passed to the scenario factory (e.g., n_days).

    Returns
    -------
    TestScenario
        Scenario with signal, spread, target, and expected outcomes.

    Raises
    ------
    ValueError
        If scenario name is not recognized.

    Examples
    --------
    >>> scenario = get_scenario("profitable_long")
    >>> scenario = get_scenario("high_correlation", n_days=500)
    """
    if name not in _SCENARIO_REGISTRY:
        available = ", ".join(sorted(_SCENARIO_REGISTRY.keys()))
        raise ValueError(f"Unknown scenario: {name}. Available: {available}")

    factory = _SCENARIO_REGISTRY[name]
    return factory(**kwargs)


def list_scenarios() -> list[str]:
    """List all available test scenario names.

    Returns
    -------
    list[str]
        Sorted list of scenario names.
    """
    return sorted(_SCENARIO_REGISTRY.keys())


def get_all_scenarios(**kwargs) -> dict[str, TestScenario]:
    """Get all test scenarios.

    Parameters
    ----------
    **kwargs
        Arguments passed to all scenario factories (e.g., n_days).

    Returns
    -------
    dict[str, TestScenario]
        Dictionary mapping scenario names to TestScenario objects.
    """
    return {name: get_scenario(name, **kwargs) for name in _SCENARIO_REGISTRY}
