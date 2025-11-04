"""
Centralized test data generation for examples.

Provides a single canonical dataset generator that all examples use.
Eliminates duplication and ensures consistency across demonstrations.
"""

import logging
import sys
from pathlib import Path

# Add src to path for direct imports when running examples
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from aponyx.data.sample_data import (
    generate_cdx_sample,
    generate_vix_sample,
    generate_etf_sample,
)

logger = logging.getLogger(__name__)


def generate_example_data(
    start_date: str = "2024-01-01",
    periods: int = 252,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generate canonical test dataset for all examples.

    Creates CDX IG 5Y, VIX, and HYG ETF data with realistic market dynamics.
    All example scripts should use this single function.

    Parameters
    ----------
    start_date : str, default "2024-01-01"
        Start date for time series.
    periods : int, default 252
        Number of trading days.
        - 252: ~1 year (default, suitable for signal demos)
        - 504: ~2 years (suitable for backtests)
        - 209: ~10 months (business days in 2024 YTD)
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        CDX, VIX, and ETF dataframes with date index.

    Notes
    -----
    - CDX: IG 5Y spreads starting at 100bp with 5bp volatility
    - VIX: Starting at 15 with moderate volatility
    - ETF: HYG prices starting at 100 with 5bp volatility
    - All data uses mean-reverting dynamics with realistic parameters
    
    Examples
    --------
    Standard 1-year dataset for signal demos:
    >>> cdx, vix, etf = generate_example_data()
    
    Extended 2-year dataset for backtests:
    >>> cdx, vix, etf = generate_example_data(
    ...     start_date="2023-01-01", periods=504
    ... )
    """
    logger.info(
        "Generating example data: start=%s, periods=%d, seed=%d",
        start_date,
        periods,
        seed,
    )

    cdx_df = generate_cdx_sample(
        start_date=start_date,
        periods=periods,
        index_name="CDX_IG",
        tenor="5Y",
        base_spread=100.0,
        volatility=5.0,
        seed=seed,
    ).set_index("date")

    vix_df = generate_vix_sample(
        start_date=start_date,
        periods=periods,
        base_vix=15.0,
        volatility=2.0,
        seed=seed,
    ).set_index("date")

    etf_df = generate_etf_sample(
        start_date=start_date,
        periods=periods,
        ticker="HYG",
        base_price=100.0,
        volatility=5.0,
        seed=seed,
    ).set_index("date")

    logger.info(
        "Generated %d days: CDX mean=%.1f, VIX mean=%.1f, ETF mean=%.1f",
        len(cdx_df),
        cdx_df["spread"].mean(),
        vix_df["level"].mean(),
        etf_df["spread"].mean(),
    )

    return cdx_df, vix_df, etf_df


def generate_persistence_data(
    start_date: str = "2024-01-01",
    periods: int = 252,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """
    Generate dataset for persistence layer demonstrations.

    Extends the standard dataset with additional instruments
    for demonstrating data registry and I/O operations.

    Parameters
    ----------
    start_date : str, default "2024-01-01"
        Start date for time series.
    periods : int, default 252
        Number of trading days.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary with keys: 'cdx_ig_5y', 'cdx_hy_5y', 'vix', 'hyg_etf'.
        Each DataFrame has date index and appropriate columns.

    Notes
    -----
    - Adds CDX HY to the standard dataset
    - Suitable for multi-instrument persistence examples
    """
    logger.info(
        "Generating persistence data: start=%s, periods=%d, seed=%d",
        start_date,
        periods,
        seed,
    )

    # Generate standard instruments
    cdx_ig, vix, hyg = generate_example_data(start_date, periods, seed)

    # Generate additional CDX HY for multi-instrument demos
    cdx_hy = generate_cdx_sample(
        start_date=start_date,
        periods=periods,
        index_name="CDX_HY",
        tenor="5Y",
        base_spread=350.0,
        volatility=20.0,
        seed=seed + 1,
    ).set_index("date")

    logger.info("Generated persistence data with %d instruments", 4)

    return {
        "cdx_ig_5y": cdx_ig[["spread"]],
        "cdx_hy_5y": cdx_hy[["spread"]],
        "vix": vix[["level"]],
        "hyg_etf": hyg[["spread"]],
    }
