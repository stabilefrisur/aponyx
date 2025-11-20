# CLI Orchestrator Design Document

**Project:** Systematic Macro Credit Research Framework  
**Component:** Command-Line Interface (CLI) Orchestrator  
**Author:** stabilefrisur  
**Date:** November 20, 2025  
**Status:** Design Phase

---

## Executive Summary

This document describes the design of a command-line interface (CLI) that simplifies the systematic macro credit research workflow from **8 manual scripts** into **declarative single-command execution**. The CLI enables quantitative researchers to run complete research pipelines (data → signal → evaluation → backtest → visualization) with smart caching, error recovery, and multiple execution modes.

---

## Problem Statement

### Current Pain Points

The existing workflow requires researchers to:

1. **Manually execute 8+ sequential scripts** in correct order
2. **Track intermediate outputs** across multiple directories
3. **Re-run entire pipelines** when single steps fail
4. **Hardcode parameters** in each script file
5. **Lack visibility** into workflow progress and state

### User Impact

- **High cognitive load:** Remembering execution order and dependencies
- **Time waste:** Re-running expensive computations unnecessarily
- **Error-prone:** Easy to skip steps or use wrong configurations
- **Poor reproducibility:** Hard to document exact workflow executed

---

## Solution Overview

### Design Principles

1. **Declarative over imperative:** Specify *what* to compute, not *how*
2. **Smart caching:** Skip completed steps automatically
3. **Fail-fast validation:** Catch configuration errors before execution
4. **Progressive disclosure:** Simple defaults, advanced options available
5. **Composability:** CLI commands work with notebooks and scripts

### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
├─────────────────────────────────────────────────────────────┤
│  CLI Commands (Click)                                        │
│  - aponyx run      : Execute workflow                        │
│  - aponyx report   : Generate reports                        │
│  - aponyx list     : Show catalog items                      │
│  - aponyx clean    : Clear cached results                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                        │
├─────────────────────────────────────────────────────────────┤
│  WorkflowEngine                                              │
│  - Dependency resolution                                     │
│  - Cache management                                          │
│  - Error handling & recovery                                 │
│  - Progress tracking                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Execution Layer                          │
├─────────────────────────────────────────────────────────────┤
│  WorkflowSteps (Abstract Protocol)                           │
│  - DataStep      : Fetch/generate data                       │
│  - SignalStep    : Compute signals                           │
│  - SuitabilityStep : Evaluate signal quality                 │
│  - BacktestStep  : Run strategy backtest                     │
│  - PerformanceStep : Compute extended metrics                │
│  - VisualizationStep : Generate charts                       │
└─────────────────────────────────────────────────────────────┘
```

---

## User Interface Design

### Command Structure

```bash
aponyx [COMMAND] [OPTIONS]
```

### Primary Commands

#### 1. `aponyx run` — Execute Research Workflow

**Purpose:** Run complete or partial research pipeline for signal-strategy combination.

**Prerequisites:** Data must be in registry (run data fetching scripts first).

**Syntax:**
```bash
aponyx run --signal SIGNAL --strategy STRATEGY [OPTIONS]
```

**Options:**
- `--signal TEXT` (required): Signal name from catalog
- `--strategy TEXT` (required): Strategy name from catalog
- `--data [synthetic|file|bloomberg]` (default: synthetic): Data source context (not used for fetching)
- `--steps TEXT`: Comma-separated step list (default: all)
- `--force`: Force re-run even if outputs exist
- `--config PATH`: Custom configuration file

**Examples:**
```bash
# Full workflow with defaults (assumes data in registry)
aponyx run --signal spread_momentum --strategy balanced

# Specific steps only
aponyx run --signal cdx_vix_gap --strategy aggressive \
  --steps signal,backtest,performance

# Force complete re-run
aponyx run --signal spread_momentum --strategy balanced --force
```

**Output:**
```
[2025-11-20 14:32:15] Starting workflow: spread_momentum (balanced)
[2025-11-20 14:32:15] Step 1/6: Data (loading from registry) ✓
[2025-11-20 14:32:18] Step 2/6: Signal computation ✓
[2025-11-20 14:32:21] Step 3/6: Suitability evaluation ✓
[2025-11-20 14:32:24] Step 4/6: Backtest execution ✓
[2025-11-20 14:32:27] Step 5/6: Performance analysis ✓
[2025-11-20 14:32:30] Step 6/6: Visualization ✓

