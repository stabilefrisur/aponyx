# Implementation Readiness Checklist: Indicator-Signal Separation

**Purpose**: Pre-implementation sanity check validating requirements completeness, clarity, and consistency across catalog design, caching architecture, and indicator-signal boundary definitions
**Created**: November 30, 2025
**Feature**: [spec.md](../spec.md)

**Focus Areas**: Caching consistency, catalog validation, indicator-signal boundary clarity
**Depth**: Lightweight sanity check (author self-review before implementation)
**Coverage**: Balanced across US1 (Define Indicators), US2 (Compose Signals), US3 (Track Dependencies)

---

## Requirement Completeness

- [ ] CHK001 - Are data requirements explicitly defined for all 3 pilot indicators (cdx_etf_spread_diff, spread_momentum_5d, cdx_vix_deviation_gap_20d)? [Completeness, Spec §FR-002]
- [ ] CHK002 - Are output units specified for each indicator type (basis_points, ratio, percentage, etc.)? [Completeness, Spec §FR-016, data-model.md §Indicator]
- [ ] CHK003 - Are catalog schema validation rules defined for all required fields (name, compute_function_name, data_requirements, output_units)? [Completeness, Spec §FR-017]
- [ ] CHK004 - Are cache invalidation requirements specified for all scenarios where indicator definitions change? [Completeness, Spec §FR-013, SC-009]
- [ ] CHK005 - Are transformation catalog entries defined with parameter validation rules? [Completeness, Spec §FR-014, data-model.md §Transformation]
- [ ] CHK006 - Are backward compatibility requirements specified for all 3 existing signals during migration? [Completeness, Spec §FR-007, SC-004]
- [ ] CHK007 - Are error handling requirements defined for missing indicator data across all required dates? [Completeness, Spec §FR-010, Edge Cases]
- [ ] CHK008 - Are dependency tracking query requirements specified with performance targets? [Completeness, Spec §SC-007]

## Requirement Clarity - Indicator-Signal Boundary

- [ ] CHK009 - Is "economically interpretable units" clearly defined with concrete examples for each output_units type? [Clarity, Spec §FR-016, Clarifications §Indicator-Signal Boundary]
- [ ] CHK010 - Are the transformation types that belong in indicators vs signals explicitly enumerated? [Clarity, Clarifications §Boundary Rules]
- [ ] CHK011 - Is the distinction between "economically meaningful raw metrics" and "normalized trading signals" measurable? [Clarity, Spec §FR-003, §FR-005]
- [ ] CHK012 - Are the criteria for "economically meaningful transformations" (differences, ratios) vs "statistical standardizations" (z-scores) clearly defined? [Clarity, Assumption §6]
- [ ] CHK013 - Is the worked example decomposition (cdx_vix_gap → indicator + signal) sufficient to guide similar decompositions? [Clarity, Clarifications §Worked Example]
- [ ] CHK014 - Are indicator output validation rules specified to prevent z-scores or percentile ranks at indicator level? [Clarity, Gap]

## Requirement Clarity - Caching Architecture

- [ ] CHK015 - Is the cache key generation algorithm specified with sufficient detail for deterministic implementation? [Clarity, data-model.md §IndicatorCache]
- [ ] CHK016 - Are cache lookup precedence rules defined (check before compute, save after compute)? [Clarity, data-model.md §IndicatorCache Lifecycle]
- [ ] CHK017 - Is the TTL caching strategy for indicators documented alongside existing data caching? [Clarity, Assumption §3]
- [ ] CHK018 - Are cache directory structure requirements specified (data/cache/indicators/{indicator_name}_{params_hash}_{data_hash}.parquet)? [Clarity, plan.md §Project Structure]
- [ ] CHK019 - Is "cache invalidation when indicator definition changes" operationally defined (what triggers it, what gets deleted)? [Clarity, Spec §FR-013]
- [ ] CHK020 - Are cache consistency guarantees specified when multiple signals concurrently request the same indicator? [Clarity, Gap]

