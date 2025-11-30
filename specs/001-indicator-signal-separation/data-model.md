# Phase 1: Data Model

**Feature**: Indicator-Signal Separation  
**Date**: 2025-11-30  
**Purpose**: Define entities, fields, relationships, and validation rules

---

## Entity Definitions

### 1. Indicator

**Purpose**: Reusable market metric computation producing economically interpretable time series.

**Attributes**:
- `name: str` - Unique identifier (e.g., "cdx_etf_spread_diff", "spread_momentum_5d")
- `description: str` - Human-readable explanation of economic meaning
- `compute_function_name: str` - Python function name in indicators.py module
- `data_requirements: dict[str, str]` - Instrument types to data fields mapping (e.g., {"cdx": "spread", "etf": "spread"})
- `default_securities: dict[str, str]` - Default security identifiers for each instrument type (e.g., {"cdx": "cdx_ig_5y", "etf": "lqd"})
- `output_units: str` - Units of output values (e.g., "basis_points", "ratio", "percentage")
- `parameters: dict[str, Any]` - Fixed computation parameters (e.g., {"lookback": 5, "method": "simple"})
- `enabled: bool` - Whether indicator is available for use (default: true)

**Relationships**:
- Referenced by one or more **Signal** entities (via `indicator_dependencies`)
- Produces cached **IndicatorCache** entries

**Validation Rules** (in `__post_init__`):
- `name` must be non-empty and match pattern `^[a-z][a-z0-9_]*$` (lowercase, underscores)
- `compute_function_name` must exist in `indicators` module (validated by IndicatorRegistry)
- `data_requirements` must be non-empty dict
- `output_units` must be one of: "basis_points", "ratio", "percentage", "index_level", "volatility_points"
- `parameters` keys must be valid Python identifiers

**Lifecycle**:
1. Defined in `indicator_catalog.json`
2. Loaded by IndicatorRegistry at initialization
3. Validated on load (compute function exists, schema valid)
4. Computed on-demand when referenced by signal
5. Cached for reuse across signals

**Example**:
```python
@dataclass(frozen=True)
class IndicatorMetadata:
    name: str
    description: str
    compute_function_name: str
    data_requirements: dict[str, str]
    default_securities: dict[str, str]
    output_units: str
    parameters: dict[str, Any]
    enabled: bool = True
    
    def __post_init__(self) -> None:
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise ValueError(f"Invalid indicator name: {self.name}")
        if not self.data_requirements:
            raise ValueError(f"Indicator {self.name} has no data requirements")
        valid_units = {"basis_points", "ratio", "percentage", "index_level", "volatility_points"}
        if self.output_units not in valid_units:
            raise ValueError(f"Invalid output_units: {self.output_units}")
```

---

### 2. Transformation

**Purpose**: Reusable signal transformation operation (normalization, volatility adjustment, filters).

**Attributes**:
- `name: str` - Unique identifier (e.g., "z_score_20d", "volatility_adjust_5d")
- `description: str` - Human-readable explanation
- `transform_type: TransformType` - Type from data.transforms (z_score, normalized_change, etc.)
- `parameters: dict[str, Any]` - Fixed transformation parameters (e.g., {"window": 20, "min_periods": 10})
- `enabled: bool` - Whether transformation is available (default: true)

**Relationships**:
- Referenced by one or more **Signal** entities (via `transformations`)
- Maps to function in `data.transforms.apply_transform()`

**Validation Rules** (in `__post_init__`):
- `name` must be non-empty and match pattern `^[a-z][a-z0-9_]*$`
- `transform_type` must be valid TransformType literal
- `parameters` must match requirements for transform_type:
  - z_score: requires `window`, optional `min_periods`
  - normalized_change: requires `window`, optional `min_periods`, optional `periods`
  - diff/pct_change/log_return: optional `periods`

**Lifecycle**:
1. Defined in `transformation_catalog.json`
2. Loaded by TransformationRegistry at initialization
3. Validated on load (transform_type valid, parameters correct)
4. Applied to indicator outputs during signal composition

**Example**:
```python
@dataclass(frozen=True)
class TransformationMetadata:
    name: str
    description: str
    transform_type: TransformType
    parameters: dict[str, Any]
    enabled: bool = True
    
    def __post_init__(self) -> None:
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise ValueError(f"Invalid transformation name: {self.name}")
        # Validate parameters match transform_type requirements
        if self.transform_type in ("z_score", "normalized_change"):
            if "window" not in self.parameters:
                raise ValueError(f"Transformation {self.name} requires 'window' parameter")
```

