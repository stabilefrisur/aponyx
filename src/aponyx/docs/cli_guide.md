# CLI User Guide

Aponyx CLI consolidates systematic credit research workflows into single-command execution.

## Quick Start

```bash
# Create minimal config
cat > workflow.yaml << EOF
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
EOF

# Run complete workflow
uv run aponyx run workflow.yaml

# Generate report
uv run aponyx report --signal spread_momentum --strategy balanced

# List available items
uv run aponyx list signals
```

**Logging:** Default is WARNING. Use `-v` for DEBUG. Logs saved to `logs/aponyx_{timestamp}.log`.

## Command Reference

- **`run`** — Execute research workflow (data → signal → suitability → backtest → performance → visualization)
- **`report`** — Generate multi-format reports from workflow results
- **`list`** — Show available signals, strategies, datasets, or steps
- **`clean`** — Remove cached workflow results

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
| `signal` | string | ✓ | - | Signal name from signal_catalog.json |
| `product` | string | ✓ | - | Product identifier (e.g., "cdx_ig_5y") |
| `strategy` | string | ✓ | - | Strategy name from strategy_catalog.json |
| `indicator` | string | | from signal | Override indicator computation |
| `transformation` | string | | from signal | Override transformation |
| `securities` | dict | | from indicator | Custom security mapping (e.g., `cdx: cdx_hy_5y`) |
| `data` | string | | "synthetic" | Data source: `synthetic`, `file`, `bloomberg` |
| `steps` | list | | all | Specific steps to execute (e.g., `[data, signal, backtest]`) |
| `force` | boolean | | false | Force re-run and update current day data |

**Examples:**

**Minimal configuration** (`workflow_minimal.yaml`):
```yaml
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
```

**Complete configuration** (`workflow_complete.yaml`):
```yaml
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced
indicator: cdx_etf_spread_diff
transformation: z_score_20d
securities:
  cdx: cdx_hy_5y
  etf: hyg
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
Signal: spread_momentum [config]
Product: cdx_ig_5y [config]
Strategy: balanced [config]
Indicator: spread_momentum_20d [from signal]
Transformation: z_score [from indicator]
Securities: {'cdx': 'cdx_ig_5y'} [from indicator]
Data: synthetic [default]
Steps: all [default]
Force re-run: False [default]

Completed 6 steps in 15.2s
Results: data/workflows/spread_momentum_balanced_20251123_143230/
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
| `--signal` | TEXT | Required | Signal name |
| `--strategy` | TEXT | Required | Strategy name |
| `--format` | CHOICE | console | Format: `console`, `markdown`, `html` |
| `--output` | PATH | - | Custom output path |

**Examples:**

```bash
# Console summary
uv run aponyx report --signal spread_momentum --strategy balanced

# Generate markdown
uv run aponyx report --signal spread_momentum --strategy balanced --format markdown

