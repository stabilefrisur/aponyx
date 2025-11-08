# Copilot Instructions — Systematic Macro Credit Project (VS Code Agent Mode)

## Purpose

These instructions optimize **Copilot Chat and inline completions** in **VS Code Agent mode** (Claude Sonnet 4.5 / GPT‑5) for the *Systematic Macro Credit* project.  
The goal is to ensure the AI assistant generates **clean, modular, and reproducible** Python code aligned with project architecture and investment research standards.

---

## Project Overview

You are working within a **systematic fixed‑income research environment**.  
The framework supports:
- Development and testing of **pilot investment strategies** (e.g., CDX overlay).
- Modular architecture for **data**, **model**, **backtest**, **visualization**, and **persistence** layers.
- Reproducible, documented, and version‑controlled research.

### Repository Layout

```
src/aponyx/
  data/               # Loaders, cleaning, transformation, validation
    providers/        # Data provider implementations (Bloomberg, etc.)
  models/             # Signal & strategy logic
  evaluation/         # Signal-product suitability assessment
  backtest/           # Backtesting engine and risk tracking
  visualization/      # Plotly & Streamlit dashboards
  persistence/        # Parquet & JSON I/O utilities
  config/             # Paths, constants, environment
  docs/               # Documentation and strategy specs
    maintenance/      # Fork/upstream sync workflows
    prompts/          # Strategy and implementation prompts
  examples/           # Example scripts and notebooks
  __init__.py         # Package initialization
  main.py             # CLI entry point / notebook runner

tests/                # Unit tests for reproducibility
  data/
  models/
  backtest/
  visualization/
  persistence/
  governance/         # Registry and catalog integration tests
.github/              # GitHub workflows and agent instructions
pyproject.toml        # Project dependencies and build system
README.md             # Project overview and setup instructions
```

---

## ⚙️ Environment Standards

