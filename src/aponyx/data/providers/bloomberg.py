"""Bloomberg Terminal/API data provider.

Fetches market data using Bloomberg's Python API via xbbg wrapper.
Requires active Bloomberg Terminal session.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from ..bloomberg_config import (
    BloombergInstrumentSpec,
    get_instrument_spec,
    get_security_from_ticker,
)

logger = logging.getLogger(__name__)


def fetch_from_bloomberg(
    ticker: str,
    instrument: str,
    start_date: str | None = None,
    end_date: str | None = None,
    security: str | None = None,
    **params: Any,
) -> pd.DataFrame:
    """
    Fetch historical data from Bloomberg Terminal via xbbg wrapper.

    Parameters
    ----------
    ticker : str
        Bloomberg ticker (e.g., 'CDX IG CDSI GEN 5Y Corp', 'VIX Index', 'HYG US Equity').
    instrument : str
        Instrument type for field mapping ('cdx', 'vix', 'etf').
    start_date : str or None, default None
        Start date in YYYY-MM-DD format. Defaults to 5 years ago.
    end_date : str or None, default None
        End date in YYYY-MM-DD format. Defaults to today.
    security : str or None, default None
        Internal security identifier (e.g., 'cdx_ig_5y', 'hyg').
        If provided, used directly for metadata. Otherwise, reverse lookup from ticker.
    **params : Any
        Additional Bloomberg request parameters passed to xbbg.

    Returns
    -------
    pd.DataFrame
        Historical data with DatetimeIndex and schema-compatible columns.

    Raises
    ------
    ImportError
        If xbbg is not installed.
    ValueError
        If ticker format is invalid or instrument type is unknown.
    RuntimeError
        If Bloomberg request fails or returns empty data.

    Notes
    -----
    Requires active Bloomberg Terminal session. Connection is handled
    automatically by xbbg wrapper.

    Returned DataFrame columns are mapped to project schemas:
    - CDX: spread, security
    - VIX: level
    - ETF: spread, security

    Example tickers:
    - CDX: 'CDX IG CDSI GEN 5Y Corp'
    - VIX: 'VIX Index'
    - ETFs: 'HYG US Equity', 'LQD US Equity'
    """
    # Get instrument specification from registry
    spec = get_instrument_spec(instrument)

    # Default to 5-year lookback if dates not provided
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_dt = datetime.now() - timedelta(days=5 * 365)
        start_date = start_dt.strftime("%Y-%m-%d")

    # Convert dates to Bloomberg format (YYYYMMDD)
    bbg_start = start_date.replace("-", "")
    bbg_end = end_date.replace("-", "")

    logger.info(
        "Fetching %s from Bloomberg: ticker=%s, dates=%s to %s",
        instrument,
        ticker,
        start_date,
        end_date,
    )

    # Import xbbg wrapper
    # Note: Use BaseException to catch pytest.Skipped from xbbg's importorskip
    try:
        from xbbg import blp
    except BaseException as e:
        # Handle multiple error types:
        # 1. Direct ImportError when xbbg not installed
        # 2. ImportError with blpapi in message (nested import failure)
        # 3. pytest.Skipped exception from xbbg's importorskip
        error_msg = str(e)

        if "blpapi" in error_msg.lower():
            raise ImportError(
                "Bloomberg API (blpapi) not installed. "
                "Install with: uv pip install blpapi\n"
                "Or install all Bloomberg dependencies: uv sync --extra bloomberg\n"
                "Note: Requires active Bloomberg Terminal subscription."
            ) from e
        elif isinstance(e, ImportError):
            raise ImportError(
                f"xbbg not installed: {error_msg}\n"
                "Install with: uv pip install xbbg\n"
                "Or install all Bloomberg dependencies: uv sync --extra bloomberg"
            ) from e
        else:
            # Re-raise other exceptions (KeyboardInterrupt, SystemExit, etc.)
            raise

    # Fetch historical data using xbbg
    try:
        df = blp.bdh(
            tickers=ticker,
            flds=spec.bloomberg_fields,
            start_date=bbg_start,
            end_date=bbg_end,
            **params,
        )
    except Exception as e:
        logger.error("Bloomberg request failed: %s", str(e))
        raise RuntimeError(f"Failed to fetch data from Bloomberg: {e}") from e

    # Check if response is empty
    if df is None or df.empty:
        raise RuntimeError(
            f"Bloomberg returned empty data for {ticker}. "
            "Check ticker format and data availability."
        )

    logger.debug("Fetched %d rows from Bloomberg", len(df))

    # Convert index to DatetimeIndex (xbbg returns object dtype)
    df.index = pd.to_datetime(df.index)
    logger.debug("Converted index to DatetimeIndex: %s", df.index.dtype)

    # Map Bloomberg field names to schema columns
    df = _map_bloomberg_fields(df, spec)

    # Add metadata columns (security identifier)
    if spec.requires_security_metadata:
        df = _add_security_metadata(df, ticker, security)

    logger.info(
        "Successfully fetched %d rows with columns: %s", len(df), list(df.columns)
    )

    return df


def _map_bloomberg_fields(
    df: pd.DataFrame,
    spec: BloombergInstrumentSpec,
) -> pd.DataFrame:
    """
    Map Bloomberg field names to schema-expected column names.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame from xbbg with Bloomberg field names.
    spec : BloombergInstrumentSpec
        Instrument specification with field mappings.

    Returns
    -------
    pd.DataFrame
        DataFrame with renamed columns matching project schemas.

    Notes
    -----
    BDH returns multi-index columns: (ticker, field) with uppercase fields.
    BDP returns flat columns: fields with lowercase.
    We normalize to uppercase before mapping.
    """
    # Handle xbbg multi-index columns: (ticker, field) from BDH
    if isinstance(df.columns, pd.MultiIndex):
        # Flatten by taking second level (field names)
        df.columns = df.columns.get_level_values(1)
        logger.debug("Flattened multi-index columns from BDH")
    else:
        # BDP returns flat columns (single ticker)
        # Normalize lowercase fields to uppercase for consistent mapping
        df.columns = df.columns.str.upper()
        logger.debug("Normalized BDP field names to uppercase")

    # Rename columns according to mapping
    df = df.rename(columns=spec.field_mapping)

    logger.debug(
        "Mapped fields: %s -> %s",
        list(spec.field_mapping.keys()),
        list(spec.field_mapping.values()),
    )

    return df


def _add_security_metadata(
    df: pd.DataFrame,
    ticker: str,
    security: str | None = None,
) -> pd.DataFrame:
    """
    Add security metadata column.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with mapped field columns.
    ticker : str
        Bloomberg ticker string.
    security : str or None
        Internal security identifier. If None, reverse lookup from ticker.

    Returns
    -------
    pd.DataFrame
        DataFrame with added 'security' column.

    Raises
    ------
    ValueError
        If security not provided and ticker not found in registry.
    """
    # Get security identifier from parameter or reverse lookup
    if security is not None:
        sec_id = security
        logger.debug("Using provided security identifier: %s", sec_id)
    else:
        # Reverse lookup from Bloomberg ticker
        try:
            sec_id = get_security_from_ticker(ticker)
            logger.debug("Reverse lookup: %s -> %s", ticker, sec_id)
        except ValueError as e:
            logger.error("Failed to resolve security from ticker: %s", ticker)
            raise ValueError(
                f"Cannot determine security identifier for ticker '{ticker}'. "
                "Either provide 'security' parameter or ensure ticker is in registry."
            ) from e

    df["security"] = sec_id
    logger.debug("Added security metadata: %s", sec_id)

    return df


def fetch_multi_ticker_from_bloomberg(
    ticker_field_map: dict[str, list[str]],
    start_date: str | None = None,
    end_date: str | None = None,
    **params: Any,
) -> dict[str, pd.DataFrame]:
    """
    Fetch historical data for multiple tickers/fields in batch from Bloomberg.

    This function enables efficient multi-ticker fetching for securities that
    require data from multiple Bloomberg tickers (e.g., CDX HY with separate
    spread and price tickers).

    Parameters
    ----------
    ticker_field_map : dict[str, list[str]]
        Mapping of Bloomberg tickers to their fields to fetch.
        Example: {"CDX HY CDSI GEN 5Y SPRD Corp": ["PX_LAST"],
                  "CDX HY CDSI GEN 5Y Corp": ["PX_LAST"]}
    start_date : str or None
        Start date in YYYY-MM-DD format.
    end_date : str or None
        End date in YYYY-MM-DD format.
    **params : Any
        Additional Bloomberg request parameters.

    Returns
    -------
    dict[str, pd.DataFrame]
        Mapping of ticker to DataFrame with DatetimeIndex.
        Each DataFrame has columns matching the requested fields.

    Raises
    ------
    ImportError
        If xbbg is not installed.
    RuntimeError
        If Bloomberg request fails.

    Notes
    -----
    Uses xbbg's batch fetching capability for efficiency.
    Each ticker's DataFrame is returned separately for flexible merging.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_dt = datetime.now() - timedelta(days=5 * 365)
        start_date = start_dt.strftime("%Y-%m-%d")

    bbg_start = start_date.replace("-", "")
    bbg_end = end_date.replace("-", "")

    logger.info(
        "Fetching %d tickers from Bloomberg: dates=%s to %s",
        len(ticker_field_map),
        start_date,
        end_date,
    )

    try:
        from xbbg import blp
    except BaseException as e:
        error_msg = str(e)
        if "blpapi" in error_msg.lower():
            raise ImportError(
                "Bloomberg API (blpapi) not installed. "
                "Install with: uv pip install blpapi"
            ) from e
        elif isinstance(e, ImportError):
            raise ImportError(f"xbbg not installed: {error_msg}") from e
        else:
            raise

    results: dict[str, pd.DataFrame] = {}

    for ticker, fields in ticker_field_map.items():
        try:
            df = blp.bdh(
                tickers=ticker,
                flds=fields,
                start_date=bbg_start,
                end_date=bbg_end,
                **params,
            )

            if df is None or df.empty:
                logger.warning("Bloomberg returned empty data for ticker: %s", ticker)
                continue

            # Convert index to DatetimeIndex
            df.index = pd.to_datetime(df.index)

            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(1)

            results[ticker] = df
            logger.debug("Fetched %d rows for ticker: %s", len(df), ticker)

        except Exception as e:
            logger.error("Failed to fetch ticker %s: %s", ticker, e)
            raise RuntimeError(f"Failed to fetch {ticker} from Bloomberg: {e}") from e

    return results


