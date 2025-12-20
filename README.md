# Aponyx

[![PyPI version](https://img.shields.io/pypi/v/aponyx.svg)](https://pypi.org/project/aponyx/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Early-stage research framework** — Not for production use

Modular Python framework for developing and backtesting systematic credit strategies with type-safe data loading, four-stage signal composition, and deterministic backtesting.

## Key Features

- **CLI orchestrator** — Automated end-to-end workflows (run, sweep, report, list, catalog, clean)
- **Parameter sweeps** — Systematic sensitivity analysis with indicator and backtest modes
- **YAML catalog management** — Single source of truth with JSON generation for runtime
- **Four-stage signal pipeline** — Indicator → Score → Signal → Position with composable transformations
- **Type-safe data loading** — Schema validation for Parquet/CSV/Bloomberg Terminal
- **Deterministic backtesting** — Transaction costs, risk controls, comprehensive metrics
- **Interactive visualization** — Plotly charts (equity curves, signals, drawdowns, dashboards)
- **File-based persistence** — Metadata tracking with versioning

## Installation

### From PyPI

```bash
pip install aponyx
```

**Optional dependencies:**

```bash
pip install aponyx[viz]         # Plotly visualization
pip install aponyx[bloomberg]   # Bloomberg Terminal (requires manual blpapi install)
pip install aponyx[dev]         # Development tools
```

### From Source

Requires **Python 3.12** and [`uv`](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/stabilefrisur/aponyx.git
cd aponyx
uv sync                         # Install dependencies
uv sync --extra viz             # Include visualization
```

### Bloomberg Terminal Setup (Optional)

Bloomberg data loading requires active Terminal session and manual `blpapi` installation:

1. Install `blpapi`: [Bloomberg API Library](https://www.bloomberg.com/professional/support/api-library/)
2. Install extra: `pip install aponyx[bloomberg]`

File-based data loading (`FileSource`) works without Bloomberg dependencies.

## Quick Start

### Run Analysis with YAML Config

Create a workflow configuration:

```yaml
# workflow.yaml
label: my_test
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced
```

Run the workflow:

```bash
aponyx run workflow.yaml
# Or use example configs
aponyx run src/aponyx/examples/configs/01_workflow_minimal.yaml
```

### Python API

```python
from datetime import datetime, timedelta
from aponyx.data import (
    fetch_cdx, fetch_vix, fetch_etf,
    BloombergSource,
    get_product_microstructure
)
from aponyx.models import SignalRegistry, compute_registered_signals
from aponyx.backtest import run_backtest, BacktestConfig, resolve_calculator
from aponyx.evaluation.performance import compute_all_metrics
from aponyx.config import SIGNAL_CATALOG_PATH

# Fetch market data from Bloomberg Terminal
source = BloombergSource()
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=5 * 365)).strftime("%Y-%m-%d")

cdx_df = fetch_cdx(source, security="cdx_ig_5y", start_date=start_date, end_date=end_date)
etf_df = fetch_etf(source, security="lqd", start_date=start_date, end_date=end_date)
vix_df = fetch_vix(source, start_date=start_date, end_date=end_date)

# Compute signals from catalog
signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)
market_data = {"cdx": cdx_df, "etf": etf_df, "vix": vix_df}
signals = compute_registered_signals(signal_registry, market_data)
signal = signals["spread_momentum"]

# Get product microstructure and calculator
microstructure = get_product_microstructure("cdx_ig_5y")
calculator = resolve_calculator(
    quote_type=microstructure.quote_type,
    dv01_per_million=microstructure.dv01_per_million,
)

# Run backtest
backtest_config = BacktestConfig(
    position_size_mm=10.0,
    sizing_mode="proportional",
    stop_loss_pct=5.0,
    take_profit_pct=10.0,
    max_holding_days=20,
    transaction_cost_bps=microstructure.transaction_cost_bps
)
results = run_backtest(signal, cdx_df["spread"], backtest_config, calculator)

# Compute performance metrics
metrics = compute_all_metrics(results.pnl, results.positions)
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Total Return: ${metrics.total_return:,.0f}")
print(f"Win Rate: {metrics.hit_rate:.1%}")
```

**Alternative: Using synthetic data (no Bloomberg required)**

```python
from aponyx.data import fetch_cdx, fetch_vix, fetch_etf, FileSource
from aponyx.config import RAW_DIR

