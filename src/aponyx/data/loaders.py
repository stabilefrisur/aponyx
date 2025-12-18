"""
Data loading utilities for signal-required data aggregation.

Provides helpers for generic instrument loading without hardcoded instrument logic.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from .registry import DataRegistry
    from ..models.registry import IndicatorTransformationRegistry, SignalRegistry


logger = logging.getLogger(__name__)


def load_instrument_from_raw(
    data_dir: Path,
    instrument: str,
    fetch_fn: Callable,
    securities: list[str] | None = None,
) -> pd.DataFrame:
    """
    Load instrument data from raw files using fetch function.

    Generic loader that handles both single-security (VIX) and multi-security
    (CDX, ETF) instruments. Uses FileSource with registry for security-based lookup.

    Parameters
    ----------
    data_dir : Path
        Raw data directory (e.g., data/raw/synthetic).
    instrument : str
        Instrument type (cdx, vix, etf).
    fetch_fn : Callable
        Fetch function to use for loading and validation.
        Signature: fetch_fn(source, security=..., use_cache=True) -> pd.DataFrame
    securities : list[str] or None
        List of security identifiers for multi-security instruments.
        If None, loads single security based on instrument type.

    Returns
    -------
    pd.DataFrame
        Loaded and validated instrument data with DatetimeIndex.

    Raises
    ------
    ValueError
        If registry not found or securities not in registry.
    FileNotFoundError
        If registry file doesn't exist.

    Examples
    --------
    >>> from aponyx.data import fetch_vix, fetch_cdx, FileSource
    >>> # Single security (VIX)
    >>> df = load_instrument_from_raw(
    ...     Path("data/raw/synthetic"),
    ...     "vix",
    ...     fetch_vix,
    ...     securities=None
    ... )
    >>> # Multi-security (CDX)
    >>> df = load_instrument_from_raw(
    ...     Path("data/raw/synthetic"),
    ...     "cdx",
    ...     fetch_cdx,
    ...     securities=["cdx_ig_5y", "cdx_hy_5y"]
    ... )
    """
    from .sources import FileSource

    # Initialize FileSource with registry
    source = FileSource(data_dir)

    if securities is None:
        # Single-security instrument (e.g., VIX)
        # Use instrument type as security ID
        security = instrument
        logger.debug("Loading %s from %s", instrument.upper(), data_dir)
        df = fetch_fn(
            source,
            security=security,
            use_cache=True,
        )
        return df

    # Multi-security instrument (e.g., CDX, ETF)
    dfs = []
    for security in securities:
        logger.debug("Loading %s from registry", security)
        df_sec = fetch_fn(
            source,
            security=security,
            use_cache=True,
        )
        dfs.append(df_sec)

    if not dfs:
        raise ValueError(
            f"No {instrument.upper()} data loaded. "
            f"Check that securities exist in registry: {data_dir / 'registry.json'}"
        )

    # Concatenate all securities
    df = pd.concat(dfs, axis=0).sort_index()

    # Remove duplicates if present (can occur when combining securities)
    if df.index.duplicated().any():
        n_dups = df.index.duplicated().sum()
        logger.debug(
            "Removing %d duplicate dates from %d securities",
            n_dups,
            len(dfs),
        )
        df = df[~df.index.duplicated(keep="last")]

    logger.info("Loaded %s from raw files: %d rows", instrument.upper(), len(df))
    return df


def load_signal_required_data(
    signal_registry: "SignalRegistry",
    data_registry: "DataRegistry",
    indicator_registry: "IndicatorTransformationRegistry | None" = None,
    security_mapping: dict[str, str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Load all market data required by enabled signals.

    Collects data requirements from all enabled signals via their indicator
    transformations and loads corresponding datasets from the data registry.
    Uses default_securities from indicator catalog unless overridden by
    security_mapping.

    Parameters
    ----------
    signal_registry : SignalRegistry
        Signal registry with enabled signal definitions.
    data_registry : DataRegistry
        Data registry for loading datasets by security ID.
    indicator_registry : IndicatorTransformationRegistry or None
        Indicator transformation registry for looking up default_securities.
        If None, will be loaded from config.INDICATOR_TRANSFORMATION_PATH.
    security_mapping : dict[str, str] or None
        Optional mapping to override default securities.
        Keys are instrument types (e.g., "cdx", "etf").
        Values are security IDs (e.g., "cdx_hy_5y", "hyg").

    Returns
    -------
    dict[str, pd.DataFrame]
        Market data mapping with all required instruments.
        Keys are generic identifiers (e.g., "cdx", "etf", "vix").

    Examples
    --------
    >>> from aponyx.models import SignalRegistry, IndicatorTransformationRegistry
    >>> from aponyx.data import DataRegistry
    >>> signal_reg = SignalRegistry("signal_catalog.json")
    >>> indicator_reg = IndicatorTransformationRegistry("indicator_transformation.json")
    >>> data_reg = DataRegistry("registry.json", "data/")
    >>> # Use default securities from catalog
    >>> data = load_signal_required_data(signal_reg, data_reg, indicator_reg)
    >>> # Override with custom securities
    >>> data = load_signal_required_data(
    ...     signal_reg,
    ...     data_reg,
    ...     indicator_reg,
    ...     security_mapping={"cdx": "cdx_hy_5y", "etf": "hyg"}
    ... )

    Notes
    -----
    For each enabled signal, retrieves the indicator transformation and uses
    its default_securities to map instrument types to specific security IDs.
    If security_mapping is provided, it overrides the defaults.
    """
    # Load indicator registry if not provided
    if indicator_registry is None:
        from ..config import INDICATOR_TRANSFORMATION_PATH
        from ..models.registry import IndicatorTransformationRegistry

        indicator_registry = IndicatorTransformationRegistry(
            INDICATOR_TRANSFORMATION_PATH
        )

    # Build mapping from instrument type to security ID
    # by collecting default_securities from indicator transformations
    instrument_to_security = {}
    for signal_name, signal_metadata in signal_registry.get_enabled().items():
        indicator_metadata = indicator_registry.get_metadata(
            signal_metadata.indicator_transformation
        )
        for inst_type, security_id in indicator_metadata.default_securities.items():
            # If multiple signals specify the same instrument type,
            # the last one wins (consistent behavior across codebase)
            instrument_to_security[inst_type] = security_id

    # Apply overrides if provided
    if security_mapping:
        for inst_type, security_id in security_mapping.items():
            logger.info(
                "Overriding default security for %s: %s -> %s",
                inst_type,
                instrument_to_security.get(inst_type, "N/A"),
                security_id,
            )
            instrument_to_security[inst_type] = security_id

    # Load data for each instrument type using the mapped security
    market_data = {}
    for inst_type, security_id in sorted(instrument_to_security.items()):
        # Use registry helper to find and load dataset by security ID
        df = data_registry.load_dataset_by_security(security_id)
        market_data[inst_type] = df

    return market_data
