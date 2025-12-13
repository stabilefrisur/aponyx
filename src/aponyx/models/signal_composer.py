"""
Signal composition functions for constructing trading signals via four-stage pipeline.

FOUR-STAGE TRANSFORMATION PIPELINE
-----------------------------------
Security → Indicator → Score → Signal → Position

1. **Indicator Transformation**: Compute economic metrics from raw securities (e.g., spread difference in bps)
2. **Score Transformation**: Normalize indicator to common scale (e.g., z-score)
3. **Signal Transformation**: Apply trading rules (floor, cap, neutral_range, scaling)
4. **Position Calculation**: Backtest layer converts signal to positions (out of scope for this module)

This module implements stages 1-3 with independent inspection capabilities.
"""

import logging
from typing import Any

import pandas as pd

from ..data.transforms import (
    TransformType,
    apply_signal_transformation,
    apply_transform,
)

logger = logging.getLogger(__name__)


def apply_score_transformation(
    indicator_series: pd.Series,
    transformation_metadata: dict[str, Any],
) -> pd.Series:
    """
    Apply a score transformation to an indicator time series.

    Score transformations normalize indicators to a common scale (z-scores, percentiles, etc.)
    for cross-signal comparison and combination.

    Parameters
    ----------
    indicator_series : pd.Series
        Input indicator time series (in economically interpretable units).
    transformation_metadata : dict[str, Any]
        Score transformation metadata with:
        - transform_type: TransformType (z_score, normalized_change, diff, etc.)
        - parameters: dict with window, min_periods, periods, etc.

    Returns
    -------
    pd.Series
        Normalized score series (dimensionless, typically z-scores).

    Notes
    -----
    - Input indicators are in interpretable units (bps, ratios, percentages)
    - Output scores are dimensionless for trading signal use
    - Preserves DatetimeIndex alignment
    - NaN values propagate from input or transformation calculation

    Examples
    --------
    >>> spread_diff = pd.Series([10, 12, 8, 15], index=pd.date_range('2024-01-01', periods=4))
    >>> metadata = {"transform_type": "z_score", "parameters": {"window": 20, "min_periods": 10}}
    >>> score = apply_score_transformation(spread_diff, metadata)
    """
    transform_type: TransformType = transformation_metadata["transform_type"]
    parameters = transformation_metadata["parameters"]

    logger.debug(
        "Applying score transformation: type=%s, params=%s, input_points=%d",
        transform_type,
        parameters,
        len(indicator_series),
    )

    # Apply transformation using data.transforms module
    transformed = apply_transform(
        indicator_series,
        transform_type,
        **parameters,
    )

    valid_count = transformed.notna().sum()
    logger.debug("Score transformation yielded %d valid values", valid_count)

    return transformed