---

### 3. Signal (Updated)

**Purpose**: Trading signal derived from one or more indicators via transformations.

**Attributes** (NEW fields highlighted):
- `name: str` - Unique identifier (existing)
- `description: str` - Human-readable explanation (existing)
- `compute_function_name: str` - DEPRECATED: Legacy field for backward compatibility
- `indicator_dependencies: list[str]` - **NEW**: Indicators required for this signal
- `transformations: list[str]` - **NEW**: Transformations to apply to indicators
- `composition_logic: str | None` - **NEW**: Optional Python expression for combining indicators
- `data_requirements: dict[str, str]` - DEPRECATED: Moved to indicators
- `default_securities: dict[str, str]` - DEPRECATED: Moved to indicators
- `enabled: bool` - Whether signal is available (existing)
- `sign_multiplier: int` - Sign convention adjustment (existing)

**Relationships**:
- References one or more **Indicator** entities (via `indicator_dependencies`)
- References one or more **Transformation** entities (via `transformations`)
- Consumed by **Strategy** entities

**Validation Rules** (in `__post_init__`):
- `name` must be non-empty and match pattern `^[a-z][a-z0-9_]*$`
- `indicator_dependencies` must be non-empty list
- All indicator names in `indicator_dependencies` must exist in IndicatorRegistry
- All transformation names in `transformations` must exist in TransformationRegistry
- `sign_multiplier` must be +1 or -1

**Lifecycle**:
1. Defined in `signal_catalog.json` (updated schema)
2. Loaded by SignalRegistry at initialization
3. Validated on load (dependencies exist)
4. Computed by retrieving indicators, applying transformations, combining if needed

**Migration Strategy**:
- Legacy signals (compute_function_name present) use facade pattern
- New signals (indicator_dependencies present) use composition
- Both patterns coexist during migration

**Example**:
```python
@dataclass(frozen=True)
class SignalMetadata:
    name: str
    description: str
    indicator_dependencies: list[str]
    transformations: list[str]
    composition_logic: str | None = None
    enabled: bool = True
    sign_multiplier: int = 1
    
    # Legacy fields (deprecated)
    compute_function_name: str | None = None
    data_requirements: dict[str, str] | None = None
    default_securities: dict[str, str] | None = None
    
    def __post_init__(self) -> None:
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise ValueError(f"Invalid signal name: {self.name}")
        if self.sign_multiplier not in (1, -1):
            raise ValueError(f"sign_multiplier must be +1 or -1, got {self.sign_multiplier}")
        # Either legacy or new pattern required
        if not self.compute_function_name and not self.indicator_dependencies:
            raise ValueError(f"Signal {self.name} must specify either compute_function_name or indicator_dependencies")
```

---

### 4. IndicatorRegistry

**Purpose**: Manage indicator catalog lifecycle (load, validate, query).

**Attributes**:
- `_catalog_path: Path` - Path to indicator_catalog.json
- `_indicators: dict[str, IndicatorMetadata]` - Loaded indicator metadata by name
- `_dependencies: dict[str, list[str]]` - Reverse index: indicator → dependent signals

**Methods**:
- `__init__(catalog_path: Path)` - Load and validate catalog
- `get_metadata(name: str) -> IndicatorMetadata` - Retrieve indicator metadata
- `get_enabled() -> list[str]` - List enabled indicator names
- `get_dependent_signals(indicator_name: str) -> list[str]` - Query dependency graph
- `indicator_exists(name: str) -> bool` - Check if indicator defined

**Validation**:
- Fail-fast on initialization (all compute functions must exist)
- No duplicate indicator names in catalog
- All referenced compute functions must be importable from indicators module

**Lifecycle**:
1. Instantiated at application startup
2. Loads indicator_catalog.json
3. Validates all entries (compute functions exist)
4. Builds dependency index from signal catalog
5. Provides read-only query interface

---

### 5. TransformationRegistry

**Purpose**: Manage transformation catalog lifecycle (load, validate, query).

**Attributes**:
- `_catalog_path: Path` - Path to transformation_catalog.json
- `_transformations: dict[str, TransformationMetadata]` - Loaded transformation metadata by name

