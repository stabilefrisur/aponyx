# Example Scripts Planning Document

**Purpose:** Define standards and patterns for creating minimal, production-ready example scripts that demonstrate each step in the systematic research workflow.

**Target Audience:** Researchers implementing strategies, developers building workflows, users learning the framework.

---

## Design Principles

### 1. Simplicity First
- **One concept per script** — Focus on a single workflow step
- **Minimal code** — Show only what's essential to demonstrate the concept
- **No cruft** — No print statements, verbose logging, or unnecessary complexity
- **Standalone execution** — Each script should run independently with minimal setup

### 2. Documentation Through Docstrings
- **Module docstring** explains the workflow step and prerequisites
- **Function docstrings** describe purpose, inputs, outputs (NumPy style)
- **No inline comments** unless explaining non-obvious design decisions
- **No print statements** — Let the code speak for itself

### 3. Production-Ready Patterns
- **Drop-in ready** — Scripts can be copied directly into research workflows
- **Framework patterns** — Use registries, catalogs, and configs correctly
- **Proper file paths** — Use config constants, avoid hardcoding
- **Load from previous steps** — Assume earlier workflow steps completed

### 4. Progressive Workflow
- **Each script builds on previous outputs** — No repetition of earlier steps
- **Single signal focus** — Demonstrate complete workflow for one signal
- **File-based handoff** — Load results from previous step's output location

---

## Script Organization

### File Naming Convention
```
{step_number}_{action}_{subject}.py
```

### Directory Structure
```
src/aponyx/examples/
  PLANNING.md                           # This file
  01_generate_synthetic_data.py         # Generate test data
  02_fetch_data_file.py                 # Load all instruments from files
  03_fetch_data_bloomberg.py            # Load all instruments from Bloomberg
  04_compute_signal.py                  # Generate signal (choose from catalog)
  05_evaluate_suitability.py            # Pre-backtest evaluation
  06_run_backtest.py                    # Execute backtest
  07_analyze_performance.py             # Post-backtest analysis
  08_visualize_results.py               # Generate charts
```

---

## Script Template Pattern

Every script should follow this structure:

```python
"""
Brief description of workflow step.

Prerequisites
-------------
- List what must exist before running this script
- Data files, configuration, previous outputs

Outputs
-------
- List what this script produces
- File paths, data structures, console output

Examples
--------
How to run this script and what to expect.
"""

from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

from aponyx.data import fetch_cdx, FileSource
from aponyx.config import DATA_DIR


def main() -> None:
    """
    Execute the workflow step.
    
    This function orchestrates the step with clear separation:
    1. Define inputs/configuration
    2. Execute core logic
    3. Handle outputs
    """
    # 1. Configuration
    config = define_config()
    
    # 2. Core logic
    result = execute_step(config)
    
    # 3. Output handling (minimal)
    save_result(result)


def define_config() -> dict[str, Any]:
    """
    Define configuration for this workflow step.
    
    Returns
    -------
    dict[str, Any]
        Configuration parameters.
    """
    return {
        "param1": "value1",
        "param2": 42,
    }


def execute_step(config: dict[str, Any]) -> pd.DataFrame:
    """
    Execute the core logic of this workflow step.
    
    Parameters
    ----------
    config : dict[str, Any]
        Configuration parameters.
    
    Returns
    -------
    pd.DataFrame
        Result of the step.
    """
    # Implementation
    pass


def save_result(result: pd.DataFrame) -> None:
    """
    Save result to appropriate location.
    
    Parameters
    ----------
    result : pd.DataFrame
        Data to save.
    """
    # Save implementation
    pass


if __name__ == "__main__":
    main()
```

---

## Documentation Standards

### Module Docstring Requirements

Every script must have a module docstring with:

1. **One-line summary** of the workflow step
2. **Prerequisites section** listing required inputs
3. **Outputs section** describing what the script produces
4. **Examples section** showing how to run it

