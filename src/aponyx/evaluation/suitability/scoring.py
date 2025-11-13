"""
Component scoring logic for suitability evaluation.

Provides scoring functions for the four evaluation components and
composite score computation.
"""

import logging

from aponyx.evaluation.suitability.config import SuitabilityConfig

logger = logging.getLogger(__name__)


def score_data_health(
    valid_obs: int,
    missing_pct: float,
    min_obs: int,
) -> float:
    """
    Score data quality and sufficiency.

    Parameters
    ----------
    valid_obs : int
        Number of valid observations after alignment.
    missing_pct : float
        Percentage of missing data (0-100).
    min_obs : int
        Minimum required observations threshold.

    Returns
    -------
    float
        Data health score on 0-1 scale.
        Returns 0.0 if insufficient observations.
        Otherwise, penalizes missing data with tolerance up to 20%.

    Notes
    -----
    Scoring logic:
    - If valid_obs < min_obs: score = 0.0 (insufficient data)
    - Else: score = max(0, 1 - missing_pct / 20)
      Capped at 0% (score=1.0) and 20% (score=0.0) missing.

    Examples
    --------
    >>> score_data_health(600, 5.0, 500)  # 600 obs, 5% missing
    0.75
    >>> score_data_health(400, 0.0, 500)  # Below threshold
    0.0
    """
    if valid_obs < min_obs:
        logger.debug(
            "Insufficient observations: %d < %d, score=0.0",
            valid_obs,
            min_obs,
        )
        return 0.0

    # Penalize missing data, tolerating up to 20%
    score = max(0.0, 1.0 - missing_pct / 20.0)

    logger.debug(
        "Data health: valid_obs=%d, missing_pct=%.2f%%, score=%.3f",
        valid_obs,
        missing_pct,
        score,
    )

    return score


def score_predictive(mean_abs_tstat: float) -> float:
    """
    Score predictive association strength.

    Parameters
    ----------
    mean_abs_tstat : float
        Mean absolute t-statistic across lags.

    Returns
    -------
    float
        Predictive score on 0-1 scale.
        Normalized by dividing by 3.0 (capped at 1.0).

    Notes
    -----
    Scoring logic:
    - score = min(1.0, mean_abs_tstat / 3.0)
    - t-stat > 2.0: Statistically significant at conventional levels
    - t-stat > 3.0: Strong evidence (score capped at 1.0)

    Examples
    --------
    >>> score_predictive(2.5)  # Significant
    0.833
    >>> score_predictive(4.0)  # Strong (capped)
    1.0
    """
    score = min(1.0, mean_abs_tstat / 3.0)

    logger.debug(
        "Predictive association: mean |t-stat|=%.3f, score=%.3f",
        mean_abs_tstat,
        score,
    )

    return score


def score_economic(effect_size_bps: float) -> float:
    """
    Score economic relevance based on effect size.

    Parameters
    ----------
    effect_size_bps : float
        Estimated impact in basis points per 1σ signal change.

    Returns
    -------
    float
        Economic score on 0-1 scale.

    Notes
    -----
    Scoring thresholds:
    - effect_size < 0.5 bps: Negligible → score = 0.2
    - 0.5 ≤ effect_size < 2.0 bps: Moderate → score = 0.6
    - effect_size ≥ 2.0 bps: Meaningful → score = 1.0

    For CDX spreads, 2 bps is ~0.4% spread change (economically relevant).

    Examples
    --------
    >>> score_economic(0.3)  # Negligible
    0.2
    >>> score_economic(1.5)  # Moderate
    0.6
    >>> score_economic(3.0)  # Meaningful
    1.0
    """
    if effect_size_bps < 0.5:
        score = 0.2
        category = "negligible"
    elif effect_size_bps < 2.0:
        score = 0.6
        category = "moderate"
    else:
        score = 1.0
        category = "meaningful"

    logger.debug(
        "Economic relevance: effect_size=%.3f bps (%s), score=%.3f",
        effect_size_bps,
        category,
        score,
    )

    return score


