# Tasks: Indicator-Signal Separation

**Feature**: `001-indicator-signal-separation`  
**Input**: Design documents from [specs/001-indicator-signal-separation/](.)  
**Date**: 2025-11-30

**Prerequisites**: ✅ plan.md, ✅ spec.md, ✅ research.md, ✅ data-model.md, ✅ contracts/

**Tests**: NOT explicitly requested in spec - tasks focus on implementation and integration validation

---

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All paths relative to repository root

---

## Phase 1: Setup

**Purpose**: Create catalogs and cache infrastructure

- [ ] T001 Create indicator catalog directory structure at data/cache/indicators/
- [ ] T002 Create empty indicator_catalog.json at src/aponyx/models/indicator_catalog.json
- [ ] T003 Create empty transformation_catalog.json at src/aponyx/models/transformation_catalog.json
- [ ] T004 [P] Add INDICATOR_CATALOG_PATH constant to src/aponyx/config/__init__.py
- [ ] T005 [P] Add TRANSFORMATION_CATALOG_PATH constant to src/aponyx/config/__init__.py
- [ ] T006 [P] Add INDICATOR_CACHE_DIR constant to src/aponyx/config/__init__.py

**Checkpoint**: Infrastructure ready - catalog files exist, constants defined

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core metadata and registry classes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 [P] Create IndicatorMetadata dataclass in src/aponyx/models/metadata.py
- [ ] T008 [P] Create TransformationMetadata dataclass in src/aponyx/models/metadata.py
- [ ] T009 [P] Create IndicatorConfig dataclass in src/aponyx/models/config.py
- [ ] T010 [P] Create TransformationConfig dataclass in src/aponyx/models/config.py
- [ ] T011 Create IndicatorRegistry class in src/aponyx/models/registry.py
- [ ] T012 Create TransformationRegistry class in src/aponyx/models/registry.py
- [ ] T013 Update SignalMetadata to add indicator_dependencies field in src/aponyx/models/metadata.py
- [ ] T014 Update SignalMetadata to add transformations field in src/aponyx/models/metadata.py
- [ ] T015 Update SignalRegistry to build dependency index in src/aponyx/models/registry.py
- [ ] T016 [P] Add cache key generation function to src/aponyx/persistence/parquet_io.py
- [ ] T017 [P] Add save_indicator_to_cache function to src/aponyx/persistence/parquet_io.py
- [ ] T018 [P] Add load_indicator_from_cache function to src/aponyx/persistence/parquet_io.py
- [ ] T019 [P] Add invalidate_indicator_cache function to src/aponyx/persistence/parquet_io.py

**Checkpoint**: Foundation ready - all registries, metadata, and cache utilities exist

---

## Phase 3: User Story 1 - Define Reusable Indicators (Priority: P1) 🎯 MVP

**Goal**: Researchers can define market indicators as standalone computations that output economically interpretable values (bps, ratios) without signal-level normalization

**Independent Test**: Define "cdx_etf_spread_diff" indicator, compute from raw market data, verify output is in basis points (not z-scores) and can be cataloged/retrieved without signal context

### Implementation for User Story 1

- [X] T020 [P] [US1] Create indicators.py module skeleton at src/aponyx/models/indicators.py
- [X] T021 [P] [US1] Implement compute_cdx_etf_spread_diff function in src/aponyx/models/indicators.py
- [X] T022 [P] [US1] Implement compute_spread_momentum function in src/aponyx/models/indicators.py
- [X] T023 [P] [US1] Implement compute_cdx_vix_deviation_gap function in src/aponyx/models/indicators.py
- [X] T024 [US1] Create compute_indicator orchestration function in src/aponyx/models/indicators.py
- [X] T025 [US1] Add indicator computation with caching to compute_indicator function
- [X] T026 [US1] Populate indicator_catalog.json with 3 pilot indicators (cdx_etf_spread_diff, spread_momentum_5d, cdx_vix_deviation_gap_20d)
- [X] T027 [US1] Validate IndicatorRegistry loads catalog without errors
- [X] T028 [P] [US1] Create test_indicators.py at tests/models/test_indicators.py
- [X] T029 [P] [US1] Add test_compute_cdx_etf_spread_diff to tests/models/test_indicators.py
- [X] T030 [P] [US1] Add test_compute_spread_momentum to tests/models/test_indicators.py
- [X] T031 [P] [US1] Add test_compute_cdx_vix_deviation_gap to tests/models/test_indicators.py
- [X] T032 [US1] Add test_compute_indicator_with_caching to tests/models/test_indicators.py
- [X] T033 [P] [US1] Create test_indicator_registry.py at tests/models/test_indicator_registry.py
- [X] T034 [P] [US1] Add test_load_indicator_catalog to tests/models/test_indicator_registry.py
- [X] T035 [P] [US1] Add test_validate_compute_functions_exist to tests/models/test_indicator_registry.py
- [X] T036 [US1] Add test_indicator_cache_invalidation to tests/models/test_indicators.py

