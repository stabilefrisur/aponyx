# Feature Specification: Indicator-Signal Separation

**Feature Branch**: `001-indicator-signal-separation`  
**Created**: November 30, 2025  
**Status**: Draft  
**Input**: User description: "Separate the definition of indicators from the construction of signals. Currently the project lumps both into one and calls it signals. This is part of a broader effort to more clearly separate: 1. traded products (highly liquid credit derivatives) 2. indicators definition (spread ratios, curve slopes, momentum, etc) 3. signal construction (transformations on indicators to produce trade signals) 4. trade construction (mapping traded product to signals) 5. backtest execution (simulation of trading including realistic assumptions). For now focus on the separation of indicator and signal."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Reusable Indicators (Priority: P1)

As a researcher, I want to define market indicators (spread ratios, curve slopes, momentum) as standalone, reusable computations so that I can combine them in different ways to create multiple trading signals without duplicating calculation logic.

**Why this priority**: This is the foundational requirement that enables all other use cases. Without separating indicator definitions, researchers cannot compose signals efficiently or maintain consistency across strategies.

**Independent Test**: Can be fully tested by defining a single indicator (e.g., "CDX-ETF spread ratio") and verifying it computes correctly from raw market data independently of any signal logic. Success means the indicator can be calculated, cataloged, and retrieved without reference to trading signals.

**Acceptance Scenarios**:

1. **Given** I have CDX and ETF spread data loaded, **When** I request computation of the "cdx_etf_ratio" indicator, **Then** the system returns a time series of ratio values without applying any signal transformations (z-score, thresholds, etc.)

2. **Given** I have defined an indicator "spread_momentum" that computes 5-day spread changes by editing indicator_catalog.json, **When** I inspect the indicator catalog, **Then** I can see its data requirements, computation parameters, and output specification without any signal-specific metadata

3. **Given** multiple signals reference the same indicator "vix_cdx_deviation", **When** the indicator is computed, **Then** it is calculated once and cached for reuse across all dependent signals

4. **Given** I have an indicator "cdx_vix_deviation_gap" that computes (CDX deviation - VIX deviation) in raw units, **When** I inspect the indicator output, **Then** I see the gap values in interpretable units (not z-scores) and can create multiple signals with different normalization windows from this one indicator

---

### User Story 2 - Compose Signals from Indicators (Priority: P2)

As a quantitative researcher, I want to construct trading signals by applying transformations (z-score normalization, threshold filters, regime adjustments) to one or more indicators so that I can rapidly test different signal formulations without modifying the underlying indicator calculations.

**Why this priority**: This enables the core value proposition - rapid signal experimentation. Once indicators are separated (P1), researchers can combine and transform them in various ways to test trading hypotheses.

**Independent Test**: Can be fully tested by creating a signal that applies z-score normalization to the "cdx_etf_ratio" indicator and verifying the signal output is the normalized version of the indicator. Success means defining a signal requires only specifying indicator inputs and transformation logic, not re-implementing calculations.

**Acceptance Scenarios**:

1. **Given** I have a "cdx_etf_ratio" indicator defined, **When** I create a signal that applies z-score normalization over a 20-day window, **Then** the signal outputs normalized values while the underlying indicator remains unchanged

2. **Given** I have two indicators "spread_change" and "volatility", **When** I create a signal that divides spread_change by volatility, **Then** the signal correctly combines both indicators without either indicator knowing about the other

3. **Given** a signal "basis_signal" references indicator "cdx_etf_basis", **When** I update the signal's normalization window from 20 to 60 days, **Then** the underlying indicator computation remains unchanged and only the signal transformation logic updates

---

### User Story 3 - Track Indicator-Signal Dependencies (Priority: P3)

As a research manager, I want to see which signals depend on which indicators so that I can understand the impact of indicator changes on downstream signals and backtest results.

**Why this priority**: Important for maintenance and governance, but not blocking for initial research workflows. Can be implemented after the core separation is working.

**Independent Test**: Can be fully tested by querying the system for all signals using the "cdx_etf_basis" indicator and verifying the list is accurate. Success means the dependency graph is queryable and reflects actual usage.

**Acceptance Scenarios**:

1. **Given** I have 5 signals that reference the "vix_level" indicator, **When** I query dependencies for "vix_level", **Then** the system returns all 5 signal names that depend on it

