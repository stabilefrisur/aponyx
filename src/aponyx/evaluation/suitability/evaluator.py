"""
Core suitability evaluation logic.

Orchestrates statistical tests, scoring, and decision logic to evaluate
whether a signal contains meaningful predictive information for a traded product.
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from aponyx.evaluation.suitability.config import SuitabilityConfig

logger = logging.getLogger(__name__)


@dataclass
class SuitabilityResult:
    """
    Result container for signal-product suitability evaluation.

    Contains decision, component scores, diagnostics, and metadata from
    the evaluation process.

    Attributes
    ----------
    decision : str
        Overall decision: "PASS" (proceed to backtest), "HOLD" (marginal),
        or "FAIL" (do not backtest).
    composite_score : float
        Weighted average of component scores (0-1 scale).
    data_health_score : float
        Data quality and sufficiency score (0-1 scale).
    predictive_score : float
        Statistical association strength score (0-1 scale).
    economic_score : float
        Economic relevance/impact score (0-1 scale).
    stability_score : float
        Temporal consistency score (0-1 scale).
    valid_obs : int
        Number of valid observations after alignment.
    missing_pct : float
        Percentage of missing data.
    correlations : dict[int, float]
        Pearson correlations by lag horizon.
    betas : dict[int, float]
        Regression coefficients by lag horizon.
    t_stats : dict[int, float]
        T-statistics by lag horizon.
    effect_size_bps : float
        Economic impact estimate (bps per 1σ signal change).
    sign_consistency_ratio : float
        Proportion of rolling windows with consistent sign.
    beta_cv : float
        Coefficient of variation of rolling betas.
    n_windows : int
        Number of valid rolling windows analyzed.
    timestamp : str
        ISO timestamp of evaluation.
    config : SuitabilityConfig
        Configuration used for evaluation.
    """

    decision: str
    composite_score: float
    data_health_score: float
    predictive_score: float
    economic_score: float
    stability_score: float
    valid_obs: int
    missing_pct: float
    correlations: dict[int, float]
    betas: dict[int, float]
    t_stats: dict[int, float]
    effect_size_bps: float
    sign_consistency_ratio: float
    beta_cv: float
    n_windows: int
    timestamp: str
    config: SuitabilityConfig

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result to dictionary for JSON serialization.

        Returns
        -------
        dict[str, Any]
            Structured dictionary with component scores, metrics, and metadata.
        """
        return {
            "decision": self.decision,
            "composite_score": self.composite_score,
            "component_scores": {
                "data_health": self.data_health_score,
                "predictive": self.predictive_score,
                "economic": self.economic_score,
                "stability": self.stability_score,
            },
            "metrics": {
                "valid_obs": self.valid_obs,
                "missing_pct": self.missing_pct,
                "correlations": self.correlations,
                "betas": self.betas,
                "t_stats": self.t_stats,
                "effect_size_bps": self.effect_size_bps,
                "sign_consistency_ratio": self.sign_consistency_ratio,
                "beta_cv": self.beta_cv,
                "n_windows": self.n_windows,
            },
            "timestamp": self.timestamp,
            "config": asdict(self.config),
        }


def compute_forward_returns(
    spread_series: pd.Series,
    lags: list[int],
) -> dict[int, pd.Series]:
    """
    Compute forward-looking returns (changes) from spread series.

    For credit spreads, forward returns represent the change in spread from
    time t to time t+lag. This is the target variable for predictive evaluation.

    Parameters
    ----------
    spread_series : pd.Series
        Time series of spread levels with DatetimeIndex.
    lags : list[int]
        List of forward horizons (e.g., [1, 3, 5] for 1-, 3-, 5-day ahead).

    Returns
    -------
    dict[int, pd.Series]
        Dictionary mapping lag → forward return series.
        Each series has the same index as input, with NaN at the end where
        forward data is not available.

    Notes
    -----
    Forward returns are computed as: spread[t+lag] - spread[t]
    For credit spreads, positive return = widening, negative = tightening.

    Examples
    --------
    >>> spreads = pd.Series([100, 102, 98, 101], index=pd.date_range('2020-01-01', periods=4))
    >>> fwd_returns = compute_forward_returns(spreads, [1, 2])
    >>> fwd_returns[1]  # 1-day forward: [102-100, 98-102, 101-98, NaN]
    """
    logger.debug(
        "Computing forward returns for %d lags: %s",
        len(lags),
        lags,
    )

    forward_returns = {}
    for lag in lags:
        # Shift backwards to get future values aligned to current index
        forward_returns[lag] = spread_series.shift(-lag) - spread_series

    logger.debug(
        "Computed forward returns with %d observations per lag",
        len(spread_series) - max(lags) if lags else len(spread_series),
    )

    return forward_returns


