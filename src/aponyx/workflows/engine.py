"""
Workflow orchestration engine.

Coordinates sequential execution of workflow steps with dependency tracking,
caching, error handling, and progress logging.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import WorkflowConfig
from .steps import WorkflowStep
from .registry import StepRegistry

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Workflow execution orchestrator.

    Manages sequential pipeline execution with:
    - Dependency resolution (data → signal → backtest → ...)
    - Smart caching (skip completed steps)
    - Error handling (save partial results)
    - Progress tracking (structured logging)

    Parameters
    ----------
    config : WorkflowConfig
        Workflow execution configuration.

    Examples
    --------
    Execute full workflow:
        >>> config = WorkflowConfig(
        ...     signal_name="spread_momentum",
        ...     strategy_name="balanced",
        ... )
        >>> engine = WorkflowEngine(config)
        >>> results = engine.execute()

    Execute specific steps:
        >>> config = WorkflowConfig(
        ...     signal_name="spread_momentum",
        ...     strategy_name="balanced",
        ...     steps=["data", "signal", "backtest"],
        ... )
        >>> engine = WorkflowEngine(config)
        >>> results = engine.execute()
    """

    def __init__(self, config: WorkflowConfig) -> None:
        self.config = config
        self._registry = StepRegistry()
        self._steps = self._resolve_steps()
        self._context: dict[str, Any] = {}
        self._start_time: datetime | None = None

    def execute(self) -> dict[str, Any]:
        """
        Execute workflow pipeline.

        Returns
        -------
        dict[str, Any]
            Workflow results with keys:
            - steps_completed: int (number of steps executed)
            - steps_skipped: int (number cached steps skipped)
            - output_dir: Path (workflow output directory)
            - duration_seconds: float (total execution time)
            - errors: list[dict] (errors if any step failed)

        Notes
        -----
        Steps execute in dependency order. If step N fails, steps N+1...
        are skipped but results from steps 1...N-1 are preserved.
        """
        self._start_time = datetime.now()

        logger.info(
            "Starting workflow: signal=%s, strategy=%s, source=%s, steps=%d",
            self.config.signal_name,
            self.config.strategy_name,
            self.config.data_source,
            len(self._steps),
        )

        # Create workflow output directory upfront
        output_dir = self._create_output_directory()

        # Add output_dir to context for steps to use
        self._context["output_dir"] = output_dir

        completed = 0
        skipped = 0
        errors = []

        for idx, step in enumerate(self._steps, start=1):
            step_num = f"{idx}/{len(self._steps)}"

            # Check cache
            if self._should_skip_step(step):
                logger.info("Step %s: %s (cached)", step_num, step.name)
                # Load cached output into context for downstream steps
                try:
                    cached_output = step.load_cached_output()
                    self._context[step.name] = cached_output
                except Exception as e:
                    logger.warning(
                        "Failed to load cached output for %s: %s. Re-running step.",
                        step.name,
                        str(e),
                    )
                    # Fall through to execute step instead
                else:
                    skipped += 1
                    continue

            # Execute step
            try:
                logger.info("Step %s: %s", step_num, step.name)
                output = step.execute(self._context)
                self._context[step.name] = output
                completed += 1
                logger.info("Step %s: %s complete", step_num, step.name)

            except Exception as e:
                logger.error("Step %s: %s failed - %s", step_num, step.name, str(e))
                errors.append(
                    {
                        "step": step.name,
                        "error": str(e),
                        "type": type(e).__name__,
                    }
                )
                break  # Stop execution on first error

        duration = (datetime.now() - self._start_time).total_seconds()

        result = {
            "steps_completed": completed,
            "steps_skipped": skipped,
            "output_dir": output_dir,
            "duration_seconds": duration,
            "errors": errors,
        }

        # Save workflow metadata
        self._save_metadata(output_dir, completed, skipped, errors, duration)

        if errors:
            logger.error(
                "Workflow failed: completed=%d, skipped=%d, failed=%d (%.1fs)",
                completed,
                skipped,
                len(errors),
                duration,
            )
        else:
            logger.info(
                "Workflow complete: completed=%d, skipped=%d (%.1fs)",
                completed,
                skipped,
                duration,
            )

        return result

    def _resolve_steps(self) -> list[WorkflowStep]:
        """
        Resolve workflow steps from configuration.

        Returns
        -------
        list[WorkflowStep]
            Ordered list of step instances to execute.

        Notes
        -----
        If config.steps is None, returns all steps in dependency order.
        If config.steps is specified, returns subset in correct order.
        """
        all_steps = self._registry.get_all_steps(self.config)

        if self.config.steps is None:
            return all_steps

        # Filter to requested steps (maintain order)
        requested = set(self.config.steps)
        return [s for s in all_steps if s.name in requested]

    def _should_skip_step(self, step: WorkflowStep) -> bool:
        """
        Determine if step should be skipped (cached).

        Parameters
        ----------
        step : WorkflowStep
            Step to check.

        Returns
        -------
        bool
            True if step output exists and force_rerun is False.
        """
        if self.config.force_rerun:
            return False
        return step.output_exists()

    def _create_output_directory(self) -> Path:
        """
        Create timestamped output directory for workflow.

        Returns
        -------
        Path
            Created output directory path.

        Notes
        -----
        Format: workflows/{label}_{timestamp}/
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dirname = f"{self.config.label}_{timestamp}"
        output_dir = self.config.output_dir / dirname
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _save_metadata(
        self,
        output_dir: Path,
        completed: int,
        skipped: int,
        errors: list[dict[str, Any]],
        duration: float,
    ) -> None:
        """
        Save workflow metadata to metadata.json.

        Parameters
        ----------
        output_dir : Path
            Workflow output directory.
        completed : int
            Number of completed steps.
        skipped : int
            Number of skipped steps.
        errors : list of dict
            Error details if any.
        duration : float
            Execution duration in seconds.
        """
        from ..persistence import save_json

        # Extract securities_used from signal step if available
        securities_used = self._context.get("signal", {}).get("securities_used", {})

        metadata = {
            "label": self.config.label,
            "signal": self.config.signal_name,
            "strategy": self.config.strategy_name,
            "product": self.config.product,
            "data_source": self.config.data_source,
            "securities_used": securities_used,
            "indicator_transformation_override": self.config.indicator_transformation_override,
            "score_transformation_override": self.config.score_transformation_override,
            "signal_transformation_override": self.config.signal_transformation_override,
            "timestamp": self._start_time.isoformat() if self._start_time else None,
            "duration_seconds": duration,
            "steps_completed": completed,
            "steps_skipped": skipped,
            "steps_total": len(self._steps),
            "status": "failed" if errors else "completed",
            "errors": errors if errors else None,
        }

        metadata_path = output_dir / "metadata.json"
        save_json(metadata, metadata_path)
        logger.debug("Saved workflow metadata: %s", metadata_path)
