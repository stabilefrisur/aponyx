"""
Sweep result dataclasses and persistence utilities.

Provides containers for sweep execution results and functions
for saving/loading results to/from disk (Parquet + JSON).
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

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
            {"path": p.path, "values": list(p.values)}
            for p in result.config.parameters
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
        raise KeyError(
            f"Column '{sort_by}' not found. Available columns: {available}"
        )

    # Filter to successful results only
    if "status" in results_df.columns:
        success_df = results_df[results_df["status"] == "success"].copy()
    else:
        success_df = results_df.copy()

    sorted_df = success_df.sort_values(sort_by, ascending=ascending)
    return sorted_df.head(limit)
