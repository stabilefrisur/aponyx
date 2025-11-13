"""
Core performance analyzer for backtest results.

Orchestrates comprehensive performance evaluation including extended metrics,
subperiod stability analysis, return attribution, and interpretive summaries.
"""

import logging
from datetime import datetime
from typing import Any

import pandas as pd

from aponyx import __version__
from aponyx.backtest import BacktestResult

from .config import PerformanceConfig, PerformanceMetrics, PerformanceResult
from .decomposition import compute_attribution
from .metrics import compute_all_metrics

logger = logging.getLogger(__name__)


def _split_into_subperiods(
    df: pd.DataFrame,
    n_subperiods: int,
) -> list[pd.DataFrame]:
    """
    Split DataFrame into n equal subperiods.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with DatetimeIndex to split.
    n_subperiods : int
        Number of equal subperiods.

    Returns
    -------
    list[pd.DataFrame]
        List of n DataFrame subperiods.

    Notes
    -----
    Uses integer division to ensure equal sizes.
    Last subperiod may be slightly larger if length not divisible.
    """
    total_len = len(df)
    period_len = total_len // n_subperiods

    subperiods = []
    for i in range(n_subperiods):
        start_idx = i * period_len
        if i == n_subperiods - 1:
            # Last period gets remainder
            end_idx = total_len
        else:
            end_idx = (i + 1) * period_len

        subperiods.append(df.iloc[start_idx:end_idx])

    return subperiods


def _compute_subperiod_metrics(
    pnl_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    n_subperiods: int,
    rolling_window: int = 63,
) -> dict[str, Any]:
    """
    Compute comprehensive metrics for each subperiod using compute_all_metrics.

    Parameters
    ----------
    pnl_df : pd.DataFrame
        P&L DataFrame with 'net_pnl' and 'cumulative_pnl' columns.
    positions_df : pd.DataFrame
        Position DataFrame with 'position' and 'days_held' columns.
    n_subperiods : int
        Number of subperiods for analysis.
    rolling_window : int
        Rolling window for metrics computation. Default: 63.

    Returns
    -------
    dict[str, Any]
        Subperiod analysis with keys:
        - 'periods': List of PerformanceMetrics objects per subperiod
        - 'subperiod_returns': List of total returns per period
        - 'subperiod_sharpes': List of Sharpe ratios per period
        - 'positive_periods': Count of profitable periods
        - 'consistency_rate': Proportion of profitable periods

    Notes
    -----
    Now uses compute_all_metrics to get all 21 metrics per subperiod.
    Stores full PerformanceMetrics dataclass objects in 'periods' list.
    """
    logger.debug("Computing subperiod metrics: n_subperiods=%d", n_subperiods)

    pnl_subperiods = _split_into_subperiods(pnl_df, n_subperiods)
    pos_subperiods = _split_into_subperiods(positions_df, n_subperiods)

    periods_metrics = []
    subperiod_returns = []
    subperiod_sharpes = []

    for i, (sub_pnl, sub_pos) in enumerate(zip(pnl_subperiods, pos_subperiods)):
        # Compute all metrics for this subperiod
        metrics = compute_all_metrics(sub_pnl, sub_pos, rolling_window)
        periods_metrics.append(metrics)

        # Extract key values for summary stats
        subperiod_returns.append(metrics.total_return)
        subperiod_sharpes.append(metrics.sharpe_ratio)

        logger.debug(
            "Subperiod %d: return=%.2f, sharpe=%.2f, trades=%d",
            i + 1,
            metrics.total_return,
            metrics.sharpe_ratio,
            metrics.n_trades,
        )

    positive_periods = sum(1 for r in subperiod_returns if r > 0)
    consistency_rate = positive_periods / n_subperiods

    return {
        "periods": periods_metrics,
        "subperiod_returns": subperiod_returns,
        "subperiod_sharpes": subperiod_sharpes,
        "positive_periods": positive_periods,
        "consistency_rate": consistency_rate,
    }


def _compute_stability_score(subperiod_analysis: dict[str, Any]) -> float:
    """
    Compute overall stability score from subperiod analysis.

    Score combines consistency rate and Sharpe stability.

    Parameters
    ----------
    subperiod_analysis : dict[str, Any]
        Subperiod metrics from _compute_subperiod_metrics.

    Returns
    -------
    float
        Stability score (0-1 scale).

    Notes
    -----
    Weights: 60% consistency rate, 40% Sharpe stability.
    Sharpe stability measured as proportion of positive Sharpe periods.
    """
    consistency_rate = subperiod_analysis["consistency_rate"]
    sharpes = subperiod_analysis["subperiod_sharpes"]

    # Sharpe stability: proportion with positive Sharpe
    positive_sharpes = sum(1 for s in sharpes if s > 0)
    sharpe_stability = positive_sharpes / len(sharpes) if sharpes else 0.0

    # Combined score
    stability_score = 0.6 * consistency_rate + 0.4 * sharpe_stability

    logger.debug(
        "Stability score: %.3f (consistency=%.1f%%, sharpe_stability=%.1f%%)",
        stability_score,
        consistency_rate * 100,
        sharpe_stability * 100,
    )

    return stability_score


