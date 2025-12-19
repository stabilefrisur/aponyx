# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Return Calculator Abstraction** (spec 009)
  - `ReturnCalculator` protocol for computing daily P&L returns
  - `SpreadReturnCalculator` for DV01-based spread products (CDX indices)
  - `PriceReturnCalculator` for price-based products (ETFs: LQD, HYG, etc.)
  - `resolve_calculator()` factory function for automatic calculator selection
  - `quote_type` field in product microstructure for product categorization
  - Price data validation for price-based calculators (fail-fast)
  - Calculator info in backtest result metadata
  - Example workflow `workflow_etf.yaml` for ETF backtesting
  - 24 new tests for calculator implementations and factory logic

### Changed
- **BREAKING: `run_backtest()` Signature Change**
  - Now requires `calculator: ReturnCalculator` as fourth positional parameter
  - DV01-based P&L calculation moved from engine to `SpreadReturnCalculator`
  - Calculator must be resolved via `resolve_calculator()` or created directly
- **BREAKING: `BacktestConfig` Changes**
  - Removed `dv01_per_million` field (now passed to calculator)
  - All backtest tests updated to inject calculator parameter
- **BREAKING: `StrategyRegistry.to_config()` Changes**
  - Removed `dv01_per_million` parameter (now handled separately via calculator)
- **Product Metadata Enhancement**
  - All products now require `quote_type` field ("spread" or "price")
  - CDX products: `quote_type: "spread"` with `dv01_per_million`
  - ETF products: `quote_type: "price"` (no DV01 required)
  - VIX: `quote_type: "price"` (can now be backtested as price-based product)

### Migration Guide
- **Workflow YAML files**: No changes required (BacktestStep handles resolution automatically)
- **Direct `run_backtest()` calls**: Add calculator parameter:
  ```python
  from aponyx.backtest import resolve_calculator
  calculator = resolve_calculator("spread", dv01_per_million=475.0)
  result = run_backtest(signal, spread, config, calculator)
  ```
- **`to_config()` calls**: Remove `dv01_per_million` parameter

### Test Coverage
- 918 total tests passing
- All existing spread-based backtests produce identical results (zero regression)

## [0.1.19] - 2025-12-15

### Added
- **Interactive Research Dashboard** for signal pipeline analysis
  - `plot_research_dashboard()` function generating 5-panel Plotly visualization
  - Displays four-stage transformation pipeline (indicator → score → signal → positions → P&L)
  - Shows traded product (CDX spread) alongside signal for correlation analysis
  - Supports runtime transformation overrides via workflow metadata
  - Example script `09_research_dashboard.py` demonstrating standalone usage
  - Dashboard height: 1440px with dual y-axes and synchronized time axis
  - Interactive features: shared x-axis, range slider, unified hover mode
  - 14 new tests for dashboard functionality in `tests/visualization/test_plots.py`

### Fixed
- **Transformation Override Passthrough** in research dashboard
  - Dashboard now correctly uses transformation overrides from workflow metadata
  - Added transformation override fields to workflow `metadata.json`
  - `recompute_signal_with_intermediates()` now accepts override parameters
  - Fixes issue where signal equaled score when signal_transformation override was specified

### Documentation
- Updated README.md architecture table with `plot_research_dashboard` function
- Added research dashboard section to `visualization_design.md`
- Updated CHANGELOG with unreleased research dashboard feature

### Test Coverage
- 769 total tests passing (increased from 755)
- 14 new visualization tests for research dashboard functionality

## [0.1.18] - 2025-12-14

### Added
- **GitHub Automation Tooling**
  - PyPI release agent (`.github/agents/pypi-release.agent.md`) for automated package publishing
  - CLI workflow testing agent (`.github/agents/test-cli-workflows.agent.md`) for validation
  - Upstream tarball agent (`.github/agents/upstream-tarball.agent.md`) for dependency tracking
  - Reset dev environment prompt (`.github/prompts/reset-dev-environment.prompt.md`)
  - Corresponding prompt files for agent invocation

### Changed
- **Build System Migration**
  - Switched build backend from `uv_build` to `hatchling` for improved compatibility
  - Updated `pyproject.toml` with hatchling configuration
  - Package builds now use standard hatchling wheel builder
- **Unified Provider Interface**
  - Refactored Bloomberg provider with adapter pattern in `_get_provider_fetch_function()`
  - Added `_bloomberg_adapter` to normalize Bloomberg provider to unified signature
  - Removed source parameter filtering from `fetch_from_bloomberg()` and `fetch_current_from_bloomberg()`
  - Restored unified `fetch_fn()` calls in `fetch_cdx`, `fetch_vix`, `fetch_etf`
  - Adapter pattern isolates provider-specific parameter handling in factory function
- **Environment Cache Cleanup Script**
  - Renamed `scripts/clean_pycache.py` → `scripts/clean_env_cache.py`
  - Added support for `.pytest_cache`, `.mypy_cache`, `.ruff_cache` cleanup
  - Virtual environments (`.venv`, `venv`, `.env`, `env`) now excluded from cleaning
  - Updated function name: `clean_pycache()` → `clean_env_cache()`
  - Updated all documentation references

### Fixed
- **Dependency Resolution**
  - Added `ipython` as explicit dependency to resolve quantstats import failures
  - quantstats has undeclared dependency on ipython (required by quantstats.reports module)
  - While only quantstats.stats is used, Python's import system loads entire package

### Test Coverage
- Updated test to check for adapter instead of identity comparison in provider tests
- All 755 tests passing

## [0.1.17] - 2025-12-14

### Added
- **CDX Knowledge Base Reference** - Comprehensive documentation for CDX trading mechanics
  - CDX index family overview (IG, HY, XO) with maturity tenors
  - DV01 and risk metrics explanation with calculation examples
  - P&L calculation formulas for both binary and proportional sizing modes
  - Transaction cost calculations and spread P&L mechanics
  - Signal interpretation conventions aligned with backtest engine
  - Project implementation details and portfolio construction guidance

### Changed
- **Catalog-Driven Configuration Enforcement**
  - Removed fallback defaults from indicator functions (fail-fast behavior)
  - `compute_spread_momentum`: Now requires `parameters['lookback']` (was `.get(lookback, 5)`)
  - `compute_cdx_vix_deviation_gap`: Now requires `parameters['lookback']` (was `.get(lookback, 20)`)
  - Added `Raises` section to docstrings documenting KeyError on missing parameters
  - Catalog misconfiguration now caught at test time instead of silently using code defaults