def compose_signal(
    signal_name: str,
    market_data: dict[str, pd.DataFrame],
    indicator_registry: Any,  # IndicatorTransformationRegistry type
    score_registry: Any,  # ScoreTransformationRegistry type
    signal_transformation_registry: Any,  # SignalTransformationRegistry type
    signal_registry: Any,  # SignalRegistry type
    *,
    indicator_transformation_override: str | None = None,
    score_transformation_override: str | None = None,
    signal_transformation_override: str | None = None,
    include_intermediates: bool = False,
) -> pd.Series | dict[str, pd.Series]:
    """
    Compose a trading signal via four-stage transformation pipeline.

    FOUR-STAGE PIPELINE
    -------------------
    Security → Indicator → Score → Signal → Position

    Each signal references exactly one transformation from each stage (1:1:1 relationship).
    This function orchestrates the complete pipeline with optional intermediate inspection.

    Parameters
    ----------
    signal_name : str
        Signal identifier (must exist in signal_registry).
    market_data : dict[str, pd.DataFrame]
        Market data keyed by instrument type (cdx, vix, etf, etc.).
    indicator_registry : IndicatorTransformationRegistry
        Registry for loading indicator transformation metadata.
    score_registry : ScoreTransformationRegistry
        Registry for loading score transformation metadata.
    signal_transformation_registry : SignalTransformationRegistry
        Registry for loading signal transformation metadata.
    signal_registry : SignalRegistry
        Registry for loading signal metadata.
    indicator_transformation_override : str or None, optional
        Override the indicator transformation from signal catalog.
        Must exist in indicator_registry.
    score_transformation_override : str or None, optional
        Override the score transformation from signal catalog.
        Must exist in score_registry.
    signal_transformation_override : str or None, optional
        Override the signal transformation from signal catalog.
        Must exist in signal_transformation_registry.
    include_intermediates : bool, default False
        If True, return dict with intermediate stages.
        If False, return final signal series only.

    Returns
    -------
    pd.Series or dict[str, pd.Series]
        If include_intermediates=False: Final signal series.
        If include_intermediates=True: Dict with keys:
            - "indicator": Raw indicator output (bps, ratios, etc.)
            - "score": Normalized score (z-score, etc.)
            - "signal": Final signal after trading rules applied

    Raises
    ------
    KeyError
        If signal_name not found in signal_registry.
        If any transformation reference not found in its registry.
    ValueError
        If market data missing required instruments.

    Notes
    -----
    - Transformation order is fixed: indicator → score → signal_transformation
    - Sign multiplier applied after signal_transformation
    - Each stage can be inspected independently via include_intermediates=True
    - NaN values propagate through all stages

    Examples
    --------
    Basic usage (final signal only):
    >>> signal = compose_signal(
    ...     signal_name="cdx_etf_basis",
    ...     market_data={"cdx": cdx_df, "etf": etf_df"},
    ...     indicator_registry=indicator_reg,
    ...     score_registry=score_reg,
    ...     signal_transformation_registry=signal_trans_reg,
    ...     signal_registry=signal_reg,
    ... )

    With intermediate inspection:
    >>> result = compose_signal(
    ...     signal_name="cdx_etf_basis",
    ...     market_data={"cdx": cdx_df, "etf": etf_df},
    ...     indicator_registry=indicator_reg,
    ...     score_registry=score_reg,
    ...     signal_transformation_registry=signal_trans_reg,
    ...     signal_registry=signal_reg,
    ...     include_intermediates=True,
    ... )
    >>> print(result["indicator"].tail())  # Raw basis in bps
    >>> print(result["score"].tail())      # Normalized z-score
    >>> print(result["signal"].tail())     # Final trading signal
    """
    from .indicators import compute_indicator

    # Load signal metadata
    signal_metadata = signal_registry.get_metadata(signal_name)

    logger.info("Composing signal via 4-stage pipeline: signal=%s", signal_name)

    # Apply runtime overrides (with validation)
    indicator_name = (
        indicator_transformation_override
        if indicator_transformation_override is not None
        else signal_metadata.indicator_transformation
    )
    score_transformation_name = (
        score_transformation_override
        if score_transformation_override is not None
        else signal_metadata.score_transformation
    )
    signal_transformation_name = (
        signal_transformation_override
        if signal_transformation_override is not None
        else signal_metadata.signal_transformation
    )

    # Validate overrides exist in registries (fail-fast)
    if indicator_transformation_override is not None:
        if not indicator_registry.indicator_exists(indicator_transformation_override):
            raise ValueError(
                f"indicator_transformation_override '{indicator_transformation_override}' "
                f"not found in indicator_registry. Available: {sorted(indicator_registry.get_all_indicators())}"
            )
        logger.info(
            "Override: indicator_transformation=%s (catalog default: %s)",
            indicator_transformation_override,
            signal_metadata.indicator_transformation,
        )

    if score_transformation_override is not None:
        if not score_registry.transformation_exists(score_transformation_override):
            raise ValueError(
                f"score_transformation_override '{score_transformation_override}' "
                f"not found in score_registry. Available: {sorted(score_registry.list_all().keys())}"
            )
        logger.info(
            "Override: score_transformation=%s (catalog default: %s)",
            score_transformation_override,
            signal_metadata.score_transformation,
        )

    if signal_transformation_override is not None:
        if not signal_transformation_registry.transformation_exists(
            signal_transformation_override
        ):
            raise ValueError(
                f"signal_transformation_override '{signal_transformation_override}' "
                f"not found in signal_transformation_registry. Available: {sorted(signal_transformation_registry.list_all().keys())}"
            )
        logger.info(
            "Override: signal_transformation=%s (catalog default: %s)",
            signal_transformation_override,
            signal_metadata.signal_transformation,
        )

    # Stage 1: Indicator Transformation
    # ----------------------------------
    # Compute economic metric from raw securities (e.g., spread difference in bps)
    indicator_metadata = indicator_registry.get_metadata(indicator_name)

    logger.debug("Stage 1: Computing indicator transformation: %s", indicator_name)
    indicator_series = compute_indicator(
        indicator_name=indicator_name,
        market_data=market_data,
        indicator_metadata=indicator_metadata,
    )
    logger.debug(
        "Indicator output: %d values, unit=%s",
        indicator_series.notna().sum(),
        indicator_metadata.output_units,
    )

    # Stage 2: Score Transformation
    # ------------------------------
    # Normalize indicator to common scale (e.g., z-score)
    score_transformation_metadata = score_registry.get_metadata(
        score_transformation_name
    )

    logger.debug(
        "Stage 2: Applying score transformation: %s", score_transformation_name
    )
    score_series = apply_score_transformation(
        indicator_series,
        vars(score_transformation_metadata),
    )
    logger.debug("Score output: %d values", score_series.notna().sum())

    # Stage 3: Signal Transformation
    # -------------------------------
    # Apply trading rules (floor, cap, neutral_range, scaling)
    signal_transformation_metadata = signal_transformation_registry.get_metadata(
        signal_transformation_name
    )

    logger.debug(
        "Stage 3: Applying signal transformation: %s", signal_transformation_name
    )
    signal_series = apply_signal_transformation(
        score_series,
        scaling=signal_transformation_metadata.scaling,
        floor=signal_transformation_metadata.floor,
        cap=signal_transformation_metadata.cap,
        neutral_range=signal_transformation_metadata.neutral_range,
    )
    logger.debug("Signal output: %d values", signal_series.notna().sum())

    # Stage 4: Sign Convention Alignment
    # -----------------------------------
    # Apply sign multiplier to ensure positive = long credit risk
    final_signal = signal_series * signal_metadata.sign_multiplier

    logger.info(
        "Signal composition complete: signal=%s, final_values=%d",
        signal_name,
        final_signal.notna().sum(),
    )

    # Return final signal or intermediates dict
    if include_intermediates:
        return {
            "indicator": indicator_series,
            "score": score_series,
            "signal": final_signal,
        }
    else:
        return final_signal


