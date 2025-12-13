# CLI User Guide

Aponyx CLI consolidates systematic credit research workflows into single-command execution.

## Quick Start

```bash
# Create minimal config
cat > workflow.yaml << EOF
label: my_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
EOF

# Run complete workflow
uv run aponyx run workflow.yaml

# Generate report (by label)
uv run aponyx report --workflow my_test

# List available items
uv run aponyx list signals
uv run aponyx list workflows
```

**Logging:** Default is WARNING. Use `-v` for DEBUG. Logs saved to `logs/aponyx_{timestamp}.log`.

## Command Reference

- **`run`** — Execute research workflow (data → signal → suitability → backtest → performance → visualization)
- **`report`** — Generate multi-format reports from workflow results
- **`list`** — Show available signals, products, indicators, transformations, securities, strategies, datasets, steps, or workflows
- **`clean`** — Remove cached workflow results and indicator cache

---

## Commands

### `run` — Execute Research Workflow

Execute complete or partial research pipeline using YAML configuration.

**Prerequisites:** Data must be in registry (run data fetching scripts first).

**Usage:**
```bash
uv run aponyx run <config_path>
```

**YAML Configuration Schema:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `label` | string | ✓ | - | Workflow label (lowercase, underscores, numbers only: ^[a-z][a-z0-9_]*$) |
| `signal` | string | ✓ | - | Signal name from signal_catalog.json |
| `product` | string | ✓ | - | Product identifier (e.g., "cdx_ig_5y") |
| `strategy` | string | ✓ | - | Strategy name from strategy_catalog.json |
| `indicator` | string | | from signal | Override indicator transformation (must exist in indicator_transformation.json) |
| `score_transformation` | string | | from signal | Override score transformation (must exist in score_transformation.json) |
| `signal_transformation` | string | | from signal | Override signal transformation (must exist in signal_transformation.json) |
| `securities` | dict | | from indicator | Custom security mapping (e.g., `cdx: cdx_hy_5y`) |
| `data` | string | | "synthetic" | Data source: `synthetic`, `file`, `bloomberg` |
| `steps` | list | | all | Specific steps to execute (e.g., `[data, signal, backtest]`) |
| `force` | boolean | | false | Force re-run all steps (skip cache)

**Examples:**

**Minimal configuration** (`workflow_minimal.yaml`):
```yaml
label: minimal_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
```

**Complete configuration** (`workflow_complete.yaml`):
```yaml
label: complete_test
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced
indicator: cdx_etf_spread_diff
score_transformation: z_score_20d
signal_transformation: bounded_1_5
securities:
  cdx: cdx_ig_5y
  etf: lqd
data: synthetic
steps: [data, signal, suitability, backtest, performance, visualization]
force: true
```

**Run workflows:**
```bash
# Use example configs
uv run aponyx run examples/workflow_minimal.yaml
uv run aponyx run examples/workflow_complete.yaml
```

**Terminal Output:**
```
=== Workflow Configuration ===
Label:                    minimal_test [config]
Product:                  cdx_ig_5y [config]
Signal:                   spread_momentum [config]
Indicator Transform:      spread_momentum_5d [from signal]
Securities:               cdx:cdx_ig_5y [from indicator]
Score Transform:          volatility_adjust_20d [from signal]
Signal Transform:         passthrough [from signal]
Strategy:                 balanced [config]
Data:                     synthetic [default]
Steps:                    all [default]
Force re-run:             False [default]
==============================

Completed 6 steps in 1.5s
Results: data/workflows/minimal_test_20251213_205920/
```

**Source Tags:**
- `[config]` — Explicitly provided in YAML
- `[from signal]` — Resolved from signal metadata
- `[from indicator]` — Resolved from indicator metadata
- `[default]` — System default value

---

### `report` — Generate Research Report

Generate comprehensive reports from workflow results.

**Usage:**
```bash
uv run aponyx report [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--workflow` | TEXT | Required | Workflow label or numeric index (0 = most recent) |
| `--format` | CHOICE | console | Format: `console`, `markdown`, `html` |

**Workflow Selection:**

- **By label**: Use the workflow label from YAML config (stable reference)
- **By index**: Use numeric index from `aponyx list workflows` (ephemeral, sorted by timestamp descending)

