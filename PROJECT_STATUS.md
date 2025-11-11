# Project Status — aponyx

**Last Updated:** November 9, 2025  
**Version:** 0.1.7  
**Maintainer:** stabilefrisur

---

## Quick Reference

| Property | Value |
|----------|-------|
| **Project Type** | Systematic fixed-income research framework |
| **Primary Focus** | CDX overlay tactical credit strategies |
| **Python Version** | 3.12 (modern syntax, no legacy compatibility) |
| **Environment Manager** | `uv` |
| **Maturity Level** | Early-stage research framework |
| **License** | MIT |

**Core Dependencies:**
- `pandas>=2.2.0`, `numpy>=2.0.0`, `pyarrow>=17.0.0`

**Optional Dependencies:**
- `bloomberg`: `xbbg>=0.7.0` (Bloomberg Terminal integration)
- `viz`: `plotly>=5.24.0`, `streamlit>=1.39.0` (visualization)
- `dev`: `pytest>=8.0.0`, `ruff>=0.6.0`, `black>=24.0.0`, `mypy>=1.11.0` (development tools)

---

## Project Purpose

aponyx is a **systematic fixed-income research framework** for developing and backtesting tactical credit strategies. The project centers on a **CDX overlay pilot strategy** that exploits temporary dislocations in liquid credit indices to generate short-term tactical alpha.

**Core Investment Objectives:**
- Generate short-term tactical alpha (holding period: days to weeks)
- Provide liquidity hedge and modest convexity enhancement
- Maintain capital efficiency through derivatives overlay
- Create uncorrelated returns to slower-moving core credit allocation

**Research Philosophy:**
- Prioritize **signal evaluation independence** over premature signal combination
- Each signal backtested individually to establish clear performance attribution
- Reproducible research with deterministic outputs and metadata logging
- Modular architecture separating strategy logic from infrastructure

---

## Architecture Overview

The project implements a **strict layered architecture** with functional boundaries:

```
src/aponyx/
  __init__.py         # Package initialization with version
  main.py             # CLI entry point (placeholder)
  py.typed            # PEP 561 type marker for mypy
  
  config/             # Paths, constants, defaults
    __init__.py       # PROJECT_ROOT, DATA_DIR, CACHE_ENABLED, SIGNAL_CATALOG_PATH, STRATEGY_CATALOG_PATH, etc.
  
  data/               # Load, validate, transform market data
    __init__.py       # Exports: fetch_*, *Source, validate_*, DataRegistry
    fetch.py          # Unified fetch interface
    sources.py        # DataSource protocol and types
    validation.py     # Schema validation functions
    schemas.py        # Schema dataclasses
    cache.py          # TTL-based caching layer
    registry.py       # Data registry management
    sample_data.py    # Synthetic data generation
    bloomberg_config.py         # Bloomberg ticker registry
    bloomberg_securities.json   # Security metadata
    bloomberg_instruments.json  # Instrument definitions
    providers/
      __init__.py
      file.py         # File-based provider
      bloomberg.py    # Bloomberg Terminal provider
  
  models/             # Signal generation and strategy logic
    __init__.py       # Exports: compute_*, SignalConfig, SignalRegistry
    signals.py        # Signal computation functions (3 signals)
    registry.py       # Signal registry and metadata
    catalog.py        # Batch computation orchestration
    config.py         # SignalConfig dataclass
    signal_catalog.json  # Signal metadata catalog
  
  backtest/           # Simulation, P&L tracking, metrics
    __init__.py       # Exports: BacktestConfig, run_backtest, StrategyRegistry, etc.
    engine.py         # Core backtest engine
    metrics.py        # Performance calculations
    config.py         # BacktestConfig dataclass
    protocols.py      # BacktestEngine, PerformanceCalculator
    registry.py       # Strategy registry and metadata
    adapters.py       # Third-party library adapters (stubs)
    strategy_catalog.json  # Strategy metadata catalog
  
  evaluation/         # Signal screening and performance analysis
    suitability/      # Pre-backtest signal-product evaluation
      __init__.py     # Exports: evaluate_signal_suitability, SuitabilityRegistry, etc.
      evaluator.py    # Core evaluation orchestration
      tests.py        # Statistical tests
      scoring.py      # Component scoring
      report.py       # Markdown report generation
      registry.py     # Evaluation registry
      config.py       # SuitabilityConfig dataclass
      suitability_registry.json  # Evaluation tracking catalog
    performance/      # Post-backtest performance analysis
      __init__.py     # Exports: analyze_backtest_performance, PerformanceRegistry, etc.
      analyzer.py     # Core performance evaluation
      decomposition.py  # Return attribution
      risk_metrics.py   # Extended metrics
      report.py         # Markdown report generation
      registry.py       # Performance registry
      config.py         # PerformanceConfig dataclass
      performance_registry.json  # Performance tracking catalog
  
  visualization/      # Plotly charts, Streamlit dashboards
    __init__.py       # Exports: plot_*, Visualizer
    plots.py          # Plotting functions (3 implemented, 3 stubs)
    visualizer.py     # Theme management
    app.py            # Streamlit dashboard (stub)
  
  persistence/        # Parquet/JSON I/O utilities
    __init__.py       # Exports: save_*, load_*
    parquet_io.py     # Parquet read/write
    json_io.py        # JSON read/write
```

### Layer Responsibilities

