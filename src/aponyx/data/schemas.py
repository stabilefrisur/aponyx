"""
Data schemas and validation rules for market data.

Defines expected column names, types, and constraints for each data source.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CDXSchema:
    """Schema for CDX index data."""

    date_col: str = "date"
    spread_col: str = "spread"
    security_col: str = "security"  # e.g., "cdx_ig_5y", "cdx_hy_5y"

    required_cols: tuple[str, ...] = ("date", "spread")

    # Validation constraints
    min_spread: float = 0.0  # Spreads in basis points
    max_spread: float = 10000.0  # 100% spread cap


@dataclass(frozen=True)
class VIXSchema:
    """Schema for VIX volatility index data."""

    date_col: str = "date"
    close_col: str = "close"

    required_cols: tuple[str, ...] = ("date", "close")

    # Validation constraints
    min_vix: float = 0.0
    max_vix: float = 200.0  # Extreme stress cap


@dataclass(frozen=True)
class ETFSchema:
    """Schema for credit ETF data (HYG, LQD)."""

    date_col: str = "date"
    close_col: str = "close"
    security_col: str = "security"  # e.g., "hyg", "lqd"

    required_cols: tuple[str, ...] = ("date", "close")

    # Validation constraints
    min_price: float = 0.0
    max_price: float = 10000.0  # Sanity check


# Schema registry for runtime lookup
SCHEMAS: dict[str, Any] = {
    "cdx": CDXSchema(),
    "vix": VIXSchema(),
    "etf": ETFSchema(),
}
