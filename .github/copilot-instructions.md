# Copilot Instructions for Aponyx

> **Auto-generated from codebase analysis** | Last Updated: November 22, 2025

This file provides comprehensive guidance for AI coding assistants working on the aponyx systematic fixed-income research framework. All patterns documented here are based on actual codebase analysis, not invented practices.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [File Organization](#file-organization)
4. [Architectural Domains](#architectural-domains)
5. [Feature Scaffold Guide](#feature-scaffold-guide)
6. [Integration Rules](#integration-rules)
7. [Code Patterns & Conventions](#code-patterns--conventions)
8. [Example Prompts](#example-prompts)

---

## Project Overview

### Purpose

Aponyx is a **Python 3.12 systematic fixed-income research framework** for developing and backtesting tactical credit overlay strategies. The project centers on CDX (credit derivative index) strategies that exploit temporary market dislocations.

### Key Capabilities

- **CLI Orchestration**: Command-line workflows via `aponyx run`, `report`, `list`, `clean`
- **Workflow Engine**: Sequential pipeline with smart caching and dependency tracking
- **Data Layer**: Provider pattern (File, Bloomberg) with TTL caching and validation
- **Signal Generation**: Registry-based computation with JSON catalogs
- **Pre-Backtest Evaluation**: Signal-product suitability assessment (PASS/HOLD/FAIL)
- **Deterministic Backtesting**: DV01-based P&L with transaction costs
- **Post-Backtest Analysis**: Extended metrics with attribution decomposition
- **Interactive Visualization**: Plotly charts (returns figures, caller controls rendering)
- **Multi-Format Reporting**: Console, markdown, HTML output

### Design Philosophy

1. **Modularity** - Clean layer separation (data → models → backtest → evaluation)
2. **Reproducibility** - Fixed seeds, metadata logging, deterministic outputs
3. **Type Safety** - Modern Python syntax (`str | None`, `dict[str, Any]`)
4. **Functions Over Classes** - Pure functions for transformations, @dataclass for containers
5. **Transparency** - Clear signal conventions, explicit P&L calculations
6. **No Legacy Support** - Breaking changes without deprecation warnings

### Workflow for Multi-Step Tasks

1. **Understand** — Read relevant files and documentation to grasp context
2. **Plan** — Break complex tasks into discrete, testable steps
3. **Implement** — Execute changes with proper type hints and docstrings
4. **Validate** — Run tests or check for errors after modifications
5. **Document** — Update only if creating new public APIs or changing behavior

**For simple tasks:** Skip planning and implement directly.

**Communication style:** Do NOT use decorative emojis in responses, code, or documentation unless explicitly requested by the user.

---

## Technology Stack

### Core Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Language** | Python | 3.12 | Strict requirement, modern syntax only |
| **CLI Framework** | Click | 8.1+ | Command-line orchestration |
| **Data Analysis** | Pandas | 2.0+ | Time series manipulation |
| **Numerical Computing** | NumPy | 1.24+ | Array operations |
| **Visualization** | Plotly | 5.24+ | Interactive charts |
| **Statistics** | Statsmodels | 0.14+ | OLS regression, statistical tests |
| **Data I/O** | PyArrow | 12.0+ | Parquet persistence |
| **Testing** | Pytest | 8.0+ | Unit and integration tests |
| **Type Checking** | Mypy | 1.11+ | Static type validation |
| **Bloomberg** | xbbg | 0.7+ | Optional Terminal integration |

### Build & Package Management

- **uv**: Package installer and environment manager
- **pyproject.toml**: Modern project metadata (PEP 621)
- **uv_build**: Build backend for distribution

### Modern Python Features

```python
# Union types (PEP 604)
def fetch_data(source: FileSource | BloombergSource) -> pd.DataFrame | None:
    ...

# Built-in generics (PEP 585)
def process_signals(signals: dict[str, pd.Series]) -> list[BacktestResult]:
    ...

# Frozen dataclasses
@dataclass(frozen=True)
class SignalConfig:
    lookback: int = 20
    min_periods: int = 10
```

---

## File Organization

### Source Code Structure

```
src/aponyx/
├── cli/                    # Command-line interface
│   ├── main.py            # CLI entry point
│   └── commands/          # run, report, list, clean
├── workflows/             # Pipeline orchestration
│   ├── engine.py          # WorkflowEngine with caching
│   ├── config.py          # WorkflowConfig dataclass
│   ├── steps.py           # WorkflowStep protocol
│   ├── concrete_steps.py  # Step implementations
│   └── registry.py        # Step factory
├── reporting/             # Multi-format output
│   └── generator.py       # Console/markdown/HTML
├── data/                  # Data loading & validation
│   ├── fetch.py           # Unified fetch interface
│   ├── sources.py         # DataSource protocol
│   ├── validation.py      # Schema validation
│   ├── cache.py           # TTL-based caching
│   ├── registry.py        # Dataset tracking
│   └── providers/         # File, Bloomberg providers
├── models/                # Signal generation
│   ├── signals.py         # Compute functions
│   ├── registry.py        # SignalRegistry
│   ├── orchestrator.py    # Batch computation
│   └── signal_catalog.json # Signal metadata
├── backtest/              # P&L simulation
│   ├── engine.py          # run_backtest()
│   ├── config.py          # BacktestConfig
│   ├── registry.py        # StrategyRegistry
│   └── strategy_catalog.json
├── evaluation/            # Pre/post-backtest analysis
│   ├── suitability/       # Pre-backtest quality gate
│   │   ├── evaluator.py   # 4-component scoring
│   │   ├── tests.py       # Statistical tests
│   │   └── registry.py    # Evaluation tracking
│   └── performance/       # Post-backtest metrics
│       ├── analyzer.py    # Extended metrics
│       ├── decomposition.py # Attribution
│       └── registry.py    # Performance tracking
├── visualization/         # Chart generation
│   ├── plots.py           # plot_equity_curve, plot_signal, plot_drawdown
│   └── visualizer.py      # Theme management
├── persistence/           # I/O operations
│   ├── parquet_io.py      # DataFrame storage
│   └── json_io.py         # Metadata storage
├── config/                # Constants & paths
│   └── __init__.py        # PROJECT_ROOT, DATA_DIR, catalog paths
├── examples/              # Standalone workflow scripts
│   ├── 01_generate_synthetic_data.py
│   ├── 02_fetch_data_file.py
│   ├── 04_compute_signal.py
│   ├── 05_evaluate_suitability.py
│   ├── 06_run_backtest.py
│   ├── 07_analyze_performance.py
│   └── 08_visualize_results.py
└── docs/                  # Design documentation
    ├── cli_guide.md
    ├── governance_design.md
    ├── signal_registry_usage.md
    ├── signal_suitability_design.md
    ├── performance_evaluation_design.md
    └── python_guidelines.md
```

### Data Storage Structure

```
data/
├── raw/                   # Source data (permanent)
│   ├── synthetic/        # Generated test data
│   └── bloomberg/        # Terminal downloads
├── cache/                # TTL cache (regenerable)
│   ├── file/
│   └── bloomberg/
├── workflows/            # Timestamped workflow runs
│   └── {signal}_{strategy}_{timestamp}/
│       ├── metadata.json
│       ├── reports/
│       ├── data/
│       ├── signals/
│       ├── backtests/
│       └── visualizations/
└── .registries/          # Runtime metadata (not in git)
    ├── registry.json     # DataRegistry
    ├── suitability.json  # SuitabilityRegistry
    └── performance.json  # PerformanceRegistry
```

### Configuration & Metadata Files

| File | Location | Type | Purpose |
|------|----------|------|---------|
| `signal_catalog.json` | `src/aponyx/models/` | Static | Signal definitions (3 signals) |
| `strategy_catalog.json` | `src/aponyx/backtest/` | Static | Strategy configs (4 strategies) |
| `bloomberg_securities.json` | `src/aponyx/data/` | Static | Security-to-ticker mapping |
| `registry.json` | `data/.registries/` | Runtime | Dataset tracking |
| `suitability.json` | `data/.registries/` | Runtime | Evaluation results |
| `performance.json` | `data/.registries/` | Runtime | Performance analysis |

---

## Architectural Domains

### Layer Boundaries

| Layer | Can Import From | Cannot Import From |
|-------|----------------|-------------------|
| **cli/** | workflows, reporting, config | data, models, backtest, evaluation |
| **workflows/** | All layers except cli | cli |
| **reporting/** | evaluation, persistence, config | data, models, backtest, visualization |
| **data/** | config, persistence | models, backtest, evaluation, visualization |
| **models/** | config, data (schemas only) | backtest, evaluation, visualization |
| **evaluation/** | config, backtest, persistence | data (direct), models, visualization |
| **backtest/** | config, models (protocols only) | data (direct), evaluation, visualization |
| **visualization/** | None (generic DataFrames) | All business logic layers |
| **persistence/** | config | All others |
| **config/** | None | All |

### Domain Responsibilities

#### CLI Orchestration (`cli/`)

**Purpose**: Command-line interface with zero business logic

**Patterns**:
- Click decorators for parameter parsing
- YAML config support with CLI overrides
- Delegates to WorkflowEngine for execution
- User-friendly error messages

**Example**:
```python
@click.command(name="run")
@click.option("--signal", type=str)
@click.option("--strategy", type=str)
@click.option("--force", is_flag=True)
def run(signal: str | None, strategy: str | None, force: bool) -> None:
    config = WorkflowConfig(signal_name=signal, strategy_name=strategy, force_rerun=force)
    engine = WorkflowEngine(config)
    results = engine.execute()
    click.echo(f"Completed {results['steps_completed']} steps")
```

#### Workflow Engine (`workflows/`)

**Purpose**: Sequential pipeline with caching and dependency tracking

**Patterns**:
- Steps execute in fixed order: data → signal → suitability → backtest → performance → visualization
- Context dict shared across steps
- Cache checking via `output_exists()` before execution
- Timestamped output directories

**Example**:
```python
class WorkflowEngine:
    def execute(self) -> dict[str, Any]:
        self._context["output_dir"] = self._create_output_directory()
        
        for step in self._steps:
            if self._should_skip_step(step):
                self._context[step.name] = step.load_cached_output()
                continue
            
            output = step.execute(self._context)
            self._context[step.name] = output
```

#### Data Layer (`data/`)

**Purpose**: Load, validate, transform market data

**Patterns**:
- Provider pattern with frozen dataclasses (FileSource, BloombergSource)
- Unified fetch functions (fetch_cdx, fetch_vix, fetch_etf)
- Strict schema validation with range checks
- TTL-based caching (1 day default)
- DataRegistry for metadata tracking

**Example**:
```python
source = FileSource("data/raw/cdx.parquet")
cdx_df = fetch_cdx(source, security="cdx_ig_5y", use_cache=True)
# Returns: pd.DataFrame with DatetimeIndex, validated schema
```

**Constraints**:
- All DataFrames MUST have DatetimeIndex
- CDX spreads: 0-10,000 bps, VIX: 0-200 (validated)
- Forward-fill for missing dates
- No imports from models/backtest/evaluation

#### Signal Generation (`models/`)

**Purpose**: Compute signals from market data

**Patterns**:
- Registry-based computation from JSON catalog
- Z-score normalization over rolling windows
- Consistent sign convention (positive = long credit)
- Frozen SignalConfig dataclass

**Example**:
```python
registry = SignalRegistry(SIGNAL_CATALOG_PATH)
signals = compute_registered_signals(registry, market_data, config)
# Returns: dict[str, pd.Series] with z-score normalized signals
```

**Constraints**:
- Signals are pure functions (NOT classes)
- Must return z-score normalized pd.Series
- Positive signal = long credit risk (buy CDX)
- Catalog declares data requirements explicitly

#### Backtest Execution (`backtest/`)

**Purpose**: Convert signals to positions and simulate P&L

**Patterns**:
- Threshold-based positions (entry/exit hysteresis)
- Binary sizing (+1, 0, -1 only)
- DV01-based P&L calculation
- Transaction costs on entry/exit
- StrategyRegistry with frozen metadata

**Example**:
```python
config = BacktestConfig(entry_threshold=1.5, exit_threshold=0.75, position_size=10.0)
result = run_backtest(signal, spread, config)
# Returns: BacktestResult with positions DataFrame, pnl DataFrame, metadata
```

**Constraints**:
- entry_threshold MUST be > exit_threshold (validated)
- Single-asset only (no portfolios)
- P&L = position * (-spread_change) * DV01 * notional / 1M
- Deterministic execution (same inputs = same outputs)

#### Evaluation Framework (`evaluation/`)

**Purpose**: Pre/post backtest analysis with registry tracking

**Pre-Backtest** (`suitability/`):
- 4-component scoring: data health (20%), predictive (40%), economic (20%), stability (20%)
- Decision thresholds: PASS ≥ 0.7, HOLD 0.4-0.7, FAIL < 0.4
- Rolling window stability (252 default)
- SuitabilityRegistry for tracking

**Post-Backtest** (`performance/`):
- Extended metrics (Sharpe, Sortino, Calmar, tail ratio, profit factor)
- Attribution analysis (directional, signal strength, win/loss)
- PerformanceRegistry for tracking

**Example**:
```python
# Pre-backtest
suitability = evaluate_signal_suitability(signal, target, config)
if suitability.decision == "FAIL":
    return  # Do not backtest

# Post-backtest  
performance = analyze_backtest_performance(result.pnl, result.positions, config)
```

#### Visualization (`visualization/`)

**Purpose**: Generate interactive charts (Plotly)

**Patterns**:
- Return `go.Figure` objects - NEVER auto-display
- Caller controls rendering (.show(), st.plotly_chart(), .write_html())
- Three implemented: plot_equity_curve, plot_signal, plot_drawdown
- Visualizer class for theme management

**Example**:
```python
fig = plot_equity_curve(pnl, show_drawdown_shading=True)
# fig.show()  # Caller decides when/how to render
```

**Constraints**:
- No imports from data/models/backtest/evaluation
- Accepts generic DataFrames only
- Testable without visual rendering

#### Persistence (`persistence/`)

**Purpose**: File I/O with automatic directory creation

**Patterns**:
- Parquet for time series data (with column/date filtering)
- JSON for metadata (UTF-8, indent=2)
- Automatic parent directory creation

**Example**:
```python
save_parquet(df, "data/processed/signal.parquet")
df = load_parquet("data/processed/signal.parquet", columns=["spread"], start_date="2024-01-01")
save_json(metadata, "data/workflows/run_123/metadata.json")
```

**Constraints**:
- Files only (no databases)
- Local filesystem (no cloud storage)
- Snappy compression default

#### Reporting (`reporting/`)

**Purpose**: Multi-format report generation

**Patterns**:
- Aggregates from Suitability and Performance registries
- Supports console, markdown, HTML formats
- No computation - read-only registry access

**Example**:
```python
report = generate_report(signal_name="spread_momentum", strategy_name="balanced", format="markdown")
```

---

## Feature Scaffold Guide

### Adding a New Signal

**Files to create/modify**:
1. Add compute function to `src/aponyx/models/signals.py`
2. Add metadata entry to `src/aponyx/models/signal_catalog.json`
3. Add tests to `tests/models/test_signals.py`

**Compute function template**:
```python
def compute_my_signal(
    cdx_df: pd.DataFrame,  # Required data
    vix_df: pd.DataFrame,  # Optional additional data
    config: SignalConfig,
) -> pd.Series:
    """
    Compute my_signal based on CDX and VIX divergence.
    
    Signal Convention
    -----------------
    Positive values → Long credit risk (buy CDX)
    Negative values → Short credit risk (sell CDX)
    
    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with 'spread' column
    vix_df : pd.DataFrame
        VIX level data with 'level' column
    config : SignalConfig
        Signal parameters (lookback, min_periods)
    
    Returns
    -------
    pd.Series
        Z-score normalized signal values
    """
    # Compute raw signal
    cdx_z = (cdx_df["spread"] - cdx_df["spread"].rolling(config.lookback).mean()) / cdx_df["spread"].rolling(config.lookback).std()
    vix_z = (vix_df["level"] - vix_df["level"].rolling(config.lookback).mean()) / vix_df["level"].rolling(config.lookback).std()
    
    raw_signal = cdx_z - vix_z  # Example: credit stress vs equity stress gap
    
    # Z-score normalize
    signal_mean = raw_signal.rolling(config.lookback, min_periods=config.min_periods).mean()
    signal_std = raw_signal.rolling(config.lookback, min_periods=config.min_periods).std()
    
    return (raw_signal - signal_mean) / signal_std
```

**Catalog entry template**:
```json
{
  "name": "my_signal",
  "description": "CDX-VIX divergence signal",
  "compute_function_name": "compute_my_signal",
  "data_requirements": {
    "cdx": "spread",
    "vix": "level"
  },
  "arg_mapping": ["cdx", "vix"],
  "enabled": true
}
```

### Adding a New Backtest Strategy

**Files to modify**:
1. `src/aponyx/backtest/strategy_catalog.json`

**Catalog entry template**:
```json
{
  "name": "my_strategy",
  "description": "Custom threshold configuration",
  "entry_threshold": 2.0,
  "exit_threshold": 1.0,
  "enabled": true
}
```

### Adding a New Data Provider

**Files to create**:
1. `src/aponyx/data/providers/my_provider.py`
2. `src/aponyx/data/sources.py` (add DataSource class)
3. `tests/data/providers/test_my_provider.py`

**Provider template**:
```python
# In sources.py
@dataclass(frozen=True)
class MySource:
    endpoint: str
    api_key: str | None = None

# In providers/my_provider.py
def fetch_from_my_source(
    source: MySource,
    instrument: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Fetch data from my custom provider."""
    # Implementation...
    return df  # Must have DatetimeIndex

# Register in resolve_provider factory in sources.py
def resolve_provider(source: DataSource) -> Any:
    if isinstance(source, MySource):
        from .providers.my_provider import fetch_from_my_source
        return fetch_from_my_source
    # ... existing providers
```

### Adding a New Workflow Step

**Files to modify**:
1. `src/aponyx/workflows/concrete_steps.py` (add step class)
2. `src/aponyx/workflows/registry.py` (register in StepRegistry)

**Step template**:
```python
class MyStep(WorkflowStep):
    @property
    def name(self) -> str:
        return "my_step"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute custom step logic."""
        # Access previous step outputs
        signal = context["signal"]["signal"]
        
        # Your logic here
        my_output = process_signal(signal)
        
        # Save output
        output_dir = context["output_dir"]
        save_parquet(my_output, output_dir / "my_step" / "result.parquet")
        
        return {"my_output": my_output}
    
    def output_exists(self) -> bool:
        """Check if step output already exists."""
        return (self.output_dir / "my_step" / "result.parquet").exists()
    
    def load_cached_output(self) -> dict[str, Any]:
        """Load previously computed output."""
        my_output = load_parquet(self.output_dir / "my_step" / "result.parquet")
        return {"my_output": my_output}

# In StepRegistry.get_all_steps(), add to step list at appropriate position
```

---

## Integration Rules

### 1. Signal Sign Convention

**REQUIRED**: All signals MUST follow this convention:
- **Positive values** → Long credit risk (buy CDX = sell protection)
- **Negative values** → Short credit risk (sell CDX = buy protection)

**Signal naming convention:**

Use consistent signal names throughout the models layer:
- **Signal names:** `cdx_etf_basis`, `cdx_vix_gap`, `spread_momentum`
- **Function names:** `compute_cdx_etf_basis`, `compute_cdx_vix_gap`, `compute_spread_momentum`
- **Function parameters:** `cdx_etf_basis`, `cdx_vix_gap`, `spread_momentum`
- **DataFrame columns:** `cdx_etf_basis`, `cdx_vix_gap`, `spread_momentum`

**Implementation guidelines:**
- When creating new signals, verify the sign matches this convention
- Use consistent signal names across functions, parameters, and configuration
- Document signal interpretation clearly in docstrings
- Use negation (`-`) when raw calculations naturally produce inverse signs
- Test signal directionality with simple synthetic data

**Implementation**:
```python
# For signals where tightening spreads = bullish
momentum = -(spread_change / spread_vol)  # Negate so tightening = positive

# Z-score normalize (preserves sign)
signal = (momentum - momentum.rolling(lookback).mean()) / momentum.rolling(lookback).std()
```

### 2. Registry Pattern

**REQUIRED**: Use registries for extensibility:

| Registry | Type | Location | Purpose |
|----------|------|----------|---------|
| SignalRegistry | Static | src/aponyx/models/signal_catalog.json | Signal definitions |
| StrategyRegistry | Static | src/aponyx/backtest/strategy_catalog.json | Strategy configs |
| DataRegistry | Runtime | data/.registries/registry.json | Dataset tracking |
| SuitabilityRegistry | Runtime | data/.registries/suitability.json | Evaluation results |
| PerformanceRegistry | Runtime | data/.registries/performance.json | Performance analysis |

**Pattern**:
```python
# Fail-fast validation on load
class MyRegistry:
    def __init__(self, catalog_path: Path):
        self._items: dict[str, Metadata] = {}
        self._load_catalog()
        self._validate_catalog()  # Validates ALL entries upfront

# Frozen metadata
@dataclass(frozen=True)
class MyMetadata:
    name: str
    enabled: bool = True
    
    def __post_init__(self) -> None:
        """Validate constraints."""
        if invalid_condition:
            raise ValueError("Constraint violated")
```

### 3. Provider Pattern

**REQUIRED**: Use DataSource protocol for data loading:

```python
# Define source
source = FileSource("data/raw/cdx.parquet")
# OR
source = BloombergSource()

# Fetch via unified interface
cdx_df = fetch_cdx(source, security="cdx_ig_5y")
```

**DO NOT**:
```python
# ❌ Direct file loading
df = pd.read_parquet("data/raw/cdx.parquet")

# ❌ String-based provider identification
df = fetch_cdx(provider="file", path="...")
```

### 4. Workflow Context Sharing

**REQUIRED**: Steps communicate via context dict:

```python
# Step N produces output
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    return {"my_output": result}

# Step N+1 consumes it
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    prev_output = context["step_name"]["my_output"]
```

### 5. Frozen Dataclass Configs

**REQUIRED**: All configs use frozen dataclasses:

```python
@dataclass(frozen=True)
class MyConfig:
    param1: float
    param2: int = 10
    
    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.param1 < 0:
            raise ValueError("param1 must be non-negative")
```

### 6. Return Figures, Never Display

**REQUIRED**: Visualization functions return figures:

```python
def plot_my_chart(data: pd.Series) -> go.Figure:
    """Generate chart - caller controls rendering."""
    fig = px.line(x=data.index, y=data.values)
    return fig  # Do NOT call .show()

# Caller decides
fig = plot_my_chart(data)
fig.show()  # OR st.plotly_chart(fig)  OR fig.write_html("chart.html")
```

### 7. Module-Level Loggers

**REQUIRED**: Use module-level loggers, never basicConfig:

```python
import logging
logger = logging.getLogger(__name__)

# INFO for user-facing operations
logger.info("Loaded %d signals from catalog", len(signals))

# DEBUG for implementation details
logger.debug("Cache hit: key=%s", cache_key)
```

**DO NOT**:
```python
# ❌ Never in library code
logging.basicConfig(level=logging.INFO)
```

### 8. Modern Type Hints

**REQUIRED**: Use PEP 604 union syntax and built-in generics:

```python
# ✅ Correct
def process(data: dict[str, Any], filters: list[str] | None = None) -> pd.DataFrame | None:
    ...

# ❌ Do NOT use
from typing import Optional, Union, List, Dict
def process(data: Dict[str, Any], filters: Optional[List[str]] = None) -> Union[pd.DataFrame, None]:
    ...
```

---

## Code Patterns & Conventions

### 1. Function-Based Transformations

```python
# ✅ Prefer pure functions
def compute_z_score(data: pd.Series, window: int) -> pd.Series:
    mean = data.rolling(window).mean()
    std = data.rolling(window).std()
    return (data - mean) / std

# ❌ Avoid classes for simple transformations
class ZScoreCalculator:
    def __init__(self, window: int):
        self.window = window
    def compute(self, data: pd.Series) -> pd.Series:
        ...
```

### 2. Metadata-to-Config Conversion

```python
@dataclass(frozen=True)
class StrategyMetadata:
    name: str
    entry_threshold: float
    exit_threshold: float
    
    def to_config(self, **overrides) -> BacktestConfig:
        """Convert metadata to runtime config with overrides."""
        return BacktestConfig(
            entry_threshold=overrides.get("entry_threshold", self.entry_threshold),
            exit_threshold=overrides.get("exit_threshold", self.exit_threshold),
            position_size=overrides.get("position_size", 10.0),  # Runtime default
        )
```

### 3. Fail-Fast Validation

```python
class SignalRegistry:
    def __init__(self, catalog_path: Path):
        self._signals = {}
        self._load_catalog()
        self._validate_catalog()  # Validate ALL entries on init
    
    def _validate_catalog(self) -> None:
        """Fail immediately if any compute function is missing."""
        for metadata in self._signals.values():
            if not hasattr(signals_module, metadata.compute_function_name):
                raise ValueError(f"Compute function not found: {metadata.compute_function_name}")
```

### 4. Rolling Window Stability

```python
def compute_stability_metrics(signal: pd.Series, target: pd.Series, window: int = 252) -> tuple[float, float]:
    """Compute sign consistency and coefficient of variation."""
    rolling_betas = []
    
    for i in range(window, len(signal)):
        window_signal = signal.iloc[i-window:i]
        window_target = target.iloc[i-window:i]
        beta = compute_regression_stats(window_signal, window_target)["beta"]
        rolling_betas.append(beta)
    
    aggregate_beta = compute_regression_stats(signal, target)["beta"]
    
    # Sign consistency: proportion matching aggregate sign
    sign_consistency = sum(
        1 for b in rolling_betas if (b > 0) == (aggregate_beta > 0)
    ) / len(rolling_betas)
    
    # Coefficient of variation
    beta_cv = np.std(rolling_betas) / abs(np.mean(rolling_betas))
    
    return sign_consistency, beta_cv
```

### 5. DV01-Based P&L

```python
# Long profits when spreads tighten, short profits when spreads widen
pnl = position * (-spread_change) * dv01_per_million * position_size / 1_000_000

# Transaction costs on position changes
if position != prev_position:
    cost = abs(transaction_cost_bps / 10000 * position_size)
else:
    cost = 0.0

net_pnl = pnl - cost
```

### 6. Timestamped Output Directories

```python
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dirname = f"{signal_name}_{strategy_name}_{timestamp}"
output_dir = DATA_WORKFLOWS_DIR / dirname
output_dir.mkdir(parents=True, exist_ok=True)
```

### 7. Cache Checking Pattern

```python
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    # Check cache
    if not self.config.force_rerun and self.output_exists():
        logger.info("Loading cached output for %s", self.name)
        return self.load_cached_output()
    
    # Execute logic
    result = self._compute_result(context)
    
    # Save for next run
    self._save_output(result)
    
    return result
```

### 8. Automatic Directory Creation

```python
def save_parquet(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, compression="snappy", index=True)
    return path
```

### 9. Column and Date Filtering

```python
# Memory-efficient loading
df = load_parquet(
    "data/cache/cdx.parquet",
    columns=["spread"],  # Load only needed columns
    start_date="2024-01-01",  # Filter date range
    end_date="2024-12-31",
)
```

### 10. NumPy-Style Docstrings

```python
def fetch_cdx(
    source: DataSource,
    security: str = "cdx_ig_5y",
    start_date: str | None = None,
    end_date: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Fetch CDX spread data from specified source.
    
    Parameters
    ----------
    source : DataSource
        Data source (FileSource or BloombergSource).
    security : str, default "cdx_ig_5y"
        Security identifier.
    start_date : str or None, optional
        Start date in YYYY-MM-DD format.
    end_date : str or None, optional
        End date in YYYY-MM-DD format.
    use_cache : bool, default True
        Whether to use cached data if available.
    
    Returns
    -------
    pd.DataFrame
        CDX spread data with DatetimeIndex and 'spread' column.
    
    Raises
    ------
    ValidationError
        If schema validation fails.
    
    Examples
    --------
    >>> source = FileSource("data/raw/cdx.parquet")
    >>> df = fetch_cdx(source, security="cdx_ig_5y")
    >>> df.head()
    """
    # Implementation...
```

---

## Example Prompts

### Example 1: Create a New Signal

**User Prompt**:
> "Create a signal that compares CDX spread percentile rank to VIX percentile rank over a 60-day window"

**Expected AI Response**:

1. Add compute function to `src/aponyx/models/signals.py`:
```python
def compute_cdx_vix_percentile_gap(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    config: SignalConfig,
) -> pd.Series:
    """
    Compute gap between CDX and VIX percentile ranks.
    
    Signal Convention
    -----------------
    Positive values → Long credit risk (CDX relatively cheap)
    Negative values → Short credit risk (CDX relatively expensive)
    """
    window = 60
    
    # Percentile ranks
    cdx_pct = cdx_df["spread"].rolling(window).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1]
    )
    vix_pct = vix_df["level"].rolling(window).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1]
    )
    
    # Gap: CDX high percentile + VIX low percentile = positive signal
    gap = cdx_pct - vix_pct
    
    # Z-score normalize
    gap_mean = gap.rolling(config.lookback, min_periods=config.min_periods).mean()
    gap_std = gap.rolling(config.lookback, min_periods=config.min_periods).std()
    
    return (gap - gap_mean) / gap_std
```

2. Add catalog entry to `src/aponyx/models/signal_catalog.json`:
```json
{
  "name": "cdx_vix_percentile_gap",
  "description": "Gap between CDX and VIX percentile ranks",
  "compute_function_name": "compute_cdx_vix_percentile_gap",
  "data_requirements": {
    "cdx": "spread",
    "vix": "level"
  },
  "arg_mapping": ["cdx", "vix"],
  "enabled": true
}
```

3. Add test to `tests/models/test_signals.py`:
```python
def test_compute_cdx_vix_percentile_gap():
    """Test CDX-VIX percentile gap signal computation."""
    cdx_df = generate_sample_cdx(n_obs=252)
    vix_df = generate_sample_vix(n_obs=252)
    config = SignalConfig(lookback=20, min_periods=10)
    
    signal = compute_cdx_vix_percentile_gap(cdx_df, vix_df, config)
    
    # Validate
    assert isinstance(signal, pd.Series)
    assert len(signal) == len(cdx_df)
    assert signal.name is not None
    
    # Check for NaN handling
    valid_signal = signal.dropna()
    assert len(valid_signal) > 0
    
    # Check sign convention (spot check)
    assert signal.dtype == np.float64
```

### Example 2: Add a Workflow Step

**User Prompt**:
> "Add a workflow step that generates a correlation matrix between signals"

**Expected AI Response**:

1. Add step class to `src/aponyx/workflows/concrete_steps.py`:
```python
class CorrelationStep(WorkflowStep):
    """Compute correlation matrix between signals."""
    
    @property
    def name(self) -> str:
        return "correlation"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Compute correlation matrix from signals."""
        logger.info("Computing signal correlation matrix")
        
        # Extract signals from context
        signals_dict = context["signal"]["signals"]
        
        # Create DataFrame from signals
        signals_df = pd.DataFrame(signals_dict)
        
        # Compute correlation
        corr_matrix = signals_df.corr()
        
        # Save to output directory
        output_dir = context["output_dir"]
        corr_path = output_dir / "correlation" / "matrix.parquet"
        save_parquet(corr_matrix, corr_path)
        
        logger.info("Saved correlation matrix: %s", corr_path)
        
        return {"correlation_matrix": corr_matrix}
    
    def output_exists(self) -> bool:
        """Check if correlation matrix exists."""
        corr_path = self.output_dir / "correlation" / "matrix.parquet"
        return corr_path.exists()
    
    def load_cached_output(self) -> dict[str, Any]:
        """Load cached correlation matrix."""
        corr_path = self.output_dir / "correlation" / "matrix.parquet"
        corr_matrix = load_parquet(corr_path)
        return {"correlation_matrix": corr_matrix}
```

2. Register in `src/aponyx/workflows/registry.py`:
```python
class StepRegistry:
    def get_all_steps(self, config: WorkflowConfig) -> list[WorkflowStep]:
        """Get all workflow steps in dependency order."""
        return [
            DataStep(config),
            SignalStep(config),
            CorrelationStep(config),  # Add after SignalStep
            SuitabilityStep(config),
            BacktestStep(config),
            PerformanceStep(config),
            VisualizationStep(config),
        ]
```

### Example 3: Run Workflow from CLI

**User Prompt**:
> "Run the spread_momentum signal with the balanced strategy using Bloomberg data"

**Expected AI Command**:
```bash
aponyx run --signal spread_momentum --strategy balanced --data bloomberg
```

### Example 4: Generate Report

**User Prompt**:
> "Generate a markdown report for the cdx_etf_basis signal with aggressive strategy"

**Expected AI Command**:
```bash
aponyx report --signal cdx_etf_basis --strategy aggressive --format markdown
```

---

## Git Commit Standards

Follow **Conventional Commits** format for consistency and automated changelog generation:

### Format
```
<type>: <description>

[optional body]
```

### Rules
- **Type**: Lowercase, from the list below
- **Description**: Capitalize first letter, no period at end, imperative mood ("Add" not "Added")
- **Length**: Keep first line under 72 characters
- **Body**: Optional, explain *why* not *what*, wrap at 72 characters

### Types
- `feat`: New feature or capability
- `fix`: Bug fix or correction
- `docs`: Documentation changes only
- `refactor`: Code restructuring without behavior change
- `test`: Adding or updating tests
- `perf`: Performance improvement
- `chore`: Maintenance (dependencies, tooling, config)
- `style`: Formatting, missing semicolons (not CSS)

### Examples

✅ **Good:**
```
feat: Add VIX-CDX divergence signal computation

Implements z-score normalized gap between equity vol and credit spreads
to identify cross-asset risk sentiment divergence.
```

```
refactor: Extract data loading to separate module

Improves modularity and testability by separating I/O from computation.
```

```
docs: Update persistence layer documentation
```

❌ **Bad:**
```
Added new feature
```

```
Fix: bug in backtest
```

```
update docs.
```

### Multi-file Commits
When changing multiple files, use the most significant type and describe the overall change:
```
refactor: Modernize type hints to modern Python syntax

- Update copilot instructions with new standards
- Add comprehensive Python guidelines document
- Remove legacy Optional/Union usage examples
```

---

## Prohibited Patterns

### ❌ DO NOT Use These Patterns

1. **Old-Style Type Hints**:
```python
from typing import Optional, Union, List, Dict
def func(x: Optional[int]) -> Union[str, None]:  # ❌ Wrong
    ...
```

2. **Classes for Simple Transformations**:
```python
class DataProcessor:  # ❌ Wrong - use pure function
    def __init__(self, window: int):
        self.window = window
    def process(self, data: pd.Series) -> pd.Series:
        return data.rolling(self.window).mean()
```

3. **Auto-Display in Visualization**:
```python
def plot_chart(data: pd.Series) -> None:  # ❌ Wrong
    fig = px.line(data)
    fig.show()  # Don't auto-display
```

4. **Direct File Paths Instead of Provider Pattern**:
```python
df = pd.read_parquet("data/raw/cdx.parquet")  # ❌ Wrong
# Use: fetch_cdx(FileSource("data/raw/cdx.parquet"))
```

5. **Mutable Config Objects**:
```python
@dataclass  # ❌ Wrong - missing frozen=True
class MyConfig:
    param: int
```

6. **String-Based Provider Identification**:
```python
fetch_data(provider="file", path="...")  # ❌ Wrong
# Use: fetch_data(FileSource("..."))
```

7. **logging.basicConfig() in Library Code**:
```python
import logging
logging.basicConfig(level=logging.INFO)  # ❌ Wrong - library shouldn't configure logging
```

---

## Quick Reference

### File Naming Conventions
- Python modules: lowercase with underscores (`my_module.py`)
- Test files: `test_` prefix (`test_my_module.py`)
- Config dataclasses: `MyConfig` in `config.py`
- JSON catalogs: `{domain}_catalog.json` (e.g., `signal_catalog.json`)

### Import Organization
```python
# Standard library
import logging
from pathlib import Path
from typing import Any

# Third-party
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Local
from aponyx.config import DATA_DIR
from aponyx.models import compute_signal
```

### Logging Levels
- **INFO**: User-facing operations (`Loaded 10 signals`, `Workflow complete`)
- **DEBUG**: Implementation details (`Cache hit`, `Resolved provider`)
- **WARNING**: Recoverable issues (`Missing optional column`)
- **ERROR**: Failures (`Step failed`, `Validation error`)

### Registry Locations
- **Static** (in src/, version controlled): Signal, Strategy, Bloomberg configs
- **Runtime** (in data/.registries/, ignored by git): Data, Suitability, Performance

### Key Constants (from config/__init__.py)
- `PROJECT_ROOT`: Project root directory
- `DATA_DIR`: `data/` directory
- `CACHE_DIR`: `data/cache/`
- `DATA_WORKFLOWS_DIR`: `data/workflows/`
- `SIGNAL_CATALOG_PATH`: `src/aponyx/models/signal_catalog.json`
- `STRATEGY_CATALOG_PATH`: `src/aponyx/backtest/strategy_catalog.json`

---

*This instruction file is auto-generated from codebase analysis. All patterns are based on actual implementation, not invented best practices.*

**Last Updated**: November 22, 2025  
**Version**: 0.1.11  
**Maintainer**: stabilefrisur
