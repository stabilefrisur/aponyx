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
    indicator_transformation_override : str | None
        Override indicator transformation from catalog (must exist in indicator_transformation.json).
        If None, uses indicator_transformation from signal catalog.
        Example: "spread_momentum_5d" to swap indicator while keeping score/signal transformations.
    score_transformation_override : str | None
        Override score transformation from catalog (must exist in score_transformation.json).
        If None, uses score_transformation from signal catalog.
        Example: "z_score_60d" to swap normalization window while keeping indicator/signal transformations.
    signal_transformation_override : str | None
        Override signal transformation from catalog (must exist in signal_transformation.json).
        If None, uses signal_transformation from signal catalog.
        Example: "bounded_2_0" to swap trading rules while keeping indicator/score transformations.
    dv01_per_million_override : float | None
        Override product's default DV01 per million parameter.
        If None, uses dv01_per_million from bloomberg_securities.json for the product.
    transaction_cost_bps_override : float | None
        Override product's default transaction cost in basis points.
        Mutually exclusive with transaction_cost_pct_override.
        If None, uses transaction_cost_bps from bloomberg_securities.json for the product.
    transaction_cost_pct_override : float | None
        Override to use percentage-based transaction costs instead of fixed bps.
        Mutually exclusive with transaction_cost_bps_override.
        When set, transaction costs are calculated as a percentage of the current spread.
        Value should be in decimal form (e.g., 0.025 for 2.5%).
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

    Four-Stage Transformation Pipeline
    -----------------------------------
    Security → Indicator → Score → Signal → Position

    Each signal references exactly one transformation from each stage (1:1:1 relationship).

    Runtime overrides allow swapping components at any stage without editing catalogs:
    - security_mapping: Override which securities to load for each instrument type
    - indicator_transformation_override: Swap indicator while keeping score/signal transformations
    - score_transformation_override: Swap normalization while keeping indicator/signal transformations
    - signal_transformation_override: Swap trading rules while keeping indicator/score transformations
    - dv01_per_million_override: Override product's DV01 for sensitivity analysis
    - transaction_cost_bps_override: Override fixed transaction costs
    - transaction_cost_pct_override: Use percentage-based transaction costs (mutually exclusive with bps)
    """

    label: str
    signal_name: str
    strategy_name: str
    product: str
    data_source: DataSource = "synthetic"
    security_mapping: dict[str, str] | None = None
    indicator_transformation_override: str | None = None
    score_transformation_override: str | None = None
    signal_transformation_override: str | None = None
    dv01_per_million_override: float | None = None
    transaction_cost_bps_override: float | None = None
    transaction_cost_pct_override: float | None = None
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

        # T016: Validate mutual exclusivity of transaction cost overrides
        if (
            self.transaction_cost_bps_override is not None
            and self.transaction_cost_pct_override is not None
        ):
            raise ValueError(
                "Cannot specify both transaction_cost_bps_override and "
                "transaction_cost_pct_override. Use either fixed basis points "
                "(bps) or percentage-based (pct), not both."
            )