def score_stability(
    sign_consistency_ratio: float,
    beta_cv: float,
) -> float:
    """
    Score temporal stability based on rolling window statistics.

    Parameters
    ----------
    sign_consistency_ratio : float
        Proportion of rolling windows with same sign as aggregate beta (0-1).
    beta_cv : float
        Coefficient of variation of rolling betas (std / |mean|).

    Returns
    -------
    float
        Stability score on 0-1 scale.
        Weighted average of sign consistency and magnitude stability scores.

    Notes
    -----
    Scoring logic:
    
    Sign Consistency Component (50% weight):
    - ratio ≥ 0.8: score = 1.0 (highly consistent)
    - 0.6 ≤ ratio < 0.8: score = 0.5 (moderately consistent)
    - ratio < 0.6: score = 0.0 (inconsistent)
    
    Magnitude Stability Component (50% weight):
    - CV < 0.5: score = 1.0 (stable magnitude)
    - 0.5 ≤ CV < 1.0: score = 0.5 (moderate variation)
    - CV ≥ 1.0: score = 0.0 (high variation)
    
    Final score = 0.5 × sign_score + 0.5 × magnitude_score

    Examples
    --------
    >>> score_stability(0.85, 0.3)  # High consistency, low CV
    1.0
    >>> score_stability(0.75, 0.6)  # Moderate both
    0.5
    >>> score_stability(0.5, 1.2)   # Low consistency, high CV
    0.0
    """
    # Score sign consistency
    if sign_consistency_ratio >= 0.8:
        sign_score = 1.0
        sign_category = "highly consistent"
    elif sign_consistency_ratio >= 0.6:
        sign_score = 0.5
        sign_category = "moderately consistent"
    else:
        sign_score = 0.0
        sign_category = "inconsistent"
    
    # Score magnitude stability (lower CV = more stable)
    if beta_cv < 0.5:
        magnitude_score = 1.0
        magnitude_category = "stable"
    elif beta_cv < 1.0:
        magnitude_score = 0.5
        magnitude_category = "moderate variation"
    else:
        magnitude_score = 0.0
        magnitude_category = "high variation"
    
    # Weighted average (equal weights)
    score = 0.5 * sign_score + 0.5 * magnitude_score
    
    logger.debug(
        "Temporal stability: sign_ratio=%.3f (%s, score=%.1f), "
        "CV=%.3f (%s, score=%.1f), final_score=%.3f",
        sign_consistency_ratio,
        sign_category,
        sign_score,
        beta_cv,
        magnitude_category,
        magnitude_score,
        score,
    )
    
    return score


def compute_composite_score(
    data_health_score: float,
    predictive_score: float,
    economic_score: float,
    stability_score: float,
    config: SuitabilityConfig,
) -> float:
    """
    Compute weighted composite score from component scores.

    Parameters
    ----------
    data_health_score : float
        Data quality score (0-1).
    predictive_score : float
        Predictive association score (0-1).
    economic_score : float
        Economic relevance score (0-1).
    stability_score : float
        Temporal stability score (0-1).
    config : SuitabilityConfig
        Configuration with component weights.

    Returns
    -------
    float
        Composite score on 0-1 scale (weighted average).

    Notes
    -----
    Default weights:
    - Data health: 20%
    - Predictive: 40%
    - Economic: 20%
    - Stability: 20%

    Examples
    --------
    >>> config = SuitabilityConfig()
    >>> compute_composite_score(0.8, 0.9, 0.6, 1.0, config)
    0.82
    """
    composite = (
        config.data_health_weight * data_health_score
        + config.predictive_weight * predictive_score
        + config.economic_weight * economic_score
        + config.stability_weight * stability_score
    )

    logger.debug(
        "Composite score: %.3f = %.2f×%.3f + %.2f×%.3f + %.2f×%.3f + %.2f×%.3f",
        composite,
        config.data_health_weight,
        data_health_score,
        config.predictive_weight,
        predictive_score,
        config.economic_weight,
        economic_score,
        config.stability_weight,
        stability_score,
    )

    return composite


def assign_decision(
    composite_score: float,
    config: SuitabilityConfig,
) -> str:
    """
    Assign decision based on composite score and thresholds.

    Parameters
    ----------
    composite_score : float
        Composite score (0-1).
    config : SuitabilityConfig
        Configuration with decision thresholds.

    Returns
    -------
    str
        Decision: "PASS", "HOLD", or "FAIL".

    Notes
    -----
    Decision logic:
    - score ≥ pass_threshold (0.7): PASS → proceed to backtest
    - pass_threshold > score ≥ hold_threshold (0.4): HOLD → marginal, requires judgment
    - score < hold_threshold: FAIL → do not backtest

    Examples
    --------
    >>> config = SuitabilityConfig()
    >>> assign_decision(0.75, config)
    'PASS'
    >>> assign_decision(0.55, config)
    'HOLD'
    >>> assign_decision(0.35, config)
    'FAIL'
    """
    if composite_score >= config.pass_threshold:
        decision = "PASS"
    elif composite_score >= config.hold_threshold:
        decision = "HOLD"
    else:
        decision = "FAIL"

    logger.debug(
        "Decision assignment: score=%.3f, pass_threshold=%.2f, hold_threshold=%.2f → %s",
        composite_score,
        config.pass_threshold,
        config.hold_threshold,
        decision,
    )

    return decision
