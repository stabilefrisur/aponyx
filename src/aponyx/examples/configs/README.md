# Aponyx Configuration Examples

Numbered examples demonstrating Aponyx workflows and parameter sweeps, from simple to advanced.

---

## Workflows (01-03)

Run workflows with: `uv run aponyx run src/aponyx/examples/configs/<file>.yaml`

### 01. Minimal Workflow
**File:** `01_workflow_minimal.yaml`  
**Purpose:** Quick start with minimal required fields  
**Features:** Default transformations, synthetic data, basic validation  
**Use Case:** Getting started, CI/CD, smoke testing

### 02. Complete Workflow
**File:** `02_workflow_complete.yaml`  
**Purpose:** Full configuration reference with all overrides  
**Features:**
- Explicit four-stage pipeline overrides
- Custom security mappings
- Product microstructure overrides (DV01, transaction costs)
- Display channel customization
- Selective step execution

**Use Case:** Custom strategy development, research, production tuning

### 03. ETF Price Backtest
**File:** `03_workflow_etf_price_backtest.yaml`  
**Purpose:** Demonstrate price-quoted product backtesting  
**Features:**
- Automatic PriceReturnCalculator selection
- Price-based P&L (not spread-based)
- Cross-asset signals (CDX + ETF)

**Use Case:** ETF strategies, price return analysis

---

## Parameter Sweeps (04-06)

Run sweeps with: `uv run aponyx sweep src/aponyx/examples/configs/<file>.yaml`

### 04. Indicator Sweep
**File:** `04_sweep_indicator_lookback.yaml`  
**Mode:** `indicator` (no backtest)  
**Combinations:** 8 (4 × 2)  
**Parameters:**
- Indicator lookback windows (10, 20, 40, 60 days)
- Score normalization windows (20, 40 days)

**Use Case:** Fast indicator optimization, pre-backtest analysis

### 05. Strategy Optimization
**File:** `05_sweep_strategy_optimization.yaml`  
**Mode:** `backtest` (full P&L)  
**Combinations:** 27 (3 × 3 × 3)  
**Parameters:**
- Position sizing (5, 10, 20 MM)
- Signal floor bounds (-1.0, -1.5, -2.0)
- Signal cap bounds (1.0, 1.5, 2.0)

**Use Case:** Risk-return optimization, production deployment

### 06. Comprehensive Sweep
**File:** `06_sweep_comprehensive.yaml`  
**Mode:** `backtest` (full P&L)  
**Combinations:** 2,048 total (limited to 200)  
**Parameters:** All four pipeline stages
- Stage 1: Indicator (lookback)
- Stage 2: Score (window, min_periods)
- Stage 3: Signal (scaling, floor, cap)
- Stage 4: Strategy (size, thresholds, risk controls)

**Use Case:** Exhaustive search, research exploration

---

## Quick Reference

| Example | Type | Runtime | Combinations | Output |
|---------|------|---------|--------------|--------|
| 01_workflow_minimal | Workflow | ~5s | 1 | Single backtest |
| 02_workflow_complete | Workflow | ~5s | 1 | Single backtest |
| 03_workflow_etf_price_backtest | Workflow | ~5s | 1 | Single backtest |
| 04_sweep_indicator_lookback | Sweep | ~5s | 8 | Statistical summaries |
| 05_sweep_strategy_optimization | Sweep | ~6s | 27 | Performance metrics |
| 06_sweep_comprehensive | Sweep | ~18s | 200 | Full optimization |

---

## Common Patterns

### Override Indicator Parameters
```yaml
indicator_transformation:
  parameters:
    lookback: 10
```

### Override Transaction Costs
```yaml
transaction_cost_bps_override: 2.5        # Fixed cost
# OR
transaction_cost_pct_override: 0.025      # Percentage of spread
```

### Control Execution
```yaml
steps: [data, signal, backtest]           # Run specific steps
force: true                               # Bypass cache
```

### Sweep Multiple Stages
```yaml
parameters:
  - path: "indicator_transformation.parameters.lookback"
    values: [10, 20]
  - path: "signal_transformation.parameters.floor"
    values: [-1.0, -1.5]
```

---

## Next Steps

1. Start with `01_workflow_minimal.yaml` to validate your environment
2. Explore `02_workflow_complete.yaml` for available overrides
3. Try `04_sweep_indicator_lookback.yaml` for quick parameter tuning
4. Use `05_sweep_strategy_optimization.yaml` for production optimization

For detailed documentation, see the main README and specs/ directory.
