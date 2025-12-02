# Phase 0: Research & Decisions

**Feature**: Indicator-Signal Separation  
**Date**: 2025-11-30  
**Purpose**: Resolve technical unknowns before design phase

---

## Research Questions

From Technical Context analysis, the following areas required research:
1. How to define the boundary between indicators and signals (what goes where)?
2. How to design the transformation catalog for reusable signal operations?
3. What cache key strategy ensures correctness and performance?
4. How to track and query indicator-signal dependencies efficiently?

---

## Decision 1: Indicator-Signal Boundary Definition

### Research Question
What computational logic belongs in indicators vs signals? Where is the boundary?

### Findings

**Economic Interpretability Principle**: The key distinction is whether the output value has economic meaning independent of trading context.

**Indicators** produce values that can be interpreted in their natural units:
- "CDX-VIX deviation gap is +15 basis points" ✅ (economically meaningful)
- "5-day spread change is -3 bps" ✅ (economically meaningful)
- "CDX/ETF spread ratio is 1.12" ✅ (economically meaningful)

**Signals** produce standardized values for position sizing:
- "Signal is +2.1 standard deviations" (requires knowing normalization window)
- "Signal is at 85th percentile" (requires knowing ranking window)
- "Signal crossed threshold" (requires knowing threshold value)

**Transformation Location Rules**:
- **In Indicator**: Ratios, differences, deviations from mean, curve slopes, percentage changes
  - Example: `cdx_etf_spread_diff = CDX spread - ETF spread` (output in bps)
  - Example: `spread_momentum_5d = 5-day spread change` (output in bps)
  
- **In Signal**: Z-score normalization, percentile ranking, volatility adjustment, threshold filters
  - Example: Apply z-score to `cdx_etf_spread_diff` over 20-day window
  - Example: Divide `spread_momentum_5d` by rolling volatility

### Decision

**Adopted Boundary**: Indicators compute economically interpretable raw metrics. Signals apply normalization and regime adjustments for trading.

**Rationale**:
- Makes indicator outputs auditable (researchers can inspect "gap is +15 bps")
- Enables multiple signals with different normalizations from same indicator
- Aligns with governance requirement (indicators validated independently)
- Clear separation of economic logic (indicator) from trading standardization (signal)

**Alternatives Considered**:
- **Alternative A**: Indicators produce normalized outputs → Rejected because loses economic interpretability
- **Alternative B**: Signals compute raw metrics → Rejected because duplicates logic across signals

---

## Decision 2: Transformation Catalog Design

### Research Question
How should reusable signal transformations (z-score, volatility adjustment, etc.) be cataloged and applied?

### Findings

**Current State**: Project has `data/transforms.py` with:
- `apply_transform()` function with `TransformType` enum
- Implementations: diff, pct_change, log_return, z_score, normalized_change
- Already tested and validated

**Options for Catalog**:
1. **JSON Catalog**: Define transformations in `transformation_catalog.json` with parameters
2. **Code Registry**: Register transformation functions dynamically
3. **Reuse Existing**: Leverage `apply_transform()` without new catalog

### Decision

**Adopted Approach**: Create `transformation_catalog.json` that references existing `apply_transform()` operations.

**Catalog Schema**:
```json
{
  "name": "z_score_20d",
  "description": "Z-score normalization over 20-day window",
  "transform_type": "z_score",
  "parameters": {
    "window": 20,
    "min_periods": 10
  },
  "enabled": true
}
```

**Rationale**:
- Reuses battle-tested `apply_transform()` implementation
- Catalog makes transformations discoverable for signal definitions
- Parameters are explicit (different windows = different catalog entries)
- Follows existing registry pattern (SignalRegistry, StrategyRegistry)

**Alternatives Considered**:
- **Alternative A**: No catalog, hardcode in signal definitions → Rejected because reduces discoverability and consistency
- **Alternative B**: Dynamic parameterization → Rejected because increases complexity and violates "fixed parameters at definition" principle

---

## Decision 3: Indicator Cache Key Strategy

### Research Question
What cache key strategy ensures indicators are reused correctly across signals while avoiding stale results?

### Findings

**Requirements**:
- Multiple signals using same indicator should share cached computation
- Different parameters should NOT share cache (momentum_5d vs momentum_10d)
- Indicator definition changes should invalidate cache
- Input data changes should invalidate cache

**Cache Key Components**:
1. **Indicator name**: Identifies which indicator
2. **Parameter hash**: Ensures different parameters get separate cache entries
3. **Input data hash**: Detects when underlying data changes

**Current Pattern**: Data cache uses `{security}_{hash}.parquet` pattern with TTL

### Decision

**Adopted Strategy**: Security-agnostic cache with composite key: `{indicator_name}_{params_hash}_{data_hash}.parquet`

**Cache Directory**: `data/cache/indicators/`

**Invalidation Strategy**:
- Catalog changes (indicator definition modified) → Delete entire `indicators/` directory
- Data changes → Data hash in filename changes automatically
- Parameter changes → Parameters are fixed in catalog (different catalog entry = different indicator)

**Rationale**:
- Composite key ensures correctness (no false cache hits)
- Separate directory enables bulk invalidation when indicators change
- Follows existing cache pattern (similar to data cache)
- Performance: 60% reduction in multi-signal computation time (measured goal)

**Alternatives Considered**:
- **Alternative A**: TTL-based cache → Rejected because doesn't detect indicator definition changes
- **Alternative B**: Single cache entry per indicator name → Rejected because can't support different parameters

