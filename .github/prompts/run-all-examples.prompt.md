---
mode: agent
model: Claude Sonnet 4.5
description: 'Run all example configurations to validate the complete pipeline (workflows and sweeps).'
---
# Run All Example Configurations

Execute all example configurations in sequence to validate the complete Aponyx pipeline, from minimal workflows to comprehensive parameter sweeps.

## Overview

This prompt runs all 6 example configurations:
- **Workflows (01-03):** Single backtests with different features
- **Sweeps (04-06):** Parameter sensitivity analysis

Total estimated runtime: ~29 seconds

## Sequence

Run the following configurations in order:

### Phase 1: Workflows (~14 seconds)

1. **Minimal Workflow** - Quick start validation
2. **Complete Workflow** - Full feature demonstration
3. **ETF Price Backtest** - Price-quoted product backtest

### Phase 2: Indicator Sweeps (~5 seconds)

4. **Indicator Lookback Sweep** - Fast parameter optimization (8 combinations)

### Phase 3: Backtest Sweeps (~24 seconds)

5. **Strategy Optimization Sweep** - Signal bounds and position sizing (27 combinations)
6. **Comprehensive Sweep** - All pipeline stages (200 combinations)

## Commands

```bash
# Phase 1: Workflows
echo "=== Phase 1: Workflows ==="
uv run aponyx run src/aponyx/examples/configs/01_workflow_minimal.yaml
uv run aponyx run src/aponyx/examples/configs/02_workflow_complete.yaml
uv run aponyx run src/aponyx/examples/configs/03_workflow_etf_price_backtest.yaml

# Phase 2: Indicator Sweeps
echo "=== Phase 2: Indicator Sweeps ==="
uv run aponyx sweep src/aponyx/examples/configs/04_sweep_indicator_lookback.yaml

# Phase 3: Backtest Sweeps
echo "=== Phase 3: Backtest Sweeps ==="
uv run aponyx sweep src/aponyx/examples/configs/05_sweep_strategy_optimization.yaml
uv run aponyx sweep src/aponyx/examples/configs/06_sweep_comprehensive.yaml
```

## Expected Output

Each workflow produces:
- Timestamped output directory in `data/workflows/<label>_<timestamp>/`
- Signal series and backtest results
- Performance metrics and visualizations
- Summary JSON with metadata

Each sweep produces:
- Timestamped output directory in `data/sweeps/<name>_<timestamp>/`
- Results for each parameter combination
- Aggregated performance metrics
- Best parameter identification

## Success Criteria

All commands should:
- Exit with code 0 (no errors)
- Generate expected output directories
- Produce valid performance metrics
- Complete without exceptions

## Optional: Quick Validation Only

To run only workflows (skip sweeps for speed):

```bash
uv run aponyx run src/aponyx/examples/configs/01_workflow_minimal.yaml
uv run aponyx run src/aponyx/examples/configs/02_workflow_complete.yaml
uv run aponyx run src/aponyx/examples/configs/03_workflow_etf_price_backtest.yaml
```

## Output Directories

After completion, check:
- `data/workflows/` - Should contain 3 new timestamped directories
- `data/sweeps/` - Should contain 3 new timestamped directories
- `logs/` - Should contain execution logs
