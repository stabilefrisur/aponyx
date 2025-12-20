"""
Sweep result dataclasses and persistence utilities.

Provides containers for sweep execution results and functions
for saving/loading results to/from disk (Parquet + JSON).
Includes utilities for flattening nested evaluation results into
DataFrame columns suitable for parameter sensitivity analysis.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from aponyx.evaluation.performance.config import PerformanceMetrics
from aponyx.evaluation.suitability.evaluator import SuitabilityResult

if TYPE_CHECKING:
    from .config import SweepConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SweepSummary:
    """
    Execution metadata for a sweep.

    Attributes
    ----------
    start_time : str
        ISO 8601 timestamp when sweep started.
    end_time : str
        ISO 8601 timestamp when sweep ended.
    duration_seconds : float
        Total execution time in seconds.
    total_combinations : int
        Total number of parameter combinations tested.
    successful : int
        Number of successfully evaluated combinations.
    failed : int
        Number of failed evaluations.
    mode : str
        Sweep mode ("indicator" or "backtest").

    Examples
    --------
    >>> summary = SweepSummary(
    ...     start_time="2025-12-20T10:30:00",
    ...     end_time="2025-12-20T10:35:00",
    ...     duration_seconds=300.5,
    ...     total_combinations=12,
    ...     successful=11,
    ...     failed=1,
    ...     mode="indicator",
    ... )
    >>> print(f"Success rate: {summary.success_rate:.1%}")
    """

    start_time: str
    end_time: str
    duration_seconds: float
    total_combinations: int
    successful: int
    failed: int
    mode: str

    @property
    def success_rate(self) -> float:
        """Calculate success rate as proportion of successful combinations."""
        if self.total_combinations == 0:
            return 0.0
        return self.successful / self.total_combinations

    def to_dict(self) -> dict[str, str | float | int]:
        """Convert to dictionary for JSON serialization."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "total_combinations": self.total_combinations,
            "successful": self.successful,
            "failed": self.failed,
            "mode": self.mode,
            "success_rate": self.success_rate,
        }


@dataclass
class SweepResult:
    """
    Complete sweep results container.

    Attributes
    ----------
    config : SweepConfig
        Original sweep configuration.
    results_df : pd.DataFrame
        Parameter combinations and metrics DataFrame.
    summary : SweepSummary
        Execution metadata.
    output_dir : Path
        Directory where results were saved.

    Notes
    -----
    Not frozen because pd.DataFrame is mutable.

    Examples
    --------
    >>> print(f"Saved to: {result.output_dir}")
    >>> print(result.results_df.sort_values("sharpe_ratio", ascending=False).head())
    """

    config: "SweepConfig"
    results_df: pd.DataFrame
    summary: SweepSummary
    output_dir: Path


def save_sweep_results(
    result: SweepResult,
    output_dir: Path | None = None,
) -> Path:
    """
    Save sweep results to disk.

    Creates a timestamped directory containing:
    - results.parquet: Parameter combinations and metrics
    - config.json: Copy of sweep configuration
    - summary.json: Execution metadata

    Parameters
    ----------
    result : SweepResult
        Sweep results to save.
    output_dir : Path | None
        Custom output directory. If None, uses default SWEEPS_DIR.

    Returns
    -------
    Path
        Path to the created output directory.

    Examples
    --------
    >>> output_path = save_sweep_results(result)
    >>> print(f"Results saved to: {output_path}")
    """
    from aponyx.config import SWEEPS_DIR

    if output_dir is None:
        # Create timestamped directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = SWEEPS_DIR / f"{result.config.name}_{timestamp}"

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Saving sweep results to: %s", output_dir)

    # Save results DataFrame as Parquet
    results_path = output_dir / "results.parquet"
    result.results_df.to_parquet(results_path, index=False)
    logger.debug("Saved results.parquet: %d rows", len(result.results_df))

    # Save config as JSON
    config_path = output_dir / "config.json"
    config_dict = {
        "name": result.config.name,
        "description": result.config.description,
        "mode": result.config.mode,
        "base": {
            "signal": result.config.base.signal,
            "strategy": result.config.base.strategy,
        },
        "parameters": [
            {"path": p.path, "values": list(p.values)} for p in result.config.parameters
        ],
        "max_combinations": result.config.max_combinations,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=2)
    logger.debug("Saved config.json")

    # Save summary as JSON
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(result.summary.to_dict(), f, indent=2)
    logger.debug("Saved summary.json")

    # Generate and save analysis report
    from .reports import save_sweep_report

    save_sweep_report(result, output_dir)

    return output_dir


