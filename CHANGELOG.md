# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.2]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.2
[0.1.1]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.1
[0.1.0]: https://github.com/stabilefrisur/aponyx/releases/tag/v0.1.0
