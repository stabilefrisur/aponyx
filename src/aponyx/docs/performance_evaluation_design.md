# Performance Evaluation Design — aponyx

**Status:** ✅ **IMPLEMENTED** (November 9, 2025)

## Objective

The second-stage evaluation feature provides **comprehensive performance analysis of backtest results**. This stage interprets simulation outputs into structured analytical insights. It sits between backtesting and visualization, enabling consistent, extensible, and comparable performance interpretation.

---

## Implementation Status

### ✅ Completed (November 9, 2025)

**Core modules:**
- ✅ `analyzer.py` - Performance orchestration and evaluation
- ✅ `decomposition.py` - Return attribution (directional, signal strength, win/loss)
- ✅ `risk_metrics.py` - Extended metrics (stability, profit factor, tail ratio, consistency)
- ✅ `registry.py` - JSON-based metadata catalog with CRUD operations
- ✅ `report.py` - Markdown report generation with comprehensive formatting
- ✅ `config.py` - PerformanceConfig dataclass with validation

**Key features:**
- Extended performance metrics beyond basic Sharpe/drawdown
- Rolling Sharpe analysis with configurable windows
- Subperiod stability assessment (quarterly by default)
- Return attribution by direction, signal strength, and win/loss
- Comprehensive markdown reports
- Registry-based metadata tracking
- Integration with backtest layer via BacktestResult objects

**Notebook:**
- ✅ `05_performance_analysis.ipynb` - Complete workflow notebook (13 cells)
  - Loads backtest results from Step 4
  - Reconstructs BacktestResult objects
  - Runs comprehensive performance analysis
  - Displays extended metrics tables
  - Visualizes rolling Sharpe and attribution
  - Generates reports for all signal-strategy pairs
  - Registers evaluations in PerformanceRegistry

**Testing:**
- ✅ Unit tests in `tests/evaluation/performance/`
- ✅ Registry integration tests
- ✅ Attribution decomposition tests
- ✅ Report generation tests

---

## Conceptual Placement

The feature will be implemented under a new subpackage:

```
src/aponyx/evaluation/performance/
```

This aligns with the project’s layered architecture, keeping the evaluation domain consistent:
- `evaluation.suitability` → pre-backtest screening
- `evaluation.performance` → post-backtest analysis

---

## Core Responsibilities

| Module | Purpose |
|--------|----------|
| `analyzer.py` | Orchestrates performance evaluation for one or more backtests |
| `decomposition.py` | Provides return attribution by signal component, trade side, or regime |
| `risk_metrics.py` | Computes advanced risk and stability metrics beyond base statistics |
| `registry.py` | Manages metadata catalog of evaluation runs (JSON-based) |
| `report.py` | Generates summary reports (Markdown or JSON) |
| `config.py` | Defines configuration dataclasses and evaluation parameters |

This mirrors the structure of the existing suitability evaluation package for consistency.

---

## Architectural Integration

**Inputs:**
- One or more `BacktestResult` objects from the backtest layer
- Optional contextual metadata such as signal name, strategy ID, and market regime labels

**Outputs:**
- Structured `PerformanceEvaluationResult` data container
- Optional Markdown or JSON report
- Registered entry in a `PerformanceRegistry` catalog for traceability

**Dependencies:**
- Imports allowed from `aponyx.backtest` and `aponyx.persistence`
- Must not import from `data`, `models`, or `visualization`

---

## Core Components

### Configuration ✅
A frozen `PerformanceConfig` dataclass defines the evaluation scope including minimum observations, subperiods, risk-free rate, rolling window, and attribution quantiles.

### Evaluation Result Container ✅
The `PerformanceResult` dataclass stores:
- Extended metrics (stability, profit factor, tail ratio, rolling Sharpe stats)
- Attribution results (directional, signal strength, win/loss decomposition)
- Subperiod stability scores
- Comprehensive metadata (timestamps, configuration, signal/strategy IDs)

### Analyzer Module ✅
The `analyze_backtest_performance` function orchestrates:
- Loading BacktestResult objects
- Computing extended metrics via risk_metrics module
- Assessing temporal stability across subperiods
- Running attribution decomposition
- Returning structured PerformanceResult

### Registry Pattern ✅
The `PerformanceRegistry` class provides:
- JSON-based catalog of evaluation runs
- CRUD operations: register, get, list (with filters)
- Metadata tracking (signal, strategy, timestamps, stability scores)
- Report path management

### Decomposition and Attribution ✅
The `decomposition.py` module computes:
- **Directional attribution:** Long vs short P&L contribution
- **Signal strength attribution:** Quantile-based decomposition (terciles by default)
- **Win/loss decomposition:** Positive vs negative day breakdown

### Reporting ✅
The `report.py` module generates:
- Comprehensive markdown reports with metrics tables
- Attribution breakdowns with visual formatting
- Stability analysis and interpretation
- Timestamped file persistence in `data/workflows/{signal}_{strategy}_{timestamp}/reports/`

