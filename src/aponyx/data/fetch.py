"""
Unified data fetching interface with provider abstraction.

Fetch functions handle data acquisition from any source (file, Bloomberg, API)
with automatic validation and optional caching.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..config import DATA_DIR, CACHE_ENABLED, CACHE_TTL_DAYS, REGISTRY_PATH
from ..persistence import save_json, save_parquet
from .bloomberg_config import get_bloomberg_ticker
from .registry import DataRegistry
from .cache import get_cached_data, save_to_cache
from .sources import DataSource, BloombergSource, resolve_provider
from .providers.file import fetch_from_file
from .providers.bloomberg import fetch_from_bloomberg
from .validation import validate_cdx_schema, validate_vix_schema, validate_etf_schema

logger = logging.getLogger(__name__)


def save_to_raw(
    df: pd.DataFrame,
    provider: str,
    security: str,
    raw_dir: Path,
    registry: DataRegistry | None = None,
    **metadata_params,
) -> Path:
    """
    Save fetched data to raw storage (permanent source of truth).

    Unlike cache, raw data is never deleted automatically.
    Raw storage represents the original data as fetched from external sources.
    Uses hash-based naming for uniqueness and permanence.

    Parameters
    ----------
    df : pd.DataFrame
        Data to save.
    provider : str
        Data provider name (e.g., "bloomberg", "synthetic").
    security : str
        Security identifier (e.g., "cdx_ig_5y", "vix", "hyg").
    raw_dir : Path
        Base raw directory path.
    registry : DataRegistry or None
        Optional registry to track the saved dataset.
    **metadata_params : Any
        Additional metadata to include in the sidecar JSON file.

    Returns
    -------
    Path
        Path to saved raw file.

    Notes
    -----
    Creates provider subdirectory if it doesn't exist.
    Files are named: {security}_{hash}.parquet
    Metadata is saved as: {security}_{hash}.json
    Hash ensures uniqueness across different date ranges and parameters.
    """
    provider_dir = raw_dir / provider
    provider_dir.mkdir(parents=True, exist_ok=True)

    # Generate hash from content and metadata for uniqueness
    safe_security = security.replace(".", "_").replace("/", "_")
    hash_input = "|".join(
        [
            provider,
            security,
            str(df.index.min()),
            str(df.index.max()),
            str(len(df)),
            str(sorted(metadata_params.items())),
        ]
    )
    file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    filename = f"{safe_security}_{file_hash}.parquet"
    raw_path = provider_dir / filename

    # Save data
    save_parquet(df, raw_path)
    logger.info("Saved to raw storage: path=%s, rows=%d", raw_path, len(df))

    # Save metadata sidecar JSON
    metadata = {
        "provider": provider,
        "security": security,
        "stored_at": datetime.now().isoformat(),
        "date_range": {
            "start": str(df.index.min()),
            "end": str(df.index.max()),
        },
        "row_count": len(df),
        "columns": list(df.columns),
        "hash": file_hash,
        **metadata_params,
    }
    metadata_path = provider_dir / f"{safe_security}_{file_hash}.json"
    save_json(metadata, metadata_path)
    logger.debug("Saved metadata: %s", metadata_path)

    # Register in data registry
    if registry is not None:
        registry.register_dataset(
            name=f"raw_{provider}_{security}_{file_hash}",
            file_path=raw_path,
            instrument=security,
            metadata=metadata,
        )

    return raw_path


def _get_provider_fetch_function(source: DataSource):
    """
    Get fetch function for data source with unified interface.

    Parameters
    ----------
    source : DataSource
        Data source configuration.

    Returns
    -------
    Callable
        Provider fetch function with unified signature:
        (source, ticker, instrument, security, start_date, end_date, **params)

    Notes
    -----
    Returns adapters that normalize provider-specific signatures to a unified
    interface. This allows callers to use the same call pattern regardless of
    provider type.
    """
    from typing import Any

    provider_type = resolve_provider(source)

    if provider_type == "file":
        return fetch_from_file
    elif provider_type == "bloomberg":
        # Adapter: accepts source for unified interface but doesn't use it
        def _bloomberg_adapter(
            source: DataSource,
            ticker: str,
            instrument: str,
            security: str,
            start_date: str | None = None,
            end_date: str | None = None,
            **params: Any,
        ) -> pd.DataFrame:
            # Bloomberg provider doesn't need source - it's stateless
            return fetch_from_bloomberg(
                ticker=ticker,
                instrument=instrument,
                security=security,
                start_date=start_date,
                end_date=end_date,
                **params,
            )

        return _bloomberg_adapter
    else:
        raise ValueError(f"Unsupported provider: {provider_type}")


def fetch_cdx(
    source: DataSource | None = None,
    security: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = CACHE_ENABLED,
    update_current_day: bool = False,
) -> pd.DataFrame:
    """
    Fetch CDX index spread data from configured source.

    Parameters
    ----------
    source : DataSource or None
        Data source. If None, uses default from config.
    security : str or None
        Security identifier (e.g., "cdx_ig_5y", "cdx_hy_5y").
        Used for Bloomberg ticker lookup and metadata.
    start_date : str or None
        Start date in YYYY-MM-DD format.
    end_date : str or None
        End date in YYYY-MM-DD format.
    use_cache : bool, default CACHE_ENABLED
        Whether to use cache.
    update_current_day : bool, default False
        If True and cache exists, only update today's data point using BDP.
        Useful for intraday refreshes without re-fetching entire history.
        Only applicable for Bloomberg source.

    Returns
    -------
    pd.DataFrame
        Validated CDX data with DatetimeIndex and columns:
        - spread: CDX spread in basis points
        - security: Security identifier (if present)

    Examples
    --------
    >>> from aponyx.data import fetch_cdx, FileSource, BloombergSource
    >>> df = fetch_cdx(FileSource("data/raw/cdx.parquet"), security="cdx_ig_5y")
    >>> df = fetch_cdx(BloombergSource(), security="cdx_ig_5y")
    >>> # Update only today's data point (intraday refresh)
    >>> df = fetch_cdx(BloombergSource(), security="cdx_ig_5y", update_current_day=True)
    """
    if source is None:
        raise ValueError("Data source must be specified for CDX fetch")

    if security is None:
        raise ValueError(
            "Security must be specified for CDX fetch (e.g., 'cdx_ig_5y', 'cdx_hy_5y')"
        )

    instrument = "cdx"
    cache_dir = DATA_DIR / "cache"

    # Check cache first
    if use_cache:
        cached = get_cached_data(
            source,
            security,
            cache_dir,
            start_date=start_date,
            end_date=end_date,
            ttl_days=CACHE_TTL_DAYS,
        )
        if cached is not None:
            # Handle update_current_day mode
            if update_current_day and isinstance(source, BloombergSource):
                from .cache import update_current_day as update_cache_day
                from .providers.bloomberg import fetch_current_from_bloomberg

                logger.info("Updating current day data from Bloomberg")

                # Get Bloomberg ticker
                ticker = get_bloomberg_ticker(security)

                # Fetch current data point
                current_df = fetch_current_from_bloomberg(
                    ticker=ticker,
                    instrument=instrument,
                    security=security,
                )

                # Handle non-trading days (no current data available)
                if current_df is None:
                    logger.info(
                        "No current data available (non-trading day), returning cached data"
                    )
                    if "security" in cached.columns:
                        return cached[cached["security"] == security]
                    return cached

                current_df = validate_cdx_schema(current_df)

                # Merge with cache
                df = update_cache_day(cached, current_df)

                # Save updated cache
                registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
                save_to_cache(
                    df,
                    source,
                    security,
                    cache_dir,
                    registry=registry,
                    start_date=start_date,
                    end_date=end_date,
                )

                # Apply security filter
                if "security" in df.columns:
                    return df[df["security"] == security]
                return df
            else:
                # Apply security filter
                if "security" in cached.columns:
                    return cached[cached["security"] == security]
                return cached

    # Fetch from source
    logger.info("Fetching CDX from %s", resolve_provider(source))
    fetch_fn = _get_provider_fetch_function(source)

    # Get ticker (Bloomberg ticker for Bloomberg, security ID for file)
    if isinstance(source, BloombergSource):
        ticker = get_bloomberg_ticker(security)
        logger.debug("Resolved security '%s' to Bloomberg ticker: %s", security, ticker)
    else:
        ticker = security  # File source uses security ID directly

    # Fetch with unified interface
    df = fetch_fn(
        source=source,
        ticker=ticker,
        instrument=instrument,
        security=security,
        start_date=start_date,
        end_date=end_date,
    )

    # Validate schema
    df = validate_cdx_schema(df)

    # Save Bloomberg data to raw storage (permanent source of truth)
    if isinstance(source, BloombergSource):
        from ..config import RAW_DIR

        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_raw(df, "bloomberg", security or instrument, RAW_DIR, registry)

    # Cache if enabled
    if use_cache:
        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_cache(
            df,
            source,
            security,
            cache_dir,
            registry=registry,
            start_date=start_date,
            end_date=end_date,
        )

    logger.info(
        "Fetched CDX data: %d rows, %s to %s", len(df), df.index.min(), df.index.max()
    )
    return df


def fetch_vix(
    source: DataSource | None = None,
    security: str = "vix",
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = CACHE_ENABLED,
    update_current_day: bool = False,
) -> pd.DataFrame:
    """
    Fetch VIX volatility index data from configured source.

    Parameters
    ----------
    source : DataSource or None
        Data source. If None, uses default from config.
    security : str, default "vix"
        Security identifier (always "vix" for VIX index).
    start_date : str or None
        Start date in YYYY-MM-DD format.
    end_date : str or None
        End date in YYYY-MM-DD format.
    use_cache : bool, default CACHE_ENABLED
        Whether to use cache.
    update_current_day : bool, default False
        If True and cache exists, only update today's data point using BDP.
        Only applicable for Bloomberg source.

    Returns
    -------
    pd.DataFrame
        Validated VIX data with DatetimeIndex and columns:
        - level: VIX closing level

    Examples
    --------
    >>> from aponyx.data import fetch_vix, FileSource, BloombergSource
    >>> df = fetch_vix(FileSource("data/raw/synthetic"))
    >>> # Update only today's data point (intraday refresh)
    >>> df = fetch_vix(BloombergSource(), update_current_day=True)
    """
    if source is None:
        raise ValueError("Data source must be specified for VIX fetch")

    instrument = "vix"
    cache_dir = DATA_DIR / "cache"

    # Check cache first
    if use_cache:
        cached = get_cached_data(
            source,
            security,
            cache_dir,
            start_date=start_date,
            end_date=end_date,
            ttl_days=CACHE_TTL_DAYS,
        )
        if cached is not None:
            # Handle update_current_day mode
            if update_current_day and isinstance(source, BloombergSource):
                from .cache import update_current_day as update_cache_day
                from .providers.bloomberg import fetch_current_from_bloomberg

                logger.info("Updating current day VIX data from Bloomberg")

                ticker = get_bloomberg_ticker(security)
                current_df = fetch_current_from_bloomberg(
                    ticker=ticker,
                    instrument=instrument,
                    security=security,
                )

                # Handle non-trading days (no current data available)
                if current_df is None:
                    logger.info(
                        "No current VIX data available (non-trading day), returning cached data"
                    )
                    return cached

                current_df = validate_vix_schema(current_df)

                # Merge with cache
                df = update_cache_day(cached, current_df)

                # Save updated cache
                registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
                save_to_cache(
                    df,
                    source,
                    security,
                    cache_dir,
                    registry=registry,
                    start_date=start_date,
                    end_date=end_date,
                )
                return df
            else:
                return cached

    # Fetch from source
    logger.info("Fetching VIX from %s", resolve_provider(source))
    fetch_fn = _get_provider_fetch_function(source)

    # Get ticker (Bloomberg ticker for Bloomberg, security ID for file)
    if isinstance(source, BloombergSource):
        ticker = get_bloomberg_ticker(security)
        logger.debug("Resolved security '%s' to Bloomberg ticker: %s", security, ticker)
    else:
        ticker = security  # File source uses security ID directly

    # Fetch with unified interface
    df = fetch_fn(
        source=source,
        ticker=ticker,
        instrument=instrument,
        security=security,
        start_date=start_date,
        end_date=end_date,
    )

    # Validate schema
    df = validate_vix_schema(df)

    # Save Bloomberg data to raw storage (permanent source of truth)
    if isinstance(source, BloombergSource):
        from ..config import RAW_DIR

        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_raw(df, "bloomberg", security, RAW_DIR, registry)

    # Cache if enabled
    if use_cache:
        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_cache(
            df,
            source,
            security,
            cache_dir,
            registry=registry,
            start_date=start_date,
            end_date=end_date,
        )

    logger.info(
        "Fetched VIX data: %d rows, %s to %s", len(df), df.index.min(), df.index.max()
    )
    return df


def fetch_etf(
    source: DataSource | None = None,
    security: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = CACHE_ENABLED,
    update_current_day: bool = False,
) -> pd.DataFrame:
    """
    Fetch credit ETF price data from configured source.

    Parameters
    ----------
    source : DataSource or None
        Data source. If None, uses default from config.
    security : str or None
        Security identifier (e.g., "hyg", "lqd").
        Used for Bloomberg ticker lookup and metadata.
    start_date : str or None
        Start date in YYYY-MM-DD format.
    end_date : str or None
        End date in YYYY-MM-DD format.
    use_cache : bool, default CACHE_ENABLED
        Whether to use cache.
    update_current_day : bool, default False
        If True and cache exists, only update today's data point using BDP.
        Only applicable for Bloomberg source.

    Returns
    -------
    pd.DataFrame
        Validated ETF data with DatetimeIndex and columns:
        - close: Closing price
        - security: Security identifier (if present)

    Examples
    --------
    >>> from aponyx.data import fetch_etf, FileSource, BloombergSource
    >>> df = fetch_etf(FileSource("data/raw/etf.parquet"), security="hyg")
    >>> df = fetch_etf(BloombergSource(), security="hyg")
    >>> # Update only today's data point (intraday refresh)
    >>> df = fetch_etf(BloombergSource(), security="hyg", update_current_day=True)
    """
    if source is None:
        raise ValueError("Data source must be specified for ETF fetch")

    if security is None:
        raise ValueError(
            "Security must be specified for ETF fetch (e.g., 'hyg', 'lqd')"
        )

    instrument = "etf"
    cache_dir = DATA_DIR / "cache"

    # Check cache first
    if use_cache:
        cached = get_cached_data(
            source,
            security,
            cache_dir,
            start_date=start_date,
            end_date=end_date,
            ttl_days=CACHE_TTL_DAYS,
        )
        if cached is not None:
            # Handle update_current_day mode
            if update_current_day and isinstance(source, BloombergSource):
                from .cache import update_current_day as update_cache_day
                from .providers.bloomberg import fetch_current_from_bloomberg

                logger.info("Updating current day ETF data from Bloomberg")

                # Get Bloomberg ticker
                ticker = get_bloomberg_ticker(security)

                # Fetch current data point
                current_df = fetch_current_from_bloomberg(
                    ticker=ticker,
                    instrument=instrument,
                    security=security,
                )

                # Handle non-trading days (no current data available)
                if current_df is None:
                    logger.info(
                        "No current ETF data available (non-trading day), returning cached data"
                    )
                    if "security" in cached.columns:
                        return cached[cached["security"] == security]
                    return cached

                current_df = validate_etf_schema(current_df)

                # Merge with cache
                df = update_cache_day(cached, current_df)

                # Save updated cache
                registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
                save_to_cache(
                    df,
                    source,
                    security,
                    cache_dir,
                    registry=registry,
                    start_date=start_date,
                    end_date=end_date,
                )

                # Apply security filter
                if "security" in df.columns:
                    return df[df["security"] == security]
                return df
            else:
                # Apply security filter
                if "security" in cached.columns:
                    return cached[cached["security"] == security]
                return cached

    # Fetch from source
    logger.info("Fetching ETF from %s", resolve_provider(source))
    fetch_fn = _get_provider_fetch_function(source)

    # Get ticker (Bloomberg ticker for Bloomberg, security ID for file)
    if isinstance(source, BloombergSource):
        ticker = get_bloomberg_ticker(security)
        logger.debug("Resolved security '%s' to Bloomberg ticker: %s", security, ticker)
    else:
        ticker = security  # File source uses security ID directly

    # Fetch with unified interface
    df = fetch_fn(
        source=source,
        ticker=ticker,
        instrument=instrument,
        security=security,
        start_date=start_date,
        end_date=end_date,
    )

    # Validate schema
    df = validate_etf_schema(df)

    # Save Bloomberg data to raw storage (permanent source of truth)
    if isinstance(source, BloombergSource):
        from ..config import RAW_DIR

        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_raw(df, "bloomberg", security or instrument, RAW_DIR, registry)

    # Cache if enabled
    if use_cache:
        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_cache(
            df,
            source,
            security,
            cache_dir,
            registry=registry,
            start_date=start_date,
            end_date=end_date,
        )

    logger.info(
        "Fetched ETF data: %d rows, %s to %s", len(df), df.index.min(), df.index.max()
    )
    return df


# =============================================================================
# Channel-aware data fetching functions (new API)
# =============================================================================

# Global singleton for security catalog (lazy-loaded)
_security_catalog: "SecurityCatalog | None" = None


def _get_security_catalog() -> "SecurityCatalog":
    """Get the global security catalog singleton."""
    global _security_catalog
    if _security_catalog is None:
        from ..config import BLOOMBERG_SECURITIES_PATH
        from .security_catalog import SecurityCatalog

        _security_catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
    return _security_catalog


def get_security_spec(security_id: str) -> "SecuritySpec":
    """
    Get security specification from catalog.

    Parameters
    ----------
    security_id : str
        Security identifier.

    Returns
    -------
    SecuritySpec
        Complete security specification including channels.

    Raises
    ------
    ValueError
        If security_id is unknown.

    Examples
    --------
    >>> spec = get_security_spec("cdx_hy_5y")
    >>> spec.instrument_type  # 'cdx'
    >>> spec.has_channel(DataChannel.SPREAD)  # True
    """

    catalog = _get_security_catalog()
    return catalog.get_spec(security_id)


def resolve_channel_for_purpose(
    security_id: str,
    purpose: "UsagePurpose",
    override: "DataChannel | None" = None,
) -> "DataChannel":
    """
    Resolve which channel to use for a security and purpose.

    Parameters
    ----------
    security_id : str
        Security identifier.
    purpose : UsagePurpose
        Why the data is being requested.
    override : DataChannel or None
        Explicit channel override.

    Returns
    -------
    DataChannel
        The channel to fetch.

    Raises
    ------
    ValueError
        If resolved channel is not available for security.

    Examples
    --------
    >>> from aponyx.data import resolve_channel_for_purpose, UsagePurpose, DataChannel
    >>> resolve_channel_for_purpose("cdx_ig_5y", UsagePurpose.INDICATOR)
    DataChannel.SPREAD
    >>> resolve_channel_for_purpose("vix", UsagePurpose.INDICATOR)
    DataChannel.LEVEL
    >>> resolve_channel_for_purpose("hyg", UsagePurpose.PNL)
    DataChannel.PRICE
    """

    catalog = _get_security_catalog()
    return catalog.resolve_channel(security_id, purpose, override)


def list_security_channels(security_id: str) -> list["DataChannel"]:
    """
    List available channels for a security.

    Parameters
    ----------
    security_id : str
        Security identifier.

    Returns
    -------
    list[DataChannel]
        Available channels.

    Examples
    --------
    >>> list_security_channels("cdx_hy_5y")
    [DataChannel.SPREAD, DataChannel.PRICE]
    >>> list_security_channels("vix")
    [DataChannel.LEVEL]
    """

    spec = get_security_spec(security_id)
    return spec.list_channels()


def fetch_security_data(
    source: DataSource,
    security_id: str,
    channels: list["DataChannel"] | None = None,
    purpose: "UsagePurpose | None" = None,
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = CACHE_ENABLED,
) -> pd.DataFrame:
    """
    Fetch security data for specified channels.

    This is the primary data fetching interface. Consumers should use this
    instead of fetch_cdx/fetch_vix/fetch_etf for channel-aware data access.

    Parameters
    ----------
    source : DataSource
        Data source (FileSource or BloombergSource).
    security_id : str
        Security identifier (e.g., "cdx_ig_5y", "hyg", "vix").
    channels : list[DataChannel] or None
        Specific channels to fetch. If None, uses purpose-based defaults.
    purpose : UsagePurpose or None
        Why data is being requested. Used for default channel resolution
        when channels is None.
    start_date : str or None
        Start date in YYYY-MM-DD format.
    end_date : str or None
        End date in YYYY-MM-DD format.
    use_cache : bool, default True
        Whether to use cached data if available.

    Returns
    -------
    pd.DataFrame
        Data with DatetimeIndex and channel names as columns.
        Inner join applied when multiple channels requested.

    Raises
    ------
    ValueError
        If security_id is unknown or requested channels unavailable.
        Includes clear guidance on how to resolve the issue.
    ChannelFetchError
        If one or more channel fetches fail (Bloomberg failures).
        Includes aggregated error messages for all failed channels.
    FileNotFoundError
        If the data file does not exist.

    Examples
    --------
    >>> from aponyx.data import fetch_security_data, FileSource, UsagePurpose, DataChannel
    >>> source = FileSource(Path("data/raw/synthetic"))
    >>>
    >>> # Fetch for indicator computation (uses instrument defaults)
    >>> df = fetch_security_data(source, "cdx_ig_5y", purpose=UsagePurpose.INDICATOR)
    >>> df.columns  # ['spread']
    >>>
    >>> # Fetch specific channels
    >>> df = fetch_security_data(source, "cdx_hy_5y", channels=[DataChannel.SPREAD, DataChannel.PRICE])
    >>> df.columns  # ['spread', 'price']
    >>>
    >>> # Fetch for P&L (uses quote_type)
    >>> df = fetch_security_data(source, "hyg", purpose=UsagePurpose.PNL)
    >>> df.columns  # ['price']
    """
    from .sources import FileSource

    # Get security specification with clear error on failure
    try:
        spec = get_security_spec(security_id)
    except ValueError as e:
        # Re-raise with additional guidance
        raise ValueError(
            f"{e}. "
            "Ensure the security is defined in bloomberg_securities.json "
            "with proper channels and quote_type configuration."
        ) from e

    # Determine which channels to fetch
    if channels is not None:
        # Validate requested channels are available
        unavailable_channels = []
        for channel in channels:
            if not spec.has_channel(channel):
                unavailable_channels.append(channel.value)

        if unavailable_channels:
            available = [c.value for c in spec.list_channels()]
            raise ValueError(
                f"Requested channels {unavailable_channels} not available for "
                f"security '{security_id}'. Available channels: {available}. "
                f"Either request different channels or update bloomberg_securities.json "
                f"to add the missing channel configuration."
            )
        channels_to_fetch = channels
    elif purpose is not None:
        # Use purpose-based default channel
        try:
            resolved_channel = resolve_channel_for_purpose(security_id, purpose)
        except ValueError as e:
            raise ValueError(
                f"Cannot resolve channel for {purpose.value} purpose: {e}. "
                f"Check that security '{security_id}' has the required channels "
                f"in bloomberg_securities.json."
            ) from e
        channels_to_fetch = [resolved_channel]
    else:
        # Fetch all available channels
        channels_to_fetch = spec.list_channels()

    logger.info(
        "Fetching security '%s' channels: %s",
        security_id,
        [c.value for c in channels_to_fetch],
    )

    # FileSource: load from multi-column parquet file
    if isinstance(source, FileSource):
        return _fetch_security_from_file(
            source=source,
            security_id=security_id,
            channels=channels_to_fetch,
            spec=spec,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )

    # BloombergSource: fetch each channel from its Bloomberg ticker
    if isinstance(source, BloombergSource):
        return _fetch_security_from_bloomberg(
            security_id=security_id,
            channels=channels_to_fetch,
            spec=spec,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )

    raise ValueError(
        f"Unsupported data source type: {type(source).__name__}. "
        f"Supported sources: FileSource, BloombergSource."
    )


def _fetch_security_from_file(
    source: "FileSource",
    security_id: str,
    channels: list["DataChannel"],
    spec: "SecuritySpec",
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Fetch security data from FileSource (multi-column parquet).

    Parameters
    ----------
    source : FileSource
        File source with security_mapping.
    security_id : str
        Security identifier.
    channels : list[DataChannel]
        Channels to extract from parquet file.
    spec : SecuritySpec
        Security specification.
    start_date : str or None
        Start date filter.
    end_date : str or None
        End date filter.
    use_cache : bool
        Whether to use cache.

    Returns
    -------
    pd.DataFrame
        Data with requested channel columns.

    Raises
    ------
    ValueError
        If security not in registry or channel columns missing from file.
    FileNotFoundError
        If data file does not exist.
    """
    from .validation import validate_channel_data, validate_channel_columns_exist
    from ..persistence.parquet_io import load_parquet

    # Resolve security to filename with clear error message
    if security_id not in source.security_mapping:
        available = sorted(source.security_mapping.keys())
        raise ValueError(
            f"Security '{security_id}' not found in file registry at "
            f"'{source.base_dir / 'registry.json'}'. "
            f"Available securities: {available}. "
            f"Run 'python scripts/generate_synthetic.py' to regenerate synthetic data "
            f"or add the security to the registry."
        )

    filename = source.security_mapping[security_id]
    file_path = source.base_dir / filename

    logger.debug("Loading security '%s' from file: %s", security_id, file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {file_path}. "
            f"Run 'python scripts/generate_synthetic.py' to generate synthetic data "
            f"or provide the missing file."
        )

    # Load parquet file
    df = load_parquet(file_path, start_date=start_date, end_date=end_date)

    # Check if file is empty
    if df.empty:
        raise ValueError(
            f"Data file '{file_path}' is empty for security '{security_id}'. "
            f"No data available for the specified date range."
        )

    # Extract requested channel columns
    channel_names = [c.value for c in channels]

    # Validate channel columns exist (FR-010: fail-fast on missing columns)
    try:
        validate_channel_columns_exist(df, channel_names, security_id)
    except ValueError as e:
        # Enhance error message with file path
        raise ValueError(
            f"{e} "
            f"File path: {file_path}. "
            f"Regenerate synthetic data with 'python scripts/generate_synthetic.py' "
            f"or update bloomberg_securities.json to match available columns."
        ) from e

    # Select only requested channels
    result = df[channel_names].copy()

    # Validate channel data bounds
    result = validate_channel_data(result, channel_names, security_id)

    logger.info(
        "Loaded security '%s': %d rows, channels: %s",
        security_id,
        len(result),
        channel_names,
    )

    return result


