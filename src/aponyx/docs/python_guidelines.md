# Python Guidelines for Systematic Macro Credit

## Overview

This document defines Python coding standards and best practices for the **Systematic Macro Credit** project. These guidelines ensure code quality, maintainability, and reproducibility across all modules.

**Target Audience:** Developers contributing to investment strategy research, data infrastructure, backtesting, and visualization components.

---

## Python Version and Environment

### Version Requirements
- **Python:** 3.12
- **Environment Manager:** `uv` (preferred)
- **Package Manager:** `uv` or `pip`

### Environment Setup
```bash
# Create environment with uv
uv venv

# Activate environment
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -e ".[dev,viz]"
```

---

## Code Style and Formatting

### Automatic Formatters
- **Black:** Code formatting (line length: 100)
- **Ruff:** Linting and import sorting
- **MyPy:** Static type checking

### Configuration
All style settings are defined in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.mypy]
python_version = "3.12"
```

### Running Formatters
```bash
# Format code
ruff format src/ tests/

# Lint and fix
ruff check --fix src/ tests/

# Type check
mypy src/
```

---

## Type Annotations

### Modern Python Syntax
Use **built-in generics** and **union syntax** (PEP 604):

✅ **CORRECT:**
```python
def process_data(
    data: dict[str, Any],
    filters: list[str] | None = None,
    threshold: int | float = 0.0,
) -> pd.DataFrame | None:
    """Process data with optional filters."""
    ...
```

❌ **AVOID (old syntax):**
```python
from typing import Optional, Union, List, Dict

def process_data(
    data: Dict[str, Any],
    filters: Optional[List[str]] = None,
    threshold: Union[int, float] = 0.0,
) -> Optional[pd.DataFrame]:
    ...
```

### Type Hint Guidelines
1. **All function signatures must include type hints**
2. **Use `Any` sparingly** — prefer specific types
3. **Use `TypedDict` for structured dictionaries**
4. **Mark library as typed** with `py.typed` marker file

### Common Type Patterns
```python
from pathlib import Path
from typing import Any, Literal
from collections.abc import Callable

# Path handling
def load_file(path: str | Path) -> pd.DataFrame:
    ...

# Literal types for restricted values
def set_level(level: Literal["INFO", "DEBUG", "WARNING"]) -> None:
    ...

# Callable types
def apply_transform(
    df: pd.DataFrame,
    func: Callable[[pd.Series], pd.Series],
) -> pd.DataFrame:
    ...

# TypedDict for metadata
from typing import TypedDict

class RunMetadata(TypedDict):
    timestamp: str
    params: dict[str, Any]
    version: str
    rows: int
```

---

## Documentation Standards

### Docstring Format
Use **NumPy-style docstrings** for all public functions and classes:

```python
def compute_spread_momentum(
    spread: pd.Series,
    window: int = 5,
    normalize: bool = True,
) -> pd.Series:
    """
    Compute short-term momentum in CDX spreads using z-score normalization.

    This function calculates rolling momentum and optionally normalizes
    the signal to make it comparable across different market regimes.

    Parameters
    ----------
    spread : pd.Series
        Daily CDX spread levels indexed by date.
    window : int, default 5
        Rolling lookback period in days.
    normalize : bool, default True
        Whether to apply z-score normalization.

    Returns
    -------
    pd.Series
        Momentum signal with same index as input.
        Returns NaN for insufficient data in rolling window.

    Raises
    ------
    ValueError
        If window < 2 or spread contains no valid data.

    Examples
    --------
    >>> spread = pd.Series([100, 102, 101, 103, 105], index=pd.date_range('2024-01-01', periods=5))
    >>> momentum = compute_spread_momentum(spread, window=3)
    >>> print(momentum)

    Notes
    -----
    Z-score normalization: (x - mean) / std over rolling window.
    Requires at least `window` non-null observations to produce output.

    See Also
    --------
    compute_vix_cdx_gap : Cross-asset momentum signal
    """
    if window < 2:
        raise ValueError(f"Window must be >= 2, got {window}")
    
    logger.debug("Computing spread momentum: window=%d, normalize=%s", window, normalize)
    
    # Implementation...
    ...
