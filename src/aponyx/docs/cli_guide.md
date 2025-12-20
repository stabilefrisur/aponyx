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

# Manage catalog configurations (edit YAML files first)
uv run aponyx catalog validate     # Check for errors
uv run aponyx catalog sync         # Regenerate JSON files

# Run parameter sweeps
uv run aponyx sweep examples/sweep_indicator.yaml --dry-run  # Preview
uv run aponyx sweep examples/sweep_backtest.yaml             # Execute
```

**Logging:** Default is WARNING. Use `-v` for DEBUG. Logs saved to `logs/aponyx_{timestamp}.log`.

## Command Reference

- **`run`** — Execute research workflow (data → signal → suitability → backtest → performance → visualization)
- **`sweep`** — Run parameter sweeps for sensitivity analysis (indicator or backtest mode)
- **`report`** — Generate multi-format reports from workflow results
- **`list`** — Show available signals, products, indicators, transformations, securities, strategies, datasets, steps, or workflows
- **`catalog`** — Manage YAML catalog files (validate, sync, migrate)
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
| `dv01_per_million_override` | float | | from product | Override product's DV01 (sensitivity analysis) |
| `transaction_cost_bps_override` | float | | from product | Override transaction cost in basis points |
| `transaction_cost_pct_override` | float | | - | Use percentage-based transaction cost mode (mutually exclusive with bps) |
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
# Product microstructure overrides (optional)
# dv01_per_million_override: 500.0
# transaction_cost_bps_override: 2.5
# transaction_cost_pct_override: 0.025  # OR use pct mode (mutually exclusive with bps)
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
Score Transform:          z_score_20d [from signal]
Signal Transform:         passthrough [from signal]
Strategy:                 balanced [config]
Data:                     synthetic [default]
Steps:                    all [default]
Force re-run:             False [default]
==============================

Completed 6 steps in 1.5s
Results: data/workflows/minimal_test_20251213_205920/
```

**With microstructure overrides:**
```
=== Workflow Configuration ===
Label:                    override_test [config]
Product:                  cdx_ig_5y [config]
...
Force re-run:             True [config]
DV01 Override:            500.0 [config]
TCost BPS Override:       3.0 [config]
==============================
```

**Source Tags:**
- `[config]` — Explicitly provided in YAML
- `[from signal]` — Resolved from signal metadata
- `[from indicator]` — Resolved from indicator metadata
- `[default]` — System default value

---

### `sweep` — Run Parameter Sweeps

Execute parameter sensitivity analysis across indicator or backtest configurations using Cartesian product of parameter values.

**Usage:**
```bash
uv run aponyx sweep <config_path> [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | FLAG | false | Preview combinations without executing evaluations |

**YAML Configuration Schema:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | ✓ | - | Sweep experiment identifier (used in output directory) |
| `description` | string | ✓ | - | Human-readable description of the experiment |
| `mode` | string | ✓ | - | Evaluation mode: `indicator` or `backtest` |
| `base.signal` | string | ✓ | - | Signal name from signal catalog |
| `base.strategy` | string | backtest only | - | Strategy name (required for backtest mode) |
| `parameters` | list | ✓ | - | Parameter overrides to sweep |
| `max_combinations` | integer | | null | Maximum combinations to test (null = unlimited) |

**Parameter Path Format:**

Parameters use dot notation paths:
- `indicator_transformation.parameters.<param>` — Indicator parameters (e.g., lookback)
- `score_transformation.parameters.<param>` — Score parameters (e.g., window)
- `signal_transformation.parameters.<param>` — Signal transformation parameters (e.g., floor, cap)
- `strategy.<param>` — Strategy parameters (backtest mode only, e.g., position_size_mm)

**Examples:**

**Indicator mode** (`sweep_indicator.yaml`):
```yaml
name: "lookback_sensitivity"
description: "Analyze impact of lookback window on indicator statistics"
mode: "indicator"

base:
  signal: "cdx_etf_basis"
  strategy: null

parameters:
  - path: "indicator_transformation.parameters.lookback"
    values: [10, 20, 40, 60]
  - path: "score_transformation.parameters.window"
    values: [20, 40]

max_combinations: null  # Test all 8 combinations
```

**Backtest mode** (`sweep_backtest.yaml`):
```yaml
name: "strategy_optimization"
description: "Find optimal entry threshold and position sizing"
mode: "backtest"

base:
  signal: "cdx_etf_basis"
  strategy: "balanced"

parameters:
  - path: "strategy.position_size_mm"
    values: [5.0, 10.0, 20.0]
  - path: "signal_transformation.parameters.floor"
    values: [-1.0, -1.5, -2.0]
  - path: "signal_transformation.parameters.cap"
    values: [1.0, 1.5, 2.0]

max_combinations: 27  # 3×3×3 = 27 combinations
```

**Run sweeps:**
```bash
# Preview combinations (no evaluation)
uv run aponyx sweep examples/sweep_indicator.yaml --dry-run

