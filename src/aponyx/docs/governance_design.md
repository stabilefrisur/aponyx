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
INDICATOR_TRANSFORMATION_PATH: Final[Path] = PROJECT_ROOT / "src/aponyx/models/indicator_transformation.json"
SCORE_TRANSFORMATION_PATH: Final[Path] = PROJECT_ROOT / "src/aponyx/models/score_transformation.json"
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
)
```

**Pattern:** Class-based registry with state (`self._catalog`). JSON persistence via `_save()` method. Supports CRUD operations.

---

### 6.3 IndicatorTransformationRegistry — Class-Based Catalog for Market Indicators

**Files:**
- `src/aponyx/models/metadata.py` — IndicatorMetadata dataclass  
- `src/aponyx/models/registry.py` — IndicatorTransformationRegistry class
- `src/aponyx/models/indicators.py` — Indicator compute functions

**Lifecycle:**

```python
from aponyx.config import INDICATOR_TRANSFORMATION_PATH
from aponyx.models import IndicatorTransformationRegistry, compute_indicator

# 1. LOAD: Instantiate registry (loads + validates JSON)
registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
# Validation happens automatically in __init__:
# - Checks all compute functions exist in indicators module
# - Validates output_units and data_requirements
# - Raises ValueError if function missing or validation fails

# 2. INSPECT: Query indicator metadata
enabled = registry.get_enabled()  # Only enabled indicators
all_indicators = registry.list_all()  # All indicators
metadata = registry.get_metadata("cdx_etf_spread_diff")

# 3. USE: Compute indicator with caching
market_data = {"cdx": cdx_df, "etf": etf_df}
indicator = compute_indicator(
    indicator_metadata=metadata,
    market_data=market_data,
    use_cache=True  # Cached at data/cache/indicators/
)

# 4. DEPENDENCY TRACKING: Query which signals use an indicator
dependent_signals = registry.get_dependent_signals("cdx_etf_spread_diff")
```

**Pattern:**
- Class-based registry with fail-fast validation
- Indicators output economically interpretable values (basis_points, ratio, percentage)
- Caching via hash-based file names in `data/cache/indicators/`
- Dependency tracking for impact analysis

---

### 6.4 ScoreTransformationRegistry — Class-Based Catalog for Signal Transformations

**Files:**
- `src/aponyx/models/metadata.py` — TransformationMetadata dataclass
- `src/aponyx/models/registry.py` — ScoreTransformationRegistry class  
- `src/aponyx/models/transformations.py` — Transformation functions

**Lifecycle:**

```python
from aponyx.config import SCORE_TRANSFORMATION_PATH
from aponyx.models import ScoreTransformationRegistry, apply_signal_transformation

# 1. LOAD: Instantiate registry (loads + validates JSON)
registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)

# 2. INSPECT: Query transformation metadata
all_transforms = registry.list_all()
metadata = registry.get_metadata("z_score_20d")

# 3. USE: Apply transformation to indicator
transformed = apply_signal_transformation(
    data=indicator,
    transformation_metadata=metadata
)
```

**Pattern:**
- Class-based registry for reusable transformations
- Transformations are pure functions (z-score, volatility adjustment, etc.)
- Parameters defined in catalog (window, min_periods, etc.)
- Applied sequentially in signal composition

---

### 6.5 SignalRegistry — Class-Based Catalog with Indicator Dependencies

**Files:** 
- `src/aponyx/models/metadata.py` — SignalMetadata dataclass
- `src/aponyx/models/registry.py` — SignalRegistry class
- `src/aponyx/models/signal_composer.py` — compose_signal() function
- `src/aponyx/models/orchestrator.py` — compute_registered_signals() function

**Lifecycle:**

```python
from aponyx.config import SIGNAL_CATALOG_PATH, INDICATOR_TRANSFORMATION_PATH, SCORE_TRANSFORMATION_PATH
from aponyx.models import SignalRegistry, IndicatorTransformationRegistry, ScoreTransformationRegistry
from aponyx.models import compose_signal, compute_registered_signals

# 1. LOAD: Instantiate registries (loads + validates JSON)
signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
transformation_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
# Validation happens automatically in __init__:
# - Signals MUST have indicator_dependencies and transformations fields
# - No compute_function_name, data_requirements, or arg_mapping allowed
# - Raises ValueError if schema violated

