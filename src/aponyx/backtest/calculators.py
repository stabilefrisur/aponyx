"""
Return calculator protocol and implementations.

This module defines the ReturnCalculator protocol for computing daily P&L
based on market data. Implementations include:
- SpreadReturnCalculator: DV01-based P&L for spread products (CDX indices)
- PriceReturnCalculator: Simple returns for price-based products (ETFs)

The calculator pattern enables extensibility for future product types while
maintaining type safety via Protocol structural subtyping.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class ReturnCalculator(Protocol):
    """
    Protocol for computing daily returns.

    Implementations must provide a compute_daily_return method that
    calculates P&L for a single trading day.

    This protocol enables structural subtyping (duck typing with type hints).
    Use isinstance() checks for validation at startup due to @runtime_checkable.
    """

    def compute_daily_return(
        self,
        position: float,
        price_today: float,
        price_yesterday: float,
        notional_mm: float,
    ) -> float:
        """
        Compute daily P&L for a single day.

        Parameters
        ----------
        position : float
            Current position size (signed).
            Binary mode: -1, 0, or +1.
            Proportional mode: actual notional in MM.
        price_today : float
            Today's market price/spread.
        price_yesterday : float
            Previous day's market price/spread.
        notional_mm : float
            Base notional in millions (for binary mode sizing).

        Returns
        -------
        float
            Daily P&L in dollars (gross, before transaction costs).
        """
        ...


@dataclass(frozen=True)
class SpreadReturnCalculator:
    """
    Return calculator for spread-based products (CDX indices).

    Uses DV01-based P&L calculation:
    P&L = -position × ΔSpread × DV01 × notional

    Parameters
    ----------
    dv01_per_million : float
        Dollar value of 01 per $1MM notional.

    Notes
    -----
    The price_today and price_yesterday parameters represent spread values
    for this calculator. A long position profits when spreads tighten
    (negative spread change).
    """

    dv01_per_million: float

    def __post_init__(self) -> None:
        """Validate DV01 is positive."""
        if self.dv01_per_million <= 0:
            raise ValueError(
                f"dv01_per_million must be positive, got {self.dv01_per_million}"
            )

    def compute_daily_return(
        self,
        position: float,
        price_today: float,
        price_yesterday: float,
        notional_mm: float,
    ) -> float:
        """
        Compute spread-based daily P&L using DV01.

        Parameters
        ----------
        position : float
            Current position size (signed).
        price_today : float
            Today's spread level (bps).
        price_yesterday : float
            Previous day's spread level (bps).
        notional_mm : float
            Base notional in millions.

        Returns
        -------
        float
            Daily P&L in dollars.
        """
        spread_change = price_today - price_yesterday
        # Long position profits when spreads tighten (negative spread_change)
        return -position * spread_change * self.dv01_per_million * notional_mm


@dataclass(frozen=True)
class PriceReturnCalculator:
    """
    Return calculator for price-based products (ETFs, bonds).

    Uses simple price returns:
    P&L = position × (Price[t]/Price[t-1] - 1) × Notional

    This calculator is stateless - no initialization parameters needed.
    """

    def compute_daily_return(
        self,
        position: float,
        price_today: float,
        price_yesterday: float,
        notional_mm: float,
    ) -> float:
        """
        Compute price-based daily P&L using simple returns.

        Parameters
        ----------
        position : float
            Current position size (signed).
        price_today : float
            Today's price level.
        price_yesterday : float
            Previous day's price level.
        notional_mm : float
            Base notional in millions.

        Returns
        -------
        float
            Daily P&L in dollars.

        Raises
        ------
        ValueError
            If price_yesterday is non-positive.
        """
        if price_yesterday <= 0:
            raise ValueError(f"price_yesterday must be positive, got {price_yesterday}")

        daily_return = (price_today / price_yesterday) - 1.0
        # Long position profits when price increases
        return position * daily_return * notional_mm * 1_000_000

    def validate_price_data(self, prices: pd.Series) -> None:
        """
        Validate price series before backtest.

        Called by engine at startup (fail-fast validation).

        Parameters
        ----------
        prices : pd.Series
            Price series to validate.

        Raises
        ------
        ValueError
            If any prices are non-positive.
        """
        if (prices <= 0).any():
            invalid = prices[prices <= 0]
            raise ValueError(
                f"Price data contains {len(invalid)} non-positive values. "
                f"First invalid dates: {list(invalid.index[:5])}"
            )


__all__ = [
    "ReturnCalculator",
    "SpreadReturnCalculator",
    "PriceReturnCalculator",
]
