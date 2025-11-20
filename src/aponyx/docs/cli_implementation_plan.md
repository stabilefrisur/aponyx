# CLI Orchestrator Implementation Plan

**Target Agent:** Claude Sonnet 4.5  
**Date:** November 20, 2025  
**Estimated Effort:** 4 implementation sessions  
**Dependencies:** Existing `aponyx` modules (config, data, models, backtest, evaluation, visualization, persistence)

---

## Implementation Overview

This plan details the complete implementation of a CLI orchestrator for the systematic macro credit research framework. The implementation is divided into **4 phases** with specific file creation/modification tasks for each.

---

## Phase 1: Core Infrastructure (Session 1)

### Objective
Create foundational abstractions for workflow orchestration without CLI interface.

### Files to Create

#### 1.1. `src/aponyx/workflows/__init__.py`
**Purpose:** Workflows package initialization  
**Exports:**
```python
from .config import WorkflowConfig
from .engine import WorkflowEngine
from .steps import WorkflowStep
from .registry import StepRegistry

__all__ = [
    "WorkflowConfig",
    "WorkflowEngine",
    "WorkflowStep",
    "StepRegistry",
]
```

---

#### 1.2. `src/aponyx/workflows/config.py`
**Purpose:** Workflow configuration data structures  
**Implementation Details:**

```python
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
```

**Key Design Points:**
- Use `@dataclass(frozen=True)` for immutability
- Validate steps in `__post_init__`
- Use modern type hints (`Literal`, no `Union`/`Optional`)
- Default output to `PROCESSED_DIR/workflows`

---

#### 1.3. `src/aponyx/workflows/steps.py`
**Purpose:** Abstract base protocol for workflow steps  
**Implementation Details:**

```python
"""
Workflow step abstractions.

Defines protocol for executable workflow steps with dependency tracking,
caching, and standardized I/O.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

from .config import WorkflowConfig

logger = logging.getLogger(__name__)


class WorkflowStep(Protocol):
    """
    Protocol for executable workflow steps.
    
    All workflow steps must implement this interface for orchestration.
    
    Attributes
    ----------
    name : str
        Step identifier (used for caching and logging).
    config : WorkflowConfig
        Workflow configuration.
        
    Methods
    -------
    execute(context)
        Execute step logic and return output data.
    output_exists()
        Check if step output already exists (for caching).
    get_output_path()
        Return path to expected output files.
    """
    
    name: str
    config: WorkflowConfig
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute workflow step.
        
        Parameters
        ----------
        context : dict[str, Any]
            Outputs from previous steps (keyed by step name).
            
        Returns
        -------
        dict[str, Any]
            Step output data to pass to subsequent steps.
            
        Notes
        -----
        Steps should be idempotent: running twice produces same results.
        Use context["data"] to access data from DataStep, etc.
        """
        ...
    
    def output_exists(self) -> bool:
        """
        Check if step output files exist.
        
        Returns
        -------
        bool
            True if all required outputs exist, False otherwise.
            
        Notes
        -----
        Used by caching logic to skip completed steps.
        Should check file existence and basic validation.
        """
        ...
    
    def get_output_path(self) -> Path:
        """
        Get expected output directory path.
        
        Returns
        -------
        Path
            Directory where step outputs are saved.
        """
        ...


class BaseWorkflowStep(ABC):
    """
    Abstract base class for workflow steps.
    
    Provides common functionality for concrete step implementations.
    
    Parameters
    ----------
    config : WorkflowConfig
        Workflow configuration.
    """
    
    def __init__(self, config: WorkflowConfig) -> None:
        self.config = config
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Step identifier."""
        ...
    
    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute step logic."""
        ...
    
    @abstractmethod
    def output_exists(self) -> bool:
        """Check if output exists."""
        ...
    
    @abstractmethod
    def get_output_path(self) -> Path:
        """Get output directory."""
        ...
    
    def _log_start(self) -> None:
        """Log step start."""
        logger.info("Starting step: %s", self.name)
        
    def _log_complete(self, output: dict[str, Any]) -> None:
        """Log step completion."""
        logger.info("Completed step: %s", self.name)
```

**Key Design Points:**
- Define `Protocol` for structural typing
- Provide `BaseWorkflowStep` ABC for shared logic
- All steps follow same interface contract
- No implementation logic here (pure abstraction)

---

