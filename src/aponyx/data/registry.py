"""
Data registry for tracking available datasets and their metadata.

Provides a centralized catalog of market data files with versioning,
validation status, and update timestamps.
"""

import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any
import pandas as pd

from ..persistence.json_io import save_json, load_json
from ..persistence.parquet_io import load_parquet

logger = logging.getLogger(__name__)


@dataclass
class DatasetEntry:
    """
    Metadata for a registered dataset.

    Attributes
    ----------
    instrument : str
        Instrument identifier (e.g., 'CDX.NA.IG', 'VIX', 'HYG').
    file_path : str
        Path to the Parquet file.
    registered_at : str
        ISO format timestamp of registration.
    tenor : str or None
        Tenor specification (e.g., '5Y', '10Y'), None if not applicable.
    start_date : str or None
        ISO format start date of data coverage.
    end_date : str or None
        ISO format end date of data coverage.
    row_count : int or None
        Number of rows in the dataset.
    last_updated : str or None
        ISO format timestamp of last statistics update.
    metadata : dict[str, Any]
        Additional user-defined metadata.
    """

    instrument: str
    file_path: str
    registered_at: str
    tenor: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    row_count: int | None = None
    last_updated: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetEntry":
        """Create entry from dictionary loaded from JSON."""
        return cls(**data)


