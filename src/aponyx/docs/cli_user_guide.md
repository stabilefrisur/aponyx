# CLI User Guide

**Aponyx CLI** provides command-line tools for running systematic macro credit research workflows.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [run](#run-command)
  - [report](#report-command)
  - [list](#list-command)
  - [clean](#clean-command)
- [Configuration Files](#configuration-files)
- [Workflow Steps](#workflow-steps)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Installation

Install the package with CLI support:

```bash
pip install aponyx
```

Or install from source in development mode:

```bash
git clone https://github.com/stabilefrisur/aponyx.git
cd aponyx
pip install -e .
```

Verify installation:

```bash
aponyx --help
```

---

## Quick Start

Run a complete research workflow:

```bash
aponyx run --signal spread_momentum --strategy balanced
```

Generate a report from results:

```bash
aponyx report --signal spread_momentum --strategy balanced
```

List available signals and strategies:

```bash
aponyx list signals
aponyx list strategies
```

---

## Commands

### `run` Command

Execute research workflows for signal-strategy combinations.

**Usage:**
```bash
aponyx run [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--signal` | TEXT | Required | Signal name from signal catalog |
| `--strategy` | TEXT | Required | Strategy name from strategy catalog |
| `--data` | CHOICE | synthetic | Data source: `synthetic`, `file`, `bloomberg` |
| `--steps` | TEXT | all | Comma-separated step list (e.g., `data,signal,backtest`) |
| `--force` | FLAG | false | Force re-run even if cached outputs exist |
| `--config` | PATH | - | Load configuration from YAML file |

**Examples:**

Basic workflow:
```bash
aponyx run --signal spread_momentum --strategy balanced
```

Custom data source:
```bash
aponyx run --signal spread_momentum --strategy balanced --data bloomberg
```

Run specific steps:
```bash
aponyx run --signal spread_momentum --strategy balanced --steps data,signal,backtest
```

Force re-run:
```bash
aponyx run --signal spread_momentum --strategy balanced --force
```

Use config file:
```bash
aponyx run --config examples/workflow_basic.yaml
```

Override config file options:
```bash
aponyx run --config examples/workflow_basic.yaml --force
```

---

### `report` Command

Generate comprehensive research reports from workflow results.

**Usage:**
```bash
aponyx report [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--signal` | TEXT | Required | Signal name |
| `--strategy` | TEXT | Required | Strategy name |
| `--format` | CHOICE | console | Output format: `console`, `markdown`, `html` |
| `--output` | PATH | - | Custom output file path |

**Examples:**

Console output:
```bash
aponyx report --signal spread_momentum --strategy balanced
```

Generate markdown:
```bash
aponyx report --signal spread_momentum --strategy balanced --format markdown
```

Save to custom location:
```bash
aponyx report --signal spread_momentum --strategy balanced --format html --output my_report.html
```

---

### `list` Command

List available catalog items.

**Usage:**
```bash
aponyx list ITEM_TYPE
```

**Arguments:**

- `ITEM_TYPE`: One of `signals`, `strategies`, or `datasets`

**Examples:**

```bash
aponyx list signals
aponyx list strategies
aponyx list datasets
```

**Sample Output:**

```
Available Signals:
  • spread_momentum     — Short-term momentum in CDX spreads
  • cdx_vix_gap         — VIX-CDX divergence signal
  • cdx_etf_basis       — CDX-HYG basis signal
```

---

### `clean` Command

Clear cached workflow results to force fresh computation.

**Usage:**
```bash
aponyx clean [OPTIONS]
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
aponyx clean --signal spread_momentum
```

Clean all cached results:
```bash
aponyx clean --all
```

Preview deletion (dry run):
```bash
aponyx clean --all --dry-run
```

---

## Configuration Files

Configuration files use YAML format and allow you to define workflow parameters without command-line options.

### Basic Configuration

**File:** `workflow.yaml`
```yaml
signal: spread_momentum
strategy: balanced
data: synthetic
```

**Usage:**
```bash
aponyx run --config workflow.yaml
```

### Custom Steps Configuration

**File:** `workflow_custom.yaml`
```yaml
signal: spread_momentum
strategy: balanced
data: synthetic

# Only run specific steps
steps:
  - data
  - signal
  - backtest

# Force re-run
force: true
```

**Usage:**
```bash
aponyx run --config workflow_custom.yaml
```

### Bloomberg Data Configuration

**File:** `workflow_bloomberg.yaml`
```yaml
signal: spread_momentum
strategy: balanced
data: bloomberg
force: false
```

**Usage:**
```bash
aponyx run --config workflow_bloomberg.yaml
```

**Note:** Requires Bloomberg terminal connection and `xbbg` package.

### Config File + CLI Override

Command-line options override config file values:

```bash
aponyx run --config workflow.yaml --force
```

This loads settings from `workflow.yaml` but forces re-run regardless of the `force` value in the file.

---

## Workflow Steps

Workflows execute in the following order:

1. **data** — Load market data from registry
2. **signal** — Compute signal values
3. **suitability** — Evaluate signal-product suitability
4. **backtest** — Run strategy backtest
5. **performance** — Compute extended metrics
6. **visualization** — Generate charts

### Step Dependencies

- `signal` requires `data`
- `suitability` requires `signal`
- `backtest` requires `signal` and `suitability`
- `performance` requires `backtest`
- `visualization` requires `backtest`

### Partial Workflow Execution

Run only specific steps:

```bash
aponyx run --signal spread_momentum --strategy balanced --steps data,signal,backtest
```

**Important:** Dependencies are NOT automatically included. If you specify `--steps backtest`, you must ensure `data` and `signal` have been run previously or include them in the step list.

---

## Examples

### Complete Research Workflow

1. **Run full workflow:**
   ```bash
   aponyx run --signal spread_momentum --strategy balanced
   ```

2. **Generate report:**
   ```bash
   aponyx report --signal spread_momentum --strategy balanced
   ```

3. **View visualizations:**
   Navigate to workflow output directory shown in results.

### Development Iteration

When developing new signals, you may want to re-run specific steps:

1. **Initial run:**
   ```bash
   aponyx run --signal new_signal --strategy balanced
   ```

2. **Modify signal logic, then re-run signal step:**
   ```bash
   aponyx run --signal new_signal --strategy balanced --steps signal,suitability,backtest,performance --force
   ```

3. **Generate updated report:**
   ```bash
   aponyx report --signal new_signal --strategy balanced --format markdown
   ```

### Batch Processing

Use config files for reproducible batch processing:

```bash
# workflow_1.yaml
signal: spread_momentum
strategy: balanced

# workflow_2.yaml
signal: cdx_vix_gap
strategy: aggressive
```

Run multiple workflows:

```bash
aponyx run --config workflow_1.yaml
aponyx run --config workflow_2.yaml
```

### Cleanup Workflow

Clear stale cached results:

1. **Preview what will be deleted:**
   ```bash
   aponyx clean --all --dry-run
   ```

2. **Clean specific signal:**
   ```bash
   aponyx clean --signal old_signal
   ```

3. **Clean everything:**
   ```bash
   aponyx clean --all
   ```

---

## Troubleshooting

### Command Not Found

**Problem:** `aponyx: command not found`

**Solution:**
- Ensure package is installed: `pip install aponyx` or `pip install -e .`
- Verify installation: `pip show aponyx`
- Check PATH includes Python scripts directory

### Missing Signal or Strategy

**Problem:** `No such signal: xyz`

**Solution:**
- List available items: `aponyx list signals` or `aponyx list strategies`
- Check signal/strategy catalog files:
  - `src/aponyx/models/signal_catalog.json`
  - `src/aponyx/backtest/strategy_catalog.json`
- Verify catalog entry is enabled: `"enabled": true`

### No Workflow Results Found

**Problem:** `No workflow results found for signal_name (strategy_name)`

**Solution:**
- Run workflow first: `aponyx run --signal <name> --strategy <name>`
- Check output directory: `data/processed/workflows/`
- Verify workflow completed successfully (no errors in log)

### Workflow Step Failure

**Problem:** Workflow fails at specific step

**Solution:**
1. **Check logs** for detailed error messages
2. **Run with verbose logging:** `aponyx --verbose run --signal <name> --strategy <name>`
3. **Common issues:**
   - **Data step:** No datasets in registry → Run data fetching workflow first
   - **Signal step:** Missing market data → Check required data keys
   - **Suitability step:** No spread data for product → Verify product in registry
   - **Backtest step:** Date alignment issues → Check signal/spread index overlap

### Bloomberg Connection Issues

**Problem:** Bloomberg data source fails

**Solution:**
- Ensure Bloomberg terminal is running and logged in
- Verify `xbbg` package installed: `pip install aponyx[bloomberg]`
- Test connection: `python -c "import xbbg.blp as blp; print(blp.bdh('SPX Index', 'PX_LAST'))"`
- Check Bloomberg securities configuration: `src/aponyx/data/bloomberg_securities.json`

### Config File Parsing Errors

**Problem:** `Failed to load config file: ...`

**Solution:**
- Validate YAML syntax: Use online validator or `python -c "import yaml; yaml.safe_load(open('file.yaml'))"`
- Check for common issues:
  - Incorrect indentation (use spaces, not tabs)
  - Missing colons after keys
  - Invalid list syntax
- Review example configs in `examples/` directory

### Permission Errors

**Problem:** `Permission denied` when saving outputs

**Solution:**
- Check directory permissions for:
  - `data/processed/`
  - `reports/`
  - `logs/`
- Run with appropriate permissions or change output directories in config

---

## Global Options

All commands support global options:

| Option | Description |
|--------|-------------|
| `--verbose`, `-v` | Enable verbose logging (DEBUG level) |
| `--quiet`, `-q` | Suppress all output except errors |
| `--help`, `-h` | Show help message and exit |

**Examples:**

```bash
aponyx --verbose run --signal spread_momentum --strategy balanced
aponyx --quiet clean --all
aponyx run --help
aponyx list -h
```

---

## Advanced Usage

### Custom Output Directories

Modify output directory in workflow config:

```python
# In code (not via CLI)
from aponyx.workflows import WorkflowConfig
from pathlib import Path

config = WorkflowConfig(
    signal_name="spread_momentum",
    strategy_name="balanced",
    output_dir=Path("custom/output/dir"),
)
```

### Programmatic Usage

Use workflows programmatically in scripts:

```python
from aponyx.workflows import WorkflowEngine, WorkflowConfig

config = WorkflowConfig(
    signal_name="spread_momentum",
    strategy_name="balanced",
    data_source="synthetic",
)

engine = WorkflowEngine(config)
results = engine.execute()

print(f"Completed {results['steps_completed']} steps")
print(f"Output: {results['output_dir']}")
```

### Integration with Notebooks

Run workflows from Jupyter notebooks:

```python
import subprocess

result = subprocess.run(
    ["aponyx", "run", "--signal", "spread_momentum", "--strategy", "balanced"],
    capture_output=True,
    text=True,
)

print(result.stdout)
```

---

## See Also

- **Main Documentation:** [README.md](../../README.md)
- **Architecture:** [governance_design.md](governance_design.md)
- **Implementation Plan:** [cli_implementation_plan.md](cli_implementation_plan.md)
- **Signal Catalog:** [src/aponyx/models/signal_catalog.json](../models/signal_catalog.json)
- **Strategy Catalog:** [src/aponyx/backtest/strategy_catalog.json](../backtest/strategy_catalog.json)

---

**Maintained by:** stabilefrisur  
**Last Updated:** November 20, 2025  
**Version:** 1.0.0
