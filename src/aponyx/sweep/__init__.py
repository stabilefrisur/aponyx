"""
Parameter sweep engine for systematic sensitivity analysis.

This module provides tools for running parameter sweeps on indicator and backtest
configurations. Researchers can define sweep experiments in YAML configuration
files specifying parameter ranges, then execute evaluations to analyze parameter
sensitivity.

Core Components
---------------
- config: SweepConfig, ParameterOverride, BaseConfig dataclasses
- engine: run_sweep(), generate_combinations()
- evaluators: evaluate_indicator(), evaluate_backtest()
- results: SweepResult, SweepSummary, save/load functions, flattening utilities

Metrics are sourced from existing evaluation modules for consistency:
- Indicator sweeps: Use `aponyx.evaluation.suitability.SuitabilityResult`
- Backtest sweeps: Use `aponyx.evaluation.performance.PerformanceMetrics`

Example
-------
>>> from aponyx.sweep import load_sweep_config, run_sweep
>>> config = load_sweep_config("examples/sweep_lookback.yaml")
>>> result = run_sweep(config)
>>> print(result.results_df.sort_values("sharpe_ratio", ascending=False).head())
"""

from aponyx.evaluation.performance.config import PerformanceMetrics
from aponyx.evaluation.suitability.evaluator import SuitabilityResult

from .config import (
    BaseConfig,
    ParameterOverride,
    SweepConfig,
    load_sweep_config,
    validate_parameter_path,
)
from .engine import generate_combinations, run_sweep
from .evaluators import evaluate_backtest, evaluate_indicator
from .reports import generate_sweep_report, save_sweep_report
from .results import (
    SweepResult,
    SweepSummary,
    flatten_performance_metrics,
    flatten_suitability_result,
    get_top_results,
    load_sweep_results,
    save_sweep_results,
    summarize_sweep_results,
)

__all__ = [
    # Config
    "BaseConfig",
    "ParameterOverride",
    "SweepConfig",
    "load_sweep_config",
    "validate_parameter_path",
    # Engine
    "generate_combinations",
    "run_sweep",
    # Evaluators
    "evaluate_backtest",
    "evaluate_indicator",
    # Metrics (re-exported from evaluation modules)
    "PerformanceMetrics",
    "SuitabilityResult",
    # Reports
    "generate_sweep_report",
    "save_sweep_report",
    # Results
    "SweepResult",
    "SweepSummary",
    "flatten_performance_metrics",
    "flatten_suitability_result",
    "get_top_results",
    "load_sweep_results",
    "save_sweep_results",
    "summarize_sweep_results",
]