- **Python:** 3.12  
- **Type Hints:** Use modern Python syntax (`str | None` instead of `Optional[str]`, `int | float` instead of `Union[int, float]`)
- **Environment:** managed with [`uv`](https://docs.astral.sh/uv/)  
- **Linting / Formatting:** `ruff`, `black`, `mypy`
- **Testing:** `pytest`
- **Docs:** `mkdocs` or `sphinx`
- **Visualization:** `plotly`, `streamlit`

All dependencies live in `pyproject.toml`.  
Use relative imports and avoid global state.

---

## Governance System

The project uses a three-pillar governance architecture:

1. **Config** (`config/`) — Import-time constants for paths, cache settings, catalog locations
2. **Registry** (`data/registry.py`) — Dataset tracking with CRUD operations (class-based, mutable)
3. **Catalog** (`models/signal_catalog.json`, `backtest/strategy_catalog.json`) — Signal and strategy definitions (class-based registries with fail-fast validation)

### Patterns

- **Import-time constants:** Static configuration (`config/__init__.py`)
- **Class-based registry:** Mutable state with CRUD (`DataRegistry`)
- **Class-based catalog:** Immutable metadata with validation (`SignalRegistry`, `StrategyRegistry`)
- **Functional pattern:** Read-only lookups with lazy loading (Bloomberg config)

See `src/aponyx/docs/governance_design.md` for complete architecture details.

### Registry vs Catalog

- **Registry** = Dataset tracking (what data files exist, where they are)
- **Catalog** = Signal/strategy definitions (what computations are available)

Both use JSON persistence but serve different purposes and have different mutability patterns.

---

## Agent Behavior Guidelines

### General
1. **Always prioritize modular, PEP 8‑compliant, type‑annotated code.**
2. **Never mix strategy logic with infrastructure code.**
3. **Always document functions and classes using NumPy‑style docstrings.**
4. **Propose structured changes — not isolated code fragments.**
5. **Assume collaboration**: other developers must read and extend your code easily.
6. **No backward compatibility required**: This is an early-stage project. Use modern best practices without legacy concerns.

### Style
- Follow **PEP 8** and **type hints** strictly.
- Use **modern Python type syntax**: `str | None` not `Optional[str]`, `int | float` not `Union[int, float]`.
- Use **built-in generics**: `list[str]` not `List[str]`, `dict[str, Any]` not `Dict[str, Any]`.
- Use **black** and **ruff** formatting conventions.
- Add **docstrings** and comments explaining rationale and data flow.
- **No decorative emojis** in code or docstrings. Only ✅ and ❌ for clarity in examples.

### Code Organization Philosophy
- **Prefer functions over classes.** Default to pure functions for transformations, calculations, and data processing.
- Only use classes when you need: (1) state management, (2) multiple related methods on shared state, (3) lifecycle management, or (4) plugin/interface patterns.
- **Use `@dataclass` for data containers** (parameters, results, metrics) — not regular classes.
- Use `@dataclass(frozen=True)` for immutable configuration/parameters.
- Avoid "calculator" or "helper" classes that just wrap a single function.

### Logging
- Use **module-level loggers**: `logger = logging.getLogger(__name__)`
- **Never** call `logging.basicConfig()` in library code.
- Use **%-formatting**: `logger.info("Loaded %d rows", len(df))` not f-strings.
- **INFO**: User-facing operations. **DEBUG**: Implementation details. **WARNING**: Recoverable errors.

### Documentation Example
```python
def compute_spread_momentum(
    cdx_df: pd.DataFrame,
    config: SignalConfig,
) -> pd.Series:
    """
    Compute short-term momentum in CDX spreads using z-score normalization.

    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX data with 'spread' column and DatetimeIndex.
    config : SignalConfig
        Signal configuration with lookback and min_periods.

    Returns
    -------
    pd.Series
        Normalized momentum signal.
        
    Notes
    -----
    Signal sign convention: positive = tightening spreads = bullish credit.
    """
```

### Documentation Structure

**Single Source of Truth Principle**: Each piece of information has exactly one authoritative location.

| Doc Type | Location | Purpose |
|----------|----------|---------|
| **API Reference** | Module docstrings | Function/class contracts, type info, parameters |
| **Quickstart** | `README.md` | Installation, quick examples, navigation |
| **Design Docs** | `src/aponyx/docs/*.md` | Architecture, standards, strategy rationale |
| **Examples** | `src/aponyx/examples/*.py` headers | Runnable demonstrations with explanatory headers |

**What to document where:**
- **Docstrings**: API contracts (parameters, returns, raises), edge cases, usage notes
- **Examples**: Workflow demonstrations with clear headers explaining purpose and expected output
- **Design docs**: Architectural decisions, cross-cutting concerns (*why*, not *how*)
- **README**: Installation, project structure, quickstart commands

**Never:**
- Create README files in implementation directories (`src/aponyx/*/README.md`)
- Duplicate API documentation outside of docstrings
- Write tutorial-style docs that duplicate runnable examples
- Document usage patterns in design docs (use examples instead)

---

## Agent Context Hints for Claude Sonnet / GPT-5

| Context | Preferred Behavior |
|----------|--------------------|  
| Editing `/config/` | Use import-time constants with `Final` type hints. No classes, no dynamic configuration. |
| Editing `/data/` | Focus on fetch functions, schema validation, and data sources. Use `DataRegistry` for dataset tracking. Support multiple providers (File, Bloomberg, API). |
| Editing `/models/` | Focus on signal functions and strategy modules. Use `SignalRegistry` for catalog management. **Signal convention: positive values = long credit risk (buy CDX).** |
| Editing `/evaluation/` | Focus on 4-component scoring (data health, predictive, economic, stability) and PASS/HOLD/FAIL decisions for signal-product pairs. Use `SuitabilityRegistry` for tracking. |
| Editing `/backtest/` | Implement transparent, deterministic backtest logic. Use `StrategyRegistry` for strategy catalog. Include metadata logging. |
| Editing `/visualization/` | Generate reusable Plotly/Streamlit components. Separate plotting from computation. |
| Editing `/persistence/` | Handle Parquet/JSON I/O. No database dependencies. Keep I/O functions pure. |
| Editing `/notebooks/` | Create workflow notebooks that work in isolation and load from previous steps. Use absolute imports (`from aponyx.config import...`). Include markdown headers explaining workflow position, prerequisites, and outputs. Format tables with `to_markdown()` for clean left-aligned display. |
| Editing `/tests/` | Write unit tests for determinism, type safety, and reproducibility. Test governance patterns separately in `tests/governance/`. |When generating code, the assistant should **infer module context from file path** and **adhere to functional boundaries** automatically.

### Signal Sign Convention (Models Layer)

**All model signals must follow a consistent sign convention:**

- **Positive signal values** → Long credit risk → Buy CDX (sell protection)
- **Negative signal values** → Short credit risk → Sell CDX (buy protection)

This convention ensures clear interpretation when:
1. Evaluating signals independently through backtests
2. Comparing performance across different signal ideas
3. Combining signals in future experiments (if needed)

**Signal naming convention:**

Use consistent signal names throughout the models layer:
- **Signal names:** `cdx_etf_basis`, `cdx_vix_gap`, `spread_momentum`
- **Function names:** `compute_cdx_etf_basis`, `compute_cdx_vix_gap`, `compute_spread_momentum`
- **Function parameters:** `cdx_etf_basis`, `cdx_vix_gap`, `spread_momentum`
- **DataFrame columns:** `cdx_etf_basis`, `cdx_vix_gap`, `spread_momentum`

**Implementation guidelines:**
- When creating new signals, verify the sign matches this convention
- Use consistent signal names across functions, parameters, and configuration
- Document signal interpretation clearly in docstrings
- Use negation (`-`) when raw calculations naturally produce inverse signs
- Test signal directionality with simple synthetic data

**Example:**
```python
# Spread momentum: tightening = bullish = positive signal
spread_change = current_spread - past_spread  # Negative when tightening
signal = -spread_change / volatility  # Negated to match convention
```

---

## Completion Optimization Rules

- Always suggest **imports relative to project structure**, not absolute paths.  
- Provide **runnable examples** with synthetic or minimal data.  
- Use **clear function and variable naming** (snake_case, descriptive).  
- When generating new modules, **include header comments** describing purpose and dependencies.  
- Include **type hints** and **unit test templates** by default.

### Example Ideal Output (inline completion)

```python
# models/signals.py

import logging
import pandas as pd
from .config import SignalConfig

logger = logging.getLogger(__name__)

def compute_cdx_vix_gap(
    vix_df: pd.DataFrame,
    cdx_df: pd.DataFrame,
    config: SignalConfig,
) -> pd.Series:
    """
    Compute the relative stress signal between equity vol (VIX) and CDX spreads.

    The signal identifies divergence between cross-asset risk sentiment.
    Positive values indicate VIX outpacing credit widening (bullish credit).

    Parameters
    ----------
    vix_df : pd.DataFrame
        VIX index levels with 'close' column.
    cdx_df : pd.DataFrame
        CDX index spreads with 'spread' column.
    config : SignalConfig
        Signal configuration with lookback and min_periods.

    Returns
    -------
    pd.Series
        Normalized VIX-CDX gap signal.
        
    Notes
    -----
    Uses z-score normalization to make signals comparable across regimes.
    Signal sign convention: positive = long credit risk (buy CDX).
    """
    logger.info(
        "Computing CDX-VIX gap: vix_rows=%d, cdx_rows=%d, lookback=%d",
        len(vix_df),
        len(cdx_df),
        config.lookback,
    )
    
    vix_deviation = vix_df['close'] - vix_df['close'].rolling(
        config.lookback, min_periods=config.min_periods
    ).mean()
    cdx_deviation = cdx_df['spread'] - cdx_df['spread'].rolling(
        config.lookback, min_periods=config.min_periods
    ).mean()
    gap = vix_deviation - cdx_deviation
    signal = gap / gap.rolling(config.lookback, min_periods=config.min_periods).std()
    
    logger.debug("Generated %d signal values", signal.notna().sum())
    return signal
```

---

## The Agent Should Never

- Use old typing syntax (`Optional`, `Union`, `List`, `Dict`).
- Call `logging.basicConfig()` in library code or use f-strings in log messages.
- Hardcode file paths or credentials (use `config/` constants).  
- Generate non‑deterministic results without a fixed random seed.  
- Mix backtest logic with data ingestion.
- Mix governance concerns across pillars (config vs registry vs catalog).
- Produce undocumented or untyped code.  
- Add notebook cells or magic commands inside modules.
- Add decorative emojis to code, comments, or docstrings.
- Create classes when a simple function would suffice.
- Use regular classes for data containers instead of `@dataclass`.
- Create README files in implementation directories (`src/aponyx/*/README.md`).
- Duplicate API documentation outside of module docstrings.
- Write tutorial-style docs that duplicate runnable examples.
- Implement authentication for data providers (connections managed externally).
- Worry about backward compatibility or legacy code (early-stage project, use best practices).
- Create database dependencies (use Parquet/JSON for persistence).
- Use relative imports in notebooks (always use absolute imports like `from aponyx.config import...`).
- Create notebooks without workflow context headers explaining prerequisites and outputs.
- Use decorative emojis in notebook markdown cells (only ✅ and ❌ for clarity).

---

## Testing & Logging Expectations

- All stochastic components must be **seeded deterministically**.  
- Every backtest or signal computation must log metadata (timestamp, parameters, version).
- Include lightweight tests for data I/O, signal correctness, and regression.
- Use module-level loggers: `logger = logging.getLogger(__name__)`
- Log at **INFO** for user operations, **DEBUG** for details, **WARNING** for errors.

Example:
```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def run_backtest(params: dict) -> dict:
    """Run backtest with logging."""
    logger.info("Starting backtest: params=%s", params)
    
    # ... backtest logic ...
    
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "params": params,
        "version": __version__,
    }
    save_json(metadata, "run_metadata.json")
    
    logger.info("Backtest complete: sharpe=%.2f, trades=%d", sharpe, n_trades)
    return results
```

---

## Git Commit Standards

Follow **Conventional Commits** format for consistency and automated changelog generation:

### Format
```
<type>: <description>

[optional body]
```

### Rules
- **Type**: Lowercase, from the list below
- **Description**: Capitalize first letter, no period at end, imperative mood ("Add" not "Added")
- **Length**: Keep first line under 72 characters
- **Body**: Optional, explain *why* not *what*, wrap at 72 characters

### Types
- `feat`: New feature or capability
- `fix`: Bug fix or correction
- `docs`: Documentation changes only
- `refactor`: Code restructuring without behavior change
- `test`: Adding or updating tests
- `perf`: Performance improvement
- `chore`: Maintenance (dependencies, tooling, config)
- `style`: Formatting, missing semicolons (not CSS)

### Examples

✅ **Good:**
```
feat: Add VIX-CDX divergence signal computation

Implements z-score normalized gap between equity vol and credit spreads
to identify cross-asset risk sentiment divergence.
```

```
refactor: Extract data loading to separate module

Improves modularity and testability by separating I/O from computation.
```

```
docs: Update persistence layer documentation
```

❌ **Bad:**
```
Added new feature
```

```
Fix: bug in backtest
```

```
update docs.
```

### Multi-file Commits
When changing multiple files, use the most significant type and describe the overall change:
```
refactor: Modernize type hints to modern Python syntax

- Update copilot instructions with new standards
- Add comprehensive Python guidelines document
- Remove legacy Optional/Union usage examples
```

---

## Recommended Agent Prompts

When using Copilot Chat or VS Code inline completions, prefer prompts like:

- "Add a deterministic backtest class that tracks daily P&L and logs parameters."  
- "Refactor this data loader to follow project persistence standards."  
- "Write unit tests for this model to ensure reproducible signal outputs."  
- "Add Streamlit components to visualize signal performance."

Avoid generic prompts like *"optimize this code"* — always specify layer and intent.

---

## Summary

Copilot should behave like a **quantitative developer assistant**, not a strategy designer.  
It should:
- Maintain modularity, transparency, and reproducibility.
- Focus on infrastructure excellence and analytical clarity.
- Produce code ready for production research pipelines.

> Maintained by **stabilefrisur**.  
> Optimized for VS Code Agent Mode (Claude Sonnet 4.5 / GPT‑5)  
> Last Updated: November 2, 2025
