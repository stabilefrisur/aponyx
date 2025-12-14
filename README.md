# Aponyx

[![PyPI version](https://img.shields.io/pypi/v/aponyx.svg)](https://pypi.org/project/aponyx/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Early-stage research framework** — Not for production use

**A modular Python framework for developing and backtesting systematic credit strategies.**

Type-safe, reproducible research environment for tactical fixed-income strategies with clean separation between strategy logic, data infrastructure, and backtesting workflows.

## Key Features

- **CLI orchestrator** for automated end-to-end research workflows (run, report, list, clean)
- **Workflow engine** with smart caching and dependency tracking across pipeline steps
- **Type-safe data loading** with schema validation (Parquet, CSV, Bloomberg Terminal)
- **Modular signal framework** with composable transformations and registry management
- **Deterministic backtesting** with transaction cost modeling and comprehensive metrics
- **Interactive visualization** with Plotly charts (equity curves, signals, drawdown)
- **File-based persistence** with metadata tracking and versioning
- **Strategy governance** with centralized registry and configuration management
- **Multi-format reporting** with console, markdown, and HTML output

## Installation

### From PyPI (Recommended)

```bash
pip install aponyx
```

**Optional dependencies:**

```bash
# Visualization (Plotly)
pip install aponyx[viz]

# Bloomberg Terminal support (requires manual blpapi install)
pip install aponyx[bloomberg]

# Development tools
pip install aponyx[dev]
```

### From Source

Requires **Python 3.12** and [`uv`](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/stabilefrisur/aponyx.git
cd aponyx
uv sync                    # Install dependencies
uv sync --extra viz        # Include visualization
```

### Bloomberg Terminal Setup (Optional)

> **Note:** Bloomberg data loading requires an active Terminal session and manual `blpapi` installation.

1. Install `blpapi` by following the instructions here: [Bloomberg API Library](https://www.bloomberg.com/professional/support/api-library/)
2. Install Bloomberg extra: `pip install aponyx[bloomberg]`

File-based data loading (`FileSource`) works without Bloomberg dependencies.

## Quick Start

### 1. Run Analysis

**Option A: Use CLI with YAML Config (Recommended)**

Create a workflow configuration file:

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
aponyx run examples/workflow_minimal.yaml
```

**Option B: Python API**

```python
from aponyx.data import fetch_cdx, fetch_etf, FileSource
from aponyx.models import (
    IndicatorTransformationRegistry, ScoreTransformationRegistry,
    SignalTransformationRegistry, SignalRegistry, compose_signal
)
from aponyx.backtest import run_backtest, BacktestConfig
from aponyx.evaluation.performance import compute_all_metrics
from aponyx.evaluation.suitability import evaluate_signal_suitability, SuitabilityConfig
from aponyx.config import (
    INDICATOR_TRANSFORMATION_PATH, SCORE_TRANSFORMATION_PATH,
    SIGNAL_TRANSFORMATION_PATH, SIGNAL_CATALOG_PATH
)
from pathlib import Path

# Load validated market data
# FileSource uses registry.json for security-to-file mapping
source = FileSource(Path("data/raw/synthetic"))
cdx_df = fetch_cdx(source, security="cdx_ig_5y")
etf_df = fetch_etf(source, security="lqd")

# FOUR-STAGE SIGNAL COMPOSITION PIPELINE:
#   Stage 1: Indicator Transformation - Raw metric from securities (bps, ratios)
#   Stage 2: Score Transformation     - Normalization (z-score, volatility adjustment)
#   Stage 3: Signal Transformation    - Trading rules (floor, cap, neutral_range)
#   Stage 4: Position Calculation     - Handled by backtest layer

# Load all four registries
indicator_registry = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
score_registry = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
signal_trans_registry = SignalTransformationRegistry(SIGNAL_TRANSFORMATION_PATH)
signal_registry = SignalRegistry(SIGNAL_CATALOG_PATH)

# Compose signal via four-stage pipeline
market_data = {"cdx": cdx_df, "etf": etf_df}
result = compose_signal(
    signal_name="cdx_etf_basis",
    market_data=market_data,
    indicator_registry=indicator_registry,
    score_registry=score_registry,
    signal_transformation_registry=signal_trans_registry,
    signal_registry=signal_registry,
    include_intermediates=True,  # Optional: inspect intermediate stages
)
signal = result["signal"]
# result also contains: result["indicator"], result["score"] for debugging

# Evaluate signal-product suitability (optional pre-backtest assessment)
suitability_config = SuitabilityConfig(rolling_window=252)  # ~1 year daily data
suitability = evaluate_signal_suitability(signal, cdx_df["spread"], suitability_config)
print(f"Suitability: {suitability.composite_score:.2f} ({suitability.decision})")

# Run backtest with transaction costs and risk management
backtest_config = BacktestConfig(
    position_size_mm=10.0,          # $10MM notional
    sizing_mode="proportional",     # Position scales with signal (default)
    stop_loss_pct=5.0,              # Exit if PnL falls 5% below entry value
    take_profit_pct=10.0,           # Exit if PnL rises 10% above entry value
    transaction_cost_bps=1.0
)
results = run_backtest(signal, cdx_df["spread"], backtest_config)

# Compute comprehensive performance metrics
metrics = compute_all_metrics(results.pnl, results.positions)

# Analyze results
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
print(f"Total Return: ${metrics.total_return:,.0f}")
print(f"Win Rate: {metrics.hit_rate:.1%}")
```

**Bloomberg Terminal alternative:**

```python
from aponyx.data import BloombergSource
from pathlib import Path

# Both sources use identical interface
source = BloombergSource()
cdx_df = fetch_cdx(source, security="cdx_ig_5y")
```

## Command-Line Interface

Aponyx provides a **complete CLI orchestrator** for running research workflows from data loading through performance analysis.

**Get started:**

```bash
aponyx --help  # or aponyx -h
```

### Run Complete Workflow

All workflows are configured via YAML files. Create a config file with required fields:

**Minimal configuration** (`workflow.yaml`):
```yaml
label: minimal_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
```

**Complete configuration with all options**:
```yaml
label: complete_test
signal: cdx_etf_basis
product: cdx_ig_5y
strategy: balanced

# Optional: Override any transformation stage
indicator: cdx_etf_spread_diff
score_transformation: z_score_20d
signal_transformation: bounded_1_5

# Optional: Override default securities
securities:
  cdx: cdx_ig_5y
  etf: lqd
data: synthetic
steps: [data, signal, suitability, backtest, performance, visualization]
force: true
```

**Run workflows:**

```bash
# Execute full 6-step workflow with minimal config
aponyx run workflow.yaml

# Use example configs
aponyx run examples/workflow_minimal.yaml
aponyx run examples/workflow_complete.yaml
```

**Available YAML fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `label` | string | ✓ | - | Workflow label (lowercase letters, numbers, underscores; must start with letter) |
| `signal` | string | ✓ | - | Signal name from signal_catalog.json |
| `product` | string | ✓ | - | Product identifier (e.g., "cdx_ig_5y") |
| `strategy` | string | ✓ | - | Strategy name from strategy_catalog.json |
| `indicator` | string | | from signal | Override indicator transformation |
| `score_transformation` | string | | from signal | Override score transformation (normalization) |
| `signal_transformation` | string | | from signal | Override signal transformation (trading rules) |
| `securities` | dict | | from indicator | Custom security mapping |
| `data` | string | | "synthetic" | Data source (synthetic, file, bloomberg) |
| `steps` | list | | all | Specific steps to execute |
| `force` | boolean | | false | Force re-run (skip cache) |

### Generate Reports

```bash
# Console output with formatted tables (by label)
aponyx report --workflow minimal_test

# By numeric index (0 = most recent, ephemeral)
aponyx report --workflow 0

# Markdown file (default location: reports/)
aponyx report --workflow minimal_test --format markdown

# HTML file with styled formatting
aponyx report --workflow minimal_test --format html --output custom_report.html
```

Reports aggregate suitability evaluation and performance analysis with comprehensive metrics and visualizations.

### List Available Items

```bash
aponyx list signals      # View signal catalog
aponyx list strategies   # View strategy catalog
aponyx list datasets     # View data registry
aponyx list workflows    # View workflow results (sorted by timestamp, newest first)
aponyx list workflows --label minimal_test  # Filter workflows by label
```

### Clean Workflow Cache

```bash
# Preview workflow cleanup
aponyx clean --workflows --all --dry-run

# Clean workflows older than 30 days
aponyx clean --workflows --older-than 30d

# Clean specific label's workflows
aponyx clean --workflows --label minimal_test --older-than 7d
```

**Output format:**
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
===============================

Completed 6 steps in 15.2s
Skipped 0 cached steps
Results: data/workflows/minimal_test_20251202_143230/
```

**See [CLI Guide](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/cli_guide.md) for complete documentation and advanced usage.**

## Architecture

Aponyx follows a **layered architecture** with clean separation of concerns:

| Layer | Purpose | Key Modules |
|-------|---------|-------------|
| **CLI** | Command-line orchestration and user interface | `aponyx run`, `aponyx report`, `aponyx list`, `aponyx clean` |
| **Workflows** | Pipeline orchestration with dependency tracking | `WorkflowEngine`, `WorkflowConfig`, `StepRegistry`, concrete steps |
| **Reporting** | Multi-format report generation | `generate_report`, console/markdown/HTML formatters |
| **Data** | Load, validate, transform market data | `fetch_cdx`, `fetch_vix`, `fetch_etf`, `apply_transform`, `FileSource`, `BloombergSource` |
| **Models** | Four-stage signal composition pipeline | `IndicatorTransformationRegistry`, `ScoreTransformationRegistry`, `SignalTransformationRegistry`, `compose_signal` |
| **Evaluation** | Pre-backtest screening (rolling window stability) and post-backtest analysis | `evaluate_signal_suitability`, `analyze_backtest_performance`, `PerformanceRegistry` |
| **Backtest** | Simulate execution and generate P&L | `run_backtest`, `BacktestConfig`, `StrategyRegistry` |
| **Visualization** | Interactive charts and dashboards | `plot_equity_curve`, `plot_signal`, `plot_drawdown` |
| **Persistence** | Save/load data with metadata registry | `save_parquet`, `load_parquet`, `DataRegistry` |

### Data Storage

```
data/
  raw/              # Original source data (permanent)
    bloomberg/      # Bloomberg Terminal downloads
      registry.json # Security-to-file mapping
    synthetic/      # Synthetic test data
      registry.json # Security-to-file mapping
  cache/            # Temporary performance cache (security-based naming: {security}_{hash}.parquet)
  workflows/        # Timestamped workflow results ({label}_{timestamp}/)
  .registries/      # Runtime metadata (not in git)
```

### Research Workflow

**CLI-Orchestrated Pipeline:**

```
CLI Command (aponyx run)
    ↓
Workflow Engine (dependency tracking + caching)
    ↓
[Step 1] Data Layer (load, validate, transform)
    ↓
[Step 2] Models Layer (indicator computation + signal composition)
    ↓
[Step 3] Evaluation Layer (signal-product suitability)
    ↓
[Step 4] Backtest Layer (execution simulation)
    ↓
[Step 5] Evaluation Layer (performance metrics & analysis)
    ↓
[Step 6] Visualization Layer (charts)
    ↓
Reporting Layer (multi-format output)
    ↓
Persistence Layer (results + metadata)
```

## Documentation

Documentation is **included with the package** and available after installation:

```python
# Access docs programmatically
from aponyx.docs import get_docs_dir
docs_path = get_docs_dir()
print(docs_path)  # Path to installed documentation
```

### Getting Started

| Document | Description |
|----------|-------------|
| [`cli_guide.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/cli_guide.md) | Complete CLI orchestrator reference and advanced usage |
| [`cdx_overlay_strategy.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/cdx_overlay_strategy.md) | Investment thesis and pilot signal implementations |

### Research Workflow

| Document | Description |
|----------|-------------|
| [`signal_registry_usage.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/signal_registry_usage.md) | Signal management and catalog workflow |
| [`signal_suitability_design.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/signal_suitability_design.md) | Pre-backtest signal-product evaluation framework |
| [`performance_evaluation_design.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/performance_evaluation_design.md) | Post-backtest performance analysis framework |

### System Architecture

| Document | Description |
|----------|-------------|
| [`governance_design.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/governance_design.md) | Registry, catalog, and config governance patterns |
| [`visualization_design.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/visualization_design.md) | Chart architecture and Plotly/Streamlit patterns |
| [`logging_design.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/logging_design.md) | Logging conventions and metadata tracking |

### Development Reference

| Document | Description |
|----------|-------------|
| [`python_guidelines.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/python_guidelines.md) | Code standards, type hints, and best practices |
| [`adding_data_providers.md`](https://github.com/stabilefrisur/aponyx/blob/master/src/aponyx/docs/adding_data_providers.md) | Data provider extension guide |

**All documentation** is included in the package and available on [GitHub](https://github.com/stabilefrisur/aponyx/tree/master/src/aponyx/docs).

## What's Included

**Three pilot signals for CDX overlay strategies (via four-stage composition):**
1. **CDX-ETF Basis** - Flow-driven mispricing from cash-derivative basis
2. **CDX-VIX Gap** - Cross-asset risk sentiment divergence
3. **Spread Momentum** - Short-term continuation in credit spreads

**Four-stage transformation pipeline:**
- Stage 1: Indicator Transformation (raw metric in interpretable units)
- Stage 2: Score Transformation (z-score, volatility adjustment)
- Stage 3: Signal Transformation (floor, cap, neutral range)
- Stage 4: Position Calculation (backtest layer)

**Core capabilities:** Type-safe data loading • Signal registry • Pre/post-backtest evaluation • Deterministic backtesting • Interactive visualizations

## Development

### Running Tests

```bash
pytest                              # All tests
pytest --cov=aponyx                # With coverage
pytest tests/models/                # Specific module
```

### Code Quality

```bash
ruff format src/ tests/             # Format code
ruff check src/ tests/              # Lint
mypy src/                          # Type check
```

All tools are configured in `pyproject.toml` with project-specific settings.

## Design Philosophy

### Core Principles

1. **Modularity** - Clean separation between data, models, backtest, and infrastructure
2. **Reproducibility** - Deterministic outputs with seed control and metadata logging
3. **Type Safety** - Strict type hints and runtime validation throughout
4. **Simplicity** - Prefer functions over classes, explicit over implicit
5. **Transparency** - Clear separation between strategy logic and execution
6. **No Legacy Support** - Breaking changes without deprecation warnings; always use latest patterns

### Signal Convention

All signals follow a **consistent sign convention** for interpretability:
- **Positive values** → Long credit risk (buy CDX = sell protection)
- **Negative values** → Short credit risk (sell CDX = buy protection)

This ensures clarity when evaluating signals independently or combining them in future research.

## Requirements

- **Python 3.12** (no backward compatibility with 3.11 or earlier)
- Modern type syntax (`str | None`, not `Optional[str]`)
- Optional: Bloomberg Terminal with `blpapi` for live data

**Breaking changes:** This is an early-stage project under active development. Breaking changes may occur between versions without deprecation warnings or backward compatibility.

## Contributing

This is an early-stage personal research project. See [CONTRIBUTING.md](CONTRIBUTING.md) for technical guidelines if you'd like to contribute.

## Security

Security issues addressed on a best-effort basis. See [SECURITY.md](SECURITY.md) for reporting guidelines and scope.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- **PyPI**: https://pypi.org/project/aponyx/
- **Repository**: https://github.com/stabilefrisur/aponyx
- **Issues**: https://github.com/stabilefrisur/aponyx/issues
- **Changelog**: https://github.com/stabilefrisur/aponyx/blob/master/CHANGELOG.md

---

**Maintained by stabilefrisur**  
**Version**: 0.1.16 | **Last Updated**: December 13, 2025