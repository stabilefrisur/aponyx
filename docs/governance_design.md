# Governance Design — aponyx Framework

**Purpose:**  
This document describes the governance architecture for the *aponyx* research framework. It explains the design principles, patterns, and implementation examples that maintain consistency and modularity across the system.

---

## 1. Design Overview

The governance system exists to:
- Provide **structure without friction** for researchers.  
- Keep **layers isolated yet interoperable** through clear conventions.  
- Ensure **consistency and reproducibility** across data, models, and backtests.

The framework organizes governance around three pillars:

| Pillar | Scope | Persistence | Description |
|--------|--------|--------------|--------------|
| **Config** | Paths, constants, defaults | Hardcoded in `config/` | Declares static project settings and directory locations. |
| **Registry** | Data and metadata tracking | JSON file | Tracks datasets and their lineage. |
| **Catalog** | Model and signal definitions | JSON file | Declares signals and computational assets available for research. |

Each pillar owns a single JSON or constant source of truth.

---

## 2. Design Principles

1. **Single Source of Truth per Concern**  
   Each governance domain (config, registry, catalog) has exactly one canonical file.

2. **Flat, Readable Metadata**  
   All metadata should be inspectable and editable by hand in JSON format.

3. **Minimal State**  
   Governance components prefer functional patterns where practical. Class-based registries are acceptable when they provide clear lifecycle management (load → validate → query → save). State should be immutable after initialization (except DataRegistry which supports CRUD operations).

4. **Pure Dependencies**  
   Governance modules never import from higher layers (e.g., models or backtest).

5. **Determinism**  
   Loading a governance object from disk must always yield the same in-memory representation.

6. **Replaceability**  
   Governance constructs are designed to be replaceable without rewriting other layers.

7. **Convention over Abstraction**  
   Uses naming and directory conventions instead of frameworks or inheritance.

---

## 3. Governance Pillars

### 3.1 Configuration (`config/`)

- Declares constant paths, project root, and cache directories.
- Must be deterministic at import time.  
- No dynamic configuration or environment-variable logic.
- Used by all layers for locating data, cache, and registries.

### 3.2 Registry (`data/registry.py`)

- Tracks datasets produced or consumed by the framework.
- Maintains lightweight metadata such as instrument, source, and date range.
- Each dataset is uniquely identified by name and stored in a single JSON registry.
- Supports basic operations: register, lookup, list.

### 3.3 Catalog (`models/registry.py`, `models/signal_catalog.json`)

- Enumerates all available signal definitions.
- Each entry specifies: name, description, data requirements, and whether it is enabled.
- The catalog acts as the research “menu” from which signals are selected for computation.
- Catalog edits are manual and version-controlled.

---

## 4. Governance Lifecycle Pattern

1. **Load** from a static source (constants or JSON file).  
2. **Inspect** or query (e.g., list enabled signals).  
3. **Use** in downstream processes (fetching data, computing signals).  
4. **Optionally Save** if new metadata is produced.

---

## 5. Layer Boundaries

| Layer | May Import From | Must Not Import From |
|-------|-----------------|----------------------|
| `config/` | None | All others |
| `persistence/` | `config` | `data`, `models`, `backtest` |
| `data/` | `config`, `persistence`, `data` (own modules) | `models`, `backtest`, `visualization` |
| `models/` | `config`, `data` (schemas only) | `backtest`, `visualization` |
| `backtest/` | `config`, `models` | `data`, `visualization` |
| `visualization/` | None | All others |

---

## 6. Implementation Patterns

### 6.1 Config — Import-Time Constants

**File:** `src/aponyx/config/__init__.py`