| Layer | Purpose | Can Import From | Cannot Import From |
|-------|---------|-----------------|-------------------|
| **data/** | Data loading, cleaning, validation | `config`, `persistence` | `models`, `backtest`, `evaluation`, `visualization` |
| **models/** | Signal computation | `config`, `data` (schemas only) | `backtest`, `evaluation`, `visualization` |
| **evaluation/** | Signal screening and performance analysis | `config`, `backtest`, `persistence` | `data` (direct), `models`, `visualization` |
| **backtest/** | P&L simulation, metrics | `config`, `models` (protocols) | `data` (direct), `evaluation`, `visualization` |
| **visualization/** | Charts, dashboards | None (accepts generic DataFrames) | `data`, `models`, `backtest`, `evaluation` |
| **persistence/** | I/O operations | `config` | All others |
| **config/** | Constants, paths | None | All |

**Design Principles:**
1. **Modularity:** Layers are decoupled; data layer knows nothing about strategy logic
2. **Reproducibility:** Deterministic outputs with seed control and metadata logging
3. **Type Safety:** Strict type hints using modern Python syntax (`str | None`, `dict[str, Any]`)
4. **Simplicity:** Functions over classes; `@dataclass` for data containers
5. **Transparency:** Clear separation of strategy logic from infrastructure

---

## Implementation Status

### ✅ Data Layer (`src/aponyx/data/`)

**Implemented:**
- **Provider Pattern:** Abstract `DataSource` protocol with multiple implementations
  - `FileSource` - Local Parquet/CSV files (frozen dataclass for configuration)
  - `BloombergSource` - Bloomberg Terminal via xbbg (frozen dataclass for configuration)
  - Provider logic implemented as functions in `providers/` directory
- **Unified Fetch Interface:** Three fetch functions with provider abstraction
  - `fetch_cdx` - CDX index spreads with security filtering
  - `fetch_vix` - VIX volatility index
  - `fetch_etf` - Credit ETF prices with security filtering
- **Schema Validation:** Comprehensive validation for all data types
  - `validate_cdx_schema` - CDX spread validation (0-10000 bps range)
  - `validate_vix_schema` - VIX level validation (0-200 range)
  - `validate_etf_schema` - ETF price validation
  - Schema dataclasses in `schemas.py` define constraints
- **TTL-Based Caching:** Simple time-based cache with Parquet storage
  - `DataCache` class with get/save operations
  - Cache key generation from fetch parameters
  - Staleness checking based on TTL (default: 1 day)
  - Automatic cache directory management
- **Data Registry:** Metadata tracking with JSON persistence
  - `DataRegistry` class for dataset cataloging
  - Automatic registration on cache save
  - Query and lookup capabilities
- **Sample Data Generation:** Deterministic test data with fixed seeds
  - `generate_sample_cdx` - Synthetic CDX spreads
  - `generate_sample_vix` - Synthetic VIX levels
  - `generate_sample_etf` - Synthetic ETF prices
- **Bloomberg Integration:** 
  - JSON-based ticker registry (`bloomberg_securities.json`, `bloomberg_instruments.json`)
  - Security-to-ticker mapping via `get_bloomberg_ticker`
  - Registry validation utilities
  - Provider implementation in `providers/bloomberg.py`
- **File Provider:** Local file support in `providers/file.py`
  - Parquet and CSV format support
  - Date range filtering
  - Instrument-based file organization

**Key Features:**
- Provider resolution and factory pattern (`resolve_provider`)
- Comprehensive logging at INFO and DEBUG levels
- Optional caching with `use_cache` parameter (default: enabled)
- Forward-fill for missing dates in alignment
- Duplicate date detection and warnings
- Security filtering for multi-security DataFrames

**Configuration:**
- Cache enabled by default (`CACHE_ENABLED = True`)
- 1-day TTL for market data (`CACHE_TTL_DAYS = 1`)
- Data directory structure: `data/raw/`, `data/processed/`, `data/cache/`
- Registry path: `data/registry.json` (from `config.REGISTRY_PATH`)
- Signal catalog path: `src/aponyx/models/signal_catalog.json` (from `config.SIGNAL_CATALOG_PATH`)
- Strategy catalog path: `src/aponyx/backtest/strategy_catalog.json` (from `config.STRATEGY_CATALOG_PATH`)
- Bloomberg config paths: `src/aponyx/data/bloomberg_securities.json`, `bloomberg_instruments.json`
- DataRegistry lives in data layer (`src/aponyx/data/registry.py`)
- SignalRegistry lives in models layer (`src/aponyx/models/registry.py`)
- StrategyRegistry lives in backtest layer (`src/aponyx/backtest/registry.py`)

**Requirements:**
- Bloomberg integration is optional (install with `pip install aponyx[bloomberg]`)
- Requires active Bloomberg Terminal session when using BloombergSource
- xbbg wrapper included in optional `bloomberg` dependencies

**Implementation Notes:**
- `APISource` dataclass is defined but not yet used by any provider
- Database integration not included (files only by design)
- Authentication/authorization handled externally
- Real-time data streaming not supported

### ✅ Models Layer (`src/aponyx/models/`)

**Implemented:**
- **Three Pilot Signals:**
  - `compute_cdx_etf_basis` - Flow-driven mispricing from CDX-ETF basis
    - Z-score normalized basis over rolling window
    - Captures temporary dislocations from ETF flows
    - Assumes ETF spread-equivalent conversion done externally
    - Positive = CDX cheap vs ETF (long CDX)
  - `compute_cdx_vix_gap` - Cross-asset risk sentiment divergence
    - Compares CDX vs VIX deviations from rolling means
    - Normalized gap captures stress divergence
    - Positive = credit stress outpacing equity stress (long CDX)
  - `compute_spread_momentum` - Short-term continuation in spreads
    - Volatility-adjusted momentum over lookback period
    - Negated so tightening spreads give positive signal
    - Positive = tightening momentum (bullish credit)
- **Signal Registry Pattern:**
  - `SignalRegistry` class - JSON catalog management
  - `SignalMetadata` dataclass - Signal metadata container
  - JSON-based catalog (`signal_catalog.json`) with signal definitions
  - Enable/disable signals via catalog without code changes
  - Data requirements validation
  - Dynamic function resolution
- **Batch Signal Computation:**
  - `compute_registered_signals` - Orchestration of all enabled signals
  - Validates data requirements before computation
  - Returns dict mapping signal names to Series
  - Comprehensive error handling and logging
- **Signal Catalog Management:**
  - `SignalCatalog` module - Registry operations and utilities
  - Catalog save/load with JSON persistence
  - Metadata query and filtering
  - Arg mapping for flexible function signatures
- **Configuration:**
  - `SignalConfig` dataclass with validation
  - Configurable lookback window (default: 20 days)
  - Configurable min_periods (default: 10 days)
  - Frozen dataclass for immutability

**Key Features:**
- **Signal Sign Convention:** All signals follow consistent sign convention
  - Positive values → Long credit risk → Buy CDX (sell protection)
  - Negative values → Short credit risk → Sell CDX (buy protection)
- **Z-Score Normalization:** All signals use rolling z-scores for regime independence
- **Forward-Fill Alignment:** Missing data handled via forward-fill before computation
- **Comprehensive Logging:** INFO for operations, DEBUG for implementation details
- **Type Safety:** Full type hints with modern Python syntax
- **Extensibility:** Add new signals by editing JSON + implementing compute function

**Signal Catalog Structure:**
```json
{
  "name": "signal_name",
  "description": "Human-readable description",
  "compute_function_name": "compute_function_name",
  "data_requirements": {"cdx": "spread", "etf": "spread"},
  "arg_mapping": ["cdx", "etf"],
  "enabled": true
}
```

**Key Files:**
- `signals.py` - Signal computation functions (3 signals)
- `registry.py` - Signal registry and metadata management
- `catalog.py` - Batch computation and orchestration
- `config.py` - Signal configuration dataclass
- `signal_catalog.json` - Signal metadata catalog (3 entries)

**Validation:**
- Data requirements checked before computation
- Required columns validated against DataFrame schemas
- Compute function existence verified at runtime
- Duplicate signal names prevented in catalog

**Implementation Notes:**
- Research framework only (not for real-time signal generation)
- Transparent rules-based signals (no ML models)
- No external signal feeds or APIs

### ✅ Evaluation Layer (`src/aponyx/evaluation/`)

**Implemented:**
- **Suitability Evaluation Framework:** Pre-backtest quality gate for signal-product relationships
  - `evaluate_signal_suitability` - Core evaluation orchestration
  - `SuitabilityResult` dataclass - Comprehensive evaluation output (13+ fields)
  - `SuitabilityConfig` - Configuration with validation (frozen dataclass)
- **Four-Component Scoring:**
  - `score_data_health` - Sample size and missing data assessment (20% weight)
  - `score_predictive` - Multi-lag correlation and regression (40% weight)
  - `score_economic` - Effect size relevance in basis points (20% weight)
  - `score_stability` - Sign consistency across subperiods (20% weight)
- **Statistical Tests:**
  - `compute_correlation` - Pearson correlation calculation
  - `compute_regression_stats` - OLS with beta, t-stat, p-value
  - `compute_subperiod_betas` - Temporal stability analysis (2-way split)
  - `check_sign_consistency` - Binary stability test
- **Report Generation:**
  - `generate_suitability_report` - Markdown template rendering
  - `save_report` - File persistence with timestamp
  - Decision interpretation (PASS/HOLD/FAIL) with visual indicators
- **Suitability Registry:**
  - `SuitabilityRegistry` - Class-based JSON catalog management
  - `EvaluationEntry` - Metadata record dataclass
  - CRUD operations: register, get, list (with filters), remove

**Decision Thresholds:**
- **PASS** (≥ 0.7): Proceed to backtest
- **HOLD** (0.4-0.7): Marginal, requires manual review
- **FAIL** (< 0.4): Do not backtest

**Key Files:**
- `evaluator.py` - Core evaluation orchestration
- `tests.py` - Statistical test functions
- `scoring.py` - Component scoring logic
- `report.py` - Markdown report generation
- `registry.py` - Suitability registry management
- `config.py` - SuitabilityConfig dataclass
- `suitability_registry.json` - Evaluation tracking catalog

**Configuration:**
- Default lags: [1, 3, 5]
- Component weights: data_health=0.2, predictive=0.4, economic=0.2, stability=0.2
- Pass threshold: 0.7, Hold threshold: 0.4
- Minimum observations: 252 (default)
- Registry path: `src/aponyx/evaluation/suitability/suitability_registry.json`

**Implementation Notes:**
- Standalone pre-backtest assessment (no trading rules or costs)
- Uses statsmodels for OLS regression
- Registry pattern consistent with SignalRegistry and StrategyRegistry
- Comprehensive test coverage (6 test modules)

### ✅ Evaluation Layer (`src/aponyx/evaluation/`)

**Implemented:**
- **Suitability Evaluation Framework:** Pre-backtest quality gate for signal-product relationships
  - `evaluate_signal_suitability` - Core evaluation orchestration
  - `SuitabilityResult` dataclass - Comprehensive evaluation output (13+ fields)
  - `SuitabilityConfig` - Configuration with validation (frozen dataclass)
- **Four-Component Scoring:**
  - `score_data_health` - Sample size and missing data assessment (20% weight)
  - `score_predictive` - Multi-lag correlation and regression (40% weight)
  - `score_economic` - Effect size relevance in basis points (20% weight)
  - `score_stability` - Sign consistency across subperiods (20% weight)
- **Suitability Registry:**
  - `SuitabilityRegistry` - Class-based JSON catalog management
  - `EvaluationEntry` - Metadata record dataclass
  - CRUD operations: register, get, list (with filters), remove
- **Performance Evaluation Framework:** Post-backtest comprehensive analysis
  - `analyze_backtest_performance` - Core performance orchestration
  - `PerformanceResult` dataclass - Extended metrics and attribution
  - `PerformanceConfig` - Configuration with validation (frozen dataclass)
- **Extended Performance Metrics:**
  - Rolling Sharpe analysis with configurable window
  - Profit factor and tail ratio calculation
  - Consistency score across time periods
  - Drawdown recovery analysis
  - Subperiod stability assessment (configurable n_subperiods)
- **Return Attribution:**
  - Directional attribution (long vs short P&L)
  - Signal strength attribution (quantile-based decomposition)
  - Win/loss decomposition with contribution percentages
- **Performance Registry:**
  - `PerformanceRegistry` - Class-based JSON catalog management
  - `PerformanceEntry` - Metadata record dataclass
  - CRUD operations: register, get, list, comprehensive metadata tracking
- **Report Generation:**
  - `generate_performance_report` - Markdown template rendering
  - `save_report` - File persistence with timestamp
  - Comprehensive metrics summary and stability analysis
  - Attribution breakdown with visual formatting

**Key Features:**
- **Suitability:** Pre-backtest signal screening with PASS/HOLD/FAIL decisions
- **Performance:** Post-backtest comprehensive analysis with extended metrics
- **Statistical Tests:** Correlation, regression, subperiod stability, sign consistency
- **Attribution:** Directional, signal strength, and win/loss decomposition
- **Registry Pattern:** Consistent governance across both evaluation types
- **Comprehensive Logging:** INFO for operations, DEBUG for implementation details
- **Type Safety:** Full type hints with modern Python syntax

**Decision Thresholds (Suitability):**
- **PASS** (≥ 0.7): Proceed to backtest
- **HOLD** (0.4-0.7): Marginal, requires manual review
- **FAIL** (< 0.4): Do not backtest

**Performance Metrics:**
- Stability score (0-1 scale)
- Profit factor (gross wins / gross losses)
- Tail ratio (95th / 5th percentile returns)
- Rolling Sharpe (mean and std of rolling window)
- Consistency score (% of positive subperiods)
- Average recovery days from drawdowns
- Drawdown count and duration analysis

**Key Files:**
- **Suitability:**
  - `suitability/evaluator.py` - Core evaluation orchestration
  - `suitability/tests.py` - Statistical test functions
  - `suitability/scoring.py` - Component scoring logic
  - `suitability/report.py` - Markdown report generation
  - `suitability/registry.py` - Suitability registry management
  - `suitability/config.py` - SuitabilityConfig dataclass
  - `suitability/suitability_registry.json` - Evaluation tracking catalog
- **Performance:**
  - `performance/analyzer.py` - Core performance evaluation
  - `performance/decomposition.py` - Return attribution logic
  - `performance/risk_metrics.py` - Extended metric calculations
  - `performance/report.py` - Markdown report generation
  - `performance/registry.py` - Performance registry management
  - `performance/config.py` - PerformanceConfig dataclass
  - `performance/performance_registry.json` - Performance tracking catalog

**Configuration:**
- **Suitability:**
  - Default lags: [1, 3, 5]
  - Component weights: data_health=0.2, predictive=0.4, economic=0.2, stability=0.2
  - Pass threshold: 0.7, Hold threshold: 0.4
  - Minimum observations: 252 (default)
  - Registry path: `src/aponyx/evaluation/suitability/suitability_registry.json`
- **Performance:**
  - Minimum observations: 252 (default)
  - Subperiods: 4 (quarterly analysis)
  - Rolling window: 63 days (3 months)
  - Attribution quantiles: 3 (terciles)
  - Risk-free rate: 0.0
  - Registry path: `src/aponyx/evaluation/performance/performance_registry.json`

**Implementation Notes:**
- Standalone evaluation modules (no trading rules or execution logic)
- Uses statsmodels for OLS regression and statistical tests
- Registry pattern consistent with SignalRegistry and StrategyRegistry
- Comprehensive test coverage in `tests/evaluation/`
- Reports saved to `reports/suitability/` and `reports/performance/`

### ✅ Backtest Layer (`src/aponyx/backtest/`)

**Implemented:**
- **Core Backtesting Engine:**
  - `run_backtest` - Position generation and P&L simulation
  - `BacktestResult` dataclass - Structured output container
  - Metadata logging with timestamps and parameters
  - Comprehensive INFO and DEBUG logging
- **Configuration:**
  - `BacktestConfig` dataclass with validation
  - Entry/exit threshold hysteresis to reduce turnover
  - Binary position sizing (on/off) for pilot
  - Transaction cost modeling (bps-based)
  - Optional max holding period constraint
  - DV01-based P&L calculation
- **Strategy Registry Pattern:**
  - `StrategyRegistry` class - JSON catalog management for backtest strategies
  - `StrategyMetadata` dataclass - Strategy metadata container (frozen)
  - JSON-based catalog (`strategy_catalog.json`) with 4 strategies
  - Enable/disable strategies via catalog without code changes
  - Metadata-to-config conversion via `to_config()` method
  - Fail-fast validation at load time (entry > exit threshold)
- **Performance Metrics:**
  - `compute_performance_metrics` - Comprehensive statistics
  - `PerformanceMetrics` dataclass - 13 metrics including:
    - Risk-adjusted returns: Sharpe, Sortino, Calmar ratios
    - Drawdown analysis: Max drawdown, drawdown duration
    - Return statistics: Total, annualized, volatility
    - Trade statistics: Hit rate, win/loss ratios, avg holding days
  - Annualization assumes 252 trading days
  - Zero risk-free rate for simplicity
- **Protocol-Based Design:**
  - `BacktestEngine` protocol for extensibility
  - `PerformanceCalculator` protocol for metrics
  - Adapter stubs for vectorbt and quantstats integration (commented)
  - Clean separation of engine logic from external libraries
- **Position Logic:**
  - Long position (sell protection) when signal > entry_threshold
  - Short position (buy protection) when signal < -entry_threshold
  - Exit when |signal| < exit_threshold or max_holding_days reached
  - Position tracking with days_held counter
- **P&L Calculation:**
  - DV01-based spread P&L calculation
  - Transaction costs on entry and exit
  - Cumulative P&L tracking
  - Proper accounting on exit day (captures final P&L before flattening)

**Key Features:**
- Deterministic backtest execution
- Entry/exit threshold hysteresis prevents whipsaw
- Transaction costs applied symmetrically
- Metadata logged for reproducibility
- Trade-level statistics with P&L aggregation
- Comprehensive validation of input data (DatetimeIndex checks)

**Key Files:**
- `engine.py` - Core backtest engine and result container
- `metrics.py` - Performance calculations
- `config.py` - Configuration dataclass with validation
- `protocols.py` - Type protocols for extensibility
- `registry.py` - Strategy registry and metadata management
- `strategy_catalog.json` - Strategy metadata catalog (4 entries)
- `adapters.py` - Stubs for third-party library integration

**Current Limitations:**
- Binary position sizing only (no notional scaling by signal strength)
- Single-asset backtests (no multi-asset portfolio support)
- No slippage modeling beyond transaction costs
- No position limits or risk constraints
- Real-time trading integration not supported
- Production risk management not included
- Order execution simulation not implemented

### ✅ Persistence Layer (`src/aponyx/persistence/`)

**Implemented:**
- **Parquet I/O:**
  - `save_parquet` - DataFrame to Parquet with automatic directory creation
  - `load_parquet` - Parquet to DataFrame with optional column/date filtering
  - `list_parquet_files` - Directory scanning for Parquet files
  - Column filtering for selective reads (reduces memory)
  - Date range filtering for time-series slicing
- **JSON I/O:**
  - `save_json` - Dictionary/list to JSON with pretty-printing (indent=2)
  - `load_json` - JSON to Python objects
  - UTF-8 encoding by default
  - Automatic directory creation
- **Comprehensive Logging:**
  - Module-level loggers in all modules
  - INFO: File operations (saved, loaded, rows, path)
  - DEBUG: Performance details (columns filtered, date range)
  - %-style formatting for log messages

**Key Features:**
- **Simple File-Based Design:** No database dependencies, just Parquet + JSON
- **Type Safety:** Full type hints with modern Python syntax
- **Automatic Path Handling:** Creates parent directories as needed
- **Selective Loading:** Column and date filtering reduces memory footprint
- **Metadata Tracking:** Rich metadata via DataRegistry in data layer

**Key Files:**
- `parquet_io.py` - Parquet read/write operations
- `json_io.py` - JSON read/write operations

**Configuration:**
- Data directory: `data/` (from `config.DATA_DIR`)
- Automatic directory initialization on config module import

**Implementation Notes:**
- Parquet/JSON only (no database backends)
- Local files only (no cloud storage integration)
- Uses Parquet default compression
- Simple append-only design (no versioning or schema evolution)

### ✅ Visualization Layer (`src/aponyx/visualization/`)

**Implemented:**
- Core plotting functions (returns Plotly `Figure` objects):
  - `plot_equity_curve` - Cumulative P&L chart with optional drawdown shading
  - `plot_signal` - Signal time series with threshold lines
  - `plot_drawdown` - Underwater chart (peak-to-trough decline)
- `Visualizer` class for theme management and styling
- Returns Plotly `Figure` objects (no auto-display; caller controls rendering)

**Key Features:**
- Interactive charts with hover tooltips and zoom controls
- Supports Jupyter, Streamlit, HTML export, and testing
- Consistent visual styling via `Visualizer` class
- All functions include comprehensive logging at INFO and DEBUG levels

**Implementation Status:**
- Three functions fully implemented: `plot_equity_curve`, `plot_signal`, `plot_drawdown`
- Six functions are stubs that raise `NotImplementedError`:
  - In `plots.py`: `plot_attribution`, `plot_exposures`, `plot_dashboard`
  - In `visualizer.py`: `attribution()`, `exposures()`, `dashboard()` (wrapper methods)
- Streamlit dashboard (`app.py`) contains only placeholder comments
- Real-time data visualization not supported
- Interactive parameter tuning UI not implemented

**Key Files:**
- `plots.py` - Plotting functions (3 implemented, 3 stubs)
- `visualizer.py` - Theme and style management
- `app.py` - Streamlit dashboard (stub)

### ✅ Testing (`tests/`)

**Implemented:**
- Unit tests for all layers:
  - `tests/data/` - Data validation and loading
  - `tests/models/` - Signal computation, registry, catalog
  - `tests/backtest/` - Engine and metrics
  - `tests/governance/` - Strategy registry, integration tests
  - `tests/persistence/` - I/O operations and registry
  - `tests/visualization/` - Plotting functions
- Deterministic test data with fixed seeds
- Pytest configuration with coverage tracking
- Comprehensive test coverage

**Testing Philosophy:**
- Test API contracts (return types, shapes, edge cases)
- Test determinism (same input → same output with fixed seeds)
- Test calculations (z-scores, P&L, metrics)
- Test error handling (missing columns, empty data)
- Do NOT test visual rendering or external services

### ✅ Documentation (`src/aponyx/docs/`, `src/aponyx/notebooks/`)

**Implemented:**
- Comprehensive design documents (9 files in `src/aponyx/docs/`):
  - `cdx_overlay_strategy.md` - Investment strategy and signal definitions
  - `python_guidelines.md` - Code standards and best practices
  - `logging_design.md` - Logging conventions and metadata
  - `signal_registry_usage.md` - Signal management workflow
  - `signal_suitability_evaluation.md` - Pre-backtest evaluation framework
  - `performance_evaluation_design.md` - Post-backtest analysis framework
  - `visualization_design.md` - Chart architecture
  - `caching_design.md` - Cache layer architecture
  - `adding_data_providers.md` - Provider extension guide
  - `documentation_structure.md` - Single source of truth principles
  - `governance_design.md` - Strategy registry and governance pattern
  - `project_setup_process.md` - Project setup and installation
- Research workflow notebooks (`src/aponyx/notebooks/`):
  - `01_data_download.ipynb` - Bloomberg data acquisition (23 cells, complete)
  - `02_signal_computation.ipynb` - Signal generation workflow (21 cells, complete)
  - `03_suitability_evaluation.ipynb` - Pre-backtest screening (25 cells, complete)
  - `04_backtest_execution.ipynb` - Backtest execution (9 cells, execution-only)
  - `05_performance_analysis.ipynb` - Post-backtest performance analysis (13 cells, complete)
  - `06_single_signal_template.ipynb` - End-to-end single-signal research template (29 cells, complete)
- NumPy-style docstrings throughout codebase
- Copilot instructions for AI-assisted development (`.github/copilot-instructions.md`)

**Documentation Structure (Single Source of Truth):**
- **API Reference:** Module docstrings
- **Quickstart:** `README.md`
- **Design Docs:** `src/aponyx/docs/*.md` (included in PyPI distribution)
- **Notebooks:** `src/aponyx/notebooks/*.ipynb` (included in PyPI distribution)

**Notebook Conventions:**
- Use absolute imports (`from aponyx.config import...`)
- Include workflow context headers (position, prerequisites, outputs)
- Format tables with `to_markdown()` for clean left-aligned display
- Each notebook works in isolation, loading from previous steps
- Only ✅ and ❌ emojis for clarity (no decorative emojis)

---

## Design Patterns and Conventions

### 1. Signal Sign Convention

**All model signals follow consistent sign convention:**
- **Positive signal values** → Long credit risk → Buy CDX (sell protection)
- **Negative signal values** → Short credit risk → Sell CDX (buy protection)

**Rationale:** Ensures clear interpretation when evaluating signals individually or comparing performance across different signal ideas.

**Implementation:** See `src/aponyx/models/signals.py` for examples.

### 2. Signal Registry Pattern

Signals are managed via **JSON catalog** + **compute function registry**:

**Files:**
- `src/aponyx/models/signal_catalog.json` - Signal metadata
- `src/aponyx/models/registry.py` - Registry implementation
- `src/aponyx/models/catalog.py` - Catalog management

**Benefits:**
- Add new signals by editing JSON + implementing compute function
- No code changes to batch computation logic
- Easy enable/disable for experiments
- Clear metadata and data requirements

**Usage:**
```python
registry = SignalRegistry("src/aponyx/models/signal_catalog.json")
signals = compute_registered_signals(registry, market_data, config)
```

### 3. Strategy Registry Pattern

Backtest strategies are managed via **JSON catalog** + **strategy metadata registry**:

**Files:**
- `src/aponyx/backtest/strategy_catalog.json` - Strategy metadata (4 strategies)
- `src/aponyx/backtest/registry.py` - Registry implementation
- `src/aponyx/config/__init__.py` - STRATEGY_CATALOG_PATH constant

**Benefits:**
- Define multiple threshold configurations without code changes
- Enable/disable strategies for comparative evaluation
- Clean separation of strategy parameters from backtest engine
- Consistent pattern with signal registry
- Convert metadata to BacktestConfig via `to_config()` method

**Current Strategies:**
- `conservative` - Entry: 2.0, Exit: 1.0 (low turnover, high conviction)
- `balanced` - Entry: 1.5, Exit: 0.75 (moderate turnover)
- `aggressive` - Entry: 1.0, Exit: 0.5 (high turnover)
- `experimental` - Entry: 0.75, Exit: 0.25 (disabled by default)

**Usage:**
```python
from aponyx.backtest import StrategyRegistry
from aponyx.config import STRATEGY_CATALOG_PATH

registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
metadata = registry.get_metadata("balanced")
config = metadata.to_config(position_size=15.0)  # Override defaults
```

**Implementation Details:**
- `StrategyMetadata` dataclass with frozen=True for immutability
- Fail-fast validation: entry_threshold > exit_threshold checked at load time
- Enable/disable strategies via catalog without code changes
- Comprehensive unit tests in `tests/governance/test_strategy_registry.py`

### 4. Provider Pattern for Data Sources

**Abstract `DataSource` protocol** supports multiple providers:

**Files:**
- `src/aponyx/data/sources.py` - Protocol definition
- `src/aponyx/data/providers/file.py` - File implementation
- `src/aponyx/data/providers/bloomberg.py` - Bloomberg Terminal implementation

**Current Implementations:**
- ✅ `FileSource` - Local Parquet/CSV files
- ✅ `BloombergSource` - Bloomberg Terminal via xbbg (requires active session)

**Example:**
```python
# File-based
source = FileSource("data/raw/cdx_data.parquet")
cdx_df = fetch_cdx(source, security="cdx_ig_5y")

# Bloomberg Terminal
source = BloombergSource()
cdx_df = fetch_cdx(source, security="cdx_ig_5y")
```

### 5. Functions Over Classes

**Default to pure functions** for transformations, calculations, and data processing.

**Only use classes for:**
1. State management (`DataRegistry`, connection pools)
2. Multiple related methods on shared state
3. Lifecycle management (context managers)
4. Plugin/interface patterns (base classes)

**Use `@dataclass` for data containers:**
- `SignalConfig` - Signal parameters
- `BacktestConfig` - Backtest configuration
- `BacktestResult` - Backtest outputs
- `PerformanceMetrics` - Performance statistics

**Files demonstrating this pattern:**
- `src/aponyx/models/signals.py` - Pure functions for signal computation
- `src/aponyx/backtest/config.py` - Dataclass configurations
- `src/aponyx/backtest/engine.py` - Functional backtest logic

### 6. Logging Standards

**Module-level loggers:**
```python
import logging
logger = logging.getLogger(__name__)
```

**%-formatting (not f-strings):**
```python
logger.info("Loaded %d rows from %s", len(df), path)
```

**Levels:**
- **INFO:** User-facing operations (file loaded, backtest started)
- **DEBUG:** Implementation details (filter applied, cache hit)
- **WARNING:** Recoverable errors (missing optional column)

**Never in library code:**
```python
logging.basicConfig(...)  # User's responsibility, not library's
```

**Examples:** See any module in `src/aponyx/` for consistent logging patterns.

### 7. Type Hints (Modern Python Syntax)

**Use built-in generics and union syntax:**
```python
def process_data(
    data: dict[str, Any],
    filters: list[str] | None = None,
    threshold: int | float = 0.0,
) -> pd.DataFrame | None:
    ...
```

**Avoid old syntax:**
```python
# ❌ Don't use: Optional, Union, List, Dict
from typing import Optional, Union, List, Dict
```

**Files:** All modules in `src/aponyx/` use modern type syntax.

---

## Data Flow and Workflow

**Typical Research Workflow:**

```
1. Data Loading
   FileSource("data/raw/cdx.parquet")
   OR BloombergSource()
   → fetch_cdx(source, security="cdx_ig_5y")
   → validate_cdx_schema(df)
   → Cache to data/cache/{provider}/{instrument}_{key}.parquet
   → Register in data/registry.json
   → Returns: pd.DataFrame with DatetimeIndex

2. Signal Generation
   SignalRegistry("src/aponyx/models/signal_catalog.json")
   → Load enabled signals from catalog
   → Validate data requirements
   → compute_registered_signals(registry, market_data, config)
     → compute_cdx_etf_basis(cdx_df, etf_df, config)
     → compute_cdx_vix_gap(cdx_df, vix_df, config)
     → compute_spread_momentum(cdx_df, config)
   → Returns: dict[str, pd.Series] of z-score normalized signals

3. Signal-Product Suitability (optional pre-backtest gate)
   SuitabilityConfig(lags=[1, 3, 5], min_obs=252)
   → evaluate_signal_suitability(signal, target, config)
     → Compute 4-component scores (data/predictive/economic/stability)
     → Assign decision (PASS/HOLD/FAIL)
     → Generate markdown report
   → SuitabilityRegistry.register_evaluation(result, signal_id, product_id)
   → Returns: SuitabilityResult with decision and scores
   → If FAIL: Archive signal, skip backtest

4. Backtesting (per signal that passes evaluation)
   BacktestConfig(
     entry_threshold=1.5,
     exit_threshold=0.75,
     position_size=10.0,
     transaction_cost_bps=1.0,
     max_holding_days=None,
     dv01_per_million=4750.0
   )
   → run_backtest(signal, spread, config)
     → Generate positions (long/short/flat)
     → Calculate spread P&L via DV01
     → Apply transaction costs
     → Track metadata
   → Returns: BacktestResult(positions, pnl, metadata)

5. Basic Performance Metrics
   compute_performance_metrics(result.pnl, result.positions)
   → Calculate 13 metrics:
     - Sharpe, Sortino, Calmar ratios
     - Max drawdown, total return
     - Hit rate, win/loss ratios
     - Trade statistics
   → Returns: PerformanceMetrics dataclass

6. Visualization
   plot_equity_curve(result.pnl["cumulative_pnl"])
   plot_signal(signal, threshold_lines=[-1.5, 1.5])
   plot_drawdown(result.pnl["net_pnl"])
   → Returns: plotly.graph_objects.Figure
   → Caller renders: .show() or st.plotly_chart()

7. Results Persistence
   save_json(result.metadata, "logs/run_metadata.json")
   save_parquet(result.pnl, "data/processed/backtest_pnl.parquet")
   DataRegistry.register_dataset(...)
```

**Data Dependencies:**

```
market_data: dict[str, pd.DataFrame]
├─ "cdx": DataFrame with DatetimeIndex
│   ├─ spread (float, bps)
│   └─ security (str, optional)
├─ "vix": DataFrame with DatetimeIndex
│   └─ level (float, index value)
└─ "etf": DataFrame with DatetimeIndex
    ├─ spread (float, spread-equivalent)
    └─ security (str, optional)

↓ (passed to signal registry)

signals: dict[str, pd.Series]
├─ "cdx_etf_basis": z-score normalized signal
├─ "cdx_vix_gap": z-score normalized signal
└─ "spread_momentum": z-score normalized signal

↓ (evaluated individually)

BacktestResult for each signal
├─ positions: DataFrame (date index)
│   ├─ signal (float, signal value)
│   ├─ position (int, +1/0/-1)
│   ├─ days_held (int)
│   └─ spread (float, spread level)
├─ pnl: DataFrame (date index)
│   ├─ spread_pnl (float, P&L from spread changes)
│   ├─ cost (float, transaction costs)
│   ├─ net_pnl (float, total P&L)
│   └─ cumulative_pnl (float, running total)
└─ metadata: dict
    ├─ timestamp (str, ISO format)
    ├─ config (dict, BacktestConfig values)
    └─ summary (dict, trade count, total P&L, etc.)

↓ (analyzed)

PerformanceMetrics (dataclass)
├─ sharpe_ratio, sortino_ratio, calmar_ratio (float)
├─ max_drawdown, total_return, annualized_return (float)
├─ annualized_volatility, hit_rate (float)
├─ avg_win, avg_loss, win_loss_ratio (float)
└─ n_trades, avg_holding_days (int/float)
```

**Key Files:**
- Data loading: `src/aponyx/data/fetch.py`, `src/aponyx/data/providers/`
- Signal generation: `src/aponyx/models/catalog.py`, `src/aponyx/models/signals.py`
- Backtesting: `src/aponyx/backtest/engine.py`
- Metrics: `src/aponyx/backtest/metrics.py`
- Visualization: `src/aponyx/visualization/plots.py`
- Persistence: `src/aponyx/persistence/parquet_io.py`, `src/aponyx/persistence/json_io.py`

---

## Notable Design Decisions

### 1. No Backward Compatibility

**Decision:** Use modern Python syntax without legacy support.

**Rationale:**
- Early-stage project allows adopting best practices immediately
- No legacy cruft or deprecated patterns
- Cleaner, more readable code

**Impact:** Use `str | None` not `Optional[str]`, `dict[str, Any]` not `Dict[str, Any]`, etc.

### 2. Files Only (No Databases)

**Decision:** Parquet/JSON only; no SQL, MongoDB, or other databases.

**Rationale:**
- Simplicity for research workflows
- Version control friendly (Parquet files in git LFS)
- No server dependencies
- Sufficient for pilot strategy data volumes

**Impact:** All persistence via `src/aponyx/persistence/parquet_io.py` and `json_io.py`.

### 3. Independent Signal Evaluation

**Decision:** Each signal backtested individually before combination.

**Rationale:**
- Establish clear performance attribution
- Understand signal behavior in isolation
- Avoid premature optimization through signal blending
- Enable apples-to-apples comparison on same backtest config

**Impact:** `compute_registered_signals` returns dict of signals; each evaluated separately.

### 4. Return Figures, Don't Display

**Decision:** Visualization functions return `plotly.graph_objects.Figure` without auto-display.

**Rationale:**
- Works in Jupyter, Streamlit, HTML export, testing
- Caller controls rendering context (`.show()`, `st.plotly_chart()`, `.write_html()`)
- Enables post-processing (annotations, subplot composition)
- Testable without rendering (check figure structure, not visuals)

**Impact:** User must call `.show()` or `st.plotly_chart()` explicitly. See `src/aponyx/visualization/plots.py`.

**Implementation Details:**
- All plot functions return `go.Figure` objects
- No side effects (no auto-display, no file writing)
- Consistent interface across all plotting functions
- Enables unit testing of plot generation logic

### 5. TTL-Based Caching (Not LRU)

**Decision:** Simple time-based cache expiration, no size limits or LRU eviction.

**Rationale:**
- Predictable behavior for research workflows
- No complex invalidation logic (staleness via TTL only)
- Manual cleanup acceptable for single-user research
- Simple implementation with file modification times

**Impact:** Cache grows until manual cleanup; no automatic eviction. See `src/aponyx/data/cache.py`.

**Implementation Details:**
- Cache key generated from fetch parameters (hash-based)
- Staleness checked via file modification time
- Default TTL: 1 day (`CACHE_TTL_DAYS = 1`)
- Cache directory structure: `data/cache/{provider}/{instrument}_{key}.parquet`
- Optional cache registration in data registry

### 6. No Authentication in Library

**Decision:** No credential management, API keys, or auth logic in library code.

**Rationale:**
- Connections established outside project (Bloomberg Terminal, APIs)
- Library assumes authenticated data access
- Security handled at infrastructure level

**Impact:** Providers accept connection parameters but don't implement auth.

### 7. Module-Level Loggers (Never `basicConfig`)

**Decision:** Use `logger = logging.getLogger(__name__)` in all modules; never call `logging.basicConfig()`.

**Rationale:**
- Library shouldn't force logging configuration on users
- Hierarchical logger names enable fine-grained control
- Works cleanly with pytest (no spurious output)

**Impact:** Applications configure logging, library uses module loggers. See `src/aponyx/docs/logging_design.md`.

---

## Reproducibility and Metadata

**All stochastic operations use fixed seeds:**
```python
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
```

**All backtest runs include comprehensive metadata:**
```python
metadata = {
    "timestamp": datetime.now().isoformat(),
    "version": __version__,  # From aponyx.__version__
    "config": {
        "entry_threshold": config.entry_threshold,
        "exit_threshold": config.exit_threshold,
        "position_size": config.position_size,
        "transaction_cost_bps": config.transaction_cost_bps,
        "max_holding_days": config.max_holding_days,
        "dv01_per_million": config.dv01_per_million,
    },
    "summary": {
        "start_date": str(aligned.index[0]),
        "end_date": str(aligned.index[-1]),
        "total_days": len(aligned),
        "n_trades": int(n_trades),
        "total_pnl": float(total_pnl),
        "avg_pnl_per_trade": float(avg_pnl_per_trade),
    },
}
```

**Metadata persistence:**
```python
# Save backtest metadata
save_json(result.metadata, "logs/run_metadata.json")

# Register cached datasets
registry.register_dataset(
    name=f"cache_{instrument}_{cache_key}",
    file_path=cache_path,
    instrument=instrument,
    metadata={
        "provider": provider,
        "cached_at": datetime.now().isoformat(),
        "cache_key": cache_key,
        "params": params,
    },
)
```

**Version tracking:**
- Package version available via `aponyx.__version__`
- Retrieved from package metadata via `importlib.metadata.version("aponyx")`
- Included in all backtest metadata for reproducibility

**Files:**
- Sample data with fixed seeds: `src/aponyx/data/sample_data.py`
- Metadata logging: `src/aponyx/backtest/engine.py`
- Metadata I/O: `src/aponyx/persistence/json_io.py`
- Registry management: `src/aponyx/data/registry.py`, `src/aponyx/data/cache.py`
- Version tracking: `src/aponyx/__init__.py`

---

## Repository Structure

```
aponyx/
├── src/aponyx/              # Main package
│   ├── __init__.py          # Package initialization with version
│   ├── main.py              # CLI entry point (placeholder)
│   ├── py.typed             # PEP 561 type marker for mypy
│   ├── config/              # Constants and configuration
│   │   └── __init__.py      # PROJECT_ROOT, DATA_DIR, CACHE_ENABLED, etc.
│   ├── data/                # Data loading, validation, caching
│   │   ├── __init__.py
│   │   ├── fetch.py         # Unified fetch interface
│   │   ├── sources.py       # DataSource protocol
│   │   ├── validation.py    # Schema validation
│   │   ├── schemas.py       # Schema dataclasses
│   │   ├── cache.py         # TTL-based caching
│   │   ├── registry.py      # Data registry management
│   │   ├── sample_data.py   # Synthetic data generation
│   │   ├── bloomberg_config.py           # Ticker registry
│   │   ├── bloomberg_securities.json     # Security metadata
│   │   ├── bloomberg_instruments.json    # Instrument definitions
│   │   └── providers/       # Provider implementations
│   │       ├── __init__.py
│   │       ├── file.py      # File-based provider
│   │       └── bloomberg.py # Bloomberg Terminal provider
│   ├── models/              # Signal generation
│   │   ├── __init__.py
│   │   ├── signals.py       # Signal computation functions
│   │   ├── registry.py      # Signal registry
│   │   ├── catalog.py       # Batch computation
│   │   ├── config.py        # SignalConfig
│   │   └── signal_catalog.json  # Signal metadata
│   ├── backtest/            # Backtesting engine
│   │   ├── __init__.py
│   │   ├── engine.py        # Core backtest engine
│   │   ├── metrics.py       # Performance calculations
│   │   ├── config.py        # BacktestConfig
│   │   ├── protocols.py     # Type protocols
│   │   ├── registry.py      # Strategy registry
│   │   ├── strategy_catalog.json  # Strategy metadata
│   │   └── adapters.py      # Third-party library adapters (stubs)
│   ├── evaluation/          # Signal screening and performance analysis
│   │   ├── suitability/     # Pre-backtest evaluation
│   │   │   ├── __init__.py
│   │   │   ├── evaluator.py
│   │   │   ├── tests.py
│   │   │   ├── scoring.py
│   │   │   ├── report.py
│   │   │   ├── registry.py
│   │   │   ├── config.py
│   │   │   └── suitability_registry.json
│   │   └── performance/     # Post-backtest analysis
│   │       ├── __init__.py
│   │       ├── analyzer.py
│   │       ├── decomposition.py
│   │       ├── risk_metrics.py
│   │       ├── report.py
│   │       ├── registry.py
│   │       ├── config.py
│   │       └── performance_registry.json
│   ├── visualization/       # Plotting and dashboards
│   │   ├── __init__.py
│   │   ├── plots.py         # Plotting functions
│   │   ├── visualizer.py    # Theme management
│   │   └── app.py           # Streamlit dashboard (stub)
│   ├── persistence/         # I/O and registry
│   │   ├── __init__.py
│   │   ├── parquet_io.py    # Parquet read/write
│   │   └── json_io.py       # JSON read/write
│   └── notebooks/           # Research workflow notebooks
│       ├── 01_data_download.ipynb
│       ├── 02_signal_computation.ipynb
│       ├── 03_suitability_evaluation.ipynb
│       ├── 04_backtest_execution.ipynb
│       └── 05_performance_analysis.ipynb
│
├── tests/                   # Unit tests (mirrors src/ structure)
│   ├── data/
│   ├── models/
│   ├── backtest/
│   ├── persistence/
│   └── visualization/
│
├── src/aponyx/
│   ├── docs/                    # Design documentation (included in package)
│   │   ├── cdx_overlay_strategy.md       # Investment strategy
│   │   ├── python_guidelines.md          # Code standards
│   │   ├── logging_design.md             # Logging conventions
│   │   ├── signal_registry_usage.md      # Signal management
│   │   ├── visualization_design.md       # Chart architecture
│   │   ├── caching_design.md             # Cache layer
│   │   ├── adding_data_providers.md      # Provider extension
│   │   ├── documentation_structure.md    # Doc principles
│   │   ├── governance_design.md          # Governance patterns
│   │   ├── project_setup_process.md      # Setup guide
│   │   ├── maintenance/         # Advanced workflows
│   │   │   ├── MAINTENANCE.md
│   │   │   └── Update-Upstream.ps1
│   │   └── prompts/             # LLM context
│   │       ├── investment strategy.txt
│   │       └── technical implementation.txt
│
├── data/                    # Data storage
│   ├── registry.json        # Dataset registry
│   ├── raw/                 # Source data files
│   ├── processed/           # Transformed data
│   └── cache/               # TTL-based cache
│       ├── bloomberg/
│       └── file/
│
├── logs/                    # Run metadata and logs
│   ├── backtest_metadata.json
│   ├── performance_evaluation_metadata.json
│   ├── signal_computation_metadata.json
│   └── suitability_evaluation_metadata.json
│
├── reports/                 # Generated reports
│   ├── suitability/         # Pre-backtest evaluation reports
│   └── performance/         # Post-backtest analysis reports
│
├── .github/
│   └── copilot-instructions.md  # AI assistant configuration
│
├── pyproject.toml           # Project metadata and dependencies
├── README.md                # Quickstart guide
├── LICENSE                  # MIT license
├── TODO.md                  # Task tracking
├── PROJECT_STATUS.md        # This file
├── CHANGELOG.md             # Version history
├── PYPI_RELEASE_CHECKLIST.md  # Release process
└── project_setup_process.md   # Setup documentation
```

---

## Current Gaps and Stubs

**Visualization Layer:**
- `plot_attribution` - Stub that raises `NotImplementedError`
- `plot_exposures` - Stub that raises `NotImplementedError`
- `plot_dashboard` - Stub that raises `NotImplementedError`
- `app.py` - Streamlit dashboard contains only placeholder comments

**Data Layer:**
- `APISource` dataclass defined in `sources.py` but no provider implementation exists

**Backtest Layer:**
- `adapters.py` contains commented-out stubs for vectorbt and quantstats integration

**Current Limitations:**
- Three signals in catalog (basis, gap, momentum); framework supports adding more
- Binary position sizing only (no scaling by signal strength)
- Single-asset backtesting (no portfolio-level support)
- File-based data only (no API or database providers beyond Bloomberg Terminal)

---

## Context for AI Assistants

This document provides comprehensive context for GPT-based AI assistants working on the aponyx project. When generating code or suggestions:

1. **Respect layer boundaries** - Data layer cannot import from models/backtest
2. **Use modern Python syntax** - `str | None`, `dict[str, Any]`, etc.
3. **Follow signal sign convention** - Positive = long credit risk
4. **Add module-level loggers** - Never use `logging.basicConfig()`
5. **Return figures, don't display** - Let caller control rendering
6. **Use functions over classes** - Default to pure functions
7. **Include type hints** - All function signatures fully typed
8. **Write NumPy-style docstrings** - Parameters, Returns, Notes sections
9. **Add tests for new features** - Deterministic tests with fixed seeds
10. **Log metadata for backtests** - Timestamp, version, config, summary stats

**Key reference files:**
- Architecture: This document (layer table, design patterns)
- Code standards: `.github/copilot-instructions.md`, `src/aponyx/docs/python_guidelines.md`
- Investment context: `src/aponyx/docs/cdx_overlay_strategy.md`
- Signal workflow: `src/aponyx/docs/signal_registry_usage.md`
- Workflows: `src/aponyx/notebooks/*.ipynb` for complete demonstrations

---

**End of Document**
