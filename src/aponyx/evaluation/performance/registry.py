"""
Registry for tracking performance evaluations.

Provides CRUD operations for evaluation metadata with JSON persistence.
Follows the SuitabilityRegistry pattern for mutable state management.
"""

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aponyx.persistence import load_json, save_json

from .config import PerformanceResult

logger = logging.getLogger(__name__)


@dataclass
class PerformanceEntry:
    """
    Metadata record for a performance evaluation.

    Attributes
    ----------
    evaluation_id : str
        Unique identifier for this evaluation.
    signal_id : str
        Signal name/identifier.
    strategy_id : str
        Strategy identifier (from backtest config).
    evaluated_at : str
        ISO timestamp of evaluation.
    sharpe_ratio : float
        Sharpe ratio from base metrics.
    max_drawdown : float
        Maximum drawdown from base metrics.
    stability_score : float
        Overall stability score (0-1).
    evaluator_version : str
        Version of evaluator used.
    report_path : str | None
        Path to generated report file, if saved.
    metadata : dict[str, Any]
        Additional metadata (config, extended metrics, attribution).
    """

    evaluation_id: str
    signal_id: str
    strategy_id: str
    evaluated_at: str
    sharpe_ratio: float
    max_drawdown: float
    stability_score: float
    evaluator_version: str
    report_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformanceEntry":
        """Create entry from dictionary."""
        return cls(**data)