2. **Given** I modify the calculation parameters for indicator "spread_momentum", **When** I request impact analysis, **Then** the system identifies all signals that would be affected by the change

---

### Edge Cases

- What happens when an indicator's data requirements cannot be satisfied (missing instrument)?
  - System should fail fast with clear error indicating which data is missing and for which indicator
  
- How does the system handle indicator computation failures during signal construction?
  - Signal computation should fail gracefully with an error identifying the specific indicator that failed and why
  
- What if multiple signals request the same indicator with different computation parameters (e.g., different lookback windows)?
  - Each unique combination of indicator + parameters should be treated as a distinct cached computation to avoid conflicts
  
- How does caching work when indicators are shared across multiple workflow runs?
  - Indicator cache should be keyed by (indicator_name, parameters, input_data_hash) to ensure deterministic retrieval and avoid stale results
  
- What if an indicator definition changes (new version) while old backtest results reference the old version?
  - System treats indicator changes as breaking changes that invalidate dependent workflow results. Researchers must re-run backtests when indicators change to ensure consistency.

- What if I want to test the same economic indicator with different lookback windows (e.g., 20-day vs 60-day deviation)?
  - Create separate indicator definitions: `cdx_vix_deviation_gap_20d` and `cdx_vix_deviation_gap_60d`. Each is a distinct catalog entry. This makes the catalog explicit about which configurations are actually being used.

- What if an indicator's economic logic requires normalization (e.g., computing a correlation coefficient which is inherently normalized)?
  - If the output is economically meaningful in its normalized form (correlation = -1 to +1 has clear interpretation), it can remain in the indicator. The key test: can a researcher interpret the raw value without knowing signal parameters? Correlation passes this test; z-scores do not.

- What if two researchers modify the indicator catalog at the same time?
  - Catalogs are version-controlled via git. Concurrent modifications result in merge conflicts that researchers resolve using standard git merge tools. System validates merged catalog on next load.

- What if an indicator requires multiple data inputs but some dates have missing data for one input (partial availability)?
  - System fails immediately if ANY required data is missing for ANY date. This ensures deterministic behavior and prevents subtle data alignment bugs. Data validation occurs before indicator computation begins, with clear error messages indicating which input has missing dates.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST separate indicator definitions into their own catalog distinct from signal definitions
  
- **FR-002**: System MUST allow indicators to be defined with explicit data requirements (e.g., "requires CDX spread and ETF spread")
  
- **FR-003**: System MUST compute indicators as economically interpretable time series (natural units like bps, ratios, deviations) without applying standardization transformations (z-score normalization, percentile ranking, threshold filters)
  
- **FR-004**: System MUST allow signals to reference one or more indicators as inputs
  
- **FR-005**: System MUST support signal definitions that specify transformation logic applied to indicators (z-score normalization, volatility adjustment, ratio calculations)
  
- **FR-006**: System MUST cache computed indicators to avoid redundant calculations when multiple signals reference the same indicator
  
- **FR-007**: System MUST maintain backward compatibility with existing signal computation for the three pilot signals (cdx_etf_basis, cdx_vix_gap, spread_momentum) during migration period
  
- **FR-008**: System MUST validate indicator data requirements can be satisfied before attempting computation
  
- **FR-009**: System MUST propagate indicator computation errors to dependent signals with clear diagnostic information

- **FR-010**: System MUST fail immediately if any required indicator input data is missing for any date in the computation period, with clear error messages indicating which input has missing dates
  
- **FR-010**: Indicators MUST be testable independently without requiring signal or backtest context
- **FR-012**: Each indicator MUST have corresponding unit tests that verify output correctness using known-good reference values (following existing test patterns in tests/models/test_signals.py). No runtime output validation is performed beyond data type checks.  
- **FR-011**: System MUST track which signals depend on which indicators for impact analysis
  
- **FR-012**: Indicator computations MUST be deterministic (same inputs produce same outputs) for reproducibility

- **FR-013**: System MUST invalidate all dependent workflow results (signals, backtests, performance analyses) when an indicator definition changes

- **FR-014**: System MUST maintain a separate catalog of reusable signal transformations (z-score, normalization, volatility adjustment, etc.)

