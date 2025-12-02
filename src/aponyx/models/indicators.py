"""
Indicator computation functions for market metrics.

Indicators compute economically interpretable market metrics (spread differences,
ratios, momentum) in their natural units (basis points, ratios, percentages)
WITHOUT signal-level normalization (z-scores, percentile ranks).

This separation enables:
- Reusable indicators across multiple signals
- Independent testing and validation
- Clear governance boundaries
"""

import logging
from typing import Any

import pandas as pd

from ..config import INDICATOR_CACHE_DIR
from ..persistence.parquet_io import (
    generate_indicator_cache_key,
    load_indicator_from_cache,
    save_indicator_to_cache,
)

logger = logging.getLogger(__name__)


def compute_cdx_etf_spread_diff(
    cdx_df: pd.DataFrame,
    etf_df: pd.DataFrame,
    parameters: dict[str, Any],
) -> pd.Series:
    """
    Compute CDX spread minus ETF spread in basis points.

    This is the raw basis between CDX index spreads and ETF-implied spreads
    without normalization. Useful for identifying flow-driven mispricing.

    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with 'spread' column.
    etf_df : pd.DataFrame
        ETF spread data with 'spread' column.
    parameters : dict[str, Any]
        Indicator parameters (unused for this simple indicator).

    Returns
    -------
    pd.Series
        Spread difference in basis points.

    Notes
    -----
    Output units: basis_points
    Positive values: CDX spreads wider than ETF spreads (CDX expensive vs ETF)
    Negative values: CDX spreads tighter than ETF spreads (CDX cheap vs ETF)
    Economic interpretation: Measures relative value between CDX and ETF markets
    """
    logger.info(
        "Computing CDX-ETF spread difference: cdx_rows=%d, etf_rows=%d",
        len(cdx_df),
        len(etf_df),
    )

    # Align data to common dates
    cdx_spread = cdx_df["spread"]
    etf_spread = etf_df["spread"].reindex(cdx_df.index, method="ffill")

    # Compute raw difference (no normalization)
    spread_diff = cdx_spread - etf_spread

    valid_count = spread_diff.notna().sum()
    logger.debug("Generated %d valid spread difference values", valid_count)

    return spread_diff


def compute_spread_momentum(
    cdx_df: pd.DataFrame,
    parameters: dict[str, Any],
) -> pd.Series:
    """
    Compute short-term spread change in basis points.

    Captures spread momentum over the specified lookback period without
    volatility adjustment or normalization.

    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with 'spread' column.
    parameters : dict[str, Any]
        Must contain 'lookback': Number of periods for momentum calculation.

    Returns
    -------
    pd.Series
        Spread change in basis points.

    Notes
    -----
    Output units: basis_points
    Positive values: Spreads widening (credit deteriorating)
    Negative values: Spreads tightening (credit improving)
    Economic interpretation: Rate of spread change over lookback period
    Sign convention: Negative change (tightening) is favorable for credit
    """
    lookback = parameters.get("lookback", 5)

    logger.info(
        "Computing spread momentum: cdx_rows=%d, lookback=%d",
        len(cdx_df),
        lookback,
    )

    spread = cdx_df["spread"]

    # Compute spread change over lookback period
    spread_change = spread.diff(lookback)

    valid_count = spread_change.notna().sum()
    logger.debug("Generated %d valid momentum values", valid_count)

    return spread_change


