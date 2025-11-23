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
    ...     instrument='CDX.NA.IG'
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
        self.data_directory = Path(data_directory).resolve()
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

    def _resolve_path(self, path: str | Path) -> Path:
        """
        Resolve path relative to data directory.

        Converts relative paths stored in registry to absolute paths
        for file operations.

        Parameters
        ----------
        path : str or Path
            Path from registry (may be relative or absolute).

        Returns
        -------
        Path
            Absolute path for file access.
        """
        p = Path(path)
        if p.is_absolute():
            return p
        return self.data_directory / p

    def _normalize_path(self, path: str | Path) -> str:
        """
        Normalize path to relative format for storage in registry.

        Converts absolute paths to relative paths from data_directory.
        Relative paths are stored as-is.

        Parameters
        ----------
        path : str or Path
            Path to normalize (absolute or relative).

        Returns
        -------
        str
            Relative path string for registry storage.
        """
        p = Path(path).resolve()
        try:
            # Try to make path relative to data_directory
            relative = p.relative_to(self.data_directory)
            return str(relative).replace("\\", "/")  # Use forward slashes
        except ValueError:
            # Path is outside data_directory, store as-is
            logger.warning("Path outside data directory, storing absolute: %s", p)
            return str(p)

    def register_dataset(
        self,
        name: str,
        file_path: str | Path,
        instrument: str,
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
        # Normalize to relative path for storage
        normalized_path = self._normalize_path(file_path)
        # Resolve to absolute path for file operations
        resolved_path = self._resolve_path(normalized_path)

        # Get dataset statistics if file exists
        if resolved_path.exists():
            try:
                df = load_parquet(resolved_path)
                start_date = (
                    df.index.min() if isinstance(df.index, pd.DatetimeIndex) else None
                )
                end_date = (
                    df.index.max() if isinstance(df.index, pd.DatetimeIndex) else None
                )
                row_count = len(df)
            except Exception as e:
                logger.warning(
                    "Failed to extract stats from %s: %s",
                    file_path,
                    str(e),
                )
                start_date = end_date = row_count = None
        else:
            logger.debug("Registering non-existent file: %s", resolved_path)
            start_date = end_date = row_count = None

        # Build registry entry using dataclass
        entry = DatasetEntry(
            instrument=instrument,
            file_path=normalized_path,
            registered_at=datetime.now().isoformat(),
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            row_count=row_count,
            metadata=metadata or {},
        )

        self._catalog[name] = entry.to_dict()
        self._save()

        logger.info(
            "Registered dataset: name=%s, instrument=%s, rows=%s",
            name,
            instrument,
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
            The file_path is returned as an absolute path.

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

        info = self._catalog[name].copy()
        # Resolve relative path to absolute for consumers
        info["file_path"] = str(self._resolve_path(info["file_path"]))
        return info

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
    ) -> list[str]:
        """
        List registered datasets, optionally filtered by instrument.

        Parameters
        ----------
        instrument : str, optional
            Filter by instrument (e.g., 'CDX.NA.IG', 'VIX').

        Returns
        -------
        list of str
            Sorted list of dataset names matching filters.

        Examples
        --------
        >>> registry.list_datasets(instrument='CDX.NA.IG')
        ['cdx_ig_5y', 'cdx_ig_10y']
        """
        datasets = []
        for name, info in self._catalog.items():
            if instrument and info.get("instrument") != instrument:
                continue
            datasets.append(name)
        return sorted(datasets)

    def find_dataset_by_security(self, security_id: str) -> str | None:
        """
        Find the most recent dataset for a specific security ID.

        Searches for datasets where metadata.params.security matches the
        provided security_id. Returns the most recently registered dataset
        if multiple matches exist.

        Parameters
        ----------
        security_id : str
            Security identifier (e.g., 'cdx_ig_5y', 'lqd', 'vix').

        Returns
        -------
        str or None
            Dataset name if found, None otherwise.

        Examples
        --------
        >>> registry.find_dataset_by_security('cdx_ig_5y')
        'cache_cdx_c3bedc49b771b0f2'
        >>> registry.find_dataset_by_security('vix')
        'cache_vix_d09015690dfa93d9'
        """
        matching_datasets = []

        for name, info in self._catalog.items():
            metadata = info.get("metadata", {})
            params = metadata.get("params", {})

            # Match by security ID in params
            if params.get("security") == security_id:
                matching_datasets.append(name)
            # For instruments without security param (VIX), match by security_id == instrument
            elif security_id == "vix" and info.get("instrument") == "vix":
                matching_datasets.append(name)

        if not matching_datasets:
            return None

        # Return most recent (sort by registration timestamp)
        return sorted(matching_datasets)[-1]

    def load_dataset_by_security(self, security_id: str) -> pd.DataFrame:
        """
        Find and load the most recent dataset for a specific security.

        Convenience method that combines find_dataset_by_security() with
        data loading from the registry.

        Parameters
        ----------
        security_id : str
            Security identifier (e.g., 'cdx_ig_5y', 'lqd', 'vix').

        Returns
        -------
        pd.DataFrame
            Loaded dataset with DatetimeIndex.

        Raises
        ------
        ValueError
            If no dataset found for the security ID.

        Examples
        --------
        >>> registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        >>> cdx_df = registry.load_dataset_by_security('cdx_ig_5y')
        >>> vix_df = registry.load_dataset_by_security('vix')
        """
        dataset_name = self.find_dataset_by_security(security_id)

        if dataset_name is None:
            raise ValueError(
                f"No dataset found for security '{security_id}'. "
                f"Available datasets: {', '.join(sorted(self._catalog.keys()))}"
            )

        info = self.get_dataset_info(dataset_name)
        return load_parquet(info["file_path"])

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
        file_path = self._resolve_path(entry["file_path"])

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
            file_path = self._resolve_path(self._catalog[name]["file_path"])
            if file_path.exists():
                file_path.unlink()
                logger.info(
                    "Deleted file for dataset: name=%s, path=%s", name, file_path
                )

        del self._catalog[name]
        self._save()
        logger.info("Removed dataset from registry: name=%s", name)

    def _save(self) -> None:
        """Persist registry catalog to JSON file."""
        save_json(self._catalog, self.registry_path)

    def __repr__(self) -> str:
        """String representation showing registry statistics."""
        return f"DataRegistry(path={self.registry_path}, datasets={len(self._catalog)})"