```python
from pathlib import Path
from typing import Final

# Project root and data directories
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"

# Cache configuration
CACHE_ENABLED: Final[bool] = True
CACHE_TTL_DAYS: Final[int] = 1
CACHE_DIR: Final[Path] = DATA_DIR / "cache"

# Catalog paths
SIGNAL_CATALOG_PATH: Final[Path] = PROJECT_ROOT / "src/aponyx/models/signal_catalog.json"
STRATEGY_CATALOG_PATH: Final[Path] = PROJECT_ROOT / "src/aponyx/backtest/strategy_catalog.json"

# Bloomberg configuration paths
BLOOMBERG_SECURITIES_PATH: Final[Path] = PROJECT_ROOT / "src/aponyx/data/bloomberg_securities.json"
BLOOMBERG_INSTRUMENTS_PATH: Final[Path] = PROJECT_ROOT / "src/aponyx/data/bloomberg_instruments.json"
```

**Usage:**
```python
from aponyx.config import SIGNAL_CATALOG_PATH, DATA_DIR, CACHE_ENABLED

# Config values are available immediately at import time
if CACHE_ENABLED:
    cache_path = DATA_DIR / "cache" / "cdx_data.parquet"
```

**Pattern:** Import-time constants with `Final` type hints. No class instantiation required.

---

### 6.2 DataRegistry — Class-Based Registry

**File:** `src/aponyx/data/registry.py`

**Lifecycle:**

```python
from aponyx.config import REGISTRY_PATH, DATA_DIR
from aponyx.data.registry import DataRegistry

# 1. LOAD: Instantiate registry (loads JSON)
registry = DataRegistry(REGISTRY_PATH, DATA_DIR)

# 2. INSPECT: Query registered datasets
all_datasets = registry.list_datasets()
cdx_datasets = registry.list_datasets(instrument="CDX.NA.IG")

# 3. USE: Retrieve metadata for data loading
info = registry.get_dataset_info("cdx_ig_5y")
file_path = info["file_path"]
start_date = info["start_date"]

# 4. SAVE: Register new dataset (auto-saves)
registry.register_dataset(
    name="new_cdx_data",
    file_path="data/raw/cdx_new.parquet",
    instrument="CDX.NA.IG",
    tenor="5Y",
)
```

**Pattern:** Class-based registry with state (`self._catalog`). JSON persistence via `_save()` method. Supports CRUD operations.

---

### 6.3 SignalRegistry — Class-Based Catalog with Fail-Fast Validation

**File:** `src/aponyx/models/registry.py`

**Lifecycle:**

```python
from aponyx.config import SIGNAL_CATALOG_PATH
from aponyx.models import SignalRegistry, SignalConfig, compute_registered_signals

# 1. LOAD: Instantiate registry (loads + validates JSON)
registry = SignalRegistry(SIGNAL_CATALOG_PATH)
# Validation happens automatically in __init__:
# - Checks all compute functions exist in signals module
# - Raises ValueError if function missing

# 2. INSPECT: Query signal metadata
enabled = registry.get_enabled()  # Only enabled signals
all_signals = registry.list_all()  # All signals
metadata = registry.get_metadata("cdx_etf_basis")

# 3. USE: Compute signals via catalog orchestration
market_data = {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}
config = SignalConfig(lookback=20)
signals = compute_registered_signals(registry, market_data, config)

# 4. SAVE: Update catalog (optional)
# Modify registry state (not typical workflow)
# registry.save_catalog()  # Overwrites original JSON
```

**Pattern:** Class-based registry with fail-fast validation. Validates compute function existence using `hasattr(signals, func_name)` at load time.

---

### 6.4 StrategyRegistry — Class-Based Catalog for Backtest Strategies

**File:** `src/aponyx/backtest/registry.py`

**Lifecycle:**

```python
from aponyx.config import STRATEGY_CATALOG_PATH
from aponyx.backtest import StrategyRegistry, run_backtest

# 1. LOAD: Instantiate registry (loads + validates JSON)
registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
# Validation happens automatically in __init__:
# - Checks entry_threshold > exit_threshold for all strategies

# 2. INSPECT: Query strategy metadata
enabled = registry.get_enabled()  # Only enabled strategies
metadata = registry.get_metadata("balanced")

# 3. USE: Convert strategy to BacktestConfig
config = metadata.to_config(
    position_size=20.0,  # Override default
    transaction_cost_bps=1.5,
)

# Run backtest with strategy config
result = run_backtest(signal_series, cdx_spread, config)

# 4. SAVE: Update catalog (optional, not typical)
# registry.save_catalog()
```