## Requirement Clarity - Catalog Validation

- [ ] CHK021 - Are catalog loading failure modes specified (missing file, malformed JSON, invalid schema)? [Clarity, Spec §FR-008, §SC-006]
- [ ] CHK022 - Is "fail within 2 seconds" error messaging requirement quantified with required diagnostic information? [Clarity, Spec §SC-006]
- [ ] CHK023 - Are compute function existence validation rules specified (when checked, what error thrown)? [Clarity, data-model.md §Validation Summary]
- [ ] CHK024 - Are transformation parameter validation rules specified for each transform_type? [Clarity, data-model.md §Transformation Validation]
- [ ] CHK025 - Is the catalog merge conflict resolution workflow documented (git-based, manual resolution)? [Clarity, Spec §FR-018, Assumption §7]

## Requirement Consistency

- [ ] CHK026 - Are indicator naming conventions consistent with signal naming conventions (lowercase, underscores)? [Consistency, data-model.md §Indicator, §Signal]
- [ ] CHK027 - Are validation timing rules consistent across IndicatorRegistry, TransformationRegistry, and SignalRegistry? [Consistency, data-model.md §Validation Summary]
- [ ] CHK028 - Are frozen dataclass patterns consistent across IndicatorMetadata, TransformationMetadata, and updated SignalMetadata? [Consistency, data-model.md]
- [ ] CHK029 - Are catalog path constant naming conventions consistent (INDICATOR_CATALOG_PATH, TRANSFORMATION_CATALOG_PATH, SIGNAL_CATALOG_PATH)? [Consistency, tasks.md §T004-T005]
- [ ] CHK030 - Are caching strategies consistent between indicator cache and existing data cache (TTL, hashing, directory structure)? [Consistency, Assumption §3]
- [ ] CHK031 - Do indicator dependencies in signal_catalog.json align with indicator definitions in indicator_catalog.json? [Consistency, Spec §FR-004]

## Acceptance Criteria Quality

- [ ] CHK032 - Can "indicator computes correctly from raw market data" be objectively verified with test data? [Measurability, US1 Independent Test]
- [ ] CHK033 - Can "output is in basis points (not z-scores)" be programmatically validated? [Measurability, US1 Independent Test]
- [ ] CHK034 - Can "signal output is normalized while indicator remains unchanged" be objectively verified? [Measurability, US2 Independent Test]
- [ ] CHK035 - Can "60% caching improvement" be measured with deterministic test scenarios? [Measurability, Spec §SC-003, tasks.md §T080]
- [ ] CHK036 - Can "identical outputs after migration" be verified with automated regression tests? [Measurability, Spec §SC-004, tasks.md §T063-T064]
- [ ] CHK037 - Can "dependency queries complete in under 1 second" be measured with test catalogs (50 indicators, 100 signals)? [Measurability, Spec §SC-007]
- [ ] CHK038 - Can "define indicator in under 5 minutes" be validated with time-bound user testing? [Measurability, Spec §SC-001]

## Scenario Coverage - Primary Flows

- [ ] CHK039 - Are requirements defined for the complete indicator definition workflow (edit JSON → validate → load → compute → cache)? [Coverage, US1]
- [ ] CHK040 - Are requirements defined for the complete signal composition workflow (reference indicators → apply transformations → combine if multi-indicator)? [Coverage, US2]
- [ ] CHK041 - Are requirements defined for dependency query workflows (indicator → dependent signals, signal → all dependencies)? [Coverage, US3]
- [ ] CHK042 - Are requirements defined for the migration workflow (refactor signal → validate backward compatibility → measure performance)? [Coverage, Phase 6]

## Scenario Coverage - Edge Cases & Error Flows

