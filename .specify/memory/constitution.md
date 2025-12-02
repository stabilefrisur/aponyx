<!--
SYNC IMPACT REPORT
==================
Version Change: 1.0.0 → 1.1.0
Modified Principles: 
- Breaking Changes Policy → Elevated to Core Principle VIII "No Backward Compatibility"
- Technology Standards → Breaking Changes Policy section removed (now core principle)
Added Sections:
- Core Principle VIII: No Backward Compatibility (NON-NEGOTIABLE)
Removed Sections: None

Template Updates Required:
✅ plan-template.md - Verified alignment with backward compatibility stance
✅ spec-template.md - Verified alignment with backward compatibility stance
✅ tasks-template.md - Verified alignment with backward compatibility stance

Follow-up TODOs: None
-->

# Aponyx Constitution

## Core Principles

### I. Modularity & Layer Separation (NON-NEGOTIABLE)

**Clean architectural boundaries with strict dependency rules.**

All code MUST follow the layered architecture:
- **CLI** → workflows, reporting, config only
- **Workflows** → all layers except CLI
- **Data** → config, persistence only (no business logic dependencies)
- **Models** → config, data schemas only (no backtest, evaluation, visualization)
- **Evaluation** → config, backtest, persistence (no direct data access, no visualization)
- **Backtest** → config, models protocols only (no direct data access)
- **Visualization** → generic DataFrames only (no business logic dependencies)
- **Persistence** → config only
- **Config** → no dependencies

**Rationale**: Clean separation enables independent testing, prevents circular dependencies, and allows layer replacement without cascading changes. Each layer has a single responsibility and minimal coupling.

**Validation**: Import violations MUST be caught in code review. Use static analysis to detect cross-layer imports that violate dependency rules.

---

### II. Reproducibility & Determinism (NON-NEGOTIABLE)

**All research outputs must be reproducible with identical inputs producing identical outputs.**

Requirements:
- Fixed random seeds for all stochastic operations
- Deterministic execution order in all pipeline steps
- Complete metadata logging (timestamps, versions, parameters, data sources)
- Timestamped output directories with full provenance tracking
- No hidden state or external dependencies that affect results

**Rationale**: Research credibility depends on reproducibility. Investment decisions require auditable, repeatable analysis. Debugging requires deterministic behavior.

**Validation**: Re-running identical workflows MUST produce byte-identical outputs (excluding timestamps). All randomness MUST be seeded and documented.

---

### III. Type Safety & Modern Python (NON-NEGLIGIBLE)

**Strict type hints using Python 3.12 modern syntax exclusively.**

Requirements:
- All function signatures MUST include complete type hints
- Use PEP 604 union syntax (`str | None` not `Optional[str]`)
- Use built-in generics (`dict[str, Any]` not `Dict[str, Any]`)
- Frozen dataclasses for all configuration objects
- `py.typed` marker for library typing
- MyPy validation in CI pipeline

**Rationale**: Type safety catches errors at development time, improves IDE support, serves as self-documentation, and prevents entire classes of runtime errors.

**Validation**: MyPy MUST pass with no errors. Code review MUST reject old-style type hints or missing annotations on public APIs.

---

### IV. Functions Over Classes

**Default to pure functions; use classes only when they provide clear value.**

Use functions for:
- Simple transformations and computations
- Stateless data processing pipelines
- Signal generation logic
- Single-responsibility operations

Use classes only when you need:
- State management (registries, connection pools, caches)
- Multiple related methods operating on shared state
- Lifecycle management (setup/teardown, context managers)
- Plugin/interface patterns (strategy implementations)

**Rationale**: Pure functions are easier to test, reason about, compose, and parallelize. Classes introduce unnecessary complexity when state management isn't required.

**Validation**: Class introduction MUST be justified in code review. Default assumption is function-based implementation.

---

### V. Registry Pattern for Extensibility

**Centralized catalogs for signals, strategies, and datasets with fail-fast validation.**

