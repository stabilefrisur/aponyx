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
from .sources import DataSource, FileSource, BloombergSource, resolve_provider
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
    Get fetch function for data source.

    Parameters
    ----------
    source : DataSource
        Data source configuration.

    Returns
    -------
    Callable
        Provider fetch function.
    """
    provider_type = resolve_provider(source)

    if provider_type == "file":
        return fetch_from_file
    elif provider_type == "bloomberg":
        return fetch_from_bloomberg
    else:
        raise ValueError(f"Unsupported provider: {provider_type}")


def fetch_cdx(
    source: DataSource | None = None,
    security: str | None = None,
    bloomberg_ticker: str | None = None,
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
    bloomberg_ticker : str or None
        Optional Bloomberg ticker override for ad-hoc research.
        If provided, bypasses registry lookup.
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
    >>> df = fetch_cdx(BloombergSource(), bloomberg_ticker="CDX IG CDSI GEN 5Y Corp")
    >>> # Update only today's data point (intraday refresh)
    >>> df = fetch_cdx(BloombergSource(), security="cdx_ig_5y", update_current_day=True)
    """
    if source is None:
        raise ValueError("Data source must be specified for CDX fetch")

    instrument = "cdx"
    cache_dir = DATA_DIR / "cache"

    # Determine security identifier for caching
    # Use provided security or default to instrument type
    security_for_cache = security if security is not None else instrument

    # Check cache first
    if use_cache:
        cached = get_cached_data(
            source,
            security_for_cache,
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
                if bloomberg_ticker is not None:
                    ticker = bloomberg_ticker
                elif security is not None:
                    ticker = get_bloomberg_ticker(security)
                else:
                    raise ValueError(
                        "Either 'security' or 'bloomberg_ticker' required for Bloomberg fetch"
                    )

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
                    df = cached
                    if security is not None and "security" in df.columns:
                        df = df[df["security"] == security]
                    return df

                current_df = validate_cdx_schema(current_df)

                # Merge with cache
                df = update_cache_day(cached, current_df)

                # Save updated cache
                registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
                save_to_cache(
                    df,
                    source,
                    instrument,
                    cache_dir,
                    registry=registry,
                    start_date=start_date,
                    end_date=end_date,
                    security=security,
                )

                # Apply filter if needed
                if security is not None and "security" in df.columns:
                    df = df[df["security"] == security]
                return df
            else:
                df = cached
                # Apply filter if needed
                if security is not None and "security" in df.columns:
                    df = df[df["security"] == security]
                return df

    # Fetch from source
    logger.info("Fetching CDX from %s", resolve_provider(source))
    fetch_fn = _get_provider_fetch_function(source)

    if isinstance(source, FileSource):
        df = fetch_fn(
            source=source,
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
        )
    elif isinstance(source, BloombergSource):
        # Get Bloomberg ticker from registry or use override
        if bloomberg_ticker is not None:
            ticker = bloomberg_ticker
            logger.debug("Using Bloomberg ticker override: %s", ticker)
        elif security is not None:
            ticker = get_bloomberg_ticker(security)
            logger.debug(
                "Resolved security '%s' to Bloomberg ticker: %s", security, ticker
            )
        else:
            raise ValueError(
                "Either 'security' or 'bloomberg_ticker' required for Bloomberg CDX fetch"
            )
        df = fetch_fn(
            ticker=ticker,
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
            security=security,
        )
    else:
        raise ValueError(f"Unsupported source type: {type(source)}")

    # Validate schema
    df = validate_cdx_schema(df)

    # Apply security filter
    if security is not None:
        if "security" not in df.columns:
            raise ValueError("Cannot filter by security: 'security' column not found")
        df = df[df["security"] == security]
        logger.debug("Filtered to security=%s: %d rows", security, len(df))

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
            security_for_cache,
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
        - close: VIX closing level

    Examples
    --------
    >>> from aponyx.data import fetch_vix, FileSource
    >>> df = fetch_vix(FileSource("data/raw/vix.parquet"))
    >>> # Update only today's data point (intraday refresh)
    >>> df = fetch_vix(BloombergSource(), update_current_day=True)
    """
    if source is None:
        raise ValueError("Data source must be specified for VIX fetch")

    instrument = "vix"
    security_for_cache = "vix"  # VIX has single security identifier
    cache_dir = DATA_DIR / "cache"

    # Check cache first
    if use_cache:
        cached = get_cached_data(
            source,
            security_for_cache,
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

                ticker = get_bloomberg_ticker("vix")
                current_df = fetch_current_from_bloomberg(
                    ticker=ticker,
                    instrument=instrument,
                    security="vix",
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
                    security_for_cache,
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

    if isinstance(source, FileSource):
        df = fetch_fn(
            source=source,
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
        )
    elif isinstance(source, BloombergSource):
        ticker = get_bloomberg_ticker("vix")
        df = fetch_fn(
            ticker=ticker,
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
            security="vix",
        )
    else:
        raise ValueError(f"Unsupported source type: {type(source)}")

    # Validate schema
    df = validate_vix_schema(df)

    # Save Bloomberg data to raw storage (permanent source of truth)
    if isinstance(source, BloombergSource):
        from ..config import RAW_DIR

        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_raw(df, "bloomberg", "vix", RAW_DIR, registry)

    # Cache if enabled
    if use_cache:
        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_cache(
            df,
            source,
            security_for_cache,
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
    bloomberg_ticker: str | None = None,
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
    bloomberg_ticker : str or None
        Optional Bloomberg ticker override for ad-hoc research.
        If provided, bypasses registry lookup.
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
    >>> df = fetch_etf(BloombergSource(), bloomberg_ticker="HYG US Equity")
    >>> # Update only today's data point (intraday refresh)
    >>> df = fetch_etf(BloombergSource(), security="hyg", update_current_day=True)
    """
    if source is None:
        raise ValueError("Data source must be specified for ETF fetch")

    instrument = "etf"
    cache_dir = DATA_DIR / "cache"

    # Determine security identifier for caching
    # Use provided security or default to instrument type
    security_for_cache = security if security is not None else instrument

    # Check cache first
    if use_cache:
        cached = get_cached_data(
            source,
            security_for_cache,
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
                if bloomberg_ticker is not None:
                    ticker = bloomberg_ticker
                elif security is not None:
                    ticker = get_bloomberg_ticker(security)
                else:
                    raise ValueError(
                        "Either 'security' or 'bloomberg_ticker' required for Bloomberg fetch"
                    )

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
                    df = cached
                    if security is not None and "security" in df.columns:
                        df = df[df["security"] == security]
                    return df

                current_df = validate_etf_schema(current_df)

                # Merge with cache
                df = update_cache_day(cached, current_df)

                # Save updated cache
                registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
                save_to_cache(
                    df,
                    source,
                    security_for_cache,
                    cache_dir,
                    registry=registry,
                    start_date=start_date,
                    end_date=end_date,
                )

                # Apply filter if needed
                if security is not None and "security" in df.columns:
                    df = df[df["security"] == security]
                return df
            else:
                df = cached
                if security is not None and "security" in df.columns:
                    df = df[df["security"] == security]
                return df

    # Fetch from source
    logger.info("Fetching ETF from %s", resolve_provider(source))
    fetch_fn = _get_provider_fetch_function(source)

    if isinstance(source, FileSource):
        df = fetch_fn(
            source=source,
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
        )
    elif isinstance(source, BloombergSource):
        # Get Bloomberg ticker from registry or use override
        if bloomberg_ticker is not None:
            ticker = bloomberg_ticker
            logger.debug("Using Bloomberg ticker override: %s", ticker)
        elif security is not None:
            ticker = get_bloomberg_ticker(security)
            logger.debug(
                "Resolved security '%s' to Bloomberg ticker: %s", security, ticker
            )
        else:
            raise ValueError(
                "Either 'security' or 'bloomberg_ticker' required for Bloomberg ETF fetch"
            )
        df = fetch_fn(
            ticker=ticker,
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
            security=security,
        )
    else:
        raise ValueError(f"Unsupported source type: {type(source)}")

    # Validate schema
    df = validate_etf_schema(df)

    # Apply security filter
    if security is not None:
        if "security" not in df.columns:
            raise ValueError("Cannot filter by security: 'security' column not found")
        df = df[df["security"] == security]
        logger.debug("Filtered to security=%s: %d rows", security, len(df))

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
            security_for_cache,
            cache_dir,
            registry=registry,
            start_date=start_date,
            end_date=end_date,
        )

    logger.info(
        "Fetched ETF data: %d rows, %s to %s", len(df), df.index.min(), df.index.max()
    )
    return df