**Pattern:** Class-based registry similar to SignalRegistry. `StrategyMetadata.to_config()` bridges catalog to runtime config dataclass.

---

### 6.5 Bloomberg Config — Functional Pattern with Module-Level Caching

**File:** `src/aponyx/data/bloomberg_config.py`

**Lifecycle:**

```python
from aponyx.data.bloomberg_config import (
    get_instrument_spec,
    get_security_spec,
    get_bloomberg_ticker,
)

# 1. LOAD: Automatic lazy-loading on first access
# JSON files loaded into module-level variables on first function call

# 2. INSPECT: Query specifications
instrument_spec = get_instrument_spec("CDX")
security_spec = get_security_spec("CDX.NA.IG", "5Y")

# 3. USE: Resolve ticker for data fetching
ticker = get_bloomberg_ticker("CDX.NA.IG", "5Y")
# Returns: "CDX IG CDSI 5Y Corp"

# 4. SAVE: Read-only (no save operation)
# Bloomberg config is managed manually via JSON files
```

**Pattern:** Functional pattern with module-level caching (`_INSTRUMENTS_CATALOG`, `_SECURITIES_CATALOG`). Pure functions, no class instantiation. Lazy-loads JSON on first access.

---

### 6.6 Pattern Comparison

| Pillar | Implementation | State | Validation | Save Support |
|--------|---------------|-------|------------|--------------|
| **Config** | Import-time constants | None | N/A | No |
| **DataRegistry** | Class-based | Mutable (`self._catalog`) | On save | Yes |
| **SignalRegistry** | Class-based | Immutable (frozen dataclass) | Fail-fast (load time) | Yes |
| **StrategyRegistry** | Class-based | Immutable (frozen dataclass) | Fail-fast (load time) | Yes |
| **Bloomberg Config** | Functional | Module-level cache | On access | No |

**When to use each pattern:**

- **Import-time constants:** Static configuration that never changes (paths, flags)
- **Class-based registry:** Needs CRUD operations or mutable state (DataRegistry)
- **Class-based catalog:** Needs validation + orchestration (SignalRegistry, StrategyRegistry)
- **Functional pattern:** Read-only lookup with lazy loading (Bloomberg config)

**Key insight:** Both class-based and functional patterns satisfy the governance spine. Choose based on:
1. **Mutability needs:** Mutable state → class-based
2. **Validation complexity:** Fail-fast validation → class-based with `__post_init__`
3. **Simplicity:** Read-only lookups → functional

---

## 7. Fail-Fast Validation

### SignalRegistry Validation

```python
def _validate_catalog(self) -> None:
    """Validate that all signal compute functions exist in signals module."""
    for name, metadata in self._signals.items():
        if not hasattr(signals, metadata.compute_function_name):
            raise ValueError(
                f"Signal '{name}' references non-existent compute function: "
                f"{metadata.compute_function_name}"
            )
```

**Timing:** Called at end of `_load_catalog()` before registry initialization completes.

**Benefits:**
- Catches typos in function names immediately
- Prevents runtime failures during signal computation
- Clear error messages with signal name and missing function

### StrategyRegistry Validation

```python
@dataclass(frozen=True)
class StrategyMetadata:
    # ... fields ...
    
    def __post_init__(self) -> None:
        """Validate strategy metadata."""
        if self.entry_threshold <= self.exit_threshold:
            raise ValueError(
                f"Strategy '{self.name}': entry_threshold ({self.entry_threshold}) "
                f"must be > exit_threshold ({self.exit_threshold})"
            )
```

**Timing:** Runs during dataclass instantiation (in `_load_catalog()`).

**Benefits:**
- Enforces business rule (hysteresis prevents whipsaw)
- Prevents invalid BacktestConfig creation
- No need for separate validation step

---

**End of Document**