# Load from synthetic data
source = FileSource(RAW_DIR / "synthetic")
cdx_df = fetch_cdx(source, security="cdx_ig_5y")
etf_df = fetch_etf(source, security="lqd")
vix_df = fetch_vix(source, security="vix")

# ... rest of code identical
```

## Command-Line Interface

```bash
aponyx --help  # View all commands
```

**Core commands:**
- `run` — Execute complete workflow from YAML config
- `sweep` — Run parameter sensitivity analysis
- `report` — Generate multi-format analysis reports
- `list` — Browse signals, strategies, datasets, workflows
- `catalog` — Manage YAML catalogs (validate, sync, migrate)
- `clean` — Remove cached workflow results

### Run Workflow

All workflows configured via YAML:

**Minimal** (`workflow.yaml`):
```yaml
label: minimal_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
```

**Complete with overrides**:
```yaml
label: complete_test
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced

# Override transformation stages
indicator: cdx_etf_spread_diff
score_transformation: z_score_20d
signal_transformation: bounded_1_5

# Override securities
securities:
  cdx: cdx_ig_5y
  etf: lqd

data: synthetic
steps: [data, signal, suitability, backtest, performance, visualization]
force: true
```

**Run:**

```bash
aponyx run workflow.yaml
# Or use examples
aponyx run src/aponyx/examples/configs/01_workflow_minimal.yaml
```

**YAML fields:**

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `label` | ✓ | - | Workflow identifier (lowercase, letters/numbers/underscores) |
| `signal` | ✓ | - | Signal name from catalog |
| `product` | ✓ | - | Product identifier (e.g., "cdx_ig_5y") |
| `strategy` | ✓ | - | Strategy name from catalog |
| `indicator` | | from signal | Override indicator transformation |
| `score_transformation` | | from signal | Override normalization |
| `signal_transformation` | | from signal | Override trading rules |
| `securities` | | from indicator | Custom security mapping |
| `data` | | "synthetic" | Data source (synthetic/file/bloomberg) |
| `steps` | | all | Specific steps to execute |
| `force` | | false | Bypass cache |

### Run Parameter Sweeps

Test parameter combinations systematically:

```bash
aponyx sweep src/aponyx/examples/configs/04_sweep_indicator_lookback.yaml
aponyx sweep src/aponyx/examples/configs/05_sweep_strategy_optimization.yaml --dry-run
```

**Sweep configuration:**

```yaml
name: indicator_lookback_sweep
description: Test indicator lookback windows
evaluation_mode: indicator  # or 'backtest'
base_signal: spread_momentum
base_product: cdx_ig_5y
parameter_overrides:
  - path: indicator_transformation.parameters.lookback
    values: [5, 10, 20, 40]
max_combinations: 50
```

**Output:** `data/sweeps/indicator_lookback_sweep_YYYYMMDD_HHMMSS/`
- `results.parquet` — Metrics for each combination
- `config.yaml` — Configuration copy
- `summary.json` — Metadata and statistics

### Other Commands

**Generate reports:**
```bash
aponyx report --workflow minimal_test                    # Console output
aponyx report --workflow 0 --format markdown             # Most recent, markdown
aponyx report --workflow minimal_test --format html      # HTML with styling
```

**List available items:**
```bash
aponyx list signals      # Signal catalog
aponyx list strategies   # Strategy catalog
aponyx list workflows    # Workflow results (newest first)
```

**Manage catalogs:**
```bash
aponyx catalog validate  # Validate cross-references
aponyx catalog sync      # Regenerate JSON from YAML
```

**Clean cache:**
```bash
aponyx clean --workflows --all --dry-run              # Preview cleanup
aponyx clean --workflows --older-than 30d             # Remove old workflows
aponyx clean --workflows --label minimal_test --older-than 7d
```

See [CLI Guide](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/cli_guide.md) for complete documentation.

## Architecture

| Layer | Purpose | Key Components |
|-------|---------|----------------|
| **CLI** | Command orchestration | `run`, `sweep`, `report`, `list`, `catalog`, `clean` |
| **Workflows** | Pipeline execution with caching | `WorkflowEngine`, step registry |
| **Sweep** | Parameter sensitivity analysis | `SweepEngine`, evaluators |
| **Reporting** | Multi-format output | Console/markdown/HTML formatters |
| **Data** | Load and validate market data | `FileSource`, `BloombergSource`, `DataRegistry` |
| **Models** | Four-stage signal composition | Indicator/Score/Signal transformations |
| **Evaluation** | Pre/post-backtest analysis | Suitability, performance metrics |
| **Backtest** | Execution simulation | `run_backtest`, `BacktestConfig` |
| **Visualization** | Charts and dashboards | `plot_equity_curve`, `plot_research_dashboard` |
| **Persistence** | File I/O with metadata | Parquet/JSON save/load |

### Data Storage

```
data/
  raw/              # Source data (permanent)
    bloomberg/
    synthetic/
  cache/            # Temporary cache (TTL-based)
  workflows/        # Timestamped workflow results
  sweeps/           # Parameter sweep experiments
  .registries/      # Runtime metadata (not in git)
