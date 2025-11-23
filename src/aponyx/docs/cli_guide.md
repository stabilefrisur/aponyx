# CLI User Guide

Aponyx CLI consolidates systematic credit research workflows into single-command execution.

## Quick Start

```bash
# Run complete workflow
uv run aponyx run --signal spread_momentum --strategy balanced

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

Execute complete or partial research pipeline.

**Prerequisites:** Data must be in registry (run data fetching scripts first).

**Usage:**
```bash
uv run aponyx run [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--signal` | TEXT | Required | Signal name from catalog |
| `--strategy` | TEXT | Required | Strategy name from catalog |
| `--product` | TEXT | cdx_ig_5y | Product identifier for backtesting |
| `--securities` | TEXT | - | Security mapping: `type1:sec1,type2:sec2` |
| `--data` | CHOICE | synthetic | Data source: `synthetic`, `file`, `bloomberg` |
| `--steps` | TEXT | all | Comma-separated step list |
| `--force` | FLAG | false | Force re-run and update current day data |
| `--config` | PATH | - | Load configuration from YAML |

**Examples:**

```bash
# Basic workflow
uv run aponyx run --signal spread_momentum --strategy balanced

# Custom data source
uv run aponyx run --signal spread_momentum --strategy balanced --data bloomberg

# Custom security mapping (override signal defaults)
uv run aponyx run --signal cdx_etf_basis --securities cdx:cdx_hy_5y,etf:hyg --strategy balanced

# Specific steps
uv run aponyx run --signal spread_momentum --strategy balanced --steps data,signal,backtest

# Force re-run (invalidates cache, refreshes today's Bloomberg data)
uv run aponyx run --signal spread_momentum --strategy balanced --force

# Use config file
uv run aponyx run --config examples/workflow_basic.yaml
```

**Output:**
```
Signal: spread_momentum (cdx:cdx_ig_5y)
Strategy: balanced
Product: cdx_ig_5y
Data: synthetic
Steps: all
Force re-run: False

Completed 6 steps in 15.2s
Results: data/workflows/spread_momentum_balanced_20251123_143230/
```

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

YAML configs support all CLI options. CLI overrides config values.

**Basic workflow:**
```yaml
signal: spread_momentum
strategy: balanced
data: synthetic
```

**Custom securities:**
```yaml
signal: cdx_etf_basis
strategy: balanced
securities:
  cdx: cdx_hy_5y
  etf: hyg
```

**Partial pipeline:**
```yaml
signal: spread_momentum
strategy: balanced
steps: [data, signal, backtest]
force: true
```

**Bloomberg data:**
```yaml
signal: spread_momentum
strategy: balanced
data: bloomberg  # Requires terminal + xbbg
```

**Usage:**
```bash
uv run aponyx run --config workflow.yaml
uv run aponyx run --config workflow.yaml --force  # Override
```

---

## Common Workflows

### Production Research

```bash
# 1. Run workflow with Bloomberg data
uv run aponyx run --signal spread_momentum --strategy balanced --data bloomberg

# 2. Generate HTML report
uv run aponyx report --signal spread_momentum --strategy balanced --format html --output reports/latest.html
```

### Signal Development

```bash
# 1. Initial test with synthetic data
uv run aponyx run --signal new_signal --strategy balanced

# 2. Iterate on signal logic (skip data loading)
uv run aponyx run --signal new_signal --strategy balanced --steps signal,suitability,backtest,performance --force

# 3. Final validation with real data
uv run aponyx run --signal new_signal --strategy balanced --data file --force
```

### Custom Security Analysis

```bash
# Test cdx_etf_basis with HY instead of IG
uv run aponyx run --signal cdx_etf_basis --securities cdx:cdx_hy_5y,etf:hyg --strategy balanced

# Compare with default (IG)
uv run aponyx run --signal cdx_etf_basis --strategy balanced
```

### Batch Processing

```bash
# Process multiple configs in sequence
for config in configs/*.yaml; do
  uv run aponyx run --config "$config"
done

# Generate consolidated reports
uv run aponyx report --signal spread_momentum --strategy balanced --format markdown
uv run aponyx report --signal cdx_vix_gap --strategy aggressive --format markdown
```

### Maintenance

```bash
# Preview what will be deleted
uv run aponyx clean --all --dry-run

# Remove old signal results
uv run aponyx clean --signal old_signal

# Fresh start (clear all cached results)
uv run aponyx clean --all
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

**Missing dependencies:**
```bash
uv pip install aponyx[bloomberg]  # Bloomberg support
uv pip list | grep -E "pandas|plotly|xbbg"  # Check versions
```

### Runtime Errors

**Missing signal/strategy:**
```bash
uv run aponyx list signals     # List available signals
uv run aponyx list strategies  # List available strategies

# Check catalog files for "enabled": true
cat src/aponyx/models/signal_catalog.json
cat src/aponyx/backtest/strategy_catalog.json
```

**No workflow results:**
```bash
# Run workflow first
uv run aponyx run --signal spread_momentum --strategy balanced

# Check output directory
ls -la data/workflows/
```

**Step failures by type:**

| Step | Common Issue | Solution |
|------|-------------|----------|
| data | No datasets in registry | Run data fetching scripts (see examples/) |
| signal | Missing required data | Check signal's data_requirements in catalog |
| suitability | No spread data for product | Verify product exists in data registry |
| backtest | Date alignment issues | Ensure signal/spread indices overlap |
| performance | Missing backtest results | Check backtest step completed successfully |

### Data Source Issues

**Bloomberg connection:**
```bash
# Verify terminal running and logged in
python -c "import xbbg.blp as blp; print(blp.bdh('SPX Index', 'PX_LAST'))"

# Check security mappings
cat src/aponyx/data/bloomberg_securities.json

# Force refresh current day data
uv run aponyx run --signal spread_momentum --strategy balanced --data bloomberg --force
```

**File source:**
```bash
# Check data directory structure
ls -R data/raw/

# Verify .parquet files exist
find data/raw -name "*.parquet"
```

### Configuration Issues

**YAML parsing errors:**
```bash
# Validate syntax
python -c "import yaml; yaml.safe_load(open('workflow.yaml'))"

# Common issues:
# - Use spaces, not tabs for indentation
# - Colons require space after (key: value, not key:value)
# - List items need hyphens or brackets
# - Strings with special chars need quotes

# Reference valid configs
ls examples/*.yaml
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
uv run aponyx -v run --signal spread_momentum --strategy balanced

# Check log file for details
tail -f logs/aponyx_*.log
```

**Cache issues:**
```bash
# Clear cache and re-run
uv run aponyx clean --all
uv run aponyx run --signal spread_momentum --strategy balanced --force
```

---

## See Also

- **Main Documentation:** [README.md](../../README.md)
- **Architecture:** [governance_design.md](governance_design.md)
- **Signal Catalog:** [../models/signal_catalog.json](../models/signal_catalog.json)
- **Strategy Catalog:** [../backtest/strategy_catalog.json](../backtest/strategy_catalog.json)

---

**Maintained by:** stabilefrisur  
**Last Updated:** November 23, 2025