**Checkpoint**: ✅ User Story 1 complete - indicators can be defined, computed, cached, and tested independently

---

## Phase 4: User Story 2 - Compose Signals from Indicators (Priority: P2)

**Goal**: Researchers can construct trading signals by applying transformations to indicators without modifying indicator code

**Independent Test**: Create signal that applies z-score normalization to "cdx_etf_spread_diff" indicator, verify signal output is normalized while indicator remains unchanged

### Implementation for User Story 2

- [ ] T037 [P] [US2] Create signal_composer.py module at src/aponyx/models/signal_composer.py
- [ ] T038 [P] [US2] Implement apply_signal_transformation function in src/aponyx/models/signal_composer.py
- [ ] T039 [US2] Implement compose_signal orchestration function in src/aponyx/models/signal_composer.py
- [ ] T040 [US2] Populate transformation_catalog.json with common transformations (z_score_20d, z_score_60d, volatility_adjust_20d, diff_5d)
- [ ] T041 [US2] Update signal_catalog.json to add indicator_dependencies for cdx_etf_basis signal
- [ ] T042 [US2] Update signal_catalog.json to add transformations for cdx_etf_basis signal
- [ ] T043 [US2] Update signal_catalog.json to add indicator_dependencies for cdx_vix_gap signal
- [ ] T044 [US2] Update signal_catalog.json to add transformations for cdx_vix_gap signal
- [ ] T045 [US2] Update signal_catalog.json to add indicator_dependencies for spread_momentum signal
- [ ] T046 [US2] Update signal_catalog.json to add transformations for spread_momentum signal
- [ ] T047 [P] [US2] Create test_signal_composer.py at tests/models/test_signal_composer.py
- [ ] T048 [P] [US2] Add test_apply_signal_transformation to tests/models/test_signal_composer.py
- [ ] T049 [P] [US2] Add test_compose_signal_single_indicator to tests/models/test_signal_composer.py
- [ ] T050 [US2] Add test_compose_signal_with_composition_logic to tests/models/test_signal_composer.py
- [ ] T051 [P] [US2] Create test_transformation_registry.py at tests/models/test_transformation_registry.py
- [ ] T052 [P] [US2] Add test_load_transformation_catalog to tests/models/test_transformation_registry.py
- [ ] T053 [P] [US2] Add test_validate_transform_types to tests/models/test_transformation_registry.py

**Checkpoint**: User Story 2 complete - signals can be composed from indicators with transformations

---

## Phase 5: User Story 3 - Track Indicator-Signal Dependencies (Priority: P3)

**Goal**: Research managers can query which signals depend on which indicators for impact analysis

**Independent Test**: Query system for all signals using "cdx_etf_spread_diff" indicator, verify list matches catalog definitions

### Implementation for User Story 3

- [ ] T054 [US3] Implement get_dependent_signals method in IndicatorRegistry at src/aponyx/models/registry.py
- [ ] T055 [US3] Implement get_all_dependencies method in IndicatorRegistry at src/aponyx/models/registry.py
- [ ] T056 [US3] Implement _build_dependency_index helper in IndicatorRegistry at src/aponyx/models/registry.py
- [ ] T057 [P] [US3] Add test_get_dependent_signals to tests/models/test_indicator_registry.py
- [ ] T058 [P] [US3] Add test_get_all_dependencies to tests/models/test_indicator_registry.py
- [ ] T059 [P] [US3] Add test_dependency_index_updates to tests/models/test_indicator_registry.py

**Checkpoint**: User Story 3 complete - dependency tracking fully functional

---

## Phase 6: Backward Compatibility & Migration

**Purpose**: Maintain backward compatibility with existing signals during migration