def _generate_summary(
    metrics: PerformanceMetrics,
    subperiod_analysis: dict[str, Any],
    attribution: dict[str, dict[str, float]],
    stability_score: float,
) -> str:
    """
    Generate interpretive summary of performance evaluation.

    Parameters
    ----------
    metrics : PerformanceMetrics
        Comprehensive performance metrics (basic + extended).
    subperiod_analysis : dict[str, Any]
        Subperiod stability results.
    attribution : dict[str, dict[str, float]]
        Return attribution breakdown.
    stability_score : float
        Overall stability score.

    Returns
    -------
    str
        Multi-line interpretive summary text.
    """
    # Key metrics (access dataclass fields)
    profit_factor = metrics.profit_factor
    tail_ratio = metrics.tail_ratio
    consistency = metrics.consistency_score
    positive_periods = subperiod_analysis["positive_periods"]
    n_periods = len(subperiod_analysis["subperiod_returns"])

    # Attribution insights
    long_pct = attribution["direction"]["long_pct"]

    summary_lines = []

    # Overall assessment
    if stability_score >= 0.7:
        assessment = "Strong and stable performance"
    elif stability_score >= 0.5:
        assessment = "Moderate performance with acceptable stability"
    else:
        assessment = "Inconsistent performance requiring review"

    summary_lines.append(f"Overall: {assessment} (stability score: {stability_score:.2f})")

    # Profitability
    if profit_factor > 1.5:
        summary_lines.append(f"Profitability: Strong (profit factor {profit_factor:.2f})")
    elif profit_factor > 1.0:
        summary_lines.append(f"Profitability: Positive (profit factor {profit_factor:.2f})")
    else:
        summary_lines.append(f"Profitability: Weak (profit factor {profit_factor:.2f})")

    # Risk characteristics
    if tail_ratio > 1.2:
        summary_lines.append(f"Risk profile: Favorable asymmetry (tail ratio {tail_ratio:.2f})")
    elif tail_ratio > 0.8:
        summary_lines.append(f"Risk profile: Balanced (tail ratio {tail_ratio:.2f})")
    else:
        summary_lines.append(f"Risk profile: Negative skew (tail ratio {tail_ratio:.2f})")

    # Temporal stability
    summary_lines.append(
        f"Temporal consistency: {positive_periods}/{n_periods} profitable periods ({consistency:.1%} positive windows)"
    )

    # Directional bias
    if abs(long_pct) > 0.7:
        direction = "long" if long_pct > 0 else "short"
        summary_lines.append(f"Strong {direction} directional bias ({abs(long_pct):.1%})")
    else:
        summary_lines.append(f"Balanced directional exposure (long: {long_pct:.1%})")

    return "\n".join(summary_lines)


def analyze_backtest_performance(
    backtest_result: BacktestResult,
    config: PerformanceConfig | None = None,
) -> PerformanceResult:
    """
    Perform comprehensive performance evaluation of backtest results.

    Orchestrates computation of extended metrics, subperiod stability analysis,
    return attribution, and interpretive summary.

    Parameters
    ----------
    backtest_result : BacktestResult
        Backtest output containing positions, P&L, and metadata.
    config : PerformanceConfig | None
        Evaluation configuration. If None, uses defaults.

    Returns
    -------
    PerformanceResult
        Structured evaluation results with metrics, attribution, and summary.

    Raises
    ------
    ValueError
        If backtest result has insufficient data or invalid structure.

    Notes
    -----
    Requires backtest_result.pnl to have DatetimeIndex and columns:
    'net_pnl', 'cumulative_pnl'.

    Requires backtest_result.positions to have columns:
    'signal', 'position'.

    Examples
    --------
    >>> result = run_backtest(signal, cdx_df, config)
    >>> performance = analyze_backtest_performance(result)
    >>> print(performance.summary)
    >>> print(f"Stability: {performance.stability_score:.2f}")
    """
    if config is None:
        config = PerformanceConfig()

    logger.info("Analyzing backtest performance: config=%s", config)

    # Validate input
    pnl_df = backtest_result.pnl
    positions_df = backtest_result.positions

    if len(pnl_df) < config.min_obs:
        raise ValueError(f"Insufficient observations: {len(pnl_df)} < {config.min_obs} (min_obs)")

    if not isinstance(pnl_df.index, pd.DatetimeIndex):
        raise ValueError("pnl_df must have DatetimeIndex")

    required_pnl_cols = {"net_pnl", "cumulative_pnl"}
    if not required_pnl_cols.issubset(pnl_df.columns):
        raise ValueError(f"pnl_df missing required columns: {required_pnl_cols}")

    required_pos_cols = {"signal", "position"}
    if not required_pos_cols.issubset(positions_df.columns):
        raise ValueError(f"positions_df missing required columns: {required_pos_cols}")

    # Compute all performance metrics (basic + extended)
    metrics = compute_all_metrics(pnl_df, positions_df, config.rolling_window)

    # Subperiod stability analysis
    subperiod_analysis = _compute_subperiod_metrics(
        pnl_df, positions_df, config.n_subperiods, config.rolling_window
    )

    # Return attribution
    attribution = compute_attribution(
        pnl_df, positions_df, n_quantiles=config.attribution_quantiles
    )

    # Overall stability score
    stability_score = _compute_stability_score(subperiod_analysis)

    # Generate interpretive summary
    summary = _generate_summary(metrics, subperiod_analysis, attribution, stability_score)

    # Build result
    timestamp = datetime.now().isoformat()

    metadata = {
        "evaluator_version": __version__,
        "signal_id": backtest_result.metadata.get("signal_id", "unknown"),
        "strategy_id": backtest_result.metadata.get("strategy_id", "unknown"),
        "backtest_config": backtest_result.metadata.get("config", {}),
    }

    result = PerformanceResult(
        metrics=metrics,
        subperiod_analysis=subperiod_analysis,
        attribution=attribution,
        stability_score=stability_score,
        summary=summary,
        timestamp=timestamp,
        config=config,
        metadata=metadata,
    )

    logger.info(
        "Performance evaluation complete: stability=%.2f, profit_factor=%.2f",
        stability_score,
        metrics.profit_factor,
    )

    return result
