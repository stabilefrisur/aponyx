"""
Signal computation orchestration using registry pattern.

This module orchestrates batch signal computation from the signal catalog.
It coordinates between signal metadata (registry.py, metadata.py) and
signal composition (signal_composer.py) via the indicator + transformation pattern.

Design Notes
------------
market_data dict pattern:
    The orchestrator accepts a dict mapping generic keys (e.g., "cdx", "etf")
    to DataFrame objects. This enables catalog-driven computation where:

    1. Different signals require different data combinations
    2. Indicators define requirements declaratively via data_requirements
    3. Orchestrator resolves data dynamically for indicator computation

    Alternative approaches considered:
    - Named parameters: Inflexible, requires knowing all data types upfront
    - Auto-loading from DataRegistry: Couples signal computation to data loading

    The dict pattern is kept for flexibility despite adding indirection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from .metadata import SignalMetadata

if TYPE_CHECKING:
    from .registry import SignalRegistry

logger = logging.getLogger(__name__)


def compute_registered_signals(
    registry: SignalRegistry,
    market_data: dict[str, pd.DataFrame],
) -> dict[str, pd.Series]:
    """
    Compute all enabled signals from registry using provided market data.

    Validates data requirements and executes signal compositions via the
    indicator + transformation pattern.

    Correct Usage Pattern
    ---------------------
    1. Get all required data keys: `aponyx.data.requirements.get_required_data_keys()`
    2. Load all required data into market_data dict
    3. Compute all enabled signals at once with this function
    4. Select individual signals for evaluation/backtesting

    This batch computation approach is efficient because:
    - Data is loaded once (not per-signal)
    - All signals computed in single pass
    - Results can be cached/reused for different analyses

    Parameters
    ----------
    registry : SignalRegistry
        Signal registry containing metadata and catalog.
    market_data : dict[str, pd.DataFrame]
        Market data mapping. Keys should match indicator data_requirements.
        Must contain ALL data keys required by ANY enabled signal.
        Example: {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}

        The dict pattern enables catalog-driven computation where different
        signals can specify different data requirements without hardcoding.

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.
        Contains one entry per enabled signal in the registry.

    Raises
    ------
    ValueError
        If required market data is missing or lacks required columns.

    Examples
    --------
    Correct pattern (load all data once, compute all signals):

    >>> from aponyx.config import SIGNAL_CATALOG_PATH
    >>> from aponyx.data.requirements import get_required_data_keys
    >>> from aponyx.models import SignalRegistry, compute_registered_signals
    >>>
    >>> # 1. Get required data keys from catalog
    >>> required_keys = get_required_data_keys(SIGNAL_CATALOG_PATH)  # {"cdx", "etf", "vix"}
    >>>
    >>> # 2. Load all required data once
    >>> market_data = {}
    >>> for key in required_keys:
    ...     market_data[key] = load_data_for(key)
    >>>
    >>> # 3. Compute all enabled signals
    >>> registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    >>> all_signals = compute_registered_signals(registry, market_data)
    >>>
    >>> # 4. Use individual signals for analysis
    >>> basis_signal = all_signals["cdx_etf_basis"]
    >>> gap_signal = all_signals["cdx_vix_gap"]

    Notes
    -----
    The market_data dict keys must match the keys in each indicator's
    data_requirements field from the catalog. For example, if an indicator
    specifies {"cdx": "spread", "vix": "level"}, then market_data must
    contain keys "cdx" and "vix" with DataFrames having those columns.

    Use aponyx.data.requirements.get_required_data_keys() to determine
    what data to load before calling this function.
    """
    enabled_signals = registry.get_enabled()

    logger.info(
        "Computing %d enabled signals: %s",
        len(enabled_signals),
        ", ".join(sorted(enabled_signals.keys())),
    )

    results: dict[str, pd.Series] = {}

    for signal_name, metadata in enabled_signals.items():
        try:
            signal_series = _compute_signal(metadata, market_data)
            results[signal_name] = signal_series

            logger.debug(
                "Computed signal '%s': valid_obs=%d",
                signal_name,
                signal_series.notna().sum(),
            )

        except Exception as e:
            logger.error(
                "Failed to compute signal '%s': %s",
                signal_name,
                e,
                exc_info=True,
            )
            raise

    logger.info("Successfully computed %d signals", len(results))
    return results


def _compute_signal(
    metadata: SignalMetadata,
    market_data: dict[str, pd.DataFrame],
) -> pd.Series:
    """
    Compute a single signal using four-stage transformation pipeline.

    Applies sign multiplier from catalog metadata (already applied in compose_signal).

    Parameters
    ----------
    metadata : SignalMetadata
        Signal metadata with indicator_transformation, score_transformation, signal_transformation.
    market_data : dict[str, pd.DataFrame]
        Available market data.

    Returns
    -------
    pd.Series
        Computed signal (sign multiplier already applied).

    Raises
    ------
    ValueError
        If required data is missing or lacks required columns.
    """
    from ..config import (
        INDICATOR_TRANSFORMATION_PATH,
        SCORE_TRANSFORMATION_PATH,
        SIGNAL_CATALOG_PATH,
        SIGNAL_TRANSFORMATION_PATH,
    )
    from .registry import (
        IndicatorTransformationRegistry,
        ScoreTransformationRegistry,
        SignalRegistry,
        SignalTransformationRegistry,
    )
    from .signal_composer import compose_signal

    # Lazy-load registries
    indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
    score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
    signal_transformation_registry = SignalTransformationRegistry(
        SIGNAL_TRANSFORMATION_PATH
    )
    signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

    # Compose signal using four-stage pipeline
    # (sign multiplier already applied within compose_signal)
    signal = compose_signal(
        signal_name=metadata.name,
        market_data=market_data,
        indicator_registry=indicator_registry,
        score_registry=score_registry,
        signal_transformation_registry=signal_transformation_registry,
        signal_registry=signal_registry,
        include_intermediates=False,
    )

    return signal
