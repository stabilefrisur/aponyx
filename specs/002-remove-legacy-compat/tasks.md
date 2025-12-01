---
description: "Task list for removing legacy compatibility from indicator-signal separation"
---

# Tasks: Remove Legacy Compatibility from Indicator-Signal Separation

**Feature Branch**: `002-remove-legacy-compat`
**Input**: Design documents from `/specs/002-remove-legacy-compat/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md, contracts/

**Tests**: No new test files requested. Existing tests will be removed or updated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project structure validation and backup preparation

- [ ] T001 Validate current project structure matches plan.md expectations
- [ ] T002 Create git branch `002-remove-legacy-compat` from main
- [ ] T003 Backup current signal_catalog.json to specs/002-remove-legacy-compat/backups/signal_catalog_before.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema and metadata changes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Update SignalMetadata dataclass in src/aponyx/models/metadata.py to remove legacy fields (compute_function_name, data_requirements, arg_mapping, default_securities)
- [ ] T005 Update SignalMetadata.__post_init__ validation in src/aponyx/models/metadata.py to enforce indicator_dependencies and transformations required
- [ ] T006 Update signal_catalog.json entries to remove legacy fields from all 3 signals (cdx_etf_basis, cdx_vix_gap, spread_momentum)
- [ ] T007 Update SignalRegistry._validate_catalog() in src/aponyx/models/registry.py to remove compute_function_name validation
- [ ] T008 Add indicator_dependencies and transformations existence validation in src/aponyx/models/registry.py

**Checkpoint**: Schema updated - legacy fields removed, new pattern enforced

---

## Phase 3: User Story 1 - Clean Architecture Without Legacy Code (Priority: P1) 🎯 MVP

**Goal**: Remove all backward compatibility code so the codebase is clean and reflects only the new indicator + transformation architecture

**Independent Test**: Verify no code paths exist for old signal computation pattern. Attempting to use old patterns results in clear errors, not fallback behavior.

### Implementation for User Story 1

- [ ] T009 [US1] Delete src/aponyx/models/signals.py file entirely (contains only legacy facade functions)
- [ ] T010 [US1] Remove _compute_signal_legacy_pattern() function from src/aponyx/models/orchestrator.py
- [ ] T011 [US1] Remove _validate_data_requirements() function from src/aponyx/models/orchestrator.py
- [ ] T012 [US1] Simplify _compute_signal() function in src/aponyx/models/orchestrator.py to only call _compute_signal_new_pattern()
- [ ] T013 [US1] Remove config parameter from _compute_signal() function signature in src/aponyx/models/orchestrator.py
- [ ] T014 [US1] Update compute_registered_signals() function in src/aponyx/models/orchestrator.py if needed after _compute_signal() changes
- [ ] T015 [US1] Remove any legacy mode conditional logic from src/aponyx/workflows/concrete_steps.py SignalStep
- [ ] T016 [US1] Search codebase for any remaining "legacy", "deprecated", or "backward compatibility" references and remove them

**Checkpoint**: At this point, all legacy computation code is removed, only indicator + transformation pattern exists

---

## Phase 4: User Story 2 - Force Migration to New Architecture (Priority: P2)

**Goal**: Ensure all three pilot signals are fully migrated and produce outputs exclusively through indicator + transformation pipeline

**Independent Test**: Verify all three signals (cdx_etf_basis, cdx_vix_gap, spread_momentum) execute successfully using only the new pattern, with no fallback paths

### Implementation for User Story 2

- [ ] T017 [US2] Verify cdx_etf_basis signal computes successfully with new pattern in integration test
- [ ] T018 [US2] Verify cdx_vix_gap signal computes successfully with new pattern in integration test
- [ ] T019 [US2] Verify spread_momentum signal computes successfully with new pattern in integration test
- [ ] T020 [US2] Delete all pre-migration workflow directories from data/workflows/ (created before December 1, 2025)
- [ ] T021 [US2] Run `aponyx run --signal cdx_etf_basis --strategy balanced` to generate new workflow cache
- [ ] T022 [US2] Run `aponyx run --signal cdx_vix_gap --strategy aggressive` to generate new workflow cache
- [ ] T023 [US2] Run `aponyx run --signal spread_momentum --strategy balanced` to generate new workflow cache
- [ ] T024 [US2] Verify all three workflows complete successfully with new metadata structure

**Checkpoint**: All pilot signals migrated and generating results with new architecture

---

## Phase 5: User Story 3 - Eliminate Deprecation Warnings (Priority: P3)

**Goal**: Ensure clean user experience without deprecation warnings or legacy pattern notifications

**Independent Test**: Run complete workflow and verify zero deprecation warnings or legacy pattern messages in logs

### Implementation for User Story 3

- [ ] T025 [US3] Search for and remove all deprecation warning log statements related to signal computation in src/aponyx/models/
- [ ] T026 [US3] Search for and remove all "legacy pattern" or "use new approach" log messages in src/aponyx/models/
- [ ] T027 [US3] Update .github/copilot-instructions.md to remove legacy pattern examples and warnings
- [ ] T028 [US3] Update docs/ files to remove all references to deprecated signal patterns
- [ ] T029 [US3] Run `aponyx run --signal spread_momentum --strategy balanced` and verify zero deprecation warnings in logs
- [ ] T030 [US3] Update CHANGELOG.md with breaking changes notice for this feature

**Checkpoint**: All deprecation warnings eliminated, documentation clean

---

## Phase 6: Test Cleanup

**Purpose**: Remove legacy tests and update tests to reflect new architecture

- [ ] T031 [P] Delete tests/models/test_signals.py file entirely (tests legacy facade functions)
- [ ] T032 [P] Update tests/models/test_sign_multiplier.py to use indicator + transformation pattern instead of compute_function_name
- [ ] T033 [P] Remove legacy pattern test functions from tests/models/test_registry.py (keep new pattern tests)
- [ ] T034 [P] Remove legacy field validation tests from tests/models/test_metadata.py (keep new pattern validation)
- [ ] T035 [P] Remove legacy pattern test functions from tests/models/test_orchestrator.py (keep new pattern orchestration tests)
- [ ] T036 Run full test suite with `pytest tests/` and verify all tests pass
- [ ] T037 Verify test count reduced by approximately 27 tests (~4% reduction from baseline 681 tests)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation

- [ ] T038 [P] Run `mypy src/aponyx/models/` to verify type checking passes
- [ ] T039 [P] Run `ruff check src/aponyx/models/` to verify linting passes
- [ ] T040 [P] Search codebase for remaining TODOs, FIXMEs related to legacy patterns and remove them
- [ ] T041 Update PROJECT_STATUS.md to reflect completion of legacy removal
- [ ] T042 Verify signal_catalog_schema.json in contracts/ matches updated schema (6 fields only)
- [ ] T043 Run quickstart.md validation by creating a test signal following the documented pattern
- [ ] T044 Generate final test coverage report and verify no coverage loss
- [ ] T045 Final code review checklist: zero legacy code, zero deprecation warnings, all tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 must complete before User Stories 2 & 3 (removes code they depend on)
  - User Stories 2 & 3 can run in parallel after User Story 1
- **Test Cleanup (Phase 6)**: Depends on User Story 1 completion (tests reference code being removed)
- **Polish (Phase 7)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - BLOCKS other stories (removes core code)
- **User Story 2 (P2)**: Can start after User Story 1 - Tests signal execution with new architecture
- **User Story 3 (P3)**: Can start after User Story 1 - Removes warnings from code that US1 cleaned

### Within Each User Story

**User Story 1** (sequential due to code dependencies):
1. Delete signals.py (T009)
2. Remove orchestrator functions (T010-T014)
3. Update workflows if needed (T015)
4. Final search and cleanup (T016)

**User Story 2** (mostly sequential, tests can be parallel):
1. Verify signals compute (T017-T019 can be parallel)
2. Clear old caches (T020)
3. Regenerate workflows (T021-T023 sequential)
4. Verify metadata (T024)

**User Story 3** (all parallel after US1):
- All tasks can run in parallel (different files)

### Parallel Opportunities

- **Phase 1**: All setup tasks can run in parallel (only 3 tasks)
- **Phase 2**: Tasks T004-T006 can run in parallel (different files), T007-T008 must follow
- **User Story 1**: Tasks are sequential (same file edits)
- **User Story 2**: Tasks T017-T019 can run in parallel (verification tests)
- **User Story 3**: Tasks T025-T028 can run in parallel (different files)
- **Phase 6**: Tasks T031-T035 can run in parallel (different test files)
- **Phase 7**: Tasks T038-T042 can run in parallel (different checks)

---

## Parallel Example: User Story 2 Verification

```bash
# Launch all signal verification tests together:
Task: "Verify cdx_etf_basis signal computes successfully"
Task: "Verify cdx_vix_gap signal computes successfully"  
Task: "Verify spread_momentum signal computes successfully"

