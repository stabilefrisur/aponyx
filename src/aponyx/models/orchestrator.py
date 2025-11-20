"""
Signal computation orchestration using registry pattern.

This module orchestrates batch signal computation from the signal catalog.
It bridges the gap between signal metadata (registry.py, metadata.py) and
signal computation functions (signals.py).

Design Notes
------------
market_data dict pattern:
    The orchestrator accepts a dict mapping generic keys (e.g., "cdx", "etf")
    to DataFrame objects. This enables catalog-driven computation where:
    
    1. Different signals require different data combinations
    2. Catalog defines requirements declaratively via data_requirements
    3. Orchestrator resolves data dynamically using arg_mapping
    
    Alternative approaches considered:
    - Named parameters: Inflexible, requires knowing all data types upfront
    - Auto-loading from DataRegistry: Couples signal computation to data loading
    
    The dict pattern is kept for flexibility despite adding indirection.

arg_mapping pattern:
    Uses positional argument mapping for simplicity in pilot phase.
    Alternative keyword-based approach ({"cdx": "cdx_param"}) was considered
    but rejected to avoid complexity. May revisit in future if needed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from . import signals
from .config import SignalConfig
from .metadata import SignalMetadata

if TYPE_CHECKING:
    from .registry import SignalRegistry

logger = logging.getLogger(__name__)


def get_required_data_keys(registry: SignalRegistry) -> set[str]:
    """
    Get union of all data keys required by enabled signals.
    
    Use this to determine what market data to load before calling
    compute_registered_signals(). The correct workflow is:
    
    1. Get required data keys from registry
    2. Load all required data into market_data dict
    3. Compute all enabled signals at once
    
    Parameters
    ----------
    registry : SignalRegistry
        Signal registry containing enabled signals.
    
    Returns
    -------
    set[str]
        Set of data keys (e.g., {"cdx", "etf", "vix"}) required
        by all enabled signals.
    
    Examples
    --------
    >>> registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    >>> data_keys = get_required_data_keys(registry)
    >>> # Load all required data
    >>> market_data = {}
    >>> for key in data_keys:
    ...     market_data[key] = load_data_for(key)
    >>> # Compute all signals at once
    >>> signals = compute_registered_signals(registry, market_data, config)
    """
    all_data_keys = set()
    for metadata in registry.get_enabled().values():
        all_data_keys.update(metadata.data_requirements.keys())
    
    logger.debug(
        "Required data keys for %d enabled signals: %s",
        len(registry.get_enabled()),
        sorted(all_data_keys),
    )
    
    return all_data_keys


def compute_registered_signals(
    registry: SignalRegistry,
    market_data: dict[str, pd.DataFrame],
    config: SignalConfig,
) -> dict[str, pd.Series]:
    """
    Compute all enabled signals from registry using provided market data.

    Validates data requirements, resolves compute functions dynamically,
    and executes signal computations in registration order.
    
    Correct Usage Pattern
    ---------------------
    1. Get all required data keys: `get_required_data_keys(registry)`
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
        Market data mapping. Keys should match signal data_requirements.
        Must contain ALL data keys required by ANY enabled signal.
        Example: {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}
        
        The dict pattern enables catalog-driven computation where different
        signals can specify different data requirements without hardcoding.
    config : SignalConfig
        Configuration parameters for signal computation (lookback, min_periods).

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.
        Contains one entry per enabled signal in the registry.

    Raises
    ------
    ValueError
        If required market data is missing or lacks required columns.
    AttributeError
        If compute function name does not exist in signals module.

    Examples
    --------
    Correct pattern (load all data once, compute all signals):
    
    >>> from aponyx.models import SignalRegistry, SignalConfig
    >>> from aponyx.models import get_required_data_keys, compute_registered_signals
    >>> 
    >>> # 1. Get required data keys from registry
    >>> registry = SignalRegistry("signal_catalog.json")
    >>> required_keys = get_required_data_keys(registry)  # {"cdx", "etf", "vix"}
    >>> 
    >>> # 2. Load all required data once
    >>> market_data = {}
    >>> for key in required_keys:
    ...     market_data[key] = load_data_for(key)
    >>> 
    >>> # 3. Compute all enabled signals
    >>> config = SignalConfig(lookback=20)
    >>> all_signals = compute_registered_signals(registry, market_data, config)
    >>> 
    >>> # 4. Use individual signals for analysis
    >>> basis_signal = all_signals["cdx_etf_basis"]
    >>> gap_signal = all_signals["cdx_vix_gap"]
    
    Notes
    -----
    The market_data dict keys must match the keys in each signal's
    data_requirements field from the catalog. For example, if a signal
    specifies {"cdx": "spread", "vix": "level"}, then market_data must
    contain keys "cdx" and "vix" with DataFrames having those columns.
    
    Use get_required_data_keys() to determine what data to load before
    calling this function.
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
            signal_series = _compute_signal(metadata, market_data, config)
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
    config: SignalConfig,
) -> pd.Series:
    """
    Compute a single signal using metadata specification.

    Applies sign multiplier from catalog metadata.

    Parameters
    ----------
    metadata : SignalMetadata
        Signal metadata with data requirements and function mapping.
    market_data : dict[str, pd.DataFrame]
        Available market data.
    config : SignalConfig
        Signal computation parameters.

    Returns
    -------
    pd.Series
        Computed signal with sign multiplier applied.

    Raises
    ------
    ValueError
        If required data is missing or lacks required columns.
    AttributeError
        If compute function does not exist in signals module.
    """
    # Validate all required data is available
    _validate_data_requirements(metadata, market_data)

    # Resolve compute function from signals module
    compute_fn = getattr(signals, metadata.compute_function_name)

    # Build positional arguments from arg_mapping
    args = [market_data[key] for key in metadata.arg_mapping]

    # Call compute function with market data and config
    raw_signal = compute_fn(*args, config)

    # Apply sign multiplier from catalog
    signal = raw_signal * metadata.sign_multiplier

    if metadata.sign_multiplier == -1:
        logger.debug(
            "Applied sign inversion to signal '%s'",
            metadata.name,
        )

    return signal


def _validate_data_requirements(
    metadata: SignalMetadata,
    market_data: dict[str, pd.DataFrame],
) -> None:
    """
    Validate market data satisfies signal's data requirements.

    Parameters
    ----------
    metadata : SignalMetadata
        Signal metadata with data requirements.
    market_data : dict[str, pd.DataFrame]
        Available market data.

    Raises
    ------
    ValueError
        If required data key is missing or DataFrame lacks required column.
    """
    for data_key, required_column in metadata.data_requirements.items():
        # Check data key exists
        if data_key not in market_data:
            raise ValueError(
                f"Signal '{metadata.name}' requires market data key '{data_key}'. "
                f"Available keys: {sorted(market_data.keys())}"
            )

        # Check required column exists in DataFrame
        df = market_data[data_key]
        if required_column not in df.columns:
            raise ValueError(
                f"Signal '{metadata.name}' requires column '{required_column}' "
                f"in '{data_key}' data. Available columns: {list(df.columns)}"
            )