class DataRegistry:
    """
    Registry for tracking and managing available market data files.

    Maintains a catalog of Parquet datasets with metadata including:
    - Data source and instrument
    - Date range coverage
    - Last update timestamp
    - Validation status

    Parameters
    ----------
    registry_path : str or Path
        Path to the registry JSON file.
    data_directory : str or Path
        Root directory containing data files.

    Examples
    --------
    >>> registry = DataRegistry('data/registry.json', 'data/')
    >>> registry.register_dataset(
    ...     name='cdx_ig_5y',
    ...     file_path='data/cdx_ig_5y.parquet',
    ...     instrument='CDX.NA.IG',
    ...     tenor='5Y'
    ... )
    >>> info = registry.get_dataset_info('cdx_ig_5y')
    """

    def __init__(
        self,
        registry_path: str | Path,
        data_directory: str | Path,
    ):
        """Initialize registry with paths to catalog and data storage."""
        self.registry_path = Path(registry_path)
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)

        # Load existing registry or create new
        if self.registry_path.exists():
            self._catalog = load_json(self.registry_path)
            logger.info(
                "Loaded existing registry: path=%s, datasets=%d",
                self.registry_path,
                len(self._catalog),
            )
        else:
            self._catalog = {}
            self._save()
            logger.info("Created new registry: path=%s", self.registry_path)

    def register_dataset(
        self,
        name: str,
        file_path: str | Path,
        instrument: str,
        tenor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Register a dataset in the catalog with metadata.

        Parameters
        ----------
        name : str
            Unique identifier for the dataset (e.g., 'cdx_ig_5y').
        file_path : str or Path
            Path to the Parquet file (relative to data_directory or absolute).
        instrument : str
            Instrument identifier (e.g., 'CDX.NA.IG', 'VIX', 'HYG').
        tenor : str, optional
            Tenor specification for CDX instruments (e.g., '5Y', '10Y').
        metadata : dict, optional
            Additional metadata to store with the dataset.

        Examples
        --------
        >>> registry.register_dataset(
        ...     name='vix_index',
        ...     file_path='data/vix.parquet',
        ...     instrument='VIX',
        ...     metadata={'source': 'CBOE', 'frequency': 'daily'}
        ... )
        """
        file_path = Path(file_path)

        # Get dataset statistics if file exists
        if file_path.exists():
            try:
                df = load_parquet(file_path)
                start_date = df.index.min() if isinstance(df.index, pd.DatetimeIndex) else None
                end_date = df.index.max() if isinstance(df.index, pd.DatetimeIndex) else None
                row_count = len(df)
            except Exception as e:
                logger.warning(
                    "Failed to extract stats from %s: %s",
                    file_path,
                    str(e),
                )
                start_date = end_date = row_count = None
        else:
            logger.debug("Registering non-existent file: %s", file_path)
            start_date = end_date = row_count = None

        # Build registry entry using dataclass
        entry = DatasetEntry(
            instrument=instrument,
            tenor=tenor,
            file_path=str(file_path),
            registered_at=datetime.now().isoformat(),
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            row_count=row_count,
            metadata=metadata or {},
        )

        self._catalog[name] = entry.to_dict()
        self._save()

        logger.info(
            "Registered dataset: name=%s, instrument=%s, tenor=%s, rows=%s",
            name,
            instrument,
            tenor,
            row_count,
        )

    def get_dataset_info(self, name: str) -> dict[str, Any]:
        """
        Retrieve metadata for a registered dataset.

        Parameters
        ----------
        name : str
            Dataset identifier.

        Returns
        -------
        dict[str, Any]
            Dataset metadata including file path, date range, etc.

        Raises
        ------
        KeyError
            If dataset name not found in registry.

        Notes
        -----
        Returns a copy to prevent external modification of catalog.
        For type-safe access, use `get_dataset_entry()` instead.
        """
        if name not in self._catalog:
            raise KeyError(f"Dataset '{name}' not found in registry")
        return self._catalog[name].copy()

    def get_dataset_entry(self, name: str) -> DatasetEntry:
        """
        Retrieve metadata as a typed DatasetEntry object.

        Parameters
        ----------
        name : str
            Dataset identifier.

        Returns
        -------
        DatasetEntry
            Typed dataset metadata with attribute access.

        Raises
        ------
        KeyError
            If dataset name not found in registry.

        Examples
        --------
        >>> entry = registry.get_dataset_entry('cdx_ig_5y')
        >>> print(entry.instrument)  # IDE autocomplete works
        'CDX.NA.IG'
        >>> print(entry.row_count)
        215
        """
        if name not in self._catalog:
            raise KeyError(f"Dataset '{name}' not found in registry")
        return DatasetEntry.from_dict(self._catalog[name])

    def list_datasets(
        self,
        instrument: str | None = None,
        tenor: str | None = None,
    ) -> list[str]:
        """
        List registered datasets, optionally filtered by instrument/tenor.

        Parameters
        ----------
        instrument : str, optional
            Filter by instrument (e.g., 'CDX.NA.IG', 'VIX').
        tenor : str, optional
            Filter by tenor (e.g., '5Y', '10Y').

        Returns
        -------
        list of str
            Sorted list of dataset names matching filters.

        Examples
        --------
        >>> registry.list_datasets(instrument='CDX.NA.IG')
        ['cdx_ig_5y', 'cdx_ig_10y']
        >>> registry.list_datasets(tenor='5Y')
        ['cdx_ig_5y', 'cdx_hy_5y', 'cdx_xo_5y']
        """
        datasets = []
        for name, info in self._catalog.items():
            if instrument and info.get("instrument") != instrument:
                continue
            if tenor and info.get("tenor") != tenor:
                continue
            datasets.append(name)
        return sorted(datasets)

    def update_dataset_stats(self, name: str) -> None:
        """
        Refresh date range and row count statistics for a dataset.

        Parameters
        ----------
        name : str
            Dataset identifier.

        Raises
        ------
        KeyError
            If dataset not found in registry.
        FileNotFoundError
            If dataset file does not exist.
        """
        if name not in self._catalog:
            raise KeyError(f"Dataset '{name}' not found in registry")

        entry = self._catalog[name]
        file_path = Path(entry["file_path"])

        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        df = load_parquet(file_path)

        if isinstance(df.index, pd.DatetimeIndex):
            entry["start_date"] = df.index.min().isoformat()
            entry["end_date"] = df.index.max().isoformat()
        entry["row_count"] = len(df)
        entry["last_updated"] = datetime.now().isoformat()

        self._save()

        logger.info(
            "Updated dataset stats: name=%s, rows=%d, date_range=%s to %s",
            name,
            len(df),
            entry["start_date"],
            entry["end_date"],
        )

    def remove_dataset(self, name: str, delete_file: bool = False) -> None:
        """
        Remove a dataset from the registry.

        Parameters
        ----------
        name : str
            Dataset identifier.
        delete_file : bool, default False
            If True, also delete the underlying Parquet file.

        Raises
        ------
        KeyError
            If dataset not found in registry.
        """
        if name not in self._catalog:
            raise KeyError(f"Dataset '{name}' not found in registry")

        if delete_file:
            file_path = Path(self._catalog[name]["file_path"])
            if file_path.exists():
                file_path.unlink()
                logger.info("Deleted file for dataset: name=%s, path=%s", name, file_path)

        del self._catalog[name]
        self._save()
        logger.info("Removed dataset from registry: name=%s", name)

    def _save(self) -> None:
        """Persist registry catalog to JSON file."""
        save_json(self._catalog, self.registry_path)

    def __repr__(self) -> str:
        """String representation showing registry statistics."""
        return f"DataRegistry(path={self.registry_path}, " f"datasets={len(self._catalog)})"