- **Test Fixture Improvements**
  - Renamed `make_test_config` → `make_minimal_test_config` with explicit deviation docs
  - Renamed `make_test_strategy_metadata` → `make_minimal_test_metadata`
  - Added `make_catalog_test_config()` for catalog-accurate testing
  - Added `make_catalog_test_metadata()` for catalog-based fixtures
  - Backwards compatibility aliases retained for existing code
- **Documentation Updates**
  - Updated all example scripts to reflect four-stage transformation pipeline
  - Fixed paths in examples (data/processed → data/workflows)
  - Simplified data loading using `DataRegistry.load_dataset_by_security()`
  - Updated version and date references across all documentation
  - Corrected registry names in design documents
  - Fixed BacktestConfig documentation (removed obsolete threshold fields)
  - Complete rewrite of signal_registry_usage.md with current patterns

### Fixed
- **DV01 Calibration** - Corrected default from 4750.0 to 475.0 per $1MM notional
  - CDX IG 5Y with ~4.75 year duration has $475 DV01 per $1MM, not $4,750
  - Previous value incorrectly represented total DV01 for $10MM position
  - Updated in BacktestConfig, StrategyMetadata, all 4 strategy catalog entries
  - Fixed 16 test cases with P&L calculations and position values
  - Updated documentation examples in copilot-instructions.md and CONTRIBUTING.md
- **Test Suite Alignment**
  - Fixed tests to align with `generate_report()` API returning dict format
  - Removed tests for deprecated `--output` CLI option
  - Fixed `TestCollectReportData` to avoid mocking non-existent attributes
  - Removed unused imports in test files

### Removed
- **Cleanup**
  - Deleted `scripts/validate_backtest_cleanup.py` (validation script no longer needed)
  - Removed duplicate default values from BacktestConfig and StrategyMetadata
  - Removed entry_threshold/exit_threshold from strategy system (replaced with signal-based triggers)

### Test Coverage
- **Catalog Completeness Validation** (4 new tests in `tests/models/test_catalog.py`)
  - `test_indicator_transformations_have_required_parameters` - Validates all indicators define required params
  - `test_score_transformations_have_required_parameters` - Validates all score transformations have params
  - `test_all_signals_reference_valid_transformations` - Validates 1:1:1 reference integrity
  - `test_strategy_catalog_completeness` - Validates all strategies have required fields
- All 755 tests passing (verified December 2025)

### Breaking Changes
- Indicator functions now raise `KeyError` if catalog is missing required parameters (was silent fallback to code defaults)

## [0.1.16] - 2025-12-13

### Added
- **Four-Stage Transformation Pipeline** (004-four-stage-transform)
  - New `signal_transformation.json` catalog for trading rules (floor, cap, neutral_range, scaling)
  - `SignalTransformationRegistry` for signal transformation metadata management
  - `apply_signal_transformation()` function for trading rule application
  - Stage inspection functions: `compute_indicator_stage()`, `compute_score_stage()`, `compute_signal_stage()`
  - Runtime overrides: `indicator_transformation_override`, `score_transformation_override`, `signal_transformation_override`
  - `include_intermediates` parameter in `compose_signal()` for debugging intermediate stages
  - CLI list support for `score-transformations` and `signal-transformations` categories
  - `CatalogValidationError` for structured error messages across all registries
- **Proportional Position Sizing Mode** (006-proportional-position-sizing)
  - Signal-proportional position sizing: `position = signal × position_size_mm`
  - Linear position scaling with signal magnitude for nuanced risk exposure
  - Transaction costs proportional to position change delta
  - Daily P&L calculation using prior day's actual notional
  - Risk management (stop-loss/take-profit) evaluated against current notional
  - Correct trade tracking and metadata for variable position sizes
  - NaN/Infinity handling with warning logs for invalid signals
  - Proportional sizing now the default mode (binary available via override)
- **Package Distribution Enhancements**
  - Included all transformation JSON files in package distribution
  - Added `synthetic_params.json` to package data
  - Complete four-stage pipeline fully accessible in installed package

### Changed
- **Signal Composition Architecture** (Breaking)
  - Refactored `compose_signal()` for explicit 4-stage pipeline: Security → Indicator → Score → Signal
  - Signal catalog structure changed: `indicator_dependencies/transformations` → `indicator_transformation/score_transformation/signal_transformation`
  - All 3 signals migrated to new structure (cdx_etf_basis, cdx_vix_gap, spread_momentum)
  - Renamed `indicator_catalog.json` → `indicator_transformation.json`
  - Renamed `transformation_catalog.json` → `score_transformation.json`
  - Split `TransformationRegistry` into `ScoreTransformationRegistry` and `SignalTransformationRegistry`
- **Backtest Strategy System** (Breaking) (005-backtest-strategy-cleanup)
  - Removed threshold-based position entry/exit in favor of signal-based triggers
  - Non-zero signal = enter position, zero signal = exit position
  - Removed `entry_threshold`, `exit_threshold`, `position_size` from `BacktestConfig`
  - Added `position_size_mm`, `sizing_mode`, `stop_loss_pct`, `take_profit_pct`, `max_holding_days`
  - Implemented `PositionState` enum (NO_POSITION, IN_POSITION, COOLDOWN) for state management
  - Added `exit_reason` tracking (signal, stop_loss, take_profit, max_holding_days, reversal)
  - Cumulative P&L tracking per position for risk threshold calculation
  - Cooldown state after PnL-based exits (prevents re-entry until signal resets)
  - Signal sign reversal without cooldown enables responsive trading
  - Migrated all 4 strategies to new schema (conservative, balanced, aggressive, experimental)
  - **Proportional sizing is now the default** (changed from binary)
  - Removed 4 `_proportional` strategy variants (8 → 4 strategies)
  - Binary sizing available via `sizing_mode_override='binary'`
- **Data Provider Interface** (Breaking)
  - Unified `FileSource` and `BloombergSource` interfaces for interchangeability
  - `FileSource` now uses `base_dir + registry.json` instead of single file path
  - Auto-load `security_mapping` from registry.json in `FileSource.__post_init__`
  - File provider signature unified: `(source, ticker, instrument, security, ...)`
  - Security column enrichment for multi-security instruments
  - Removed `bloomberg_ticker` parameter from `fetch_cdx()` and `fetch_etf()`
  - All Bloomberg ticker resolution via `get_bloomberg_ticker(security)`
  - Removed obsolete `find_raw_file()` and `concat_multi_security()` functions
