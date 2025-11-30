# Implementation Plan: Indicator-Signal Separation

**Branch**: `001-indicator-signal-separation` | **Date**: 2025-11-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-indicator-signal-separation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature separates the definition of **indicators** (economically meaningful market metrics) from **signals** (trading signals derived from indicator transformations). Currently, the project combines both into a single "signal" concept, mixing economic metric computation (spread ratios, momentum) with trading standardization (z-score normalization, thresholds).

The separation enables:
1. **Reusable indicators** - Define market metrics once, combine in multiple signals
2. **Rapid signal experimentation** - Test different normalizations/transformations without recomputing indicators
3. **Clear governance** - Indicators validated independently from trading logic
4. **Composability** - Signals constructed from multiple indicators via transformation catalog

**Technical Approach**: Introduce `indicator_catalog.json` (economically interpretable metrics) alongside existing `signal_catalog.json` (trading signals referencing indicators + transformations). Refactor existing signal functions into indicator computations + signal transformations. Add `transformation_catalog.json` for reusable standardization operations (z-score, volatility adjustment).

## Technical Context

**Language/Version**: Python 3.12 (strict requirement, modern syntax only)
**Primary Dependencies**: Pandas 2.0+, NumPy 1.24+, Click 8.1+, PyArrow 12.0+, Statsmodels 0.14+
**Storage**: Parquet for time series (pyarrow), JSON for catalogs (indicator, signal, transformation), runtime registries in data/.registries/
**Testing**: Pytest 8.0+ with 681 existing tests across all layers
**Target Platform**: Cross-platform Python (Windows/Linux/macOS)
**Project Type**: Single project (research framework library with CLI)
**Performance Goals**: 
  - Indicator caching reduces multi-signal computation time by 60%
  - Dependency queries complete in <1s for 50 indicators + 100 signals
  - Catalog validation fails within 2s on missing data requirements
**Constraints**:
  - Must maintain backward compatibility with existing 3 pilot signals (cdx_etf_basis, cdx_vix_gap, spread_momentum)
  - All outputs must be deterministic (same inputs = same outputs)
  - Layer boundaries enforced (models cannot import from backtest/evaluation/visualization)
  - Indicators must output economically interpretable units (bps, ratios, percentages)
**Scale/Scope**:
  - Currently: 3 signals, 4 strategies
  - Target: 50+ indicators, 100+ signals
  - Catalog-driven extensibility without code changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Post-Design Re-Evaluation (2025-11-30)**: ✅ CONFIRMED - All gates remain PASS after Phase 1 design completion.

### I. Modularity & Layer Separation ✅ PASS

**Evaluation**: Feature maintains strict layer boundaries.
- Indicators will live in `models/` layer (existing location for signal computations)
- Indicator registry follows existing SignalRegistry pattern (models-only dependencies)
- No new cross-layer imports introduced
- Transformation catalog reuses existing `data/transforms.py` (already in data layer, models can import)

**Gate**: PASS - No layer boundary violations

---

### II. Reproducibility & Determinism ✅ PASS

**Evaluation**: Feature enhances reproducibility.
- Indicator caching keyed by (name, parameters, input_data_hash) ensures deterministic retrieval
- Catalog versioning via git provides audit trail
- Indicator definition changes invalidate dependent workflow results (explicit invalidation)
- All computations remain pure functions with fixed parameters

**Gate**: PASS - Strengthens determinism guarantees

---

### III. Type Safety & Modern Python ✅ PASS

**Evaluation**: Feature follows type safety requirements.
- All new catalogs use frozen dataclasses with `__post_init__` validation
- Modern type hints (`dict[str, Any]`, `str | None`) required
- MyPy validation continues in CI
- Existing pattern already demonstrated in SignalRegistry/StrategyRegistry

**Gate**: PASS - Consistent with existing type safety standards

---

### IV. Functions Over Classes ✅ PASS

**Evaluation**: Feature prioritizes functions.
- Indicator computations remain pure functions (like current signals)
- Registries use classes for state management (catalog loading, validation) - justified use case
- Transformations remain pure functions (existing `apply_transform` pattern)
- No new unnecessary classes introduced

**Gate**: PASS - Appropriate use of functions vs classes

---

### V. Registry Pattern for Extensibility ✅ PASS

**Evaluation**: Feature extends existing registry pattern.
- Creates IndicatorRegistry following SignalRegistry pattern
- Creates TransformationRegistry following same pattern
- Fail-fast validation on catalog load
- Frozen dataclass metadata with validation
- JSON-based catalog editing

**Gate**: PASS - Consistent with governance model

---

### VI. Signal Sign Convention ✅ PASS

**Evaluation**: Feature preserves sign convention.
- Indicators compute raw metrics (no sign convention at indicator level)
- Signals apply transformations that preserve sign convention
- Separation makes sign convention explicit in signal layer
- Easier to audit sign correctness when separated from indicator logic

**Gate**: PASS - Clarifies sign convention enforcement

