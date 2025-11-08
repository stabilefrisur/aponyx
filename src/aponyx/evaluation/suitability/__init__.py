"""
Signal-product suitability evaluation module.

This module provides tools to evaluate whether signals contain economically
and statistically meaningful information for traded products. Acts as a
research screening gate before proceeding to strategy design and backtesting.

Public API
----------
- evaluate_signal_suitability: Main evaluation function
- SuitabilityConfig: Configuration dataclass
- SuitabilityResult: Result dataclass
- SuitabilityRegistry: Evaluation tracking with CRUD operations
- EvaluationEntry: Registry entry dataclass
- generate_suitability_report: Markdown report generator
- save_report: Report file persistence
- compute_forward_returns: Target construction utility

Examples
--------
>>> from aponyx.evaluation.suitability import (
...     evaluate_signal_suitability,
...     SuitabilityConfig,
...     generate_suitability_report,
...     save_report,
...     SuitabilityRegistry,
... )
>>> from aponyx.config import EVALUATION_DIR, SUITABILITY_REGISTRY_PATH
>>>
>>> # Evaluate signal
>>> result = evaluate_signal_suitability(signal, target_change)
>>> print(result.decision, result.composite_score)
>>>
>>> # Generate report
>>> report = generate_suitability_report(result, "cdx_etf_basis", "cdx_ig_5y")
>>> report_path = save_report(report, "cdx_etf_basis", "cdx_ig_5y", EVALUATION_DIR)
>>>
>>> # Register evaluation
>>> registry = SuitabilityRegistry(SUITABILITY_REGISTRY_PATH)
>>> eval_id = registry.register_evaluation(result, "cdx_etf_basis", "cdx_ig_5y")
"""

from aponyx.evaluation.suitability.config import SuitabilityConfig
from aponyx.evaluation.suitability.evaluator import (
    SuitabilityResult,
    evaluate_signal_suitability,
    compute_forward_returns,
)
from aponyx.evaluation.suitability.registry import (
    SuitabilityRegistry,
    EvaluationEntry,
)
from aponyx.evaluation.suitability.report import (
    generate_suitability_report,
    save_report,
)

__all__ = [
    "SuitabilityConfig",
    "SuitabilityResult",
    "evaluate_signal_suitability",
    "compute_forward_returns",
    "SuitabilityRegistry",
    "EvaluationEntry",
    "generate_suitability_report",
    "save_report",
]