# Run workflow regeneration sequentially (shares cache):
Task: "Run cdx_etf_basis workflow" → wait → "Run cdx_vix_gap workflow" → wait → "Run spread_momentum workflow"
```

## Parallel Example: User Story 3 Cleanup

```bash
# Launch all documentation cleanup together:
Task: "Remove deprecation warnings from models/"
Task: "Remove legacy pattern log messages"
Task: "Update copilot-instructions.md"
Task: "Update docs/ files"
```

## Parallel Example: Test Cleanup (Phase 6)

```bash
# Delete/update all test files in parallel:
Task: "Delete test_signals.py"
Task: "Update test_sign_multiplier.py"
Task: "Update test_registry.py"
Task: "Update test_metadata.py"
Task: "Update test_orchestrator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T008) - CRITICAL foundation
3. Complete Phase 3: User Story 1 (T009-T016) - Core legacy removal
4. **STOP and VALIDATE**: Ensure code compiles and main signal path works
5. This is the minimal viable cleanup - legacy code removed

### Incremental Delivery

1. Foundation (Phase 1-2) → Schema updated, legacy fields gone
2. Add User Story 1 (Phase 3) → Legacy code deleted, clean architecture
3. Add User Story 2 (Phase 4) → All signals verified working
4. Add User Story 3 (Phase 5) → Warnings removed, docs updated
5. Test Cleanup (Phase 6) → Test suite reflects new reality
6. Polish (Phase 7) → Production-ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Phases 1-2)
2. Developer A: User Story 1 (Phase 3) - BLOCKING, must complete first
3. Once User Story 1 done:
   - Developer B: User Story 2 (Phase 4)
   - Developer C: User Story 3 (Phase 5)
   - Developer D: Test Cleanup (Phase 6) in parallel with B & C
