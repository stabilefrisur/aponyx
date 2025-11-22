"""
Workflow step registry.

Central factory for creating workflow step instances.
Decouples engine from concrete step implementations.
"""

import logging
from typing import TYPE_CHECKING

from .config import WorkflowConfig
from .concrete_steps import (
    DataStep,
    SignalStep,
    SuitabilityStep,
    BacktestStep,
    PerformanceStep,
    VisualizationStep,
)

if TYPE_CHECKING:
    from .steps import WorkflowStep

logger = logging.getLogger(__name__)


class StepRegistry:
    """
    Factory for workflow step instances.

    Centralizes step creation and ensures consistent dependency order.

    Examples
    --------
    Get all steps for workflow:
        >>> registry = StepRegistry()
        >>> config = WorkflowConfig(signal_name="spread_momentum", strategy_name="balanced")
        >>> steps = registry.get_all_steps(config)

    Get specific step:
        >>> step = registry.get_step("data", config)
    """

    def __init__(self) -> None:
        self._step_order = [
            "data",
            "signal",
            "suitability",
            "backtest",
            "performance",
            "visualization",
        ]

    def get_canonical_order(self) -> list[str]:
        """
        Get canonical workflow step order.

        Returns
        -------
        list[str]
            Ordered list of step names.
        """
        return self._step_order.copy()

    def get_all_steps(self, config: WorkflowConfig) -> list["WorkflowStep"]:
        """
        Create all workflow steps in dependency order.

        Parameters
        ----------
        config : WorkflowConfig
            Workflow configuration.

        Returns
        -------
        list[WorkflowStep]
            Ordered list of step instances.
        """
        return [self._create_step(name, config) for name in self._step_order]

    def get_step(self, name: str, config: WorkflowConfig) -> "WorkflowStep":
        """
        Create single workflow step by name.

        Parameters
        ----------
        name : str
            Step name (data, signal, suitability, backtest, performance, visualization).
        config : WorkflowConfig
            Workflow configuration.

        Returns
        -------
        WorkflowStep
            Step instance.

        Raises
        ------
        ValueError
            If step name is invalid.
        """
        if name not in self._step_order:
            raise ValueError(f"Unknown step: {name}")
        return self._create_step(name, config)

    def _create_step(self, name: str, config: WorkflowConfig) -> "WorkflowStep":
        """Create step instance by name."""
        step_classes = {
            "data": DataStep,
            "signal": SignalStep,
            "suitability": SuitabilityStep,
            "backtest": BacktestStep,
            "performance": PerformanceStep,
            "visualization": VisualizationStep,
        }
        return step_classes[name](config)
