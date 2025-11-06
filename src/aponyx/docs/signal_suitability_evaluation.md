# Signal-Product Suitability Evaluation Module

**Status:** ✅ Implemented  
**Location:** `src/aponyx/evaluation/suitability/`  
**Last Updated:** November 6, 2025

## Purpose
Evaluate whether a signal contains economically and statistically meaningful information for a specific traded product. Acts as a **research screening gate** that precedes strategy design and backtesting.

This framework is **fully implemented** and includes comprehensive test coverage, working examples, and integration with the models and backtest layers.

## Conceptual Position in Research Workflow

| Evaluation Type                | Core Question                                                                    | Typical Inputs                                        | Nature of Evidence                                         | Decision Output                                |
| ------------------------------ | -------------------------------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| **Signal–product suitability** | *Is this signal economically and statistically relevant for the traded product?* | Raw time series (signal, target), controls, lags      | Predictive correlation, incremental R², economic rationale | *Should we even backtest this signal?*         |
| **Backtest effectiveness**     | *If we trade on this signal, do we make money under realistic conditions?*       | Trading rules, position sizing, execution assumptions | Risk-adjusted return, turnover, OOS robustness             | *Should we allocate capital to this strategy?* |

**Key Distinction:** Suitability evaluation is **pre-strategy** — it assesses data relationships before any trading rules are defined.

## Scope
- Operates **before** strategy design and backtesting
- Evaluates **signal-target relationships** without trading rules, costs, or position sizing
- Produces structured, reproducible **evaluation report** and **registry entry**
- Supports governance: versioning, auditability, and linkage to subsequent backtests
- Prevents wasted effort on signals with no predictive content

---

## Architecture Overview

### Layer Positioning

The evaluation module sits between **models** and **backtest** layers:

```
data/          → Load and clean market data
models/        → Generate signals from market data
evaluation/    → Assess signal–product relationships ← NEW LAYER
backtest/      → Execute trading strategies with costs and sizing
visualization/ → Display results
```

**Rationale:** Suitability evaluation is neither signal generation nor strategy execution — it's a distinct analytical step that determines research workflow branching.

### Module Structure

```
aponyx/
  evaluation/
    __init__.py
    suitability/
      __init__.py           # Public API exports
      config.py             # Configuration dataclass
      evaluator.py          # Core evaluation orchestration
      tests.py              # Statistical test functions
      scoring.py            # Component scoring logic
      report.py             # Report generation
      registry.py           # Evaluation tracking
```

### Design Principles

1. **Functional Core:** Evaluation logic uses pure functions (signal, target → metrics)
2. **Dataclass Configuration:** Immutable `@dataclass(frozen=True)` for all config and results
3. **Registry for Governance:** Class-based registry following DataRegistry pattern for CRUD operations
4. **Separation of Concerns:** Statistical tests, scoring, and reporting are separate modules
5. **Type Safety:** Modern Python type hints throughout (`dict[str, Any]`, `list[int]`)
6. **Reproducibility:** All evaluations logged with timestamps, parameters, and version info

---

## Core Interfaces

### Input Contract

| Input | Type | Description |
|-------|------|-------------|
| `signal` | `pd.Series` | Signal time series with DatetimeIndex and `.name` attribute |
| `target_change` | `pd.Series` | Forward-looking target changes with DatetimeIndex |
| `config` | `SuitabilityConfig` | Evaluation parameters (immutable dataclass) |

**Critical:** No trading rules, costs, or position sizing in inputs.

### Output Contract

| Output | Type | Description |
|--------|------|-------------|
| `SuitabilityResult` | `@dataclass(frozen=True)` | Structured metrics and decision |
| `report` | `str` (Markdown) | Human-readable analysis document |
| `registry_entry` | `EvaluationEntry` | Governance record for audit trail |

### Configuration Schema

**SuitabilityConfig** — Immutable evaluation parameters:
- `lags: list[int]` — Forecast horizons to test (e.g., [1, 3, 5] days)
- `min_obs: int` — Minimum observations required (default: 500)
- `pass_threshold: float` — Score threshold for PASS (default: 0.7)
- `hold_threshold: float` — Score threshold for HOLD (default: 0.4)
- `data_health_weight: float` — Component weight (default: 0.2)
- `predictive_weight: float` — Component weight (default: 0.4)
- `economic_weight: float` — Component weight (default: 0.2)
- `stability_weight: float` — Component weight (default: 0.2)

**Validation:** Weights must sum to 1.0, thresholds ordered 0 < HOLD < PASS < 1.

### Result Schema

**SuitabilityResult** — Comprehensive evaluation metrics:
- **Component Scores** (0-1 scale):
  - `data_health_score`
  - `predictive_score`
  - `economic_score`
  - `stability_score`