---

## Decision 4: Dependency Tracking Implementation

### Research Question
How to efficiently track and query which signals depend on which indicators?

### Findings

**Use Cases**:
- Impact analysis: "Which signals use this indicator?"
- Cascade invalidation: "What needs recomputation if indicator changes?"
- Governance audit: "Show me all dependencies for this signal"

**Options**:
1. **Catalog-based**: Parse signal_catalog.json entries for indicator_dependencies field
2. **Runtime registry**: Build dependency graph at initialization
3. **Separate index**: Maintain indicator→signals mapping in separate file

### Decision

**Adopted Approach**: Catalog-based dependency tracking with runtime index in IndicatorRegistry.

**Signal Catalog Schema Update**:
```json
{
  "name": "cdx_vix_gap",
  "description": "Cross-asset risk sentiment signal",
  "indicator_dependencies": ["cdx_vix_deviation_gap_20d"],
  "transformations": ["z_score_20d"],
  "enabled": true
}
```

**IndicatorRegistry Methods**:
- `get_dependent_signals(indicator_name: str) -> list[str]`: Returns signal names
- `get_all_dependencies() -> dict[str, list[str]]`: Returns full dependency graph

**Implementation**:
```python
def _build_dependency_index(self) -> None:
    """Build reverse index: indicator -> list of signals."""
    self._dependencies: dict[str, list[str]] = {}
    for signal_name, signal_metadata in self._signal_registry._signals.items():
        for indicator_name in signal_metadata.indicator_dependencies:
            if indicator_name not in self._dependencies:
                self._dependencies[indicator_name] = []
            self._dependencies[indicator_name].append(signal_name)
```

**Rationale**:
- Catalog is source of truth (single place to declare dependencies)
- Runtime index provides O(1) lookup for impact queries
- Meets performance requirement (<1s for 50 indicators + 100 signals)
- No separate file to keep in sync

**Alternatives Considered**:
- **Alternative A**: Parse catalogs on every query → Rejected because too slow for large catalogs
- **Alternative B**: Separate dependency file → Rejected because creates sync issues

---

## Decision 5: Backward Compatibility Strategy

### Research Question
How to maintain backward compatibility with existing 3 pilot signals during migration?

### Findings

**Current Signal Functions**:
- `compute_cdx_etf_basis()`: Returns z-score normalized basis
- `compute_cdx_vix_gap()`: Returns z-score normalized gap
- `compute_spread_momentum()`: Returns volatility-adjusted momentum

**Requirement**: Existing backtest results must remain reproducible

**Migration Strategies**:
1. **Facade Pattern**: Keep old functions as wrappers calling indicator + signal composition
2. **Dual Implementation**: Maintain old and new side-by-side
3. **Direct Refactor**: Replace old functions, verify outputs match

### Decision

**Adopted Strategy**: Facade pattern with validation.

**Implementation**:
```python
# In signals.py (maintained for backward compatibility)
def compute_cdx_etf_basis(
    cdx_df: pd.DataFrame,
    etf_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    LEGACY: Compute CDX-ETF basis signal.
    
    This function is maintained for backward compatibility.
    New code should use:
      indicator = compute_indicator("cdx_etf_spread_diff", ...)
      signal = apply_signal_transformation(indicator, "z_score_20d", ...)
    """
    # Compute indicator
    indicator = compute_indicator(
        "cdx_etf_spread_diff",
        {"cdx": cdx_df, "etf": etf_df},
        config
    )
    
    # Apply transformation
    signal = apply_signal_transformation(
        indicator,
        "z_score_20d",
        config
    )
    
    return signal
```

**Validation**:
- Integration tests verify old and new produce identical outputs
- Deprecation warnings NOT added (per constitution: no backward compatibility promises)
- Documentation updated to recommend new pattern

**Rationale**:
- Maintains reproducibility of existing backtests
- Provides clear migration path for new development
- Validates refactoring correctness (old and new must match)
- Eventually can be removed after full migration

**Alternatives Considered**:
- **Alternative A**: Immediate breaking change → Rejected because invalidates existing backtest results
- **Alternative B**: Permanent dual implementation → Rejected because creates maintenance burden

---

## Summary of Decisions

| Decision | Choice | Key Benefit |
|----------|--------|-------------|
| **Indicator-Signal Boundary** | Economic interpretability principle | Clear separation, auditable indicators |
| **Transformation Catalog** | JSON catalog + existing `apply_transform()` | Reuses tested code, discoverable transformations |
| **Cache Key Strategy** | Composite key with parameter + data hash | Correctness + 60% performance gain |
| **Dependency Tracking** | Catalog-based with runtime index | O(1) lookups, single source of truth |
| **Backward Compatibility** | Facade pattern with validation | Reproducibility + migration path |

---

## Technology Choices Validated

| Technology | Usage | Best Practice |
|------------|-------|---------------|
| **Frozen Dataclasses** | IndicatorMetadata, TransformationMetadata | `__post_init__` validation, immutability |
| **JSON Catalogs** | indicator_catalog.json, transformation_catalog.json | Human-editable, version-controlled |
| **Pytest** | Unit tests for indicators, integration tests for composition | Independent test execution, fixtures |
| **Parquet** | Indicator cache storage | Fast I/O, column filtering, compression |
| **Module-level loggers** | `logger = logging.getLogger(__name__)` | Selective debugging, no `basicConfig()` |

---

**Research Complete**: All NEEDS CLARIFICATION items resolved. Ready for Phase 1 design.
