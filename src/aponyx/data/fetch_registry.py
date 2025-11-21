"""
Instrument fetch function registry.

Maps instrument type strings to their fetch functions using catalog pattern.
Provides generic dispatch without hardcoded if/elif logic.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchSpec:
    """
    Metadata for instrument fetch function.

    Attributes
    ----------
    instrument : str
        Instrument type identifier (e.g., "cdx", "vix", "etf").
    fetch_fn : Callable
        Fetch function for this instrument.
    requires_security : bool
        Whether this instrument requires security parameter.
        True for CDX and ETF (multi-security), False for VIX (single-security).
    """

    instrument: str
    fetch_fn: Callable
    requires_security: bool


# Lazy-loaded registry to avoid circular imports
_FETCH_REGISTRY: dict[str, FetchSpec] | None = None


def _load_fetch_registry() -> dict[str, FetchSpec]:
    """
    Load fetch function registry.

    Registry is populated on first access to avoid import-time side effects.

    Returns
    -------
    dict[str, FetchSpec]
        Mapping from instrument type to fetch specification.
    """
    global _FETCH_REGISTRY

    if _FETCH_REGISTRY is not None:
        return _FETCH_REGISTRY

    # Import fetch functions
    from .fetch import fetch_cdx, fetch_vix, fetch_etf

    _FETCH_REGISTRY = {
        "cdx": FetchSpec(
            instrument="cdx",
            fetch_fn=fetch_cdx,
            requires_security=True,
        ),
        "vix": FetchSpec(
            instrument="vix",
            fetch_fn=fetch_vix,
            requires_security=False,
        ),
        "etf": FetchSpec(
            instrument="etf",
            fetch_fn=fetch_etf,
            requires_security=True,
        ),
    }

    logger.debug("Loaded fetch registry: %d instruments", len(_FETCH_REGISTRY))
    return _FETCH_REGISTRY


def get_fetch_spec(instrument: str) -> FetchSpec:
    """
    Get fetch specification for instrument type.

    Parameters
    ----------
    instrument : str
        Instrument type (e.g., "cdx", "vix", "etf").

    Returns
    -------
    FetchSpec
        Fetch specification with function and metadata.

    Raises
    ------
    ValueError
        If instrument type is not registered.

    Examples
    --------
    >>> spec = get_fetch_spec("vix")
    >>> spec.instrument
    'vix'
    >>> spec.requires_security
    False
    >>> df = spec.fetch_fn(FileSource("data.parquet"), use_cache=True)
    """
    registry = _load_fetch_registry()

    if instrument not in registry:
        raise ValueError(
            f"Unknown instrument type: '{instrument}'. "
            f"Available instruments: {sorted(registry.keys())}"
        )

    return registry[instrument]


def list_instruments() -> list[str]:
    """
    List all registered instrument types.

    Returns
    -------
    list[str]
        Sorted list of instrument type identifiers.

    Examples
    --------
    >>> list_instruments()
    ['cdx', 'etf', 'vix']
    """
    registry = _load_fetch_registry()
    return sorted(registry.keys())