**Examples:**

```bash
# Console summary (by label)
uv run aponyx report --workflow minimal_test

# By numeric index (0 = most recent)
uv run aponyx report --workflow 0

# Generate markdown (saved to workflow's reports/ folder)
uv run aponyx report --workflow minimal_test --format markdown

# Generate HTML (saved to workflow's reports/ folder)
uv run aponyx report --workflow minimal_test --format html
```

**Note:** Numeric indices are ephemeral and change as new workflows are created. Use labels for stable references in scripts. Reports are saved to the workflow's `reports/` folder.

---

### `list` — Show Catalog Items

List available signals, strategies, datasets, or workflow results.

**Usage:**
```bash
uv run aponyx list {signals|products|indicators|score-transformations|signal-transformations|securities|datasets|strategies|steps|workflows}
```

**Item Types:**

| Item Type | Description |
|-----------|-------------|
| `signals` | Available signals from signal_catalog.json |
| `products` | Available products (CDX indices) |
| `indicators` | Indicator transformations from indicator_transformation.json |
| `score-transformations` | Score transformations (z-score, volatility adjust, etc.) |
| `signal-transformations` | Signal transformations (bounds, neutral zones) |
| `securities` | Available securities for data fetching |
| `datasets` | Cached datasets in data registry |
| `strategies` | Available strategies from strategy_catalog.json |
| `steps` | Workflow steps in canonical order |
| `workflows` | Completed workflow results |

**Workflow Filters (workflows only):**

| Option | Type | Description |
|--------|------|-------------|
| `--signal` | TEXT | Filter by signal name |
| `--product` | TEXT | Filter by product identifier |
| `--strategy` | TEXT | Filter by strategy name |

**Examples:**
```bash
uv run aponyx list signals
uv run aponyx list products
uv run aponyx list indicators
uv run aponyx list score-transformations
uv run aponyx list signal-transformations
uv run aponyx list securities
uv run aponyx list strategies
uv run aponyx list datasets
uv run aponyx list steps
uv run aponyx list workflows                      # All workflows (up to 50 most recent)
uv run aponyx list workflows --signal spread_momentum
uv run aponyx list workflows --product cdx_ig_5y --strategy balanced
```

**Workflow Output:**

Displays table with IDX (ephemeral index), LABEL, SIGNAL, STRATEGY, PRODUCT, STATUS, and TIMESTAMP. Sorted by timestamp descending (newest first). Limited to 50 results unless filtered.

---

### `clean` — Clear Cached Results

Remove cached workflow results with age-based filtering.

**Usage:**
```bash
uv run aponyx clean [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--workflows` | FLAG | Enable workflow pruning mode |
| `--indicators` | FLAG | Clean indicator cache |
| `--signal` | TEXT | Filter by signal name (workflows only) |
| `--older-than` | TEXT | Age threshold (e.g., "30d", minimum 1 day) |
| `--all` | FLAG | Clean all matching items |
| `--dry-run` | FLAG | Preview without deleting |

**Examples:**

```bash
# Preview all workflow deletions
uv run aponyx clean --workflows --all --dry-run

# Clean workflows older than 30 days
uv run aponyx clean --workflows --older-than 30d

# Clean specific signal's workflows older than 7 days
uv run aponyx clean --workflows --signal spread_momentum --older-than 7d

# Clean all workflows (no preview)
uv run aponyx clean --workflows --all

# Clean indicator cache
uv run aponyx clean --indicators
```

**Validation:**
- `--older-than` format: `{number}d` (e.g., "30d", "7d")
- Minimum age: 1 day (prevents accidental deletion of current work)
- Can combine `--signal` and `--older-than` filters

---

## Understanding Workflows

### Execution Pipeline

Workflows execute 6 steps in order:

1. **data** — Load market data from registry
2. **signal** — Compute signal values (z-score normalized)
3. **suitability** — Pre-backtest evaluation (PASS/HOLD/FAIL)
4. **backtest** — Simulate P&L with transaction costs (binary or proportional sizing)
5. **performance** — Extended metrics (Sharpe, Sortino, attribution)
6. **visualization** — Generate interactive charts

**Dependencies:** Steps depend on previous steps. `signal` requires `data`; `backtest` requires `signal` + `suitability`; etc.