- **Composite:** `composite_score` (weighted average)
- **Decision:** `Literal["PASS", "HOLD", "FAIL"]`
- **Diagnostics:**
  - `n_obs: int` — Valid observations
  - `missing_pct: float` — Missing data percentage
  - `lags_tested: list[int]` — Horizons evaluated
  - `correlations: dict[int, float]` — Lag → correlation
  - `betas: dict[int, float]` — Lag → regression coefficient
  - `tstats: dict[int, float]` — Lag → t-statistic
  - `effect_bps: float` — Economic impact estimate
  - `stability_test_passed: bool` — Temporal consistency flag

---

## Evaluation Methodology

### Four-Component Framework

Each component produces a score on [0, 1] scale, combined via weighted average.

#### 1. Data Health Score (Weight: 0.2)

**Purpose:** Assess data quality and sufficiency for reliable inference.

**Metrics:**
- Valid observations after alignment
- Missing data percentage
- Sample size relative to minimum threshold

**Scoring Logic:**
- If `n_obs < min_obs`: score = 0.0 (insufficient data)
- Else: penalize missing data, capping tolerance at ~20%
- Formula: `max(0, 1 - missing_rate / 0.2)`

**Interpretation:**
- 0.8–1.0: Excellent data quality
- 0.5–0.8: Acceptable with caveats
- <0.5: Data concerns may undermine results

---

#### 2. Predictive Association Score (Weight: 0.4)

**Purpose:** Measure statistical relationship between signal and target.

**Methodology:**
- For each lag horizon:
  - Compute Pearson correlation: `corr(signal[t], target_change[t+lag])`
  - Run OLS regression: `target_change[t+lag] ~ signal[t]`
  - Extract beta coefficient and t-statistic
- Aggregate: mean absolute t-statistic across lags

**Scoring Logic:**
- Convert mean |t-stat| to [0, 1] scale
- Cap at t-stat = 3.0 → score 1.0
- Formula: `min(1.0, mean_abs_tstat / 3.0)`

**Interpretation:**
- t-stat > 2.0: Statistically significant at conventional levels
- t-stat > 3.0: Strong evidence of predictive power
- t-stat < 1.5: Weak or noisy relationship

**Note:** This measures *correlation*, not causation. Economic interpretation required.

---

#### 3. Economic Relevance Score (Weight: 0.2)

**Purpose:** Estimate practical economic impact of signal.

**Methodology:**
- Compute effect size: bps change in target per 1σ signal change
- Based on average beta across lags
- Formula: `effect_bps = |avg_beta × signal_std|`

**Scoring Thresholds:**
- < 0.5 bps: Negligible → score 0.2
- 0.5–2.0 bps: Moderate → score 0.6
- > 2.0 bps: Meaningful → score 1.0

**Interpretation:**
- For CDX spreads: 2 bps move is ~0.4% spread change (economically relevant)
- Context-dependent: thresholds may need calibration per product type

**Note:** Effect size ≠ profitability (no costs, no execution considered).

---

#### 4. Stability Score (Weight: 0.2)

**Purpose:** Test temporal consistency of predictive relationship.

**Methodology:**
- Split sample chronologically into two halves
- For each lag, compute beta in each subperiod
- Check sign consistency: `sign(beta_half1) == sign(beta_half2)`
- All lags must maintain consistent sign

**Scoring Logic:**
- All lags consistent → score 1.0
- Any lag inconsistent → score 0.0 (binary test)

**Interpretation:**
- Pass: Relationship is stable across regimes (confidence booster)
- Fail: Relationship reversed or unstable (red flag for regime changes)

**Limitations:** 
- Binary test is conservative (no partial credit)
- Two-way split may miss finer regime structure
- Future: consider rolling window stability

---

### Composite Scoring

**Formula:**
```
composite = 0.2 × data_health 
          + 0.4 × predictive 
          + 0.2 × economic 
          + 0.2 × stability
```

**Decision Thresholds:**
- `composite ≥ 0.7` → **PASS** (proceed to backtest)
- `0.4 ≤ composite < 0.7` → **HOLD** (marginal, requires judgment)
- `composite < 0.4` → **FAIL** (do not backtest)

**Rationale for Weights:**
- Predictive association (40%) is primary criterion
- Data health (20%) gates reliability
- Economic relevance (20%) ensures practical significance
- Stability (20%) tests robustness

**Customization:** Weights configurable via `SuitabilityConfig`.

---

## Governance & Registry Design

### Registry Pattern

**Pattern:** Class-based registry with CRUD operations (follows DataRegistry pattern)

**Purpose:**
- Track which signal-product pairs have been evaluated
- Prevent redundant evaluation work
- Create audit trail for research decisions
- Enable linkage to subsequent backtests via `eval_id`

### Registry Schema