#### 1.4. `src/aponyx/workflows/engine.py`
**Purpose:** Workflow orchestration engine  
**Implementation Details:**

```python
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
        
        completed = 0
        skipped = 0
        errors = []
        
        for idx, step in enumerate(self._steps, start=1):
            step_num = f"{idx}/{len(self._steps)}"
            
            # Check cache
            if self._should_skip_step(step):
                logger.info("Step %s: %s (cached) ⏭", step_num, step.name)
                skipped += 1
                continue
                
            # Execute step
            try:
                logger.info("Step %s: %s", step_num, step.name)
                output = step.execute(self._context)
                self._context[step.name] = output
                completed += 1
                logger.info("Step %s: %s ✓", step_num, step.name)
                
            except Exception as e:
                logger.error("Step %s: %s ✗ - %s", step_num, step.name, str(e))
                errors.append({
                    "step": step.name,
                    "error": str(e),
                    "type": type(e).__name__,
                })
                break  # Stop execution on first error
                
        duration = (datetime.now() - self._start_time).total_seconds()
        
        # Create workflow output directory
        output_dir = self._create_output_directory()
        
        result = {
            "steps_completed": completed,
            "steps_skipped": skipped,
            "output_dir": output_dir,
            "duration_seconds": duration,
            "errors": errors,
        }
        
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
        Format: workflows/{signal}_{strategy}_{timestamp}/
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dirname = f"{self.config.signal_name}_{self.config.strategy_name}_{timestamp}"
        output_dir = self.config.output_dir / dirname
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
```

**Key Design Points:**
- Sequential execution with early exit on errors
- Cache checking before each step
- Structured logging with progress indicators
- Preserve partial results on failure
- Return comprehensive execution metadata

---

#### 1.5. `src/aponyx/workflows/registry.py`
**Purpose:** Step factory and registry  
**Implementation Details:**

```python
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
```

**Key Design Points:**
- Encapsulates step creation logic
- Enforces dependency order
- Makes adding new steps trivial
- Type-safe with protocol compliance

---

#### 1.6. `src/aponyx/workflows/concrete_steps.py`
**Purpose:** Concrete implementations of workflow steps  
**Implementation Details:**

This file implements 6 concrete step classes that wrap existing example scripts. Each step:
1. Inherits from `BaseWorkflowStep`
2. Implements `execute()` by calling existing modules
3. Implements `output_exists()` to check for output files
4. Implements `get_output_path()` for cache location

