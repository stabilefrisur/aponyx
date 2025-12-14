# Contributing to Aponyx

> Personal research project. May introduce breaking changes without deprecation warnings.

## Setup

**Requirements:** Python 3.12, [uv](https://docs.astral.sh/uv/), Git

```bash
git clone https://github.com/YOUR_USERNAME/aponyx.git
cd aponyx
uv sync --extra dev --extra viz
uv run pytest
```

## Development Workflow

```bash
git checkout -b feat/your-feature-name

# Make changes, then run checks
uv run pytest --cov=aponyx
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run mypy src/

# Commit (conventional format: feat/fix/docs/refactor/test/perf/chore)
git commit -m "feat: Add new signal"
```

## Code Standards

- **Type hints:** `str | None`, `dict[str, Any]` (PEP 604/585)
- **Logging:** `logger = logging.getLogger(__name__)` at module level
- **Docstrings:** NumPy format
- **Configs:** `@dataclass(frozen=True)` with `__post_init__` validation
- **Visualization:** Return `go.Figure`, never auto-display

Full details: [Python Guidelines](src/aponyx/docs/python_guidelines.md), [Copilot Instructions](.github/copilot-instructions.md)

## Architecture

### Four-Stage Signal Pipeline

All signals use: **Indicator Transformation** → **Score Transformation** → **Signal Transformation**

```json
{
  "name": "spread_momentum",
  "indicator_transformation": "spread_momentum_5d",
  "score_transformation": "volatility_adjust_20d",
  "signal_transformation": "passthrough",
  "sign_multiplier": 1,
  "enabled": true
}
```

### Workflow Configuration

```yaml
label: my_test
signal: spread_momentum
product: cdx_ig_5y
strategy: balanced
```

## Adding Features

### New Signal

1. Add indicator function to `src/aponyx/models/indicators.py`
2. Add entry to `indicator_transformation.json`
3. Add signal entry to `signal_catalog.json`
4. Add tests

### New Strategy

Add to `strategy_catalog.json`:
```json
{
  "name": "my_strategy",
  "position_size_mm": 10.0,
  "sizing_mode": "proportional",
  "stop_loss_pct": 5.0,
  "take_profit_pct": 10.0,
  "transaction_cost_bps": 1.0,
  "dv01_per_million": 475.0,
  "enabled": true
}
```

## CLI

```bash
aponyx run examples/workflow_minimal.yaml
aponyx report 0 --format md
aponyx list signals
aponyx clean --all
```

## Pull Requests

Before submitting: all tests pass, code formatted/linted, types checked, CHANGELOG.md updated.

---

**Maintained by stabilefrisur** | Last Updated: December 13, 2025