- **CLI Improvements**
  - Removed `--output` flag from `report` command (always saves to workflow's reports/ folder)
  - `generate_report()` now returns dict with content and output_path
  - Split CLI list `transformations` into `score-transformations` and `signal-transformations`
  - YAML config `transformation` field replaced with `score_transformation` and `signal_transformation`
  - Updated workflow config display format for better alignment
- **Documentation Overhaul**
  - Streamlined `CONTRIBUTING.md` from 725 to 280 lines (61% reduction)
  - Comprehensive Position Sizing Modes section in CLI guide
  - Updated all examples with new backtest schema and 4-stage pipeline
  - Updated test count from 681 to 755 across all documentation
  - Fixed signal transformation references (all signals use passthrough)
  - Corrected dev dependencies list (pytest only, not ruff/mypy/pandas-stubs)
  - Changed black references to ruff format throughout
  - Updated dates to December 13, 2025

### Fixed
- **Type Safety**
  - Fixed type cast for `iterrows()` date parameter in backtest engine (mypy compliance)
  - Added `Any` import to backtest protocols for proper type hints
  - Enhanced date handling in position tracking logic
- **Error Handling**
  - Suppress division by zero warnings in Sharpe ratio calculation (zero std edge case)
  - Wrap quantstats metric calls to suppress expected RuntimeWarnings
- **Data Flow**
  - Fixed `SuitabilityStep` and `BacktestStep` to get spread data from workflow context
  - Resolved fresh registry data flow issue (no longer reloads from DataRegistry)
  - Removed dead code in loaders.py (unreachable block after return)

### Breaking Changes
- Signal catalog schema changed - signals now require `indicator_transformation`, `score_transformation`, and `signal_transformation` fields
- `compose_signal()` signature updated with renamed registries and three override parameters
- Backtest config schema changed - removed thresholds, added position sizing and risk management fields
- Strategy catalog schema changed - all strategies migrated to signal-based triggers
- `FileSource` now requires `base_dir` with `registry.json` instead of single file path
- `fetch_cdx()` and `fetch_etf()` require `security` parameter (removed `bloomberg_ticker`)
- CLI list `transformations` split into `score-transformations` and `signal-transformations`
- YAML workflow config requires `score_transformation` and `signal_transformation` instead of `transformation`
- Proportional position sizing is now the default (binary available via override)
- Report command no longer accepts `--output` flag

### Test Coverage
- 755 total tests passing (increased from 681)
- 30+ new backtest tests for signal-based triggers and PnL risk management
- 59 backtest engine tests (20+ new proportional sizing tests)
- All governance tests updated for new schema
- Complete test coverage for four-stage transformation pipeline

## [0.1.15] - 2024-12-02

### Added
- **Indicator-Signal Separation Architecture**
  - New `indicators.py` module with reusable indicator computation functions
  - New `transformations.py` module with signal processing operations
  - `indicator_catalog.json` defining 3 core indicators with metadata
  - `transformation_catalog.json` defining 4 transformation operations
  - Indicator caching for performance optimization across signals
  - `IndicatorRegistry` and `TransformationRegistry` for metadata management
  - Runtime overrides: `indicator_override`, `transformation_override`, `security_mapping`
- **Enhanced CLI List Command**
  - New `aponyx list products` to display available CDX products
  - New `aponyx list indicators` to show indicator catalog with data requirements
  - New `aponyx list transformations` to show available signal transformations
  - New `aponyx list securities` to display Bloomberg security mappings
  - Improved formatting with rich table output for all list commands
- **Comprehensive Test Suite**
  - 361 tests in `test_indicator_registry.py` for indicator metadata validation
  - 329 tests in `test_indicators.py` for indicator computation logic
  - 317 tests in `test_transformation_registry.py` for transformation metadata
  - 379 tests in `test_signal_composer.py` for signal composition patterns
  - All CLI tests updated and passing (681 total tests)

### Changed
- **Signal Composition Pattern** (Breaking)
  - Signals now ALWAYS composed from indicator + transformation (no direct computation)
  - Removed `signals.py` module - all computation split into indicators and transformations
  - Signal catalog entries now reference `indicator_dependencies` and `transformations`
  - `compose_signal()` replaces direct signal computation functions
  - Indicators output raw economic values (bps, ratios) - NOT pre-normalized
  - Transformations apply signal processing (z-score, volatility adjustment, differencing)
- **Workflow Configuration** (Breaking)
  - CLI simplified to YAML-config-only approach (no CLI parameter overrides)
  - Removed `--signal`, `--strategy`, `--product`, `--securities`, `--data` flags from `run` command
  - All workflow parameters configured via YAML files only
  - New `workflow_minimal.yaml` and `workflow_complete.yaml` examples
  - Removed `workflow_basic.yaml`, `workflow_bloomberg.yaml`, `workflow_custom_securities.yaml`, `workflow_custom_steps.yaml`
- **Label-Based Workflow System**
  - Workflow directories renamed to `{label}_{timestamp}` format
  - Label field now required in workflow config
  - `aponyx report` accepts label or index (0 = most recent)
  - Improved workflow discovery and organization
- **Registry Architecture**
  - Split `SignalRegistry` into `IndicatorRegistry`, `TransformationRegistry`, `SignalRegistry`
  - Enhanced metadata validation with comprehensive error messages
  - Removed legacy compatibility code and deprecated patterns
  - Catalog schema enforced at load time with fail-fast validation

### Fixed
- **CLI Test Suite** completely refactored for new workflow API
  - Fixed all 894 test assertions in `test_commands.py`
  - Updated error handling tests for YAML-only configuration
  - Fixed integration tests for label-based workflow discovery
  - All 681 tests passing with new architecture

### Removed
- **Legacy Compatibility Code**
  - Removed backward compatibility layer from indicator-signal architecture
  - Removed CLI parameter override support (YAML-only now)
  - Removed deprecated `signals.py` module
  - Removed `.github` internal files (kept `copilot-instructions.md` only)
  - Removed `.specify` and `specs/` folders from version control
  - Cleaned up 4,213 lines of legacy code

### Documentation
- **Comprehensive Updates** for new architecture
  - Updated `copilot-instructions.md` with indicator-transformation-signal pattern
  - Clarified signal composition pattern with MANDATORY indicator + transformation requirement
  - Added runtime override documentation (indicator_override, transformation_override, security_mapping)
  - Updated CLI guide for YAML-config-only approach
  - Enhanced governance documentation with architectural evolution details
  - Updated README with new workflow examples and list command capabilities

### Breaking Changes
- Signal catalog schema changed - all signals must declare `indicator_dependencies` and `transformations`
- Direct signal computation functions removed - use `compose_signal()` with indicator + transformation
- CLI no longer accepts workflow parameter overrides - use YAML config files only
- Workflow directory naming changed to `{label}_{timestamp}` format
- Removed multiple example workflow files - use `workflow_minimal.yaml` or `workflow_complete.yaml`

## [0.1.14] - 2025-11-23

### Added
- **Enhanced CLI Logging** for better debugging and development
  - Global `-v/--verbose` flag for DEBUG-level logging across all commands
  - Default logging level changed from INFO to WARNING for cleaner output
  - FileHandler for timestamped logs in `logs/` directory
  - Visible output for `clean --all` showing all file deletions

### Changed
- **CLI Output Improvements**
  - Updated `run` command output schema with comprehensive execution summary:
    * Signal: {signal} ({securities})
    * Strategy: {strategy}
    * Product: {product}
    * Data: {source}
    * Steps: {steps}
    * Force re-run: {True/False}
  - Improved force flag documentation for clarity as cache invalidation
- **Cache and Workflow Filenames** for consistency
  - Cache files renamed from `{instrument}_{hash}` to `{security}_{hash}`
  - Signal files simplified to `signal.parquet` (was `{signal_name}.parquet`)
  - Suitability reports: `suitability_evaluation_{timestamp}.md`
  - Performance reports: `performance_analysis_{timestamp}.md`
  - Added `securities_used` mapping to workflow `metadata.json`
- **Emoji Removal** for better terminal compatibility
  - Replaced all emoji indicators with ASCII equivalents
  - Suitability: `[PASS]`, `[HOLD]`, `[FAIL]`
  - Performance: `[STRONG]`, `[MODERATE]`, `[WEAK]`
  - Recommendations: `[WARNING]`, `[FAIL]`, `[PASS]`
- **Simplified Dependency Management**
  - Removed `[tool.ruff]`, `[tool.black]`, and `[tool.mypy]` sections from pyproject.toml
  - Removed ruff, black, mypy, and pandas-stubs from dev dependencies
  - Leverages uv's on-demand tool execution model (`uv run ruff check/format`)
  - Cleaner dependency tree and faster environment setup

### Fixed
- **Report Generation** timestamp extraction
  - Fixed SuitabilityStep timestamp extraction to use context `output_dir`
  - Fixed PerformanceStep timestamp extraction to use context `output_dir`
  - Updated report generator glob patterns for new filenames
  - Removed Unicode fallback (no longer needed with ASCII format)
- **Test Suite Updates**
  - Updated test_commands.py for new clean output format
  - Updated test_integration.py for new run output schema
  - Updated test_fetch.py for security-based parameters
  - Fixed emoji expectations to ASCII format
  - Fixed filename assertions for timestamped reports
  - All 681 tests passing

### Documentation
- **CLI Guide Restructure** for better usability
  - Added command reference section at top for quick lookup
  - Consolidated Understanding Workflows section with directory tree visualization
  - Replaced generic Examples with Common Workflows (production, development, batch)
  - Restructured Troubleshooting by category with actionable solutions
  - 15% shorter with better scanability
- **Updated Documentation** to reflect current implementation
  - cli_guide.md with new output schema and logging behavior
  - copilot-instructions.md with latest patterns
  - README.md with current CLI examples
  - PROJECT_STATUS.md with implementation status

### Breaking Changes
- Cache file naming changed (invalidates existing cache)
- Workflow output structure simplified (old filenames incompatible)
- Run command output format changed

## [0.1.13] - 2025-11-23

### Added
- **Flexible Security Mapping** for signal computation
  - `default_securities` field in signal catalog defining instrument-to-security defaults
  - `security_mapping` parameter in WorkflowConfig for custom security selection
  - `--securities` CLI option for runtime security overrides (e.g., `cdx:cdx_hy_5y,etf:hyg`)
  - `workflow_custom_securities.yaml` example demonstrating security mapping
  - DataRegistry helper methods: `find_dataset_by_security()` and `load_dataset_by_security()`
  - `load_signal_required_data()` helper in data/loaders.py for reusable data loading logic
- **Bloomberg Data Fetching** enhancements
  - DataStep now downloads all securities from bloomberg_securities.json
  - Smart current-day refresh for intraday Bloomberg data updates

### Changed
- **Signal Data Loading** architecture
  - Security selection moved from DataStep to SignalStep
  - SignalStep maps instrument types to specific securities using defaults or overrides
  - DataStep becomes signal-agnostic, downloading all available securities
  - Signal catalog now explicitly declares default_securities for each signal
  - VIX loading skips security parameter (single instrument)
- **Documentation Updates**
  - Updated copilot-instructions.md with security mapping patterns
  - Updated README.md with `--securities` CLI option examples
  - Updated PROJECT_STATUS.md with DataRegistry helpers
  - All documentation dates updated to November 23, 2025

### Fixed
- Signal computation now properly supports running same signal with different securities
- Products for backtesting default to cdx_ig_5y consistently

## [0.1.12] - 2025-11-22

### Added
- **Utility Scripts** for build and maintenance workflows
  - `scripts/clean_env_cache.py` - Remove Python and tool cache directories (excludes virtual environments)
  - `scripts/clean_runtime_data.py` - Clean runtime data (cache, registries, workflows)
  - `scripts/README.md` - Comprehensive documentation for utility scripts
- **CLI Enhancements**
  - Global `-v/--verbose` flag for DEBUG-level logging across all commands
  - Dynamic data source discovery from filesystem in `list` command
  - Extended `list` command with 'steps' category for workflow step browsing
  - Improved help text formatting with categorized examples
  - Source column in dataset listings showing data provider
- **Documentation Improvements**
  - Comprehensive copilot instructions with scaffolding templates (2600+ lines)
  - Workflow guidance with 5-step process for multi-step tasks
  - Git commit standards with conventional commits format
  - Enhanced signal naming consistency guidelines
  - Cross-reference table in PROJECT_STATUS for documentation navigation
  - Python guidelines with modern type hints and code patterns

### Changed
- **Workflow Architecture**
  - Consolidated all workflow outputs to timestamped directories (`data/workflows/{signal}_{strategy}_{timestamp}/`)
  - Registry files moved to `data/.registries/` directory
  - Bloomberg data fetcher now uses smart refresh (update current day data only)
  - Force flag (`--force`) now documented as cache invalidation mechanism
- **Documentation Structure**
  - Streamlined PROJECT_STATUS to focus on implementation status vs code patterns
  - Removed redundant code patterns from PROJECT_STATUS (deferred to copilot-instructions)
  - Updated all documentation dates to November 22, 2025
  - Fixed Python version consistency (py312) across all documentation
  - Removed `scripts/` from .gitignore to track utility scripts

### Fixed
- **Synthetic Data Generation** duplicate dates issue
  - Changed date generation from calendar days (`freq="D"`) to business days (`pd.bdate_range()`)
  - Eliminated ~520 duplicate weekend dates that were causing validation warnings
  - Fixed mismatch between period calculation and data generation
- **Data Validation** logging behavior
  - Reduced duplicate date removal logging from WARNING to DEBUG level
  - Updated `concat_multi_security` to handle expected multi-security duplicates silently
  - Duplicates from multi-security concatenation now logged at DEBUG level with context
- **Test Suite** validation test expectations
  - Updated `test_validate_cdx_schema_duplicate_dates` to verify silent duplicate removal
  - All 223 data layer tests passing

### Breaking Changes
- Workflow outputs now use timestamped directory structure instead of scattered files
- Registry files relocated to `data/.registries/` (migration handled automatically)

## [0.1.11] - 2025-11-21

### Added
- **CLI Orchestrator** for automated research workflows
  - `aponyx run` command for executing complete signal-strategy pipelines
  - `aponyx report` command for generating comprehensive analysis reports (console/markdown/HTML)
  - `aponyx list` command for browsing available signals, strategies, and datasets
  - `aponyx clean` command for managing cached workflow results with improved feedback
  - YAML configuration file support for reproducible workflows
  - Smart caching with automatic skip of completed steps
  - Force re-run option for invalidating cache
  - Subset execution for running specific workflow steps
  - Example workflow YAML files in `examples/` directory
  - Comprehensive CLI user guide (`src/aponyx/docs/cli_user_guide.md`)
  - Help text shorthand (`-h`) for all commands
  - Comprehensive CLI layer test suite with 28 tests
- **Workflow Engine** infrastructure
  - `WorkflowEngine` for sequential pipeline execution with dependency tracking
  - `WorkflowConfig` for immutable workflow configuration
  - Protocol-based step abstraction with `WorkflowStep` interface
  - Six concrete workflow steps: data, signal, suitability, backtest, performance, visualization
  - `StepRegistry` for centralized step factory and ordering
  - Error handling with partial result preservation
  - Structured logging with progress indicators
  - Cache-then-raw fallback for workflow data loading
  - Decoupled data step from instrument-specific logic
- **Reporting Package** for analysis aggregation
  - `generate_report()` function with multiple output formats
  - Console reports with table formatting
  - Markdown reports with embedded visualization links
  - HTML reports with styled formatting
  - Automatic aggregation of suitability and performance evaluations
  - Smart report data collection from workflow outputs
- **Example Scripts** for standalone workflow execution
  - `01_generate_synthetic_data.py` - Synthetic data generation
  - `02_fetch_data_file.py` - File-based data loading
  - `03_fetch_data_bloomberg.py` - Bloomberg Terminal data fetch
  - `04_compute_signal.py` - Signal computation
  - `05_evaluate_suitability.py` - Signal-product suitability assessment
  - `06_run_backtest.py` - Strategy backtesting
  - `07_analyze_performance.py` - Performance analysis
  - `08_visualize_results.py` - Results visualization

### Changed
- **Architecture Improvements**
  - Decoupled configuration from specific instruments for better modularity
  - Separated signal metadata, registry, and orchestration into distinct modules
  - Removed defensive error handling from example scripts for clarity
- **CLI Enhancements**
  - Simplified CLI output for better readability
  - Changed default product to `cdx_ig_5y` for consistency
  - Improved help formatting with better descriptions
- **Documentation Overhaul**
  - Consolidated and streamlined documentation structure
  - Updated all docs for CLI/workflow infrastructure
  - Fixed README Quick Start example and documentation links
  - Removed all notebook-related documentation
- **Testing**
  - Resolved all 28 failing tests
  - Added comprehensive CLI layer test coverage
- **Dependencies**
  - Updated `pyproject.toml` to include `pyyaml>=6.0` dependency
  - Added `aponyx` CLI entry point in `[project.scripts]`

### Removed
- **Jupyter Notebooks** - Complete removal of notebook workflow
  - Deleted entire `src/aponyx/notebooks/` directory with all workflow notebooks
  - Removed `NOTEBOOK_TROUBLESHOOTING.md`
  - Removed notebook-related sections from README.md
  - Removed notebook context from copilot-instructions.md
  - Cleaned up notebook references from design docs (performance_evaluation, visualization, python_guidelines)
  - Removed notebook references from PROJECT_STATUS.md
  - CLI workflows now provide complete orchestration, making notebooks redundant

## [0.1.10] - 2025-11-16

### Added
- Comprehensive raw data storage system with hash-based file naming across all providers
  - Unified storage under `data/raw/synthetic/`, `data/raw/file/`, `data/raw/bloomberg/`
  - Deterministic hash-based naming for deduplication and integrity
  - Metadata JSON files tracking fetch parameters and timestamps
  - Test suite validating storage patterns across providers
- Intraday data update capability in single-signal notebook template
  - `update_cached_data()` workflow for Bloomberg refresh
  - Configurable field subsets and refresh intervals
  - Automatic cache validation and staleness checks
- Signal lag parameter sweep example demonstrating systematic optimization
  - Grid search across entry/exit thresholds and signal lags
  - Heatmap visualization of performance surfaces
  - Best parameter identification workflow
- Sign multiplier feature in signal catalog for flexible signal inversion
  - `sign_multiplier` field in signal catalog JSON (+1 or -1)
  - Automatic signal inversion without code changes
  - Enhanced signal registry with multiplier validation

### Changed
- Refactored data architecture to proper raw/cache/processed separation
  - Raw storage: immutable source data with metadata
  - Cache: TTL-based Parquet for fetch optimization
  - Processed: analysis-ready transformed datasets
  - Clear separation of concerns and data lineage
- Enhanced synthetic data generation with improved market dynamics
  - More realistic correlation structures between CDX/VIX/ETF
  - Configurable regime simulation (normal, stress, recovery)
  - Better alignment with actual market behavior patterns
- Streamlined example scripts with improved Bloomberg integration
  - Enhanced error handling for Terminal connection issues
  - Better fallback patterns for offline development
  - Clearer documentation of Bloomberg requirements
- Integrated quantstats library for enhanced performance analytics
  - Extended metrics beyond internal calculations
  - Professional tearsheet generation capability
  - Comprehensive risk-adjusted performance analysis
- Converted backtest adapters to protocol-based interface
  - Clean separation between internal engine and third-party libraries
  - Extensible adapter pattern for quantstats/vectorbt integration
  - Improved testability and modularity

### Fixed
- Bloomberg provider now correctly handles BDP/BDH format differences
  - BDP returns dict format for static fields
  - BDH returns DataFrame format for time series
  - Proper handling of both response types
- Suitability evaluation import path corrected in Quick Start example
  - Fixed module path in README.md demonstration
  - Updated to match actual package structure

### Documentation
- Added comprehensive raw data storage design document
  - Hash-based naming rationale and implementation
  - Provider-specific storage patterns
  - Metadata schema and validation approach
- Updated caching design documentation to reflect architecture changes
  - Clarified cache vs raw storage distinction
  - Enhanced provider integration patterns
  - Improved cache invalidation workflows

## [0.1.9] - 2025-11-15

### Added
- Intraday cache update feature for Bloomberg data with selective field updates
  - `update_cached_data()` function for efficient cache refresh
  - Configurable refresh intervals and field subsets
  - Comprehensive integration tests validating update workflow
- Centralized time series transformation module (`data/transforms.py`)
  - Reusable functions for z-score normalization, returns calculation, rolling statistics
  - Separation of data processing logic from signal computation
  - Enhanced code modularity and testability

### Changed
- Refined evaluation layer positioning and scope in documentation
  - Clarified relationship between suitability and performance evaluation
  - Updated governance design with evaluation registry patterns
  - Enhanced documentation structure guide

### Fixed
- P&L calculation now correctly computes incremental returns instead of cumulative from entry
  - Prevents compounding errors in multi-period backtests
  - Aligns with standard financial performance metrics
- Resolved test suite failures and improved code quality
  - Fixed suitability evaluation test configuration patterns
  - Enhanced error handling in transformation functions
  - Updated type hints to modern Python syntax

### Documentation
- Added `CONTRIBUTING.md` with project scope disclaimers and contribution guidelines
- Added `SECURITY.md` with security policy and research framework limitations
- Updated evaluation layer documentation for clarity and accuracy

## [0.1.8] - 2025-11-13

### Added
- Single-signal research workflow template notebook (`notebooks/06_single_signal_template.ipynb`) with 8588 lines
  - Complete end-to-end workflow for individual signal development and validation
  - Integrated suitability evaluation, backtesting, and performance analysis
  - Self-contained template for rapid signal idea iteration
- Jupyter notebook stability settings and troubleshooting guide (`NOTEBOOK_TROUBLESHOOTING.md`)
  - Solutions for kernel crashes and execution issues
  - Environment variable configuration for Windows stability
  - Best practices for notebook development workflow

### Changed
- Refactored performance metrics consolidation into evaluation layer
  - Moved `backtest/metrics.py` → `evaluation/performance/metrics.py`
  - Enhanced metrics module with comprehensive risk-adjusted calculations
  - Unified performance analysis through evaluation layer
- Implemented rolling window stability analysis with dual-metric scoring
  - Enhanced `PerformanceAnalyzer` with temporal stability assessment
  - Added rolling Sharpe ratio tracking for regime consistency
  - Improved performance reporting with stability diagnostics
- Aligned structure and formatting across notebooks 01-05
  - Standardized markdown headers and cell organization
  - Consistent workflow documentation and prerequisite tracking
  - Improved table formatting with left-aligned display
- Updated documentation for accuracy across design docs and notebooks
  - Corrected signal registry usage examples
  - Fixed performance evaluation design documentation
  - Enhanced signal suitability design document (renamed from `signal_suitability_evaluation.md`)

### Fixed
- Performance metrics now correctly compute extended risk metrics (profit factor, tail ratio, Calmar)
- Suitability evaluation tests updated with correct configuration patterns
- Notebook execution stability improved with proper error handling

## [0.1.7] - 2025-11-09

### Added

#### Performance Evaluation Layer
- Complete post-backtest performance analysis framework with extended risk metrics:
  - Stability metrics: rolling Sharpe, consistency scores, regime analysis
  - Risk-adjusted returns: Calmar, Sortino, profit factor, tail ratio
  - Return attribution: directional, signal strength, win/loss decomposition
- `PerformanceConfig` for immutable analysis parameters (frozen dataclass)
- `PerformanceResult` with structured performance summary and diagnostics
- `PerformanceRegistry` for tracking analysis history with JSON catalog
- Markdown report generation with comprehensive metrics and visualizations
- 5-step performance analysis workflow:
  1. Extended metrics calculation (stability, profit factor, tail ratio)
  2. Rolling Sharpe analysis for temporal consistency
  3. Return attribution decomposition
  4. Risk decomposition and diagnostics
  5. Comprehensive reporting with interpretations
- Production-ready notebook (`notebooks/05_performance_analysis.ipynb`) with 31 cells:
  - Registry-driven batch analysis for multiple strategies
  - Comparative performance tables and rankings
  - Individual strategy deep-dive reports
  - Metadata persistence for reproducibility
- Comprehensive test suite with 6 test modules (136 tests total)
- Performance evaluation design documentation (`docs/performance_evaluation_design.md`)

#### Infrastructure Improvements
- Performance report directory structure in project config
- Enhanced backtest persistence with performance metrics in metadata
- Updated backtest notebook to save comprehensive performance data

### Changed
- Removed examples folder and all references (replaced by production notebooks)
  - Cleaned up `pyproject.toml` to remove examples package data
  - Updated documentation to reference notebooks instead of examples
  - Removed example data helpers and demo scripts
- Simplified `.gitignore` to focus on actual runtime artifacts
  - Removed unnecessary `.gitkeep` files from data directories
  - Added performance reports and registry to ignore patterns
- Updated evaluation layer `__init__.py` with performance module exports
- Enhanced governance design documentation with performance layer details
- Updated documentation structure guide with performance evaluation section

### Fixed
- Corrected documentation claims about speculative features
- Improved alignment between design docs and actual implementation

## [0.1.6] - 2025-11-09

### Added

#### Backtest Workflow Notebook
- Complete backtest execution notebook (`notebooks/04_backtest_execution.ipynb`) with 9 cells (execution-only)
  - Strategy registry integration for catalog-driven backtesting
  - Multi-strategy batch execution with error handling
  - Comprehensive performance metrics visualization
  - Signal-strategy alignment validation
  - Metadata persistence for reproducibility
  - Production-ready workflow completing the 4-step research cycle

#### Synthetic Data Support
- Synthetic data generation utilities for development workflow (`notebooks/generate_synthetic_data.py`)
  - CDX, VIX, and ETF synthetic time series generation
  - Configurable market regimes and correlations
  - Documentation for synthetic data usage (`notebooks/README_SYNTHETIC_DATA.md`)
  - Enables full workflow execution without Bloomberg Terminal access

### Changed
- Standardized `product_id` naming to lowercase format across all modules
  - Registry schema updated to use lowercase identifiers (e.g., `cdx_ig_5y`)
  - Strategy catalog updated with lowercase product references
  - All notebooks and examples updated for consistency
- Enhanced signal computation notebook with improved visualizations
  - Better subplot layouts and formatting
  - Clearer correlation heatmap presentation
- Refactored signal computation notebook to use fetch functions instead of hardcoded cache paths
- Updated documentation to reflect current codebase state and workflow completeness

### Fixed
- Added missing imports to signal computation notebook
- Removed deprecated `tenor` field from DataRegistry schema
- Improved suitability evaluation workflow notebook organization

## [0.1.5] - 2025-11-08

### Added

#### Research Workflow Notebooks
- Complete systematic research workflow notebooks included in PyPI distribution
- `notebooks/01_data_download.ipynb` - Bloomberg data download (21 cells)
  - Automated download for all configured securities (CDX, VIX, ETF)
  - BloombergSource integration with graceful error handling
  - Cache directory management and validation
  - Sample data generation for missing securities
  - Comprehensive logging and progress tracking
- `notebooks/02_signal_computation.ipynb` - Signal computation (20 cells)
  - Batch signal computation from cached Bloomberg data
  - SignalRegistry integration for catalog-driven signal generation
  - Comprehensive validation (z-score normalization, alignment, correlations)
  - Plotly visualizations (individual signals, 3-panel subplot, correlation heatmap)
  - Metadata persistence for reproducibility
  - Production-ready workflow with error handling
- `notebooks/__init__.py` - Package initialization with workflow documentation
  - Notebook sequence documentation
  - Workflow position markers for each step
  - Prerequisites and outputs clearly defined

#### Distribution Improvements
- Research notebooks now included in PyPI package (`aponyx/notebooks/`)
- Notebooks accessible after installation for copy/modification
- Updated packaging to include notebook JSON files

#### Examples Enhancements
- Signal suitability evaluation added to `end_to_end_demo.ipynb`
  - Pre-backtest quality gate demonstration
  - PASS/HOLD/FAIL decision workflow
  - Component scoring breakdown visualization

### Changed
- Updated `.gitignore` to preserve `notebooks/` directory structure
- Enhanced `README.md` with research notebooks section and workflow documentation
- Updated `PROJECT_STATUS.md` to reflect notebook distribution
- Copilot instructions updated with notebook workflow context
- `pyproject.toml` now includes notebook files in package data

### Fixed
- Bloomberg demo error handling for missing Terminal connection
- Suitability report path references in demo notebook

## [0.1.4] - 2025-11-07

### Added

#### Evaluation Layer
- Signal-product suitability assessment framework with 4-component scoring:
  - Data health (20%): Sample size and missing data quality
  - Predictive association (40%): Statistical significance via OLS regression
  - Economic relevance (20%): Effect size in basis points
  - Temporal stability (20%): Subperiod beta sign consistency
- `SuitabilityConfig` for immutable evaluation parameters (frozen dataclass)
- `SuitabilityResult` with structured PASS/HOLD/FAIL decisions
- `SuitabilityRegistry` for tracking evaluation history with JSON catalog
- Markdown report generation with component breakdowns and interpretations
- Statistical tests: correlation, OLS regression, subperiod analysis
- Configurable scoring thresholds and component weights
- Comprehensive test suite with 7 test modules
- Suitability demonstration example (`suitability_demo.py`)
- 10 sample evaluation reports in `reports/suitability/demo_reports/`

#### Distribution Improvements
- Documentation now included in PyPI package distribution (`src/aponyx/docs/`)
- Examples included in PyPI package distribution (`src/aponyx/examples/`)
- Helper functions for locating docs and examples after installation:
  - `get_docs_dir()` for accessing documentation
  - `get_examples_dir()` for locating example scripts
- Examples can now be run via `python -m aponyx.examples.<demo_name>`

### Changed
- All demonstration examples now use Bloomberg Terminal as primary data source with graceful fallback to synthetic data
- `data_demo.py`: BloombergSource with FileSource fallback
- `models_demo.py`: Bloomberg fetches for CDX/VIX/ETF data
- `backtest_demo.py`: Real market data (2024-01-01 to present)
- `persistence_demo.py`: Bloomberg fetch → save → register workflow
- `end_to_end_demo.ipynb`: Updated for Bloomberg integration
- Performance metrics now consolidated into `run_metadata.json` under `performance_metrics` key
- Type hints cleaned up across examples folder to use modern Python syntax

### Fixed
- Bloomberg provider implementation corrected and validated with comprehensive tests
- `.gitignore` patterns updated to properly exclude runtime data while preserving static config
- Type annotations in examples now follow project guidelines consistently

### Documentation
- Updated `PROJECT_STATUS.md` for accuracy and clarity
- Added evaluation layer to architecture documentation
- Research workflow diagram showing PASS/FAIL quality gate branching
- Complete methodology documentation in `signal_suitability_evaluation.md`
- Updated Bloomberg requirements with installation instructions
- Consolidated dependency sections and repository structure
- Added agent context hints for evaluation layer in `copilot-instructions.md`

## [0.1.3] - 2025-11-02

### Fixed
- Package data paths now use package-relative resolution instead of project-relative
- JSON catalog files (signals, strategies, Bloomberg config) now correctly located in installed package
- Added explicit package data inclusion in `pyproject.toml` for JSON catalogs and `py.typed` marker
- Resolved `FileNotFoundError` when accessing Bloomberg configuration after pip installation

### Changed
- Config module now distinguishes between `PACKAGE_ROOT` (installed location) and `PROJECT_ROOT` (development location)
- Catalog paths (`SIGNAL_CATALOG_PATH`, `STRATEGY_CATALOG_PATH`, `BLOOMBERG_SECURITIES_PATH`, `BLOOMBERG_INSTRUMENTS_PATH`) now reference `PACKAGE_ROOT` for distribution compatibility
- Data paths (`DATA_DIR`, `REGISTRY_PATH`, `LOGS_DIR`, `CACHE_DIR`) remain project-relative for user data management

## [0.1.2] - 2025-11-02

### Added

#### Governance Framework
- Strategy registry system for centralized strategy management (`backtest/registry.py`)
- JSON-based strategy catalog with versioning and metadata tracking (`strategy_catalog.json`)
- Comprehensive integration tests validating cross-component workflows (`tests/governance/`)
- Configuration management supporting multiple strategy configurations
- Protocol-based adapters for decoupled signal/spread inputs

#### Examples Enhancement
- Bloomberg data provider demonstration (`bloomberg_demo.py`)
- Complete persistence workflow examples (`persistence_demo.py`)
- Enhanced backtest examples demonstrating strategy registry patterns
- Improved models examples with catalog-based signal retrieval
- Streamlined and modernized data examples

#### Documentation
- Expanded governance design plan with implementation details
- Enhanced examples navigation with governance workflow guidance
- Strategy catalog inline documentation with JSON schema

### Changed
- Refactored backtest examples to use strategy registry
- Updated models examples to demonstrate catalog integration
- Modernized data examples for clarity and consistency

### Fixed
- Strategy/signal compatibility validation in registry
- Cross-module integration patterns in backtest layer

## [0.1.1] - 2025-11-01

### Fixed
- Python version requirement corrected from 3.13 to 3.12 in documentation and metadata

## [0.1.0] - 2025-11-01

### Added

#### Data Layer
- File-based data loading with Parquet support (`FileSource`)
- Bloomberg Terminal integration via xbbg wrapper (`BloombergSource`)
- Schema validation for CDX, VIX, and ETF data
- TTL-based caching system with configurable expiration (`DataCache`)
- Data registry with metadata tracking (`DataRegistry`)
- Sample data generation for testing and examples
- Fetch functions: `fetch_cdx`, `fetch_vix`, `fetch_etf`

#### Models Layer
- Three pilot signals for CDX overlay strategy:
  - `compute_cdx_etf_basis` - Flow-driven mispricing from CDX-ETF basis
  - `compute_cdx_vix_gap` - Cross-asset risk sentiment divergence
  - `compute_spread_momentum` - Short-term continuation in spreads
- Signal registry pattern with JSON catalog (`SignalRegistry`)
- Batch signal computation (`compute_registered_signals`)
- Configurable signal parameters (`SignalConfig`)
- Signal catalog management utilities (`SignalCatalog`)

#### Backtest Layer
- Core backtesting engine (`run_backtest`)
- Position generation with entry/exit thresholds
- P&L simulation with transaction cost modeling
- Comprehensive performance metrics:
  - Sharpe, Sortino, Calmar ratios
  - Maximum drawdown and duration tracking
  - Win rate and profit factor
  - Trade statistics and holding period analysis
- Metadata logging with timestamps and parameters
- Protocol-based adapters for signal/spread inputs

#### Persistence Layer
- Parquet I/O with column filtering and date ranges
- JSON I/O for metadata and configuration
- Data registry system for tracking datasets
- Module-level logging at INFO and DEBUG levels

#### Visualization Layer
- Core plotting functions:
  - `plot_equity_curve` - Cumulative P&L visualization
  - `plot_signal` - Signal values with entry/exit thresholds
  - `plot_drawdown` - Underwater chart
- `Visualizer` class for theme management
- Returns Plotly `Figure` objects for flexible rendering

#### Testing
- Comprehensive unit tests for all implemented layers
- Deterministic test data with fixed random seeds
- Pytest configuration with coverage tracking
- Tests for API contracts, calculations, and error handling

#### Documentation
- Complete design documentation:
  - Investment strategy and signal definitions
  - Python code standards and best practices
  - Logging conventions and metadata design
  - Signal registry usage workflow
  - Visualization architecture
  - Caching design principles
  - Data provider extension guide
  - Documentation structure guidelines
- Runnable examples for each layer
- NumPy-style docstrings throughout codebase
- Copilot instructions for AI-assisted development

### Design Decisions
- Python 3.13+ required (no backward compatibility)
- Modern type syntax (`str | None`, `dict[str, Any]`)
- Functions over classes (use `@dataclass` for data containers)
- Signal sign convention: positive = long credit risk
- Independent signal evaluation before combination
- File-based persistence only (Parquet/JSON, no databases)
- Visualization functions return figures without auto-display
- TTL-based caching (not LRU)
- Module-level loggers (no `basicConfig` in library code)

### Known Limitations
- Streamlit dashboard is a placeholder (not yet implemented)
- Advanced attribution charts are stubs (`NotImplementedError`)
- Bloomberg integration requires active Terminal session
- No multi-asset portfolio backtesting yet
- Binary position sizing only (on/off)

[0.1.19]: https://github.com/stabilefrisur/aponyx/compare/v0.1.18...v0.1.19
[0.1.18]: https://github.com/stabilefrisur/aponyx/compare/v0.1.17...v0.1.18
[0.1.17]: https://github.com/stabilefrisur/aponyx/compare/v0.1.16...v0.1.17
[0.1.16]: https://github.com/stabilefrisur/aponyx/compare/v0.1.15...v0.1.16
[0.1.15]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.15
[0.1.14]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.14
[0.1.13]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.13
[0.1.12]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.12
[0.1.11]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.11
[0.1.10]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.10
[0.1.9]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.9
[0.1.8]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.8
[0.1.7]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.7
[0.1.6]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.6
[0.1.5]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.5
[0.1.4]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.4
[0.1.3]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.3
[0.1.2]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.2
[0.1.1]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.1
[0.1.0]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.0