**EvaluationEntry** — Immutable record structure:
- `eval_id: str` — Unique identifier (ISO timestamp + signal + product)
- `signal_id: str` — Signal name from Series.name
- `product_id: str` — Product identifier (user-provided)
- `evaluation_date: str` — ISO timestamp of evaluation
- `metrics: dict[str, float]` — Component and composite scores
- `decision: Literal["PASS", "HOLD", "FAIL"]` — Outcome
- `report_path: str` — Path to Markdown report
- `n_obs: int` — Valid observations count
- `composite_score: float` — Final score

### Registry Operations

**SuitabilityRegistry** supports:
1. `register_evaluation()` — Add new evaluation, auto-save, return eval_id
2. `get_evaluation(eval_id)` — Retrieve by ID
3. `list_evaluations(filters)` — Query with optional filters (signal, product, decision)
4. Internal `_load()` and `_save()` for JSON persistence

### Storage Location

**Path:** `src/aponyx/evaluation/suitability/registry.json`

**Rationale:** Keep evaluation layer self-contained and separated from data layer.

**Format:** Dictionary mapping eval_id → EvaluationEntry dict

**Relationship to other registries:**
- **DataRegistry:** `data/registry.json` — Tracks datasets (raw market data files)
- **SignalRegistry:** `src/aponyx/models/signal_catalog.json` — Catalog of available signal computations
- **StrategyRegistry:** `src/aponyx/backtest/strategy_catalog.json` — Catalog of backtest strategies
- **SuitabilityRegistry:** `src/aponyx/evaluation/suitability/registry.json` — Evaluation results ← NEW

**Note:** Each layer manages its own registry/catalog files within its module structure.

### Config Integration

Add to `aponyx/config/__init__.py`:
```python
# Evaluation layer
SUITABILITY_REGISTRY_PATH: Final[Path] = PROJECT_ROOT / "src/aponyx/evaluation/suitability/registry.json"
```

---

## Report Design

### Report Purpose

Human-readable Markdown document for:
- Reviewing evaluation logic and metrics
- Understanding why decision was made
- Archiving research rationale
- Communicating results to stakeholders

### Report Structure

**Header Section:**
- Signal and product identifiers
- Evaluation timestamp
- Evaluator version
- Overall decision and score

**Executive Summary:**
- Decision with visual indicator (✅ PASS / ⚠️ HOLD / ❌ FAIL)
- Composite score
- Brief interpretation (1-2 sentences)

**Component Sections (4):**

Each component gets dedicated section with:
- **Metrics table:** Raw statistics
- **Score:** Component score on 0-1 scale
- **Interpretation:** What the score means in context

1. **Data Health**
   - Valid observations
   - Missing data percentage
   - Health score

2. **Predictive Association**
   - Correlation, beta, t-stat for each lag
   - Mean |t-stat| aggregation
   - Predictive score
   - Statistical significance interpretation

3. **Economic Relevance**
   - Effect size (bps per 1σ signal)
   - Economic score
   - Practical significance interpretation

4. **Temporal Stability**
   - Subperiod beta sign comparison
   - Stability score
   - Consistency status (pass/fail)

**Composite Scoring Table:**
- Component weights
- Component scores
- Weighted contributions
- Total composite score

**Decision Section:**
- Threshold definitions (PASS/HOLD/FAIL)
- Final decision
- Recommended next steps based on outcome

**Footer:**
- Auto-generation timestamp
- Evaluator version
- Reproducibility note

### Report Generation

**Function:** `generate_suitability_report(result, signal_id, product_id, output_path)`

**Inputs:**
- `SuitabilityResult` dataclass
- Signal and product identifiers
- Optional output path for file save

**Output:**
- Markdown string (always)
- File saved to `reports/suitability/` if path provided

**Template Approach:**
- Use f-string template or jinja2 for consistency
- Dynamic interpretation text based on score ranges
- Visual indicators: ✅ (PASS), ⚠️ (HOLD), ❌ (FAIL)

### Report Persistence

**Storage:** `reports/suitability/{signal_id}_{product_id}_{date}.md`

**Linkage:** Report path stored in registry entry for retrieval

---

## Integration Points

### With Existing Layers

**Data Layer:**
- Input: Uses cleaned time series from `data/` loaders
- No modifications to data layer required

**Models Layer:**
- Input: Receives computed signals from `models/signals.py`
- Evaluation happens after signal computation, before strategy design

**Backtest Layer:**
- Linkage: Backtest results can reference `eval_id` from suitability evaluation
- Decision gate: FAIL evaluations prevent backtest execution
- Separate concerns: Suitability (is signal predictive?) vs Backtest (is strategy profitable?)

**Config Layer:**
- Add `SUITABILITY_REGISTRY_PATH` constant
- No other config changes needed

