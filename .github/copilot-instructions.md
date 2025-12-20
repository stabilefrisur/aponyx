# Copilot Instructions for Aponyx

> Last Updated: December 20, 2025 | Version 0.1.21

**Aponyx** is a Python 3.12 systematic fixed-income research framework for developing and backtesting tactical credit overlay strategies on CDX indices.

---

## Quick Start

```bash
# Environment
uv sync                    # Install dependencies
uv sync --extra dev        # Include dev tools

# Quality
uv run pytest              # Run tests (900+)
uv run mypy src/           # Type checking
uv run ruff check src/     # Linting

# Workflows
uv run aponyx run examples/workflow_minimal.yaml
uv run aponyx list signals
```

---

## Essential Patterns

### Modern Python (REQUIRED)

```python
# Union types (PEP 604) - NOT Optional[str]
def fetch(source: FileSource | BloombergSource) -> pd.DataFrame | None: ...

# Built-in generics (PEP 585) - NOT Dict[str, Any]
def process(signals: dict[str, pd.Series]) -> list[Result]: ...

# Frozen dataclasses with validation
@dataclass(frozen=True)
class Config:
    param: float
    def __post_init__(self) -> None:
        if self.param < 0:
            raise ValueError("param must be non-negative")
```

### Four-Stage Signal Pipeline (MANDATORY)

Every signal goes through this pipeline - no exceptions:

1. **Indicator Transformation** → Raw economic metric (bps, ratios)
2. **Score Transformation** → Normalize to common scale (z-score)
3. **Signal Transformation** → Trading rules (floor, cap, neutral_range)
4. **Position Calculation** → Backtest layer converts to positions

```python
signal = compose_signal(
    signal_name="cdx_etf_basis",
    market_data={"cdx": cdx_df, "etf": etf_df},
    indicator_registry=indicator_reg,
    score_registry=score_reg,
    signal_transformation_registry=signal_trans_reg,
    signal_registry=signal_reg,
)
```

### Signal Sign Convention

- **Positive** → Long credit risk (buy CDX = sell protection)
- **Negative** → Short credit risk (sell CDX = buy protection)

### Visualization

```python
def plot_chart(data: pd.Series) -> go.Figure:
    fig = px.line(x=data.index, y=data.values)
    return fig  # NEVER call .show() - caller decides
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)  # Module-level, never basicConfig()
```

---

## Project Structure

```
src/aponyx/
├── cli/          # Command-line interface (zero business logic)
├── workflows/    # Pipeline orchestration with caching
├── data/         # Provider pattern (File, Bloomberg) with validation
├── models/       # Four-stage signal composition
├── backtest/     # DV01-based P&L simulation
├── evaluation/   # Pre/post-backtest analysis
├── visualization/ # Plotly charts (return figures)
└── persistence/  # Parquet/JSON I/O

data/
├── raw/          # Source data (synthetic/, bloomberg/)
├── cache/        # TTL cache (1 day default)
├── workflows/    # Timestamped workflow outputs
└── .registries/  # Runtime metadata (not in git)
```

### Layer Import Boundaries

| Layer | Can Import From | Cannot Import From |
|-------|-----------------|-------------------|
| cli/ | workflows, reporting, config | data, models, backtest, evaluation |
| data/ | config, persistence | models, backtest, evaluation |
| models/ | config, data (schemas) | backtest, evaluation, visualization |
| backtest/ | config, models (protocols) | data, evaluation, visualization |
| visualization/ | None (generic DataFrames) | All business logic |

---

## Registry Pattern

All extensibility uses JSON catalog registries with frozen metadata:

| Registry | Location | Purpose |
|----------|----------|---------|
| SignalRegistry | `src/aponyx/models/signal_catalog.json` | Signal definitions |
| StrategyRegistry | `src/aponyx/backtest/strategy_catalog.json` | Strategy configs |
| IndicatorTransformationRegistry | `src/aponyx/models/indicator_transformation.json` | Indicators |
| ScoreTransformationRegistry | `src/aponyx/models/score_transformation.json` | Normalizations |
| SignalTransformationRegistry | `src/aponyx/models/signal_transformation.json` | Trading rules |

---

## Development Scaffolds

For detailed implementation guides, use these prompts:

| Prompt | Description |
|--------|-------------|
| `/add-signal` | Create a new signal (four-stage pipeline) |
| `/add-strategy` | Create a new backtest strategy |
| `/add-workflow-step` | Create a new workflow step |
| `/add-data-provider` | Create a new data provider |

Or switch to the **Aponyx Development** agent for guided feature development.

---

## Git Commit Standards

```
<type>: <description>

feat: Add VIX-CDX divergence signal computation
fix: Handle missing data in backtest engine
refactor: Extract data loading to separate module
docs: Update signal registry documentation
test: Add coverage for edge cases
chore: Update dependencies
```

---

## Prohibited Patterns

```python
# ❌ Old-style type hints
from typing import Optional, Union, List, Dict

# ❌ Classes for simple transformations
class DataProcessor:
    def process(self, data): ...

# ❌ Auto-display in visualization
fig.show()  # Let caller decide

# ❌ Direct file loading
pd.read_parquet("data/raw/cdx.parquet")
# ✅ Use provider pattern
fetch_cdx(FileSource(Path("data/raw/synthetic")))

# ❌ Mutable configs
@dataclass  # Missing frozen=True

# ❌ Library logging config
logging.basicConfig(level=logging.INFO)
```

---

## Key Constants

```python
from aponyx.config import (
    PROJECT_ROOT,
    DATA_DIR,
    CACHE_DIR,
    DATA_WORKFLOWS_DIR,
    SIGNAL_CATALOG_PATH,
    STRATEGY_CATALOG_PATH,
)
```

---

## Workflow

1. **Understand** — Read relevant files and patterns
2. **Plan** — Break into discrete, testable steps
3. **Implement** — Follow conventions strictly
4. **Validate** — Run tests and type checks
5. **Document** — Only for new public APIs

**Communication style:** No decorative emojis unless requested.
