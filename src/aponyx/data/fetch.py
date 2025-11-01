"""
Unified data fetching interface with provider abstraction.

Fetch functions handle data acquisition from any source (file, Bloomberg, API)
with automatic validation and optional caching.
"""

import logging

import pandas as pd

from ..config import DATA_DIR, CACHE_ENABLED, CACHE_TTL_DAYS, DEFAULT_DATA_SOURCES
from ..config.bloomberg_config import get_bloomberg_ticker
from ..persistence.registry import DataRegistry, REGISTRY_PATH
from .cache import get_cached_data, save_to_cache
from .sources import DataSource, FileSource, BloombergSource, resolve_provider
from .providers.file import fetch_from_file
from .providers.bloomberg import fetch_from_bloomberg
from .validation import validate_cdx_schema, validate_vix_schema, validate_etf_schema

logger = logging.getLogger(__name__)


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
    force_refresh: bool = False,
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
    force_refresh : bool, default False
        Force fetch from source, bypassing cache.

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
    """
    source = source or DEFAULT_DATA_SOURCES.get("cdx")
    if source is None:
        raise ValueError("No source provided and no default configured for CDX")

    instrument = "cdx"
    cache_dir = DATA_DIR / "cache"

    # Check cache first
    if use_cache and not force_refresh:
        cached = get_cached_data(
            source,
            instrument,
            cache_dir,
            start_date=start_date,
            end_date=end_date,
            ttl_days=CACHE_TTL_DAYS.get(instrument),
            security=security,
        )
        if cached is not None:
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
            file_path=source.path,
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
            logger.debug("Resolved security '%s' to Bloomberg ticker: %s", security, ticker)
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

    # Cache if enabled
    if use_cache:
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

    logger.info("Fetched CDX data: %d rows, %s to %s", len(df), df.index.min(), df.index.max())
    return df


def fetch_vix(
    source: DataSource | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = CACHE_ENABLED,
    force_refresh: bool = False,
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
    force_refresh : bool, default False
        Force fetch from source, bypassing cache.

    Returns
    -------
    pd.DataFrame
        Validated VIX data with DatetimeIndex and columns:
        - close: VIX closing level

    Examples
    --------
    >>> from aponyx.data import fetch_vix, FileSource
    >>> df = fetch_vix(FileSource("data/raw/vix.parquet"))
    """
    source = source or DEFAULT_DATA_SOURCES.get("vix")
    if source is None:
        raise ValueError("No source provided and no default configured for VIX")

    instrument = "vix"
    cache_dir = DATA_DIR / "cache"

    # Check cache first
    if use_cache and not force_refresh:
        cached = get_cached_data(
            source,
            instrument,
            cache_dir,
            start_date=start_date,
            end_date=end_date,
            ttl_days=CACHE_TTL_DAYS.get(instrument),
        )
        if cached is not None:
            return cached

    # Fetch from source
    logger.info("Fetching VIX from %s", resolve_provider(source))
    fetch_fn = _get_provider_fetch_function(source)

    if isinstance(source, FileSource):
        df = fetch_fn(
            file_path=source.path,
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

    # Cache if enabled
    if use_cache:
        registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        save_to_cache(
            df,
            source,
            instrument,
            cache_dir,
            registry=registry,
            start_date=start_date,
            end_date=end_date,
        )

    logger.info("Fetched VIX data: %d rows, %s to %s", len(df), df.index.min(), df.index.max())
    return df


def fetch_etf(
    source: DataSource | None = None,
    security: str | None = None,
    bloomberg_ticker: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = CACHE_ENABLED,
    force_refresh: bool = False,
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
    force_refresh : bool, default False
        Force fetch from source, bypassing cache.

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
    """
    source = source or DEFAULT_DATA_SOURCES.get("etf")
    if source is None:
        raise ValueError("No source provided and no default configured for ETF")

    instrument = "etf"
    cache_dir = DATA_DIR / "cache"

    # Check cache first
    if use_cache and not force_refresh:
        cached = get_cached_data(
            source,
            instrument,
            cache_dir,
            start_date=start_date,
            end_date=end_date,
            ttl_days=CACHE_TTL_DAYS.get(instrument),
            security=security,
        )
        if cached is not None:
            df = cached
            if security is not None and "security" in df.columns:
                df = df[df["security"] == security]
            return df

    # Fetch from source
    logger.info("Fetching ETF from %s", resolve_provider(source))
    fetch_fn = _get_provider_fetch_function(source)

    if isinstance(source, FileSource):
        df = fetch_fn(
            file_path=source.path,
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
            logger.debug("Resolved security '%s' to Bloomberg ticker: %s", security, ticker)
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

    # Cache if enabled
    if use_cache:
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

    logger.info("Fetched ETF data: %d rows, %s to %s", len(df), df.index.min(), df.index.max())
    return df