def load_sweep_results(sweep_dir: str | Path) -> SweepResult:
    """
    Load sweep results from disk.

    Parameters
    ----------
    sweep_dir : str | Path
        Path to sweep output directory containing results.parquet,
        config.json, and summary.json.

    Returns
    -------
    SweepResult
        Loaded sweep results.

    Raises
    ------
    FileNotFoundError
        If required files are missing.

    Examples
    --------
    >>> result = load_sweep_results("data/sweeps/lookback_sweep_20251220_103000")
    >>> print(result.results_df.head())
    """
    from .config import BaseConfig, ParameterOverride, SweepConfig

    sweep_dir = Path(sweep_dir)

    if not sweep_dir.exists():
        raise FileNotFoundError(f"Sweep directory not found: {sweep_dir}")

    logger.info("Loading sweep results from: %s", sweep_dir)

    # Load results DataFrame
    results_path = sweep_dir / "results.parquet"
    if not results_path.exists():
        raise FileNotFoundError(f"results.parquet not found in: {sweep_dir}")
    results_df = pd.read_parquet(results_path)
    logger.debug("Loaded results.parquet: %d rows", len(results_df))

    # Load config
    config_path = sweep_dir / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"config.json not found in: {sweep_dir}")
    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = json.load(f)

    base = BaseConfig(
        signal=config_dict["base"]["signal"],
        strategy=config_dict["base"].get("strategy"),
    )
    parameters = tuple(
        ParameterOverride(path=p["path"], values=tuple(p["values"]))
        for p in config_dict["parameters"]
    )
    config = SweepConfig(
        name=config_dict["name"],
        description=config_dict["description"],
        mode=config_dict["mode"],
        base=base,
        parameters=parameters,
        max_combinations=config_dict.get("max_combinations"),
    )

    # Load summary
    summary_path = sweep_dir / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"summary.json not found in: {sweep_dir}")
    with open(summary_path, "r", encoding="utf-8") as f:
        summary_dict = json.load(f)

    summary = SweepSummary(
        start_time=summary_dict["start_time"],
        end_time=summary_dict["end_time"],
        duration_seconds=summary_dict["duration_seconds"],
        total_combinations=summary_dict["total_combinations"],
        successful=summary_dict["successful"],
        failed=summary_dict["failed"],
        mode=summary_dict["mode"],
    )

    return SweepResult(
        config=config,
        results_df=results_df,
        summary=summary,
        output_dir=sweep_dir,
    )


def get_top_results(
    results_df: pd.DataFrame,
    sort_by: str = "sharpe_ratio",
    limit: int = 10,
    ascending: bool = False,
) -> pd.DataFrame:
    """
    Get top performing parameter combinations sorted by metric.

    Parameters
    ----------
    results_df : pd.DataFrame
        Sweep results DataFrame.
    sort_by : str
        Column name to sort by. Default: "sharpe_ratio".
    limit : int
        Maximum number of results to return. Default: 10.
    ascending : bool
        Sort ascending if True, descending if False. Default: False.

    Returns
    -------
    pd.DataFrame
        Top results sorted by specified metric.

    Raises
    ------
    KeyError
        If sort_by column doesn't exist.

    Examples
    --------
    >>> top = get_top_results(result.results_df, sort_by="sharpe_ratio", limit=5)
    >>> print(top)
    """
    if sort_by not in results_df.columns:
        available = ", ".join(sorted(results_df.columns))
        raise KeyError(f"Column '{sort_by}' not found. Available columns: {available}")

    # Filter to successful results only
    if "status" in results_df.columns:
        success_df = results_df[results_df["status"] == "success"].copy()
    else:
        success_df = results_df.copy()

    sorted_df = success_df.sort_values(sort_by, ascending=ascending)
    return sorted_df.head(limit)


