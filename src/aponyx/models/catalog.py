"""
Signal computation orchestration using registry pattern.
"""

import logging

import pandas as pd

from . import signals
from .config import SignalConfig
from .registry import SignalRegistry, SignalMetadata

logger = logging.getLogger(__name__)


def compute_registered_signals(
    registry: SignalRegistry,
    market_data: dict[str, pd.DataFrame],
    config: SignalConfig,
) -> dict[str, pd.Series]:
    """
    Compute all enabled signals from registry using provided market data.

    Validates data requirements, resolves compute functions dynamically,
    and executes signal computations in registration order.

    Parameters
    ----------
    registry : SignalRegistry
        Signal registry containing metadata and catalog.
    market_data : dict[str, pd.DataFrame]
        Market data mapping. Keys should match signal data_requirements.
        Example: {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}
    config : SignalConfig
        Configuration parameters for signal computation (lookback, min_periods).

    Returns
    -------
    dict[str, pd.Series]
        Mapping from signal name to computed signal series.

    Raises
    ------
    ValueError
        If required market data is missing or lacks required columns.
    AttributeError
        If compute function name does not exist in signals module.

    Examples
    --------
    >>> registry = SignalRegistry("signal_catalog.json")
    >>> market_data = {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}
    >>> config = SignalConfig(lookback=20)
    >>> signals_dict = compute_registered_signals(registry, market_data, config)
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