**Smart caching:** Completed steps are skipped unless `--force` is used.

### Output Structure

Results saved to: `data/workflows/{label}_{timestamp}/`

```
├── metadata.json              # Run parameters (label, signal, strategy, product, securities_used, status, timestamp)
├── signals/
│   └── signal.parquet         # Signal time series
├── reports/
│   ├── suitability_evaluation_{timestamp}.md  # Pre-backtest analysis
│   └── performance_analysis_{timestamp}.md    # Post-backtest metrics
├── backtest/
│   ├── pnl.parquet            # P&L time series
│   └── positions.parquet      # Position time series
└── visualizations/            # Plotly charts (HTML)
    ├── equity_curve.html
    ├── drawdown.html
    └── signal.html
```

**Cache:** `data/cache/{provider}/{security}_{hash}.parquet` (TTL-based, auto-regenerated)

### Configuration Files

All workflows use YAML configuration files with required and optional fields.

**Minimal workflow** (`workflow_minimal.yaml`):
```yaml
label: minimal_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
```

**Custom securities**:
```yaml
label: custom_securities
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced
securities:
  cdx: cdx_hy_5y
  etf: hyg
```

**Partial pipeline**:
```yaml
label: partial_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
steps: [data, signal, backtest]
force: true
```

**Bloomberg data**:
```yaml
label: bloomberg_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
data: bloomberg
force: true  # Update current day data
```

**Runtime overrides**:
```yaml
label: override_test
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced
indicator: cdx_etf_spread_diff       # Override indicator transformation
score_transformation: z_score_60d    # Override score transformation (e.g., 60-day instead of 20-day)
signal_transformation: bounded_1_5   # Override signal transformation (apply bounds)
```

**Proportional sizing** (position size scales with signal magnitude - default):
```yaml
label: proportional_test
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced      # Uses proportional sizing mode by default
```

**Usage:**
```bash
uv run aponyx run examples/workflow_minimal.yaml
```

**Default Resolution Priority:**
1. Explicitly provided in YAML config (`[config]`)
2. Resolved from signal metadata (`[from signal]`)
3. Resolved from indicator metadata (`[from indicator]`)
4. System defaults (`[default]`)

---

## Position Sizing Modes

Strategies support two sizing modes that determine how signal values translate to position sizes:

### Proportional Sizing (Default)

**Mode:** `sizing_mode: "proportional"`

Position scales with signal magnitude:
- Position = signal × `position_size_mm`
- Higher conviction signals → Larger positions
- Rebalancing occurs when signal magnitude changes (with transaction costs)
- Position values recorded as actual notional in MM (e.g., 5.0, -3.5)

**Strategies:** `conservative`, `balanced`, `aggressive`, `experimental` (all default to proportional)

**Use case:** When signal strength indicates conviction and you want position size to reflect that.

### Binary Sizing (Runtime Override)

**Mode:** `sizing_mode: "binary"` (use as runtime override)`

Position is full size regardless of signal magnitude:
- Non-zero signal → Full `position_size_mm` (direction from sign)
- Signal magnitude is ignored (only sign matters)
- Position values recorded as ±1 (direction indicator)

**Override via workflow config or to_config():**
```yaml
sizing_mode_override: binary
```

**Use case:** When you want consistent position sizes and only care about signal direction.

### Risk Management Differences

| Feature | Binary | Proportional |
|---------|--------|--------------|
| Stop loss check | vs entry notional × DV01 | vs current notional |
| Take profit check | vs entry notional × DV01 | vs current notional |
| Rebalancing | None (position is fixed) | On signal magnitude change |
| Transaction costs | Entry/exit only | Entry/exit + rebalancing |
| Cooldown release | Signal returns to zero | Signal returns to zero OR sign change |

### Example Comparison

```yaml
# Proportional (default): Position = signal × 10MM
# Signal 0.5 → 5MM position, Signal 1.5 → 15MM position
label: proportional_test
signal: spread_momentum
strategy: balanced              # sizing_mode: proportional (default), position_size_mm: 10.0