# Custom location
uv run aponyx report --signal spread_momentum --strategy balanced --format html --output reports/custom.html
```

---

### `list` — Show Catalog Items

List available signals, strategies, or datasets.

**Usage:**
```bash
uv run aponyx list {signals|strategies|datasets}
```

**Examples:**
```bash
uv run aponyx list signals
uv run aponyx list strategies
uv run aponyx list datasets
```

---

### `clean` — Clear Cached Results

Remove cached workflow results.

**Usage:**
```bash
uv run aponyx clean [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--signal` | TEXT | Clean specific signal only |
| `--all` | FLAG | Clean all cached results |
| `--dry-run` | FLAG | Preview without deleting |

**Examples:**

```bash
# Clean specific signal
uv run aponyx clean --signal spread_momentum

# Clean all (shows deletions)
uv run aponyx clean --all

# Preview
uv run aponyx clean --all --dry-run
```

---

## Understanding Workflows

### Execution Pipeline

Workflows execute 6 steps in order:

1. **data** — Load market data from registry
2. **signal** — Compute signal values (z-score normalized)
3. **suitability** — Pre-backtest evaluation (PASS/HOLD/FAIL)
4. **backtest** — Simulate P&L with transaction costs
5. **performance** — Extended metrics (Sharpe, Sortino, attribution)
6. **visualization** — Generate interactive charts

**Dependencies:** Steps depend on previous steps. `signal` requires `data`; `backtest` requires `signal` + `suitability`; etc.

**Smart caching:** Completed steps are skipped unless `--force` is used.

### Output Structure

Results saved to: `data/workflows/{signal}_{strategy}_{timestamp}/`

```
├── metadata.json                          # Run parameters, securities used
├── signal.parquet                         # Signal time series
├── suitability_evaluation_{timestamp}.md  # Pre-backtest analysis
├── backtest_result.parquet               # P&L and positions
├── performance_analysis_{timestamp}.md    # Post-backtest metrics
└── visualizations/                        # Plotly charts (HTML)
    ├── equity_curve.html
    ├── drawdown.html
    └── signal.html
```

**Cache:** `data/cache/{provider}/{security}_{hash}.parquet` (TTL-based, auto-regenerated)

### Configuration Files

All workflows use YAML configuration files with required and optional fields.

**Minimal workflow** (`workflow_minimal.yaml`):
```yaml
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
```

**Custom securities**:
```yaml
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced
securities:
  cdx: cdx_hy_5y
  etf: hyg
```

**Partial pipeline**:
```yaml
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
steps: [data, signal, backtest]
force: true
```

**Bloomberg data**:
```yaml
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
data: bloomberg
force: true  # Update current day data
```

**Runtime overrides**:
```yaml
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced
indicator: cdx_etf_spread_diff  # Override indicator
transformation: z_score_60d     # Override transformation
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

## Common Workflows

### Production Research

```bash
# Create Bloomberg workflow config
cat > workflow_bloomberg.yaml << EOF
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
data: bloomberg
force: true
EOF

# 1. Run workflow with Bloomberg data
uv run aponyx run workflow_bloomberg.yaml

# 2. Generate HTML report
uv run aponyx report --signal spread_momentum --strategy balanced --format html --output reports/latest.html
```

### Batch Processing

```bash
# Process multiple configs in sequence
for config in configs/*.yaml; do
  uv run aponyx run "$config"
done

# Generate consolidated reports
uv run aponyx report --signal spread_momentum --strategy balanced --format markdown
uv run aponyx report --signal cdx_vix_gap --strategy aggressive --format markdown
```

### Maintenance

```bash
# Preview what will be deleted
uv run aponyx clean --all --dry-run

# Fresh start (clear all cached results)
uv run aponyx clean --all

# Remove old signal results
uv run aponyx clean --signal old_signal
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
# Error: "Missing required field: signal"
# Solution: Add all required fields to YAML

cat > workflow.yaml << EOF
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
uv run aponyx list strategies

# Check catalog files
cat src/aponyx/models/signal_catalog.json
cat src/aponyx/models/indicator_catalog.json
cat src/aponyx/models/transformation_catalog.json
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
# Clear cache and re-run
uv run aponyx clean --all
```

---

## See Also

- **Main Documentation:** [README.md](../../README.md)
- **Architecture:** [governance_design.md](governance_design.md)
- **Signal Catalog:** [../models/signal_catalog.json](../models/signal_catalog.json)
- **Indicator Catalog:** [../models/indicator_catalog.json](../models/indicator_catalog.json)
- **Transformation Catalog:** [../models/transformation_catalog.json](../models/transformation_catalog.json)
- **Securities Catalog:** [../data/bloomberg_securities.json](../data/bloomberg_securities.json)
- **Strategy Catalog:** [../backtest/strategy_catalog.json](../backtest/strategy_catalog.json)

---

**Maintained by:** stabilefrisur  
**Last Updated:** November 23, 2025
