# Examples

Runnable demonstrations of the aponyx framework using synthetic market data.

## Prerequisites

- Python 3.12 with `uv` environment manager
- Core dependencies: `pandas`, `numpy` (installed via `uv sync`)
- Optional: visualization dependencies (`uv sync --extra viz` for plotting demos)
- Optional: Bloomberg Terminal (for `bloomberg_demo.py` only)

## Quick Start

```bash
# From project root, ensure dependencies are installed
uv sync

# Run demonstrations
uv run python examples/data_demo.py          # Data fetching, validation, caching
uv run python examples/persistence_demo.py   # Parquet/JSON I/O, registry (209 days)
uv run python examples/models_demo.py        # Registry-based signal generation (252 days)
uv run python examples/backtest_demo.py      # Registry-based strategy evaluation (504 days)

# Bloomberg Terminal integration (requires active Terminal session)
uv run python examples/bloomberg_demo.py     # Exits gracefully if Terminal unavailable

# Visualization demo (requires viz extra)
uv sync --extra viz
uv run python examples/visualization_demo.py # Interactive charts
```

## Example Scripts

| Script | Purpose | Key Features | Expected Output |
|--------|---------|--------------|-----------------|
| `data_demo.py` | Data fetching and validation | FileSource, schema validation, caching demo | Prints fetch results, validation checks, cache behavior |
| `persistence_demo.py` | Data I/O and registry | Parquet/JSON I/O, DataRegistry CRUD, DatasetEntry | File paths, registry queries, type-safe access demos |
| `models_demo.py` | Registry-based signals | SignalRegistry, compute_registered_signals(), batch computation | Signal stats, correlations, distribution analysis |
| `backtest_demo.py` | Registry-based strategies | StrategyRegistry, multi-strategy comparison, metadata tracking | Comparative performance metrics, version tracking |
| `bloomberg_demo.py` | Bloomberg Terminal integration | BloombergSource, ticker lookup, graceful error handling | Data from Terminal OR warning message if unavailable |
| `visualization_demo.py` | Interactive plotting | Equity curves, signals, drawdown charts | Plotly interactive HTML charts |
| `end_to_end_demo.ipynb` | Complete workflow notebook | Registry patterns, governance, metadata tracking | Jupyter notebook with all workflow steps |

All scripts include inline comments explaining each step. See the script source code for detailed documentation.

## Expected Behavior

### Successful Output
Each demo prints structured information about the operations performed:

```bash
# data_demo.py
INFO - Fetching CDX data...
INFO - Loaded 252 rows...
  ✓ CDX schema valid

# models_demo.py
INFO - Computing signals via registry...
  ✓ Computed 3 signals
cdx_etf_basis: valid=232, mean=0.001, std=0.998

# backtest_demo.py
INFO - Backtesting conservative strategy...
  ✓ Complete: 18 trades, Total P&L: $45,231
```

### Common Issues

**Import Error:** "No module named 'aponyx'"
```bash
# Solution: Install package in development mode
uv sync
```

**Missing Visualization Dependencies**
```bash
# Error: "No module named 'plotly'" when running visualization_demo.py
# Solution: Install optional visualization extras
uv sync --extra viz
```

**Bloomberg Terminal Not Available**
```bash
# bloomberg_demo.py will print:
# BLOOMBERG TERMINAL NOT AVAILABLE
# Demo exiting gracefully...
# This is expected behavior if Terminal is not installed or not running
```

**Data Directory Errors**
```bash
# Error: "data/processed/ directory not found"
# Solution: Demos create directories automatically, but ensure write permissions
```

## Test Data

All examples use **`example_data.py`** for consistent synthetic data generation:

```python
from example_data import generate_example_data

# Generate 252 days of synthetic CDX, VIX, and ETF data
cdx_df, vix_df, etf_df = generate_example_data(
    start_date="2024-01-01",
    periods=252,
    seed=42  # Reproducible results
)
```

**Customization:**
- Change `periods=` for different time ranges (63 = 3 months, 1260 = 5 years)
- Change `start_date=` for different date ranges
- Change `seed=` for different random paths (use fixed seeds for reproducibility)

## Registry-Based Patterns

The framework uses registry patterns for governance and reproducibility:

### Signal Registry (`models_demo.py`)
```python
from aponyx.models import SignalRegistry, compute_registered_signals

# Load catalog and compute all enabled signals
registry = SignalRegistry("src/aponyx/models/signal_catalog.json")
signals = compute_registered_signals(registry, market_data, config)
```

### Strategy Registry (`backtest_demo.py`)
```python
from aponyx.backtest import StrategyRegistry

# Load catalog and compare multiple strategies
registry = StrategyRegistry("src/aponyx/backtest/strategy_catalog.json")
for name, metadata in registry.get_enabled().items():
    config = metadata.to_config(position_size=10.0, ...)
    result = run_backtest(signal, spread, config)
```

## Extending Examples

### Creating New Examples

1. Import test data generator:
   ```python
   from example_data import generate_example_data
   ```

2. Generate synthetic data with fixed seed:
   ```python
   cdx_df, vix_df, etf_df = generate_example_data(periods=252, seed=42)
   ```

3. Demonstrate your feature with clear logging and comments

4. Add script description to this README

### Best Practices

**Do:**
- Use `generate_example_data()` for consistency
- Keep examples focused on one layer or feature
- Include logging output to explain operations
- Use type hints in example code
- Show realistic usage patterns
- Demonstrate registry patterns when applicable

**Don't:**
- Duplicate data generation logic across scripts
- Mix concerns from multiple layers in one demo
- Create non-deterministic outputs (always use fixed seeds)
- Hardcode file paths (use `Path` from `pathlib`)
- Use direct function calls when registry patterns exist

---

**Last Updated**: November 2, 2025
