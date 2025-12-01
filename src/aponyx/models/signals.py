"""
Core signal generation functions for CDX overlay strategy.

Implements the three pilot signals:
1. CDX-ETF basis (flow-driven mispricing)
2. CDX-VIX gap (cross-asset risk sentiment)
3. Spread momentum (short-term continuation)

LEGACY FUNCTIONS - BACKWARD COMPATIBILITY FACADE
================================================
The functions in this module are maintained for backward compatibility.
New code should use the indicator-signal separation pattern:
  - Define indicators in indicator_catalog.json
  - Compose signals in signal_catalog.json
  - Use compute_indicator() and compose_signal() functions

These facade functions internally call the new composition workflow
to ensure identical outputs while enabling code migration.
"""

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING
import pandas as pd

from .config import SignalConfig

if TYPE_CHECKING:
    from .registry import IndicatorRegistry, TransformationRegistry, SignalRegistry

logger = logging.getLogger(__name__)

# Lazy-loaded registries to avoid circular import
_indicator_registry: "IndicatorRegistry | None" = None
_transformation_registry: "TransformationRegistry | None" = None
_signal_registry: "SignalRegistry | None" = None


def _get_registries() -> tuple[
    "IndicatorRegistry", "TransformationRegistry", "SignalRegistry"
]:
    """
    Lazy-load registries to avoid circular imports.

    Returns
    -------
    tuple[IndicatorRegistry, TransformationRegistry, SignalRegistry]
        Loaded registry instances.
    """
    global _indicator_registry, _transformation_registry, _signal_registry

    if _indicator_registry is None:
        from ..config import (
            INDICATOR_CATALOG_PATH,
            TRANSFORMATION_CATALOG_PATH,
            SIGNAL_CATALOG_PATH,
        )
        from .registry import IndicatorRegistry, TransformationRegistry, SignalRegistry

        _indicator_registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        _transformation_registry = TransformationRegistry(TRANSFORMATION_CATALOG_PATH)
        _signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

    # Guaranteed to be non-None after if block
    assert _indicator_registry is not None
    assert _transformation_registry is not None
    assert _signal_registry is not None

    return _indicator_registry, _transformation_registry, _signal_registry


def compute_cdx_etf_basis(
    cdx_df: pd.DataFrame,
    etf_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    LEGACY: Compute normalized basis between CDX index spreads and ETF-implied spreads.

    This function is maintained for backward compatibility with existing workflows.
    New code should use:
        market_data = {"cdx": cdx_df, "etf": etf_df}
        signal = compose_signal(
            indicator_registry,
            transformation_registry,
            signal_metadata,
            market_data
        )

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
        Configuration parameters (unused in new pattern).

    Returns
    -------
    pd.Series
        Z-score normalized basis signal aligned to common dates.

    Notes
    -----
    - Internally calls compose_signal() with "cdx_etf_basis" signal definition
    - Output is identical to legacy implementation for reproducibility
    - Uses z-score normalization over rolling window for regime independence
    """
    logger.info(
        "Computing CDX-ETF basis (legacy facade): cdx_rows=%d, etf_rows=%d",
        len(cdx_df),
        len(etf_df),
    )

    # Import here to avoid circular dependency
    from .signal_composer import compose_signal

    # Get registries (lazy-loaded)
    indicator_reg, transformation_reg, signal_reg = _get_registries()

    # Prepare market data for new pattern
    market_data = {
        "cdx": cdx_df,
        "etf": etf_df,
    }

    # Get signal metadata from registry
    signal_metadata = signal_reg.get_metadata("cdx_etf_basis")

    # Compose signal using new pattern
    signal = compose_signal(
        indicator_reg,
        transformation_reg,
        asdict(signal_metadata),
        market_data,
    )

    valid_count = signal.notna().sum()
    logger.debug("Generated %d valid basis signals (via composition)", valid_count)

    return signal


def compute_cdx_vix_gap(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    LEGACY: Compute cross-asset risk sentiment gap between credit spreads and equity vol.

    This function is maintained for backward compatibility with existing workflows.
    New code should use:
        market_data = {"cdx": cdx_df, "vix": vix_df}
        signal = compose_signal(
            indicator_registry,
            transformation_registry,
            signal_metadata,
            market_data
        )

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
        Configuration parameters (unused in new pattern).

    Returns
    -------
    pd.Series
        Z-score normalized CDX-VIX gap signal.

    Notes
    -----
    - Internally calls compose_signal() with "cdx_vix_gap" signal definition
    - Output is identical to legacy implementation for reproducibility
    - Both CDX and VIX deviations are computed from their own rolling means
    - Gap computed as CDX stress minus VIX stress for consistent sign convention
    """
    logger.info(
        "Computing CDX-VIX gap (legacy facade): cdx_rows=%d, vix_rows=%d",
        len(cdx_df),
        len(vix_df),
    )

    # Import here to avoid circular dependency
    from .signal_composer import compose_signal

    # Get registries (lazy-loaded)
    indicator_reg, transformation_reg, signal_reg = _get_registries()

    # Prepare market data for new pattern
    market_data = {
        "cdx": cdx_df,
        "vix": vix_df,
    }

    # Get signal metadata from registry
    signal_metadata = signal_reg.get_metadata("cdx_vix_gap")

    # Compose signal using new pattern
    signal = compose_signal(
        indicator_reg,
        transformation_reg,
        asdict(signal_metadata),
        market_data,
    )

    valid_count = signal.notna().sum()
    logger.debug(
        "Generated %d valid CDX-VIX gap signals (via composition)", valid_count
    )

    return signal


def compute_spread_momentum(
    cdx_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    LEGACY: Compute short-term volatility-adjusted momentum in CDX spreads.

    This function is maintained for backward compatibility with existing workflows.
    New code should use:
        market_data = {"cdx": cdx_df}
        signal = compose_signal(
            indicator_registry,
            transformation_registry,
            signal_metadata,
            market_data
        )

    Captures continuation or mean-reversion tendencies over 3-10 day horizons.
    Positive signal suggests long credit risk (spreads tightening, momentum favorable).
    Negative signal suggests short credit risk (spreads widening, momentum unfavorable).

    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with DatetimeIndex and 'spread' column.
    config : SignalConfig | None
        Configuration parameters (unused in new pattern).

    Returns
    -------
    pd.Series
        Volatility-normalized momentum signal (change / rolling_std).

    Notes
    -----
    - Internally calls compose_signal() with "spread_momentum" signal definition
    - Output is identical to legacy implementation for reproducibility
    - Uses negative of spread change: tightening spreads give positive signal
    - Normalized by rolling volatility to make comparable across regimes
    """
    logger.info(
        "Computing spread momentum (legacy facade): cdx_rows=%d",
        len(cdx_df),
    )

    # Import here to avoid circular dependency
    from .signal_composer import compose_signal

    # Get registries (lazy-loaded)
    indicator_reg, transformation_reg, signal_reg = _get_registries()

    # Prepare market data for new pattern
    market_data = {
        "cdx": cdx_df,
    }

    # Get signal metadata from registry
    signal_metadata = signal_reg.get_metadata("spread_momentum")

    # Compose signal using new pattern
    signal = compose_signal(
        indicator_reg,
        transformation_reg,
        asdict(signal_metadata),
        market_data,
    )

    valid_count = signal.notna().sum()
    logger.debug("Generated %d valid momentum signals (via composition)", valid_count)

    return signal
