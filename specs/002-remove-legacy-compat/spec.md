# Feature Specification: Remove Legacy Compatibility from Indicator-Signal Separation

**Feature Branch**: `002-remove-legacy-compat`  
**Created**: December 1, 2025  
**Status**: Draft  
**Input**: User description: "remove backward compatibility that was introduced as part of the indicator-signal-separation. I would like to remove all backward compatibility, deprecation, legacy considerations. Breaks are totally acceptable for this project."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Architecture Without Legacy Code (Priority: P1)

As a developer implementing the indicator-signal separation, I want all backward compatibility code removed so that the codebase is clean, maintainable, and reflects only the new architecture without confusion from legacy patterns.

**Why this priority**: This is the foundation of the feature. Removing legacy code eliminates maintenance burden, reduces cognitive load for developers, and ensures the new architecture is implemented cleanly without compromises.

**Independent Test**: Can be fully tested by verifying that no code paths exist for the old signal computation pattern (monolithic signal functions) and that all signal computations exclusively use the new indicator + transformation pattern. Success means attempting to use old signal patterns results in clear errors, not fallback behavior.

**Acceptance Scenarios**:

1. **Given** the indicator-signal separation architecture is implemented, **When** I inspect the codebase, **Then** I find no conditional logic checking for "legacy mode" or "compatibility mode"

2. **Given** the new signal architecture is in place, **When** I attempt to call old monolithic signal computation functions directly, **Then** the system fails with a clear error indicating those functions no longer exist

3. **Given** the signal catalog has been updated to reference indicators, **When** I run a signal computation, **Then** it exclusively uses the new indicator registry and transformation pipeline without any fallback to old compute functions

---

### User Story 2 - Force Migration to New Architecture (Priority: P2)

As a research manager, I want existing signals to be fully migrated to the new architecture so that all research uses the consistent indicator-signal pattern without any signals using the old monolithic approach.

**Why this priority**: Important for consistency across the research platform. All signals should use the same architectural pattern to ensure maintainability and enable the full benefits of indicator reuse.

**Independent Test**: Can be fully tested by verifying that all three pilot signals (cdx_etf_basis, cdx_vix_gap, spread_momentum) produce outputs exclusively through the indicator + transformation pipeline. Success means all signals in the catalog reference indicators, and no signal has its own embedded computation logic.

**Acceptance Scenarios**:

1. **Given** the three pilot signals exist in the system, **When** I inspect their definitions in signal_catalog.json, **Then** each signal specifies indicator dependencies and transformation references, with no embedded computation logic

2. **Given** a signal is executed, **When** I trace its execution flow, **Then** the flow is: data → indicator computation → indicator caching → signal transformation → output, with no alternative code paths

3. **Given** all signals have been migrated, **When** I search the codebase for old signal compute functions (compute_cdx_etf_basis, compute_cdx_vix_gap, compute_spread_momentum), **Then** these functions either don't exist or exist only as historical references in documentation/tests

---

### User Story 3 - Eliminate Deprecation Warnings (Priority: P3)

As a researcher using the system, I want a clean user experience without deprecation warnings so that I can focus on research without confusion about which patterns to use.

**Why this priority**: Important for user experience and clarity, but not blocking. Once the migration is complete, deprecation warnings become noise rather than helpful guidance.

**Independent Test**: Can be fully tested by running a complete workflow (data → signal → backtest → analysis) and verifying zero deprecation warnings are logged or displayed. Success means no messages about "legacy patterns" or "use new approach instead".

**Acceptance Scenarios**:

1. **Given** I run a complete workflow with the balanced strategy and spread_momentum signal, **When** I review the logs, **Then** I see no deprecation warnings or legacy pattern notifications

2. **Given** I am viewing system documentation, **When** I read about signal creation, **Then** only the new indicator + transformation approach is documented, with no mentions of deprecated patterns

---

### Edge Cases

- What happens when someone tries to execute a workflow that was saved before the migration?
  - System should fail with a clear error indicating the workflow format is no longer supported and must be regenerated using the new architecture

- How does the system handle old cached workflow results that reference monolithic signals?
  - System invalidates all pre-migration workflow caches. Researchers must re-run workflows to generate results using the new architecture.

- What if a researcher has custom scripts that call old signal compute functions directly?
  - Scripts fail with ImportError or AttributeError. Documentation clearly indicates breaking changes and provides migration guide.

- How are old unit tests that verify legacy signal behavior handled?
  - Tests for old monolithic signal functions are removed. New tests verify indicator computation and signal transformation separately.

