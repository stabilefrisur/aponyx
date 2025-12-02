"""
Signal composition functions for constructing trading signals from indicators.

Signals are composed by:
1. Loading indicator time series (cached or computed)
2. Applying transformations (z-score, volatility adjustment, etc.)
3. Combining multiple indicators if needed (via composition_logic)

This separation enables rapid signal experimentation without recomputing indicators.
"""

import logging
from typing import Any

import pandas as pd

from ..data.transforms import TransformType, apply_transform

logger = logging.getLogger(__name__)


def apply_signal_transformation(
    indicator_series: pd.Series,
    transformation_metadata: dict[str, Any],
) -> pd.Series:
    """
    Apply a transformation to an indicator time series.

    Parameters
    ----------
    indicator_series : pd.Series
        Input indicator time series (in economically interpretable units).
    transformation_metadata : dict[str, Any]
        Transformation metadata with:
        - transform_type: TransformType (z_score, diff, pct_change, etc.)
        - parameters: dict with window, min_periods, periods, etc.

    Returns
    -------
    pd.Series
        Transformed series suitable for trading signal use.

    Notes
    -----
    - Input indicators are in interpretable units (bps, ratios, percentages)
    - Output transformations normalize for trading (z-scores, volatility-adjusted)
    - Preserves DatetimeIndex alignment
    - NaN values propagate from input or transformation calculation

    Examples
    --------
    >>> spread_diff = pd.Series([10, 12, 8, 15], index=pd.date_range('2024-01-01', periods=4))
    >>> metadata = {"transform_type": "z_score", "parameters": {"window": 20, "min_periods": 10}}
    >>> signal = apply_signal_transformation(spread_diff, metadata)
    """
    transform_type: TransformType = transformation_metadata["transform_type"]
    parameters = transformation_metadata["parameters"]

    logger.debug(
        "Applying transformation: type=%s, params=%s, input_points=%d",
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
    logger.debug("Transformation yielded %d valid values", valid_count)

    return transformed


def compose_signal(
    indicator_registry: Any,  # IndicatorRegistry type
    transformation_registry: Any,  # TransformationRegistry type
    signal_metadata: dict[str, Any],
    market_data: dict[str, pd.DataFrame],
) -> pd.Series:
    """
    Compose a trading signal from indicators and transformations.
    
    SIGNAL COMPOSITION PATTERN
    --------------------------
    Every signal is ALWAYS constructed from:
    1. Indicator(s) - Economically interpretable market metrics
    2. Transformation(s) - Signal processing operations
    
    This function is the ONLY way to generate signals in the system.
    Direct indicator computation is for analysis/debugging only.

    Orchestrates the signal composition workflow:
    1. Load indicators (from cache or compute)
    2. Apply transformations to each indicator
    3. Combine indicators if composition_logic provided
    4. Apply sign multiplier for convention alignment

    Parameters
    ----------
    indicator_registry : IndicatorRegistry
        Registry for loading indicator metadata.
    transformation_registry : TransformationRegistry
        Registry for loading transformation metadata.
    signal_metadata : dict[str, Any]
        Signal metadata with:
        - name: str - Signal identifier
        - indicator_dependencies: list[str] - Required indicators
        - transformations: list[str] - Transformations to apply
        - composition_logic: str | None - Optional combination expression
        - sign_multiplier: int - Sign convention adjustment (+1 or -1)
    market_data : dict[str, pd.DataFrame]
        Market data keyed by instrument type (cdx, vix, etf, etc.).

    Returns
    -------
    pd.Series
        Composed trading signal (normalized, transformed).

    Raises
    ------
    ValueError
        If indicator dependencies don't match transformation count.
        If composition_logic is invalid or references undefined variables.

    Notes
    -----
    - For single-indicator signals, transformations[0] applied to indicator
    - For multi-indicator signals, each indicator gets its own transformation,
      then combined via composition_logic
    - Sign multiplier applied last to ensure convention compliance

    Examples
    --------
    Single-indicator signal:
    >>> signal_metadata = {
    ...     "name": "cdx_etf_basis_zscore",
    ...     "indicator_dependencies": ["cdx_etf_spread_diff"],
    ...     "transformations": ["z_score_20d"],
    ...     "composition_logic": None,
    ...     "sign_multiplier": 1,
    ... }

    Multi-indicator signal:
    >>> signal_metadata = {
    ...     "name": "combined_momentum",
    ...     "indicator_dependencies": ["spread_momentum_5d", "cdx_vix_deviation_gap_20d"],
    ...     "transformations": ["z_score_20d", "z_score_60d"],
    ...     "composition_logic": "spread_momentum_5d + cdx_vix_deviation_gap_20d",
    ...     "sign_multiplier": 1,
    ... }
    """
    from .indicators import compute_indicator

    signal_name = signal_metadata["name"]
    indicator_deps = signal_metadata["indicator_dependencies"]
    transformation_names = signal_metadata["transformations"]
    composition_logic = signal_metadata.get("composition_logic")
    sign_multiplier = signal_metadata.get("sign_multiplier", 1)

    logger.info(
        "Composing signal: name=%s, indicators=%d, transformations=%d",
        signal_name,
        len(indicator_deps),
        len(transformation_names),
    )

    # Validate transformation count matches indicator count
    if len(transformation_names) != len(indicator_deps):
        raise ValueError(
            f"Signal {signal_name}: transformation count ({len(transformation_names)}) "
            f"must match indicator count ({len(indicator_deps)})"
        )

    # Step 1: Load and transform each indicator
    transformed_indicators: dict[str, pd.Series] = {}

    for indicator_name, transformation_name in zip(
        indicator_deps, transformation_names
    ):
        # Load indicator metadata
        indicator_metadata = indicator_registry.get_metadata(indicator_name)

        # Compute indicator (cached or fresh)
        indicator_series = compute_indicator(
            indicator_name=indicator_name,
            market_data=market_data,
            indicator_metadata=indicator_metadata,
        )

        # Load transformation metadata
        transformation_metadata = transformation_registry.get_metadata(
            transformation_name
        )

        # Apply transformation
        transformed = apply_signal_transformation(
            indicator_series,
            vars(transformation_metadata),
        )

        transformed_indicators[indicator_name] = transformed

    # Step 2: Combine indicators if multi-indicator signal
    if len(indicator_deps) == 1:
        # Single indicator - use directly
        signal = transformed_indicators[indicator_deps[0]]
    else:
        # Multi-indicator - apply composition logic
        if composition_logic is None:
            raise ValueError(
                f"Signal {signal_name}: composition_logic required for multi-indicator signals"
            )

        logger.debug("Applying composition logic: %s", composition_logic)

        # Build namespace for eval (indicator series only)
        namespace = transformed_indicators.copy()

        try:
            # Evaluate composition expression
            result = pd.eval(composition_logic, local_dict=namespace)
        except Exception as e:
            raise ValueError(
                f"Signal {signal_name}: composition_logic evaluation failed: {e}"
            ) from e

        # Ensure result is Series
        if not isinstance(result, pd.Series):
            raise ValueError(
                f"Signal {signal_name}: composition_logic must return pd.Series, got {type(result)}"
            )

        signal = result

    # Step 3: Apply sign multiplier
    final_signal: pd.Series = signal * sign_multiplier

    logger.info(
        "Signal composition complete: %d valid values", final_signal.notna().sum()
    )

    return final_signal