def flatten_suitability_result(
    result: SuitabilityResult,
) -> dict[str, float | int | str]:
    """
    Flatten a SuitabilityResult into a dict suitable for DataFrame columns.

    Converts nested dict fields (correlations, betas, t_stats) into separate
    columns with lag-based suffixes (e.g., correlation_lag_1, beta_lag_5).

    Parameters
    ----------
    result : SuitabilityResult
        Suitability evaluation result to flatten.

    Returns
    -------
    dict[str, float | int | str]
        Flattened key-value pairs for DataFrame row construction.

    Examples
    --------
    >>> flat = flatten_suitability_result(suitability_result)
    >>> df = pd.DataFrame([flat])
    >>> print(df.columns.tolist())
    ['decision', 'composite_score', 'correlation_lag_1', ...]
    """
    flat: dict[str, Any] = {
        "decision": result.decision,
        "composite_score": result.composite_score,
        "data_health_score": result.data_health_score,
        "predictive_score": result.predictive_score,
        "economic_score": result.economic_score,
        "stability_score": result.stability_score,
        "valid_obs": result.valid_obs,
        "missing_pct": result.missing_pct,
        "effect_size_bps": result.effect_size_bps,
        "sign_consistency_ratio": result.sign_consistency_ratio,
        "beta_cv": result.beta_cv,
        "n_windows": result.n_windows,
    }

    # Flatten lag-indexed dicts
    for lag, corr in result.correlations.items():
        flat[f"correlation_lag_{lag}"] = corr
    for lag, beta in result.betas.items():
        flat[f"beta_lag_{lag}"] = beta
    for lag, tstat in result.t_stats.items():
        flat[f"tstat_lag_{lag}"] = tstat

    return flat


def flatten_performance_metrics(metrics: PerformanceMetrics) -> dict[str, float | int]:
    """
    Flatten a PerformanceMetrics dataclass into a dict for DataFrame columns.

    Parameters
    ----------
    metrics : PerformanceMetrics
        Performance metrics from backtest evaluation.

    Returns
    -------
    dict[str, float | int]
        All metrics as key-value pairs (already flat structure).

    Examples
    --------
    >>> flat = flatten_performance_metrics(perf_metrics)
    >>> df = pd.DataFrame([flat])
    >>> print(f"Sharpe: {df['sharpe_ratio'].iloc[0]:.2f}")
    """
    return asdict(metrics)


def summarize_sweep_results(
    results_df: pd.DataFrame,
    metric_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Compute summary statistics across all sweep runs.

    Calculates mean, std, min, max, and best values for each metric column,
    providing a compact overview of parameter sensitivity.

    Parameters
    ----------
    results_df : pd.DataFrame
        Sweep results DataFrame with metric columns.
    metric_columns : list[str] | None
        Columns to summarize. If None, auto-detects numeric columns
        excluding parameter and metadata columns.

    Returns
    -------
    pd.DataFrame
        Summary statistics with metrics as rows and stats as columns.
        Columns: mean, std, min, max, count.

    Examples
    --------
    >>> summary = summarize_sweep_results(result.results_df)
    >>> print(summary.loc['sharpe_ratio'])
    mean     1.45
    std      0.23
    min      0.95
    max      1.98
    count   12.00
    Name: sharpe_ratio, dtype: float64
    """
    # Filter to successful results
    if "status" in results_df.columns:
        df = results_df[results_df["status"] == "success"].copy()
    else:
        df = results_df.copy()

    # Auto-detect metric columns if not specified
    if metric_columns is None:
        # Exclude known non-metric columns
        exclude_cols = {
            "combination_id",
            "status",
            "error",
            "timestamp",
            "decision",  # categorical
        }
        # Also exclude parameter columns (contain dots or known prefixes)
        metric_columns = [
            col
            for col in df.columns
            if col not in exclude_cols
            and df[col].dtype in [np.float64, np.int64, float, int]
            and "." not in col  # parameter paths contain dots
        ]

    if not metric_columns:
        logger.warning("No numeric metric columns found for summarization")
        return pd.DataFrame()

    # Compute statistics
    stats = df[metric_columns].agg(["mean", "std", "min", "max", "count"]).T
    stats.columns = ["mean", "std", "min", "max", "count"]

    logger.debug(
        "Summarized %d metrics across %d successful runs",
        len(metric_columns),
        len(df),
    )

    return stats
