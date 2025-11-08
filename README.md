# Aponyx

[![PyPI version](https://img.shields.io/pypi/v/aponyx.svg)](https://pypi.org/project/aponyx/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A modular Python framework for developing and backtesting systematic credit strategies.**

Aponyx provides a type-safe, reproducible research environment for tactical fixed-income strategies. Built for investment professionals who need clean separation between strategy logic, data infrastructure, and backtesting workflows.

## Key Features

- **Type-safe data loading** with schema validation (Parquet, CSV, Bloomberg Terminal)
- **Modular signal framework** with composable transformations and registry management
- **Deterministic backtesting** with transaction cost modeling and comprehensive metrics
- **Interactive visualization** with Plotly charts (equity curves, signals, drawdown)
- **Production-ready persistence** with metadata tracking and versioning
- **Strategy governance** with centralized registry and configuration management

## Installation

### From PyPI (Recommended)

```bash
pip install aponyx
```

**Optional dependencies:**

```bash
# Visualization (Plotly, Streamlit)
pip install aponyx[viz]

# Bloomberg Terminal support (requires manual blpapi install)
pip install aponyx[bloomberg]

# Development tools
pip install aponyx[dev]
```

### From Source

Requires **Python 3.12** and [`uv`](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/stabilefrisur/aponyx.git
cd aponyx
uv sync                    # Install dependencies
uv sync --extra viz        # Include visualization
uv run python -m aponyx.examples.backtest_demo
```

### Bloomberg Terminal Setup (Optional)

> **Note:** Bloomberg data loading requires an active Terminal session and manual `blpapi` installation.

1. Download `blpapi` from Bloomberg's API Library
2. Install: `pip install path/to/blpapi-*.whl`
3. Install Bloomberg extra: `pip install aponyx[bloomberg]`

File-based data loading (`FileSource`) works without Bloomberg dependencies.

## Quick Start

```python
from aponyx.data import fetch_cdx, fetch_etf, FileSource
from aponyx.models import compute_cdx_etf_basis, SignalConfig
from aponyx.backtest import run_backtest, BacktestConfig, compute_performance_metrics

# Load validated market data
cdx_df = fetch_cdx(FileSource("data/raw/cdx_data.parquet"), security="cdx_ig_5y")
etf_df = fetch_etf(FileSource("data/raw/etf_data.parquet"), security="hyg")

# Generate signal with configuration
signal_config = SignalConfig(lookback=20, min_periods=10)
signal = compute_cdx_etf_basis(cdx_df, etf_df, signal_config)

# Evaluate signal-product suitability (optional pre-backtest gate)
from aponyx.evaluation import evaluate_signal_suitability
result = evaluate_signal_suitability(signal, cdx_df["spread"])
if result.decision != "PASS":
    print(f"Signal evaluation: {result.decision} (score: {result.composite_score:.2f})")
    # Optionally skip backtest for low-quality signals

# Run backtest with transaction costs
backtest_config = BacktestConfig(
    entry_threshold=1.5,
    exit_threshold=0.75,
    transaction_cost_bps=1.0
)
results = run_backtest(signal, cdx_df["spread"], backtest_config)

# Compute performance metrics
metrics = compute_performance_metrics(results.pnl, results.positions)

# Analyze results
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: ${metrics.max_drawdown:,.0f}")
print(f"Hit Rate: {metrics.hit_rate:.2%}")
```

**Bloomberg Terminal alternative:**

```python
from aponyx.data import BloombergSource

source = BloombergSource()
cdx_df = fetch_cdx(source, security="cdx_ig_5y")
```

## Architecture

Aponyx follows a **layered architecture** with clean separation of concerns:

| Layer | Purpose | Key Modules |
|-------|---------|-------------|
| **Data** | Load, validate, transform market data | `fetch_cdx`, `fetch_vix`, `fetch_etf`, `FileSource`, `BloombergSource` |
| **Models** | Generate signals for independent evaluation | `compute_cdx_etf_basis`, `compute_cdx_vix_gap`, `SignalRegistry` |
| **Evaluation** | Pre-backtest signal screening and quality gates | `evaluate_signal_suitability`, `SuitabilityRegistry` |
| **Backtest** | Simulate execution and compute metrics | `run_backtest`, `BacktestConfig`, `StrategyRegistry` |
| **Visualization** | Interactive charts and dashboards | `plot_equity_curve`, `plot_signal`, `plot_drawdown` |
| **Persistence** | Save/load data with metadata registry | `save_parquet`, `load_parquet`, `DataRegistry` |

### Research Workflow

```
Raw Data (Parquet/CSV/Bloomberg)
    ↓
Data Layer (load, validate, transform)
    ↓
Models Layer (signal computation)
    ↓
Evaluation Layer (signal-product suitability)
    ├─ PASS → Backtest Layer (simulation, metrics)
    │            ↓
    │         Visualization Layer (charts)
    │            ↓
    │         Persistence Layer (results)
    │
    └─ FAIL → Archive (no backtest)
```

## Examples

Examples are included with the installed package and demonstrate specific workflows with synthetic data.

**After installing via PyPI:**

```bash
# Locate installed examples
python -c "from aponyx.examples import get_examples_dir; print(get_examples_dir())"

# Run examples as modules
python -m aponyx.examples.data_demo          # Data loading and validation
python -m aponyx.examples.models_demo        # Signal generation and catalog
python -m aponyx.examples.suitability_demo   # Pre-backtest signal screening
python -m aponyx.examples.backtest_demo      # Complete backtest workflow
python -m aponyx.examples.visualization_demo # Interactive charts (requires viz extra)
python -m aponyx.examples.persistence_demo   # Data I/O and registry
python -m aponyx.examples.bloomberg_demo     # Bloomberg Terminal integration
```

**During development:**

```bash
# Clone repo and run directly
git clone https://github.com/stabilefrisur/aponyx.git
cd aponyx
uv sync
uv run python -m aponyx.examples.backtest_demo
```

## Research Notebooks

Complete workflow notebooks are included in the package for end-to-end research workflows.

**Access installed notebooks:**

```python
# Locate notebook directory
from pathlib import Path
import aponyx
notebooks_dir = Path(aponyx.__file__).parent / "notebooks"
print(notebooks_dir)
```

**Workflow notebooks:**

| Notebook | Description |
|----------|-------------|
| `01_data_download.ipynb` | Download market data from Bloomberg Terminal |
| `02_signal_computation.ipynb` | Generate signals using SignalRegistry (coming soon) |
| `03_suitability_evaluation.ipynb` | Pre-backtest signal screening (coming soon) |
| `04_backtest.ipynb` | Execute backtests and compute metrics (coming soon) |
| `05_analysis.ipynb` | Visualize results and generate reports (coming soon) |

**Usage:**

```bash
# Copy notebooks to your workspace
pip install aponyx[viz]  # Install with notebook dependencies
python -c "from pathlib import Path; import aponyx, shutil; src = Path(aponyx.__file__).parent / 'notebooks'; shutil.copytree(src, 'notebooks')"
jupyter notebook notebooks/
```

Notebooks demonstrate the complete systematic research workflow from data acquisition through performance analysis.

## Documentation

Documentation is **included with the package** and available after installation:

```python
# Access docs programmatically
from aponyx.docs import get_docs_dir
docs_path = get_docs_dir()
print(docs_path)  # Path to installed documentation
```

**Available documentation:**

| Document | Description |
|----------|-------------|
| `python_guidelines.md` | Code standards and best practices |
| `cdx_overlay_strategy.md` | Investment thesis and pilot implementation |
| `signal_registry_usage.md` | Signal management workflow |
| `signal_suitability_evaluation.md` | Pre-backtest evaluation framework |
| `visualization_design.md` | Chart architecture and patterns |
| `logging_design.md` | Logging conventions and metadata |
| `caching_design.md` | Cache layer architecture |
| `adding_data_providers.md` | Provider extension guide |
| `governance_design.md` | Registry, catalog, and config patterns |

**During development**, docs are also available on GitHub:
- [Documentation Index](https://github.com/stabilefrisur/aponyx/tree/master/src/aponyx/docs)

## What's Included

### Implemented
- ✅ Type-safe data loading with schema validation (Parquet, CSV, Bloomberg)
- ✅ Modular signal framework with registry and catalog management
- ✅ Deterministic backtesting with transaction costs and comprehensive metrics
- ✅ Interactive Plotly visualizations (equity curves, signals, drawdown)
- ✅ Strategy governance with centralized registry and versioning
- ✅ Metadata tracking and reproducibility controls
- ✅ Comprehensive test suite with >90% coverage

### Pilot Signals
Three signals for CDX overlay strategies:
1. **CDX-ETF Basis** - Flow-driven mispricing from cash-derivative basis
2. **CDX-VIX Gap** - Cross-asset risk sentiment divergence
3. **Spread Momentum** - Short-term continuation in credit spreads

### Roadmap
- 🔜 Streamlit dashboard (architecture defined, implementation pending)
- 🔜 Advanced attribution charts (performance decomposition)
- 🔜 Multi-asset portfolio backtesting
- 🔜 Position sizing and risk budgeting

## Development

### Running Tests

```bash
pytest                              # All tests
pytest --cov=aponyx                # With coverage
pytest tests/models/                # Specific module
```

### Code Quality

```bash
black src/ tests/                   # Format code
ruff check src/ tests/              # Lint
mypy src/                          # Type check
```

All tools are configured in `pyproject.toml` with project-specific settings.

## Design Philosophy

### Core Principles

1. **Modularity** - Clean separation between data, models, backtest, and infrastructure
2. **Reproducibility** - Deterministic outputs with seed control and metadata logging
3. **Type Safety** - Strict type hints and runtime validation throughout
4. **Simplicity** - Prefer functions over classes, explicit over implicit
5. **Transparency** - Clear separation between strategy logic and execution

### Signal Convention

All signals follow a **consistent sign convention** for interpretability:
- **Positive values** → Long credit risk (buy CDX = sell protection)
- **Negative values** → Short credit risk (sell CDX = buy protection)

This ensures clarity when evaluating signals independently or combining them in future research.

## Requirements

- **Python 3.12** (no backward compatibility with 3.11 or earlier)
- Modern type syntax (`str | None`, not `Optional[str]`)
- Optional: Bloomberg Terminal with `blpapi` for live data

## Contributing

Contributions welcome! This is a research framework under active development.

- **Code standards**: See [Python Guidelines](src/aponyx/docs/python_guidelines.md) (or `from aponyx.docs import get_docs_dir` after install)
- **Testing**: All new features require unit tests
- **Documentation**: NumPy-style docstrings required

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- **PyPI**: https://pypi.org/project/aponyx/
- **Repository**: https://github.com/stabilefrisur/aponyx
- **Issues**: https://github.com/stabilefrisur/aponyx/issues
- **Changelog**: https://github.com/stabilefrisur/aponyx/blob/master/CHANGELOG.md

---

**Maintained by stabilefrisur**  
**Version**: 0.1.4  
**Last Updated**: November 7, 2025
