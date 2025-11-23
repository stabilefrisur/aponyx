"""
JSON I/O utilities for metadata, parameters, and run logs.

Handles serialization of dictionaries with support for common data types
including datetime, Path, and numpy arrays.
"""

import json
import logging
from pathlib import Path
from typing import Any
from datetime import datetime, date
import numpy as np

logger = logging.getLogger(__name__)


class EnhancedJSONEncoder(json.JSONEncoder):
    """
    JSON encoder with support for datetime, Path, and numpy types.

    Extends standard JSONEncoder to handle common scientific computing types
    that appear in metadata and parameter dictionaries.
    """

    def default(self, obj: Any) -> Any:
        """Convert non-serializable objects to JSON-compatible types."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def save_json(
    data: dict[str, Any],
    path: str | Path,
    indent: int = 2,
    sort_keys: bool = True,
) -> Path:
    """
    Save dictionary to JSON file with enhanced type support.

    Parameters
    ----------
    data : dict
        Dictionary to serialize. Supports datetime, Path, and numpy types.
    path : str or Path
        Target file path. Parent directories created if needed.
    indent : int, default 2
        Number of spaces for indentation (for readability).
    sort_keys : bool, default True
        Whether to sort dictionary keys alphabetically.

    Returns
    -------
    Path
        Absolute path to the saved file.

    Examples
    --------
    >>> metadata = {
    ...     'timestamp': datetime.now(),
    ...     'params': {'window': 5, 'threshold': 0.5},
    ...     'version': '0.1.0'
    ... }
    >>> save_json(metadata, 'logs/run_20241025.json')
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Saving JSON to %s (%d top-level keys)", path, len(data))

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            cls=EnhancedJSONEncoder,
            indent=indent,
            sort_keys=sort_keys,
            ensure_ascii=False,
        )

    logger.debug("Successfully saved %d bytes to %s", path.stat().st_size, path)
    return path.absolute()


def load_json(path: str | Path) -> dict[str, Any]:
    """
    Load dictionary from JSON file.

    Parameters
    ----------
    path : str or Path
        Source file path.

    Returns
    -------
    dict
        Deserialized dictionary.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    json.JSONDecodeError
        If the file contains invalid JSON.

    Examples
    --------
    >>> metadata = load_json('logs/run_20241025.json')
    >>> print(metadata['timestamp'])
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    logger.info("Loading JSON from %s", path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    logger.debug(
        "Loaded JSON with %d top-level keys", len(data) if isinstance(data, dict) else 0
    )
    return data