def compute_cdx_vix_deviation_gap(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    parameters: dict[str, Any],
) -> pd.Series:
    """
    Compute gap between CDX and VIX deviations from their means.

    Identifies cross-asset risk sentiment divergence by comparing how far
    each asset is from its recent average level.

    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spreads with 'spread' column.
    vix_df : pd.DataFrame
        VIX levels with 'level' column.
    parameters : dict[str, Any]
        Must contain 'lookback': Window for computing mean deviations.

    Returns
    -------
    pd.Series
        Deviation gap in basis points.

    Notes
    -----
    Output units: basis_points (approximate, combining CDX bps and VIX points)
    Positive values: Credit stress > equity stress (CDX elevated relative to VIX)
    Negative values: Equity stress > credit stress (VIX elevated relative to CDX)
    Economic interpretation: Cross-asset risk sentiment divergence
    """
    lookback = parameters.get("lookback", 20)

    logger.info(
        "Computing CDX-VIX deviation gap: cdx_rows=%d, vix_rows=%d, lookback=%d",
        len(cdx_df),
        len(vix_df),
        lookback,
    )

    # Align data to common dates
    cdx = cdx_df["spread"]
    vix = vix_df["level"].reindex(cdx_df.index, method="ffill")

    # Compute deviations from rolling means
    cdx_mean = cdx.rolling(window=lookback, min_periods=lookback // 2).mean()
    cdx_deviation = cdx - cdx_mean

    vix_mean = vix.rolling(window=lookback, min_periods=lookback // 2).mean()
    vix_deviation = vix - vix_mean

    # Raw gap: CDX stress minus VIX stress
    gap = cdx_deviation - vix_deviation

    valid_count = gap.notna().sum()
    logger.debug("Generated %d valid deviation gap values", valid_count)

    return gap


def compute_indicator(
    indicator_name: str,
    market_data: dict[str, pd.DataFrame],
    indicator_metadata: Any,
    use_cache: bool = True,
) -> pd.Series:
    """
    Orchestration function for indicator computation with caching.

    Parameters
    ----------
    indicator_name : str
        Name of the indicator to compute.
    market_data : dict[str, pd.DataFrame]
        Market data required for indicator computation.
        Keys should match data_requirements in indicator metadata.
    indicator_metadata : IndicatorMetadata
        Metadata containing compute function, parameters, and requirements.
    use_cache : bool, default True
        Whether to use cached values if available.

    Returns
    -------
    pd.Series
        Computed indicator time series.

    Raises
    ------
    ValueError
        If required market data is missing or compute function not found.

    Examples
    --------
    >>> from aponyx.models.registry import IndicatorRegistry
    >>> from aponyx.config import INDICATOR_CATALOG_PATH
    >>> registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
    >>> metadata = registry.get_metadata("cdx_etf_spread_diff")
    >>> market_data = {"cdx": cdx_df, "etf": etf_df}
    >>> indicator = compute_indicator(
    ...     "cdx_etf_spread_diff",
    ...     market_data,
    ...     metadata,
    ...     use_cache=True
    ... )
    """
    logger.info("Computing indicator: name=%s, use_cache=%s", indicator_name, use_cache)

    # Check cache if enabled
    if use_cache:
        cache_key = generate_indicator_cache_key(
            indicator_name,
            indicator_metadata.parameters,
            market_data,
        )
        cached_result = load_indicator_from_cache(cache_key, INDICATOR_CACHE_DIR)
        if cached_result is not None:
            logger.info("Using cached indicator: name=%s", indicator_name)
            return cached_result

    # Get compute function from this module's namespace
    import sys

    current_module = sys.modules[__name__]
    compute_fn_name = indicator_metadata.compute_function_name
    if not hasattr(current_module, compute_fn_name):
        raise ValueError(
            f"Compute function '{compute_fn_name}' not found in indicators module"
        )

    compute_fn = getattr(current_module, compute_fn_name)

    # Prepare arguments based on data requirements
    args = []
    for data_key in sorted(indicator_metadata.data_requirements.keys()):
        if data_key not in market_data:
            raise ValueError(
                f"Missing required market data '{data_key}' for indicator '{indicator_name}'"
            )
        args.append(market_data[data_key])

    # Add parameters as last argument
    args.append(indicator_metadata.parameters)

    # Compute indicator
    logger.debug("Calling compute function: %s", compute_fn_name)
    result: pd.Series = compute_fn(*args)

    # Cache result if enabled
    if use_cache:
        save_indicator_to_cache(result, cache_key, INDICATOR_CACHE_DIR)

    logger.info("Computed indicator: name=%s, values=%d", indicator_name, len(result))
    return result