**Methods**:
- `__init__(catalog_path: Path)` - Load and validate catalog
- `get_metadata(name: str) -> TransformationMetadata` - Retrieve transformation metadata
- `get_enabled() -> list[str]` - List enabled transformation names
- `transformation_exists(name: str) -> bool` - Check if transformation defined

**Validation**:
- Fail-fast on initialization (all transform_types must be valid)
- No duplicate transformation names in catalog
- Parameters must match transform_type requirements

**Lifecycle**:
1. Instantiated at application startup
2. Loads transformation_catalog.json
3. Validates all entries (transform_types valid, parameters correct)
4. Provides read-only query interface

---

### 6. IndicatorCache

**Purpose**: Persistent storage for computed indicator time series.

**Attributes**:
- `cache_dir: Path` - Root directory (data/cache/indicators/)
- `cache_key: str` - Composite key: `{indicator_name}_{params_hash}_{data_hash}`
- `cached_values: pd.Series` - Computed indicator time series

**Storage Format**: Parquet files at `{cache_dir}/{cache_key}.parquet`

**Cache Key Generation**:
```python
def generate_cache_key(
    indicator_name: str,
    parameters: dict[str, Any],
    input_data: dict[str, pd.DataFrame]
) -> str:
    # Hash parameters
    params_str = json.dumps(parameters, sort_keys=True)
    params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:8]
    
    # Hash input data (concatenate all DataFrame hashes)
    data_hashes = []
    for key in sorted(input_data.keys()):
        df_hash = hashlib.sha256(
            pd.util.hash_pandas_object(input_data[key]).values
        ).hexdigest()[:8]
        data_hashes.append(df_hash)
    data_hash = hashlib.sha256("".join(data_hashes).encode()).hexdigest()[:8]
    
    return f"{indicator_name}_{params_hash}_{data_hash}"
```

**Lifecycle**:
1. Check cache before computing indicator
2. Compute if cache miss
3. Save to cache after computation
4. Invalidated when indicator definition changes (delete cache directory)

---

## Relationships Diagram

```
┌─────────────────────┐
│ IndicatorCatalog    │
│ (indicator_catalog. │
│  json)              │
└──────────┬──────────┘
           │ defines
           ▼
┌─────────────────────┐      ┌──────────────────┐
│ Indicator           │─────>│ IndicatorCache   │
│ (metadata)          │      │ (parquet files)  │
└──────────┬──────────┘      └──────────────────┘
           │
           │ referenced by
           ▼
┌─────────────────────┐      ┌──────────────────┐
│ Signal              │─────>│ Transformation   │
│ (updated metadata)  │      │ (metadata)       │
└──────────┬──────────┘      └─────────▲────────┘
           │                            │
           │ consumed by                │ defines
           ▼                            │
┌─────────────────────┐      ┌─────────┴────────┐
│ Strategy            │      │ Transformation   │
│ (existing)          │      │ Catalog          │
└─────────────────────┘      │ (transformation_ │
                             │  catalog.json)   │
                             └──────────────────┘
```

---

## State Transitions

### Indicator State
```
[Defined in JSON] → [Loaded by Registry] → [Validated] → [Available for Use]
                                                            ↓
                                                   [Computed on Demand]
                                                            ↓
                                                      [Cached in Parquet]
                                                            ↓
                                                     [Reused by Signals]
```

### Signal State (New Pattern)
```
[Defined in JSON] → [Loaded by Registry] → [Validated] → [Dependencies Resolved]
                                                                  ↓
                                                        [Indicators Retrieved]
                                                                  ↓
                                                      [Transformations Applied]
                                                                  ↓
                                                       [Signal Values Returned]
```

---

## Validation Summary

| Entity | Validation Timing | Validation Method | Failure Mode |
|--------|------------------|-------------------|--------------|
| **Indicator** | On registry load | `__post_init__`, compute function existence check | ValueError, fail-fast |
| **Transformation** | On registry load | `__post_init__`, transform_type validation | ValueError, fail-fast |
| **Signal** | On registry load | `__post_init__`, dependency existence check | ValueError, fail-fast |
| **IndicatorCache** | On cache save/load | Parquet schema validation | IOError, regenerate |
| **IndicatorRegistry** | On initialization | Catalog JSON validation, function resolution | FileNotFoundError, ValueError |
| **TransformationRegistry** | On initialization | Catalog JSON validation, parameter validation | FileNotFoundError, ValueError |

---

**Phase 1 Data Model Complete**: All entities defined with fields, relationships, and validation rules. Ready for contract generation.
