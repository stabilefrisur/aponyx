# Implementation Plan: Remove Legacy Compatibility from Indicator-Signal Separation

**Branch**: `002-remove-legacy-compat` | **Date**: December 1, 2025 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-remove-legacy-compat/spec.md`

## Summary

Remove all backward compatibility code, deprecation warnings, and legacy signal computation functions introduced during the indicator-signal separation (feature 001). The system will exclusively use the new indicator + transformation architecture with no fallback paths. This cleanup eliminates maintenance burden, removes cognitive load for developers, and ensures the codebase reflects only the current architecture.

Primary changes:
- Remove legacy compute functions (compute_cdx_etf_basis, compute_cdx_vix_gap, compute_spread_momentum) from signals.py
- Remove backward compatibility facades and lazy-loading registry logic
- Update orchestrator to remove dual-pattern support (legacy vs new)
- Remove compute_function_name and arg_mapping from signal catalog schema
- Invalidate all pre-migration workflow caches
- Update documentation to remove references to deprecated patterns

## Technical Context

**Language/Version**: Python 3.12 (strict requirement, modern syntax only)

**Primary Dependencies**: 
- Pandas 2.0+ (time series manipulation)
- PyArrow 12.0+ (Parquet persistence)
- Click 8.1+ (CLI framework)
- Plotly 5.24+ (visualization)
- Statsmodels 0.14+ (statistical tests)

**Storage**: 
- Parquet files for time series data (data/cache/, data/workflows/)
- JSON catalogs for metadata (src/aponyx/models/*.json, data/.registries/*.json)
- No database dependencies

**Testing**: 
- Pytest 8.0+ (681 tests baseline)
- MyPy 1.11+ (strict type checking)
- Unit tests for all layers (models, backtest, evaluation, workflows)

**Target Platform**: 
- Linux/macOS/Windows development environments
- Command-line research workflows
- Single-node execution (no distributed computing)

**Project Type**: Single Python project with layered architecture

**Performance Goals**: 
- Signal computation: <5 seconds for 252 trading days
- Backtest execution: <10 seconds for 1-year simulation
- Cache loading: <1 second for indicator retrieval

**Constraints**: 
- Deterministic execution (fixed seeds, identical outputs)
- Layer boundary enforcement (data → models → backtest → evaluation)
- Type safety (all public APIs fully typed)
- No backward compatibility required

**Scale/Scope**: 
- 3 pilot signals (cdx_etf_basis, cdx_vix_gap, spread_momentum)
- ~50 source files in src/aponyx/
- 681 existing tests (no reduction expected)
- Single-user research workflows

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principle Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Modularity & Layer Separation** | ✅ PASS | No layer boundary changes. Removing code from models layer only. |
| **II. Reproducibility & Determinism** | ✅ PASS | Removing legacy code improves reproducibility by eliminating dual code paths. |
| **III. Type Safety & Modern Python** | ✅ PASS | Simplifies type signatures by removing Optional[SignalConfig] parameters. |
| **IV. Functions Over Classes** | ✅ PASS | Removing facade functions, keeping indicator/transformation functions. |
| **V. Registry Pattern** | ✅ PASS | Strengthens registry pattern by making it the only path (removes compute_function_name). |
| **VI. Signal Sign Convention** | ✅ PASS | No changes to signal sign convention. |
| **VII. Logging Discipline** | ✅ PASS | Remove "legacy facade" log messages, keep indicator computation logs. |
| **VIII. No Backward Compatibility** | ✅ PASS | **This feature directly implements Constitution Principle VIII.** |

### Technology Standards Compliance

| Standard | Status | Notes |
|----------|--------|-------|
| **Python 3.12** | ✅ PASS | No syntax changes required. |
| **Type Checking** | ✅ PASS | Removing Optional params improves type safety. |
| **Code Quality Tools** | ✅ PASS | All changes will pass ruff/mypy checks. |

### Development Workflow Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| **Test Coverage** | ✅ PASS | Replace legacy tests with indicator/transformation tests. |
| **Documentation** | ✅ PASS | Update docs to remove deprecated pattern references. |

### Overall Gate Status

**✅ ALL GATES PASSED - Proceed to Phase 0 research**

This feature is perfectly aligned with Constitution Principle VIII (No Backward Compatibility). No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/002-remove-legacy-compat/
├── plan.md              # This file (complete)
├── research.md          # Phase 0 - Next to generate
├── data-model.md        # Phase 1 - Signal catalog schema
├── quickstart.md        # Phase 1 - Developer guide
└── contracts/           # Phase 1 - Catalog schemas
    └── signal_catalog_schema.json
```

