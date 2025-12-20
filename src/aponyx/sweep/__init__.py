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
- metrics: IndicatorMetrics, BacktestMetrics, compute_indicator_statistics()
- results: SweepResult, SweepSummary, save/load functions

Example
-------
>>> from aponyx.sweep import load_sweep_config, run_sweep
>>> config = load_sweep_config("examples/sweep_lookback.yaml")
>>> result = run_sweep(config)
>>> print(result.results_df.sort_values("sharpe_ratio", ascending=False).head())
"""

from .config import (
    BaseConfig,
    ParameterOverride,
    SweepConfig,
    load_sweep_config,
    validate_parameter_path,
)
from .engine import generate_combinations, run_sweep
from .evaluators import evaluate_backtest, evaluate_indicator
from .metrics import BacktestMetrics, IndicatorMetrics, compute_indicator_statistics
from .results import (
    SweepResult,
    SweepSummary,
    get_top_results,
    load_sweep_results,
    save_sweep_results,
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
    # Metrics
    "BacktestMetrics",
    "IndicatorMetrics",
    "compute_indicator_statistics",
    # Results
    "SweepResult",
    "SweepSummary",
    "get_top_results",
    "load_sweep_results",
    "save_sweep_results",
]
