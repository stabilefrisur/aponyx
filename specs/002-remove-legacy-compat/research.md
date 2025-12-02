# Phase 0 Research: Remove Legacy Compatibility

**Feature**: Remove Legacy Compatibility from Indicator-Signal Separation  
**Date**: December 1, 2025  
**Status**: Complete

## Executive Summary

This research phase analyzed the codebase to determine the optimal strategy for removing all backward compatibility code introduced during feature 001 (indicator-signal separation). Key findings:

1. **signals.py is ENTIRELY legacy** - The entire file exists only as a backward compatibility facade
2. **Orchestrator has clear dual-pattern logic** - Easy to identify and remove legacy path
3. **Test impact is significant but contained** - 50+ test references, all in models layer
4. **Cache invalidation is simple** - Delete workflow directories, no migration needed
5. **Schema simplification is straightforward** - Remove 4 fields from SignalMetadata

## Research Task 1: Legacy Function Removal Strategy

### Investigation

Searched codebase for all usages of the three legacy compute functions:
- `compute_cdx_etf_basis`
- `compute_cdx_vix_gap`
- `compute_spread_momentum`

### Findings

**Call sites found**: 21 matches across codebase

**Location breakdown**:
1. **src/aponyx/models/signals.py** (9 matches)
   - Function definitions (lines 73, 147, 226)
   - Internal facade logic that calls compose_signal()
   - Docstrings explaining backward compatibility

2. **tests/models/test_signals.py** (12 matches)
   - Import statements (lines 10-12)
   - Direct function calls in unit tests (6 test functions)
   - Tests verify legacy facade behavior

3. **tests/models/test_sign_multiplier.py** (4 matches)
   - Uses compute_function_name references in test metadata construction
   - Tests sign multiplier functionality with legacy pattern

### Decision

**Remove signals.py entirely** - Do NOT keep the file.

### Rationale

1. **Zero external dependencies**: No production code outside signals.py calls these functions
2. **Pure facade pattern**: signals.py exists ONLY to delegate to the new compose_signal() workflow
3. **Constitution compliance**: Principle VIII explicitly prohibits backward compatibility code
4. **Code clarity**: Keeping an empty or stub file would confuse future developers

From signals.py header comment:
```python
"""
LEGACY FUNCTIONS - BACKWARD COMPATIBILITY FACADE
================================================
The functions in this module are maintained for backward compatibility.
New code should use the indicator-signal separation pattern
"""
```

This is exactly what we want to remove.

### Alternatives Considered

**Alternative 1: Keep file with ImportError stubs**
```python
def compute_cdx_etf_basis(*args, **kwargs):
    raise ImportError("Legacy signal functions removed. Use indicator + transformation pattern.")
```

**Rejected because**:
- Violates Constitution VIII (no deprecation warnings or compatibility code)
- Adds complexity instead of removing it
- Partial solution creates ambiguity about project direction

**Alternative 2: Keep file with deprecation warnings**
```python
import warnings
def compute_cdx_etf_basis(*args, **kwargs):
    warnings.warn("Deprecated, use compose_signal()", DeprecationWarning)
    # ... facade logic
```

**Rejected because**:
- Explicitly prohibited by Constitution VIII
- We want clean breaks, not gradual migration
- Deprecation warnings were specifically mentioned in the user's request

**Alternative 3: Delete file completely (CHOSEN)**

**Accepted because**:
- Aligns with Constitution Principle VIII
- Simplest implementation (just delete)
- Clear, unambiguous message to developers
- No maintenance burden

### Call Site Remediation Plan

Since ALL call sites are in test files:

1. **test_signals.py**: Delete entire file (tests legacy facade functions)
2. **test_sign_multiplier.py**: Update to use indicator + transformation pattern
3. **test_orchestrator.py**: Remove legacy pattern test cases
4. **test_registry.py**: Remove compute_function_name validation tests
5. **test_metadata.py**: Remove legacy field validation tests

## Research Task 2: Orchestrator Dual-Pattern Logic