### Source Code (repository root)

```text
src/aponyx/
├── models/
│   ├── signals.py              # REMOVE entire file (legacy functions)
│   ├── orchestrator.py         # UPDATE: remove dual-pattern logic
│   ├── registry.py             # UPDATE: remove compute_function_name validation
│   ├── metadata.py             # UPDATE: remove compute_function_name field
│   ├── signal_catalog.json     # UPDATE: remove compute_function_name, arg_mapping
│   ├── indicators.py           # NO CHANGE
│   ├── signal_composer.py      # NO CHANGE
│   └── indicator_catalog.json  # NO CHANGE
│
├── workflows/
│   └── concrete_steps.py       # UPDATE: adjust SignalStep if needed
│
└── config/
    └── __init__.py             # NO CHANGE (catalog paths remain)

tests/
├── models/
│   ├── test_signals.py         # REMOVE/REPLACE: legacy signal tests
│   ├── test_orchestrator.py    # UPDATE: remove dual-pattern tests
│   └── test_registry.py        # UPDATE: remove compute_function_name tests
│
└── workflows/
    └── test_concrete_steps.py  # UPDATE: ensure SignalStep tests pass

data/workflows/
└── [all pre-migration dirs]/   # INVALIDATE: clear or mark as deprecated
```

**Structure Decision**: Single Python project structure (Option 1). All changes are within existing src/aponyx/models/ directory. No new directories needed. This is a code removal feature, not an addition feature.

## Complexity Tracking

> **No violations - No justification needed**

This feature removes complexity rather than adding it. No constitution violations exist.

---

## Phase 0: Research & Decision Documentation

**Objective**: Resolve all technical unknowns and document removal strategy

### Research Tasks

1. **Legacy Function Removal Strategy**
   - Task: Analyze all call sites of compute_cdx_etf_basis, compute_cdx_vix_gap, compute_spread_momentum
   - Question: Are these functions called anywhere outside signals.py?
   - Expected finding: Only called by legacy facade pattern (internal to signals.py)

2. **Orchestrator Dual-Pattern Logic**
   - Task: Map out the conditional logic in _compute_signal() that switches between legacy/new patterns
   - Question: What other functions in orchestrator.py depend on compute_function_name?
   - Expected finding: _compute_signal_legacy_pattern() and _validate_data_requirements() can be removed

3. **Signal Catalog Schema Migration**
   - Task: Identify all fields that can be removed from signal catalog entries
   - Question: What are the required fields after removing compute_function_name and arg_mapping?
   - Expected finding: Required fields are: name, description, indicator_dependencies, transformations, enabled, sign_multiplier

4. **Test Impact Analysis**
   - Task: Count how many tests directly verify legacy signal compute functions
   - Question: Which tests need to be removed vs updated vs replaced?
   - Expected finding: ~10-15 tests in test_signals.py need removal, ~5-10 in test_orchestrator.py need updates

5. **Cache Invalidation Strategy**
   - Task: Determine how to invalidate pre-migration workflow caches
   - Question: Should we delete old workflow directories or mark them invalid with metadata?
   - Expected finding: Simple deletion is cleanest approach, no migration utility needed

### Output Artifact

`research.md` will document:
- Decision: Remove signals.py entirely (not just functions)
- Rationale: File exists only for backward compatibility facades
- Alternatives: Keep file with deprecation warnings (REJECTED per Constitution VIII)
- Call site analysis: No external dependencies found
- Schema changes: Remove 2 fields, keep 6 fields
- Test strategy: Remove 12 legacy tests, add 0 new tests (existing indicator tests sufficient)
- Cache strategy: Delete all workflows older than feature 001 completion date

---

## Phase 1: Design & Contracts

**Prerequisites**: research.md complete

### Design Artifacts

#### 1. Data Model (`data-model.md`)

Document the cleaned-up signal catalog schema:

**SignalMetadata (updated)**:
```python
@dataclass(frozen=True)
class SignalMetadata:
    name: str
    description: str
    indicator_dependencies: list[str]  # Required (was optional)
    transformations: list[str]         # Required (was optional)
    enabled: bool = True
    sign_multiplier: int = 1
    
    # REMOVED FIELDS:
    # compute_function_name: str | None = None  # ❌ DELETED
    # arg_mapping: list[str] | None = None      # ❌ DELETED
    # data_requirements: dict[str, str] | None = None  # ❌ DELETED (computed from indicators)
```

