# Contributing to Aponyx

> **Early-stage research framework** — Personal project, not community-maintained

**Breaking changes:** This project may introduce breaking changes between versions without deprecation warnings. No backward compatibility guarantees.

---

## Quick Start

### Prerequisites

- **Python 3.12** (strict requirement)
- **uv** package manager ([installation guide](https://docs.astral.sh/uv/))
- Git for version control

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/aponyx.git
cd aponyx
uv sync --extra dev --extra viz
uv run pytest  # 681 tests should pass
```

### Workflow

1. **Create branch:** `git checkout -b feat/your-feature-name`
2. **Make changes** following [code standards](#code-standards)
3. **Run checks:**
   ```bash
   uv run pytest --cov=aponyx    # Tests
   uv run ruff format src/ tests/ # Format
   uv run ruff check src/ tests/  # Lint
   uv run mypy src/               # Type check
   ```
4. **Commit** with [conventional commit format](#commit-messages)
5. **Push** and create PR

---

## Code Standards

**Primary References:**
- [Python Guidelines](src/aponyx/docs/python_guidelines.md) - Comprehensive code standards
- [Copilot Instructions](.github/copilot-instructions.md) - Architecture and patterns

### Key Requirements

**Modern Type Hints:**
```python
def process(data: dict[str, Any], filters: list[str] | None = None) -> pd.DataFrame | None:
    ...
```

**Module-Level Logging:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Loaded %d rows from %s", len(df), path)  # %-formatting
```

**NumPy Docstrings:**
```python
def compute_signal(spread: pd.Series, window: int = 20) -> pd.Series:
    """
    Compute momentum signal from spread time series.
    
    Parameters
    ----------
    spread : pd.Series
        Daily spread levels with DatetimeIndex.
    window : int, default 20
        Rolling window for normalization.
    
    Returns
    -------
    pd.Series
        Z-score normalized momentum signal.
    """
```

**Functions Over Classes:**
- Default to pure functions for transformations
- Use `@dataclass(frozen=True)` for configs/metadata
- Classes only for: state management, lifecycle, or plugin patterns

---

## Architecture

### Signal Composition (CRITICAL)

All signals = **Indicator** + **Transformation**

```json
{
  "name": "cdx_etf_basis",
  "indicator_dependencies": ["cdx_etf_spread_diff"],
  "transformations": ["z_score_20d"],
  "enabled": true
}
```

**See:** [Signal Registry Usage](src/aponyx/docs/signal_registry_usage.md)

### Workflow Configuration (YAML-Only)

```yaml
label: my_test          # Required
signal: spread_momentum # Required
product: cdx_ig_5y      # Required
strategy: balanced      # Required

# Optional overrides
securities: {cdx: cdx_hy_5y, etf: hyg}
indicator: cdx_vix_deviation_gap_20d
transformation: z_score_60d
```

**See:** [CLI Guide](src/aponyx/docs/cli_guide.md)

---

## Contributing Features

### Add Indicator

1. Add function to `src/aponyx/models/indicators.py`
2. Add entry to `indicator_catalog.json`
3. Add tests to `tests/models/test_indicators.py`

```python
def compute_my_indicator(cdx_df: pd.DataFrame, vix_df: pd.DataFrame) -> pd.Series:
    """Compute indicator in natural units (bps, ratios) - NOT normalized."""
    return cdx_df["spread"] - vix_df["level"]  # Example
```

### Add Signal

Add entry to `signal_catalog.json`:
```json
{
  "name": "my_signal",
  "indicator_dependencies": ["my_indicator"],
  "transformations": ["z_score_20d"],
  "enabled": true
}
```

### Add Strategy

Add entry to `strategy_catalog.json`:
```json
{
  "name": "my_strategy",
  "entry_threshold": 2.0,
  "exit_threshold": 1.0,
  "enabled": true
}
```

---

## Testing

**Requirements:**
- All new features need unit tests
- Maintain >85% coverage
- Fixed random seeds (seed=42)
- Test edge cases and errors

```bash
uv run pytest                              # All tests (681)
uv run pytest --cov=aponyx --cov-report=html # With coverage
uv run pytest tests/models/                # Specific module
```

---

## Commit Messages

**Format:** `<type>: <description>`

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `chore`

**Examples:**
```
feat: Add VIX-CDX divergence signal

refactor: Extract data loading to separate module

docs: Update CLI guide
```

---

## CLI Commands

```bash
# Run workflow
aponyx run examples/workflow_minimal.yaml

# Generate reports
aponyx report 0                    # Most recent
aponyx report my_test --format md  # By label

# List catalogs
aponyx list signals
aponyx list strategies
aponyx list indicators

# Clean data
aponyx clean           # Cache only
aponyx clean --all     # Everything
```

**See:** [CLI Guide](src/aponyx/docs/cli_guide.md)

---

## Pull Request Process

**Before submitting:**
1. All tests pass: `uv run pytest --cov=aponyx`
2. Code formatted: `uv run ruff format src/ tests/`
3. Linting passes: `uv run ruff check src/ tests/`
4. Type checks pass: `uv run mypy src/`
5. Documentation updated
6. `CHANGELOG.md` entry added

**PR Requirements:**
- Clear title (conventional commit format)
- Reference related issues
- Comprehensive tests
- Pass all CI checks

---

## Questions?

1. Check documentation in `src/aponyx/docs/`
2. Search closed issues
3. Open new issue (response time varies)

**Thank you for contributing!**

---

**Maintained by stabilefrisur**  
**Last Updated:** December 2, 2025
