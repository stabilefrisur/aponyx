"""
Calculator factory for resolving return calculators based on product metadata.

This module provides the resolve_calculator() function for automatic calculator
selection based on product quote_type. The factory pattern enables clean
separation between product configuration and calculator implementation.
"""

import logging

from .calculators import (
    ReturnCalculator,
    SpreadReturnCalculator,
    PriceReturnCalculator,
)

logger = logging.getLogger(__name__)


def resolve_calculator(
    quote_type: str,
    dv01_per_million: float | None = None,
) -> ReturnCalculator:
    """
    Resolve return calculator based on product quote type.

    Factory function for automatic calculator selection based on
    product metadata.

    Parameters
    ----------
    quote_type : str
        Product quote type. Must be 'spread' or 'price'.
    dv01_per_million : float | None, optional
        DV01 parameter. Required for spread-based products.

    Returns
    -------
    ReturnCalculator
        Appropriate calculator implementation.

    Raises
    ------
    ValueError
        If quote_type is unknown or required parameters missing.

    Examples
    --------
    >>> calc = resolve_calculator("spread", dv01_per_million=475.0)
    >>> isinstance(calc, SpreadReturnCalculator)
    True

    >>> calc = resolve_calculator("price")
    >>> isinstance(calc, PriceReturnCalculator)
    True
    """
    if quote_type == "spread":
        if dv01_per_million is None:
            raise ValueError("dv01_per_million is required for spread-based products")
        spread_calc = SpreadReturnCalculator(dv01_per_million=dv01_per_million)
        logger.debug(
            "Resolved SpreadReturnCalculator with dv01=%.1f",
            dv01_per_million,
        )
        return spread_calc

    elif quote_type == "price":
        price_calc = PriceReturnCalculator()
        logger.debug("Resolved PriceReturnCalculator")
        return price_calc

    else:
        raise ValueError(
            f"Unknown quote_type: '{quote_type}'. Must be 'spread' or 'price'"
        )


__all__ = [
    "resolve_calculator",
]
