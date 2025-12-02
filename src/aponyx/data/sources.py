"""
Data source configuration for pluggable data providers.

Defines source types (file, Bloomberg, API) and factory for provider resolution.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileSource:
    """
    File-based data source with security-to-file mapping.

    Attributes
    ----------
    base_dir : Path
        Base directory containing data files.
    registry_path : Path or None
        Path to registry JSON file. If None, defaults to {base_dir}/registry.json.
    security_mapping : dict[str, str]
        Mapping from security ID to filename (auto-loaded from registry).
    """

    base_dir: Path
    registry_path: Path | None = None
    security_mapping: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Load security mapping from registry file."""
        import json
        
        # Convert base_dir to Path if string
        if isinstance(self.base_dir, str):
            object.__setattr__(self, "base_dir", Path(self.base_dir))
        
        # Determine registry path
        if self.registry_path is None:
            registry_path = self.base_dir / "registry.json"
        else:
            registry_path = self.registry_path if isinstance(self.registry_path, Path) else Path(self.registry_path)
        
        # Load security mapping from registry if not provided
        if self.security_mapping is None:
            if registry_path.exists():
                with open(registry_path, encoding="utf-8") as f:
                    mapping = json.load(f)
                object.__setattr__(self, "security_mapping", mapping)
                logger.debug("Loaded security mapping from %s: %d securities", registry_path, len(mapping))
            else:
                raise FileNotFoundError(
                    f"Registry file not found: {registry_path}. "
                    "Generate synthetic data or provide explicit security_mapping."
                )


@dataclass(frozen=True)
class BloombergSource:
    """
    Bloomberg Terminal data source.

    Notes
    -----
    Requires active Bloomberg Terminal session.
    Connection is handled automatically by xbbg wrapper.
    """

    pass


@dataclass(frozen=True)
class APISource:
    """
    Generic REST API data source.

    Attributes
    ----------
    endpoint : str
        API endpoint URL.
    params : dict[str, Any]
        Additional request parameters.
    """

    endpoint: str
    params: dict[str, Any] | None = None


# Union type for all data sources
DataSource = FileSource | BloombergSource | APISource


class DataProvider(Protocol):
    """
    Protocol for data provider implementations.

    All providers must implement fetch method with standardized signature.
    """

    def fetch(
        self,
        instrument: str,
        start_date: str | None = None,
        end_date: str | None = None,
        **params: Any,
    ) -> pd.DataFrame:
        """
        Fetch data for specified instrument and date range.

        Parameters
        ----------
        instrument : str
            Instrument identifier (e.g., 'CDX.NA.IG.5Y', 'VIX', 'HYG').
        start_date : str or None
            Start date in ISO format (YYYY-MM-DD).
        end_date : str or None
            End date in ISO format (YYYY-MM-DD).
        **params : Any
            Provider-specific parameters.

        Returns
        -------
        pd.DataFrame
            Data with DatetimeIndex.
        """
        ...


def resolve_provider(source: DataSource) -> str:
    """
    Resolve data source to provider type identifier.

    Parameters
    ----------
    source : DataSource
        Data source configuration.

    Returns
    -------
    str
        Provider type: 'file', 'bloomberg', or 'api'.

    Examples
    --------
    >>> resolve_provider(FileSource("data.parquet"))
    'file'
    >>> resolve_provider(BloombergSource())
    'bloomberg'
    """
    if isinstance(source, FileSource):
        return "file"
    elif isinstance(source, BloombergSource):
        return "bloomberg"
    elif isinstance(source, APISource):
        return "api"
    else:
        raise ValueError(f"Unknown source type: {type(source)}")
