"""
Security catalog registry with channel configurations.

Provides SecuritySpec dataclass and SecurityCatalog registry for channel-aware
security management with fail-fast validation.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .channels import DataChannel, ChannelConfig, UsagePurpose, INSTRUMENT_DEFAULTS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecuritySpec:
    """
    Security specification with channel configurations.

    Attributes
    ----------
    security_id : str
        Unique identifier (e.g., "cdx_hy_5y").
    description : str
        Human-readable description.
    instrument_type : str
        Category: "cdx", "etf", "vix".
    quote_type : str
        Primary quote type: "spread" or "price".
    channels : dict[DataChannel, ChannelConfig]
        Available channels and their configurations.
    dv01_per_million : float | None
        DV01 per million notional (required for spread quote_type).
    transaction_cost_bps : float | None
        Transaction cost in basis points (required for tradeable products).

    Examples
    --------
    >>> channels = {
    ...     DataChannel.SPREAD: ChannelConfig("CDX IG CDSI GEN 5Y Corp"),
    ... }
    >>> spec = SecuritySpec(
    ...     security_id="cdx_ig_5y",
    ...     description="CDX North America Investment Grade 5Y",
    ...     instrument_type="cdx",
    ...     quote_type="spread",
    ...     channels=channels,
    ...     dv01_per_million=475.0,
    ... )
    """

    security_id: str
    description: str
    instrument_type: str
    quote_type: str
    channels: dict[DataChannel, ChannelConfig]
    dv01_per_million: float | None = None
    transaction_cost_bps: float | None = None

    def __post_init__(self) -> None:
        """Validate security specification constraints.

        Raises
        ------
        ValueError
            - If quote_type='spread' but dv01_per_million is missing
            - If quote_type='spread' but dv01_per_million <= 0
            - If no channels are defined
            - If quote_type is not 'spread' or 'price'
            - If instrument_type is unknown
            - If quote_type='spread' but no SPREAD channel defined (non-VIX only)
            - If quote_type='price' but no PRICE channel defined (non-VIX only)
            - If dv01_per_million is provided for price-quoted product (warning logged)
        """
        # Validate quote_type is valid first (needed for subsequent checks)
        if self.quote_type not in ("spread", "price"):
            raise ValueError(
                f"Security '{self.security_id}' has invalid quote_type='{self.quote_type}'. "
                "Must be 'spread' or 'price'"
            )

        # Validate instrument_type is known
        if self.instrument_type not in INSTRUMENT_DEFAULTS:
            raise ValueError(
                f"Security '{self.security_id}' has unknown instrument_type='{self.instrument_type}'. "
                f"Must be one of: {list(INSTRUMENT_DEFAULTS.keys())}"
            )

        # Validate at least one channel defined
        if not self.channels:
            raise ValueError(
                f"Security '{self.security_id}' must define at least one channel"
            )

        # VIX is a special case - non-tradeable index, uses LEVEL channel
        # Skip P&L-related validations for VIX
        if self.instrument_type == "vix":
            return

        # Validate quote_type requires DV01 for spread products
        if self.quote_type == "spread":
            if self.dv01_per_million is None:
                raise ValueError(
                    f"Security '{self.security_id}' has quote_type='spread' "
                    "but missing dv01_per_million. "
                    "Spread-quoted products require DV01 for P&L calculation."
                )
            if self.dv01_per_million <= 0:
                raise ValueError(
                    f"Security '{self.security_id}' has invalid dv01_per_million={self.dv01_per_million}. "
                    "DV01 must be a positive value."
                )

        # Validate P&L channel availability (quote_type determines P&L channel)
        if self.quote_type == "spread":
            if DataChannel.SPREAD not in self.channels:
                available = [c.value for c in self.channels.keys()]
                raise ValueError(
                    f"Security '{self.security_id}' has quote_type='spread' "
                    f"but no SPREAD channel defined. "
                    f"Available channels: {available}. "
                    "Spread-quoted products require a SPREAD channel for P&L."
                )
        elif self.quote_type == "price":
            if DataChannel.PRICE not in self.channels:
                available = [c.value for c in self.channels.keys()]
                raise ValueError(
                    f"Security '{self.security_id}' has quote_type='price' "
                    f"but no PRICE channel defined. "
                    f"Available channels: {available}. "
                    "Price-quoted products require a PRICE channel for P&L."
                )

        # Log warning if DV01 is provided for price-quoted product (ignored)
        if self.quote_type == "price" and self.dv01_per_million is not None:
            logger.warning(
                "Security '%s' has quote_type='price' but dv01_per_million=%s is provided. "
                "DV01 is ignored for price-quoted products.",
                self.security_id,
                self.dv01_per_million,
            )

    def has_channel(self, channel: DataChannel) -> bool:
        """
        Check if security supports the given channel.

        Parameters
        ----------
        channel : DataChannel
            Channel to check.

        Returns
        -------
        bool
            True if channel is available.
        """
        return channel in self.channels

    def get_channel_config(self, channel: DataChannel) -> ChannelConfig:
        """
        Get configuration for a channel.

        Parameters
        ----------
        channel : DataChannel
            Channel to get config for.

        Returns
        -------
        ChannelConfig
            Channel configuration.

        Raises
        ------
        ValueError
            If channel is not available for this security.
            Error message includes security ID, requested channel,
            and list of available channels.
        """
        if channel not in self.channels:
            available = [c.value for c in self.channels.keys()]
            raise ValueError(
                f"Channel '{channel.value}' not available for security "
                f"'{self.security_id}'. Available channels: {available}. "
                f"Check bloomberg_securities.json to verify channel configuration."
            )
        return self.channels[channel]

    def list_channels(self) -> list[DataChannel]:
        """
        List all available channels.

        Returns
        -------
        list[DataChannel]
            Available channels.
        """
        return list(self.channels.keys())


class SecurityCatalog:
    """
    Registry of security specifications with channel configurations.

    Loads from bloomberg_securities.json with full validation at init.

    Attributes
    ----------
    catalog_path : Path
        Path to the JSON catalog file.

    Examples
    --------
    >>> from aponyx.config import BLOOMBERG_SECURITIES_PATH
    >>> catalog = SecurityCatalog(BLOOMBERG_SECURITIES_PATH)
    >>> spec = catalog.get_spec("cdx_ig_5y")
    >>> spec.instrument_type
    'cdx'
    """

    def __init__(self, catalog_path: Path):
        """
        Initialize catalog from JSON file.

        Parameters
        ----------
        catalog_path : Path
            Path to bloomberg_securities.json.

        Raises
        ------
        FileNotFoundError
            If catalog file does not exist.
        ValueError
            If any security specification is invalid.
        """
        self._catalog_path = catalog_path
        self._securities: dict[str, SecuritySpec] = {}
        self._load_catalog()
        self._validate_all()

    def _load_catalog(self) -> None:
        """Load catalog from JSON file."""
        if not self._catalog_path.exists():
            raise FileNotFoundError(f"Catalog file not found: {self._catalog_path}")

        with open(self._catalog_path, encoding="utf-8") as f:
            raw_catalog = json.load(f)

        for security_id, config in raw_catalog.items():
            # Parse channels from JSON structure
            channels_raw = config.get("channels", {})
            channels: dict[DataChannel, ChannelConfig] = {}

            for channel_name, channel_config in channels_raw.items():
                try:
                    channel = DataChannel(channel_name)
                except ValueError:
                    raise ValueError(
                        f"Security '{security_id}' has invalid channel name "
                        f"'{channel_name}'. Must be one of: spread, price, level"
                    )

                channels[channel] = ChannelConfig(
                    bloomberg_ticker=channel_config["bloomberg_ticker"],
                    field=channel_config.get("field", "PX_LAST"),
                )

            # Handle legacy format (single bloomberg_ticker, no channels dict)
            if not channels and "bloomberg_ticker" in config:
                # Legacy: single ticker mapped to default channel based on instrument_type
                instrument_type = config.get("instrument_type", "")
                if instrument_type == "vix":
                    default_channel = DataChannel.LEVEL
                elif instrument_type in ("cdx", "etf"):
                    # For spread quote_type, map to spread channel
                    # For price quote_type, map to price channel
                    quote_type = config.get("quote_type", "spread")
                    default_channel = (
                        DataChannel.SPREAD
                        if quote_type == "spread"
                        else DataChannel.PRICE
                    )
                else:
                    default_channel = DataChannel.SPREAD

                channels[default_channel] = ChannelConfig(
                    bloomberg_ticker=config["bloomberg_ticker"],
                    field="PX_LAST",
                )

            spec = SecuritySpec(
                security_id=security_id,
                description=config.get("description", ""),
                instrument_type=config.get("instrument_type", ""),
                quote_type=config.get("quote_type", "spread"),
                channels=channels,
                dv01_per_million=config.get("dv01_per_million"),
                transaction_cost_bps=config.get("transaction_cost_bps"),
            )
            self._securities[security_id] = spec

        logger.info(
            "Loaded security catalog: %d securities from %s",
            len(self._securities),
            self._catalog_path,
        )

    def _validate_all(self) -> None:
        """
        Validate all securities have required fields.

        Raises
        ------
        ValueError
            If any validation fails.
        """
        for security_id, spec in self._securities.items():
            # VIX is a special case - it's not tradeable and uses LEVEL channel
            # Skip P&L channel validation for VIX
            if spec.instrument_type == "vix":
                continue

            # Validate P&L channel availability for tradeable securities
            if spec.quote_type == "spread":
                if not spec.has_channel(DataChannel.SPREAD):
                    raise ValueError(
                        f"Security '{security_id}' has quote_type='spread' but "
                        "no SPREAD channel defined"
                    )
            elif spec.quote_type == "price":
                if not spec.has_channel(DataChannel.PRICE):
                    raise ValueError(
                        f"Security '{security_id}' has quote_type='price' but "
                        "no PRICE channel defined"
                    )

        logger.debug("Security catalog validation passed")

    def get_spec(self, security_id: str) -> SecuritySpec:
        """
        Get security specification by ID.

        Parameters
        ----------
        security_id : str
            Security identifier.

        Returns
        -------
        SecuritySpec
            Complete security specification.

        Raises
        ------
        ValueError
            If security_id is unknown.
        """
        if security_id not in self._securities:
            available = sorted(self._securities.keys())
            raise ValueError(
                f"Unknown security: '{security_id}'. Available: {available}"
            )
        return self._securities[security_id]

    def resolve_channel(
        self,
        security_id: str,
        purpose: UsagePurpose,
        override: DataChannel | None = None,
    ) -> DataChannel:
        """
        Resolve which channel to use for a security and purpose.

        Parameters
        ----------
        security_id : str
            Security identifier.
        purpose : UsagePurpose
            Why the data is being requested.
        override : DataChannel or None
            Explicit channel override (e.g., from workflow config).

        Returns
        -------
        DataChannel
            The channel to fetch.

        Raises
        ------
        ValueError
            If resolved channel is not available for security.
            Error includes purpose, security, and available channels.

        Examples
        --------
        >>> catalog.resolve_channel("cdx_ig_5y", UsagePurpose.INDICATOR)
        DataChannel.SPREAD
        >>> catalog.resolve_channel("vix", UsagePurpose.INDICATOR)
        DataChannel.LEVEL
        >>> catalog.resolve_channel("hyg", UsagePurpose.PNL)
        DataChannel.PRICE
        """
        spec = self.get_spec(security_id)

        if override is not None:
            # Validate override is available
            if not spec.has_channel(override):
                available = [c.value for c in spec.list_channels()]
                raise ValueError(
                    f"Channel override '{override.value}' not available for "
                    f"security '{security_id}'. Available channels: {available}. "
                    f"Check bloomberg_securities.json for channel configuration."
                )
            return override

        # Use purpose-based resolution
        if purpose == UsagePurpose.PNL:
            # P&L uses quote_type directly
            resolved_channel = DataChannel(spec.quote_type)
            # Validate the channel exists (should be guaranteed by __post_init__)
            if not spec.has_channel(resolved_channel):
                available = [c.value for c in spec.list_channels()]
                raise ValueError(
                    f"P&L channel '{resolved_channel.value}' (from quote_type) "
                    f"not available for security '{security_id}'. "
                    f"Available channels: {available}. "
                    f"This indicates a catalog configuration error."
                )
            return resolved_channel
        else:
            # Indicator/Display use instrument type defaults
            defaults = INSTRUMENT_DEFAULTS.get(spec.instrument_type)
            if defaults is None:
                raise ValueError(
                    f"Unknown instrument type '{spec.instrument_type}' for "
                    f"security '{security_id}'. Cannot resolve channel for "
                    f"purpose '{purpose.value}'."
                )
            resolved_channel = defaults[purpose.value]
            # Validate the resolved channel is available
            if not spec.has_channel(resolved_channel):
                available = [c.value for c in spec.list_channels()]
                raise ValueError(
                    f"Default channel '{resolved_channel.value}' for {purpose.value} "
                    f"purpose not available for security '{security_id}' "
                    f"(instrument_type='{spec.instrument_type}'). "
                    f"Available channels: {available}. "
                    f"Add the missing channel to bloomberg_securities.json."
                )
            return resolved_channel

    def list_securities(self, instrument_type: str | None = None) -> list[str]:
        """
        List all security IDs, optionally filtered by instrument type.

        Parameters
        ----------
        instrument_type : str or None
            Filter by instrument type (cdx, etf, vix).

        Returns
        -------
        list[str]
            Security IDs.
        """
        if instrument_type is None:
            return list(self._securities.keys())
        return [
            s
            for s, spec in self._securities.items()
            if spec.instrument_type == instrument_type
        ]

    def __len__(self) -> int:
        """Return number of securities in catalog."""
        return len(self._securities)

    def __contains__(self, security_id: str) -> bool:
        """Check if security exists in catalog."""
        return security_id in self._securities
