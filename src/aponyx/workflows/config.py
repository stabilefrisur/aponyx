"""
Workflow configuration management.

Defines immutable configuration for workflow execution including
signal/strategy selection, data sources, and execution options.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from aponyx.config import PROCESSED_DIR

StepName = Literal[
    "data",
    "signal",
    "suitability",
    "backtest",
    "performance",
    "visualization",
]

DataSource = Literal["synthetic", "file", "bloomberg"]


@dataclass(frozen=True)
class WorkflowConfig:
    """
    Immutable workflow execution configuration.
    
    Attributes
    ----------
    signal_name : str
        Signal name from signal catalog.
    strategy_name : str
        Strategy name from strategy catalog.
    product : str
        Product identifier for backtesting (e.g., "cdx_ig_5y", "cdx_hy_5y").
    data_source : DataSource
        Data source type (synthetic, file, bloomberg).
    steps : list[StepName] | None
        Specific steps to execute (None = all steps in order).
    force_rerun : bool
        Force re-execution even if cached outputs exist.
    output_dir : Path
        Base directory for workflow outputs.
        
    Notes
    -----
    Configuration is frozen to prevent accidental mutation during execution.
    Use dataclasses.replace() to create modified copies if needed.
    """
    signal_name: str
    strategy_name: str
    product: str
    data_source: DataSource = "synthetic"
    steps: list[StepName] | None = None
    force_rerun: bool = False
    output_dir: Path = field(default_factory=lambda: PROCESSED_DIR / "workflows")
    
    def __post_init__(self) -> None:
        """Validate configuration on initialization."""
        if self.steps is not None:
            valid_steps = {
                "data", "signal", "suitability",
                "backtest", "performance", "visualization",
            }
            invalid = set(self.steps) - valid_steps
            if invalid:
                raise ValueError(f"Invalid steps: {invalid}")
