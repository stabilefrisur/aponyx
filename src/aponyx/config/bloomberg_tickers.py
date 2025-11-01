"""Bloomberg ticker registry for market data fetching.

This module provides the authoritative mapping from internal security identifiers
to actual Bloomberg Terminal ticker symbols. The registry handles Bloomberg's
idiosyncratic ticker formats across CDX, iTraxx, ETF, and index instruments.

Security Name Convention
-----------------------
Internal security names use lowercase with underscores (e.g., 'cdx_ig_5y', 'hyg')
to distinguish them from actual Bloomberg tickers.

Bloomberg Ticker Formats
------------------------
CDX IG: "CDX IG CDSI GEN 5Y Corp"
CDX HY: "CDX HY CDSI GEN 5Y SPRD Corp" (SPRD for spread quote vs. price)
iTraxx: "ITRX XOVER CDSI GEN 5Y Corp", "ITRX EUR CDSI GEN 5Y Corp"
ETFs: "{TICKER} US Equity" (e.g., "HYG US Equity")
VIX: "VIX Index"

Usage
-----
>>> from aponyx.config.bloomberg_tickers import BLOOMBERG_TICKER_REGISTRY
>>> ticker = BLOOMBERG_TICKER_REGISTRY["cdx_ig_5y"]
>>> print(ticker)
'CDX IG CDSI GEN 5Y Corp'
"""

# Bloomberg ticker registry: security name -> Bloomberg ticker
BLOOMBERG_TICKER_REGISTRY: dict[str, str] = {
    # CDX North America Investment Grade
    "cdx_ig_5y": "CDX IG CDSI GEN 5Y Corp",
    "cdx_ig_10y": "CDX IG CDSI GEN 10Y Corp",
    # CDX North America High Yield (SPRD for spread quote)
    "cdx_hy_5y": "CDX HY CDSI GEN 5Y SPRD Corp",
    # iTraxx Europe
    "itrx_xover_5y": "ITRX XOVER CDSI GEN 5Y Corp",
    "itrx_eur_5y": "ITRX EUR CDSI GEN 5Y Corp",
    # Credit ETFs
    "hyg": "HYG US Equity",
    "lqd": "LQD US Equity",
    # Volatility Index
    "vix": "VIX Index",
}


def get_bloomberg_ticker(security: str) -> str:
    """Get Bloomberg ticker for a security.

    Parameters
    ----------
    security : str
        Internal security identifier (e.g., 'cdx_ig_5y', 'hyg').

    Returns
    -------
    str
        Bloomberg Terminal ticker string.

    Raises
    ------
    ValueError
        If security not found in registry.

    Examples
    --------
    >>> get_bloomberg_ticker("cdx_ig_5y")
    'CDX IG CDSI GEN 5Y Corp'
    >>> get_bloomberg_ticker("hyg")
    'HYG US Equity'
    """
    if security not in BLOOMBERG_TICKER_REGISTRY:
        available = ", ".join(sorted(BLOOMBERG_TICKER_REGISTRY.keys()))
        raise ValueError(
            f"Security '{security}' not found in Bloomberg ticker registry. "
            f"Available securities: {available}"
        )
    return BLOOMBERG_TICKER_REGISTRY[security]


def get_security_from_ticker(bloomberg_ticker: str) -> str:
    """Reverse lookup: get security name from Bloomberg ticker.

    Parameters
    ----------
    bloomberg_ticker : str
        Bloomberg Terminal ticker string.

    Returns
    -------
    str
        Internal security identifier.

    Raises
    ------
    ValueError
        If Bloomberg ticker not found in registry.

    Examples
    --------
    >>> get_security_from_ticker("CDX IG CDSI GEN 5Y Corp")
    'cdx_ig_5y'
    >>> get_security_from_ticker("HYG US Equity")
    'hyg'
    """
    # Build reverse lookup
    reverse_registry = {v: k for k, v in BLOOMBERG_TICKER_REGISTRY.items()}

    if bloomberg_ticker not in reverse_registry:
        raise ValueError(
            f"Bloomberg ticker '{bloomberg_ticker}' not found in registry. "
            "This ticker may not be configured for use in aponyx."
        )
    return reverse_registry[bloomberg_ticker]