# 2. INSPECT: Query signal metadata
enabled = signal_registry.get_enabled()  # Only enabled signals
all_signals = signal_registry.list_all()  # All signals
metadata = signal_registry.get_metadata("cdx_etf_basis")

# 3. USE: Compose signal from indicator + transformation
market_data = {"cdx": cdx_df, "etf": etf_df}
signal = compose_signal(
    signal_metadata=metadata,
    market_data=market_data,
    indicator_registry=indicator_registry,
    transformation_registry=transformation_registry
)

# Batch computation of all enabled signals
signals = compute_registered_signals(
    signal_registry, market_data, indicator_registry, transformation_registry
)

# 4. SAVE: Update catalog (optional)
# registry.save_catalog()  # Overwrites original JSON
```

**Pattern:** 
- Class-based registry with fail-fast validation
- Signals reference indicators (no embedded computation logic)
- Signals reference transformations (applied sequentially)
- Schema enforcement via SignalMetadata.__post_init__
- Orchestration bridges three registries

**Module Organization:**
```
models/
  metadata.py          # IndicatorMetadata, TransformationMetadata, SignalMetadata
  registry.py          # IndicatorTransformationRegistry, ScoreTransformationRegistry, SignalRegistry
  indicators.py        # Indicator compute functions
  transformations.py   # Transformation functions
  signal_composer.py   # compose_signal() - combines indicators + transformations
  orchestrator.py      # compute_registered_signals() - batch computation
  config.py            # IndicatorConfig, TransformationConfig
```

This separation clarifies responsibilities:
- `metadata.py` = data structure definitions
- `registry.py` = catalog lifecycle management for all three layers
- `indicators.py` = economically interpretable market metrics
- `transformations.py` = signal processing operations
- `signal_composer.py` = signal composition logic
- `orchestrator.py` = batch orchestration

---

### 6.6 PerformanceRegistry — Class-Based Catalog for Performance Evaluations

**File:** `src/aponyx/evaluation/performance/registry.py`

**Lifecycle:**

```python
from aponyx.config import PERFORMANCE_REGISTRY_PATH
from aponyx.evaluation.performance import PerformanceRegistry

# 1. LOAD: Instantiate registry (loads JSON)
registry = PerformanceRegistry(PERFORMANCE_REGISTRY_PATH)

# 2. INSPECT: Query evaluation metadata
all_evals = registry.list_evaluations()
cdx_evals = registry.list_evaluations(signal_id="cdx_etf_basis")
balanced_evals = registry.list_evaluations(strategy_id="balanced")

# 3. USE: Register new performance evaluation
eval_id = registry.register_evaluation(
    performance_result=perf_result,
    signal_id="cdx_etf_basis",
    strategy_id="balanced",
    report_path=Path("data/workflows/cdx_etf_basis_balanced_20251109_120000/reports/cdx_etf_basis_balanced_20251109.md"),
)

# 4. RETRIEVE: Get specific evaluation metadata
metadata = registry.get_evaluation(eval_id)

# 5. SAVE: Auto-saves on register (manual save also available)
registry.save_catalog()
```

**Pattern:** Class-based registry similar to SuitabilityRegistry. Tracks performance evaluation runs with comprehensive metadata including signal, strategy, stability score, and report paths.

---

### 6.7 StrategyRegistry — Class-Based Catalog for Backtest Strategies

**File:** `src/aponyx/backtest/registry.py`

**Lifecycle:**

```python
from aponyx.config import STRATEGY_CATALOG_PATH
from aponyx.backtest import StrategyRegistry, run_backtest

# 1. LOAD: Instantiate registry (loads + validates JSON)
registry = StrategyRegistry(STRATEGY_CATALOG_PATH)
# Validation happens automatically in __init__:
# - Validates position_size_mm > 0
# - Validates sizing_mode is 'binary' or 'proportional'
# - Validates stop_loss_pct/take_profit_pct in (0, 100] if set

# 2. INSPECT: Query strategy metadata
enabled = registry.get_enabled()  # Only enabled strategies
metadata = registry.get_metadata("balanced")

# 3. USE: Convert strategy to BacktestConfig
config = metadata.to_config(
    position_size_mm_override=20.0,  # Override default
)

# Run backtest with strategy config
result = run_backtest(signal_series, cdx_spread, config)