- [ ] CHK043 - Are requirements defined for partial data availability scenarios (some dates missing for one input)? [Coverage, Spec §FR-010, Edge Cases]
- [ ] CHK044 - Are requirements defined for indicator computation failure scenarios (missing data, division by zero, NaN propagation)? [Coverage, Spec §FR-009, Edge Cases]
- [ ] CHK045 - Are requirements defined for catalog validation failure scenarios (duplicate names, missing compute functions, invalid transform_types)? [Coverage, data-model.md §Validation Summary]
- [ ] CHK046 - Are requirements defined for cache consistency scenarios (concurrent requests, partial writes, stale cache)? [Coverage, Edge Cases]
- [ ] CHK047 - Are requirements defined for dependency resolution failure scenarios (circular dependencies, missing indicator references)? [Coverage, Gap]
- [ ] CHK048 - Are requirements defined for parameter uniqueness scenarios (same indicator different lookback windows)? [Coverage, Edge Cases, Design Decision §2]
- [ ] CHK049 - Are requirements defined for transformation compatibility scenarios (applying incompatible transformation to indicator output)? [Coverage, Gap]

## Scenario Coverage - Non-Functional Requirements

- [ ] CHK050 - Are performance requirements specified for indicator computation with large datasets (multi-year daily data)? [Coverage, Gap]
- [ ] CHK051 - Are memory usage requirements specified for caching strategies with many indicators? [Coverage, Gap]
- [ ] CHK052 - Are type safety requirements specified for all catalog dataclasses (frozen, type hints, validation)? [Coverage, plan.md §Constitution Check III]
- [ ] CHK053 - Are determinism requirements specified for all indicator computations (same inputs = same outputs)? [Coverage, Spec §FR-012]
- [ ] CHK054 - Are logging requirements specified for indicator computation, caching, and validation operations? [Coverage, tasks.md §T071-T073]

## Dependencies & Assumptions - Catalog Design

- [ ] CHK055 - Is the assumption "each unique parameter combination = separate catalog entry" validated as feasible? [Assumption, Design Decision §2]
- [ ] CHK056 - Is the dependency on existing data.transforms module documented and validated? [Dependency, plan.md §Technical Context]
- [ ] CHK057 - Is the assumption "JSON catalog editing is primary workflow" validated with researcher workflows? [Assumption, Clarifications §Session 2025-11-30]
- [ ] CHK058 - Are the constraints on catalog scale (10-30 indicators initially, 50+ over time) explicitly documented? [Assumption §8]
- [ ] CHK059 - Is the assumption "no runtime parameterization" vs "catalog-time parameterization" clearly documented? [Assumption §1]

## Dependencies & Assumptions - Caching Strategy

- [ ] CHK060 - Is the dependency on existing parquet_io.py caching infrastructure documented? [Dependency, tasks.md §T016-T019]
- [ ] CHK061 - Is the assumption "indicator caching similar to data caching (TTL + hashing)" validated? [Assumption §3]
- [ ] CHK062 - Is the assumption "cache invalidation on definition change is acceptable workflow" validated? [Assumption §4, Design Decision §1]
- [ ] CHK063 - Are cache persistence requirements defined (survive application restarts, portable across environments)? [Gap]
- [ ] CHK064 - Is the assumption "no distributed caching or multi-user coordination" explicitly documented? [Gap]

## Dependencies & Assumptions - Migration Path

- [ ] CHK065 - Is the dependency on existing signal functions (compute_cdx_etf_basis, etc.) for backward compatibility documented? [Dependency, Spec §FR-007]
- [ ] CHK066 - Is the assumption "facade pattern maintains API compatibility" validated with existing callers? [Assumption §4]
- [ ] CHK067 - Are the requirements for coexistence of legacy and new signal patterns during migration defined? [Completeness, data-model.md §Signal Migration Strategy]
- [ ] CHK068 - Is the assumption "breaking changes invalidate backtests is acceptable" validated with stakeholders? [Assumption §4, Design Decision §1]