```

### Documentation Requirements
| Component | Required Documentation |
|-----------|------------------------|
| **Public functions** | Full NumPy docstring with Parameters, Returns, Examples |
| **Private functions** | Brief docstring describing purpose |
| **Classes** | Class-level docstring + method docstrings |
| **Modules** | Module-level docstring at top of file |
| **Complex logic** | Inline comments explaining *why*, not *what* |

### Module-Level Docstrings
```python
"""
CDX overlay strategy implementation.

This module contains the core logic for the systematic CDX overlay strategy,
including signal generation, position sizing, and risk management.

Key Components
--------------
- CDXOverlayModel: Main strategy class
- compute_entry_signal: Generate trade entry signals
- compute_position_size: Dynamic position sizing based on volatility

Dependencies
------------
Requires cleaned market data from `aponyx.data.loader`.
Outputs results compatible with `aponyx.backtest.engine`.

Examples
--------
>>> from aponyx.models.cdx_overlay_model import CDXOverlayModel
>>> model = CDXOverlayModel(lookback=20, threshold=1.5)
>>> signals = model.generate_signals(market_data)
"""
```

---

## Logging Standards

### Logger Initialization
**Always use module-level loggers:**

```python
import logging

logger = logging.getLogger(__name__)
```

### Logging Levels

| Level | Use Case | Example |
|-------|----------|---------|
| **DEBUG** | Implementation details, low-level operations | File sizes, filter details, iteration counts |
| **INFO** | User-facing operations, high-level events | File loaded, backtest started, signal generated |
| **WARNING** | Recoverable errors, missing optional data | Missing optional column, default value used |
| **ERROR** | Operation failures requiring attention | File not found, invalid data format |

### Logging Best Practices

✅ **CORRECT:**
```python
# Use %-formatting for lazy evaluation
logger.info("Loaded %d rows from %s", len(df), path)
logger.debug("Applied filter: column=%s, threshold=%.2f", col_name, threshold)

# Include context in messages
logger.warning("Missing optional column '%s', using default value %s", col, default)

# Log at appropriate levels
logger.info("Starting backtest: params=%s", params)  # User operation
logger.debug("Iteration %d: PnL=%.2f", i, pnl)      # Implementation detail
```

❌ **AVOID:**
```python
# Don't use f-strings (eager evaluation, prevents structured logging)
logger.info(f"Loaded {len(df)} rows from {path}")

# Don't call basicConfig in library code
logging.basicConfig(level=logging.INFO)  # User's responsibility, not library's

# Don't log sensitive information
logger.info(f"API key: {api_key}")  # Security risk

# Don't use print() statements
print("Processing data...")  # Use logger.info() instead
```

### Logging in Tests
```python
# pytest automatically captures logs
# Run tests with logging output:
pytest -v --log-cli-level=INFO

# In test code, logging works normally:
def test_data_loading(tmp_path):
    logger.info("Testing data load with path: %s", tmp_path)
    # Test implementation...
```

**See `logging_design.md` (in same directory) for complete logging architecture.**

---

## Classes vs Functions

### Prefer Functions Over Classes

**Default to functions.** Only introduce classes when they provide clear value.

✅ **Use functions for:**
```python
# Simple transformations
from aponyx.data import apply_transform

def compute_spread_momentum(spread: pd.Series, window: int = 5) -> pd.Series:
    """Pure function - no state needed."""
    return apply_transform(spread, "normalized_change", window=window, periods=window)

# Data processing pipelines
def clean_cdx_data(df: pd.DataFrame) -> pd.DataFrame:
    """Stateless transformation."""
    return df.dropna().sort_index()

