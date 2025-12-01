# Project Status — aponyx

**Last Updated:** December 1, 2025  
**Version:** 0.1.14 (Post-Legacy-Cleanup)

## Quick Reference

| Property | Value |
|----------|-------|
| **Project Type** | Systematic fixed-income research framework |
| **Primary Focus** | CDX overlay tactical credit strategies |
| **Python Version** | 3.12 (modern syntax, no legacy compatibility) |
| **Environment Manager** | `uv` |
| **Maturity Level** | Early-stage research framework |
| **Breaking Changes** | May occur without deprecation warnings |
| **License** | MIT |
| **Test Coverage** | 681 tests across all layers |

**Core Dependencies:**
- `pandas>=2.0.0`, `numpy>=1.24.0`, `pyarrow>=12.0.0`, `scipy>=1.7.0`, `statsmodels>=0.14.0`, `quantstats>=0.0.77`, `click>=8.1.0`, `pyyaml>=6.0`

**Optional Dependencies:**
- `bloomberg`: `xbbg>=0.7.0` (Bloomberg Terminal integration)
- `viz`: `plotly>=5.24.0`, `streamlit>=1.39.0`, `nbformat>=5.10.0`, `ipykernel>=6.29.0`, `tabulate>=0.9.0`, `jupyter>=1.0.0`, `matplotlib>=3.3.0`, `seaborn>=0.11.0` (visualization)
- `dev`: `pytest>=8.0.0`, `pytest-cov>=5.0.0`, `ruff>=0.6.0`, `black>=24.0.0`, `mypy>=1.11.0`, `pandas-stubs>=2.0.0` (development tools)

---

## Purpose of This Document

This document tracks implementation status and business context for the aponyx project:
- What's implemented vs. stubbed
- Investment strategy rationale (CDX overlay pilot)
- Architecture decisions (why files-only, why independent signals)
- Current system capabilities and limitations

For coding patterns and conventions, see `.github/copilot-instructions.md`.

## Related Documentation

| Question | See |
|----------|-----|
| How to add a new signal? | `.github/copilot-instructions.md` Feature Scaffold Guide |
| What's implemented vs. stubbed? | This document Implementation Status |
| What are the coding standards? | `.github/copilot-instructions.md` Code Patterns |
| Why independent signal evaluation? | This document Notable Design Decisions |
| What's the investment strategy? | `src/aponyx/docs/cdx_overlay_strategy.md` |

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
  
  cli/                # Command-line interface
    __init__.py       # Command exports
    main.py           # CLI entry point with click
    commands/         # Command implementations
      run.py          # Workflow execution command
      report.py       # Report generation command
      list.py         # Catalog browsing command
      clean.py        # Cache management command
  
  workflows/          # Workflow orchestration engine
    __init__.py       # Workflow exports
    engine.py         # WorkflowEngine with caching and dependency tracking
    config.py         # WorkflowConfig dataclass
    steps.py          # WorkflowStep protocol
    concrete_steps.py # Six concrete workflow steps
    registry.py       # Step factory and ordering
  
  reporting/          # Multi-format report generation
    __init__.py       # Reporting exports
    generator.py      # Console/markdown/HTML report generation
  
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
  
  models/             # Indicator, transformation, and signal composition
    __init__.py       # Exports: IndicatorRegistry, TransformationRegistry, SignalRegistry, compose_signal, etc.
    indicators.py     # Indicator computation functions (3 indicators)
    transformations.py  # Transformation functions (z-score, vol adjustment, etc.)
    signal_composer.py  # Signal composition from indicators + transformations
    registry.py       # IndicatorRegistry, TransformationRegistry, SignalRegistry
    metadata.py       # IndicatorMetadata, TransformationMetadata, SignalMetadata dataclasses
    orchestrator.py   # compute_registered_signals batch orchestration
    config.py         # IndicatorConfig, TransformationConfig dataclasses
    indicator_catalog.json      # Indicator metadata catalog (3 indicators)
    transformation_catalog.json # Transformation metadata catalog (4 transformations)
    signal_catalog.json         # Signal metadata catalog (3 signals)
  
  backtest/           # Execution simulation and P&L tracking
    __init__.py       # Exports: BacktestConfig, run_backtest, StrategyRegistry, etc.
    engine.py         # Core backtest engine
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
  
  examples/           # Standalone workflow scripts (included in distribution)
    01_generate_synthetic_data.py  # Synthetic data generation
    02_fetch_data_file.py          # File-based data loading
    03_fetch_data_bloomberg.py     # Bloomberg Terminal fetch
    04_compute_signal.py           # Signal computation
    05_evaluate_suitability.py     # Suitability assessment
    06_run_backtest.py             # Strategy backtesting
    07_analyze_performance.py      # Performance analysis
    08_visualize_results.py        # Results visualization
  
  docs/               # Design documentation (included in distribution)
    cdx_overlay_strategy.md       # Investment strategy
    python_guidelines.md          # Code standards
    logging_design.md             # Logging conventions
    signal_registry_usage.md      # Signal management
    signal_suitability_design.md  # Suitability evaluation
    performance_evaluation_design.md  # Performance analysis
    visualization_design.md       # Chart architecture
    governance_design.md          # Governance patterns
    cli_guide.md                  # CLI user guide
    adding_data_providers.md      # Provider extension
