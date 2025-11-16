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


def generate_for_fetch_interface(
    output_dir: str | Path,
    start_date: str = "2020-01-01",
    end_date: str = "2025-01-01",
    seed: int = 42,
) -> dict[str, Path]:
    """
    Generate synthetic data for all securities in bloomberg_securities.json.

    Creates individual files per security that work with fetch_cdx, fetch_vix,
    and fetch_etf functions. Uses bloomberg_instruments.json for schema mapping.

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
    Automatically generates data for all securities defined in bloomberg_securities.json:
    - CDX indices: spread column with realistic credit dynamics
    - VIX: level column with volatility spikes
    - ETFs: spread column representing option-adjusted spreads
    """
    import json

    logger.info(
        "Generating synthetic data for fetch interface: %s to %s",
        start_date,
        end_date,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load security and instrument configurations
    config_dir = Path(__file__).parent
    with open(config_dir / "bloomberg_securities.json") as f:
        securities = json.load(f)

    # Calculate periods from date range
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    dates = pd.bdate_range(start=start, end=end)
    periods = len(dates)

    file_paths = {}
    seed_offset = 0

    # Default parameters by instrument type
    default_params = {
        "cdx": {
            "cdx_ig_5y": {"base_spread": 60.0, "volatility": 5.0},
            "cdx_ig_10y": {"base_spread": 70.0, "volatility": 6.0},
            "cdx_hy_5y": {"base_spread": 350.0, "volatility": 20.0},
            "itrx_xover_5y": {"base_spread": 280.0, "volatility": 18.0},
            "itrx_eur_5y": {"base_spread": 55.0, "volatility": 4.5},
        },
        "vix": {"base_vix": 18.0, "volatility": 2.5},
        "etf": {
            "hyg": {"base_price": 350.0, "volatility": 15.0},
            "lqd": {"base_price": 100.0, "volatility": 8.0},
        },
    }

    for security_id, security_config in securities.items():
        instrument_type = security_config["instrument_type"]

        logger.info("Generating %s data: %s", instrument_type, security_id)

        if instrument_type == "cdx":
            # Parse tenor from security_id or description
            tenor = "5Y" if "5y" in security_id.lower() else "10Y"
            index_name = security_id.upper().replace("_", " ")

            params = default_params["cdx"].get(
                security_id, {"base_spread": 100.0, "volatility": 10.0}
            )

            df = generate_cdx_sample(
                start_date=start_date,
                periods=periods,
                index_name=index_name,
                tenor=tenor,
                base_spread=params["base_spread"],
                volatility=params["volatility"],
                seed=seed + seed_offset,
            )

            # Transform to CDX schema
            df = df.set_index("date")
            df = df[["spread"]].copy()
            df["security"] = security_id
            file_path = output_path / f"cdx_{security_id}.parquet"

        elif instrument_type == "vix":
            params = default_params["vix"]

            df = generate_vix_sample(
                start_date=start_date,
                periods=periods,
                base_vix=params["base_vix"],
                volatility=params["volatility"],
                seed=seed + seed_offset,
            )

            # Transform to VIX schema
            df = df.set_index("date")
            df = df[["level"]].copy()
            file_path = output_path / f"vix_{security_id}.parquet"

        elif instrument_type == "etf":
            params = default_params["etf"].get(
                security_id, {"base_price": 200.0, "volatility": 12.0}
            )

            df = generate_etf_sample(
                start_date=start_date,
                periods=periods,
                ticker=security_id.upper(),
                base_price=params["base_price"],
                volatility=params["volatility"],
                seed=seed + seed_offset,
            )

            # Transform to ETF schema
            df = df.set_index("date")
            df = df[["spread"]].copy()
            df["security"] = security_id
            file_path = output_path / f"etf_{security_id}.parquet"

        else:
            logger.warning("Unknown instrument type: %s", instrument_type)
            seed_offset += 1
            continue

        save_parquet(df, file_path)
        file_paths[security_id] = file_path
        logger.info("Saved %s to %s (%d rows)", security_id, file_path, len(df))

        seed_offset += 1

    logger.info("Synthetic data generation complete: %d files", len(file_paths))
    return file_paths