All extensible components MUST use registry pattern:
- **SignalRegistry** - JSON catalog at `src/aponyx/models/signal_catalog.json` (static)
- **StrategyRegistry** - JSON catalog at `src/aponyx/backtest/strategy_catalog.json` (static)
- **DataRegistry** - Runtime JSON at `data/.registries/registry.json`
- **SuitabilityRegistry** - Runtime JSON at `data/.registries/suitability.json`
- **PerformanceRegistry** - Runtime JSON at `data/.registries/performance.json`

Requirements:
- Frozen dataclass metadata with `__post_init__` validation
- Fail-fast on catalog load (validate ALL entries upfront)
- Dynamic function/class resolution via registered names
- Enable/disable toggles for all registered items

**Rationale**: Registries enable adding new signals/strategies without code changes, provide single source of truth for available components, and enforce consistent metadata structure.

**Validation**: New extensible components MUST use registry pattern. Direct hardcoding of options is prohibited.

---

### VI. Signal Sign Convention (NON-NEGOTIABLE)

**All signals MUST follow consistent directional convention.**

Universal rule:
- **Positive signal values** → Long credit risk → Buy CDX (sell protection)
- **Negative signal values** → Short credit risk → Sell CDX (buy protection)

Requirements:
- All signal compute functions MUST document sign convention in docstring
- Use negation (`-`) when raw calculations naturally produce inverse signs
- Z-score normalization MUST preserve sign
- Test signal directionality with synthetic data

**Rationale**: Consistent sign convention prevents catastrophic position reversals, enables signal comparison, and simplifies position sizing logic.

**Validation**: All new signals MUST include sign convention tests. Code review MUST verify docstring documentation.

---

### VII. Logging Discipline

**Module-level loggers with appropriate level usage; NEVER configure logging in library code.**

Requirements:
- Always use `logger = logging.getLogger(__name__)`
- NEVER call `logging.basicConfig()` in library code
- Use lazy evaluation: `logger.info("Loaded %d rows", len(df))` not f-strings
- **INFO**: User-facing operations (file loaded, backtest started, signal generated)
- **DEBUG**: Implementation details (cache hits, filter details, iteration counts)
- **WARNING**: Recoverable issues (missing optional column, default value used)
- **ERROR**: Operation failures requiring attention

**Rationale**: Module-level loggers enable selective debugging. Lazy evaluation prevents performance overhead when logging disabled. Library code must not override user's logging configuration.

**Validation**: Code review MUST reject `logging.basicConfig()` in library code and f-strings in log messages.

---

### VIII. No Backward Compatibility (NON-NEGOTIABLE)

**Breaking changes are acceptable and encouraged. No deprecation warnings. No legacy support.**

This project is an active-development research framework that prioritizes velocity, code clarity, and architectural cleanliness over backward compatibility.

**Explicit Policy**:
- **NO deprecation warnings** - Remove old code immediately, don't warn about it
- **NO compatibility layers** - No fallback logic, no "legacy mode" switches
- **NO migration utilities** - Users re-run workflows after breaking changes
- **NO version pinning requirements** - Latest version may break existing code
- **Breaking changes MAY occur in ANY release** - Including PATCH versions

**When Making Breaking Changes**:
1. Remove old code completely (no conditional logic)
2. Update documentation to reflect only current patterns
3. Invalidate affected caches and workflow results
4. Document change briefly in CHANGELOG.md
5. Increment version per semantic versioning

**Version Semantics**:
- **MAJOR**: Large architectural changes or multiple breaking changes
- **MINOR**: New features (may include breaking changes to experimental features)
- **PATCH**: Bug fixes and small improvements (may include breaking changes to internal APIs)

**Rationale**: Research frameworks evolve rapidly. Maintaining backward compatibility in early development slows velocity, clutters codebase with conditional logic, confuses new developers with legacy patterns, and creates maintenance burden. Clean breaks enable faster iteration and clearer architecture. Users working with this codebase understand that re-running workflows after updates is normal and acceptable.

