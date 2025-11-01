"""Bloomberg Terminal/API data provider.

Fetches market data using Bloomberg's Python API via xbbg wrapper.
Requires active Bloomberg Terminal session.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from ...config.bloomberg_tickers import get_security_from_ticker

logger = logging.getLogger(__name__)


# Bloomberg field mappings for different instrument types
BLOOMBERG_FIELDS = {
    "cdx": ["PX_LAST"],  # CDX spread only
    "vix": ["PX_LAST"],  # VIX close only
    "etf": ["PX_LAST"],  # ETF close only
}

# Mapping from Bloomberg field names to schema column names
FIELD_MAPPING = {
    "cdx": {
        "PX_LAST": "spread",
    },
    "vix": {
        "PX_LAST": "close",
    },
    "etf": {
        "PX_LAST": "close",
    },
}


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
    - VIX: close
    - ETF: close, security

    Example tickers:
    - CDX: 'CDX IG CDSI GEN 5Y Corp'
    - VIX: 'VIX Index'
    - ETFs: 'HYG US Equity', 'LQD US Equity'
    """
    # Validate instrument type
    if instrument not in BLOOMBERG_FIELDS:
        raise ValueError(
            f"Unknown instrument type: {instrument}. "
            f"Must be one of {list(BLOOMBERG_FIELDS.keys())}"
        )

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
    try:
        from xbbg import blp
    except ImportError:
        raise ImportError(
            "xbbg not installed. "
            "Install with: uv pip install --optional bloomberg"
        )

    # Fetch historical data using xbbg
    fields = BLOOMBERG_FIELDS[instrument]
    try:
        df = blp.bdh(
            tickers=ticker,
            flds=fields,
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

    # Map Bloomberg field names to schema columns
    df = _map_bloomberg_fields(df, instrument, ticker)

    # Add metadata columns (security identifier)
    df = _add_metadata_columns(df, instrument, ticker, security)

    logger.info("Successfully fetched %d rows with columns: %s", len(df), list(df.columns))

    return df


def _map_bloomberg_fields(
    df: pd.DataFrame,
    instrument: str,
    ticker: str,
) -> pd.DataFrame:
    """
    Map Bloomberg field names to schema-expected column names.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame from xbbg with Bloomberg field names.
    instrument : str
        Instrument type for field mapping.
    ticker : str
        Bloomberg ticker (used for multi-ticker responses).

    Returns
    -------
    pd.DataFrame
        DataFrame with renamed columns matching project schemas.

    Notes
    -----
    xbbg returns multi-index columns for multiple tickers: (ticker, field).
    For single ticker requests, we flatten to just field names.
    """
    # Handle xbbg multi-index columns: (ticker, field)
    if isinstance(df.columns, pd.MultiIndex):
        # Flatten by taking second level (field names)
        df.columns = df.columns.get_level_values(1)

    # Rename columns according to mapping
    field_map = FIELD_MAPPING[instrument]
    df = df.rename(columns=field_map)

    logger.debug("Mapped fields: %s -> %s", list(field_map.keys()), list(field_map.values()))

    return df


def _add_metadata_columns(
    df: pd.DataFrame,
    instrument: str,
    ticker: str,
    security: str | None = None,
) -> pd.DataFrame:
    """
    Add metadata columns required by schemas.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with mapped field columns.
    instrument : str
        Instrument type ('cdx', 'vix', 'etf').
    ticker : str
        Bloomberg ticker string.
    security : str or None
        Internal security identifier. If None, reverse lookup from ticker.

    Returns
    -------
    pd.DataFrame
        DataFrame with added metadata columns.

    Raises
    ------
    ValueError
        If security not provided and ticker not found in registry.

    Notes
    -----
    For CDX and ETF instruments, adds 'security' column with internal identifier.
    VIX doesn't require metadata columns.
    """
    if instrument in ("cdx", "etf"):
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

    # VIX doesn't need metadata columns
    elif instrument == "vix":
        pass

    return df