- **FR-015**: Each unique combination of indicator parameters MUST be defined as a separate indicator in the catalog (e.g., "momentum_5d" and "momentum_10d" are distinct indicators)

- **FR-016**: Indicator outputs MUST be in economically interpretable units (basis points, ratios, percentage changes, etc.) documented in the indicator metadata

- **FR-017**: System MUST support JSON-based indicator catalog editing with validation on load (similar to existing signal_catalog.json pattern)

- **FR-018**: Indicator and signal catalogs MUST be version-controlled files with concurrent modifications resolved via git merge workflow

### Key Entities

- **Indicator**: A reusable market metric computation (e.g., spread ratio, curve slope, momentum)
  - Attributes: name, description, data requirements (instrument types + fields), computation parameters, output units (bps, ratio, percentage, etc.), economic interpretation
  - Relationships: Referenced by one or more Signals
  - Lifecycle: Defined once, computed on-demand, cached for reuse
  - Constraint: Output must be in economically interpretable units, not pre-normalized
  
- **Signal**: A trading signal derived from one or more Indicators via transformations
  - Attributes: name, description, indicator dependencies, transformation logic, sign convention
  - Relationships: References one or more Indicators, consumed by Strategies
  - Lifecycle: Defined with indicator references, computed by applying transformations to indicator outputs
  
- **Indicator Catalog**: Registry of all available indicator definitions
  - Attributes: catalog path, validation rules, metadata schema
  - Relationships: Contains all Indicator definitions, distinct from Signal Catalog
  
- **Signal Catalog**: Registry of all available signal definitions (existing, now references indicators)
  - Attributes: catalog path, validation rules, metadata schema (updated to include indicator references)
  - Relationships: Contains all Signal definitions, references Indicator Catalog entries
  
- **Indicator Cache**: Storage for computed indicator time series
  - Attributes: cache key (indicator_name + data_hash), computed values, timestamp
  - Relationships: Populated by Indicator computations, consumed by Signal computations
  - Lifecycle: Invalidated when indicator definition changes

- **Transformation Catalog**: Registry of reusable signal transformation operations
  - Attributes: transformation name, description, parameters, validation rules
  - Relationships: Referenced by Signal definitions to specify how indicators are transformed into signals
  - Examples: z_score_normalize, volatility_adjust, threshold_filter, rolling_rank

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Researchers can define a new indicator in under 5 minutes without modifying signal code

- **SC-002**: Researchers can create a new signal by composing existing indicators in under 10 minutes

- **SC-003**: Indicator computation time is reduced by 60% when multiple signals reference the same indicator (due to caching)

- **SC-004**: All three pilot signals (cdx_etf_basis, cdx_vix_gap, spread_momentum) continue to produce identical outputs after migration to indicator-signal architecture

- **SC-005**: 100% of indicator definitions are testable independently without signal or backtest context

- **SC-006**: System fails within 2 seconds with clear error message when indicator data requirements cannot be satisfied

- **SC-007**: Dependency queries (which signals use this indicator) complete in under 1 second for catalogs containing up to 50 indicators and 100 signals

- **SC-008**: All common signal transformations (z-score, volatility adjustment, threshold filters) are available in the transformation catalog and reusable across signal definitions

- **SC-009**: System detects indicator definition changes and invalidates all dependent caches and workflow results within 5 seconds

- **SC-010**: 100% of indicator outputs can be interpreted in their natural units (e.g., "CDX-VIX gap is +15 bps") without requiring knowledge of signal normalization parameters

## Assumptions

### Technical Assumptions

1. **Indicator parameters are fixed at definition time**: Each unique combination of indicator parameters is a separate catalog entry (e.g., "momentum_5d" and "momentum_10d" are distinct indicators with no runtime parameterization)

2. **Indicators output pandas Series**: All indicators return time-series data as pandas Series with DatetimeIndex, consistent with current signal outputs

3. **Caching strategy**: Indicator caching uses similar TTL and hashing approach as current data caching (indicator name-based file naming with input data hashing). Cache is invalidated when indicator definition changes.

4. **Migration path**: Existing signal functions (compute_cdx_etf_basis, etc.) will be refactored into indicator computations + signal transformations, but the external API remains unchanged during transition

5. **No multi-asset indicators initially**: First version supports indicators that compute over single or multiple time series but output a single time series (no matrix outputs or multi-asset tensors)

