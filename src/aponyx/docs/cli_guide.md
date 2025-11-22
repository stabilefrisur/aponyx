# CLI User Guide

**Aponyx CLI** simplifies systematic macro credit research workflows from 8+ manual scripts into declarative single-command execution.

## Quick Start

Run a complete research workflow:

```bash
uv run aponyx run --signal spread_momentum --strategy balanced
```

Generate a report:

```bash
uv run aponyx report --signal spread_momentum --strategy balanced
```

List available items:

```bash
uv run aponyx list signals
uv run aponyx list strategies
```

---

## Commands

### `run` — Execute Research Workflow

Execute complete or partial research pipeline for signal-strategy combinations.

**Prerequisites:** Data must be in registry (run data fetching scripts first).

**Usage:**
```bash
uv run aponyx run [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--signal` | TEXT | Required | Signal name from signal catalog |
| `--strategy` | TEXT | Required | Strategy name from strategy catalog |
| `--product` | TEXT | cdx_ig_5y | Product identifier for backtesting |
| `--data` | CHOICE | synthetic | Data source: `synthetic`, `file`, `bloomberg` |
| `--steps` | TEXT | all | Comma-separated step list |
| `--force` | FLAG | false | Force re-run even if cached outputs exist |
| `--config` | PATH | - | Load configuration from YAML file |

**Examples:**

Basic workflow:
```bash
uv run aponyx run --signal spread_momentum --strategy balanced
```

Custom data source:
```bash
uv run aponyx run --signal spread_momentum --strategy balanced --data bloomberg
```

Run specific steps:
```bash
uv run aponyx run --signal spread_momentum --strategy balanced --steps data,signal,backtest
```

Force re-run:
```bash
uv run aponyx run --signal spread_momentum --strategy balanced --force
```

Use config file:
```bash
uv run aponyx run --config examples/workflow_basic.yaml
```

**Output:**
```
Running: spread_momentum (balanced)
Inputs: cdx → Product: cdx_ig_5y
Data: synthetic

Completed 6 steps in 15.2s
Results: data/workflows/spread_momentum_balanced_20251121_143230/
```

---

### `report` — Generate Research Report

Generate comprehensive research reports from workflow results.

**Usage:**
```bash
uv run aponyx report [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--signal` | TEXT | Required | Signal name |
| `--strategy` | TEXT | Required | Strategy name |
| `--format` | CHOICE | console | Output format: `console`, `markdown`, `html` |
| `--output` | PATH | - | Custom output file path |

**Examples:**

Console summary:
```bash
uv run aponyx report --signal spread_momentum --strategy balanced
```

Generate markdown:
```bash
uv run aponyx report --signal spread_momentum --strategy balanced --format markdown
```

Save to custom location:
```bash
uv run aponyx report --signal spread_momentum --strategy balanced \
  --format html --output reports/custom.html
```

---

### `list` — Show Catalog Items

List available signals, strategies, or datasets.

**Usage:**
```bash
uv run aponyx list ITEM_TYPE
```

**Arguments:**

- `ITEM_TYPE`: One of `signals`, `strategies`, or `datasets`

**Examples:**

```bash
uv run aponyx list signals
uv run aponyx list strategies
uv run aponyx list datasets
```

**Sample Output:**

```
spread_momentum      Short-term momentum in CDX spreads
cdx_vix_gap          VIX-CDX divergence signal
cdx_etf_basis        CDX-HYG basis signal
```

---

### `clean` — Clear Cached Results

Remove cached workflow results to force fresh computation.

**Usage:**
```bash
uv run aponyx clean [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--signal` | TEXT | Clean specific signal results only |
| `--all` | FLAG | Clean all cached results |
| `--dry-run` | FLAG | Show what would be deleted without deleting |

**Examples:**

Clean specific signal:
```bash
uv run aponyx clean --signal spread_momentum
```

Clean all cached results:
```bash
uv run aponyx clean --all
```

Preview deletion:
```bash
uv run aponyx clean --all --dry-run
```

---

## Configuration Files

Configuration files use YAML format for workflow parameters.

### Basic Configuration

**File:** `workflow.yaml`
```yaml
signal: spread_momentum
strategy: balanced
data: synthetic
```

**Usage:**
```bash
uv run aponyx run --config workflow.yaml
```

### Custom Steps

**File:** `workflow_custom.yaml`
```yaml
signal: spread_momentum
strategy: balanced
data: synthetic
steps:
  - data
  - signal
  - backtest
force: true
```

### Bloomberg Data

**File:** `workflow_bloomberg.yaml`
```yaml
signal: spread_momentum
strategy: balanced
data: bloomberg
force: false
```

**Note:** Requires Bloomberg terminal connection and `xbbg` package.

### Config File Overrides

Command-line options override config file values:

```bash
uv run aponyx run --config workflow.yaml --force
```

---

## Workflow Steps