# Run full sweep
uv run aponyx sweep examples/sweep_indicator.yaml

# Run backtest sweep
uv run aponyx sweep examples/sweep_backtest.yaml
```

**Terminal Output:**
```
=== Sweep Configuration ===
Name:        lookback_sensitivity
Description: Analyze impact of lookback window on indicator statistics
Mode:        indicator
Signal:      cdx_etf_basis
Combinations: 8

Parameters:
  - indicator_transformation.parameters.lookback: [10, 20, 40, 60]
  - score_transformation.parameters.window: [20, 40]
===========================

Sweep: lookback_sensitivity: 100%|████████| 8/8 [00:02<00:00, 3.45combo/s]

=== Sweep Summary ===
Total combinations: 8
Successful:         8
Failed:             0
Success rate:       100.0%
Duration:           2.3s
Results saved:      data/sweeps/lookback_sensitivity_20251220_174958/
=====================
```

**Output Structure:**

Results saved to: `data/sweeps/{name}_{timestamp}/`

```
├── config.json      # Copy of sweep configuration
├── summary.json     # Execution metadata (timing, success/fail counts)
└── results.parquet  # Parameter combinations and metrics DataFrame
```

**Available Metrics by Mode:**

| Mode | Key Metrics |
|------|-------------|
| `indicator` | `composite_score`, `decision`, `correlation_lag_1`, `beta_lag_1`, `tstat_lag_1`, `data_health_score`, `predictive_score`, `economic_score`, `stability_score` |
| `backtest` | `sharpe_ratio`, `max_drawdown`, `hit_rate`, `n_trades`, `annualized_return`, `sortino_ratio`, `calmar_ratio`, `win_rate` |

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

### `catalog` — Manage YAML Catalog Files

Manage unified YAML catalog files for signals, strategies, and securities.

**Purpose**: The catalog system provides a single source of truth for all configuration metadata. Researchers edit human-friendly YAML files with inline comments, which are automatically synced to JSON files consumed by the codebase.

**Usage:**
```bash
uv run aponyx catalog {validate|sync|migrate} [OPTIONS]
```

**Subcommands:**

| Subcommand | Description |
|------------|-------------|
| `validate` | Check catalog YAML files for errors and cross-reference integrity |
| `sync` | Regenerate all JSON catalog files from YAML sources |
| `migrate` | One-time migration to bootstrap YAML files from existing JSON catalogs |

---

#### `catalog validate` — Validate Catalog Integrity

Check catalog YAML files for errors, duplicates, and cross-reference integrity before committing changes.

**Usage:**
```bash
uv run aponyx catalog validate
```

**Validation checks:**
- Duplicate entry names within each catalog
- Cross-references between signals and transformations
- Security references in indicator transformations
- Field constraints (sign_multiplier, sizing_mode, position_size_mm, etc.)

**Example:**
```bash
uv run aponyx catalog validate
# ✓ signals: 3 entries ... All catalog references valid.
# OR: Validation failed with 2 error(s): [signals] cdx_etf_basis: Invalid reference...
```

---

#### `catalog sync` — Sync YAML to JSON

Regenerate all JSON catalog files from YAML sources. Always validates before syncing.

**Usage:**
```bash
uv run aponyx catalog sync [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--dry-run` | FLAG | Preview changes without writing files |

**Generated JSON files:**
- `src/aponyx/models/indicator_transformation.json`
- `src/aponyx/models/score_transformation.json`
- `src/aponyx/models/signal_transformation.json`
- `src/aponyx/models/signal_catalog.json`
- `src/aponyx/backtest/strategy_catalog.json`
- `src/aponyx/data/bloomberg_securities.json`
- `src/aponyx/data/bloomberg_instruments.json`

**Example:**
```bash
uv run aponyx catalog sync --dry-run   # Preview
uv run aponyx catalog sync             # Apply
# Output: Sync complete. 1 files updated, 6 unchanged.
```

**Workflow:** Edit YAML → `validate` → `sync --dry-run` → `sync` → git commit

---

#### `catalog migrate` — Migrate JSON to YAML

One-time migration to bootstrap YAML source files from existing JSON catalogs.

**Usage:**
```bash
uv run aponyx catalog migrate [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--force` | FLAG | Overwrite existing YAML files |

**Generated YAML files:**
- `config/catalogs.yaml` - Signals, strategies, and transformations
- `config/securities.yaml` - Securities and instruments

**Example:**
```bash
uv run aponyx catalog migrate          # One-time migration
uv run aponyx catalog migrate --force  # Overwrite existing
```

**Note:** One-time operation with automatic round-trip verification. After migration, edit YAML only.

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
4. **backtest** — Simulate P&L with transaction costs (proportional sizing by default)
5. **performance** — Extended metrics (Sharpe, Sortino, attribution)
6. **visualization** — Generate interactive charts

**Dependencies:** Steps depend on previous steps. `signal` requires `data`; `backtest` requires `signal` + `suitability`; etc.

**Smart caching:** Completed steps are skipped unless `--force` is used.

### Output Structure

Results saved to: `data/workflows/{label}_{timestamp}/`

```
├── metadata.json              # Run parameters (label, signal, strategy, product, securities_used, status, timestamp)
├── signals/
│   ├── indicator.parquet      # Raw indicator output (bps, ratios)
│   ├── score.parquet          # Normalized score (z-score)
│   └── signal.parquet         # Final signal after trading rules
├── reports/
│   ├── suitability_evaluation_{timestamp}.md  # Pre-backtest analysis
│   └── performance_analysis_{timestamp}.md    # Post-backtest metrics
├── backtest/
│   ├── pnl.parquet            # P&L time series
│   └── positions.parquet      # Position time series
└── visualizations/            # Plotly charts (HTML)
    ├── equity_curve.html
    ├── drawdown.html
    ├── signal.html
    └── research_dashboard.html  # 5-panel pipeline visualization
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
4. Resolved from product metadata (`[from product]`)
5. System defaults (`[default]`)

---

## Product Microstructure

Each product has DV01 and transaction cost parameters in `bloomberg_securities.json`, applied automatically during backtesting.

| Product | DV01/MM | TCost (bps) |
|---------|---------|-------------|
| `cdx_ig_5y` | 475.0 | 1.5 |
| `cdx_ig_10y` | 875.0 | 2.0 |
| `cdx_hy_5y` | 425.0 | 8.0 |
| `itrx_eur_5y` | 475.0 | 1.5 |
| `itrx_xover_5y` | 425.0 | 7.0 |

### Runtime Overrides

```yaml
# Override for sensitivity analysis
dv01_per_million_override: 500.0         # Override DV01
transaction_cost_bps_override: 5.0        # Fixed bps mode
# OR
transaction_cost_pct_override: 0.025      # Percentage mode (mutually exclusive)
```

---

## Position Sizing Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `proportional` (default) | Position = signal × `position_size_mm` | Signal strength = conviction |
| `binary` | Full size regardless of magnitude | Only direction matters |

All default strategies use proportional sizing. Configure `sizing_mode: "binary"` in `strategy_catalog.json` to change.

### Entry Threshold

For mean-reversion strategies, `entry_threshold` requires extreme signals to enter:

| Strategy | entry_threshold |
|----------|----------------|
| `conservative` | 1.8 |
| `balanced` | 1.5 |
| `aggressive` | 1.0 |
| `experimental` | null |

---

## Common Workflows

```bash
# Production: Bloomberg data + HTML report
uv run aponyx run workflow_bloomberg.yaml
uv run aponyx report --workflow bloomberg_run --format html

# Batch processing
for config in configs/*.yaml; do uv run aponyx run "$config"; done

# Parameter sensitivity analysis
uv run aponyx sweep examples/sweep_indicator.yaml
uv run aponyx sweep examples/sweep_backtest.yaml

# Catalog management: validate → preview → sync → commit
uv run aponyx catalog validate
uv run aponyx catalog sync --dry-run
uv run aponyx catalog sync
git add config/ src/ && git commit -m "Update catalogs"

# Maintenance
uv run aponyx clean --workflows --older-than 30d
uv run aponyx clean --workflows --all --dry-run   # Preview before delete
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Command not found | `uv pip install -e .` then `uv run aponyx --help` |
| YAML parsing errors | Check indentation (spaces, not tabs), colons need space after |
| Missing required fields | Ensure `label`, `signal`, `product`, `strategy` are set |
| Invalid catalog reference | Run `uv run aponyx list signals` (or other item types) |
| Catalog validation errors | `uv run aponyx catalog validate`, fix YAML, re-validate |
| Cache issues | `uv run aponyx clean --workflows --all` |
| Debugging | `uv run aponyx -v run ...` for verbose logging |
| Sweep: strategy required | For backtest mode, `base.strategy` must be specified in config |
| Sweep: invalid parameter path | Path must start with `indicator_transformation.`, `score_transformation.`, `signal_transformation.`, or `strategy.` |

---

## See Also

- **Main Documentation:** [README.md](../../README.md)
- **Architecture:** [governance_design.md](governance_design.md)
- **YAML Catalog Sources:** [../../config/catalogs.yaml](../../config/catalogs.yaml), [../../config/securities.yaml](../../config/securities.yaml)
- **Signal Catalog:** [../models/signal_catalog.json](../models/signal_catalog.json)
- **Indicator Transformation Catalog:** [../models/indicator_transformation.json](../models/indicator_transformation.json)
- **Score Transformation Catalog:** [../models/score_transformation.json](../models/score_transformation.json)
- **Signal Transformation Catalog:** [../models/signal_transformation.json](../models/signal_transformation.json)
- **Securities Catalog:** [../data/bloomberg_securities.json](../data/bloomberg_securities.json)
- **Strategy Catalog:** [../backtest/strategy_catalog.json](../backtest/strategy_catalog.json)

---

**Maintained by:** stabilefrisur  
**Last Updated:** December 20, 2025