```

### Research Workflow

**CLI-Orchestrated Pipeline:**

```
CLI Command (aponyx run)
    ↓
Workflow Engine (dependency tracking + caching)
    ↓
[Step 1] DataStep (load, validate, transform)
    ↓
[Step 2] SignalStep (indicator computation + signal composition)
    ↓
[Step 3] SuitabilityStep (signal-product suitability evaluation)
    ↓
[Step 4] BacktestStep (execution simulation)
    ↓
[Step 5] PerformanceStep (performance metrics & analysis)
    ↓
[Step 6] VisualizationStep (charts + research dashboard)
    ↓
Reporting Layer (multi-format output)
    ↓
Persistence Layer (results + metadata)
```

## Documentation

Documentation is included in the package and available on [GitHub](https://github.com/stabilefrisur/aponyx/tree/master/src/aponyx/docs).

### Core Guides

- [**CLI Guide**](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/cli_guide.md) — Complete CLI reference
- [**CDX Overlay Strategy**](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/cdx_overlay_strategy.md) — Investment thesis
- [**Signal Registry Usage**](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/signal_registry_usage.md) — Catalog workflow

### Design Docs

- [Signal Suitability](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/signal_suitability_design.md) — Pre-backtest evaluation
- [Performance Evaluation](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/performance_evaluation_design.md) — Post-backtest analysis
- [Governance](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/governance_design.md) — Registry patterns
- [Visualization](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/visualization_design.md) — Chart architecture
- [Python Guidelines](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/python_guidelines.md) — Code standards

## What's Included

**Three pilot signals via four-stage composition:**
1. **CDX-ETF Basis** — Cash-derivative basis mispricing
2. **CDX-VIX Gap** — Risk sentiment divergence
3. **Spread Momentum** — Short-term credit continuation

**Four-stage pipeline:**
1. Indicator → Raw metric (bps, ratios)
2. Score → Normalization (z-score, volatility adjustment)
3. Signal → Trading rules (floor, cap, neutral range)
4. Position → Backtest layer

**Core capabilities:** Type-safe data loading • Signal composition • Pre/post-backtest evaluation • Deterministic backtesting • Interactive charts

## Development

### Testing

```bash
pytest                    # All tests
pytest --cov=aponyx      # With coverage
pytest tests/models/     # Specific module
```

### Code Quality

```bash
uv run ruff format src/ tests/    # Format code
uv run ruff check src/ tests/     # Lint
uv run mypy src/                  # Type check
```

## Design Philosophy

1. **Modularity** — Clean layer separation
2. **Reproducibility** — Deterministic outputs with metadata
3. **Type Safety** — Strict type hints and validation
4. **Simplicity** — Functions over classes
5. **No Legacy Support** — Breaking changes without deprecation

**Signal convention:**
- **Positive** → Long credit risk (buy CDX = sell protection)
- **Negative** → Short credit risk (sell CDX = buy protection)

## Requirements

- **Python 3.12** (modern type syntax: `str | None`, not `Optional[str]`)
- Optional: Bloomberg Terminal with `blpapi` for live data

Early-stage project under active development. Breaking changes may occur between versions.

## Contributing

Early-stage personal research project. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

Best-effort security support. See [SECURITY.md](SECURITY.md) for reporting guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- **PyPI**: https://pypi.org/project/aponyx/
- **Repository**: https://github.com/stabilefrisur/aponyx
- **Issues**: https://github.com/stabilefrisur/aponyx/issues
- **Changelog**: https://github.com/stabilefrisur/aponyx/blob/master/CHANGELOG.md

---

**Maintained by stabilefrisur**  
**Version**: 0.1.20 | **Last Updated**: December 20, 2025