✅ Workflow complete (15.2s)
📊 Results: data/processed/workflows/spread_momentum_balanced_20251120_143230/
```

---

#### 2. `aponyx report` — Generate Research Report

**Purpose:** Create comprehensive analysis document from existing results.

**Syntax:**
```bash
aponyx report --signal SIGNAL --strategy STRATEGY [OPTIONS]
```

**Options:**
- `--signal TEXT` (required): Signal name
- `--strategy TEXT` (required): Strategy name
- `--format [console|markdown|html]` (default: console): Output format
- `--output PATH`: Custom output path

**Examples:**
```bash
# Console summary
aponyx report --signal spread_momentum --strategy balanced

# HTML report
aponyx report --signal spread_momentum --strategy balanced \
  --format html --output reports/momentum_report.html
```

---

#### 3. `aponyx list` — Show Catalog Items

**Purpose:** Display available signals, strategies, or datasets.

**Syntax:**
```bash
aponyx list [signals|strategies|datasets]
```

**Examples:**
```bash
# List all signals
aponyx list signals

# List all strategies
aponyx list strategies

# List registered datasets
aponyx list datasets
```

**Output:**
```
Available Signals:
  • spread_momentum      — CDX spread momentum (z-score)
  • cdx_etf_basis        — CDX-ETF basis divergence
  • cdx_vix_gap          — VIX-CDX cross-asset gap

Available Strategies:
  • balanced             — 50% exposure, ±2 thresholds
  • aggressive           — 100% exposure, ±1 thresholds
  • conservative         — 25% exposure, ±3 thresholds
```

---

#### 4. `aponyx clean` — Clear Cached Results

**Purpose:** Remove processed outputs to force fresh computation.

**Syntax:**
```bash
aponyx clean [OPTIONS]
```

**Options:**
- `--signal TEXT`: Clean specific signal results
- `--all`: Clean all cached results
- `--dry-run`: Show what would be deleted

**Examples:**
```bash
# Clean specific signal
aponyx clean --signal spread_momentum

# Clean everything (with confirmation)
aponyx clean --all

# Preview deletions
aponyx clean --all --dry-run
```

---

## Workflow Execution Model

### Step Dependency Graph

```
DataStep (Load from registry)
   ↓
SignalStep (Compute via compute_registered_signals)
   ↓
SuitabilityStep (Evaluate with forward returns)
   ↓
BacktestStep (Run via run_backtest function)
   ↓
PerformanceStep (Analyze via analyze_backtest_performance)
   ↓