**Example:**
```python
"""
Load all market data instruments from file sources.

Prerequisites
-------------
Raw data files must exist:
- data/raw/synthetic/cdx_ig_5y.parquet
- data/raw/synthetic/vix.parquet
- data/raw/synthetic/hyg.parquet

Outputs
-------
Validated DataFrames for each instrument:
- CDX: spread column with DatetimeIndex
- VIX: level column with DatetimeIndex
- ETF: close column with DatetimeIndex

Examples
--------
Run from project root:
    python -m aponyx.examples.02_fetch_data_file

Expected output: Three validated DataFrames with ~500 rows each.
"""
```

### Function Docstring Requirements

All functions must have NumPy-style docstrings with:

1. **One-line summary** (imperative mood: "Execute", "Load", "Compute")
2. **Parameters section** with types (if not trivial)
3. **Returns section** with type and description
4. **Raises section** (only if function explicitly raises)
5. **Notes section** (only if context needed)

**Omit:**
- Examples (module docstring handles this)
- See Also (keep scripts self-contained)
- References (not needed for examples)

---

## Type Hints and Imports

### Type Hint Standards

```python
# Always use modern Python syntax
from pathlib import Path
from typing import Any

def process_data(
    data: pd.DataFrame,
    filters: list[str] | None = None,
) -> pd.DataFrame | None:
    """Process data with optional filters."""
    pass

# Use Path for file paths
def load_file(path: Path) -> pd.DataFrame:
    """Load data file."""
    pass

# Use TypedDict for structured dicts
from typing import TypedDict

class Config(TypedDict):
    lookback: int
    threshold: float

def configure() -> Config:
    """Build configuration."""
    return {"lookback": 20, "threshold": 1.5}
```

### Import Organization

```python
# 1. Standard library
from pathlib import Path
from datetime import datetime

# 2. Third-party
import pandas as pd
import numpy as np

# 3. Local (use absolute imports in examples)
from aponyx.data import fetch_cdx, FileSource
from aponyx.models import compute_cdx_etf_basis, SignalConfig
from aponyx.backtest import run_backtest, BacktestConfig
from aponyx.config import DATA_DIR, RAW_DIR
```

