"""
Registry for tracking suitability evaluations.

Provides CRUD operations for evaluation metadata with JSON persistence.
Follows the DataRegistry pattern for mutable state management.
"""

import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aponyx.persistence import load_json, save_json
from aponyx.evaluation.suitability.evaluator import SuitabilityResult

logger = logging.getLogger(__name__)


@dataclass
class EvaluationEntry:
    """
    Metadata record for a suitability evaluation.

    Attributes
    ----------
    signal_id : str
        Signal name/identifier (from signal.name).
    product_id : str
        Product identifier (user-provided).
    evaluated_at : str
        ISO timestamp of evaluation.
    decision : str
        Evaluation decision: "PASS", "HOLD", or "FAIL".
    composite_score : float
        Final composite score (0-1).
    evaluator_version : str
        Version of evaluator used.
    report_path : str or None
        Path to generated report file, if saved.
    metadata : dict[str, Any]
        Additional metadata (config, component scores, etc.).
    """

    signal_id: str
    product_id: str
    evaluated_at: str
    decision: str
    composite_score: float
    evaluator_version: str
    report_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationEntry":
        """Create entry from dictionary."""
        return cls(**data)


class SuitabilityRegistry:
    """
    Registry for tracking suitability evaluations.

    Implements CRUD operations (create, read, update, delete) with
    JSON persistence. Follows the DataRegistry pattern for mutable
    state management.

    Parameters
    ----------
    registry_path : str or Path
        Path to JSON registry file.

    Examples
    --------
    >>> from aponyx.config import SUITABILITY_REGISTRY_PATH
    >>> registry = SuitabilityRegistry(SUITABILITY_REGISTRY_PATH)
    >>> eval_id = registry.register_evaluation(result, "cdx_etf_basis", "CDX_IG_5Y")
    >>> entry = registry.get_evaluation(eval_id)
    >>> evaluations = registry.list_evaluations(decision="PASS")
    """

    def __init__(self, registry_path: str | Path):
        """
        Initialize registry with JSON persistence.

        Parameters
        ----------
        registry_path : str or Path
            Path to registry JSON file.
        """
        self.registry_path = Path(registry_path)
        self._catalog: dict[str, dict] = {}

        # Load existing registry or create new
        if self.registry_path.exists():
            try:
                self._catalog = load_json(self.registry_path)
                logger.info(
                    "Loaded existing registry: %d evaluations",
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
            logger.info("Creating new registry at %s", self.registry_path)
            self._save()

    def register_evaluation(
        self,
        result: SuitabilityResult,
        signal_id: str,
        product_id: str,
        report_path: str | None = None,
        evaluator_version: str = "0.1.0",
    ) -> str:
        """
        Register new evaluation result.

        Parameters
        ----------
        result : SuitabilityResult
            Evaluation result to register.
        signal_id : str
            Signal identifier (typically signal.name).
        product_id : str
            Product identifier (user-provided).
        report_path : str, optional
            Path to saved report file.
        evaluator_version : str, default="0.1.0"
            Version of evaluator used.

        Returns
        -------
        str
            Unique evaluation ID for retrieval.

        Notes
        -----
        Evaluation ID format: {signal_id}_{product_id}_{timestamp}
        Automatically persists registry to disk.
        """
        # Generate unique evaluation ID
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        evaluation_id = f"{signal_id}_{product_id}_{timestamp_str}"

        logger.debug("Registering evaluation: %s", evaluation_id)

        # Create entry
        entry = EvaluationEntry(
            signal_id=signal_id,
            product_id=product_id,
            evaluated_at=result.timestamp,
            decision=result.decision,
            composite_score=result.composite_score,
            evaluator_version=evaluator_version,
            report_path=report_path,
            metadata={
                "component_scores": {
                    "data_health": result.data_health_score,
                    "predictive": result.predictive_score,
                    "economic": result.economic_score,
                    "stability": result.stability_score,
                },
                "metrics": {
                    "valid_obs": result.valid_obs,
                    "missing_pct": result.missing_pct,
                    "effect_size_bps": result.effect_size_bps,
                },
                "config": asdict(result.config),
            },
        )

        # Add to catalog and save
        self._catalog[evaluation_id] = entry.to_dict()
        self._save()

        logger.info(
            "Registered evaluation: %s (decision=%s, score=%.3f)",
            evaluation_id,
            result.decision,
            result.composite_score,
        )

        return evaluation_id

    def get_evaluation(self, evaluation_id: str) -> EvaluationEntry:
        """
        Retrieve evaluation by ID.

        Parameters
        ----------
        evaluation_id : str
            Unique evaluation identifier.

        Returns
        -------
        EvaluationEntry
            Typed evaluation entry.

        Raises
        ------
        KeyError
            If evaluation ID not found.
        """
        if evaluation_id not in self._catalog:
            raise KeyError(f"Evaluation not found: {evaluation_id}")

        logger.debug("Retrieved evaluation: %s", evaluation_id)
        return EvaluationEntry.from_dict(self._catalog[evaluation_id])

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
            raise KeyError(f"Evaluation not found: {evaluation_id}")

        return self._catalog[evaluation_id].copy()

    def list_evaluations(
        self,
        signal_id: str | None = None,
        product_id: str | None = None,
        decision: str | None = None,
    ) -> list[str]:
        """
        List evaluations with optional filters.

        Parameters
        ----------
        signal_id : str, optional
            Filter by signal identifier.
        product_id : str, optional
            Filter by product identifier.
        decision : str, optional
            Filter by decision ("PASS", "HOLD", "FAIL").

        Returns
        -------
        list[str]
            Sorted list of evaluation IDs matching filters.

        Examples
        --------
        >>> registry.list_evaluations()  # All evaluations
        >>> registry.list_evaluations(decision="PASS")  # Only PASS
        >>> registry.list_evaluations(signal_id="cdx_etf_basis")
        """
        results = []

        for eval_id, info in self._catalog.items():
            # Apply filters
            if signal_id and info.get("signal_id") != signal_id:
                continue
            if product_id and info.get("product_id") != product_id:
                continue
            if decision and info.get("decision") != decision:
                continue

            results.append(eval_id)

        logger.debug(
            "Listed evaluations: %d total, %d matching filters",
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
            raise KeyError(f"Evaluation not found: {evaluation_id}")

        del self._catalog[evaluation_id]
        self._save()

        logger.info("Removed evaluation: %s", evaluation_id)

    def _save(self) -> None:
        """Persist registry to JSON."""
        # Ensure parent directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        save_json(self._catalog, self.registry_path)
        logger.debug("Saved registry to %s", self.registry_path)