VisualizationStep (Generate charts)
```

### Workflow Assumptions

**Data Availability:**
- Workflow assumes data is **already in registry** from prior data fetching
- DataStep loads from registry, does not fetch fresh data
- For fresh data, run data fetching scripts (`01_generate_synthetic_data.py` or `02_fetch_data_file.py`) before workflow

**Signal Computation:**
- Uses `compute_registered_signals()` to batch-compute all enabled signals
- Extracts target signal for workflow from batch results
- Requires forward returns computation for suitability evaluation

**Backtest Execution:**
- Uses `run_backtest()` function, not a BacktestEngine class
- Returns `BacktestResult` dataclass with positions and P&L
- Requires strategy metadata from StrategyRegistry for config

**Performance Analysis:**
- Uses `analyze_backtest_performance()` function
- Accepts `BacktestResult` dataclass from backtest step
- Generates markdown reports with comprehensive metrics

### Caching Strategy

**Cache Key:** `{signal_name}_{strategy_name}_{data_source}_{step_name}`

**Cache Location:** `data/processed/workflows/{signal}_{strategy}_{timestamp}/`

**Cache Invalidation:**
1. Manual: `--force` flag or `aponyx clean`
2. Automatic: Upstream step re-run invalidates downstream cache
3. Configuration change: Catalog modification invalidates dependent steps

**Cache Hit Detection:**
- Check for output files in expected locations
- Validate file modification timestamps
- Compare configuration checksums

### Error Handling

**Failure Modes:**

1. **Configuration Error** (fail-fast)
   - Invalid signal/strategy name
   - Missing required catalog entries
   - Incompatible parameter combinations

2. **Data Error** (recoverable)
   - Missing data files
   - Data validation failures
   - Connection timeouts (Bloomberg)

3. **Computation Error** (partial recovery)
   - Signal computation failures
   - Backtest exceptions
   - Insufficient data for analysis

**Recovery Strategies:**

- **Fail-fast:** Configuration errors → exit immediately with clear message
- **Partial execution:** Step N fails → save results from steps 1–(N-1)
- **Retry logic:** Network errors → exponential backoff (3 attempts)
- **Graceful degradation:** Missing optional data → skip dependent visualizations

---

## Configuration Management

### Configuration Sources (Priority Order)

1. **Command-line flags** (highest priority)
2. **Config file** (`--config workflow.yaml`)
3. **Catalog defaults** (signal/strategy catalogs)
4. **System defaults** (hardcoded fallbacks)

### Configuration File Format

**YAML Example:**
```yaml
# workflow.yaml
workflow:
  signal: spread_momentum
  strategy: balanced
  data_source: bloomberg
  
  steps:
    - data
    - signal
    - backtest
    - visualization
    
  options:
    force_rerun: false
    cache_enabled: true
    
  data:
    bloomberg:
      universe: cdx_ig_5y
      start_date: 2020-01-01
      end_date: 2025-11-20
      
  backtest:
    transaction_costs: 0.0001
    slippage: 0.0005
```

---

## Implementation Phases

### Phase 1: Core CLI Framework (Week 1)
- Click-based CLI structure
- Basic `run` command with hardcoded steps
- Simple progress logging
- No caching (always re-run)

### Phase 2: Workflow Engine (Week 2)
- Abstract `WorkflowStep` protocol
- Dependency graph execution
- Cache detection and skip logic
- Error handling and partial execution

### Phase 3: Additional Commands (Week 3)
- `report` command
- `list` command
- `clean` command
- Configuration file support

### Phase 4: Advanced Features (Week 4)
- Parallel step execution (independent steps)
- Progress bars and rich terminal output
- Workflow resumption after failure
- Configuration validation and linting

---

## Success Metrics

### Quantitative

- **Time savings:** Reduce workflow execution from 8 manual steps to 1 command
- **Error reduction:** Eliminate 90% of configuration errors via validation
- **Cache hit rate:** 80%+ cache reuse for iterative development

### Qualitative

- **Ease of use:** New researchers can run workflows without reading 8 scripts
- **Reproducibility:** Configuration files enable exact workflow replication
- **Discoverability:** `aponyx list` makes catalog exploration trivial

---

## Future Enhancements

### Near-term (Next Quarter)

1. **Streamlit dashboard:** Interactive UI for non-technical users
2. **Workflow templates:** Pre-configured YAML files for common patterns
3. **Result comparison:** Diff reports between workflow runs

### Long-term (Next Year)

1. **Cloud execution:** Remote workflow execution via API
2. **Distributed backtests:** Parallel execution across parameters
3. **Live monitoring:** Real-time signal tracking dashboards
4. **Jupyter integration:** Magic commands (`%aponyx run`)

---

## Appendix: Design Alternatives Considered

### Alternative 1: Makefile-based Pipeline
**Pros:** Standard tooling, dependency tracking  
**Cons:** Poor error messages, Windows compatibility issues  
**Decision:** Rejected — Python-native solution preferred

### Alternative 2: Airflow/Prefect DAG
**Pros:** Enterprise-grade orchestration, UI included  
**Cons:** Heavy dependencies, overkill for single-user research  
**Decision:** Rejected — too complex for target use case

### Alternative 3: Jupyter Notebook with Widgets
**Pros:** Interactive, familiar to researchers  
**Cons:** Hard to version control, non-reproducible  
**Decision:** Rejected — CLI preferred for automation

---

## References

- [Click Documentation](https://click.palletsprojects.com/)
- [Rich Terminal Library](https://rich.readthedocs.io/)
- [Workflow Orchestration Patterns](https://martinfowler.com/articles/patterns-of-distributed-systems/workflow.html)