- [ ] T060 Refactor compute_cdx_etf_basis to use facade pattern in src/aponyx/models/signals.py
- [ ] T061 Refactor compute_cdx_vix_gap to use facade pattern in src/aponyx/models/signals.py
- [ ] T062 Refactor compute_spread_momentum to use facade pattern in src/aponyx/models/signals.py
- [ ] T063 Add test_legacy_signal_compatibility to tests/models/test_signals.py
- [ ] T064 Verify existing backtest results reproduce identically with refactored signals

**Checkpoint**: Backward compatibility verified - existing workflows continue to work

---

## Phase 7: Integration with Workflows

**Purpose**: Integrate indicator-signal separation into existing workflow orchestration

- [ ] T065 Update compute_registered_signals in orchestrator.py to use compose_signal for new pattern signals
- [ ] T066 Update compute_registered_signals to handle both legacy and new signal patterns
- [ ] T067 Update workflow DataStep to support indicator caching
- [ ] T068 Update workflow SignalStep to use signal composition
- [ ] T069 Add indicator cache invalidation to workflow cleanup logic
- [ ] T070 Add test_workflow_with_indicator_caching to tests/workflows/test_engine.py

**Checkpoint**: Workflows fully integrated with indicator-signal architecture

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finalize implementation with documentation and validation

- [ ] T071 [P] Add indicator computation logging (INFO level) to indicators.py
- [ ] T072 [P] Add signal composition logging (INFO level) to signal_composer.py
- [ ] T073 [P] Add cache operation logging (DEBUG level) to parquet_io.py
- [ ] T074 Update copilot-instructions.md with indicator definition examples (if not already done)
- [ ] T075 Update copilot-instructions.md with signal composition examples (if not already done)
- [ ] T076 Validate quickstart.md examples work correctly
- [ ] T077 Run full test suite and verify all 681+ tests pass
- [ ] T078 Run mypy type checking and fix any errors
- [ ] T079 Run ruff format and ruff check on all modified files
- [ ] T080 Measure indicator caching performance improvement (target: 60% reduction)

**Checkpoint**: Feature complete, validated, and ready for production use

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ⚠️ BLOCKS ALL USER STORIES
    ↓
Phase 3 (US1 - Define Indicators) 🎯 MVP ←─┐
    ↓                                        │
Phase 4 (US2 - Compose Signals)             │ Can parallelize
    ↓                                        │ if team capacity
Phase 5 (US3 - Track Dependencies) ←────────┘
    ↓
Phase 6 (Backward Compatibility)
    ↓
Phase 7 (Workflow Integration)
    ↓
Phase 8 (Polish)
```

### User Story Dependencies

- **User Story 1 (P1)**: Depends ONLY on Phase 2 Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Depends on Phase 2 Foundational - Uses indicators from US1 but can be developed in parallel
- **User Story 3 (P3)**: Depends on Phase 2 Foundational - Can be developed in parallel with US1/US2

### Within Each User Story

**User Story 1**:
1. Indicator functions (T021-T023) can run in parallel
2. compute_indicator (T024-T025) depends on functions existing
3. Catalog population (T026) can happen anytime
4. Tests (T028-T036) can run in parallel after implementation

**User Story 2**:
1. signal_composer functions (T037-T039) depend on US1 indicators existing
2. Catalog updates (T040-T046) can happen anytime
3. Tests (T047-T053) can run in parallel after implementation

**User Story 3**:
1. Registry methods (T054-T056) depend on US2 signal catalog updates
2. Tests (T057-T059) can run in parallel after implementation

### Parallel Opportunities

**Phase 1 (Setup)** - All parallelizable:
```bash
T004, T005, T006 can run simultaneously (different constant additions)
```

**Phase 2 (Foundational)** - Parallel groups:
```bash
# Group 1: Metadata classes
T007, T008, T009, T010 (different dataclasses)

# Group 2: Cache utilities
T016, T017, T018, T019 (different functions in same file - do sequentially or coordinate)
```

**Phase 3 (User Story 1)** - Parallel groups:
```bash
# Indicator functions
T021, T022, T023 (different functions)

# Tests
T028, T029, T030, T031, T033, T034, T035 (different test files/functions)
```

**Phase 4 (User Story 2)** - Parallel groups:
```bash
# Implementation
T037, T038 (different functions in signal_composer.py)

# Tests
T047, T048, T049, T051, T052, T053 (different test files/functions)
```

**Phase 5 (User Story 3)** - Parallel groups:
```bash
# Tests
T057, T058, T059 (different test functions)
```

**Phase 8 (Polish)** - Parallel groups:
```bash
# Logging
T071, T072, T073 (different files)

