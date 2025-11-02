"""Bloomberg instrument and security registry.

Centralizes Bloomberg configuration in JSON catalogs including instrument
specifications, field mappings, and security-to-ticker mappings.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from ..config import BLOOMBERG_SECURITIES_PATH, BLOOMBERG_INSTRUMENTS_PATH

logger = logging.getLogger(__name__)

_INSTRUMENTS_PATH = BLOOMBERG_INSTRUMENTS_PATH
_SECURITIES_PATH = BLOOMBERG_SECURITIES_PATH
_INSTRUMENTS_CATALOG: dict[str, Any] | None = None
_SECURITIES_CATALOG: dict[str, Any] | None = None


@dataclass(frozen=True)
class BloombergInstrumentSpec:
    """Bloomberg instrument specification with field mappings."""

    instrument_type: str
    description: str
    bloomberg_fields: tuple[str, ...]
    field_mapping: dict[str, str]
    requires_security_metadata: bool


@dataclass(frozen=True)
class BloombergSecuritySpec:
    """Bloomberg security specification with ticker mapping."""

    security_id: str
    description: str
    bloomberg_ticker: str
    instrument_type: str


def _load_instruments_catalog() -> dict[str, Any]:
    """Load Bloomberg instruments catalog from JSON file."""
    global _INSTRUMENTS_CATALOG
    if _INSTRUMENTS_CATALOG is None:
        with open(_INSTRUMENTS_PATH, encoding="utf-8") as f:
            _INSTRUMENTS_CATALOG = json.load(f)
        logger.debug("Loaded Bloomberg instruments catalog from %s", _INSTRUMENTS_PATH)
    return _INSTRUMENTS_CATALOG


def _load_securities_catalog() -> dict[str, Any]:
    """Load Bloomberg securities catalog from JSON file."""
    global _SECURITIES_CATALOG
    if _SECURITIES_CATALOG is None:
        with open(_SECURITIES_PATH, encoding="utf-8") as f:
            _SECURITIES_CATALOG = json.load(f)
        logger.debug("Loaded Bloomberg securities catalog from %s", _SECURITIES_PATH)
    return _SECURITIES_CATALOG


def validate_bloomberg_registry() -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Load and validate Bloomberg instrument and security registries.

    Ensures all securities reference valid instrument types defined in the
    instruments catalog. This validates the configuration integrity at startup.

    Returns
    -------
    tuple[dict[str, Any], dict[str, Any]]
        (instruments, securities) dictionaries.

    Raises
    ------
    ValueError
        If any security references an undefined instrument type.

    Examples
    --------
    >>> instruments, securities = validate_bloomberg_registry()
    >>> len(instruments)
    3
    >>> len(securities)
    8
    """
    instruments = _load_instruments_catalog()
    securities = _load_securities_catalog()

    # Validate all securities reference valid instrument types
    valid_types = set(instruments.keys())
    invalid_refs = []

    for sec_id, sec_config in securities.items():
        inst_type = sec_config.get("instrument_type")
        if inst_type not in valid_types:
            invalid_refs.append((sec_id, inst_type))

    if invalid_refs:
        error_msg = "Securities reference undefined instrument types:\n"
        for sec_id, inst_type in invalid_refs:
            error_msg += f"  - '{sec_id}' references '{inst_type}'\n"
        error_msg += f"Valid instrument types: {', '.join(sorted(valid_types))}"
        raise ValueError(error_msg)

    logger.info(
        "Bloomberg registry validated: %d instruments, %d securities",
        len(instruments),
        len(securities),
    )
    return instruments, securities