**Structure:**
```python
"""
Concrete workflow step implementations.

Each step wraps existing functionality from aponyx modules:
- DataStep: Fetches/generates data (wraps data providers)
- SignalStep: Computes signals (wraps models.signals)
- SuitabilityStep: Evaluates signal quality (wraps evaluation.suitability)
- BacktestStep: Runs strategy backtest (wraps backtest.engine)
- PerformanceStep: Computes extended metrics (wraps evaluation.performance)
- VisualizationStep: Generates charts (wraps visualization.plots)
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from aponyx.config import PROCESSED_DIR, RAW_DIR, REGISTRY_PATH, DATA_DIR
from aponyx.data import DataRegistry
from aponyx.models import compute_registered_signals, get_required_data_keys
from aponyx.models.registry import SignalRegistry
from aponyx.evaluation.suitability import evaluate_signal_suitability, compute_forward_returns
from aponyx.evaluation.performance import analyze_backtest_performance
from aponyx.backtest import run_backtest
from aponyx.backtest.registry import StrategyRegistry
from aponyx.visualization import plot_equity_curve, plot_drawdown, plot_signal
from aponyx.persistence import load_parquet, save_parquet
from .steps import BaseWorkflowStep
from .config import WorkflowConfig

logger = logging.getLogger(__name__)


class DataStep(BaseWorkflowStep):
    """Load all required market data from registry."""
    
    @property
    def name(self) -> str:
        return "data"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()
        
        # Get required data keys from ALL enabled signals in catalog
        from aponyx.config import SIGNAL_CATALOG_PATH
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        required_keys = get_required_data_keys(signal_registry)
        
        # Load all required data from registry
        from aponyx.config import REGISTRY_PATH, DATA_DIR
        data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        market_data = {}
        
        for data_key in sorted(required_keys):
            matching_datasets = data_registry.list_datasets(instrument=data_key)
            
            if not matching_datasets:
                raise ValueError(
                    f"No datasets found for instrument '{data_key}'. "
                    f"Run data fetching workflow first."
                )
            
            dataset_name = sorted(matching_datasets)[-1]
            info = data_registry.get_dataset_info(dataset_name)
            df = load_parquet(info["file_path"])
            market_data[data_key] = df
        
        output = {"market_data": market_data}
        self._log_complete(output)
        return output
    
    def output_exists(self) -> bool:
        # Check if market data is loaded in registry
        # For workflow caching, check if output directory has data files
        return self.get_output_path().exists() and any(self.get_output_path().glob("*.parquet"))
    
    def get_output_path(self) -> Path:
        return PROCESSED_DIR / "workflows" / "data" / self.config.signal_name


class SignalStep(BaseWorkflowStep):
    """Compute signal values."""
    
    @property
    def name(self) -> str:
        return "signal"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()
        
        # Get market data from previous step
        market_data = context["data"]["market_data"]
        
        # Compute all enabled signals using registry
        from aponyx.models import SignalConfig
        from aponyx.config import SIGNAL_CATALOG_PATH
        signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
        config = SignalConfig(lookback=20, min_periods=10)
        all_signals = compute_registered_signals(signal_registry, market_data, config)
        
        # Extract target signal for this workflow
        signal = all_signals[self.config.signal_name]
        
        # Save signal
        output_path = self.get_output_path() / f"{self.config.signal_name}.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        signal_df = signal.to_frame(name="value")
        save_parquet(signal_df, output_path)
        
        output = {"signal": signal}
        self._log_complete(output)
        return output
    
    def output_exists(self) -> bool:
        signal_path = self.get_output_path() / f"{self.config.signal_name}.parquet"
        return signal_path.exists()
    
    def get_output_path(self) -> Path:
        return PROCESSED_DIR / "workflows" / "signals" / self.config.signal_name


class SuitabilityStep(BaseWorkflowStep):
    """Evaluate signal-product suitability."""
    
    @property
    def name(self) -> str:
        return "suitability"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()
        
        signal = context["signal"]["signal"]
        
        # Get product from strategy catalog
        from aponyx.config import STRATEGY_CATALOG_PATH
        strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
        strategy_metadata = strategy_registry.get_metadata(self.config.strategy_name)
        product = strategy_metadata.product
        
        # Load spread data for product
        from aponyx.config import REGISTRY_PATH, DATA_DIR
        data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        spread_df = self._load_spread_for_product(data_registry, product)
        
        # Compute forward returns for evaluation
        forward_returns = compute_forward_returns(spread_df["spread"], lags=[1])
        target_change = forward_returns[1]
        
        # Run suitability evaluation
        from aponyx.evaluation.suitability import SuitabilityConfig
        config = SuitabilityConfig()
        result = evaluate_signal_suitability(signal, target_change, config)
        
        # Generate and save report
        from aponyx.evaluation.suitability import generate_suitability_report, save_report
        from aponyx.config import EVALUATION_DIR
        report = generate_suitability_report(result, self.config.signal_name, product)
        save_report(report, self.config.signal_name, product, EVALUATION_DIR / "suitability")
        
        output = {"suitability_result": result, "product": product}
        self._log_complete(output)
        return output
    
    def output_exists(self) -> bool:
        # Check for suitability report markdown file
        report_files = list(self.get_output_path().glob(f"{self.config.signal_name}_*.md"))
        return len(report_files) > 0
    
    def get_output_path(self) -> Path:
        return PROCESSED_DIR / "workflows" / "suitability" / self.config.signal_name


class BacktestStep(BaseWorkflowStep):
    """Run strategy backtest."""
    
    @property
    def name(self) -> str:
        return "backtest"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()
        
        signal = context["signal"]["signal"]
        product = context["suitability"]["product"]
        
        # Load spread data for backtest
        from aponyx.config import REGISTRY_PATH, DATA_DIR
        data_registry = DataRegistry(REGISTRY_PATH, DATA_DIR)
        spread_df = self._load_spread_for_product(data_registry, product)
        spread = spread_df["spread"]
        
        # Align signal and spread to common dates
        common_idx = signal.index.intersection(spread.index)
        signal = signal.loc[common_idx]
        spread = spread.loc[common_idx]
        
        # Get strategy config from catalog
        from aponyx.config import STRATEGY_CATALOG_PATH
        strategy_registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
        strategy_metadata = strategy_registry.get_metadata(self.config.strategy_name)
        backtest_config = strategy_metadata.to_config()
        
        # Run backtest using function (not class)
        from aponyx.backtest import BacktestResult
        result = run_backtest(signal, spread, backtest_config)
        
        # Save results
        output_dir = self.get_output_path()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        save_parquet(result.pnl, output_dir / "pnl.parquet")
        save_parquet(result.positions, output_dir / "positions.parquet")
        
        output = {"backtest_result": result}
        self._log_complete(output)
        return output
    
    def output_exists(self) -> bool:
        pnl_path = self.get_output_path() / "pnl.parquet"
        positions_path = self.get_output_path() / "positions.parquet"
        return pnl_path.exists() and positions_path.exists()
    
    def get_output_path(self) -> Path:
        return PROCESSED_DIR / "workflows" / "backtests" / f"{self.config.signal_name}_{self.config.strategy_name}"


class PerformanceStep(BaseWorkflowStep):
    """Compute extended performance metrics."""
    
    @property
    def name(self) -> str:
        return "performance"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()
        
        backtest_result = context["backtest"]["backtest_result"]
        
        # Compute comprehensive performance metrics
        from aponyx.evaluation.performance import PerformanceConfig
        config = PerformanceConfig(
            n_subperiods=4,
            rolling_window=63,
            attribution_quantiles=3,
        )
        performance = analyze_backtest_performance(backtest_result, config)
        
        # Generate and save report
        from aponyx.evaluation.performance import generate_performance_report, save_report
        from aponyx.config import PERFORMANCE_REPORTS_DIR
        report = generate_performance_report(
            performance,
            signal_id=self.config.signal_name,
            strategy_id=self.config.strategy_name,
            generate_tearsheet=False,
        )
        save_report(report, self.config.signal_name, self.config.strategy_name, PERFORMANCE_REPORTS_DIR)
        
        output = {"performance": performance}
        self._log_complete(output)
        return output
    
    def output_exists(self) -> bool:
        # Check for performance report markdown file
        report_files = list(self.get_output_path().glob(f"{self.config.signal_name}_{self.config.strategy_name}_*.md"))
        return len(report_files) > 0
    
    def get_output_path(self) -> Path:
        return PROCESSED_DIR / "workflows" / "performance" / f"{self.config.signal_name}_{self.config.strategy_name}"


class VisualizationStep(BaseWorkflowStep):
    """Generate visualization charts."""
    
    @property
    def name(self) -> str:
        return "visualization"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._log_start()
        
        backtest_result = context["backtest"]["backtest_result"]
        pnl = backtest_result.pnl
        positions = backtest_result.positions
        
        # Generate charts with descriptive titles
        title_prefix = f"{self.config.signal_name} ({self.config.strategy_name})"
        equity_fig = plot_equity_curve(
            pnl["net_pnl"],
            title=f"Equity Curve: {title_prefix}",
            show_drawdown_shading=True,
        )
        drawdown_fig = plot_drawdown(
            pnl["net_pnl"],
            title=f"Drawdown: {title_prefix}",
        )
        signal_fig = plot_signal(
            positions["signal"],
            title=f"Signal: {self.config.signal_name}",
        )
        
        # Save charts (HTML)
        output_dir = self.get_output_path()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        equity_fig.write_html(output_dir / "equity_curve.html")
        drawdown_fig.write_html(output_dir / "drawdown.html")
        signal_fig.write_html(output_dir / "signal.html")
        
        output = {
            "equity_fig": equity_fig,
            "drawdown_fig": drawdown_fig,
            "signal_fig": signal_fig,
        }
        self._log_complete(output)
        return output
    
    def output_exists(self) -> bool:
        equity_path = self.get_output_path() / "equity_curve.html"
        return equity_path.exists()
    
    def get_output_path(self) -> Path:
        return PROCESSED_DIR / "workflows" / "visualizations" / f"{self.config.signal_name}_{self.config.strategy_name}"
    
    def _load_spread_for_product(self, data_registry: DataRegistry, product: str) -> pd.DataFrame:
        """
        Load spread data for product from registry.
        
        Parameters
        ----------
        data_registry : DataRegistry
            Data registry instance.
        product : str
            Product identifier (e.g., "cdx_ig_5y").
        
        Returns
        -------
        pd.DataFrame
            Spread data with DatetimeIndex.
        
        Raises
        ------
        ValueError
            If no dataset found for product.
        """
        all_datasets = data_registry.list_datasets()
        
        for dataset_name in all_datasets:
            info = data_registry.get_dataset_info(dataset_name)
            metadata = info.get("metadata", {})
            params = metadata.get("params", {})
            
            if params.get("security") == product:
                return load_parquet(info["file_path"])
        
        raise ValueError(f"No dataset found for product: {product}")
```