```

### Layer Responsibilities

| Layer | Purpose | Can Import From | Cannot Import From |
|-------|---------|-----------------|-------------------|
| **cli/** | Command-line interface | `workflows`, `reporting`, `config` | Core layers (uses via workflows) |
| **workflows/** | Pipeline orchestration | `data`, `models`, `backtest`, `evaluation`, `visualization`, `reporting`, `persistence`, `config` | `cli` |
| **reporting/** | Report generation | `evaluation`, `persistence`, `config` | `data`, `models`, `backtest`, `visualization` |
| **data/** | Data loading, cleaning, validation | `config`, `persistence` | `models`, `backtest`, `evaluation`, `visualization` |
| **models/** | Signal computation | `config`, `data` (schemas only) | `backtest`, `evaluation`, `visualization` |
| **evaluation/** | Signal screening and performance analysis | `config`, `backtest`, `persistence` | `data` (direct), `models`, `visualization` |
| **backtest/** | P&L simulation, metrics | `config`, `models` (protocols) | `data` (direct), `evaluation`, `visualization` |
| **visualization/** | Charts, dashboards | None (accepts generic DataFrames) | `data`, `models`, `backtest`, `evaluation` |
| **persistence/** | I/O operations | `config` | All others |
| **config/** | Constants, paths | None | All |

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
- Data directory structure: `data/raw/`, `data/workflows/`, `data/cache/`, `data/.registries/`
- Data registry path: `data/.registries/registry.json` (runtime-generated, from `config.REGISTRY_PATH`)
- Signal catalog path: `src/aponyx/models/signal_catalog.json` (static, from `config.SIGNAL_CATALOG_PATH`)
- Strategy catalog path: `src/aponyx/backtest/strategy_catalog.json` (static, from `config.STRATEGY_CATALOG_PATH`)
- Bloomberg config paths: `src/aponyx/data/bloomberg_securities.json`, `bloomberg_instruments.json` (static)
- Suitability registry path: `data/.registries/suitability.json` (runtime-generated, from `config.SUITABILITY_REGISTRY_PATH`)
- Performance registry path: `data/.registries/performance.json` (runtime-generated, from `config.PERFORMANCE_REGISTRY_PATH`)
- **DataRegistry** - Data layer (`src/aponyx/data/registry.py`) - Runtime JSON at `data/.registries/registry.json`
- **SignalRegistry** - Models layer (`src/aponyx/models/registry.py`) - Static catalog at `src/aponyx/models/signal_catalog.json`
- **StrategyRegistry** - Backtest layer (`src/aponyx/backtest/registry.py`) - Static catalog at `src/aponyx/backtest/strategy_catalog.json`
- **SuitabilityRegistry** - Evaluation/suitability layer (`src/aponyx/evaluation/suitability/registry.py`) - Runtime JSON at `data/.registries/suitability.json` (not tracked in git)
- **PerformanceRegistry** - Evaluation/performance layer (`src/aponyx/evaluation/performance/registry.py`) - Runtime JSON at `data/.registries/performance.json` (not tracked in git)

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
- **Indicator-Signal Separation Architecture:**
  - **Indicators** - Reusable market metrics in economically interpretable units (bps, ratios, percentages)
  - **Transformations** - Signal processing operations (z-score normalization, volatility adjustment, etc.)
  - **Signals** - Trading signals composed from indicators + transformations
- **Three Pilot Indicators:**
  - `compute_cdx_etf_spread_diff` - CDX-ETF basis in raw basis points (no normalization)
  - `compute_spread_momentum` - 5-day CDX spread change in basis points
  - `compute_cdx_vix_deviation_gap` - Credit-equity stress gap from 20-day means in bps
- **Three Pilot Signals:**
  - `cdx_etf_basis` - Flow-driven mispricing (indicator: cdx_etf_spread_diff + transformation: z_score_20d)
  - `spread_momentum` - Vol-adjusted momentum (indicator: spread_momentum_5d + transformation: volatility_adjust_20d)
  - `cdx_vix_gap` - Cross-asset sentiment (indicator: cdx_vix_deviation_gap_20d + transformation: z_score_60d)
- **Indicator Registry Pattern:**
  - `IndicatorRegistry` class - JSON catalog management for market indicators
  - `IndicatorMetadata` dataclass - Indicator metadata with output_units, parameters, compute function
  - `compute_indicator` - Orchestration function with caching at `data/cache/indicators/`
  - Catalog at `src/aponyx/models/indicator_catalog.json` (3 indicators)
  - Indicators output economically interpretable values (basis points, ratios, percentages)
- **Transformation Registry Pattern:**
  - `TransformationRegistry` class - JSON catalog of reusable transformations
  - `TransformationMetadata` dataclass - Transformation metadata with transform_type and parameters
  - Four transformations: z_score_20d, z_score_60d, volatility_adjust_20d, diff_5d
  - Catalog at `src/aponyx/models/transformation_catalog.json`
- **Signal Registry Pattern:**
  - `SignalRegistry` class - JSON catalog management for trading signals
  - `SignalMetadata` dataclass - Signal metadata container (NO compute_function_name, data_requirements, or arg_mapping)
  - Signals reference indicators via `indicator_dependencies` field (list of indicator names)
  - Signals reference transformations via `transformations` field (list of transformation names)
  - Schema enforcement: signals MUST have indicator_dependencies and transformations
  - Catalog at `src/aponyx/models/signal_catalog.json` (3 signals)
- **Signal Composition:**
  - `compose_signal` - Orchestrates indicator computation + transformation application
  - `apply_signal_transformation` - Applies cataloged transformations to indicator outputs
  - Support for multi-indicator composition via optional `composition_logic` field
  - Single-indicator signals apply transformations sequentially
- **Batch Signal Computation:**
  - `compute_registered_signals` - Orchestration of all enabled signals
  - Uses indicator + transformation pattern exclusively (no legacy compute functions)
  - Returns dict mapping signal names to Series
  - Comprehensive error handling and logging
- **Configuration:**
  - `IndicatorConfig` dataclass - Indicator parameters with validation
  - `TransformationConfig` dataclass - Transformation parameters with validation
  - All configs frozen for immutability

**Key Features:**
- **Signal Sign Convention:** All signals follow consistent sign convention
  - Positive values → Long credit risk → Buy CDX (sell protection)
  - Negative values → Short credit risk → Sell CDX (buy protection)
- **Indicator Reusability:** Indicators computed once, cached, and reused across multiple signals
- **Economic Interpretability:** Indicators output values in natural units (bps, ratios, percentages) without pre-normalization
- **Transformation Catalog:** Common transformations (z-score, volatility adjustment) cataloged for reuse across signals
- **Clean Architecture:** Complete removal of legacy monolithic signal functions (no compute_cdx_etf_basis, etc.)
- **No Backward Compatibility:** Breaking changes fully implemented, no deprecation warnings
- **Comprehensive Logging:** INFO for operations, DEBUG for implementation details
- **Type Safety:** Full type hints with modern Python syntax
- **Default Securities:** Indicators define default securities in catalog (e.g., cdx_ig_5y, lqd, vix)
- **Security Mapping:** Override defaults via WorkflowConfig.security_mapping

**Signal Catalog Structure (New Pattern):**
```json
{
  "name": "signal_name",
  "description": "Human-readable description",
  "indicator_dependencies": ["indicator_name"],
  "transformations": ["transformation_name"],
  "composition_logic": "optional custom composition for multi-indicator signals",
  "enabled": true,
  "sign_multiplier": 1
}
```

**Indicator Catalog Structure:**
```json
{
  "name": "indicator_name",
  "description": "Market metric description",
  "compute_function_name": "compute_indicator_name",
  "data_requirements": {"cdx": "spread"},
  "default_securities": {"cdx": "cdx_ig_5y"},
  "output_units": "basis_points",
  "parameters": {"lookback": 20},
  "enabled": true
}
```

**Key Files:**
- `indicators.py` - Indicator computation functions (3 indicators)
- `transformations.py` - Transformation functions (z-score, volatility adjustment, etc.)
- `signal_composer.py` - Signal composition from indicators + transformations
- `registry.py` - IndicatorRegistry, TransformationRegistry, SignalRegistry
- `metadata.py` - IndicatorMetadata, TransformationMetadata, SignalMetadata dataclasses
- `orchestrator.py` - compute_registered_signals batch orchestration
- `config.py` - IndicatorConfig, TransformationConfig dataclasses
- `indicator_catalog.json` - Indicator definitions (3 entries)
- `transformation_catalog.json` - Transformation definitions (4 entries)
- `signal_catalog.json` - Signal definitions (3 entries)

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
  - `SuitabilityResult` dataclass - Comprehensive evaluation output (15+ fields)
  - `SuitabilityConfig` - Configuration with validation (frozen dataclass)
- **Four-Component Scoring:**
  - `score_data_health` - Sample size and missing data assessment (20% weight)
  - `score_predictive` - Multi-lag correlation and regression (40% weight)
  - `score_economic` - Effect size relevance in basis points (20% weight)
  - `score_stability` - Dual-metric temporal stability (20% weight)
- **Statistical Tests:**
  - `compute_correlation` - Pearson correlation calculation
  - `compute_regression_stats` - OLS with beta, t-stat, p-value
  - `compute_rolling_betas` - Rolling window regression (252-day default)
  - `compute_stability_metrics` - Sign consistency ratio + coefficient of variation
- **Stability Analysis:**
  - Rolling window approach (default: 252 observations, min: 50)
  - Sign consistency ratio: proportion of windows matching aggregate direction
  - Coefficient of variation: std/mean of rolling betas for magnitude stability
  - Dual-metric scoring: 50% sign (≥0.8 high, ≥0.6 moderate) + 50% CV (<0.5 high, <1.0 moderate)
- **Report Generation:**
  - `generate_suitability_report` - Markdown template rendering
  - `save_report` - File persistence with timestamp
  - Rolling window statistics with interpretation
  - Decision interpretation (PASS/HOLD/FAIL) with visual indicators
- **Suitability Registry:**
  - `SuitabilityRegistry` - Class-based JSON catalog management
  - `EvaluationEntry` - Metadata record dataclass with stability metrics
  - CRUD operations: register, get, list (with filters), remove

**Decision Thresholds:**
- **PASS** (≥ 0.7): Proceed to backtest
- **HOLD** (0.4-0.7): Marginal, requires manual review
- **FAIL** (< 0.4): Do not backtest

**Key Files:**
- `evaluator.py` - Core evaluation orchestration
- `tests.py` - Statistical test functions (rolling window analysis)
- `scoring.py` - Component scoring logic (dual-metric stability)
- `report.py` - Markdown report generation
- `registry.py` - Suitability registry management
- `config.py` - SuitabilityConfig dataclass
- `suitability_registry.json` - Evaluation tracking catalog

**Configuration:**
- Default lags: [1, 3, 5]
- Rolling window: 252 observations (~1 year for daily data)
- Component weights: data_health=0.2, predictive=0.4, economic=0.2, stability=0.2
- Pass threshold: 0.7, Hold threshold: 0.4
- Minimum observations: 500 (default)
- Suitability registry: Runtime JSON (not in version control)
- Performance registry: Runtime JSON (not in version control)

**Implementation Notes:**
- Standalone pre-backtest assessment (no trading rules or costs)
- Uses statsmodels for OLS regression
- Rolling window stability replaces fixed subperiod analysis
- Registry pattern consistent with SignalRegistry and StrategyRegistry
- Comprehensive test coverage (154 tests in evaluation layer)
- Reports saved to workflow-specific directories: `data/workflows/{signal}_{strategy}_{timestamp}/reports/`

### ✅ CLI Layer (`src/aponyx/cli/`)

**Implemented:**
- **Command-Line Interface:**
  - `aponyx run` - Execute complete or partial research workflows
  - `aponyx report` - Generate multi-format analysis reports
  - `aponyx list` - Browse signals, strategies, and datasets
  - `aponyx clean` - Manage workflow cache
- **Configuration:**
  - YAML configuration file support for reproducible workflows
  - CLI argument parsing with click framework
  - Example config files in `examples/` directory
- **Error Handling:**
  - Graceful error messages with exit codes
  - Validation of signal/strategy/product combinations

**Key Features:**
- Single-command execution of 6-step research pipeline
- Output schema: Signal/Strategy/Product/Data/Steps/Force format
- Smart defaults with explicit override options
- Help text with `-h` or `--help` flags
- Integration with workflow engine for orchestration
- Force flag triggers Bloomberg current day refresh (`update_current_day=True`)

**Key Files:**
- `main.py` - CLI entry point and command registration
- `commands/run.py` - Workflow execution command
- `commands/report.py` - Report generation command
- `commands/list.py` - Catalog browsing command
- `commands/clean.py` - Cache management command

**CLI Options:**
- Signal/strategy/product selection
- Data source choice (synthetic/file/bloomberg)
- Step subset execution
- Force re-run flag
- Output format selection (console/markdown/HTML)

**Documentation:**
- Complete CLI user guide (`docs/cli_guide.md`)
- Example YAML configurations in `examples/`

### ✅ Workflows Layer (`src/aponyx/workflows/`)

**Implemented:**
- **Workflow Engine:**
  - `WorkflowEngine` - Sequential pipeline execution with dependency tracking
  - Smart caching with automatic skip of completed steps
  - Force re-run option for cache invalidation
  - Error handling with partial result preservation
- **Configuration:**
  - `WorkflowConfig` - Frozen dataclass for immutable workflow parameters
  - `security_mapping` - Optional dict mapping instrument types to specific securities
  - Step selection (all or subset)
  - Data source configuration
  - Output directory management
- **Step Registry:**
  - `StepRegistry` - Centralized step factory and ordering
  - Protocol-based step abstraction (`WorkflowStep`)
  - Six concrete steps: data, signal, suitability, backtest, performance, visualization
- **Concrete Steps:**
  - Data step - Load and validate market data
  - Signal step - Compute signals from registry
  - Suitability step - Pre-backtest evaluation
  - Backtest step - Execute strategy simulation
  - Performance step - Comprehensive analysis
  - Visualization step - Generate charts

**Key Features:**
- Dependency tracking ensures correct execution order
- Structured logging with progress indicators
- Step completion time tracking
- Output metadata persistence
- Cache validation with timestamp checks

**Key Files:**
- `engine.py` - Core workflow orchestration
- `config.py` - Configuration dataclass
- `steps.py` - WorkflowStep protocol
- `concrete_steps.py` - Step implementations
- `registry.py` - Step factory and ordering

**Workflow Steps:**
1. Data - Load all securities from bloomberg_securities.json (or data source)
2. Signal - Compute signal using default_securities or custom security_mapping
3. Suitability - Evaluate signal-product fit (PASS/HOLD/FAIL)
4. Backtest - Execute strategy with transaction costs on specified product
5. Performance - Extended metrics and attribution analysis
6. Visualization - Generate equity curves and diagnostic charts

**Caching Strategy:**
- Outputs saved to `data/workflows/{signal}_{strategy}_{timestamp}/`
- Simplified filenames: `signal.parquet`, `suitability_evaluation_{timestamp}.md`, `performance_analysis_{timestamp}.md`
- Metadata JSON includes `securities_used` mapping
- Cache files use security-based naming: `{security}_{hash}.parquet`
- Cache hit skips step execution unless `force_rerun=True`
- Partial results preserved on error for debugging

### ✅ Reporting Layer (`src/aponyx/reporting/`)

**Implemented:**
- **Report Generation:**
  - `generate_report()` - Multi-format report aggregation
  - Console reports with formatted tables
  - Markdown reports with embedded visualization links
  - HTML reports with styled formatting
- **Data Aggregation:**
  - Automatic collection from suitability registry
  - Automatic collection from performance registry
  - Signal-strategy-product combination matching
  - Timestamp-based result retrieval
- **Format Support:**
  - Console - Tabulated output with color support
  - Markdown - GitHub-flavored markdown with tables
  - HTML - Styled report with CSS formatting

**Key Features:**
- Single function for all output formats
- Smart data collection from multiple registries
- Comprehensive metrics aggregation
- Visualization reference linking
- Custom output path support

**Key Files:**
- `generator.py` - Core report generation logic

**Report Sections:**
- Suitability Evaluation Summary (4-component scores, decision)
- Performance Analysis Summary (extended metrics, attribution)
- Backtest Statistics (trades, P&L, Sharpe)
- Signal Characteristics (z-score stats, regime analysis)

**Output Locations:**
- Console: stdout
- Markdown: `reports/<signal>_<strategy>_<timestamp>.md`
- HTML: `reports/<signal>_<strategy>_<timestamp>.html` or custom path

### ✅ Evaluation Layer - Performance Analysis (`src/aponyx/evaluation/performance/`)

**Implemented:**
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
  - Suitability registry: Runtime JSON (not in version control)
- **Performance:**
  - Minimum observations: 252 (default)
  - Subperiods: 4 (quarterly analysis)
  - Rolling window: 63 days (3 months)
  - Attribution quantiles: 3 (terciles)
  - Risk-free rate: 0.0
  - Performance registry: Runtime JSON (not in version control)

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
- Comprehensive test coverage across all layers (680 tests total):
  - `tests/backtest/` - 36 tests (engine, P&L, protocols)
  - `tests/cli/` - 83 tests (commands, error handling, integration)
  - `tests/data/` - 223 tests (validation, loading, caching, providers)
  - `tests/evaluation/` - 154 tests (suitability and performance)
  - `tests/governance/` - 19 tests (registry integration)
  - `tests/models/` - 74 tests (signals, registry, catalog)
  - `tests/persistence/` - 27 tests (I/O operations)
  - `tests/reporting/` - 18 tests (report generation)
  - `tests/visualization/` - 19 tests (plotting functions)
  - `tests/workflows/` - 27 tests (engine, steps)
- Deterministic test data with fixed seeds
- Pytest configuration with coverage tracking
- All tests passing (no errors or failures)

**Testing Philosophy:**
- Test API contracts (return types, shapes, edge cases)
- Test determinism (same input → same output with fixed seeds)
- Test calculations (z-scores, P&L, metrics)
- Test error handling (missing columns, empty data)
- Do NOT test visual rendering or external services

### ✅ Documentation (`src/aponyx/docs/`)

**Implemented:**
- Comprehensive design documents (10 files in `src/aponyx/docs/`):
  - `cdx_overlay_strategy.md` - Investment strategy and signal definitions
  - `python_guidelines.md` - Code standards and best practices
  - `logging_design.md` - Logging conventions and metadata
  - `signal_registry_usage.md` - Signal management workflow
  - `signal_suitability_design.md` - Pre-backtest evaluation framework
  - `performance_evaluation_design.md` - Post-backtest analysis framework
  - `visualization_design.md` - Chart architecture
  - `governance_design.md` - Strategy registry and governance pattern
  - `cli_guide.md` - Complete CLI orchestrator reference
  - `adding_data_providers.md` - Provider extension guide
- NumPy-style docstrings throughout codebase
- Copilot instructions for AI-assisted development (`.github/copilot-instructions.md`)

**Documentation Structure (Single Source of Truth):**
- **API Reference:** Module docstrings
- **Quickstart:** `README.md`
- **Design Docs:** `src/aponyx/docs/*.md` (included in PyPI distribution)

---

## Coding Conventions

For implementation patterns, see `.github/copilot-instructions.md`, which documents:
- Signal sign convention (positive = long credit)
- Registry patterns (Signal, Strategy, Data, Suitability, Performance)
- Provider pattern for data sources
- Functions over classes
- Logging standards
- Modern type hints (PEP 604 unions, built-in generics)
- Frozen dataclass configs
- Return figures without auto-display

---

## Data Flow

Data flows through 6 workflow steps: load → signal → suitability → backtest → performance → visualization. Each step produces outputs consumed by subsequent steps. See `.github/copilot-instructions.md` Example Prompts for concrete workflow examples.

---

## Notable Design Decisions

### Files Only (No Databases)

**Decision:** Parquet/JSON only; no SQL, MongoDB, or other databases.

**Rationale:**
- Simplicity for research workflows
- Version control friendly (Parquet files in git LFS)
- No server dependencies
- Sufficient for pilot strategy data volumes

**Impact:** All persistence via `src/aponyx/persistence/parquet_io.py` and `json_io.py`.

### Independent Signal Evaluation

**Decision:** Each signal backtested individually before combination.

**Rationale:**
- Establish clear performance attribution
- Understand signal behavior in isolation
- Avoid premature optimization through signal blending
- Enable apples-to-apples comparison on same backtest config

**Impact:** `compute_registered_signals` returns dict of signals; each evaluated separately.

### No Authentication in Library

**Decision:** No credential management, API keys, or auth logic in library code.

**Rationale:**
- Connections established outside project (Bloomberg Terminal, APIs)
- Library assumes authenticated data access
- Security handled at infrastructure level

**Impact:** Providers accept connection parameters but don't implement auth.

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
│   ├── cli/                 # Command-line interface
│   │   ├── __init__.py
│   │   ├── main.py          # CLI entry point with click
│   │   └── commands/        # Command implementations
│   │       ├── run.py       # Workflow execution
│   │       ├── report.py    # Report generation
│   │       ├── list.py      # Catalog browsing
│   │       └── clean.py     # Cache management
│   ├── workflows/           # Workflow orchestration
│   │   ├── __init__.py
│   │   ├── engine.py        # WorkflowEngine
│   │   ├── config.py        # WorkflowConfig
│   │   ├── steps.py         # WorkflowStep protocol
│   │   ├── concrete_steps.py # Step implementations
│   │   └── registry.py      # Step factory
│   ├── reporting/           # Report generation
│   │   ├── __init__.py
│   │   └── generator.py     # Multi-format output
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
│   │   │   └── config.py
│   │   │   # suitability_registry.json (runtime-generated, not in git)
│   │   └── performance/     # Post-backtest analysis
│   │       ├── __init__.py
│   │       ├── analyzer.py
│   │       ├── decomposition.py
│   │       ├── risk_metrics.py
│   │       ├── report.py
│   │       ├── registry.py
│   │       └── config.py
│   │       # performance_registry.json (runtime-generated, not in git)
│   ├── visualization/       # Plotting and dashboards
│   │   ├── __init__.py
│   │   ├── plots.py         # Plotting functions
│   │   ├── visualizer.py    # Theme management
│   │   └── app.py           # Streamlit dashboard (stub)
│   ├── persistence/         # I/O and registry
│   │   ├── __init__.py
│   │   ├── parquet_io.py    # Parquet read/write
│   │   └── json_io.py       # JSON read/write
│   ├── examples/            # Standalone workflow scripts (in distribution)
│   │   ├── 01_generate_synthetic_data.py
│   │   ├── 02_fetch_data_file.py
│   │   ├── 03_fetch_data_bloomberg.py
│   │   ├── 04_compute_signal.py
│   │   ├── 05_evaluate_suitability.py
│   │   ├── 06_run_backtest.py
│   │   ├── 07_analyze_performance.py
│   │   └── 08_visualize_results.py
│   └── docs/                # Design documentation (in distribution)
│       ├── cdx_overlay_strategy.md
│       ├── python_guidelines.md
│       ├── logging_design.md
│       ├── signal_registry_usage.md
│       ├── signal_suitability_design.md
│       ├── performance_evaluation_design.md
│       ├── visualization_design.md
│       ├── governance_design.md
│       ├── cli_guide.md
│       └── adding_data_providers.md
│
├── tests/                   # Unit tests (680 tests total)
│   ├── backtest/            # 36 tests
│   ├── cli/                 # 83 tests
│   ├── data/                # 223 tests
│   ├── evaluation/          # 154 tests
│   ├── governance/          # 19 tests
│   ├── models/              # 74 tests
│   ├── persistence/         # 27 tests
│   ├── reporting/           # 18 tests
│   ├── visualization/       # 19 tests
│   └── workflows/           # 27 tests
│
├── examples/                # YAML workflow configurations
│   ├── workflow_basic.yaml
│   ├── workflow_bloomberg.yaml
│   └── workflow_custom_steps.yaml
│
├── data/                    # Data storage (not in git)
│   ├── registry.json        # Dataset registry (runtime)
│   ├── raw/                 # Source data files
│   ├── processed/           # Transformed data
│   │   ├── reports/
│   │   └── workflows/       # Workflow outputs
│   │       ├── backtests/
│   │       ├── signals/
│   │       └── visualizations/
│   └── cache/               # TTL-based cache
│       ├── bloomberg/
│       ├── file/
│       └── synthetic/
│
├── logs/                    # Run metadata (not in git)
│
├── reports/                 # Generated reports (not in git)
│   ├── suitability/         # Pre-backtest evaluations
│   └── performance/         # Post-backtest analyses
│
├── scripts/                 # Utility scripts (not in git)
│   ├── clean_pycache.py
│   ├── clean_runtime_data.py
│   └── README.md
│
├── .github/
│   └── copilot-instructions.md  # AI assistant configuration
│
├── pyproject.toml           # Project metadata and dependencies
├── README.md                # Quickstart guide
├── LICENSE                  # MIT license
├── CHANGELOG.md             # Version history
├── CONTRIBUTING.md          # Contribution guidelines
├── SECURITY.md              # Security policy
└── PROJECT_STATUS.md        # This file
├── TODO.md                  # Task tracking
├── PROJECT_STATUS.md        # This file
├── CHANGELOG.md             # Version history
├── PYPI_RELEASE_CHECKLIST.md  # Release process
└── project_setup_process.md   # Setup documentation
```

---

## Context for AI Assistants

When providing both `PROJECT_STATUS.md` and `.github/copilot-instructions.md` to AI assistants:

- **This document**: Implementation status, business context, architecture decisions
- **copilot-instructions.md**: Coding patterns, scaffolding templates, integration rules

**Key reference files:**
- Architecture: This document (layer table, implementation status)
- Code patterns: `.github/copilot-instructions.md`
- Investment context: `src/aponyx/docs/cdx_overlay_strategy.md`
- Python standards: `src/aponyx/docs/python_guidelines.md`

---

**End of Document**