def compute_indicator_stage(
    signal_name: str,
    market_data: dict[str, pd.DataFrame],
    indicator_registry: Any,  # IndicatorTransformationRegistry type
    signal_registry: Any,  # SignalRegistry type
) -> pd.Series:
    """
    Compute indicator transformation stage only (Stage 1).

    Use for debugging or analysis when you need the raw indicator output
    without subsequent normalization or trading rules.

    Parameters
    ----------
    signal_name : str
        Signal identifier (must exist in signal_registry).
    market_data : dict[str, pd.DataFrame]
        Market data keyed by instrument type.
    indicator_registry : IndicatorTransformationRegistry
        Registry for loading indicator transformation metadata.
    signal_registry : SignalRegistry
        Registry for loading signal metadata.

    Returns
    -------
    pd.Series
        Raw indicator output in economic units (bps, ratios, etc.).

    Examples
    --------
    >>> indicator = compute_indicator_stage(
    ...     signal_name="cdx_etf_basis",
    ...     market_data={"cdx": cdx_df, "etf": etf_df},
    ...     indicator_registry=indicator_reg,
    ...     signal_registry=signal_reg,
    ... )
    >>> print(f"Basis: {indicator.tail()}")  # Raw bps values
    """
    from .indicators import compute_indicator

    signal_metadata = signal_registry.get_metadata(signal_name)
    indicator_name = signal_metadata.indicator_transformation
    indicator_metadata = indicator_registry.get_metadata(indicator_name)

    logger.info(
        "Computing indicator stage only: signal=%s, indicator=%s",
        signal_name,
        indicator_name,
    )

    return compute_indicator(
        indicator_name=indicator_name,
        market_data=market_data,
        indicator_metadata=indicator_metadata,
    )