**Key Design Points:**
- Each step wraps existing modules (no duplicate logic)
- Steps are self-contained and testable
- Output paths follow consistent structure
- Context dictionary passes structured results (dataclasses via BacktestResult)
- Helper method `_load_spread_for_product()` shared across SuitabilityStep and BacktestStep
- All steps use actual functions from codebase, not non-existent classes

---

### Phase 1 Testing

Create `tests/workflows/test_engine.py`:
- Test workflow execution with synthetic config
- Test caching behavior
- Test error handling
- Test partial execution on failure

---

## Phase 2: CLI Interface (Session 2)

### Objective
Create Click-based CLI commands that use the workflow engine.

### Files to Create

#### 2.1. `src/aponyx/cli/__init__.py`
**Purpose:** CLI package initialization  
**Content:**
```python
from .main import cli

__all__ = ["cli"]
```

---

#### 2.2. `src/aponyx/cli/main.py`
**Purpose:** Primary CLI entry point  
**Implementation Details:**

```python
"""
Command-line interface for systematic macro credit research.

Provides commands for running workflows, generating reports, and
managing catalog items.
"""

import logging
import sys

import click

from aponyx.cli.commands import run, report, list_items, clean

logger = logging.getLogger(__name__)


@click.group(name="aponyx")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress all output except errors",
)
def cli(verbose: bool, quiet: bool) -> None:
    """
    Systematic Macro Credit Research CLI.
    
    Run research workflows, generate reports, and manage catalog items.
    """
    # Configure logging
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# Register commands
cli.add_command(run)
cli.add_command(report)
cli.add_command(list_items)
cli.add_command(clean)


def main() -> None:
    """Entry point for installed CLI."""
    try:
        cli()
    except Exception as e:
        logger.exception("Unexpected error: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Key Design Points:**
- Use `click.group()` for command grouping
- Global `--verbose` and `--quiet` flags
- Centralized logging configuration
- Exception handling at top level

---

#### 2.3. `src/aponyx/cli/commands/__init__.py`
**Purpose:** Commands subpackage  
**Content:**
```python
from .run import run
from .report import report
from .list import list_items
from .clean import clean