**Signal Catalog Entry (updated)**:
```json
{
  "name": "cdx_etf_basis",
  "description": "Flow-driven mispricing signal from CDX-ETF basis divergence",
  "indicator_dependencies": ["cdx_etf_spread_diff"],
  "transformations": ["z_score_20d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

**Validation Rules**:
- indicator_dependencies MUST be non-empty list
- transformations MUST be non-empty list
- All indicators referenced MUST exist in indicator_catalog.json
- All transformations referenced MUST exist in transformation_catalog.json

#### 2. API Contracts (`contracts/signal_catalog_schema.json`)

JSON Schema for signal catalog validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["name", "description", "indicator_dependencies", "transformations"],
    "properties": {
      "name": {"type": "string", "pattern": "^[a-z_]+$"},
      "description": {"type": "string", "minLength": 10},
      "indicator_dependencies": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1
      },
      "transformations": {
        "type": "array", 
        "items": {"type": "string"},
        "minItems": 1
      },
      "enabled": {"type": "boolean", "default": true},
      "sign_multiplier": {"type": "integer", "enum": [-1, 1], "default": 1}
    },
    "additionalProperties": false
  }
}
```

#### 3. Developer Guide (`quickstart.md`)

Document the single supported pattern for signal creation:

**Before (legacy pattern - NO LONGER SUPPORTED)**:
```python
# ❌ This pattern is removed
def compute_my_signal(cdx_df: pd.DataFrame, config: SignalConfig) -> pd.Series:
    # ... computation logic ...
    return signal
```

**After (current pattern - ONLY way to create signals)**:
```python
# 1. Define indicator in indicator_catalog.json
{
  "name": "my_indicator",
  "description": "My indicator computation",
  "data_requirements": {"cdx": "spread"},
  "function": "compute_my_indicator"
}

# 2. Implement indicator function in indicators.py
def compute_my_indicator(cdx_df: pd.DataFrame, params: dict) -> pd.Series:
    return cdx_df["spread"].pct_change(5)

# 3. Define signal in signal_catalog.json
{
  "name": "my_signal",
  "description": "My trading signal",
  "indicator_dependencies": ["my_indicator"],
  "transformations": ["z_score_20d"],
  "enabled": true
}
```

#### 4. Agent Context Update

Run script to preserve changes:
```powershell
.\.specify\scripts\powershell\update-agent-context.ps1 -AgentType copilot
```

This updates `.github/copilot-instructions.md` with:
- Removed patterns (what NOT to do)
- Signal creation workflow (single pattern only)
- Schema validation requirements

---

## Phase 2: Task Generation

**NOT EXECUTED BY /speckit.plan COMMAND**

Run `/speckit.tasks` after reviewing this plan to generate `tasks.md` with:
- Code removal tasks (signals.py deletion)
- Schema update tasks (signal_catalog.json, metadata.py)
- Orchestrator refactoring tasks
- Test cleanup/update tasks
- Documentation update tasks
- Cache invalidation tasks

---

## Risk Assessment

### Breaking Changes

1. **All workflows using legacy signal computation will fail**
   - Impact: HIGH
   - Mitigation: Delete old workflow caches, re-run after migration
   - Justification: Per Constitution VIII, breaking changes are acceptable

2. **External scripts calling compute_* functions will break**
   - Impact: MEDIUM
   - Mitigation: None (follow-up user action required)
   - Justification: Internal development project, no external users

3. **Existing unit tests will fail until updated**
   - Impact: LOW
   - Mitigation: Update tests in same PR as code changes
   - Justification: Standard refactoring practice

### Rollback Strategy

Git revert of the feature branch. No data migration needed (caches are regenerable).

---

## Success Criteria (from spec)

- **SC-001**: ✅ Zero lines of backward compatibility code remain
- **SC-002**: ✅ Zero deprecation warnings in logs
- **SC-003**: ✅ 100% of signals use indicator + transformation pattern
- **SC-004**: ✅ Attempting legacy patterns fails with clear error
- **SC-005**: ✅ Old workflow caches invalidated
- **SC-006**: ✅ No legacy references in codebase
- **SC-007**: ✅ No legacy references in documentation
- **SC-008**: ✅ Test suite runs faster (fewer legacy tests)

---

## Next Steps

1. ✅ Phase 0 Setup: Plan template created and filled
2. ⏭️ Phase 0 Research: Generate research.md (automated below)
3. ⏭️ Phase 1 Design: Generate data-model.md, quickstart.md, contracts/
4. ⏭️ Phase 1 Agent Update: Run update-agent-context script
5. ⏭️ Phase 2 Tasks: Run `/speckit.tasks` command separately
