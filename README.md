# Aponyx

[![PyPI version](https://img.shields.io/pypi/v/aponyx.svg)](https://pypi.org/project/aponyx/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modular Python framework for developing and backtesting systematic credit strategies.

> **⚠️ Bloomberg Terminal Required**: Data loading via `BloombergSource` requires an active Bloomberg Terminal session and manual installation of the `blpapi` library. See installation instructions below. File-based alternatives (`FileSource`) are also supported.

## Quick Start

### Installation from PyPI

```bash
pip install aponyx

# Optional: visualization dependencies
pip install aponyx[viz]

# Optional: Bloomberg Terminal support (requires manual blpapi install, see below)
pip install aponyx[bloomberg]
```

### Installation from Source

Requires **Python 3.12** and [`uv`](https://docs.astral.sh/uv/) for environment management.

```bash
# Clone repository
git clone https://github.com/stabilefrisur/aponyx.git
cd aponyx

# Create virtual environment with uv
uv venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Install visualization dependencies (optional)
uv sync --extra viz

# Install Bloomberg support (optional, requires manual blpapi install)
uv sync --extra bloomberg

# Run examples
uv run python examples/backtest_demo.py
```

### Bloomberg Terminal Setup (Optional)

To use the Bloomberg data provider:

1. **Install `blpapi` manually** (not available on PyPI):
   - Download from Bloomberg's API Library
   - Install: `pip install path/to/blpapi-*.whl`

2. **Install Bloomberg extra**:
   ```bash
   pip install aponyx[bloomberg]
   # or with uv
   uv sync --extra bloomberg
   ```

3. **Ensure active Terminal session** before fetching data

### Basic Usage

```python
from aponyx.data import fetch_cdx, fetch_etf, FileSource, BloombergSource
from aponyx.models import compute_cdx_etf_basis, SignalConfig
from aponyx.backtest import run_backtest, BacktestConfig

# Load market data with validation (file-based)
cdx_df = fetch_cdx(FileSource("data/raw/cdx_data.parquet"), security="cdx_ig_5y")
etf_df = fetch_etf(FileSource("data/raw/etf_data.parquet"), security="hyg")

# Or use Bloomberg Terminal (requires active session, manual blpapi install, and aponyx[bloomberg])
# source = BloombergSource()
# cdx_df = fetch_cdx(source, security="cdx_ig_5y")
# etf_df = fetch_etf(source, security="hyg")

# Generate signal
signal_config = SignalConfig(lookback=20, min_periods=10)
signal = compute_cdx_etf_basis(cdx_df, etf_df, signal_config)

# Run backtest
backtest_config = BacktestConfig(entry_threshold=1.5, exit_threshold=0.75)
results = run_backtest(signal, cdx_df["spread"], backtest_config)
print(f"Sharpe Ratio: {results.metrics['sharpe_ratio']:.2f}")
```

## Project Structure

```
aponyx/
├── src/aponyx/       # Core framework
│   ├── data/              # Data loading, validation, transformation
│   ├── models/            # Signal generation for credit strategies
│   ├── backtest/          # Backtesting engine and metrics
│   ├── visualization/     # Plotly charts and Streamlit dashboard
│   ├── persistence/       # Parquet/JSON I/O and registry
│   └── config/            # Configuration and constants
├── examples/              # Runnable demonstrations
├── tests/                 # Unit tests
└── docs/                  # Architecture and design docs
```

### Key Layers

| Layer | Purpose | Entry Point |
|-------|---------|-------------|
| **Data** | Load, validate, transform market data | `aponyx.data` |
| **Models** | Generate signals for independent evaluation | `aponyx.models` |
| **Backtest** | Simulate execution and compute metrics | `aponyx.backtest` |
| **Visualization** | Interactive charts and dashboards | `aponyx.visualization` |
| **Persistence** | Save/load data with metadata registry | `aponyx.persistence` |

## Documentation

### Getting Started
- **[Python Guidelines](docs/python_guidelines.md)** - Code standards and best practices
- **[Examples](examples/)** - Runnable demos for each layer

### Strategy & Architecture
- **[CDX Overlay Strategy](docs/cdx_overlay_strategy.md)** - Investment thesis and pilot implementation
- **[Documentation Structure](docs/documentation_structure.md)** - Single source of truth principles

### Design Guides
- **[Logging Design](docs/logging_design.md)** - Logging conventions and metadata tracking
- **[Signal Registry Usage](docs/signal_registry_usage.md)** - Signal management and research workflow
- **[Visualization Design](docs/visualization_design.md)** - Chart architecture and integration patterns
- **[Caching Design](docs/caching_design.md)** - Cache layer architecture and usage
- **[Adding Data Providers](docs/adding_data_providers.md)** - Provider extension guide

## Features

✅ **Type-safe data loading** with schema validation  
✅ **Modular signal framework** with composable transformations  
✅ **Deterministic backtesting** with transaction cost modeling  
✅ **Interactive visualization** with Plotly charts (equity, signals, drawdown)  
✅ **Parquet-based persistence** with JSON metadata registry  
✅ **Comprehensive logging** with run metadata tracking  
✅ **Bloomberg Terminal integration** via xbbg wrapper (optional `bloomberg` extra, requires manual `blpapi` install)

**Planned Features:**
- 🔜 Streamlit dashboard (stub exists, not yet implemented)
- 🔜 Advanced attribution charts (stubs with NotImplementedError)

## Development

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=aponyx --cov-report=term-missing

# Specific module
uv run pytest tests/models/
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

### Examples

Each example demonstrates a specific layer with synthetic data:

```bash
uv run python examples/data_demo.py          # Data loading and transformation
uv run python examples/models_demo.py        # Signal generation
uv run python examples/backtest_demo.py      # Complete backtest workflow
uv run python examples/visualization_demo.py # Interactive charts (requires viz extra)
uv run python examples/persistence_demo.py   # Data I/O and registry
```

## Design Principles

1. **Modularity** - Separate data, models, backtest, and persistence layers
2. **Reproducibility** - Deterministic outputs with seed control and metadata logging
3. **Type safety** - Strict type hints and runtime validation
4. **Simplicity** - Prefer functions over classes, explicit over implicit
5. **Transparency** - Clear separation between strategy logic and infrastructure

## Architecture Notes

### Signal Convention

All model signals follow a **consistent sign convention**:
- **Positive values** → Long credit risk (buy CDX / sell protection)
- **Negative values** → Short credit risk (sell CDX / buy protection)

This convention ensures clear interpretation when evaluating signals individually
or when combining signals in future experiments.

### Data Flow

```
Raw Data (Parquet/CSV)
    ↓
Data Layer (load, validate, transform)
    ↓
Models Layer (signal computation)
    ↓
Backtest Layer (simulation, metrics)
    ↓
Persistence Layer (save results, metadata)
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

This is a research project under active development. See [Python Guidelines](docs/python_guidelines.md) for code standards.

---

**Maintained by stabilefrisur**  
Version 0.1.0 | Last Updated: October 31, 2025
