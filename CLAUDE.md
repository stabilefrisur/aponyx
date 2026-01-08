# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Aponyx is a Python 3.12 systematic fixed-income research framework for developing and backtesting tactical credit overlay strategies on CDX indices. It uses a four-stage signal pipeline (Indicator → Score → Signal → Position) with YAML-based catalog management and deterministic backtesting.

## Common Commands

```bash
# Environment setup
uv sync                        # Install dependencies
uv sync --extra dev            # Include dev tools (pytest, mypy, ruff)
uv sync --extra viz            # Include Plotly visualization

# Testing
uv run pytest                  # Run all tests (~1,700+)
uv run pytest tests/models/    # Run specific module tests
uv run pytest -k "test_name"   # Run single test by name

# Code quality
uv run ruff check src/         # Lint
uv run ruff format src/ tests/ # Format
uv run mypy src/               # Type check

# CLI workflows
uv run aponyx run src/aponyx/examples/configs/01_workflow_minimal.yaml
uv run aponyx sweep src/aponyx/examples/configs/06_sweep_comprehensive.yaml
uv run aponyx list signals     # Browse catalogs
uv run aponyx catalog validate # Validate cross-references
```

## Architecture

The codebase follows a strict layered architecture with enforced import boundaries:

```
src/aponyx/
├── cli/           # Command orchestration (Click-based)
│                  # Imports: workflows, reporting, config
│                  # Cannot import: data, models, backtest, evaluation
├── workflows/     # Pipeline engine with caching and step registry
├── sweep/         # Parameter sensitivity analysis
├── data/          # Provider pattern: FileSource, BloombergSource
│                  # Channel-aware fetching with UsagePurpose
├── models/        # Four-stage signal composition
│                  # Registry-based: IndicatorTransformationRegistry, etc.
├── backtest/      # DV01-based P&L simulation
│                  # Calculator pattern: SpreadReturnCalculator, PriceReturnCalculator
├── evaluation/    # Pre-backtest (suitability) and post-backtest (performance)
├── visualization/ # Plotly charts (always return go.Figure, never call .show())
├── persistence/   # Parquet/JSON I/O with metadata
├── catalog/       # YAML catalog management and JSON sync
└── config/        # Path constants: PROJECT_ROOT, DATA_DIR, CACHE_DIR, etc.
```

## Registry Pattern

All extension points use JSON catalog registries with frozen metadata:

| Registry | Location |
|----------|----------|
| SignalRegistry | `src/aponyx/models/signal_catalog.json` |
| StrategyRegistry | `src/aponyx/backtest/strategy_catalog.json` |
| IndicatorTransformationRegistry | `src/aponyx/models/indicator_transformation.json` |
| ScoreTransformationRegistry | `src/aponyx/models/score_transformation.json` |
| SignalTransformationRegistry | `src/aponyx/models/signal_transformation.json` |

YAML source catalogs in `config/` are the single source of truth; JSON is generated via `aponyx catalog sync`.

## Four-Stage Signal Pipeline

Every signal follows this mandatory transformation sequence:

1. Indicator Transformation → Raw economic metric (bps, ratios)
2. Score Transformation → Normalization (z-score, volatility adjustment)
3. Signal Transformation → Trading rules (floor, cap, neutral_range)
4. Position Calculation → Backtest layer converts to positions

Signal sign convention: Positive → Long credit risk (buy CDX), Negative → Short credit risk.

## Data Layer

Use the provider pattern for all data fetching:

```python
from aponyx.data import fetch_security_data, FileSource, UsagePurpose

source = FileSource(RAW_DIR / "synthetic")
cdx_df = fetch_security_data(source, "cdx_ig_5y", purpose=UsagePurpose.INDICATOR)
```

Never load files directly with `pd.read_parquet()`.

## Code Style Requirements

Use modern Python 3.12 syntax exclusively:

```python
# Correct
def fetch(source: FileSource | BloombergSource) -> pd.DataFrame | None: ...
def process(signals: dict[str, pd.Series]) -> list[Result]: ...

# Wrong - do not use
from typing import Optional, Union, List, Dict
```

Always use `@dataclass(frozen=True)` for configuration objects. Module-level logging only (`logger = logging.getLogger(__name__)`), never `logging.basicConfig()` in library code.

## Path Constants

Import from `aponyx.config`:

```python
from aponyx.config import (
    PROJECT_ROOT,
    DATA_DIR,
    CACHE_DIR,
    RAW_DIR,
    DATA_WORKFLOWS_DIR,
    SIGNAL_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
)
```

## Workflow Configuration

Workflows are YAML-driven with these required fields:

```yaml
label: my_workflow      # Identifier (lowercase, letters/numbers/underscores)
signal: spread_momentum # Signal name from catalog
product: cdx_ig_5y      # Product identifier
strategy: balanced      # Strategy name from catalog
```

Optional: `indicator`, `score_transformation`, `signal_transformation`, `securities`, `data`, `steps`, `force`.

## Scripts

Utility scripts in `scripts/` (not tracked in git):

```bash
uv run python scripts/generate_synthetic.py  # Generate test data
python scripts/clean_runtime_data.py         # Clean data/, logs/, .registries/
python scripts/clean_env_cache.py            # Clean __pycache__, .pytest_cache, etc.
```

## Git Commit Format

```
<type>: <description>

feat: Add VIX-CDX divergence signal computation
fix: Handle missing data in backtest engine
refactor: Extract data loading to separate module
test: Add coverage for edge cases
chore: Update dependencies
```
