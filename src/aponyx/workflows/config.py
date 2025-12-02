"""
Workflow configuration management.

Defines immutable configuration for workflow execution including
signal/strategy selection, data sources, and execution options.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from aponyx.config import DATA_WORKFLOWS_DIR

StepName = Literal[
    "data",
    "signal",
    "suitability",
    "backtest",
    "performance",
    "visualization",
]

# DataSource now accepts any string to support dynamic source discovery
DataSource = str


@dataclass(frozen=True)
class WorkflowConfig:
    """
    Immutable workflow execution configuration.

    Attributes
    ----------
    label : str
        Workflow label (lowercase, underscores only, pattern: ^[a-z][a-z0-9_]*$).
        Used for workflow identification and directory naming.
    signal_name : str
        Signal name from signal catalog.
    strategy_name : str
        Strategy name from strategy catalog.
    product : str
        Product identifier for backtesting (e.g., "cdx_ig_5y", "cdx_hy_5y").
    data_source : str
        Data source type (e.g., "synthetic", "file", "bloomberg", or custom sources).
    security_mapping : dict[str, str] | None
        Maps generic instrument types to specific securities.
        Example: {"cdx": "cdx_ig_5y", "etf": "hyg", "vix": "vix"}
        If None, uses defaults from indicator catalog.
    indicator_override : str | None
        Override indicator from catalog (must exist in indicator_catalog.json).
        If None, uses indicator_dependencies from signal catalog.
        Example: "spread_momentum_5d" to swap indicator while keeping transformation.
    transformation_override : str | None
        Override transformation from catalog (must exist in transformation_catalog.json).
        If None, uses transformations from signal catalog.
        Example: "z_score_60d" to swap normalization window while keeping indicator.
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
    
    Signal Composition Pattern
    --------------------------
    Signals are ALWAYS composed from:
    1. Indicator (economically interpretable metric from indicator_catalog.json)
    2. Transformation (signal processing operation from transformation_catalog.json)
    
    Runtime overrides allow swapping components without editing catalogs:
    - security_mapping: Override which securities to load for each instrument type
    - indicator_override: Override which indicator to use (keeps transformation)
    - transformation_override: Override which transformation to apply (keeps indicator)
    """

    label: str
    signal_name: str
    strategy_name: str
    product: str
    data_source: DataSource = "synthetic"
    security_mapping: dict[str, str] | None = None
    indicator_override: str | None = None
    transformation_override: str | None = None
    steps: list[StepName] | None = None
    force_rerun: bool = False
    output_dir: Path = field(default_factory=lambda: DATA_WORKFLOWS_DIR)

    def __post_init__(self) -> None:
        """Validate configuration on initialization."""
        import re
        
        # Validate label format
        if not re.match(r"^[a-z][a-z0-9_]*$", self.label):
            raise ValueError(
                f"Label '{self.label}' is invalid. "
                "Must start with lowercase letter and contain only lowercase letters, numbers, and underscores."
            )
        
        # Validate steps
        if self.steps is not None:
            valid_steps = {
                "data",
                "signal",
                "suitability",
                "backtest",
                "performance",
                "visualization",
            }
            invalid = set(self.steps) - valid_steps
            if invalid:
                raise ValueError(f"Invalid steps: {invalid}")