# 4. SAVE: Update catalog (optional, not typical)
# registry.save_catalog()
```

**Pattern:** Class-based registry similar to SignalRegistry. `StrategyMetadata.to_config()` bridges catalog to runtime config dataclass.

---

### 6.6 Bloomberg Config — Functional Pattern with Module-Level Caching

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

### 6.10 Pattern Comparison

| Pillar | Implementation | State | Validation | Save Support |
|--------|---------------|-------|------------|--------------|
| **Config** | Import-time constants | None | N/A | No |
| **DataRegistry** | Class-based | Mutable (`self._catalog`) | On save | Yes |
| **IndicatorTransformationRegistry** | Class-based | Immutable (frozen dataclass) | Fail-fast (load time) | Yes |
| **ScoreTransformationRegistry** | Class-based | Immutable (frozen dataclass) | Fail-fast (load time) | Yes |
| **SignalRegistry** | Class-based | Immutable (frozen dataclass) | Fail-fast (load time) | Yes |
| **StrategyRegistry** | Class-based | Immutable (frozen dataclass) | Fail-fast (load time) | Yes |
| **SuitabilityRegistry** | Class-based | Mutable (`self._evaluations`) | On register | Yes |
| **PerformanceRegistry** | Class-based | Mutable (`self._evaluations`) | On register | Yes |
| **Bloomberg Config** | Functional | Module-level cache | On access | No |

**When to use each pattern:**

- **Import-time constants:** Static configuration that never changes (paths, flags)
- **Class-based registry:** Needs CRUD operations or mutable state (DataRegistry)
- **Class-based catalog:** Needs validation + orchestration (IndicatorTransformationRegistry, ScoreTransformationRegistry, SignalRegistry, StrategyRegistry)
- **Functional pattern:** Read-only lookup with lazy loading (Bloomberg config)

**Key insight:** Both class-based and functional patterns satisfy the governance spine. Choose based on:
1. **Mutability needs:** Mutable state → class-based
2. **Validation complexity:** Fail-fast validation → class-based with `__post_init__`
3. **Simplicity:** Read-only lookups → functional

---

## 7. Fail-Fast Validation

### IndicatorTransformationRegistry Validation

```python
def _validate_catalog(self) -> None:
    """Validate that all indicator compute functions exist in indicators module."""
    for name, metadata in self._indicators.items():
        if not hasattr(indicators, metadata.compute_function_name):
            raise ValueError(
                f"Indicator '{name}' references non-existent compute function: "
                f"{metadata.compute_function_name}"
            )
```

**Timing:** Called at end of `_load_catalog()` before registry initialization completes.

**Benefits:**
- Catches typos in function names immediately
- Prevents runtime failures during indicator computation
- Clear error messages with indicator name and missing function

### SignalRegistry Validation

```python
def _validate_catalog(self) -> None:
    """Validate that all signals have required fields and reference valid indicators."""
    for name, metadata in self._signals.items():
        # Enforce schema: signals MUST have indicator_dependencies and transformations
        if not metadata.indicator_dependencies:
            raise ValueError(
                f"Signal '{name}' missing required field: indicator_dependencies"
            )
        if not metadata.transformations:
            raise ValueError(
                f"Signal '{name}' missing required field: transformations"
            )
        
        # Reject legacy fields
        if hasattr(metadata, 'compute_function_name'):
            raise ValueError(
                f"Signal '{name}' uses deprecated field 'compute_function_name'. "
                "Signals must reference indicators via indicator_dependencies."
            )
```

**Timing:** Called during SignalMetadata.__post_init__() and at end of `_load_catalog()`.

**Benefits:**
- Enforces new architecture (no embedded computation in signals)
- Prevents mixing of old and new patterns
- Clear migration path for deprecated fields

### StrategyRegistry Validation

```python
@dataclass(frozen=True)
class StrategyMetadata:
    # ... fields ...
    
    def __post_init__(self) -> None:
        """Validate strategy metadata."""
        if self.position_size_mm <= 0:
            raise ValueError(
                f"Strategy '{self.name}': position_size_mm must be positive, "
                f"got {self.position_size_mm}"
            )
        if self.sizing_mode not in {"binary", "proportional"}:
            raise ValueError(
                f"Strategy '{self.name}': sizing_mode must be 'binary' or 'proportional', "
                f"got '{self.sizing_mode}'"
            )
```

**Timing:** Runs during dataclass instantiation (in `_load_catalog()`).

**Benefits:**
- Enforces valid position sizing parameters
- Prevents invalid BacktestConfig creation
- No need for separate validation step

---

**End of Document**