def fetch_current_from_bloomberg(
    ticker: str,
    instrument: str,
    security: str | None = None,
    **params: Any,
) -> pd.DataFrame | None:
    """
    Fetch current/latest data point from Bloomberg using BDP.

    Parameters
    ----------
    ticker : str
        Bloomberg ticker.
    instrument : str
        Instrument type for field mapping ('cdx', 'vix', 'etf').
    security : str or None
        Internal security identifier.
    **params : Any
        Additional Bloomberg request parameters.

    Returns
    -------
    pd.DataFrame or None
        Single-row DataFrame with current data and today's date as index.
        Returns None if no data available (e.g., non-trading day).

    Raises
    ------
    ImportError
        If xbbg is not installed.
    RuntimeError
        If Bloomberg request fails due to connection/authentication issues.

    Notes
    -----
    Uses Bloomberg's BDP (current data) instead of BDH (historical data).
    Returns data with today's date (US/Eastern timezone) as the index.
    Gracefully returns None on weekends/holidays instead of raising errors.
    """
    spec = get_instrument_spec(instrument)

    logger.info(
        "Fetching current %s from Bloomberg: ticker=%s",
        instrument,
        ticker,
    )

    try:
        from xbbg import blp
    except BaseException as e:
        # Handle multiple error types:
        # 1. Direct ImportError when xbbg not installed
        # 2. ImportError with blpapi in message (nested import failure)
        # 3. pytest.Skipped exception from xbbg's importorskip
        error_msg = str(e)

        if "blpapi" in error_msg.lower():
            raise ImportError(
                "Bloomberg API (blpapi) not installed. "
                "Install with: uv pip install blpapi\n"
                "Or install all Bloomberg dependencies: uv sync --extra bloomberg\n"
                "Note: Requires active Bloomberg Terminal subscription."
            ) from e
        elif isinstance(e, ImportError):
            raise ImportError(
                f"xbbg not installed: {error_msg}\n"
                "Install with: uv pip install xbbg\n"
                "Or install all Bloomberg dependencies: uv sync --extra bloomberg"
            ) from e
        else:
            # Re-raise other exceptions (KeyboardInterrupt, SystemExit, etc.)
            raise

    try:
        # Use BDP for current data point
        current_data = blp.bdp(
            tickers=ticker,
            flds=spec.bloomberg_fields,
            **params,
        )
    except Exception as e:
        logger.error("Bloomberg BDP request failed: %s", str(e))
        raise RuntimeError(f"Failed to fetch current data from Bloomberg: {e}") from e

    if current_data is None or current_data.empty:
        # Gracefully handle no data (weekends, holidays, market closed)
        logger.warning(
            "Bloomberg BDP returned empty data for %s (likely non-trading day)",
            ticker,
        )
        return None

    logger.debug("Fetched current data from Bloomberg: %s", current_data.shape)

    # Convert BDP format to time series format
    # BDP returns: index=tickers, columns=fields (lowercase)
    # Need: index=dates, columns=fields (to match BDH format)
    eastern = ZoneInfo("America/New_York")
    today = datetime.now(eastern).strftime("%Y-%m-%d")

    # Extract single ticker row and reassign index to today's date
    df = current_data.iloc[[0]].copy()  # Keep as DataFrame with single row
    df.index = pd.to_datetime([today])
    df.index.name = "date"

    # Map Bloomberg field names to schema columns
    df = _map_bloomberg_fields(df, spec)

    # Add security metadata if required
    if spec.requires_security_metadata:
        df = _add_security_metadata(df, ticker, security)

    logger.info(
        "Successfully fetched current data with columns: %s",
        list(df.columns),
    )

    return df