**Never use relative imports in examples** (they're meant to be standalone).

---

## Code Style Requirements

### Functions Over Classes

Examples should use **pure functions** whenever possible:

```python
# ✅ GOOD: Simple, clear, testable
def compute_signal(
    cdx_df: pd.DataFrame,
    config: SignalConfig,
) -> pd.Series:
    """Compute spread momentum signal."""
    return compute_spread_momentum(cdx_df, config)

# ❌ AVOID: Unnecessary class wrapper
class SignalComputer:
    def __init__(self, config: SignalConfig):
        self.config = config
    
    def compute(self, cdx_df: pd.DataFrame) -> pd.Series:
        return compute_spread_momentum(cdx_df, self.config)
```

### Minimal Error Handling

Let framework functions handle errors. Don't add defensive checks:

```python
# ✅ GOOD: Framework handles validation
def load_data(path: Path, security: str) -> pd.DataFrame:
    """Load and validate CDX data."""
    return fetch_cdx(FileSource(path), security=security)

# ❌ AVOID: Defensive error handling
def load_data(path: Path, security: str) -> pd.DataFrame:
    """Load and validate CDX data."""
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    
    df = fetch_cdx(FileSource(path), security=security)
    
    if df.empty:
        raise ValueError("Empty DataFrame")
    
    return df
```

### No Logging in Examples

**Exception:** Only use logging if demonstrating logging patterns.

```python
# ✅ DEFAULT: No logging
def compute_signal(df: pd.DataFrame) -> pd.Series:
    """Compute momentum signal."""
    return compute_spread_momentum(df)

# ❌ AVOID: Unnecessary logging noise
import logging
logger = logging.getLogger(__name__)

def compute_signal(df: pd.DataFrame) -> pd.Series:
    """Compute momentum signal."""
    logger.info("Computing signal with %d rows", len(df))
    result = compute_spread_momentum(df)
    logger.info("Generated %d signal values", result.notna().sum())
    return result
```

### No Print Statements

**Never use print()** — Let docstrings and return values speak:

```python
# ✅ GOOD: Clean output
def main() -> None:
    """Execute workflow step."""
    df = load_data()
    signal = compute_signal(df)
    save_signal(signal)

# ❌ AVOID: Verbose output
def main() -> None:
    """Execute workflow step."""
    print("Loading data...")
    df = load_data()
    print(f"Loaded {len(df)} rows")
    
    print("Computing signal...")
    signal = compute_signal(df)
    print(f"Generated {signal.notna().sum()} signals")
    
    print("Saving results...")
    save_signal(signal)
    print("Done!")
```

---

## Workflow Coverage

Complete single-signal research pipeline:

| Step | Script | Purpose | Input | Output |
|------|--------|---------|-------|--------|
| **1** | `01_generate_synthetic_data.py` | Generate test data for all instruments | None | `data/raw/synthetic/*.parquet` (CDX, VIX, ETF) |
| **2** | `02_fetch_data_file.py` | Load all instruments from files | Raw files | Validated DataFrames (CDX, VIX, ETF) |
| **3** | `03_fetch_data_bloomberg.py` | Load all instruments from Bloomberg | Bloomberg Terminal | `data/raw/bloomberg/*.parquet` + cache |
| **4** | `04_compute_signal.py` | Generate signal (from catalog) | Market data | `data/processed/signals/*.parquet` |
| **5** | `05_evaluate_suitability.py` | Pre-backtest screening | Signal + spreads | Suitability result |
| **6** | `06_run_backtest.py` | Execute backtest | Signal + config | `data/processed/backtests/*.parquet` |
| **7** | `07_analyze_performance.py` | Compute metrics | Backtest result | Performance metrics |
| **8** | `08_visualize_results.py` | Generate charts | Backtest result | Plotly figures |

---

## Data Storage Patterns

### Raw Data (Permanent Source of Truth)

```python
from aponyx.config import RAW_DIR

# Synthetic data
synthetic_dir = RAW_DIR / "synthetic"
cdx_path = synthetic_dir / "cdx_ig_5y.parquet"

# Bloomberg data (hash-based naming handled by fetch functions)
bloomberg_dir = RAW_DIR / "bloomberg"
# Files saved as: {instrument}_{hash}.parquet
```

### Cache (Temporary Performance Optimization)

```python
from aponyx.config import CACHE_DIR

# Cache files (auto-managed by fetch functions)
# Location: CACHE_DIR / {provider}_{instrument}_{hash}.parquet
# TTL controlled by CACHE_TTL_DAYS config
```

### Processed Data (Derived Outputs)

```python
from aponyx.config import PROCESSED_DIR

# Signals
signals_dir = PROCESSED_DIR / "signals"
signal_path = signals_dir / "spread_momentum.parquet"

# Backtest results
backtests_dir = PROCESSED_DIR / "backtests"
backtest_path = backtests_dir / "spread_momentum_balanced.parquet"
```

### File Path Resolution

Use config constants and programmatic naming:

```python
from aponyx.config import RAW_DIR, PROCESSED_DIR

# ✅ GOOD: Config-based with programmatic naming
def get_signal_path(signal_name: str) -> Path:
    """Resolve signal output path."""
    return PROCESSED_DIR / "signals" / f"{signal_name}.parquet"

def get_backtest_path(signal_name: str, strategy_name: str) -> Path:
    """Resolve backtest output path."""
    return PROCESSED_DIR / "backtests" / f"{signal_name}_{strategy_name}.parquet"

# ❌ AVOID: Hardcoded paths
signal_path = Path("data/processed/signals/spread_momentum.parquet")
```

---

## Registry and Catalog Usage

### Data Registry (Mutable Dataset Tracking)

```python
from aponyx.config import REGISTRY_PATH, DATA_DIR
from aponyx.data.registry import DataRegistry

# Load registry
registry = DataRegistry(REGISTRY_PATH, DATA_DIR)

# Query datasets
all_datasets = registry.list_datasets()
cdx_datasets = registry.list_datasets(instrument="CDX.NA.IG")

# Get dataset info
info = registry.get_dataset_info("raw_synthetic_cdx_ig_5y")
file_path = info["file_path"]
```

### Signal Catalog (Immutable Signal Definitions)

```python
from aponyx.config import SIGNAL_CATALOG_PATH
from aponyx.models.registry import SignalRegistry

# Load catalog
registry = SignalRegistry(SIGNAL_CATALOG_PATH)

# Query signals
enabled = registry.get_enabled()
metadata = registry.get_metadata("spread_momentum")

# Get compute function name
func_name = metadata.compute_function_name  # "compute_spread_momentum"
```

### Strategy Catalog (Immutable Strategy Definitions)

```python
from aponyx.config import STRATEGY_CATALOG_PATH
from aponyx.backtest.registry import StrategyRegistry

# Load catalog
registry = StrategyRegistry(STRATEGY_CATALOG_PATH)

# Get strategy config
metadata = registry.get_metadata("balanced")
config = metadata.to_config()  # Returns BacktestConfig

# Run backtest with catalog strategy
result = run_backtest(signal, spread, config)
```

---

## Anti-Patterns to Avoid

### ❌ Tutorial-Style Prose

Don't write explanatory text outside docstrings:

```python
# ❌ BAD: Narrative comments
# Now we need to load the data from the file system.
# This uses the FileSource which abstracts file loading.
cdx_df = fetch_cdx(FileSource(path), security="cdx_ig_5y")

# Then we validate the schema to ensure data quality.
# This step is critical because...
validate_cdx_schema(cdx_df)
```

**Instead:** Use clear function names and docstrings.

### ❌ Over-Engineering

Don't add abstractions or complexity:

```python
# ❌ BAD: Unnecessary abstraction
class DataLoader:
    def __init__(self, source: FileSource):
        self.source = source
    
    def load_and_validate(self, security: str) -> pd.DataFrame:
        df = fetch_cdx(self.source, security=security)
        validate_cdx_schema(df)
        return df

# ✅ GOOD: Direct and simple
def load_cdx_data(path: Path, security: str) -> pd.DataFrame:
    """Load and validate CDX data from file."""
    df = fetch_cdx(FileSource(path), security=security)
    return df
```

### ❌ Repeating Previous Steps

Load from previous step outputs, don't repeat:

```python
# ❌ BAD: Re-fetching data in signal computation script
def main() -> None:
    """Compute signal."""
    # Don't re-fetch data that was already saved
    cdx_df = fetch_cdx(FileSource(RAW_DIR / "synthetic" / "cdx_ig_5y.parquet"))
    signal = compute_spread_momentum(cdx_df)
    save_parquet(signal, PROCESSED_DIR / "signals" / "spread_momentum.parquet")

# ✅ GOOD: Load from previous step's output
def main() -> None:
    """Compute signal."""
    # Assume data fetching already done in earlier script
    cdx_df = load_parquet(RAW_DIR / "synthetic" / "cdx_ig_5y.parquet")
    signal = compute_spread_momentum(cdx_df)
    save_parquet(signal, PROCESSED_DIR / "signals" / "spread_momentum.parquet")
```

### ❌ Mixing Concerns

Keep examples focused on one workflow step:

```python
# ❌ BAD: Multiple workflow steps in one script
def main() -> None:
    """Run complete pipeline."""
    cdx_df = fetch_cdx(FileSource(raw_path))
    signal = compute_spread_momentum(cdx_df)
    result = run_backtest(signal, cdx_df["spread"])
    fig = plot_equity_curve(result.pnl)

# ✅ GOOD: One script per step
# 02_fetch_data_file.py (data loading)
# 04_compute_signal.py (signal computation)
# 06_run_backtest.py (backtest execution)
# 08_visualize_results.py (visualization)
```

## Summary Checklist

When creating a new example script, ensure:

- [ ] **Module docstring** includes Prerequisites, Outputs, Examples
- [ ] **All functions have NumPy docstrings**
- [ ] **No print statements** or verbose logging
- [ ] **Type hints use modern Python syntax**
- [ ] **Uses absolute imports** from aponyx
- [ ] **Follows template pattern** (main → config → execute → save)
- [ ] **Uses config constants** for all paths (RAW_DIR, PROCESSED_DIR, etc.)
- [ ] **Loads from previous step outputs** (no repetition)
- [ ] **Demonstrates one workflow step** clearly
- [ ] **Uses registries/catalogs correctly** where applicable
- [ ] **Follows Python guidelines** (see python_guidelines.md)
- [ ] **Production-ready** (can be dropped into actual workflow)
