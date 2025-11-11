# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.7]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.7
[0.1.6]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.6
[0.1.5]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.5
[0.1.4]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.4
[0.1.3]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.3
[0.1.2]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.2
[0.1.1]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.1
[0.1.0]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.0