---

### VII. Logging Discipline ✅ PASS

**Evaluation**: Feature follows logging standards.
- Module-level loggers only
- No logging configuration in library code
- INFO for user-facing operations (indicator cached, signal computed)
- DEBUG for implementation details (cache key computation, dependency resolution)

**Gate**: PASS - Consistent with logging requirements

---

### Summary

**Overall Gate Status**: ✅ PASS

All constitution principles satisfied. Feature extends existing patterns (registry, frozen dataclasses, pure functions) without introducing violations. The separation actually strengthens modularity and reproducibility by making the indicator-signal boundary explicit.

## Project Structure

### Documentation (this feature)

```text
specs/001-indicator-signal-separation/
├── spec.md              # Feature specification (user input)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (research decisions)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (developer guide)
└── contracts/           # Phase 1 output (API schemas)
    ├── indicator_catalog_schema.json
    ├── transformation_catalog_schema.json
    └── updated_signal_catalog_schema.json
```

### Source Code (repository root)

```text
src/aponyx/
├── models/
│   ├── signals.py              # MODIFY: Refactor into indicators + signal transformations
│   ├── indicators.py           # NEW: Indicator computation functions
│   ├── signal_composer.py      # NEW: Signal construction from indicators + transformations
│   ├── registry.py             # MODIFY: Add IndicatorRegistry, TransformationRegistry
│   ├── metadata.py             # MODIFY: Add IndicatorMetadata, TransformationMetadata
│   ├── config.py               # MODIFY: Add IndicatorConfig, TransformationConfig
│   ├── orchestrator.py         # MODIFY: Update to compute indicators then signals
│   ├── signal_catalog.json     # MODIFY: Add indicator_dependencies field
│   ├── indicator_catalog.json  # NEW: Indicator definitions
│   └── transformation_catalog.json  # NEW: Transformation definitions
├── data/
│   ├── transforms.py           # EXISTING: Already has z_score, normalized_change, etc.
│   └── ...
├── persistence/
│   ├── parquet_io.py           # MODIFY: Add indicator cache I/O helpers
│   └── ...
└── config/
    └── __init__.py             # MODIFY: Add INDICATOR_CATALOG_PATH, TRANSFORMATION_CATALOG_PATH

data/
├── cache/
│   ├── indicators/             # NEW: Indicator cache directory
│   │   └── {indicator_name}_{params_hash}_{data_hash}.parquet
│   └── ...
└── .registries/
    ├── indicators.json         # NEW: IndicatorRegistry runtime metadata
    ├── transformations.json    # NEW: TransformationRegistry runtime metadata
    └── ...

tests/
├── models/
│   ├── test_indicators.py      # NEW: Indicator computation tests
│   ├── test_signal_composer.py # NEW: Signal composition tests
│   ├── test_indicator_registry.py  # NEW: IndicatorRegistry tests
│   ├── test_transformation_registry.py  # NEW: TransformationRegistry tests
│   ├── test_signals.py         # MODIFY: Update to test refactored signals
│   └── ...
└── ...
```

**Structure Decision**: Single project structure (existing). All indicator/signal separation happens within `src/aponyx/models/` layer. New indicator and transformation catalogs follow existing signal catalog pattern (JSON in models directory). Cache separation via `data/cache/indicators/` subdirectory. Registries follow existing pattern in `data/.registries/`.

## Complexity Tracking

> **No violations to track - Constitution Check passed all gates.**

This feature extends existing patterns (registry pattern, frozen dataclasses, pure functions) without introducing complexity violations. The separation of indicators and signals actually reduces complexity by clarifying boundaries and enabling independent testing.

---

## Phase 2: Next Steps

**Command Ends Here** - This is the output of `/speckit.plan`. 

**What Was Generated**:
- ✅ Technical Context filled
- ✅ Constitution Check evaluated (all gates PASS)
- ✅ Project Structure documented
- ✅ Phase 0 Research completed ([research.md](./research.md))
- ✅ Phase 1 Data Model defined ([data-model.md](./data-model.md))
- ✅ Phase 1 API Contracts created ([contracts/](./contracts/))
- ✅ Phase 1 Developer Guide written ([quickstart.md](./quickstart.md))
- ✅ Agent context updated (copilot-instructions.md)

**For Implementation**:
1. Run `/speckit.tasks` to generate task breakdown from this plan
2. Execute tasks in dependency order
3. Validate with tests and type checking
4. Update documentation if adding new public APIs

**Key Artifacts**:
- **Branch**: `001-indicator-signal-separation`
- **Plan**: `specs/001-indicator-signal-separation/plan.md` (this file)
- **Research**: `specs/001-indicator-signal-separation/research.md`
- **Data Model**: `specs/001-indicator-signal-separation/data-model.md`
- **Contracts**: `specs/001-indicator-signal-separation/contracts/`
- **Quickstart**: `specs/001-indicator-signal-separation/quickstart.md`
