"""
Synthetic data generation for testing and demonstrations.

Generates realistic market data for CDX, VIX, and ETF instruments
with configurable volatility, correlation, and trend parameters.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..persistence.parquet_io import save_parquet
from .sources import FileSource

logger = logging.getLogger(__name__)


def generate_cdx_sample(
    start_date: str = "2024-01-01",
    periods: int = 252,
    index_name: str = "CDX_IG",
    tenor: str = "5Y",
    base_spread: float = 100.0,
    volatility: float = 5.0,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic CDX spread data.

    Parameters
    ----------
    start_date : str, default "2024-01-01"
        Start date for time series.
    periods : int, default 252
        Number of daily observations (trading days).
    index_name : str, default "CDX_IG"
        Index identifier (CDX_IG, CDX_HY, CDX_XO).
    tenor : str, default "5Y"
        Tenor string (5Y, 10Y).
    base_spread : float, default 100.0
        Starting spread level in basis points.
    volatility : float, default 5.0
        Daily spread volatility in basis points.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        CDX data with columns: date, spread, index, tenor, series

    Notes
    -----
    - Uses geometric Brownian motion with mean reversion
    - Spreads constrained to positive values
    - Realistic credit market dynamics
    """
    logger.info(
        "Generating CDX sample: index=%s, tenor=%s, periods=%d",
        index_name,
        tenor,
        periods,
    )

    rng = np.random.default_rng(seed)
    dates = pd.date_range(start_date, periods=periods, freq="D")

    # Mean-reverting spread dynamics
    spread = [base_spread]
    mean_reversion_speed = 0.1
    mean_level = base_spread

    for _ in range(periods - 1):
        drift = mean_reversion_speed * (mean_level - spread[-1])
        shock = rng.normal(0, volatility)
        new_spread = max(1.0, spread[-1] + drift + shock)
        spread.append(new_spread)

    df = pd.DataFrame(
        {
            "date": dates,
            "spread": spread,
            "index": [f"{index_name}_{tenor}"] * periods,
            "tenor": [tenor] * periods,
            "series": [42] * periods,
        }
    )

    logger.debug("Generated CDX sample: mean_spread=%.2f", df["spread"].mean())
    return df


