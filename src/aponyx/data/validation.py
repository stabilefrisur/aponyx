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
        DataFrame with DatetimeIndex, sorted by date.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
    
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


def validate_cdx_schema(df: pd.DataFrame, schema: CDXSchema = CDXSchema()) -> pd.DataFrame:
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

    # Check for duplicates
    _check_duplicate_dates(df)

    logger.debug("CDX validation passed: date_range=%s to %s", df.index.min(), df.index.max())
    return df


def validate_vix_schema(df: pd.DataFrame, schema: VIXSchema = VIXSchema()) -> pd.DataFrame:
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
    if not df[schema.close_col].between(schema.min_vix, schema.max_vix).all():
        invalid = df[~df[schema.close_col].between(schema.min_vix, schema.max_vix)]
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
    if df.index.duplicated().any():
        _check_duplicate_dates(df)
        df = df[~df.index.duplicated(keep="first")]

    logger.debug("VIX validation passed: date_range=%s to %s", df.index.min(), df.index.max())
    return df


def validate_etf_schema(df: pd.DataFrame, schema: ETFSchema = ETFSchema()) -> pd.DataFrame:
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
    if not df[schema.close_col].between(schema.min_price, schema.max_price).all():
        invalid = df[~df[schema.close_col].between(schema.min_price, schema.max_price)]
        logger.warning(
            "Found %d invalid price values outside [%.1f, %.1f]",
            len(invalid),
            schema.min_price,
            schema.max_price,
        )
        raise ValueError(f"Price values outside valid range: {invalid.head()}")

    # Convert to DatetimeIndex and sort
    df = _ensure_datetime_index(df, schema.date_col)

    # Check for duplicates per security
    if schema.security_col in df.columns:
        for security in df[schema.security_col].unique():
            security_df = df[df[schema.security_col] == security]
            _check_duplicate_dates(security_df, context=f"security {security}")

    logger.debug("ETF validation passed: date_range=%s to %s", df.index.min(), df.index.max())
    return df
