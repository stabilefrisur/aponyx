"""Synthetic data generation for testing and demonstrations.

Generates realistic market data for CDX, VIX, and ETF instruments
with configurable volatility, correlation, and trend parameters.
"""

import hashlib
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
    dates = pd.bdate_range(start=start_date, periods=periods)

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
    dates = pd.bdate_range(start=start_date, periods=periods)

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
    dates = pd.bdate_range(start=start_date, periods=periods)

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

    Creates individual files per security with channel columns that work with
    fetch_security_data() function. Each file contains columns for all defined
    channels in the security catalog.

    Parameters
    ----------
    output_dir : str or Path
        Base directory for raw files (e.g., "data/raw/synthetic").
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
    Generates data for all securities defined in bloomberg_securities.json with
    channel-based columns:
    - CDX indices: 'spread' column (+ 'price' column for securities with price channel)
    - VIX: 'level' column
    - ETFs: 'price' and 'spread' columns
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

    # Load parameters from config file
    config_path = Path(__file__).parent / "synthetic_params.json"
    with open(config_path, encoding="utf-8") as f:
        default_params = json.load(f)

    for security_id, security_config in securities.items():
        instrument_type = security_config["instrument_type"]
        channels_config = security_config.get("channels", {})

        logger.info("Generating %s data: %s", instrument_type, security_id)

        if instrument_type == "cdx":
            # Parse tenor from security_id or description
            tenor = "5Y" if "5y" in security_id.lower() else "10Y"
            index_name = security_id.upper().replace("_", " ")

            params = default_params["cdx"].get(
                security_id, default_params["cdx"]["default"]
            )

            # Generate spread data
            spread_df = generate_cdx_sample(
                start_date=start_date,
                periods=periods,
                index_name=index_name,
                tenor=tenor,
                base_spread=params["base_spread"],
                volatility=params["volatility"],
                seed=seed + seed_offset,
            )
            spread_df = spread_df.set_index("date")

            # Start with spread column
            df = spread_df[["spread"]].copy()

            # Add price column if security has price channel
            if "price" in channels_config:
                # Generate price data (inverted relationship with spread)
                # Higher spread = lower price, approximately
                base_price = 100.0  # Par value
                # Price ~ 100 - (spread / 100) with some noise
                price_values = (
                    base_price
                    - (df["spread"] / 100)
                    + np.random.default_rng(seed + seed_offset + 100).normal(
                        0, 0.5, len(df)
                    )
                )
                df["price"] = price_values.clip(50, 150)  # Reasonable bounds

            # Generate hash for raw storage naming
            safe_instrument = security_id.replace(".", "_").replace("/", "_")
            hash_input = (
                f"synthetic|{security_id}|{df.index.min()}|{df.index.max()}|{len(df)}"
            )
            file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            file_path = output_path / f"{safe_instrument}_{file_hash}.parquet"
            metadata_path = output_path / f"{safe_instrument}_{file_hash}.json"

        elif instrument_type == "vix":
            params = default_params["vix"]

            vix_df = generate_vix_sample(
                start_date=start_date,
                periods=periods,
                base_vix=params["base_vix"],
                volatility=params["volatility"],
                seed=seed + seed_offset,
            )

            # Transform to VIX schema with 'level' channel
            df = vix_df.set_index("date")
            df = df[["level"]].copy()

            # Generate hash for raw storage naming
            safe_instrument = security_id.replace(".", "_").replace("/", "_")
            hash_input = (
                f"synthetic|{security_id}|{df.index.min()}|{df.index.max()}|{len(df)}"
            )
            file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            file_path = output_path / f"{safe_instrument}_{file_hash}.parquet"
            metadata_path = output_path / f"{safe_instrument}_{file_hash}.json"

        elif instrument_type == "etf":
            params = default_params["etf"].get(
                security_id, default_params["etf"]["default"]
            )

            # Generate price data
            price_df = generate_etf_sample(
                start_date=start_date,
                periods=periods,
                ticker=security_id.upper(),
                base_price=params["base_price"],
                volatility=params["volatility"],
                seed=seed + seed_offset,
            )
            price_df = price_df.set_index("date")

            # Start DataFrame with price channel (rename 'spread' to 'price')
            df = price_df[["spread"]].rename(columns={"spread": "price"}).copy()

            # Add spread channel (OAS spread for ETF)
            # Generate realistic OAS spread values (typically 100-500 bps for HY, 50-150 for IG)
            if security_id == "hyg":
                base_oas = 350.0  # HY ETF
                oas_vol = 30.0
            else:  # lqd
                base_oas = 100.0  # IG ETF
                oas_vol = 10.0

            rng = np.random.default_rng(seed + seed_offset + 200)
            oas_spreads = [base_oas]
            for _ in range(periods - 1):
                drift = 0.1 * (base_oas - oas_spreads[-1])
                shock = rng.normal(0, oas_vol)
                new_spread = max(10.0, oas_spreads[-1] + drift + shock)
                oas_spreads.append(new_spread)
            df["spread"] = oas_spreads

            # Generate hash for raw storage naming
            safe_instrument = security_id.replace(".", "_").replace("/", "_")
            hash_input = (
                f"synthetic|{security_id}|{df.index.min()}|{df.index.max()}|{len(df)}"
            )
            file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            file_path = output_path / f"{safe_instrument}_{file_hash}.parquet"
            metadata_path = output_path / f"{safe_instrument}_{file_hash}.json"

        else:
            logger.warning("Unknown instrument type: %s", instrument_type)
            seed_offset += 1
            continue

        # Save data and metadata
        save_parquet(df, file_path)

        metadata = {
            "provider": "synthetic",
            "instrument": instrument_type,
            "security": security_id,
            "stored_at": pd.Timestamp.now().isoformat(),
            "date_range": {
                "start": str(df.index.min()),
                "end": str(df.index.max()),
            },
            "row_count": len(df),
            "columns": list(df.columns),
            "hash": file_hash,
            "generation_params": params,
        }
        from ..persistence.json_io import save_json

        save_json(metadata, metadata_path)

        file_paths[security_id] = file_path
        logger.info(
            "Saved %s to %s (%d rows, columns: %s)",
            security_id,
            file_path,
            len(df),
            list(df.columns),
        )

        seed_offset += 1

    # Generate registry.json mapping security_id to filename
    registry = {
        security_id: Path(file_path).name
        for security_id, file_path in file_paths.items()
    }
    registry_path = output_path / "registry.json"
    save_json(registry, registry_path)
    logger.info(
        "Saved security registry: %s (%d securities)", registry_path, len(registry)
    )

    logger.info("Synthetic data generation complete: %d files", len(file_paths))
    return file_paths