def compute_score_stage(
    signal_name: str,
    market_data: dict[str, pd.DataFrame],
    indicator_registry: Any,  # IndicatorTransformationRegistry type
    score_registry: Any,  # ScoreTransformationRegistry type
    signal_registry: Any,  # SignalRegistry type
) -> pd.Series:
    """
    Compute through score transformation stage (Stages 1-2).

    Use for debugging normalization behavior without trading rules applied.

    Parameters
    ----------
    signal_name : str
        Signal identifier (must exist in signal_registry).
    market_data : dict[str, pd.DataFrame]
        Market data keyed by instrument type.
    indicator_registry : IndicatorTransformationRegistry
        Registry for loading indicator transformation metadata.
    score_registry : ScoreTransformationRegistry
        Registry for loading score transformation metadata.
    signal_registry : SignalRegistry
        Registry for loading signal metadata.

    Returns
    -------
    pd.Series
        Normalized score (z-score, etc.).

    Examples
    --------
    >>> score = compute_score_stage(
    ...     signal_name="cdx_etf_basis",
    ...     market_data={"cdx": cdx_df, "etf": etf_df},
    ...     indicator_registry=indicator_reg,
    ...     score_registry=score_reg,
    ...     signal_registry=signal_reg,
    ... )
    >>> print(f"Z-score: {score.tail()}")  # Normalized values
    """
    from .indicators import compute_indicator

    signal_metadata = signal_registry.get_metadata(signal_name)

    # Stage 1: Indicator
    indicator_name = signal_metadata.indicator_transformation
    indicator_metadata = indicator_registry.get_metadata(indicator_name)
    indicator_series = compute_indicator(
        indicator_name=indicator_name,
        market_data=market_data,
        indicator_metadata=indicator_metadata,
    )

    # Stage 2: Score
    score_transformation_name = signal_metadata.score_transformation
    score_transformation_metadata = score_registry.get_metadata(
        score_transformation_name
    )

    logger.info(
        "Computing score stage: signal=%s, indicator=%s, score=%s",
        signal_name,
        indicator_name,
        score_transformation_name,
    )

    return apply_score_transformation(
        indicator_series,
        vars(score_transformation_metadata),
    )


def compute_signal_stage(
    signal_name: str,
    market_data: dict[str, pd.DataFrame],
    indicator_registry: Any,  # IndicatorTransformationRegistry type
    score_registry: Any,  # ScoreTransformationRegistry type
    signal_transformation_registry: Any,  # SignalTransformationRegistry type
    signal_registry: Any,  # SignalRegistry type
) -> pd.Series:
    """
    Compute through signal transformation stage (Stages 1-3).

    This is equivalent to compose_signal() with include_intermediates=False,
    provided for symmetry with other stage-specific functions.

    Parameters
    ----------
    signal_name : str
        Signal identifier (must exist in signal_registry).
    market_data : dict[str, pd.DataFrame]
        Market data keyed by instrument type.
    indicator_registry : IndicatorTransformationRegistry
        Registry for loading indicator transformation metadata.
    score_registry : ScoreTransformationRegistry
        Registry for loading score transformation metadata.
    signal_transformation_registry : SignalTransformationRegistry
        Registry for loading signal transformation metadata.
    signal_registry : SignalRegistry
        Registry for loading signal metadata.

    Returns
    -------
    pd.Series
        Final trading signal (with trading rules applied, sign convention aligned).

    Examples
    --------
    >>> signal = compute_signal_stage(
    ...     signal_name="cdx_etf_basis",
    ...     market_data={"cdx": cdx_df, "etf": etf_df},
    ...     indicator_registry=indicator_reg,
    ...     score_registry=score_reg,
    ...     signal_transformation_registry=signal_trans_reg,
    ...     signal_registry=signal_reg,
    ... )
    >>> print(f"Signal: {signal.tail()}")  # Bounded, final values
    """
    logger.info("Computing signal stage (full pipeline): signal=%s", signal_name)

    return compose_signal(
        signal_name=signal_name,
        market_data=market_data,
        indicator_registry=indicator_registry,
        score_registry=score_registry,
        signal_transformation_registry=signal_transformation_registry,
        signal_registry=signal_registry,
        include_intermediates=False,
    )