def generate_vix_sample(
    start_date: str = "2024-01-01",
    periods: int = 252,
    base_vix: float = 15.0,
    volatility: float = 2.0,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic VIX volatility data.

    Parameters
    ----------
    start_date : str, default "2024-01-01"
        Start date for time series.
    periods : int, default 252
        Number of daily observations.
    base_vix : float, default 15.0
        Starting VIX level.
    volatility : float, default 2.0
        Volatility of volatility (vol of vol).
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        VIX data with columns: date, level

    Notes
    -----
    - Uses mean-reverting process with occasional spikes
    - VIX constrained to positive values
    """
    logger.info("Generating VIX sample: periods=%d", periods)

    rng = np.random.default_rng(seed)
    dates = pd.date_range(start_date, periods=periods, freq="D")

    # Mean-reverting VIX with spike potential
    vix_close = [base_vix]
    mean_reversion_speed = 0.15
    mean_level = base_vix

    for i in range(periods - 1):
        # Occasional spike (5% probability)
        if rng.random() < 0.05:
            spike = rng.uniform(5, 15)
        else:
            spike = 0

        drift = mean_reversion_speed * (mean_level - vix_close[-1])
        shock = rng.normal(0, volatility)
        new_vix = max(8.0, vix_close[-1] + drift + shock + spike)
        vix_close.append(new_vix)

    df = pd.DataFrame(
        {
            "date": dates,
            "level": vix_close,
        }
    )

    logger.debug("Generated VIX sample: mean=%.2f", df["level"].mean())
    return df


def generate_etf_sample(
    start_date: str = "2024-01-01",
    periods: int = 252,
    ticker: str = "HYG",
    base_price: float = 80.0,
    volatility: float = 0.5,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic credit ETF price data.

    Parameters
    ----------
    start_date : str, default "2024-01-01"
        Start date for time series.
    periods : int, default 252
        Number of daily observations.
    ticker : str, default "HYG"
        ETF ticker symbol (HYG, LQD).
    base_price : float, default 80.0
        Starting price.
    volatility : float, default 0.5
        Daily price volatility.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        ETF data with columns: date, spread, ticker

    Notes
    -----
    - Uses geometric Brownian motion
    - Prices constrained to positive values
    """
    logger.info("Generating ETF sample: ticker=%s, periods=%d", ticker, periods)

    rng = np.random.default_rng(seed)
    dates = pd.date_range(start_date, periods=periods, freq="D")

    # Geometric Brownian motion for prices
    returns = rng.normal(0.0001, volatility / base_price, periods)
    price = base_price * np.exp(np.cumsum(returns))

    df = pd.DataFrame(
        {
            "date": dates,
            "spread": price,
            "ticker": [ticker] * periods,
        }
    )

    logger.debug("Generated ETF sample: mean_price=%.2f", df["spread"].mean())
    return df


def generate_full_sample_dataset(
    output_dir: str = "data/raw",
    start_date: str = "2023-01-01",
    periods: int = 252,
    seed: int = 42,
) -> dict[str, str]:
    """
    Generate complete sample dataset for testing.

    Parameters
    ----------
    output_dir : str, default "data/raw"
        Directory to save Parquet files.
    start_date : str, default "2023-01-01"
        Start date for all time series.
    periods : int, default 252
        Number of daily observations.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    dict[str, str]
        Dictionary mapping data type to file path.

    Notes
    -----
    Generates and saves:
    - CDX IG 5Y spreads
    - CDX HY 5Y spreads
    - VIX volatility
    - HYG and LQD ETF prices
    """
    from pathlib import Path

    logger.info("Generating full sample dataset: output_dir=%s", output_dir)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate CDX data (multiple indices)
    cdx_ig = generate_cdx_sample(
        start_date=start_date,
        periods=periods,
        index_name="CDX_IG",
        tenor="5Y",
        base_spread=70.0,
        volatility=3.0,
        seed=seed,
    )

    cdx_hy = generate_cdx_sample(
        start_date=start_date,
        periods=periods,
        index_name="CDX_HY",
        tenor="5Y",
        base_spread=350.0,
        volatility=15.0,
        seed=seed + 1,
    )

    cdx_all = pd.concat([cdx_ig, cdx_hy], ignore_index=True)
    cdx_path = output_path / "cdx_spreads.parquet"
    save_parquet(cdx_all, cdx_path)

    # Generate VIX data
    vix = generate_vix_sample(start_date=start_date, periods=periods, base_vix=16.0, seed=seed + 2)
    vix_path = output_path / "vix.parquet"
    save_parquet(vix, vix_path)

    # Generate ETF data (multiple tickers)
    hyg = generate_etf_sample(
        start_date=start_date,
        periods=periods,
        ticker="HYG",
        base_price=75.0,
        volatility=0.6,
        seed=seed + 3,
    )

    lqd = generate_etf_sample(
        start_date=start_date,
        periods=periods,
        ticker="LQD",
        base_price=110.0,
        volatility=0.4,
        seed=seed + 4,
    )

    etf_all = pd.concat([hyg, lqd], ignore_index=True)
    etf_path = output_path / "etf_prices.parquet"
    save_parquet(etf_all, etf_path)

    file_paths = {
        "cdx": str(cdx_path),
        "vix": str(vix_path),
        "etf": str(etf_path),
    }

    logger.info("Sample dataset generated: %s", file_paths)
    return file_paths


def generate_full_sample_sources(
    output_dir: str = "data/raw",
    start_date: str = "2023-01-01",
    periods: int = 252,
    seed: int = 42,
) -> dict[str, FileSource]:
    """
    Generate complete sample dataset and return FileSource configs.

    Parameters
    ----------
    output_dir : str, default "data/raw"
        Directory to save Parquet files.
    start_date : str, default "2023-01-01"
        Start date for all time series.
    periods : int, default 252
        Number of daily observations.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    dict[str, FileSource]
        Dictionary mapping data type to FileSource configuration.

    Notes
    -----
    Convenience wrapper around generate_full_sample_dataset that returns
    FileSource objects ready to use with fetch functions.
    """
    file_paths = generate_full_sample_dataset(output_dir, start_date, periods, seed)

    return {
        "cdx": FileSource(Path(file_paths["cdx"])),
        "vix": FileSource(Path(file_paths["vix"])),
        "etf": FileSource(Path(file_paths["etf"])),
    }


def generate_for_fetch_interface(
    output_dir: str | Path,
    start_date: str = "2020-01-01",
    end_date: str = "2025-01-01",
    seed: int = 42,
) -> dict[str, Path]:
    """
    Generate synthetic data matching fetch layer schema requirements.

    Creates individual files per security that work with fetch_cdx, fetch_vix,
    and fetch_etf functions. Data is saved to cache directory structure.

    Parameters
    ----------
    output_dir : str or Path
        Base directory for cache files (e.g., "data/cache/file").
    start_date : str, default "2020-01-01"
        Start date for time series.
    end_date : str, default "2025-01-01"
        End date for time series.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    dict[str, Path]
        Mapping of security identifier to file path.

    Notes
    -----
    Generates files matching fetch layer expectations:
    - CDX: spread column, security="cdx_ig_5y"
    - VIX: level column (renamed from close)
    - ETF: spread column (prices), security="hyg"
    """
    logger.info(
        "Generating synthetic data for fetch interface: %s to %s",
        start_date,
        end_date,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Calculate periods from date range
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    dates = pd.bdate_range(start=start, end=end)
    periods = len(dates)

    # Generate CDX IG 5Y - schema requires "spread" column
    cdx_df = generate_cdx_sample(
        start_date=start_date,
        periods=periods,
        index_name="CDX_IG",
        tenor="5Y",
        base_spread=60.0,
        volatility=5.0,
        seed=seed,
    )
    # Transform to match CDX schema (spread column, DatetimeIndex)
    cdx_df = cdx_df.set_index("date")
    cdx_df = cdx_df[["spread"]].copy()
    cdx_df["security"] = "cdx_ig_5y"
    cdx_path = output_path / "cdx_cdx_ig_5y.parquet"
    save_parquet(cdx_df, cdx_path)
    logger.info("Saved CDX to %s (%d rows)", cdx_path, len(cdx_df))

    # Generate VIX - schema requires "level" column
    vix_df = generate_vix_sample(
        start_date=start_date,
        periods=periods,
        base_vix=18.0,
        volatility=2.5,
        seed=seed + 1,
    )
    # Transform to match VIX schema (level column, DatetimeIndex)
    vix_df = vix_df.set_index("date")
    vix_df = vix_df[["level"]].copy()
    vix_path = output_path / "vix_vix.parquet"
    save_parquet(vix_df, vix_path)
    logger.info("Saved VIX to %s (%d rows)", vix_path, len(vix_df))

    # Generate ETF (HYG) - schema requires "spread" column
    # Use spread directly as it represents OAS-equivalent metric
    etf_df = generate_etf_sample(
        start_date=start_date,
        periods=periods,
        ticker="HYG",
        base_price=350.0,  # Spread-like value in bps
        volatility=15.0,
        seed=seed + 2,
    )
    # Transform to match ETF schema (spread column, DatetimeIndex)
    etf_df = etf_df.set_index("date")
    etf_df = etf_df[["spread"]].copy()
    etf_df["security"] = "hyg"
    etf_path = output_path / "etf_hyg.parquet"
    save_parquet(etf_df, etf_path)
    logger.info("Saved ETF to %s (%d rows)", etf_path, len(etf_df))

    file_paths = {
        "cdx_ig_5y": cdx_path,
        "vix": vix_path,
        "hyg": etf_path,
    }

    logger.info("Synthetic data generation complete: %d files", len(file_paths))
    return file_paths