__all__ = ["run", "report", "list_items", "clean"]
```

---

#### 2.4. `src/aponyx/cli/commands/run.py`
**Purpose:** Workflow execution command  
**Implementation Details:**

```python
"""
Run workflow command.

Executes research workflows for signal-strategy combinations.
"""

import logging
from pathlib import Path

import click

from aponyx.workflows import WorkflowEngine, WorkflowConfig

logger = logging.getLogger(__name__)


@click.command(name="run")
@click.option(
    "--signal",
    required=True,
    type=str,
    help="Signal name from signal catalog",
)
@click.option(
    "--strategy",
    required=True,
    type=str,
    help="Strategy name from strategy catalog",
)
@click.option(
    "--data",
    type=click.Choice(["synthetic", "file", "bloomberg"], case_sensitive=False),
    default="synthetic",
    help="Data source (default: synthetic)",
)
@click.option(
    "--steps",
    type=str,
    help="Comma-separated step list (default: all steps)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-run even if cached outputs exist",
)
def run(
    signal: str,
    strategy: str,
    data: str,
    steps: str | None,
    force: bool,
) -> None:
    """
    Run research workflow for signal-strategy combination.
    
    Executes full pipeline: data → signal → evaluation → backtest → visualization.
    Skips completed steps unless --force is specified.
    
    Examples:
    
        aponyx run --signal spread_momentum --strategy balanced
        
        aponyx run --signal cdx_vix_gap --strategy aggressive --data bloomberg
        
        aponyx run --signal spread_momentum --strategy balanced --steps data,signal,backtest --force
    """
    # Parse steps
    step_list = None
    if steps:
        step_list = [s.strip() for s in steps.split(",")]
        
    # Create config
    try:
        config = WorkflowConfig(
            signal_name=signal,
            strategy_name=strategy,
            data_source=data,
            steps=step_list,
            force_rerun=force,
        )
    except ValueError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        raise click.Abort()
        
    # Execute workflow
    click.echo(f"\n🚀 Starting workflow: {signal} ({strategy})")
    click.echo(f"   Data source: {data}")
    if step_list:
        click.echo(f"   Steps: {', '.join(step_list)}")
    if force:
        click.echo(f"   Mode: Force re-run")
        
    engine = WorkflowEngine(config)
    results = engine.execute()
    
    # Display results
    if results["errors"]:
        click.echo(f"\n❌ Workflow failed after {results['steps_completed']} steps", err=True)
        for error in results["errors"]:
            click.echo(f"   Error in {error['step']}: {error['error']}", err=True)
        raise click.Abort()
    else:
        click.echo(f"\n✅ Workflow complete ({results['duration_seconds']:.1f}s)")
        click.echo(f"   Steps completed: {results['steps_completed']}")
        click.echo(f"   Steps skipped: {results['steps_skipped']}")
        click.echo(f"   Results: {results['output_dir']}")