# Binary override: Full 10MM position for any non-zero signal
label: binary_test
signal: spread_momentum
strategy: balanced
sizing_mode_override: binary    # Override to binary sizing
```

---

## Common Workflows

### Production Research

```bash
# Create Bloomberg workflow config
cat > workflow_bloomberg.yaml << EOF
label: bloomberg_run
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
data: bloomberg
force: true
EOF

# 1. Run workflow with Bloomberg data
uv run aponyx run workflow_bloomberg.yaml

# 2. Generate HTML report
uv run aponyx report --workflow bloomberg_run --format html --output reports/latest.html
```

### Batch Processing

```bash
# Process multiple configs in sequence
for config in configs/*.yaml; do
  uv run aponyx run "$config"
done

# Generate consolidated reports (using labels from configs)
uv run aponyx report --workflow run1 --format markdown
uv run aponyx report --workflow run2 --format markdown
```

### Maintenance

```bash
# Preview what will be deleted
uv run aponyx clean --workflows --all --dry-run

# Fresh start (clear all cached results)
uv run aponyx clean --workflows --all

# Remove old workflows (older than 30 days)
uv run aponyx clean --workflows --older-than 30d

# Clean specific signal's old workflows
uv run aponyx clean --workflows --signal old_signal --older-than 7d
```

---

## Troubleshooting

### Installation & Setup

**Command not found:**
```bash
uv pip install -e .     # Install package
uv pip show aponyx      # Verify installation
uv run aponyx --help    # Test command
```

### Configuration Issues

**YAML parsing errors:**
```bash
# Validate syntax
python -c "import yaml; yaml.safe_load(open('workflow.yaml'))"

# Common issues:
# - Use spaces, not tabs for indentation
# - Colons require space after (key: value, not key:value)
# - List items use brackets: steps: [data, signal]
# - Dict items use colons: securities: {cdx: cdx_ig_5y}
# - Strings with special chars need quotes

# Reference valid configs
ls examples/*.yaml
cat examples/workflow_minimal.yaml
```

**Missing required fields:**
```bash
# Error: "Missing required field: label"
# Solution: Add all required fields to YAML

cat > workflow.yaml << EOF
label: my_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
EOF
```

**Invalid catalog references:**
```bash
# Error: "Signal 'invalid_signal' not found in catalog"
# Solution: List available items

uv run aponyx list signals
uv run aponyx list indicators
uv run aponyx list score-transformations
uv run aponyx list signal-transformations
uv run aponyx list securities
uv run aponyx list products
uv run aponyx list strategies

# Check catalog files directly
cat src/aponyx/models/signal_catalog.json
cat src/aponyx/models/indicator_transformation.json
cat src/aponyx/models/score_transformation.json
cat src/aponyx/models/signal_transformation.json
cat src/aponyx/data/bloomberg_securities.json
cat src/aponyx/backtest/strategy_catalog.json
```

**Permission errors:**
```bash
# Check directory permissions
ls -la data/workflows/ reports/ logs/

# Create directories if missing
mkdir -p data/workflows reports logs

# Fix permissions if needed
chmod -R u+w data/ reports/ logs/
```

### Performance & Debugging

**Enable verbose logging:**
```bash
uv run aponyx -v run examples/workflow_minimal.yaml

# Check log file for details
tail -f logs/aponyx_*.log
```

**Cache issues:**
```bash
# Clear workflow cache and re-run
uv run aponyx clean --workflows --all

# Clear indicator cache
uv run aponyx clean --indicators
```

---

## See Also

- **Main Documentation:** [README.md](../../README.md)
- **Architecture:** [governance_design.md](governance_design.md)
- **Signal Catalog:** [../models/signal_catalog.json](../models/signal_catalog.json)
- **Indicator Transformation Catalog:** [../models/indicator_transformation.json](../models/indicator_transformation.json)
- **Score Transformation Catalog:** [../models/score_transformation.json](../models/score_transformation.json)
- **Signal Transformation Catalog:** [../models/signal_transformation.json](../models/signal_transformation.json)
- **Securities Catalog:** [../data/bloomberg_securities.json](../data/bloomberg_securities.json)
- **Strategy Catalog:** [../backtest/strategy_catalog.json](../backtest/strategy_catalog.json)

---

**Maintained by:** stabilefrisur  
**Last Updated:** December 13, 2025