def _fetch_security_from_bloomberg(
    security_id: str,
    channels: list["DataChannel"],
    spec: "SecuritySpec",
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Fetch security data from Bloomberg (multi-ticker).

    Parameters
    ----------
    security_id : str
        Security identifier.
    channels : list[DataChannel]
        Channels to fetch.
    spec : SecuritySpec
        Security specification with channel configs.
    start_date : str or None
        Start date.
    end_date : str or None
        End date.
    use_cache : bool
        Whether to use cache.

    Returns
    -------
    pd.DataFrame
        Data with requested channel columns (inner joined by date).

    Raises
    ------
    ChannelFetchError
        If one or more channel fetches fail (aggregated error).
    RuntimeError
        If Bloomberg returns no data for a channel.
    """
    from .channels import DataChannel, ChannelFetchError

    cache_dir = DATA_DIR / "cache"
    channel_dfs: dict[str, pd.DataFrame] = {}
    failures: dict[DataChannel, str] = {}

    for channel in channels:
        config = spec.get_channel_config(channel)

        logger.debug(
            "Fetching channel '%s' from Bloomberg: ticker=%s, field=%s",
            channel.value,
            config.bloomberg_ticker,
            config.field,
        )

        try:
            # Check cache first
            cache_key = f"{security_id}_{channel.value}"
            if use_cache:
                cached = get_cached_data(
                    BloombergSource(),
                    cache_key,
                    cache_dir,
                    start_date=start_date,
                    end_date=end_date,
                    ttl_days=CACHE_TTL_DAYS,
                )
                if cached is not None:
                    # Extract the value column and rename to channel name
                    if "value" in cached.columns:
                        channel_dfs[channel.value] = cached[["value"]].rename(
                            columns={"value": channel.value}
                        )
                    else:
                        # Assume first non-date column is the value
                        value_col = [c for c in cached.columns if c != "security"][0]
                        channel_dfs[channel.value] = cached[[value_col]].rename(
                            columns={value_col: channel.value}
                        )
                    continue

            # Fetch from Bloomberg
            df = fetch_from_bloomberg(
                ticker=config.bloomberg_ticker,
                instrument=spec.instrument_type,
                security=security_id,
                start_date=start_date,
                end_date=end_date,
            )

            # Handle Bloomberg returning no data (T042)
            if df is None or df.empty:
                failures[channel] = (
                    f"Bloomberg returned no data for ticker '{config.bloomberg_ticker}'. "
                    f"Verify the ticker is correct and data is available for the date range."
                )
                logger.error(
                    "Bloomberg returned no data for channel '%s' (ticker: %s) "
                    "for security '%s'. Check ticker validity and date range.",
                    channel.value,
                    config.bloomberg_ticker,
                    security_id,
                )
                continue

            # Map Bloomberg field to channel name
            # Bloomberg provider returns columns like 'spread', 'level', 'close'
            # We need to rename to the channel name
            if spec.instrument_type == "vix":
                value_col = "level"
            elif spec.instrument_type == "etf":
                value_col = "spread" if "spread" in df.columns else "close"
            else:  # cdx
                value_col = "spread"

            if value_col in df.columns:
                channel_df = df[[value_col]].rename(columns={value_col: channel.value})
            else:
                # Fallback: use first numeric column
                numeric_cols = df.select_dtypes(include=["number"]).columns
                if len(numeric_cols) > 0:
                    channel_df = df[[numeric_cols[0]]].rename(
                        columns={numeric_cols[0]: channel.value}
                    )
                else:
                    failures[channel] = (
                        f"Bloomberg response for ticker '{config.bloomberg_ticker}' "
                        f"contains no numeric columns. Response columns: {list(df.columns)}"
                    )
                    continue

            channel_dfs[channel.value] = channel_df

            # Cache the result
            if use_cache:
                registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
                save_to_cache(
                    channel_df.rename(columns={channel.value: "value"}),
                    BloombergSource(),
                    cache_key,
                    cache_dir,
                    registry=registry,
                    start_date=start_date,
                    end_date=end_date,
                )

        except ImportError as e:
            # Bloomberg/xbbg not available
            failures[channel] = (
                f"Bloomberg dependencies not installed: {e}. "
                f"Install with: uv sync --extra bloomberg"
            )
            logger.error(
                "Bloomberg dependencies not available for channel '%s': %s",
                channel.value,
                e,
            )
        except RuntimeError as e:
            # Bloomberg request failed
            failures[channel] = (
                f"Bloomberg request failed for ticker '{config.bloomberg_ticker}': {e}"
            )
            logger.error(
                "Failed to fetch channel '%s' for security '%s': %s",
                channel.value,
                security_id,
                e,
            )
        except Exception as e:
            # Catch-all for unexpected errors
            failures[channel] = f"Unexpected error: {e}"
            logger.error(
                "Unexpected error fetching channel '%s' for security '%s': %s",
                channel.value,
                security_id,
                e,
            )

    # If any failures, raise aggregated error (T043)
    if failures:
        raise ChannelFetchError(security_id, failures)

    # If no channels were successfully fetched
    if not channel_dfs:
        raise ValueError(
            f"No channel data fetched for security '{security_id}'. "
            f"All {len(channels)} channel fetches failed."
        )

    # Merge channel DataFrames with inner join (only dates with all channels)
    result = _merge_channel_data(channel_dfs)

    # Log warning if inner join significantly reduces data
    total_rows = max(len(df) for df in channel_dfs.values())
    if len(result) < total_rows * 0.8:  # More than 20% data loss
        logger.warning(
            "Inner join for security '%s' reduced data from %d to %d rows (%.1f%% retention). "
            "Channels may have misaligned trading days.",
            security_id,
            total_rows,
            len(result),
            100 * len(result) / total_rows,
        )

    logger.info(
        "Fetched security '%s' from Bloomberg: %d rows, channels: %s",
        security_id,
        len(result),
        list(channel_dfs.keys()),
    )

    return result


def _merge_channel_data(channel_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Merge channel DataFrames with inner join on dates.

    Parameters
    ----------
    channel_dfs : dict[str, pd.DataFrame]
        Mapping of channel names to DataFrames.

    Returns
    -------
    pd.DataFrame
        Merged DataFrame with all channel columns.

    Raises
    ------
    ValueError
        If no channel data to merge or result is empty after join.
    """
    if not channel_dfs:
        raise ValueError(
            "No channel data to merge. All channel fetches may have failed."
        )

    result: pd.DataFrame | None = None
    for channel_name, df in channel_dfs.items():
        if result is None:
            result = df
        else:
            result = result.join(df, how="inner")

    # Check if inner join resulted in empty DataFrame
    if result is None or result.empty:
        channel_info = {name: len(df) for name, df in channel_dfs.items()}
        raise ValueError(
            f"Inner join resulted in empty DataFrame. "
            f"Channels have no overlapping dates. "
            f"Channel row counts: {channel_info}. "
            f"Check that all channel tickers have data for the same date range."
        )

    return result