```

**Key Design Points:**
- Use `click.option()` for all parameters
- Provide helpful `--help` text
- Validate configuration before execution
- Rich output with emojis for status
- Handle errors gracefully with click.Abort()

---

#### 2.5. `src/aponyx/cli/commands/report.py`
**Purpose:** Report generation command  
**Implementation Details:**

```python
"""
Generate research report command.

Creates comprehensive analysis documents from workflow results.
"""

import logging
from pathlib import Path

import click

logger = logging.getLogger(__name__)


@click.command(name="report")
@click.option(
    "--signal",
    required=True,
    type=str,
    help="Signal name",
)
@click.option(
    "--strategy",
    required=True,
    type=str,
    help="Strategy name",
)
@click.option(
    "--format",
    type=click.Choice(["console", "markdown", "html"], case_sensitive=False),
    default="console",
    help="Report output format (default: console)",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    help="Custom output path",
)
def report(
    signal: str,
    strategy: str,
    format: str,
    output: Path | None,
) -> None:
    """
    Generate comprehensive research report from existing results.
    
    Aggregates metrics, charts, and analysis into single document.
    
    Examples:
    
        aponyx report --signal spread_momentum --strategy balanced
        
        aponyx report --signal spread_momentum --strategy balanced --format html --output report.html
    """
    click.echo(f"\n📄 Generating {format} report: {signal} ({strategy})")
    
    # TODO: Implement report generation
    # This is a placeholder for Phase 3
    click.echo("   Report generation not yet implemented")
    click.echo("   Planned for Phase 3")
```

---

#### 2.6. `src/aponyx/cli/commands/list.py`
**Purpose:** Catalog listing command  
**Implementation Details:**

```python
"""
List catalog items command.

Displays available signals, strategies, and datasets.
"""

import logging

import click

from aponyx.models.registry import SignalRegistry
from aponyx.backtest.registry import StrategyRegistry
from aponyx.data.registry import DataRegistry

logger = logging.getLogger(__name__)


@click.command(name="list")
@click.argument(
    "item_type",
    type=click.Choice(["signals", "strategies", "datasets"], case_sensitive=False),
)
def list_items(item_type: str) -> None:
    """
    List available catalog items.
    
    ITEM_TYPE can be: signals, strategies, or datasets
    
    Examples:
    
        aponyx list signals
        
        aponyx list strategies
        
        aponyx list datasets
    """
    click.echo()
    
    if item_type == "signals":
        registry = SignalRegistry()
        signals = registry.list_signals()
        
        click.echo("Available Signals:")
        for signal in signals:
            config = registry.get_config(signal)
            click.echo(f"  • {signal:<20} — {config.description}")
            
    elif item_type == "strategies":
        registry = StrategyRegistry()
        strategies = registry.list_strategies()
        
        click.echo("Available Strategies:")
        for strategy in strategies:
            config = registry.get_config(strategy)
            click.echo(f"  • {strategy:<20} — {config.description}")
            
    elif item_type == "datasets":
        registry = DataRegistry()
        datasets = registry.list_datasets()
        
        click.echo("Registered Datasets:")
        for dataset in datasets:
            entry = registry.get(dataset)
            click.echo(f"  • {dataset:<20} — {entry['product']}")
            
    click.echo()
