"""
Sweep execution engine for parameter sensitivity analysis.

Provides the main orchestration logic for running parameter sweeps,
including combination generation and execution with progress tracking.
"""

import logging
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from .config import ParameterOverride, SweepConfig
from .results import SweepResult, SweepSummary, save_sweep_results

logger = logging.getLogger(__name__)


def generate_combinations(
    parameters: tuple[ParameterOverride, ...],
    max_combinations: int | None = None,
) -> list[dict[str, Any]]:
    """
    Generate all parameter combinations using Cartesian product.

    Parameters
    ----------
    parameters : tuple[ParameterOverride, ...]
        Parameter overrides to combine.
    max_combinations : int | None
        Maximum combinations to generate. None = unlimited.

    Returns
    -------
    list[dict[str, Any]]
        List of parameter combination dictionaries.
        Each dict maps parameter path to value.

    Examples
    --------
    >>> params = (
    ...     ParameterOverride(path="a.b", values=(1, 2)),
    ...     ParameterOverride(path="c.d", values=("x", "y")),
    ... )
    >>> combos = generate_combinations(params)
    >>> len(combos)
    4
    >>> combos[0]
    {'a.b': 1, 'c.d': 'x'}
    """
    param_paths = [p.path for p in parameters]
    param_values = [p.values for p in parameters]

    combinations: list[dict[str, Any]] = []
    for combo in product(*param_values):
        combinations.append(dict(zip(param_paths, combo)))
        if max_combinations is not None and len(combinations) >= max_combinations:
            logger.info(
                "Reached max_combinations limit: %d (total possible: %d)",
                max_combinations,
                _calculate_total_combinations(parameters),
            )
            break

    logger.debug("Generated %d parameter combinations", len(combinations))
    return combinations


def _calculate_total_combinations(
    parameters: tuple[ParameterOverride, ...],
) -> int:
    """Calculate total possible combinations without max limit."""
    total = 1
    for p in parameters:
        total *= len(p.values)
    return total


def run_sweep(
    config: SweepConfig,
    *,
    dry_run: bool = False,
    output_dir: Path | None = None,
) -> SweepResult:
    """
    Execute a parameter sweep based on configuration.

    Main orchestrator that:
    1. Generates all parameter combinations
    2. Evaluates each combination (indicator or backtest mode)
    3. Collects metrics into results DataFrame
    4. Saves results to disk

    Parameters
    ----------
    config : SweepConfig
        Sweep configuration specifying parameters and mode.
    dry_run : bool
        If True, generate combinations but skip evaluation.
        Useful for previewing sweep scope.
    output_dir : Path | None
        Custom output directory. Uses default SWEEPS_DIR if None.

    Returns
    -------
    SweepResult
        Complete sweep results including DataFrame and metadata.

    Raises
    ------
    ValueError
        If signal or strategy not found in catalogs.
    KeyboardInterrupt
        Saves partial results before re-raising.

    Examples
    --------
    >>> config = load_sweep_config("examples/sweep_lookback.yaml")
    >>> result = run_sweep(config)
    >>> print(f"Tested {len(result.results_df)} combinations")

    >>> # Dry run to preview
    >>> result = run_sweep(config, dry_run=True)
    >>> print(f"Would test {len(result.results_df)} combinations")
    """
    from .evaluators import evaluate_backtest, evaluate_indicator

    start_time = datetime.now()
    logger.info(
        "Starting sweep: name=%s, mode=%s, dry_run=%s",
        config.name,
        config.mode,
        dry_run,
    )

    # Generate combinations
    combinations = generate_combinations(
        config.parameters,
        config.max_combinations,
    )
    total_combinations = len(combinations)

    logger.info(
        "Generated %d combinations (max_combinations=%s)",
        total_combinations,
        config.max_combinations,
    )

    # Prepare results storage
    results: list[dict[str, Any]] = []
    successful = 0
    failed = 0

    # Dry run: return empty results with combination info
    if dry_run:
        for i, combo in enumerate(combinations):
            row: dict[str, Any] = {
                "combination_id": i,
                **combo,
                "status": "dry_run",
                "error": None,
            }
            results.append(row)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        summary = SweepSummary(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            total_combinations=total_combinations,
            successful=0,
            failed=0,
            mode=config.mode,
        )

        results_df = pd.DataFrame(results)

        # For dry run, don't save to disk
        from aponyx.config import SWEEPS_DIR

        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = SWEEPS_DIR / f"{config.name}_{timestamp}"

        result = SweepResult(
            config=config,
            results_df=results_df,
            summary=summary,
            output_dir=output_dir,
        )

        logger.info("Dry run complete: %d combinations previewed", total_combinations)
        return result

    # Execute evaluations with progress bar
    try:
        with tqdm(
            combinations,
            desc=f"Sweep: {config.name}",
            unit="combo",
        ) as pbar:
            for i, combo in enumerate(pbar):
                row = {
                    "combination_id": i,
                    **combo,
                }

                try:
                    if config.mode == "indicator":
                        indicator_metrics = evaluate_indicator(config, combo)
                        row.update(indicator_metrics.to_dict())
                    else:  # backtest mode
                        backtest_metrics = evaluate_backtest(config, combo)
                        row.update(backtest_metrics.to_dict())
                    row["status"] = "success"
                    row["error"] = None
                    successful += 1

                except Exception as e:
                    logger.warning(
                        "Evaluation failed for combination %d: %s", i, str(e)
                    )
                    row["status"] = "failed"
                    row["error"] = str(e)
                    failed += 1

                results.append(row)

                # Update progress bar postfix
                pbar.set_postfix(
                    success=successful, failed=failed, refresh=False
                )

    except KeyboardInterrupt:
        logger.warning(
            "Sweep interrupted by user. Saving %d partial results...",
            len(results),
        )
        # Fall through to save partial results

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    summary = SweepSummary(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        duration_seconds=duration,
        total_combinations=total_combinations,
        successful=successful,
        failed=failed,
        mode=config.mode,
    )

    results_df = pd.DataFrame(results)

    # Create result object
    from aponyx.config import SWEEPS_DIR

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = SWEEPS_DIR / f"{config.name}_{timestamp}"

    result = SweepResult(
        config=config,
        results_df=results_df,
        summary=summary,
        output_dir=output_dir,
    )

    # Save results
    saved_dir = save_sweep_results(result, output_dir)
    result = SweepResult(
        config=config,
        results_df=results_df,
        summary=summary,
        output_dir=saved_dir,
    )

    logger.info(
        "Sweep complete: %d/%d successful in %.1fs. Results: %s",
        successful,
        total_combinations,
        duration,
        saved_dir,
    )

    return result