- What happens to workflow metadata that contains references to old signal computation parameters?
  - Old metadata becomes invalid. System does not attempt to preserve or migrate it. Re-running workflows generates new metadata in the current format.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove all code implementing backward compatibility with monolithic signal computation patterns

- **FR-002**: System MUST remove all conditional logic that checks for "legacy mode", "compatibility mode", or similar fallback behaviors

- **FR-003**: System MUST remove deprecated signal compute functions (compute_cdx_etf_basis, compute_cdx_vix_gap, compute_spread_momentum) from the production codebase

- **FR-004**: System MUST remove all deprecation warnings related to signal computation patterns

- **FR-005**: System MUST invalidate all workflow caches that were generated using the old monolithic signal architecture

- **FR-006**: System MUST update all three pilot signals (cdx_etf_basis, cdx_vix_gap, spread_momentum) to exclusively use the indicator + transformation pattern with no fallback paths

- **FR-007**: System MUST remove any configuration options that enable legacy signal computation modes

- **FR-008**: System MUST fail clearly and immediately when attempting to use removed legacy patterns, with error messages directing users to the new approach

- **FR-009**: Documentation MUST be updated to remove all references to deprecated signal patterns, presenting only the new indicator-signal architecture

- **FR-010**: System MUST remove old unit tests that verify legacy signal computation behavior

- **FR-011**: System MUST create new unit tests that verify signals fail appropriately when attempting to use legacy patterns (if such attempts are still possible through configuration)

- **FR-012**: System MUST remove any migration utility functions that were created to ease the transition from old to new architecture

- **FR-013**: The signal catalog schema MUST enforce indicator references, rejecting any signal definitions that attempt to embed computation logic

### Key Entities

- **Legacy Signal Function**: Old monolithic Python functions that combined indicator computation and signal transformation
  - Lifecycle: Must be completely removed from codebase
  - References: May remain in git history and migration documentation only

- **Workflow Cache**: Persisted workflow results from previous runs
  - Lifecycle: Pre-migration caches must be invalidated
  - Constraint: Only caches generated by new architecture are valid

- **Signal Definition**: Entry in signal_catalog.json
  - Constraint: Must reference indicators, cannot contain embedded computation logic
  - Validation: Schema enforcement at catalog load time

- **Deprecation Warning**: Log messages indicating use of deprecated patterns
  - Lifecycle: All such warnings must be removed from codebase

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero lines of code implement backward compatibility logic for monolithic signal computation

- **SC-002**: Zero deprecation warnings logged during a complete workflow execution (data → signal → backtest → performance → visualization)

- **SC-003**: 100% of signals in the catalog (all three pilot signals) use the indicator + transformation architecture

- **SC-004**: Attempting to use removed legacy patterns results in failure within 1 second with clear error message

- **SC-005**: All workflow caches created before the migration are invalidated, confirmed by re-execution of at least one workflow from each pilot signal

- **SC-006**: Codebase passes static analysis with zero TODOs, FIXMEs, or comments referencing "legacy", "deprecated", or "backward compatibility" related to signal computation

- **SC-007**: Documentation review finds zero references to old monolithic signal patterns in user-facing docs (README, CLI guide, signal registry usage)

- **SC-008**: Test suite runs 10% faster due to removal of legacy pattern tests (estimated based on typical test cleanup gains)

## Assumptions

### Technical Assumptions

1. **Clean break is acceptable**: Breaking changes that require re-running all workflows are acceptable for this project's development phase

2. **No production users yet**: The system is in active development without external production users who would be disrupted by breaking changes

3. **Git history preservation**: While code is removed from the working codebase, it remains accessible in git history for reference if needed

4. **Complete migration first**: This feature assumes the indicator-signal separation (feature 001) has been fully implemented before legacy removal begins

5. **Cache invalidation is simple**: The system can invalidate old workflow caches by either deleting them or updating cache key validation to reject pre-migration results

6. **Schema enforcement**: The signal catalog loading mechanism supports schema validation that can enforce the new structure requirements

### Business Assumptions

1. **Development velocity priority**: The team prioritizes development speed and code clarity over backward compatibility during the research platform's evolution

2. **Re-running workflows is acceptable**: Researchers understand that architectural improvements may require re-running backtests and analyses

3. **Documentation maintenance**: The team will update documentation as part of this feature to reflect only current patterns

4. **No long-term support needed**: There is no requirement to maintain multiple versions or provide long-term support for old signal computation patterns

5. **Learning curve acceptable**: New developers joining the project will learn only the current architecture without needing to understand historical patterns

## Clarifications

*No clarifications needed - the requirements are clear and explicit about removing all backward compatibility without exceptions.*