```

**Key Design Points:**
- Use `click.argument()` for positional args
- Format output with consistent spacing
- Display descriptive information from catalogs

---

#### 2.7. `src/aponyx/cli/commands/clean.py`
**Purpose:** Cache cleaning command  
**Implementation Details:**

```python
"""
Clean cached results command.

Removes processed outputs to force fresh computation.
"""

import logging
import shutil
from pathlib import Path

import click

from aponyx.config import PROCESSED_DIR

logger = logging.getLogger(__name__)


@click.command(name="clean")
@click.option(
    "--signal",
    type=str,
    help="Clean specific signal results only",
)
@click.option(
    "--all",
    "clean_all",
    is_flag=True,
    help="Clean all cached results",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without deleting",
)
def clean(
    signal: str | None,
    clean_all: bool,
    dry_run: bool,
) -> None:
    """
    Clear cached workflow results.
    
    Examples:
    
        aponyx clean --signal spread_momentum
        
        aponyx clean --all
        
        aponyx clean --all --dry-run
    """
    workflows_dir = PROCESSED_DIR / "workflows"
    
    if not workflows_dir.exists():
        click.echo("\n✓ No cached results found")
        return
        
    # Determine what to clean
    if signal:
        targets = list(workflows_dir.glob(f"**/{signal}_*"))
    elif clean_all:
        targets = [workflows_dir]
    else:
        click.echo("❌ Must specify --signal or --all", err=True)
        raise click.Abort()
        
    if not targets:
        click.echo(f"\n✓ No cached results found for: {signal}")
        return
        
    # Show/delete targets
    click.echo()
    for target in targets:
        if dry_run:
            click.echo(f"   Would delete: {target}")
        else:
            click.echo(f"   Deleting: {target}")
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
                
    if dry_run:
        click.echo("\n✓ Dry run complete (no files deleted)")
    else:
        click.echo(f"\n✓ Cleaned {len(targets)} item(s)")
```

---

### Phase 2 Configuration

#### 2.8. Update `pyproject.toml`
Add CLI entry point:

```toml
[project.scripts]
aponyx = "aponyx.cli.main:main"
```

This allows users to run `aponyx` command after installation.

---

### Phase 2 Testing

Create `tests/cli/test_commands.py`:
- Test `run` command with various options
- Test `list` command output
- Test `clean` command (dry-run mode)
- Mock workflow execution to avoid side effects

---

## Phase 3: Enhanced Features (Session 3)

### Objective
Add report generation, configuration files, and improved output formatting.

### Files to Create/Modify

#### 3.1. `src/aponyx/reporting/__init__.py`
**Purpose:** Report generation package  
**Exports:**
```python
from .generator import generate_report, ReportFormat

