"""
Core signal generation functions for CDX overlay strategy.

Implements the three pilot signals:
1. CDX-ETF basis (flow-driven mispricing)
2. CDX-VIX gap (cross-asset risk sentiment)
3. Spread momentum (short-term continuation)
"""

import logging
import pandas as pd

from ..data.transforms import apply_transform
from .config import SignalConfig

logger = logging.getLogger(__name__)


def compute_cdx_etf_basis(
    cdx_df: pd.DataFrame,
    etf_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    Compute normalized basis between CDX index spreads and ETF-implied spreads.

    The signal captures temporary mispricing driven by ETF flows and liquidity
    constraints. Positive values indicate CDX is cheap relative to ETF (long CDX
    vs short ETF). Negative values indicate CDX is expensive (short CDX vs long ETF).

    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with DatetimeIndex and 'spread' column.
    etf_df : pd.DataFrame
        ETF spread data with DatetimeIndex and 'spread' column.
    config : SignalConfig | None
        Configuration parameters. Uses defaults if None.

    Returns
    -------
    pd.Series
        Z-score normalized basis signal aligned to common dates.

    Notes
    -----
    - Uses z-score normalization over rolling window for regime independence.
    - Assumes ETF prices have been converted to spread-equivalent units externally.
    - Missing values are forward-filled before alignment to avoid spurious gaps.
    """
    if config is None:
        config = SignalConfig()

    logger.info(
        "Computing CDX-ETF basis: cdx_rows=%d, etf_rows=%d, lookback=%d",
        len(cdx_df),
        len(etf_df),
        config.lookback,
    )

    # Align data to common dates
    cdx_spread = cdx_df["spread"]
    etf_spread = etf_df["spread"].reindex(cdx_df.index, method="ffill")

    # Compute raw basis
    raw_basis = cdx_spread - etf_spread

    # Normalize using rolling z-score
    signal = apply_transform(
        raw_basis,
        "z_score",
        window=config.lookback,
        min_periods=config.min_periods,
    )

    valid_count = signal.notna().sum()
    logger.debug("Generated %d valid basis signals", valid_count)

    return signal


def compute_cdx_vix_gap(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    Compute cross-asset risk sentiment gap between credit spreads and equity vol.

    Identifies divergence between CDX and VIX movements. Positive values indicate
    credit stress outpacing equity stress (long credit risk). Negative values indicate
    equity stress outpacing credit stress (short credit risk).

    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spreads with DatetimeIndex and 'spread' column.
    vix_df : pd.DataFrame
        VIX levels with DatetimeIndex and 'level' column.
    config : SignalConfig | None
        Configuration parameters. Uses defaults if None.

    Returns
    -------
    pd.Series
        Z-score normalized CDX-VIX gap signal.

    Notes
    -----
    - Both CDX and VIX deviations are computed from their own rolling means.
    - Gap computed as CDX stress minus VIX stress for consistent sign convention.
    - Normalized to account for varying volatility regimes.
    - Filters out transient spikes by using mean deviation over the lookback period.
    """
    if config is None:
        config = SignalConfig()

    logger.info(
        "Computing CDX-VIX gap: cdx_rows=%d, vix_rows=%d, lookback=%d",
        len(cdx_df),
        len(vix_df),
        config.lookback,
    )

    # Align data to common dates
    cdx = cdx_df["spread"]
    vix = vix_df["level"].reindex(cdx_df.index, method="ffill")

    # Compute deviations from rolling means
    cdx_deviation = (
        cdx
        - cdx.rolling(
            window=config.lookback,
            min_periods=config.min_periods,
        ).mean()
    )
    vix_deviation = (
        vix
        - vix.rolling(
            window=config.lookback,
            min_periods=config.min_periods,
        ).mean()
    )

    # Raw gap: CDX stress minus VIX stress
    # Positive when credit stress outpaces equity stress (buy CDX)
    # Negative when equity stress outpaces credit stress (sell CDX)
    raw_gap = cdx_deviation - vix_deviation

    # Normalize the gap
    signal = apply_transform(
        raw_gap,
        "z_score",
        window=config.lookback,
        min_periods=config.min_periods,
    )

    valid_count = signal.notna().sum()
    logger.debug("Generated %d valid CDX-VIX gap signals", valid_count)

    return signal


def compute_spread_momentum(
    cdx_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    Compute short-term volatility-adjusted momentum in CDX spreads.

    Captures continuation or mean-reversion tendencies over 3-10 day horizons.
    Positive signal suggests long credit risk (spreads tightening, momentum favorable).
    Negative signal suggests short credit risk (spreads widening, momentum unfavorable).

    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with DatetimeIndex and 'spread' column.
    config : SignalConfig | None
        Configuration parameters. Uses defaults if None.

    Returns
    -------
    pd.Series
        Volatility-normalized momentum signal (change / rolling_std).

    Notes
    -----
    - Uses negative of spread change: tightening spreads give positive signal.
    - Normalized by rolling volatility to make comparable across regimes.
    - Short lookback (5-10 days) suitable for tactical overlay strategy.
    - Positive signal indicates tightening momentum (bullish credit).
    """
    if config is None:
        config = SignalConfig()

    logger.info(
        "Computing spread momentum: cdx_rows=%d, lookback=%d",
        len(cdx_df),
        config.lookback,
    )

    spread = cdx_df["spread"]

    # Compute volatility-normalized change
    # Negate because tightening spreads (negative change) should give positive signal
    normalized = apply_transform(
        spread,
        "normalized_change",
        window=config.lookback,
        min_periods=config.min_periods,
        periods=config.lookback,
    )
    signal = -normalized

    valid_count = signal.notna().sum()
    logger.debug("Generated %d valid momentum signals", valid_count)

    return signal
