"""
Data validation utilities for market data quality checks.

Validates schema compliance, data types, and business logic constraints.
"""

import logging

import pandas as pd

from .schemas import CDXSchema, VIXSchema, ETFSchema

logger = logging.getLogger(__name__)


def _ensure_datetime_index(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """
    Convert DataFrame to use DatetimeIndex if not already.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to process.
    date_col : str
        Name of date column to use as index.

    Returns
    -------
    pd.DataFrame
        DataFrame with DatetimeIndex named 'date', sorted by date.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)

    # Ensure index is named 'date'
    df.index.name = "date"

    return df.sort_index()


def _check_duplicate_dates(df: pd.DataFrame, context: str = "") -> None:
    """
    Check for and log duplicate dates in DataFrame index.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with DatetimeIndex to check.
    context : str, optional
        Additional context for log message (e.g., ticker name).
    """
    if df.index.duplicated().any():
        n_dups = df.index.duplicated().sum()
        if context:
            logger.warning("Found %d duplicate dates for %s", n_dups, context)
        else:
            logger.warning("Found %d duplicate dates", n_dups)


def handle_duplicate_index(
    df: pd.DataFrame,
    strategy: str = "last",
    context: str = "",
) -> pd.DataFrame:
    """
    Remove duplicate index entries with logging.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with potential duplicate indices.
    strategy : str, default "last"
        Deduplication strategy:
        - "first": Keep first occurrence
        - "last": Keep last occurrence
        - "raise": Raise ValueError if duplicates found
    context : str, optional
        Context for logging (e.g., "CDX IG 5Y").

    Returns
    -------
    pd.DataFrame
        DataFrame with duplicates removed.

    Raises
    ------
    ValueError
        If strategy="raise" and duplicates are found, or if strategy is invalid.

    Examples
    --------
    >>> df = pd.DataFrame({"value": [1, 2, 3]}, index=pd.DatetimeIndex(["2024-01-01", "2024-01-01", "2024-01-02"]))
    >>> clean_df = handle_duplicate_index(df, strategy="last")
    >>> clean_df = handle_duplicate_index(df, strategy="raise")  # Raises ValueError
    """
    if strategy not in ("first", "last", "raise"):
        raise ValueError(
            f"Invalid strategy '{strategy}'. Must be 'first', 'last', or 'raise'"
        )

    if not df.index.duplicated().any():
        return df

    # Log duplicates
    _check_duplicate_dates(df, context)

    # Handle based on strategy
    if strategy == "raise":
        n_dups = df.index.duplicated().sum()
        raise ValueError(
            f"Found {n_dups} duplicate index entries"
            + (f" for {context}" if context else "")
        )

    # Remove duplicates
    df_clean = df[~df.index.duplicated(keep=strategy)]
    logger.debug("Removed duplicates using strategy='%s'", strategy)
    return df_clean


def validate_cdx_schema(
    df: pd.DataFrame, schema: CDXSchema = CDXSchema()
) -> pd.DataFrame:
    """
    Validate CDX index data against expected schema.

    Parameters
    ----------
    df : pd.DataFrame
        Raw CDX data to validate.
    schema : CDXSchema, default CDXSchema()
        Schema definition with column names and constraints.

    Returns
    -------
    pd.DataFrame
        Validated DataFrame with DatetimeIndex.

    Raises
    ------
    ValueError
        If required columns are missing or data violates constraints.

    Notes
    -----
    - Converts date column to DatetimeIndex
    - Validates spread values are within bounds
    - Checks for duplicate dates per index
    """
    logger.info("Validating CDX schema: %d rows", len(df))

    # Check required columns (except date if already indexed)
    required_cols = list(schema.required_cols)
    if isinstance(df.index, pd.DatetimeIndex):
        # Already has DatetimeIndex, don't require date column
        required_cols = [col for col in required_cols if col != schema.date_col]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Validate spread bounds
    if not df[schema.spread_col].between(schema.min_spread, schema.max_spread).all():
        invalid = df[
            ~df[schema.spread_col].between(schema.min_spread, schema.max_spread)
        ]
        logger.warning(
            "Found %d invalid spread values outside [%.1f, %.1f]",
            len(invalid),
            schema.min_spread,
            schema.max_spread,
        )
        raise ValueError(f"Spread values outside valid range: {invalid.head()}")

    # Convert to DatetimeIndex and sort
    df = _ensure_datetime_index(df, schema.date_col)

    # Remove duplicates if present (without logging warning)
    if df.index.duplicated().any():
        n_dups = df.index.duplicated().sum()
        logger.debug("Removing %d duplicate dates for CDX", n_dups)
        df = df[~df.index.duplicated(keep="last")]

    logger.debug(
        "CDX validation passed: date_range=%s to %s", df.index.min(), df.index.max()
    )
    return df


def validate_vix_schema(
    df: pd.DataFrame, schema: VIXSchema = VIXSchema()
) -> pd.DataFrame:
    """
    Validate VIX volatility data against expected schema.

    Parameters
    ----------
    df : pd.DataFrame
        Raw VIX data to validate.
    schema : VIXSchema, default VIXSchema()
        Schema definition with column names and constraints.

    Returns
    -------
    pd.DataFrame
        Validated DataFrame with DatetimeIndex.

    Raises
    ------
    ValueError
        If required columns are missing or data violates constraints.
    """
    logger.info("Validating VIX schema: %d rows", len(df))

    # Check required columns (except date if already indexed)
    required_cols = list(schema.required_cols)
    if isinstance(df.index, pd.DatetimeIndex):
        # Already has DatetimeIndex, don't require date column
        required_cols = [col for col in required_cols if col != schema.date_col]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Validate VIX bounds
    if not df[schema.level_col].between(schema.min_vix, schema.max_vix).all():
        invalid = df[~df[schema.level_col].between(schema.min_vix, schema.max_vix)]
        logger.warning(
            "Found %d invalid VIX values outside [%.1f, %.1f]",
            len(invalid),
            schema.min_vix,
            schema.max_vix,
        )
        raise ValueError(f"VIX values outside valid range: {invalid.head()}")

    # Convert to DatetimeIndex and sort
    df = _ensure_datetime_index(df, schema.date_col)

    # Check for duplicates (remove duplicates for VIX)
    df = handle_duplicate_index(df, strategy="first", context="VIX")

    logger.debug(
        "VIX validation passed: date_range=%s to %s", df.index.min(), df.index.max()
    )
    return df


def validate_etf_schema(
    df: pd.DataFrame, schema: ETFSchema = ETFSchema()
) -> pd.DataFrame:
    """
    Validate credit ETF data against expected schema.

    Parameters
    ----------
    df : pd.DataFrame
        Raw ETF data to validate.
    schema : ETFSchema, default ETFSchema()
        Schema definition with column names and constraints.

    Returns
    -------
    pd.DataFrame
        Validated DataFrame with DatetimeIndex.

    Raises
    ------
    ValueError
        If required columns are missing or data violates constraints.
    """
    logger.info("Validating ETF schema: %d rows", len(df))

    # Check required columns (except date if already indexed)
    required_cols = list(schema.required_cols)
    if isinstance(df.index, pd.DatetimeIndex):
        # Already has DatetimeIndex, don't require date column
        required_cols = [col for col in required_cols if col != schema.date_col]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Validate price bounds
    if not df[schema.spread_col].between(schema.min_price, schema.max_price).all():
        invalid = df[~df[schema.spread_col].between(schema.min_price, schema.max_price)]
        logger.warning(
            "Found %d invalid price values outside [%.1f, %.1f]",
            len(invalid),
            schema.min_price,
            schema.max_price,
        )
        raise ValueError(f"Price values outside valid range: {invalid.head()}")

    # Convert to DatetimeIndex and sort
    df = _ensure_datetime_index(df, schema.date_col)

    # Remove duplicates if present (without logging warning)
    if df.index.duplicated().any():
        n_dups = df.index.duplicated().sum()
        logger.debug("Removing %d duplicate dates for ETF", n_dups)
        df = df[~df.index.duplicated(keep="last")]

    logger.debug(
        "ETF validation passed: date_range=%s to %s", df.index.min(), df.index.max()
    )
    return df


# =============================================================================
# Channel-aware validation functions
# =============================================================================

# Validation bounds per channel type
CHANNEL_BOUNDS: dict[str, dict[str, float]] = {
    "spread": {"min": 0.0, "max": 10000.0},  # Basis points
    "price": {"min": 0.0, "max": 10000.0},   # Price levels
    "level": {"min": 0.0, "max": 200.0},     # VIX-style levels
}


def validate_channel_data(
    df: pd.DataFrame,
    channels: list[str],
    security_id: str | None = None,
) -> pd.DataFrame:
    """
    Validate DataFrame with channel columns.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with channel columns to validate.
    channels : list[str]
        List of channel names (e.g., ["spread"], ["price", "spread"]).
    security_id : str or None
        Security identifier for error messages.

    Returns
    -------
    pd.DataFrame
        Validated DataFrame with DatetimeIndex.

    Raises
    ------
    ValueError
        If required channels are missing or values are out of bounds.

    Examples
    --------
    >>> df = pd.DataFrame({"spread": [100.0, 150.0]}, index=dates)
    >>> validated = validate_channel_data(df, ["spread"], "cdx_ig_5y")
    """
    logger.debug(
        "Validating channel data: security=%s, channels=%s, rows=%d",
        security_id,
        channels,
        len(df),
    )

    # Ensure DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        if "date" in df.columns:
            df = _ensure_datetime_index(df.copy(), "date")
        else:
            raise ValueError("DataFrame must have DatetimeIndex or 'date' column")

    # Check all requested channels exist
    missing_channels = [c for c in channels if c not in df.columns]
    if missing_channels:
        available = list(df.columns)
        sec_context = f" for security '{security_id}'" if security_id else ""
        raise ValueError(
            f"Missing channels {missing_channels}{sec_context}. "
            f"Available columns: {available}"
        )

    # Validate value bounds for each channel
    for channel in channels:
        bounds = CHANNEL_BOUNDS.get(channel)
        if bounds is None:
            logger.debug("No bounds defined for channel '%s', skipping validation", channel)
            continue

        min_val, max_val = bounds["min"], bounds["max"]
        series = df[channel]

        # Check for NaN values
        nan_count = series.isna().sum()
        if nan_count > 0:
            logger.debug(
                "Channel '%s' has %d NaN values (%.1f%%)",
                channel,
                nan_count,
                100 * nan_count / len(series),
            )

        # Validate non-NaN values are within bounds
        valid_values = series.dropna()
        if len(valid_values) > 0:
            out_of_bounds = ~valid_values.between(min_val, max_val)
            if out_of_bounds.any():
                invalid_count = out_of_bounds.sum()
                sec_context = f" for security '{security_id}'" if security_id else ""
                logger.warning(
                    "Channel '%s'%s has %d values outside [%.1f, %.1f]",
                    channel,
                    sec_context,
                    invalid_count,
                    min_val,
                    max_val,
                )
                raise ValueError(
                    f"Channel '{channel}' values outside valid range [{min_val}, {max_val}]"
                    f"{sec_context}"
                )

    # Handle duplicate dates
    if df.index.duplicated().any():
        n_dups = df.index.duplicated().sum()
        logger.debug("Removing %d duplicate dates", n_dups)
        df = df[~df.index.duplicated(keep="last")]

    logger.debug(
        "Channel validation passed: %d rows, date_range=%s to %s",
        len(df),
        df.index.min(),
        df.index.max(),
    )

    return df


def validate_channel_columns_exist(
    df: pd.DataFrame,
    channels: list[str],
    security_id: str,
) -> None:
    """
    Check that all requested channel columns exist in DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to check.
    channels : list[str]
        Required channel column names.
    security_id : str
        Security identifier for error messages.

    Raises
    ------
    ValueError
        If any requested channels are missing.

    Notes
    -----
    This is a lightweight check without value validation.
    Use validate_channel_data() for full validation.
    """
    missing = [c for c in channels if c not in df.columns]
    if missing:
        available = list(df.columns)
        raise ValueError(
            f"Channels {missing} not found in file for security '{security_id}'. "
            f"Available columns: {available}"
        )