6. **Transformation composition**: Indicators may apply economically meaningful transformations (differences, ratios, deviations from mean) but NOT statistical standardizations (z-scores, percentile ranks). The latter are exclusively signal-level transformations.

7. **Version control integration**: Catalogs are committed to git repository. Concurrent modifications follow standard git workflow (pull, edit, commit, push, resolve conflicts if needed).

8. **Catalog scale**: System is designed to efficiently handle 10-30 indicators in the first 6 months, with architecture supporting growth to 50+ indicators over time. Initial implementation optimizes for moderate research portfolio size.

9. **Observability approach**: Indicator computation relies on standard Python logging (INFO for operations, DEBUG for details) without additional metrics infrastructure. Performance measurement uses existing workflow timing mechanisms (T080 measures caching improvement via workflow execution time comparison).

### Business Assumptions

1. **Researcher workflow**: Researchers currently define signals by writing Python functions; the new system should still allow this but also support declarative indicator composition

2. **Backward compatibility requirement**: Existing backtest results must remain valid and reproducible after the migration

3. **Governance requirement**: The separation supports future audit requirements where indicator definitions may need independent validation from signal trading logic

4. **Breaking changes are acceptable**: Researchers expect that changing indicator definitions will invalidate dependent backtests, similar to how code changes invalidate test results. Re-running backtests is acceptable workflow.

5. **Transformation reusability**: Common signal transformations (z-score, volatility adjustment, etc.) are applied frequently across multiple signals and benefit from being cataloged as reusable operations

6. **Exploratory testing workflow**: Researchers test new indicator configurations by temporarily adding them to the catalog, testing via Python scripts or unit tests, then removing unsuccessful experiments via git. This simple workflow avoids maintaining separate experimental infrastructure while leveraging version control for cleanup.

## Clarifications

### Session 2025-11-30

- Q: When a researcher wants to define a new indicator, what is the primary workflow? → A: JSON catalog editing - Researchers edit indicator_catalog.json directly, system validates on load
- Q: When multiple researchers are working on the same codebase, how should the system handle concurrent catalog modifications? → A: Git-based conflict resolution - Catalogs are version-controlled files, conflicts resolved via standard git merge
- Q: What is the expected number of indicators to be defined in the first 6 months after implementation? → A: 10-30 indicators (moderate research portfolio)
- Q: How should the system handle partial data availability when computing an indicator that requires multiple inputs? → A: Fail immediately if ANY required data is missing for ANY date
- Q: What observability metrics should be captured for indicator computation beyond basic logging? → A: No metrics beyond logs (keep it simple)
- Q: How should researchers test new indicator configurations during development before adding them to the official catalog? → A: Add to catalog, test, then remove if not useful
- Q: What mechanism should exist to detect when an indicator produces incorrect or unexpected output? → A: Unit tests required (per existing patterns), no runtime validation

### Indicator-Signal Boundary Definition

**Core Principle**: Indicators compute **economically meaningful raw metrics** from market data. Signals apply **normalization and regime adjustments** to indicators to produce tradeable signals.

**Boundary Rules**:

1. **Indicators produce interpretable values** - Output should have economic meaning (e.g., "CDX-VIX deviation gap in basis points", "5-day spread change in bps", "CDX/ETF ratio")

2. **Signals produce standardized trading signals** - Output is normalized for position sizing (e.g., z-scores, percentile ranks, binary thresholds)

3. **Transformation location**:
   - **In Indicator**: Transformations that define the economic metric (ratios, differences, deviations, curve slopes)
   - **In Signal**: Transformations that standardize for trading (z-score, volatility normalization, regime filters)

**Example Decomposition**:

| Current "Signal" | Indicator Component | Signal Component |
|------------------|--------------------|-----------------|
| **cdx_etf_basis** | `cdx_etf_spread_diff` = CDX spread - ETF spread (raw bps) | Apply z-score normalization over 20-day window |
| **cdx_vix_gap** | `cdx_vix_deviation_gap` = (CDX deviation from mean) - (VIX deviation from mean) (raw gap) | Apply z-score normalization to the gap |
| **spread_momentum** | `cdx_spread_change_5d` = 5-day CDX spread change (raw bps) | Divide by rolling volatility, then negate for sign convention |

