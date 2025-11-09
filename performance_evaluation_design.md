# Performance Evaluation Design — aponyx

## Objective

Implement the second-stage evaluation feature: **performance analysis of backtest results**. This stage interprets simulation outputs into structured analytical insights. It sits between backtesting and visualization, enabling consistent, extensible, and comparable performance interpretation.

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

### Configuration
A frozen configuration dataclass will define the evaluation scope and options, including minimum observation count, number of subperiods, risk-free rate, rolling window length, and report output format.

### Evaluation Result Container
A structured dataclass will store metrics, subperiod analyses, attribution results, stability assessments, interpretive summaries, and metadata such as timestamps and configuration details.

### Analyzer Module
This module orchestrates the performance analysis process. It loads one or more backtest results, computes extended metrics, assesses subperiod stability, interprets the findings, and registers results. Its output is a structured result suitable for further visualization or reporting.

### Registry Pattern
A JSON-based registry will track all evaluation runs, recording metadata such as signal, strategy, timestamps, and summary statistics. CRUD operations will allow for easy querying, versioning, and retrieval of evaluation results.

### Decomposition and Attribution
Return attribution will initially be basic—separating contributions by trade direction or signal strength buckets. A protocol interface will define the contract for decomposition so more advanced attribution engines can be added later.

### Reporting
Reports will summarize key metrics, stability, and recommendations. Markdown will be the default format for readability, with optional JSON or HTML formats added later. Reports will emphasize interpretability and reproducibility.

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

## MVP Scope

### Must-haves
- Single-signal evaluation of backtest results
- Extended performance metrics (risk-adjusted returns, drawdown, stability)
- Subperiod stability analysis
- Markdown report generation
- Registry-based metadata tracking

### Should-haves
- Comparative evaluation across strategies or signals
- Basic attribution by trade type or signal quantile
- Optional adapters for external analytics libraries
- Rolling performance diagnostics for time-based robustness

### Nice-to-haves
- Multi-strategy or portfolio-level aggregation
- Advanced attribution by risk source or regime
- Streamlit dashboard integration for interactive review

---

## Directory Layout

```
src/aponyx/evaluation/
├── suitability/             # Pre-backtest evaluation
└── performance/             # Post-backtest analysis
    ├── analyzer.py          # Core orchestration
    ├── decomposition.py     # Attribution logic
    ├── risk_metrics.py      # Extended metric computations
    ├── report.py            # Markdown/JSON summaries
    ├── registry.py          # Metadata catalog
    ├── config.py            # Configuration dataclasses
    └── adapters.py          # Third-party integration stubs
```

---

## Data Flow

```
BacktestResult(s)
   ↓
PerformanceAnalyzer(config)
   ↓
PerformanceEvaluationResult
   ↓
Report + Registry Entry
   ↓
Visualization Layer (optional)
```

---

## Future Extensibility

- **Adapters:** Optional plugin interfaces for third-party analytics libraries.
- **Metrics registry:** Dynamically register new performance metrics without changing core logic.
- **Comparison engine:** Evaluate relative performance across strategies or signals.
- **Dashboard integration:** Connect with Streamlit for interactive result exploration.
- **Portfolio extensions:** Aggregate results for multi-strategy analysis.

---

## Design Intent

This design preserves the modular, layered philosophy of the existing system. It introduces a standardized framework for interpreting backtest outputs, leaving room for scalability in analytics, visualization, and external integrations.

