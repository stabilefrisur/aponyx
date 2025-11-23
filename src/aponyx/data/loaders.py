"""
Data loading utilities for raw file discovery and multi-security aggregation.

Provides helpers for generic instrument loading without hardcoded instrument logic.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from .registry import DataRegistry
    from ..models.registry import SignalRegistry


logger = logging.getLogger(__name__)


def find_raw_file(
    data_dir: Path,
    instrument: str,
    security: str | None = None,
) -> Path | None:
    """
    Find raw data file for given instrument/security.

    Searches for parquet files matching the pattern:
    - With security: {security}_*.parquet
    - Without security: {instrument}_*.parquet

    Parameters
    ----------
    data_dir : Path
        Directory to search (e.g., data/raw/synthetic).
    instrument : str
        Instrument type (cdx, vix, etf).
    security : str or None
        Security identifier if applicable.

    Returns
    -------
    Path or None
        Path to most recent data file if found, None otherwise.
        Most recent is determined by file modification time.

    Examples
    --------
    >>> find_raw_file(Path("data/raw/synthetic"), "vix")
    Path("data/raw/synthetic/vix_abc123.parquet")
    >>> find_raw_file(Path("data/raw/synthetic"), "cdx", "cdx_ig_5y")
    Path("data/raw/synthetic/cdx_ig_5y_def456.parquet")
    """
    search_pattern = security if security else instrument
    matches = list(data_dir.glob(f"{search_pattern}_*.parquet"))

    if not matches:
        return None

    # Return most recent file (by modification time)
    return sorted(matches, key=lambda p: p.stat().st_mtime)[-1]


def concat_multi_security(
    dfs: list[pd.DataFrame],
    instrument: str,
) -> pd.DataFrame:
    """
    Concatenate DataFrames for multiple securities with duplicate handling.

    Performs outer join to handle different date ranges across securities.
    Removes duplicate index entries (keeps last) after concatenation.

    Parameters
    ----------
    dfs : list[pd.DataFrame]
        List of DataFrames to concatenate, each with DatetimeIndex.
    instrument : str
        Instrument type for logging context (e.g., "CDX", "ETF").

    Returns
    -------
    pd.DataFrame
        Concatenated and sorted DataFrame with duplicates removed.

    Notes
    -----
    Uses outer join to preserve all dates across securities.
    Duplicate handling uses "last" strategy to prefer most recent data.
    """
    if not dfs:
        raise ValueError("Cannot concatenate empty DataFrame list")

    # Concatenate with outer join for different date ranges
    df = pd.concat(dfs, axis=0).sort_index()

    # Remove duplicates if present (expected when combining securities)
    if df.index.duplicated().any():
        n_dups = df.index.duplicated().sum()
        logger.debug(
            "Removing %d duplicate dates from %d securities (expected for multi-security instruments)",
            n_dups,
            len(dfs),
        )
        df = df[~df.index.duplicated(keep="last")]

    return df


def load_instrument_from_raw(
    data_dir: Path,
    instrument: str,
    fetch_fn: Callable,
    securities: list[str] | None = None,
) -> pd.DataFrame:
    """
    Load instrument data from raw files using fetch function.

    Generic loader that handles both single-security (VIX) and multi-security
    (CDX, ETF) instruments. Uses file discovery to find raw data files and
    fetch functions to load with proper validation.

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
        If None, loads single file for instrument.

    Returns
    -------
    pd.DataFrame
        Loaded and validated instrument data with DatetimeIndex.

    Raises
    ------
    ValueError
        If no data files found for instrument/securities.

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

    if securities is None:
        # Single-security instrument (e.g., VIX)
        file_path = find_raw_file(data_dir, instrument)
        if not file_path:
            raise ValueError(
                f"No {instrument.upper()} data file found in {data_dir}. "
                f"Run data generation or download workflow first."
            )

        logger.debug("Loading %s from %s", instrument.upper(), file_path)
        df = fetch_fn(
            FileSource(file_path),
            use_cache=True,
        )
        return df

    # Multi-security instrument (e.g., CDX, ETF)
    dfs = []
    for security in securities:
        file_path = find_raw_file(data_dir, instrument, security)
        if file_path:
            logger.debug("Loading %s from %s", security, file_path)
            df_sec = fetch_fn(
                FileSource(file_path),
                security=security,
                use_cache=True,
            )
            dfs.append(df_sec)

    if not dfs:
        raise ValueError(
            f"No {instrument.upper()} data files found in {data_dir}. "
            f"Run data generation or download workflow first."
        )

    # Concatenate all securities
    df = concat_multi_security(dfs, instrument.upper())
    logger.info("Loaded %s from raw files: %d rows", instrument.upper(), len(df))
    return df


def load_signal_required_data(
    signal_registry: "SignalRegistry",
    data_registry: "DataRegistry",
    security_mapping: dict[str, str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Load all market data required by enabled signals.

    Collects data requirements from all enabled signals and loads
    corresponding datasets from the data registry. Uses default_securities
    from signal catalog unless overridden by security_mapping.

    Parameters
    ----------
    signal_registry : SignalRegistry
        Signal registry with enabled signal definitions.
    data_registry : DataRegistry
        Data registry for loading datasets by security ID.
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
    >>> from aponyx.models import SignalRegistry
    >>> from aponyx.data import DataRegistry
    >>> signal_reg = SignalRegistry("signal_catalog.json")
    >>> data_reg = DataRegistry("registry.json", "data/")
    >>> # Use default securities from catalog
    >>> data = load_signal_required_data(signal_reg, data_reg)
    >>> # Override with custom securities
    >>> data = load_signal_required_data(
    ...     signal_reg,
    ...     data_reg,
    ...     security_mapping={"cdx": "cdx_hy_5y", "etf": "hyg"}
    ... )

    Notes
    -----
    For each enabled signal, uses default_securities to map
    instrument types to specific security IDs. If security_mapping
    is provided, it overrides the defaults for specified instruments.
    """
    # Build mapping from instrument type to security ID
    # by collecting default_securities from all enabled signals
    instrument_to_security = {}
    for signal_name, metadata in signal_registry.get_enabled().items():
        for inst_type, security_id in metadata.default_securities.items():
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
