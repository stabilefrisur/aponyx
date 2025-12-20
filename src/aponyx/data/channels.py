"""
Data channel types and resolution logic for multi-ticker data fetching.

Defines fixed channel types (spread, price, level), purpose-based resolution,
and instrument-type defaults for automatic channel selection.
"""

from dataclasses import dataclass
from enum import Enum


class DataChannel(Enum):
    """
    Fixed data channel types.

    Attributes
    ----------
    SPREAD : str
        Credit spread in basis points (e.g., CDX OAS, ETF YAS_ISPREAD).
    PRICE : str
        Price level (e.g., ETF NAV, index price, CDX price).
    LEVEL : str
        Non-price values (e.g., VIX level).
    """

    SPREAD = "spread"
    PRICE = "price"
    LEVEL = "level"


class UsagePurpose(Enum):
    """
    Purpose of data request for channel resolution.

    Attributes
    ----------
    INDICATOR : str
        For signal/indicator computation (uses instrument_type defaults).
    PNL : str
        For backtest P&L calculation (uses quote_type from security spec).
    DISPLAY : str
        For visualization and reports (uses instrument_type defaults, overridable).
    """

    INDICATOR = "indicator"
    PNL = "pnl"
    DISPLAY = "display"


@dataclass(frozen=True)
class ChannelConfig:
    """
    Configuration for a single data channel.

    Attributes
    ----------
    bloomberg_ticker : str
        Bloomberg ticker for this channel (e.g., "CDX HY CDSI GEN 5Y SPRD Corp").
    field : str
        Bloomberg field to fetch (e.g., "PX_LAST", "YAS_ISPREAD").

    Examples
    --------
    >>> config = ChannelConfig(
    ...     bloomberg_ticker="CDX HY CDSI GEN 5Y SPRD Corp",
    ...     field="PX_LAST"
    ... )
    >>> config.bloomberg_ticker
    'CDX HY CDSI GEN 5Y SPRD Corp'
    """

    bloomberg_ticker: str
    field: str = "PX_LAST"

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.bloomberg_ticker:
            raise ValueError("bloomberg_ticker must not be empty")
        if not self.field:
            raise ValueError("field must not be empty")


class ChannelFetchError(Exception):
    """
    Raised when one or more channel fetches fail.

    Attributes
    ----------
    security_id : str
        Security that failed to fetch.
    failures : dict[DataChannel, str]
        Map of failed channels to error messages.

    Examples
    --------
    >>> try:
    ...     # Fetch that fails
    ...     pass
    ... except ChannelFetchError as e:
    ...     print(f"Failed channels: {e.failures}")
    """

    def __init__(self, security_id: str, failures: dict[DataChannel, str]):
        self.security_id = security_id
        self.failures = failures
        # Format failures for error message
        failures_str = ", ".join(
            f"{ch.value}: {msg}" for ch, msg in failures.items()
        )
        msg = f"Failed to fetch channels for '{security_id}': {{{failures_str}}}"
        super().__init__(msg)


# Default channel preferences per instrument type
# Used for INDICATOR and DISPLAY purposes; PNL uses quote_type directly
INSTRUMENT_DEFAULTS: dict[str, dict[str, DataChannel]] = {
    "cdx": {
        "indicator": DataChannel.SPREAD,
        "display": DataChannel.SPREAD,
    },
    "etf": {
        "indicator": DataChannel.SPREAD,
        "display": DataChannel.SPREAD,
    },
    "vix": {
        "indicator": DataChannel.LEVEL,
        "display": DataChannel.LEVEL,
    },
}