**Rationale**: This separation ensures:
- Indicators can be inspected in their natural units (basis points, ratios)
- Different signals can apply different normalizations to the same indicator
- Economic interpretation remains clear at the indicator level
- Trading standardization is explicit at the signal level

**Counter-Example** (What NOT to do):
- ❌ Indicator outputs z-scores directly → Loses economic interpretability
- ❌ Signal computes the ratio → Economic logic buried in signal definition

### Worked Example: cdx_vix_gap Decomposition

**Current Implementation** (everything in "signal"):
```
compute_cdx_vix_gap():
  1. Compute CDX deviation from 20-day mean
  2. Compute VIX deviation from 20-day mean  
  3. Take difference: cdx_deviation - vix_deviation
  4. Apply z-score normalization to the gap
  5. Return normalized signal
```

**Proposed Separation**:

**Indicator: `cdx_vix_deviation_gap_20d`**
- **Computes**: (CDX deviation from 20-day mean) - (VIX deviation from 20-day mean)
- **Output**: Raw gap in basis points (e.g., +15 bps, -8 bps)
- **Economic meaning**: "Credit stress is 15 bps higher than equity stress relative to their 20-day means"
- **Reusable**: Multiple signals can apply different normalizations to this gap

**Signal: `cdx_vix_gap`**  
- **Input**: `cdx_vix_deviation_gap_20d` indicator
- **Transformation**: Apply z-score normalization over 20-day window (from transformation catalog)
- **Output**: Standardized signal (e.g., +2.1 σ, -1.3 σ)
- **Trading meaning**: "Gap is 2.1 standard deviations above average → strong long credit signal"

**Alternative Signal: `cdx_vix_gap_percentile`**
- **Input**: Same `cdx_vix_deviation_gap_20d` indicator
- **Transformation**: Apply percentile rank over 60-day window (from transformation catalog)
- **Output**: Percentile rank (e.g., 85th percentile)
- **Trading meaning**: "Gap is at 85th percentile → strong but not extreme"

**Key Benefits**:
1. ✅ Indicator computed once, reused by both signals
2. ✅ Indicator value interpretable: "gap is +15 bps"
3. ✅ Easy to test different normalization approaches without changing indicator
4. ✅ Clear separation: indicator = economic metric, signal = trading standardization

## Design Decisions

### 1. Indicator Versioning: Breaking Changes Approach (Selected: Option B)

**Decision**: Indicator definition changes are treated as breaking changes that invalidate dependent workflow results (signals, backtests, performance analyses).

**Rationale**: 
- Simplifies system design by avoiding versioning overhead
- Aligns with research workflow expectations (code changes → re-run tests)
- Ensures all results use current indicator definitions
- Researchers can manually archive old workflow results before making changes

**Trade-offs**:
- ✅ Simpler implementation - no version management needed
- ✅ Always using latest indicator logic
- ❌ Cannot compare current vs historical indicator versions side-by-side
- ❌ Must re-run all dependent backtests when indicators change

### 2. Indicator Parameterization: Separate Definitions (Selected: Option B)

**Decision**: Each unique combination of indicator parameters is defined as a separate catalog entry (e.g., "momentum_5d" and "momentum_10d" are distinct indicators).

**Rationale**:
- Makes catalog explicit - all used indicator configurations visible
- Simplifies caching - no parameter hashing needed in cache keys
- Reduces complexity in dependency tracking
- Researchers can see exactly which parameter combinations are being used

**Trade-offs**:
- ✅ Simpler implementation - each indicator is immutable
- ✅ Explicit catalog of all configurations
- ✅ Straightforward cache invalidation
- ❌ May lead to catalog growth with many similar indicators
- ❌ Requires creating new catalog entry to test different parameters

### 3. Transformation Catalog: Separate Registry (Selected: Option A)

**Decision**: Create a separate transformation catalog for reusable signal transformation operations (z-score normalization, volatility adjustment, threshold filters, etc.).

**Rationale**:
- Transformations like z-score are used across many signals
- Cataloging makes transformations discoverable and consistent
- Enables validation and testing of transformation logic independently
- Supports governance requirement for auditable signal construction

**Trade-offs**:
- ✅ Transformations are discoverable and reusable
- ✅ Consistent implementation across signals
- ✅ Testable transformation logic
- ❌ Additional catalog to maintain
- ❌ More abstraction layers in signal construction