def get_instrument_spec(instrument_type: str) -> BloombergInstrumentSpec:
    """
    Get Bloomberg instrument specification.

    Parameters
    ----------
    instrument_type : str
        Instrument type identifier ('cdx', 'vix', 'etf').

    Returns
    -------
    BloombergInstrumentSpec
        Specification with field mappings and metadata requirements.

    Raises
    ------
    ValueError
        If instrument type not found in catalog.
    """
    catalog = _load_instruments_catalog()

    if instrument_type not in catalog:
        available = ", ".join(sorted(catalog.keys()))
        raise ValueError(
            f"Unknown instrument type: {instrument_type}. "
            f"Available: {available}"
        )

    spec_data = catalog[instrument_type]
    return BloombergInstrumentSpec(
        instrument_type=instrument_type,
        description=spec_data["description"],
        bloomberg_fields=tuple(spec_data["bloomberg_fields"]),
        field_mapping=spec_data["field_mapping"],
        requires_security_metadata=spec_data["requires_security_metadata"],
    )


def get_security_spec(security_id: str) -> BloombergSecuritySpec:
    """
    Get Bloomberg security specification.

    Parameters
    ----------
    security_id : str
        Internal security identifier (e.g., 'cdx_ig_5y', 'hyg').

    Returns
    -------
    BloombergSecuritySpec
        Security specification with Bloomberg ticker and instrument type.

    Raises
    ------
    ValueError
        If security not found in catalog.
    """
    catalog = _load_securities_catalog()

    if security_id not in catalog:
        available = ", ".join(sorted(catalog.keys()))
        raise ValueError(
            f"Security '{security_id}' not found in catalog. "
            f"Available: {available}"
        )

    spec_data = catalog[security_id]
    return BloombergSecuritySpec(
        security_id=security_id,
        description=spec_data["description"],
        bloomberg_ticker=spec_data["bloomberg_ticker"],
        instrument_type=spec_data["instrument_type"],
    )


def get_bloomberg_ticker(security_id: str) -> str:
    """
    Get Bloomberg ticker for a security.

    Parameters
    ----------
    security_id : str
        Internal security identifier (e.g., 'cdx_ig_5y', 'hyg').

    Returns
    -------
    str
        Bloomberg Terminal ticker string.

    Raises
    ------
    ValueError
        If security not found in catalog.

    Examples
    --------
    >>> get_bloomberg_ticker("cdx_ig_5y")
    'CDX IG CDSI GEN 5Y Corp'
    >>> get_bloomberg_ticker("hyg")
    'HYG US Equity'
    """
    spec = get_security_spec(security_id)
    return spec.bloomberg_ticker


def get_security_from_ticker(bloomberg_ticker: str) -> str:
    """
    Reverse lookup: get security ID from Bloomberg ticker.

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
        If Bloomberg ticker not found in catalog.

    Examples
    --------
    >>> get_security_from_ticker("CDX IG CDSI GEN 5Y Corp")
    'cdx_ig_5y'
    >>> get_security_from_ticker("HYG US Equity")
    'hyg'
    """
    catalog = _load_securities_catalog()

    # Build reverse lookup
    for sec_id, spec_data in catalog.items():
        if spec_data["bloomberg_ticker"] == bloomberg_ticker:
            return sec_id

    raise ValueError(
        f"Bloomberg ticker '{bloomberg_ticker}' not found in catalog. "
        "Ticker may not be configured for use in aponyx."
    )


def list_instrument_types() -> list[str]:
    """
    Return list of available instrument types.

    Returns
    -------
    list[str]
        Instrument type identifiers.
    """
    catalog = _load_instruments_catalog()
    return list(catalog.keys())


def list_securities(instrument_type: str | None = None) -> list[str]:
    """
    Return list of available securities.

    Parameters
    ----------
    instrument_type : str or None, default None
        If provided, filter to securities of this instrument type.

    Returns
    -------
    list[str]
        List of security identifiers.
    """
    catalog = _load_securities_catalog()

    if instrument_type is None:
        return list(catalog.keys())

    return [
        sec_id
        for sec_id, spec_data in catalog.items()
        if spec_data["instrument_type"] == instrument_type
    ]


__all__ = [
    "BloombergInstrumentSpec",
    "BloombergSecuritySpec",
    "get_instrument_spec",
    "get_security_spec",
    "get_bloomberg_ticker",
    "get_security_from_ticker",
    "list_instrument_types",
    "list_securities",
    "validate_bloomberg_registry",
]