**Validation**: 
- Code review MUST reject deprecation warnings
- Code review MUST reject "legacy mode" or compatibility switches
- Code review MUST reject conditional logic that preserves old behavior
- Breaking changes MUST be documented but NOT announced with warnings in runtime

---

## Technology Standards

### Required Stack (NON-NEGOTIABLE)

- **Python**: 3.12 (strict requirement, modern syntax only, no legacy support)
- **Environment Manager**: `uv` (preferred)
- **Package Manager**: `uv` or `pip`
- **CLI Framework**: Click 8.1+
- **Type Checking**: MyPy 1.11+
- **Testing**: Pytest 8.0+
- **Data Analysis**: Pandas 2.0+, NumPy 1.24+, PyArrow 12.0+
- **Visualization**: Plotly 5.24+ (optional dependency)
- **Statistics**: Statsmodels 0.14+

### Code Quality Tools

All code MUST pass `uv run` checks:
- **Formatting**: `uv run ruff format` (line length: 100, Python 3.12 target)
- **Linting**: `uv run ruff check` (import sorting, code quality)
- **Type Checking**: `uv run mypy src/` (strict type checking)

**Rationale**: `uv` provides unified tooling with consistent environment management. Ruff replaces Black (faster, same output) while adding comprehensive linting.

---

## Development Workflow

### Feature Development Process

1. **Specification** - Create spec in `.specify/specs/[###-feature-name]/spec.md`
2. **Planning** - Generate plan with `/speckit.plan` command
3. **Task Breakdown** - Generate tasks with `/speckit.tasks` command
4. **Implementation** - Execute tasks in dependency order
5. **Validation** - Run tests, type checking, and linting
6. **Documentation** - Update only if creating new public APIs or changing behavior

### Test Requirements

- **681 tests** across all layers (current coverage baseline)
- Unit tests for all public functions
- Integration tests for workflow orchestration
- No test required for simple one-line changes
- Tests MUST be independently runnable

### Code Review Standards

All changes MUST verify:
- Constitution compliance (layer boundaries, type hints, logging)
- Test coverage for new functionality
- Documentation updates for public API changes
- No introduction of circular dependencies
- Appropriate use of classes vs functions

### Documentation Requirements

- **NumPy-style docstrings** for all public functions and classes
- Module-level docstrings explaining purpose and dependencies
- README updates for new user-facing features
- Design documents in `src/aponyx/docs/` for architectural changes

---

## Governance

### Authority & Enforcement

This Constitution supersedes all other development practices and guidelines. The Constitution defines non-negotiable principles that ensure project integrity, maintainability, and research credibility.

**Enforcement**:
- All code reviews MUST verify Constitution compliance
- Layer boundary violations MUST be rejected
- Type safety violations MUST be rejected
- Logging configuration in library code MUST be rejected
- Signal sign convention violations MUST be rejected
- Deprecation warnings MUST be rejected
- Backward compatibility code MUST be rejected

### Amendment Process

Constitution amendments require:
1. **Documentation** - Proposal with rationale in project issue
2. **Impact Analysis** - Review of affected code and templates
3. **Version Increment** - Semantic versioning based on change type:
   - **MAJOR**: Backward incompatible governance/principle removals or redefinitions
   - **MINOR**: New principle/section added or materially expanded guidance
   - **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements
4. **Template Updates** - Synchronize all `.specify/templates/` files
5. **Migration Plan** - Strategy for updating existing code (if needed)

### Compliance Review

Periodic compliance reviews MUST check:
- Layer dependency violations across entire codebase
- Type hint coverage on all public APIs
- Logging configuration presence in library code
- Registry pattern usage for all extensible components
- Signal sign convention consistency
- Absence of deprecation warnings or backward compatibility code

### Runtime Development Guidance

For coding patterns, conventions, and feature scaffolding examples, see `.github/copilot-instructions.md`. The copilot instructions provide implementation details while this Constitution defines non-negotiable architectural principles.

**Version**: 1.1.0 | **Ratified**: 2025-11-30 | **Last Amended**: 2025-12-01