### Investigation

Analyzed `src/aponyx/models/orchestrator.py` to map conditional logic between legacy and new patterns.

### Findings

**Dual-pattern switching**: Located in `_compute_signal()` function (lines 206-222):

```python
def _compute_signal(metadata, market_data, config):
    # Determine which pattern to use
    if metadata.indicator_dependencies:
        # New pattern: compose signal from indicators + transformations
        raw_signal = _compute_signal_new_pattern(metadata, market_data)
    else:
        # Legacy pattern: call compute function directly
        raw_signal = _compute_signal_legacy_pattern(metadata, market_data, config)
    
    # Apply sign multiplier from catalog
    signal = raw_signal * metadata.sign_multiplier
    return signal
```

**Dependencies identified**:

1. **`_compute_signal_legacy_pattern()`** (lines 225-254)
   - Validates data requirements via `_validate_data_requirements()`
   - Resolves compute function from signals module using `getattr()`
   - Builds positional arguments from arg_mapping
   - Calls compute function with config parameter

2. **`_validate_data_requirements()`** (lines 281-313)
   - Only used by legacy pattern
   - Checks market_data dict has required keys
   - Verifies required columns exist in DataFrames
   - New pattern gets validation from indicator layer (doesn't need this)

3. **`_compute_signal_new_pattern()`** (lines 257-278)
   - Loads indicator/transformation registries
   - Calls compose_signal() from signal_composer.py
   - KEEP THIS - it's the only pattern after cleanup

### Decision

**Remove 3 functions from orchestrator.py**:
1. `_compute_signal_legacy_pattern()` - Delete entirely
2. `_validate_data_requirements()` - Delete entirely  
3. `_get_registries()` from signals.py (global state) - Not needed after signals.py deletion

**Simplify `_compute_signal()` to only call new pattern**:
```python
def _compute_signal(metadata, market_data):
    # Compose signal from indicators + transformations
    raw_signal = _compute_signal_new_pattern(metadata, market_data)
    
    # Apply sign multiplier from catalog
    signal = raw_signal * metadata.sign_multiplier
    return signal
```

Note: `config` parameter removed since new pattern doesn't use SignalConfig.

### Rationale

1. **Clean separation**: All legacy code removed in one step
2. **Single code path**: No conditional logic remains
3. **Simpler interface**: SignalConfig no longer needed at orchestration layer (used only in indicators)
4. **Validation moves to correct layer**: Data validation happens in indicator computation, not signal orchestration

### Impact on Other Functions

**`compute_registered_signals()` (main entry point)**:
- No changes required
- Already calls `_compute_signal()` which we're simplifying
- Public API remains stable

## Research Task 3: Signal Catalog Schema Migration

### Investigation

Analyzed SignalMetadata dataclass and signal_catalog.json to identify fields for removal.

### Findings

**Current SignalMetadata fields** (from metadata.py):

```python
@dataclass(frozen=True)
class SignalMetadata:
    # Core identity
    name: str
    description: str
    
    # New composition pattern fields (KEEP)
    indicator_dependencies: list[str] | None = None
    transformations: list[str] | None = None
    composition_logic: str | None = None
    
    # Legacy pattern fields (REMOVE)
    compute_function_name: str | None = None      # ❌ DELETE
    data_requirements: dict[str, str] | None = None  # ❌ DELETE
    arg_mapping: list[str] | None = None          # ❌ DELETE
    default_securities: dict[str, str] | None = None  # ❌ DELETE (moved to indicators)
    
    # Common fields (KEEP)
    enabled: bool = True
    sign_multiplier: int = 1
```

**Current signal_catalog.json entries**:

All three signals have BOTH legacy and new pattern fields:
```json
{
  "name": "cdx_etf_basis",
  "description": "...",
  "compute_function_name": "compute_cdx_etf_basis",  // ❌ REMOVE
  "data_requirements": {"cdx": "spread", "etf": "spread"},  // ❌ REMOVE
  "arg_mapping": ["cdx", "etf"],  // ❌ REMOVE
  "default_securities": {"cdx": "cdx_ig_5y", "etf": "lqd"},  // ❌ REMOVE
  "indicator_dependencies": ["cdx_etf_spread_diff"],  // ✅ KEEP
  "transformations": ["z_score_20d"],  // ✅ KEEP
  "composition_logic": null,  // ✅ KEEP
  "enabled": true,  // ✅ KEEP
  "sign_multiplier": 1  // ✅ KEEP
}
```

### Decision

**Remove 4 fields from SignalMetadata**:
1. `compute_function_name` - No longer needed, all signals use composition
2. `data_requirements` - Moved to indicator layer
3. `arg_mapping` - Only used by legacy pattern
4. `default_securities` - Moved to indicator layer

**Keep 6 fields in SignalMetadata**:
1. `name` - Required, signal identifier
2. `description` - Required, documentation
3. `indicator_dependencies` - Required (was optional, now mandatory)
4. `transformations` - Required (was optional, now mandatory)
5. `composition_logic` - Optional (for multi-indicator signals)
6. `enabled` - Optional, defaults to True
7. `sign_multiplier` - Optional, defaults to 1

**Updated schema validation** (in `__post_init__`):

Before:
```python
# Either legacy or new pattern required
has_legacy = self.compute_function_name is not None
has_new = self.indicator_dependencies is not None

if not has_legacy and not has_new:
    raise ValueError("Must specify compute_function_name or indicator_dependencies")
```

After:
```python
# New pattern REQUIRED
if not self.indicator_dependencies:
    raise ValueError(f"Signal {self.name} requires indicator_dependencies")
if not self.transformations:
    raise ValueError(f"Signal {self.name} requires transformations")
```

### Rationale

1. **Enforce single pattern**: By making indicator_dependencies and transformations required, we prevent accidental legacy pattern usage
2. **Schema validation**: Validation moves from "either/or" to "must have new pattern"
3. **Cleaner catalog**: Remove 4 fields from JSON entries (60% reduction in fields)
4. **Explicit requirements**: New signals cannot be created without indicators and transformations

### Migration Steps for signal_catalog.json

For each of the 3 signals:
1. Remove `compute_function_name` line
2. Remove `data_requirements` line
3. Remove `arg_mapping` line
4. Remove `default_securities` line (still in indicators)
5. Keep `indicator_dependencies` (already present)
6. Keep `transformations` (already present)
7. Keep `composition_logic` (already null)
8. Keep `enabled` (already true)
9. Keep `sign_multiplier` (already 1)

## Research Task 4: Test Impact Analysis

### Investigation

Searched for all test files referencing legacy pattern fields or functions.

### Findings

**Test files requiring changes** (50+ matches found):

1. **test_signals.py** (12 matches)
   - Imports compute functions (lines 10-12)
   - Tests legacy facade functions directly (6 test functions)
   - **Action**: DELETE entire file
   - **Rationale**: Tests legacy functions that will no longer exist

2. **test_sign_multiplier.py** (4 matches)
   - Uses compute_function_name in metadata construction
   - Tests sign multiplier with legacy pattern
   - **Action**: UPDATE to use new pattern
   - **Keep**: Sign multiplier functionality tests (still valid)
   - **Change**: Use indicator + transformation instead of compute_function_name

3. **test_registry.py** (15 matches)
   - Tests SignalRegistry with compute_function_name
   - Tests dual-pattern validation logic
   - **Action**: REMOVE legacy pattern tests
   - **Keep**: New pattern validation tests
   - **Remove**: ~6 test functions related to compute_function_name

4. **test_metadata.py** (20 matches)
   - Tests SignalMetadata validation with both patterns
   - Tests compute_function_name + arg_mapping validation
   - **Action**: REMOVE legacy field validation tests
   - **Keep**: New pattern field validation
   - **Remove**: ~8 test functions related to legacy fields

5. **test_orchestrator.py** (19 matches)
   - Tests compute_registered_signals with both patterns
   - Tests _compute_signal dual-pattern switching
   - Tests _validate_data_requirements
   - **Action**: REMOVE legacy pattern tests
   - **Keep**: New pattern orchestration tests
   - **Remove**: ~7 test functions related to legacy pattern

### Decision

**Test cleanup strategy**:

| File | Total Tests | Remove | Update | Keep | Action |
|------|------------|--------|---------|------|--------|
| test_signals.py | 6 | 6 | 0 | 0 | DELETE file |
| test_sign_multiplier.py | 4 | 0 | 4 | 4 | UPDATE |
| test_registry.py | 12 | 6 | 0 | 6 | PARTIAL |
| test_metadata.py | 15 | 8 | 0 | 7 | PARTIAL |
| test_orchestrator.py | 15 | 7 | 0 | 8 | PARTIAL |
| **TOTAL** | **52** | **27** | **4** | **25** | **Mixed** |

**Expected test count after cleanup**: 
- Before: 681 tests
- Remove: ~27 legacy tests
- After: ~654 tests
- Reduction: 4% (27/681 = 3.96%)

### Rationale

1. **Delete test_signals.py entirely**: No reason to test functions that don't exist
2. **Update test_sign_multiplier.py**: Sign multiplier feature is still valid, just uses new pattern
3. **Remove legacy tests from other files**: Keep file structure, delete legacy test functions
4. **Keep new pattern tests**: Already exist and verify current behavior
5. **No new tests needed**: Indicator and transformation tests already cover the functionality

### Test Removal Examples

**test_registry.py - REMOVE**:
```python
def test_signal_metadata_legacy_pattern():
    """Test legacy pattern with compute_function_name."""  # ❌ DELETE
```

**test_registry.py - KEEP**:
```python
def test_signal_metadata_new_pattern():
    """Test new pattern with indicator_dependencies."""  # ✅ KEEP
```

**test_orchestrator.py - REMOVE**:
```python
def test_compute_signal_calls_legacy_function():
    """Test orchestrator calls compute function for legacy pattern."""  # ❌ DELETE
```

**test_orchestrator.py - KEEP**:
```python
def test_compute_signal_composes_from_indicators():
    """Test orchestrator composes signal from indicators."""  # ✅ KEEP
```

## Research Task 5: Cache Invalidation Strategy

### Investigation

Examined data/workflows/ directory structure and workflow metadata format.

### Findings

**Current workflow directory structure**:
```
data/workflows/
├── cdx_etf_basis_balanced_20251201_115403/
├── cdx_vix_gap_aggressive_20251123_210559/
├── spread_momentum_balanced_20251123_210651/
└── test_signal_test_strategy_20241120_123456/
```

**Each workflow directory contains**:
- `metadata.json` - Workflow configuration and execution metadata
- `signal.parquet` - Computed signal time series
- `suitability_evaluation_{timestamp}.md` - Pre-backtest evaluation
- `backtest_result_{timestamp}.parquet` - Backtest P&L and positions
- `performance_analysis_{timestamp}.md` - Post-backtest metrics

**Metadata structure** (from workflow metadata):
```json
{
  "workflow_id": "spread_momentum_balanced_20251123_210651",
  "signal_name": "spread_momentum",
  "strategy_name": "balanced",
  "timestamp": "2025-11-23T21:06:51",
  "securities_used": {"cdx": "cdx_ig_5y"},
  "signal_metadata": {
    "compute_function_name": "compute_spread_momentum",  // ← Legacy field
    "indicator_dependencies": ["spread_momentum_5d"],
    ...
  }
}
```

**Pre-migration workflows**: Identifiable by presence of `compute_function_name` in signal_metadata.

### Decision

**Delete all pre-migration workflow directories** - No migration, no marking, just delete.

### Rationale

1. **Simplest approach**: No code needed, just manual deletion
2. **Regenerable**: All workflow results can be re-computed after migration
3. **Constitution compliance**: Principle VIII explicitly allows breaking changes
4. **Clean slate**: Ensures all results use new architecture
5. **No data loss**: Raw data (data/raw/) is preserved, only computed results deleted

### Implementation

**Delete all workflows created before December 1, 2025**:

```powershell
# Option 1: Delete all workflow directories
Remove-Item -Path "data/workflows/*" -Recurse -Force

# Option 2: Delete only pre-migration workflows (check metadata)
$PreMigrationDate = Get-Date "2025-12-01"
Get-ChildItem "data/workflows" -Directory | Where-Object {
    $timestamp = $_.Name -replace '.*_(\d{8})_\d{6}$', '$1'
    [datetime]::ParseExact($timestamp, "yyyyMMdd", $null) -lt $PreMigrationDate
} | Remove-Item -Recurse -Force
```

**User notification**: Update CHANGELOG.md with breaking change notice:
```markdown
## [0.2.0] - 2025-12-01

### BREAKING CHANGES

- **Legacy signal computation removed**: All signals now use indicator + transformation pattern
- **Workflow cache invalidation**: All workflow results before 2025-12-01 must be regenerated
- **Action required**: Delete `data/workflows/` directory and re-run workflows

### Removed

- `src/aponyx/models/signals.py` - Legacy compute functions (compute_cdx_etf_basis, compute_cdx_vix_gap, compute_spread_momentum)
- `SignalMetadata.compute_function_name` field
- `SignalMetadata.arg_mapping` field
- `SignalMetadata.data_requirements` field (moved to indicators)
- `SignalMetadata.default_securities` field (moved to indicators)
```

### Alternatives Considered

**Alternative 1: Keep old workflows with "LEGACY" suffix**

**Rejected because**:
- Clutters data directory
- Confuses users about which results are current
- Violates clean break principle

**Alternative 2: Add migration utility to convert workflow metadata**

**Rejected because**:
- Constitution VIII prohibits migration utilities
- Adds complexity for temporary problem
- Workflow results are deterministic and easily regenerated

**Alternative 3: Delete old workflows automatically on first run**

**Rejected because**:
- Surprising behavior (deletes user data without explicit action)
- Better to require explicit user action (documented in migration guide)

## Summary: Design Decisions

All unknowns from Technical Context resolved:

| Unknown | Resolution |
|---------|------------|
| **Call sites for legacy functions** | Only in tests, no production code dependencies |
| **Orchestrator dual-pattern dependencies** | 3 functions to remove: _compute_signal_legacy_pattern, _validate_data_requirements, and dual-pattern switching |
| **Signal catalog schema after cleanup** | Remove 4 fields (compute_function_name, arg_mapping, data_requirements, default_securities), keep 6 fields |
| **Test impact** | Delete 1 file, update 1 file, remove tests from 3 files (~27 tests total) |
| **Cache invalidation approach** | Simple deletion of all pre-migration workflow directories |

## Design Principles Applied

1. **Simplicity over flexibility**: Delete entire files rather than stub them out
2. **Fail fast**: Make legacy patterns impossible, not just deprecated
3. **Clean breaks**: No migration utilities, no compatibility layers
4. **Constitution compliance**: Principle VIII strictly followed
5. **Deterministic regeneration**: All deleted data is regenerable

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Accidental deletion of important workflows** | Workflows before Dec 1 are regenerable from raw data |
| **Tests break during implementation** | Remove tests in same commit as code removal |
| **External scripts calling legacy functions** | Document breaking change in CHANGELOG.md, no code mitigation |
| **Confusion about removed patterns** | Update quickstart.md to show only supported pattern |

## Next Phase Inputs

This research provides complete specifications for Phase 1 design artifacts:

1. **data-model.md**: Schema changes documented (remove 4 fields, enforce 2 fields)
2. **quickstart.md**: Single pattern workflow documented (indicator → transformation → signal)
3. **contracts/**: JSON Schema for cleaned signal catalog (6 required/optional fields)

All unknowns resolved - ready to proceed to Phase 1.