__all__ = ["generate_report", "ReportFormat"]
```

---

#### 3.2. `src/aponyx/reporting/generator.py`
**Purpose:** Report generation logic  
**Implementation:** Aggregate workflow results into formatted report (console/markdown/HTML)

---

#### 3.3. Implement `report` command
Update `src/aponyx/cli/commands/report.py` to use reporting module.

---

#### 3.4. Configuration file support
Add `--config` option to `run` command that loads YAML configuration.

---

## Phase 4: Polish & Documentation (Session 4)

### Objective
Add tests, documentation, and quality-of-life improvements.

### Tasks

#### 4.1. Comprehensive testing
- Unit tests for all workflow steps
- Integration tests for full workflows
- CLI command tests
- Error handling tests

---

#### 4.2. Documentation
Create `src/aponyx/docs/cli_user_guide.md`:
- Installation instructions
- Command reference
- Usage examples
- Troubleshooting guide

---

#### 4.3. Quality improvements
- Add progress bars (using `rich` or `click.progressbar`)
- Improve error messages
- Add workflow resumption (save state on failure)
- Add timing breakdown by step

---

## Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Create `workflows/__init__.py`
- [ ] Create `workflows/config.py`
- [ ] Create `workflows/steps.py`
- [ ] Create `workflows/engine.py`
- [ ] Create `workflows/registry.py`
- [ ] Create `workflows/concrete_steps.py`
- [ ] Create `tests/workflows/test_engine.py`
- [ ] Run tests and verify

### Phase 2: CLI Interface
- [ ] Create `cli/__init__.py`
- [ ] Create `cli/main.py`
- [ ] Create `cli/commands/__init__.py`
- [ ] Create `cli/commands/run.py`
- [ ] Create `cli/commands/report.py` (stub)
- [ ] Create `cli/commands/list.py`
- [ ] Create `cli/commands/clean.py`
- [ ] Update `pyproject.toml` with entry point
- [ ] Install package in dev mode
- [ ] Test CLI commands manually
- [ ] Create `tests/cli/test_commands.py`

### Phase 3: Enhanced Features
- [ ] Create `reporting/__init__.py`
- [ ] Create `reporting/generator.py`
- [ ] Implement report command
- [ ] Add YAML config support to run command
- [ ] Create example config files
- [ ] Test report generation

### Phase 4: Polish & Documentation
- [ ] Write comprehensive unit tests
- [ ] Write integration tests
- [ ] Create user guide documentation
- [ ] Add progress bars
- [ ] Improve error messages
- [ ] Add workflow state persistence
- [ ] Performance profiling
- [ ] Final QA and cleanup

---

## Critical Implementation Notes

### Type Hints
- Use modern syntax: `str | None` not `Optional[str]`
- Use `list[str]` not `List[str]`
- Use `Literal` for enum-like types
- All functions must have complete type annotations

### Logging
- Use module-level loggers: `logger = logging.getLogger(__name__)`
- Use %-formatting: `logger.info("Step %s complete", name)`
- Never call `logging.basicConfig()` in library code (only CLI entry point)

### Error Handling
- Fail-fast for configuration errors
- Graceful degradation for data errors
- Preserve partial results on failure
- Clear error messages for users

### Testing
- Unit tests for each step independently
- Integration tests for full workflows
- Mock external dependencies (Bloomberg, file I/O)
- Test caching behavior explicitly

### Documentation
- NumPy-style docstrings for all public APIs
- Include usage examples in docstrings
- Document workflow dependencies clearly
- Keep README updated with CLI examples

---

## Dependencies to Add

Update `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "click>=8.1.0",
    "pyyaml>=6.0",  # For config file support
]

[project.optional-dependencies]
dev = [
    # ... existing dev dependencies ...
    "pytest-click>=1.1.0",  # For CLI testing
]
```

---

## Success Criteria

Phase 1 Complete:
- [ ] Workflow engine executes all steps sequentially
- [ ] Caching works (skips completed steps)
- [ ] Errors handled gracefully with partial results
- [ ] All unit tests pass

Phase 2 Complete:
- [ ] CLI commands installed and runnable
- [ ] `aponyx run` executes workflows successfully
- [ ] `aponyx list` shows catalog items
- [ ] `aponyx clean` removes cached results
- [ ] Manual testing confirms user experience

Phase 3 Complete:
- [ ] Report generation works for all formats
- [ ] YAML config files supported
- [ ] Example configs provided

Phase 4 Complete:
- [ ] Test coverage >80%
- [ ] User guide documentation complete
- [ ] Performance acceptable (<30s for full workflow)
- [ ] Ready for production use

---

## Post-Implementation Tasks

1. Update main `README.md` with CLI usage examples
2. Create `CHANGELOG.md` entry for new CLI feature
3. Add CLI examples to notebooks
4. Record demo video (optional)
5. Update project roadmap

---

## Agent Execution Instructions

When implementing this plan:

1. **Follow phase order strictly** — Each phase builds on previous
2. **Run tests after each file** — Don't proceed if tests fail
3. **Use existing modules** — Don't duplicate logic from examples/
4. **Keep functions pure** — Avoid side effects where possible
5. **Log extensively** — User visibility is critical
6. **Handle errors gracefully** — Clear messages, no stack traces to users
7. **Type everything** — Complete type annotations required
8. **Document as you go** — Docstrings before implementation

**Communication style:**
- Confirm understanding before starting each phase
- Report progress after creating each major file
- Flag any blockers or missing dependencies immediately
- Suggest improvements if design issues discovered

**File creation order within phases:**
- Abstract interfaces before concrete implementations
- Core logic before CLI wrappers
- Tests alongside implementation (not after)

---

This implementation plan provides complete specifications for building the CLI orchestrator. Each phase is self-contained and testable. The agent should be able to execute this plan with minimal additional guidance.