# Documentation
T074, T075 (different sections)
```

---

## Parallel Example: User Story 1

```bash
# Launch all indicator functions in parallel:
Task T021: "Implement compute_cdx_etf_spread_diff in indicators.py"
Task T022: "Implement compute_spread_momentum in indicators.py"
Task T023: "Implement compute_cdx_vix_deviation_gap in indicators.py"

# Then launch all tests in parallel:
Task T028: "Create test_indicators.py"
Task T029: "Add test_compute_cdx_etf_spread_diff"
Task T030: "Add test_compute_spread_momentum"
Task T031: "Add test_compute_cdx_vix_deviation_gap"
Task T033: "Create test_indicator_registry.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

**Minimal viable delivery** - 36 tasks (T001-T036):

1. **Phase 1**: Setup (6 tasks) - Catalog files and constants
2. **Phase 2**: Foundational (13 tasks) - Metadata, registries, cache utilities
3. **Phase 3**: User Story 1 (17 tasks) - Indicator definition and computation
4. **STOP and VALIDATE**: Test indicators independently
5. **Deploy/Demo**: Show reusable indicator computation with caching

**Estimated effort**: 2-3 days for single developer

**Value delivered**: Researchers can define and compute indicators independently of signals

---

### Incremental Delivery

**Build in priority order** - validate each increment:

1. **MVP** (T001-T036): User Story 1 → Independent indicator computation ✅
2. **Increment 2** (T037-T053): User Story 2 → Signal composition from indicators ✅
3. **Increment 3** (T054-T059): User Story 3 → Dependency tracking ✅
4. **Integration** (T060-T070): Backward compatibility and workflow integration ✅
5. **Polish** (T071-T080): Logging, documentation, performance validation ✅

Each increment adds value without breaking previous functionality.

---

### Parallel Team Strategy

**With 3 developers** after Phase 2 completes:

- **Developer A**: User Story 1 (T020-T036) - Indicators
- **Developer B**: User Story 2 (T037-T053) - Signal composition (can start in parallel once indicators module exists)
- **Developer C**: User Story 3 (T054-T059) - Dependency tracking (can start in parallel)

Then converge for integration (T060-T070) and polish (T071-T080).

**Estimated effort**: 3-4 days with parallel team

---

## Task Count Summary

- **Total Tasks**: 80
- **Setup**: 6 tasks
- **Foundational**: 13 tasks (BLOCKING)
- **User Story 1**: 17 tasks (MVP - P1)
- **User Story 2**: 17 tasks (P2)
- **User Story 3**: 6 tasks (P3)
- **Backward Compatibility**: 5 tasks
- **Integration**: 6 tasks
- **Polish**: 10 tasks

**Parallelizable**: ~30 tasks marked [P] can run simultaneously (35% of total)

**MVP Tasks**: 36 (Setup + Foundational + US1)

**Independent Stories**: All 3 user stories can be validated independently

---

## Success Criteria Mapping

Tasks directly address spec success criteria:

- **SC-001** (Define indicator <5 min): T026 - catalog-based definition
- **SC-002** (Create signal <10 min): T040-T046 - catalog-based composition
- **SC-003** (60% caching improvement): T016-T019, T080 - caching + measurement
- **SC-004** (Identical outputs): T063-T064 - backward compatibility validation
- **SC-005** (100% testable independently): T028-T036 - independent indicator tests
- **SC-006** (Fail within 2s): T027 - registry validation
- **SC-007** (Dependency queries <1s): T054-T059 - dependency tracking
- **SC-008** (Transformation catalog): T040, T051-T053 - transformation registry
- **SC-009** (Invalidation within 5s): T019, T069 - cache invalidation
- **SC-010** (100% interpretable units): T021-T023, T029-T031 - indicator outputs in bps/ratios

---

## Notes

- **[P]** indicates tasks operating on different files or independent functions
- **[US1/US2/US3]** maps each task to its user story for traceability
- **Tests** are included but not explicitly requested - focus on validation
- **Checkpoints** enable stopping after any phase to validate incrementally
- **Backward compatibility** (Phase 6) ensures existing workflows continue functioning
- **Integration** (Phase 7) wires everything into existing workflow engine
- Commit frequently - after each task or logical group
- Run tests continuously - don't wait until the end
