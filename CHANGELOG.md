# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



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
  - `scripts/clean_pycache.py` - Remove Python bytecode and `__pycache__` directories
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