Workflows execute in this order:

1. **data** — Load market data from registry
2. **signal** — Compute signal values
3. **suitability** — Evaluate signal-product suitability
4. **backtest** — Run strategy backtest
5. **performance** — Compute extended metrics
6. **visualization** — Generate charts

**Step Dependencies:**

- `signal` requires `data`
- `suitability` requires `signal`
- `backtest` requires `signal` and `suitability`
- `performance` requires `backtest`
- `visualization` requires `backtest`

**Partial Execution:**

Run only specific steps:

```bash
uv run aponyx run --signal spread_momentum --strategy balanced \
  --steps data,signal,backtest
```

**Important:** Dependencies are NOT automatically included. If you specify `--steps backtest`, ensure `data` and `signal` have been run previously or include them in the step list.

---

## Examples

### Complete Research Workflow

1. Run full workflow:
   ```bash
   uv run aponyx run --signal spread_momentum --strategy balanced
   ```

2. Generate report:
   ```bash
   uv run aponyx report --signal spread_momentum --strategy balanced
   ```

3. View visualizations in the workflow output directory.

### Development Iteration

When developing new signals:

1. Initial run:
   ```bash
   uv run aponyx run --signal new_signal --strategy balanced
   ```

2. Modify signal logic, then re-run:
   ```bash
   uv run aponyx run --signal new_signal --strategy balanced \
     --steps signal,suitability,backtest,performance --force
   ```

3. Generate updated report:
   ```bash
   uv run aponyx report --signal new_signal --strategy balanced --format markdown
   ```

### Batch Processing

Use config files for reproducible batch processing:

```yaml
# workflow_1.yaml
signal: spread_momentum
strategy: balanced

# workflow_2.yaml
signal: cdx_vix_gap
strategy: aggressive
```

Run multiple workflows:

```bash
uv run aponyx run --config workflow_1.yaml
uv run aponyx run --config workflow_2.yaml
```

### Cleanup Workflow

1. Preview deletions:
   ```bash
   uv run aponyx clean --all --dry-run
   ```

2. Clean specific signal:
   ```bash
   uv run aponyx clean --signal old_signal
   ```

3. Clean everything:
   ```bash
   uv run aponyx clean --all
   ```

---

## Troubleshooting

### Command Not Found

**Problem:** `aponyx: command not found`

**Solution:**
- Ensure package installed: `uv pip install -e .`
- Use `uv run` prefix: `uv run aponyx run ...`
- Verify installation: `uv pip show aponyx`

### Missing Signal or Strategy

**Problem:** `No such signal: xyz`

**Solution:**
- List available items: `uv run aponyx list signals`
- Check catalog files:
  - `src/aponyx/models/signal_catalog.json`
  - `src/aponyx/backtest/strategy_catalog.json`
- Verify `"enabled": true` in catalog entry

### No Workflow Results Found

**Problem:** `No workflow results found for signal_name (strategy_name)`

**Solution:**
- Run workflow first: `uv run aponyx run --signal <name> --strategy <name>`
- Check output directory: `data/workflows/`
- Verify workflow completed successfully

### Workflow Step Failure

**Common issues:**
- **Data step:** No datasets in registry → Run data fetching workflow first
- **Signal step:** Missing market data → Check required data keys
- **Suitability step:** No spread data for product → Verify product in registry
- **Backtest step:** Date alignment issues → Check signal/spread index overlap

### Bloomberg Connection Issues

**Problem:** Bloomberg data source fails

**Solution:**
- Ensure Bloomberg terminal is running and logged in
- Verify `xbbg` installed: `uv pip install aponyx[bloomberg]`
- Test connection: `python -c "import xbbg.blp as blp; print(blp.bdh('SPX Index', 'PX_LAST'))"`
- Check Bloomberg securities config: `src/aponyx/data/bloomberg_securities.json`

### Config File Parsing Errors

**Problem:** `Failed to load config file: ...`

**Solution:**
- Validate YAML syntax online or with: `python -c "import yaml; yaml.safe_load(open('file.yaml'))"`
- Check for:
  - Incorrect indentation (use spaces, not tabs)
  - Missing colons after keys
  - Invalid list syntax
- Review example configs in `examples/` directory

### Permission Errors

**Problem:** `Permission denied` when saving outputs

**Solution:**
- Check directory permissions for:
  - `data/workflows/`
  - `reports/`
  - `logs/`
- Run with appropriate permissions or change output directories in config

---

## See Also

- **Main Documentation:** [README.md](../../README.md)
- **Architecture:** [governance_design.md](governance_design.md)
- **Signal Catalog:** [../models/signal_catalog.json](../models/signal_catalog.json)
- **Strategy Catalog:** [../backtest/strategy_catalog.json](../backtest/strategy_catalog.json)

---

**Maintained by:** stabilefrisur  
**Last Updated:** November 21, 2025