# Signal generation
def generate_vix_cdx_gap(vix: pd.Series, cdx: pd.Series, lookback: int) -> pd.Series:
    """Pure computation - easier to test and reason about."""
    vix_z = apply_transform(vix, "z_score", window=lookback)
    cdx_z = apply_transform(cdx, "z_score", window=lookback)
    return vix_z - cdx_z
```

❌ **Avoid classes when functions suffice:**
```python
# BAD: Unnecessary class wrapping a single function
class MomentumCalculator:
    def __init__(self, window: int):
        self.window = window
    
    def calculate(self, spread: pd.Series) -> pd.Series:
        return apply_transform(spread, 'normalized_change', window=self.window)

# GOOD: Simple function
def compute_momentum(spread: pd.Series, window: int) -> pd.Series:
    return apply_transform(spread, 'normalized_change', window=window)
```

### When to Use Classes

**Only use classes when you need:**

1. **State management** (DataRegistry, connection pools)
2. **Multiple related methods** operating on shared state
3. **Lifecycle management** (setup/teardown, context managers)
4. **Plugin/interface patterns** (base classes for strategies)

---

## Classes vs Dataclasses

### When to Use Each

✅ **Use `@dataclass` for data containers:**
```python
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass(frozen=True)
class SignalParameters:
    """Immutable signal parameters with validation."""
    momentum_window: int = 5
    volatility_window: int = 20
    
    def __post_init__(self) -> None:
        if self.momentum_window < 2:
            raise ValueError(f"momentum_window must be >= 2")

@dataclass
class BacktestResult:
    """Mutable container for backtest metrics."""
    sharpe_ratio: float
    total_return: float
    num_trades: int
    metadata: dict[str, Any] = field(default_factory=dict)  # Mutable default
```

❌ **Use regular classes for behavior-heavy components:**
```python
class DataRegistry:
    """Complex state and many methods."""
    def __init__(self, registry_path: Path, data_directory: Path):
        self.registry_path = registry_path
        self._catalog = self._load_or_create()
    
    def register_dataset(self, ...) -> None: ...
    def update_dataset_stats(self, ...) -> None: ...
```

### Decision Guide

| Use Case | Choose | Why |
|----------|--------|-----|
| Config/parameters | `@dataclass(frozen=True)` | Immutable, type-safe |
| Results/metrics | `@dataclass` | Structured data |
| Manager/registry | Regular class | Complex behavior |
| Engine/orchestrator | Regular class | Primarily methods |

### Key Dataclass Features

```python
from dataclasses import dataclass, field, asdict
from typing import ClassVar

@dataclass
class StrategyConfig:
    VERSION: ClassVar[str] = "1.0"  # Class variable
    name: str  # Required
    max_position: float = 1.0  # Optional with default
    limits: dict[str, float] = field(default_factory=dict)  # Mutable default
    _cache: dict = field(default_factory=dict, repr=False)  # Hidden from repr
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

---

## Code Organization and Architecture

### Module Structure
```
src/aponyx/
  data/          # Data loading, cleaning, transformation
  models/        # Signal generation, strategy logic
  backtest/      # Backtesting engine, performance tracking
  visualization/ # Plotly charts, Streamlit dashboards
  persistence/   # Parquet/JSON I/O, data registry
  config/        # Configuration, paths, constants
```

### Separation of Concerns