4. All team: Polish (Phase 7) together

---

## Success Metrics

After all tasks complete, verify:

- ✅ **SC-001**: Zero lines of backward compatibility code (grep for "legacy", "deprecated")
- ✅ **SC-002**: Zero deprecation warnings in workflow logs
- ✅ **SC-003**: 100% of signals use indicator + transformation (verify catalog entries)
- ✅ **SC-004**: Legacy patterns fail with clear error within 1 second
- ✅ **SC-005**: All pre-migration workflow caches deleted and regenerated
- ✅ **SC-006**: Zero legacy TODOs/FIXMEs in codebase
- ✅ **SC-007**: Zero legacy references in docs/
- ✅ **SC-008**: Test suite runs faster (~27 tests removed, ~4% speedup)

## Task Count Summary

- **Total Tasks**: 45
- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 5 tasks
- **Phase 3 (User Story 1)**: 8 tasks
- **Phase 4 (User Story 2)**: 8 tasks
- **Phase 5 (User Story 3)**: 6 tasks
- **Phase 6 (Test Cleanup)**: 7 tasks
- **Phase 7 (Polish)**: 8 tasks

**Parallel Opportunities**: 15 tasks marked [P] can run in parallel within their phases

**Suggested MVP Scope**: Phases 1-3 only (16 tasks) - delivers core legacy code removal

---

## Notes

- All task IDs follow strict format: `- [ ] TXXX [P?] [Story?] Description`
- File paths are absolute where possible, workspace-relative otherwise
- Each user story is independently testable per spec.md requirements
- Breaking changes are explicitly acceptable per Constitution Principle VIII
- No deprecation period - immediate clean break
- Git history preserves removed code if needed for reference
- Backup of signal_catalog.json in Phase 1 provides rollback option
