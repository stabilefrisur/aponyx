"""
Signal data requirements resolution.

Determines what market data to load based on signal catalog configuration.
Bridges signal metadata (models layer) with data loading (data layer).
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_required_data_keys(signal_catalog_path: Path) -> set[str]:
    """
    Get union of all data keys required by enabled signals.

    Use this to determine what market data to load before computing signals.
    Reads signal catalog JSON directly without importing models layer.

    The correct workflow is:
    1. Get required data keys from catalog
    2. Load all required data into market_data dict
    3. Compute all enabled signals at once

    Parameters
    ----------
    signal_catalog_path : Path
        Path to signal catalog JSON file.

    Returns
    -------
    set[str]
        Set of data keys (e.g., {"cdx", "etf", "vix"}) required
        by all enabled signals.

    Raises
    ------
    FileNotFoundError
        If signal catalog file does not exist.
    ValueError
        If catalog JSON is invalid or missing required fields.

    Examples
    --------
    >>> from aponyx.config import SIGNAL_CATALOG_PATH
    >>> from aponyx.data.requirements import get_required_data_keys
    >>> data_keys = get_required_data_keys(SIGNAL_CATALOG_PATH)
    >>> # Load all required data
    >>> market_data = {}
    >>> for key in data_keys:
    ...     market_data[key] = load_data_for(key)
    >>> # Compute all signals
    >>> from aponyx.models import compute_registered_signals, SignalConfig
    >>> from aponyx.models.registry import SignalRegistry
    >>> registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    >>> config = SignalConfig(lookback=20)
    >>> signals = compute_registered_signals(registry, market_data, config)
    """
    if not signal_catalog_path.exists():
        raise FileNotFoundError(f"Signal catalog not found: {signal_catalog_path}")

    # Load catalog JSON
    with open(signal_catalog_path, encoding="utf-8") as f:
        catalog_data = json.load(f)

    if not isinstance(catalog_data, list):
        raise ValueError("Signal catalog must be a JSON array")

    # Aggregate data requirements from enabled signals
    all_data_keys = set()

    for entry in catalog_data:
        # Skip disabled signals
        if not entry.get("enabled", True):
            continue

        # Get data requirements
        data_requirements = entry.get("data_requirements", {})
        if not isinstance(data_requirements, dict):
            raise ValueError(
                f"Signal '{entry.get('name', 'unknown')}' has invalid data_requirements. "
                f"Expected dict, got {type(data_requirements)}"
            )

        # Add all data keys
        all_data_keys.update(data_requirements.keys())

    logger.debug(
        "Required data keys from %d enabled signals: %s",
        sum(1 for e in catalog_data if e.get("enabled", True)),
        sorted(all_data_keys),
    )

    return all_data_keys