| Layer | Responsibility | Dependencies |
|-------|---------------|--------------|
| **data/** | Load and clean raw data | ❌ No strategy logic |
| **models/** | Generate signals and positions | ✅ Uses cleaned data |
| **backtest/** | Execute trades, track P&L | ✅ Uses models and data |
| **visualization/** | Create charts and dashboards | ✅ Uses backtest results |
| **persistence/** | Save/load data to disk | ❌ No business logic |

### Anti-Patterns to Avoid

❌ **Don't mix concerns:**
```python
# BAD: Data loader shouldn't contain strategy logic
def load_cdx_data(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    # ❌ Wrong layer for signal logic!
    df['signal'] = compute_momentum(df['spread'])
    return df
```

✅ **Keep layers separate:**
```python
# GOOD: Data layer only handles loading/cleaning
def load_cdx_data(path: Path) -> pd.DataFrame:
    """Load and validate CDX data."""
    df = pd.read_parquet(path)
    validate_required_columns(df, ['spread', 'date'])
    return df

# Strategy logic belongs in models/
def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate trading signals from market data."""
    df['signal'] = compute_momentum(df['spread'])
    return df
```

---

## Testing Standards

### Test Organization
```
tests/
  data/              # Test data loaders and transforms
  models/            # Test signal generation
  backtest/          # Test backtest engine
  persistence/       # Test I/O operations
  visualization/     # Test plotting functions
```

### Test Requirements
1. **All public functions must have unit tests**
2. **Tests must be deterministic** (use fixed random seeds)
3. **Use fixtures for shared test data**
4. **Test edge cases and error conditions**
5. **Aim for >80% code coverage**

### Example Test Structure
```python
"""Tests for CDX overlay model."""

import pytest
import pandas as pd
import numpy as np
from aponyx.models.cdx_overlay_model import compute_spread_momentum


@pytest.fixture
def sample_spread_data() -> pd.Series:
    """Create deterministic test data."""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)  # Deterministic
    values = 100 + np.cumsum(np.random.randn(100) * 2)
    return pd.Series(values, index=dates, name='spread')


def test_compute_spread_momentum_basic(sample_spread_data):
    """Test basic momentum calculation."""
    result = compute_spread_momentum(sample_spread_data, window=5)
    
    # Check shape and type
    assert isinstance(result, pd.Series)
    assert len(result) == len(sample_spread_data)
    
    # Check for NaN in first window
    assert result.iloc[:4].isna().all()
    
    # Check values are finite after window
    assert result.iloc[5:].notna().all()


def test_compute_spread_momentum_invalid_window(sample_spread_data):
    """Test error handling for invalid window."""
    with pytest.raises(ValueError, match="Window must be >= 2"):
        compute_spread_momentum(sample_spread_data, window=1)


def test_compute_spread_momentum_empty_series():
    """Test handling of empty input."""
    empty = pd.Series([], dtype=float)
    with pytest.raises(ValueError, match="no valid data"):
        compute_spread_momentum(empty, window=5)
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aponyx --cov-report=html

# Run specific test file
pytest tests/models/test_cdx_overlay_model.py

# Run with logging output
pytest -v --log-cli-level=INFO
```

---

## Import Organization

### Import Order (Ruff will enforce this)
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# 1. Standard library
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

# 2. Third-party
import pandas as pd
import numpy as np
from plotly import graph_objects as go

# 3. Local application
from aponyx.config import DATA_DIR
from aponyx.persistence import save_parquet, load_parquet
from aponyx.models.base import BaseModel
```

### Relative vs Absolute Imports

✅ **Use relative imports within package:**
```python
# In aponyx/models/cdx_overlay_model.py
from ..data.loader import load_market_data
from ..data.registry import DataRegistry
from .base import BaseModel
```

✅ **Use absolute imports from outside package:**
```python
# In tests/
from aponyx.models.cdx_overlay_model import CDXOverlayModel
from aponyx.persistence import save_parquet
```

---

## Error Handling

### Exception Best Practices

✅ **Be specific about exceptions:**
```python
def load_dataset(name: str) -> pd.DataFrame:
    """Load dataset by name from registry."""
    try:
        metadata = load_json(REGISTRY_PATH)
    except FileNotFoundError:
        logger.error("Registry not found at %s", REGISTRY_PATH)
        raise
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in registry: %s", e)
        raise ValueError(f"Corrupted registry file: {e}") from e
    
    if name not in metadata:
        raise KeyError(f"Dataset '{name}' not found in registry")
    
    return pd.read_parquet(metadata[name]['path'])
```

### Validation Functions
```python
def validate_required_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """
    Validate that DataFrame contains required columns.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to validate.
    columns : list[str]
        Required column names.
        
    Raises
    ------
    ValueError
        If any required columns are missing.
    """
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    logger.debug("Validated required columns: %s", columns)
```

---

## Reproducibility

### Random Seeds
**All stochastic operations must use fixed seeds:**

```python
import numpy as np
import random

# Set seeds at module level for reproducibility
RANDOM_SEED = 42

def generate_synthetic_data(n_samples: int = 1000) -> pd.DataFrame:
    """Generate synthetic market data for testing."""
    np.random.seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)
    
    dates = pd.date_range('2020-01-01', periods=n_samples, freq='D')
    spreads = 100 + np.cumsum(np.random.randn(n_samples) * 2)
    
    return pd.DataFrame({'date': dates, 'spread': spreads})
```

### Versioning and Metadata
**All backtest runs and model outputs must include metadata:**

```python
from datetime import datetime
from aponyx import __version__

def run_backtest(params: dict[str, Any]) -> dict[str, Any]:
    """Run backtest with full metadata logging."""
    logger.info("Starting backtest: params=%s", params)
    
    # Run backtest logic...
    results = execute_backtest(params)
    
    # Add metadata
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'version': __version__,
        'params': params,
        'random_seed': RANDOM_SEED,
        'python_version': sys.version,
    }
    
    # Save metadata alongside results
    save_json(metadata, 'run_metadata.json')
    
    logger.info("Backtest complete: sharpe=%.2f, n_trades=%d", 
                results['sharpe'], results['n_trades'])
    
    return {**results, 'metadata': metadata}
```

---

## Performance Guidelines

### Pandas Best Practices

✅ **Vectorized operations:**
```python
# GOOD: Vectorized using centralized transforms
from aponyx.data import apply_transform
df['momentum'] = apply_transform(df['spread'], 'z_score', window=20)
```

❌ **Avoid iteration:**
```python
# BAD: Row-by-row iteration
for i in range(len(df)):
    df.loc[i, 'momentum'] = compute_momentum(df.loc[i, 'spread'])
```

### Memory Management
```python
# Use appropriate dtypes
df['date'] = pd.to_datetime(df['date'])
df['spread'] = df['spread'].astype('float32')  # If precision allows
df['instrument'] = df['instrument'].astype('category')

# Load large files in chunks if needed
chunks = pd.read_parquet(large_file, chunksize=100_000)
for chunk in chunks:
    process_chunk(chunk)
```

---

## Pre-Commit Checklist

Before committing code, ensure:

- [ ] **All tests pass:** `pytest`
- [ ] **Code is formatted:** `ruff format src/ tests/`
- [ ] **No linting errors:** `ruff check src/ tests/`
- [ ] **Type checks pass:** `mypy src/`
- [ ] **Docstrings are complete** for public functions
- [ ] **Logging follows standards** (module-level logger, %-formatting)
- [ ] **Tests include edge cases** and error conditions
- [ ] **No hardcoded paths** or credentials
- [ ] **Type hints use modern Python syntax** (no `Optional`, `Union`, etc.)

---

## Additional Resources

- **Project Architecture:** See `README.md`
- **Logging Design:** See `logging_design.md` (in same directory)
- **Strategy Documentation:** See `cdx_overlay_strategy.md` (in same directory)
- **Copilot Instructions:** See `.github/copilot-instructions.md`

---

## Contributing

When adding new features:

1. **Follow the layered architecture** (data → models → backtest → visualization)
2. **Add tests first** (TDD approach recommended)
3. **Document all public APIs** with NumPy-style docstrings
4. **Log at appropriate levels** (INFO for user operations, DEBUG for details)
5. **Use type hints** with Python 3.12 syntax
6. **Make operations deterministic** with fixed random seeds
7. **Include metadata** in all outputs (timestamps, versions, parameters)

---

**Maintained by:** stabilefrisur  
**Version:** 1.0  
**Last Updated:** December 13, 2025