---

## Modular Design Principles

| Design Choice | Rationale |
|----------------|------------|
| Protocol-based interfaces | Allow integration with third-party analytics libraries such as QuantStats or vectorbt without code rewrites |
| Functional orchestration with data containers | Simplify testing, serialization, and reproducibility |
| Registry pattern | Maintain consistent governance across evaluation layers |
| Separation of computation and interpretation | Enable flexible decision logic and visualization reuse |
| Optional external adapters | Support gradual integration of external toolkits |

---

## Implementation Status Summary

### ✅ Must-haves (Completed)
- ✅ Single-signal evaluation of backtest results
- ✅ Extended performance metrics (stability, profit factor, tail ratio, rolling Sharpe)
- ✅ Subperiod stability analysis (quarterly by default)
- ✅ Markdown report generation
- ✅ Registry-based metadata tracking

### ✅ Should-haves (Completed)
- ✅ Comparative evaluation across strategies or signals
- ✅ Basic attribution by trade direction and signal quantile
- ✅ Rolling performance diagnostics (rolling Sharpe analysis)

### 🔄 Nice-to-haves (Future Work)
- ⏳ Optional adapters for external analytics libraries (QuantStats, vectorbt)
- ⏳ Multi-strategy or portfolio-level aggregation
- ⏳ Advanced attribution by risk source or regime
- ⏳ Streamlit dashboard integration for interactive review

---

## Directory Layout (Implemented)

```
src/aponyx/evaluation/
├── suitability/             # Pre-backtest evaluation
└── performance/             # Post-backtest analysis ✅
    ├── __init__.py          # Exports: analyze_backtest_performance, PerformanceRegistry, etc.
    ├── analyzer.py          # Core orchestration ✅
    ├── decomposition.py     # Attribution logic ✅
    ├── risk_metrics.py      # Extended metric computations ✅
    ├── report.py            # Markdown summaries ✅
    ├── registry.py          # Metadata catalog ✅
    └── config.py            # Configuration dataclasses ✅

data/.registries/
└── performance.json         # Evaluation tracking (runtime) ✅
```

**Tests:**
```
tests/evaluation/performance/
├── test_analyzer.py         # Core evaluation tests ✅
├── test_decomposition.py    # Attribution tests ✅
├── test_risk_metrics.py     # Extended metrics tests ✅
├── test_report.py           # Report generation tests ✅
└── test_registry.py         # Registry CRUD tests ✅
```

---

## Data Flow (Implemented)

```
BacktestResult(s) from backtest execution
   ↓
PerformanceConfig (min_obs=252, n_subperiods=4, rolling_window=63)
   ↓
analyze_backtest_performance(backtest_result, config)
   ├─ compute_extended_metrics() → stability, profit factor, tail ratio
   ├─ compute_rolling_sharpe() → mean/std of rolling window
   ├─ compute_attribution() → directional, signal strength, win/loss
   └─ assess_subperiod_stability() → quarterly stability scores
   ↓
PerformanceResult (extended metrics + attribution + metadata)
   ↓
generate_performance_report() → Markdown file
   ↓
PerformanceRegistry.register_evaluation() → JSON catalog entry
   ↓
Visualization Layer (optional)
```

**Workflow integration:**
```
Step 1: Data Download
Step 2: Signal Computation
Step 3: Suitability Evaluation
Step 4: Backtest Execution
Step 5: Performance Analysis ← NEW
```

---

## Key Metrics Implemented

### Extended Performance Metrics
- **Stability Score:** Temporal consistency across subperiods (0-1 scale)
- **Profit Factor:** Gross wins / gross losses
- **Tail Ratio:** 95th percentile / 5th percentile return
- **Rolling Sharpe:** Mean and standard deviation of rolling window Sharpe ratios
- **Consistency Score:** Percentage of positive subperiods
- **Recovery Statistics:** Average days to recover from drawdowns, drawdown count

### Attribution Components
- **Directional:** Long vs short P&L contribution and percentages
- **Signal Strength:** Tercile-based decomposition (weak/medium/strong)
- **Win/Loss:** Positive vs negative day breakdown with contribution percentages

---

## Future Extensibility (Unchanged)

- **Adapters:** Optional plugin interfaces for third-party analytics libraries.
- **Metrics registry:** Dynamically register new performance metrics without changing core logic.
- **Comparison engine:** Evaluate relative performance across strategies or signals.
- **Dashboard integration:** Connect with Streamlit for interactive result exploration.
- **Portfolio extensions:** Aggregate results for multi-strategy analysis.

---

## Design Intent

This design preserves the modular, layered philosophy of the existing system. It introduces a standardized framework for interpreting backtest outputs, leaving room for scalability in analytics, visualization, and external integrations.