class PerformanceRegistry:
    """
    Registry for tracking performance evaluations.

    Implements CRUD operations (create, read, update, delete) with
    JSON persistence. Follows the SuitabilityRegistry pattern for
    mutable state management.

    Parameters
    ----------
    registry_path : str | Path
        Path to JSON registry file.

    Examples
    --------
    >>> from aponyx.config import PERFORMANCE_REGISTRY_PATH
    >>> registry = PerformanceRegistry(PERFORMANCE_REGISTRY_PATH)
    >>> eval_id = registry.register_evaluation(result, "cdx_etf_basis", "simple_threshold")
    >>> entry = registry.get_evaluation(eval_id)
    >>> evaluations = registry.list_evaluations(signal_id="cdx_etf_basis")
    """

    def __init__(self, registry_path: str | Path):
        """
        Initialize registry with JSON persistence.

        Parameters
        ----------
        registry_path : str | Path
            Path to registry JSON file.
        """
        self.registry_path = Path(registry_path)
        self._catalog: dict[str, dict] = {}

        # Load existing registry or create new
        if self.registry_path.exists():
            try:
                self._catalog = load_json(self.registry_path)
                logger.info(
                    "Loaded existing performance registry: %d evaluations",
                    len(self._catalog),
                )
            except Exception as e:
                logger.warning(
                    "Failed to load registry from %s: %s, creating new",
                    self.registry_path,
                    e,
                )
                self._catalog = {}
                self._save()
        else:
            logger.info("Creating new performance registry at %s", self.registry_path)
            self._save()

    def register_evaluation(
        self,
        result: PerformanceResult,
        signal_id: str,
        strategy_id: str,
        report_path: str | None = None,
    ) -> str:
        """
        Register new performance evaluation result.

        Parameters
        ----------
        result : PerformanceResult
            Performance evaluation result to register.
        signal_id : str
            Signal identifier.
        strategy_id : str
            Strategy identifier from backtest config.
        report_path : str | None
            Path to saved report file.

        Returns
        -------
        str
            Unique evaluation ID for retrieval.

        Notes
        -----
        Evaluation ID format: {signal_id}_{strategy_id}_{timestamp}
        Automatically persists registry to disk.
        """
        # Generate unique evaluation ID
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        evaluation_id = f"{signal_id}_{strategy_id}_{timestamp_str}"

        logger.debug("Registering performance evaluation: %s", evaluation_id)

        # Extract key metrics from PerformanceMetrics dataclass
        sharpe_ratio = result.metrics.sharpe_ratio
        max_drawdown = result.metrics.max_drawdown

        # Create entry
        entry = PerformanceEntry(
            evaluation_id=evaluation_id,
            signal_id=signal_id,
            strategy_id=strategy_id,
            evaluated_at=result.timestamp,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            stability_score=result.stability_score,
            evaluator_version=result.metadata.get("evaluator_version", "unknown"),
            report_path=report_path,
            metadata={
                "extended_metrics": asdict(result.metrics),
                "subperiod_analysis": result.subperiod_analysis,
                "attribution": result.attribution,
                "summary": result.summary,
                "config": asdict(result.config),
                "backtest_config": result.metadata.get("backtest_config", {}),
            },
        )

        # Add to catalog and save
        self._catalog[evaluation_id] = entry.to_dict()
        self._save()

        logger.info(
            "Registered performance evaluation: %s (stability=%.3f, sharpe=%.2f)",
            evaluation_id,
            result.stability_score,
            sharpe_ratio,
        )

        return evaluation_id

    def get_evaluation(self, evaluation_id: str) -> PerformanceEntry:
        """
        Retrieve evaluation by ID.

        Parameters
        ----------
        evaluation_id : str
            Unique evaluation identifier.

        Returns
        -------
        PerformanceEntry
            Typed evaluation entry.

        Raises
        ------
        KeyError
            If evaluation ID not found.
        """
        if evaluation_id not in self._catalog:
            raise KeyError(f"Performance evaluation not found: {evaluation_id}")

        logger.debug("Retrieved performance evaluation: %s", evaluation_id)
        return PerformanceEntry.from_dict(self._catalog[evaluation_id])

    def get_evaluation_info(self, evaluation_id: str) -> dict[str, Any]:
        """
        Retrieve evaluation as dictionary.

        Parameters
        ----------
        evaluation_id : str
            Unique evaluation identifier.

        Returns
        -------
        dict[str, Any]
            Copy of evaluation data.

        Raises
        ------
        KeyError
            If evaluation ID not found.
        """
        if evaluation_id not in self._catalog:
            raise KeyError(f"Performance evaluation not found: {evaluation_id}")

        return self._catalog[evaluation_id].copy()

    def list_evaluations(
        self,
        signal_id: str | None = None,
        strategy_id: str | None = None,
    ) -> list[str]:
        """
        List evaluations with optional filters.

        Parameters
        ----------
        signal_id : str | None
            Filter by signal identifier.
        strategy_id : str | None
            Filter by strategy identifier.

        Returns
        -------
        list[str]
            Sorted list of evaluation IDs matching filters.

        Examples
        --------
        >>> registry.list_evaluations()  # All evaluations
        >>> registry.list_evaluations(signal_id="cdx_etf_basis")
        >>> registry.list_evaluations(strategy_id="simple_threshold")
        """
        results = []

        for eval_id, info in self._catalog.items():
            # Apply filters
            if signal_id and info.get("signal_id") != signal_id:
                continue
            if strategy_id and info.get("strategy_id") != strategy_id:
                continue

            results.append(eval_id)

        logger.debug(
            "Listed performance evaluations: %d total, %d matching filters",
            len(self._catalog),
            len(results),
        )

        return sorted(results)

    def remove_evaluation(self, evaluation_id: str) -> None:
        """
        Remove evaluation from registry.

        Parameters
        ----------
        evaluation_id : str
            Unique evaluation identifier.

        Raises
        ------
        KeyError
            If evaluation ID not found.

        Notes
        -----
        Does not delete associated report file.
        Automatically persists registry to disk.
        """
        if evaluation_id not in self._catalog:
            raise KeyError(f"Performance evaluation not found: {evaluation_id}")

        del self._catalog[evaluation_id]
        self._save()

        logger.info("Removed performance evaluation: %s", evaluation_id)

    def _save(self) -> None:
        """Persist registry to JSON."""
        # Ensure parent directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        save_json(self._catalog, self.registry_path)
        logger.debug("Saved performance registry to %s", self.registry_path)