**Persistence Layer:**
- Uses existing `json_io` utilities for registry and reports
- Report storage in `reports/suitability/` directory

### Workflow Position

```
[Data Loading] 
    ↓
[Signal Computation]
    ↓
[Suitability Evaluation] ← NEW STEP
    ├─ PASS → [Strategy Design] → [Backtest]
    ├─ HOLD → [Manual Review] → [Strategy Design or Archive]
    └─ FAIL → [Archive / Document Failure]
```

### API Surface

**Primary Entry Point:**
```python
evaluate_signal_suitability(
    signal: pd.Series,
    target_change: pd.Series,
    config: SuitabilityConfig,
) -> SuitabilityResult
```

**Supporting Functions:**
- `generate_suitability_report(result, signal_id, product_id, path) -> str`
- `SuitabilityRegistry.register_evaluation(...) -> str`
- `SuitabilityRegistry.list_evaluations(filters) -> list[EvaluationEntry]`

**Dataclasses:**
- `SuitabilityConfig` — Evaluation parameters
- `SuitabilityResult` — Evaluation output
- `EvaluationEntry` — Registry record

---

## Testing Strategy

### Unit Tests

**Test Coverage:**
1. **Config validation** — Invalid thresholds, weights, lags
2. **Data health** — Edge cases (empty, insufficient, high missing %)
3. **Predictive tests** — Known correlations, regression calculations
4. **Economic scoring** — Effect size thresholds
5. **Stability tests** — Sign consistency logic, split behavior
6. **Composite scoring** — Weight application, decision thresholds
7. **Registry CRUD** — Add, retrieve, filter operations
8. **Report generation** — Template rendering, file I/O

### Integration Tests

1. End-to-end evaluation with synthetic data (known relationships)
2. Registry persistence and reload
3. Report file creation and content validation

### Test Data

**Synthetic signals with known properties:**
- Perfect positive correlation (control)
- Perfect negative correlation (control)
- No correlation (should FAIL)
- Regime-changing correlation (should fail stability)
- High missing data (should fail data health)

---

## Future Enhancements (Out of Scope for MVP)

### Statistical Extensions
- Multiple regression with controls (e.g., control for market beta)
- Information coefficient (IC) analysis
- Quantile regression for tail behavior
- Rolling window stability (vs binary split)

### Economic Extensions
- Conditional effect sizes by regime
- Transaction cost sensitivity (preview)
- Capacity estimates

### Reporting Extensions
- Interactive HTML reports with Plotly charts
- Scatter plots (signal vs target by lag)
- Residual diagnostics
- Automated hypothesis generation

### Registry Extensions
- Version tracking for signal definitions
- Comparison across evaluations (signal evolution)
- Bulk re-evaluation on data updates

### Integration Extensions
- Automatic triggering from signal computation
- Slack/email notifications for PASS decisions
- Integration with research task tracker

---

## Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Create `evaluation/suitability/` module structure
- [ ] Implement `SuitabilityConfig` dataclass with validation
- [ ] Implement `SuitabilityResult` dataclass
- [ ] Add `SUITABILITY_REGISTRY_PATH` to config

### Phase 2: Evaluation Logic
- [ ] Implement data health calculation
- [ ] Implement predictive association tests
- [ ] Implement economic relevance scoring
- [ ] Implement stability tests
- [ ] Implement composite scoring and decision logic
- [ ] Integrate into main `evaluate_signal_suitability()` function

### Phase 3: Governance
- [ ] Implement `EvaluationEntry` dataclass
- [ ] Implement `SuitabilityRegistry` class
- [ ] Add unit tests for registry CRUD operations
- [ ] Create initial empty registry JSON file

### Phase 4: Reporting
- [ ] Design Markdown template
- [ ] Implement `generate_suitability_report()` function
- [ ] Add interpretation logic for score ranges
- [ ] Test report generation with sample data

### Phase 5: Testing & Documentation
- [ ] Unit tests for all evaluation components
- [ ] Integration test with end-to-end workflow
- [ ] Usage examples in `examples/suitability_demo.py`
- [ ] Update project README with new evaluation layer
- [ ] Document in `docs/signal_suitability_evaluation.md`

---

## Success Criteria

**MVP is successful if:**
1. ✅ Can evaluate signal-product pairs with <5 lines of user code
2. ✅ Produces interpretable, actionable reports
3. ✅ Decision flags correctly identify predictive vs non-predictive relationships
4. ✅ Registry tracks all evaluations for audit trail
5. ✅ Integrates cleanly with existing project architecture
6. ✅ All tests pass with >80% coverage
7. ✅ Documentation enables independent use by other researchers

---

**Maintained by:** stabilefrisur  
**Version:** 0.1 (Design Specification)  
**Last Updated:** November 4, 2025