## Ambiguities & Conflicts - Boundary Clarity

- [ ] CHK069 - Is "economically meaningful transformation" vs "statistical standardization" boundary unambiguous for all common operations? [Ambiguity, Clarifications §Boundary Rules]
- [ ] CHK070 - Does the requirement "indicators output interpretable units" conflict with indicators that compute inherently normalized values (correlations)? [Conflict, Edge Cases]
- [ ] CHK071 - Is the treatment of normalization-like operations (deviations from mean) in indicators vs signals clearly disambiguated? [Ambiguity, Clarifications §Worked Example]

## Ambiguities & Conflicts - Catalog Schema

- [ ] CHK072 - Are the overlapping fields between indicator and signal catalogs (data_requirements, default_securities) migration paths clear? [Ambiguity, data-model.md §Signal Attributes]
- [ ] CHK073 - Is the relationship between IndicatorConfig vs IndicatorMetadata.parameters clearly defined (runtime vs catalog-time)? [Ambiguity, data-model.md]
- [ ] CHK074 - Are transformation naming conventions (z_score_20d vs z_score with window=20 parameter) consistently specified? [Ambiguity, tasks.md §T040]

## Ambiguities & Conflicts - Caching Semantics

- [ ] CHK075 - Is the cache key uniqueness guarantee specified when multiple indicators have same name but different parameters? [Conflict, data-model.md §IndicatorCache]
- [ ] CHK076 - Is the behavior defined when cache exists but input data hash changes (recompute vs error)? [Ambiguity, Gap]
- [ ] CHK077 - Are cache eviction policies specified (LRU, size limits, TTL expiration)? [Gap]
- [ ] CHK078 - Is the requirement "cache keyed by input_data_hash" compatible with "cache survives data updates"? [Conflict, data-model.md §IndicatorCache]

## Traceability & Cross-References

- [ ] CHK079 - Are all 10 success criteria (SC-001 to SC-010) mapped to specific tasks in tasks.md? [Traceability, tasks.md §Success Criteria Mapping]
- [ ] CHK080 - Are all 3 user story acceptance scenarios mapped to implementation tasks? [Traceability, spec.md §User Scenarios, tasks.md]
- [ ] CHK081 - Are all edge cases from spec.md addressed in task breakdown or marked as deferred? [Traceability, spec.md §Edge Cases]
- [ ] CHK082 - Are all design decisions from spec.md reflected in data-model.md and tasks.md? [Traceability, spec.md §Design Decisions]
- [ ] CHK083 - Are catalog JSON schemas in contracts/ consistent with metadata dataclasses in data-model.md? [Traceability, contracts/, data-model.md]

---

## Summary

**Total Items**: 83
**Categories**: 13 (Completeness, Clarity x3, Consistency, Acceptance Criteria, Coverage x3, Dependencies x3, Ambiguities x3, Traceability)
**Focus Distribution**:
- Caching consistency: 18 items (CHK015-CHK020, CHK030, CHK046, CHK060-CHK064, CHK075-CHK078)
- Catalog validation: 16 items (CHK003, CHK005, CHK021-CHK025, CHK045, CHK055-CHK059, CHK072-CHK074, CHK083)
- Boundary clarity: 13 items (CHK009-CHK014, CHK069-CHK071)
- User Story coverage: Balanced across US1 (17 items), US2 (14 items), US3 (8 items), Cross-cutting (44 items)

**Risk Areas Emphasized**:
1. **Caching Consistency** - Cache key generation, invalidation triggers, concurrent access, stale data handling
2. **Catalog Validation** - Schema validation, fail-fast behavior, merge conflicts, parameter validation
3. **Boundary Clarity** - Indicator vs signal transformations, output unit requirements, normalization placement

**Usage**: Check items as requirements are validated. Add inline notes for findings or clarifications needed. This is a **requirements quality test** - validates what's written in spec/plan/data-model, NOT implementation correctness.