def evaluate_signal_suitability(
    signal: pd.Series,
    target_change: pd.Series,
    config: SuitabilityConfig | None = None,
) -> SuitabilityResult:
    """
    Evaluate whether signal contains predictive information for target product.

    This is the main entry point for suitability evaluation. Orchestrates
    statistical tests, scoring, and decision logic.

    Parameters
    ----------
    signal : pd.Series
        Signal time series with DatetimeIndex and .name attribute.
        Should be z-score normalized for interpretability.
    target_change : pd.Series
        Target series (e.g., spread levels) with DatetimeIndex.
        Forward returns will be computed internally for each lag horizon.
    config : SuitabilityConfig, optional
        Evaluation configuration. If None, uses defaults.

    Returns
    -------
    SuitabilityResult
        Comprehensive evaluation result with decision, scores, and diagnostics.

    Raises
    ------
    ValueError
        If signal or target lack required attributes (DatetimeIndex, name).

    Notes
    -----
    This function does NOT include trading rules, costs, or position sizing.
    It purely evaluates the statistical and economic relationship between
    signal and target.

    The function computes forward-looking returns (target[t+lag] - target[t])
    internally for each configured lag horizon.

    Examples
    --------
    >>> signal = compute_spread_momentum(cdx_df, config)
    >>> result = evaluate_signal_suitability(signal, cdx_df['spread'])
    >>> print(result.decision, result.composite_score)
    """
    from aponyx.evaluation.suitability import tests, scoring

    if config is None:
        config = SuitabilityConfig()

    logger.info(
        "Starting suitability evaluation: signal=%s, config=%s",
        getattr(signal, "name", "unnamed"),
        config,
    )

    # Validate inputs
    if not isinstance(signal.index, pd.DatetimeIndex):
        raise ValueError("Signal must have DatetimeIndex")
    if not isinstance(target_change.index, pd.DatetimeIndex):
        raise ValueError("Target must have DatetimeIndex")

    # Align signal and target on common dates
    aligned_df = pd.DataFrame({"signal": signal, "target": target_change}).dropna()
    signal_aligned = aligned_df["signal"]
    target_aligned = aligned_df["target"]

    logger.debug(
        "Aligned data: original_signal=%d, original_target=%d, aligned=%d",
        len(signal),
        len(target_change),
        len(aligned_df),
    )

    # Compute data health metrics
    valid_obs = len(aligned_df)
    total_obs = max(len(signal), len(target_change))
    missing_pct = (1 - valid_obs / total_obs) * 100 if total_obs > 0 else 100.0

    logger.debug(
        "Data health: valid_obs=%d, missing_pct=%.2f%%",
        valid_obs,
        missing_pct,
    )

    # Score data health
    data_health_score = scoring.score_data_health(
        valid_obs=valid_obs,
        missing_pct=missing_pct,
        min_obs=config.min_obs,
    )
    logger.info("Data health score: %.3f", data_health_score)

    # Compute predictive statistics for all configured lags
    logger.debug("Computing stats for %d lags: %s", len(config.lags), config.lags)

    correlations = {}
    betas = {}
    t_stats = {}

    for lag in config.lags:
        # Compute forward returns for this lag
        target_fwd = target_change.shift(-lag)

        # Align signal with forward target
        aligned_lag = pd.DataFrame({"signal": signal, "target": target_fwd}).dropna()
        signal_lag = aligned_lag["signal"]
        target_lag = aligned_lag["target"]

        # Compute correlation
        correlations[lag] = tests.compute_correlation(signal_lag, target_lag)

        # Compute regression stats
        regression_stats = tests.compute_regression_stats(signal_lag, target_lag)
        betas[lag] = regression_stats["beta"]
        t_stats[lag] = regression_stats["t_stat"]

        logger.debug(
            "Lag %d: n=%d, corr=%.3f, beta=%.3f, t_stat=%.3f",
            lag,
            len(signal_lag),
            correlations[lag],
            betas[lag],
            t_stats[lag],
        )

    # Score predictive association using mean |t-stat| across all lags
    mean_abs_tstat = np.mean([abs(t) for t in t_stats.values()])
    predictive_score = scoring.score_predictive(mean_abs_tstat)
    logger.info(
        "Predictive score: %.3f (mean |t-stat|=%.3f across %d lags)",
        predictive_score,
        mean_abs_tstat,
        len(config.lags),
    )

    # Compute economic relevance
    avg_beta = np.mean(list(betas.values()))
    signal_std = signal_aligned.std()
    effect_size_bps = abs(avg_beta * signal_std)

    logger.debug("Economic impact: effect_size=%.3f bps", effect_size_bps)

    # Score economic relevance
    economic_score = scoring.score_economic(effect_size_bps)
    logger.info("Economic score: %.3f", economic_score)

    # Compute temporal stability using rolling window approach
    rolling_betas = tests.compute_rolling_betas(
        signal_aligned,
        target_aligned,
        window=config.rolling_window,
    )
    
    # Compute stability metrics
    stability_metrics = tests.compute_stability_metrics(rolling_betas, avg_beta)
    sign_consistency_ratio = stability_metrics['sign_consistency_ratio']
    beta_cv = stability_metrics['beta_cv']
    n_windows = stability_metrics['n_windows']

    logger.debug(
        "Stability: sign_ratio=%.3f, CV=%.3f, n_windows=%d",
        sign_consistency_ratio,
        beta_cv,
        n_windows,
    )

    # Score stability
    stability_score = scoring.score_stability(sign_consistency_ratio, beta_cv)
    logger.info("Stability score: %.3f", stability_score)

    # Compute composite score
    composite_score = scoring.compute_composite_score(
        data_health_score=data_health_score,
        predictive_score=predictive_score,
        economic_score=economic_score,
        stability_score=stability_score,
        config=config,
    )
    logger.info("Composite score: %.3f", composite_score)

    # Assign decision
    decision = scoring.assign_decision(composite_score, config)
    logger.info("Decision: %s", decision)

    # Create result
    result = SuitabilityResult(
        decision=decision,
        composite_score=composite_score,
        data_health_score=data_health_score,
        predictive_score=predictive_score,
        economic_score=economic_score,
        stability_score=stability_score,
        valid_obs=valid_obs,
        missing_pct=missing_pct,
        correlations=correlations,
        betas=betas,
        t_stats=t_stats,
        effect_size_bps=effect_size_bps,
        sign_consistency_ratio=sign_consistency_ratio,
        beta_cv=beta_cv,
        n_windows=n_windows,
        timestamp=datetime.now().isoformat(),
        config=config,
    )

    logger.info(
        "Evaluation complete: signal=%s, decision=%s, score=%.3f",
        getattr(signal, "name", "unnamed"),
        decision,
        composite_score,
    )

    return result
