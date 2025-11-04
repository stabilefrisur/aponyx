# Documentation Structure

## Single Source of Truth Principle

| Doc Type | Location | Purpose | Audience |
|----------|----------|---------|----------|
| **API Reference** | Module docstrings | Function/class contracts | Developers (in-editor) |
| **Quickstart** | `README.md` | Installation, examples, overview | New users |
| **Design Docs** | `src/aponyx/docs/*.md` | Architecture, standards, strategy | Contributors |
| **Examples** | `src/aponyx/examples/*.py` + headers | Runnable demonstrations | Researchers |

**Rule**: Each piece of information has exactly one authoritative location.

---

## Documentation Map

### Root Level
- **`README.md`** - Installation, quickstart, project overview, navigation

### Documentation (`src/aponyx/docs/`)
- **`cdx_overlay_strategy.md`** - Investment strategy and implementation
- **`python_guidelines.md`** - Code standards and best practices
- **`logging_design.md`** - Logging conventions and metadata tracking
- **`documentation_structure.md`** - This file (documentation philosophy)

### Examples (`src/aponyx/examples/`)
- **`README.md`** - Quick start commands and script overview
- **`*_demo.py`** - Self-documenting executable demonstrations

### Source Code (`src/aponyx/`)
- **Module/function docstrings** - NumPy-style API documentation
- **Inline comments** - Implementation details and rationale

---

## What Belongs Where

### Root `README.md`
✅ Installation, quick start, project structure, links to docs  
❌ Implementation details, API reference, exhaustive examples

**Example:**
```markdown
✅ DO: "Install with `uv sync` and run `uv run python -m aponyx.examples.backtest_demo`"
❌ DON'T: Copy entire function signatures or explain implementation details
```

### Design Docs (`src/aponyx/docs/*.md`)
✅ Architecture decisions, design patterns, cross-cutting concerns  
❌ Code usage examples, API documentation, implementation summaries

**Example:**
```markdown
✅ DO: "Signals use positive values for long credit risk to ensure consistent interpretation"
❌ DON'T: "Call compute_signal(df, window=20) to generate signals" (use docstrings instead)
```

### `src/aponyx/examples/README.md`
✅ Quick run commands, script purpose table, prerequisites, troubleshooting  
❌ Detailed explanations (use script headers), code snippets (use actual scripts)

**Example:**
```markdown
✅ DO: "Run `uv run python -m aponyx.examples.backtest_demo` to see complete workflow"
✅ DO: "Common issue: Missing viz dependencies. Solution: `uv sync --extra viz`"
❌ DON'T: Reproduce code from the actual demo scripts
```

### Demo Script Headers
✅ What it demonstrates, workflow steps, key configuration, expected output  
❌ Installation instructions, design rationale

**Example:**
```python
✅ DO:
"""
Backtest Demo - Complete strategy workflow
Demonstrates: Signal generation → Backtest → Performance metrics
Expected output: Sharpe ratio, max drawdown, trade statistics
"""

❌ DON'T: Include installation instructions or explain why we chose this architecture
```

### Docstrings
✅ API contracts (params, returns, raises), type info, edge cases  
❌ Project overview, installation instructions

**Example:**
```python
✅ DO:
def compute_signal(spread: pd.Series, window: int = 20) -> pd.Series:
    """
    Compute momentum signal from spread time series.
    
    Parameters
    ----------
    spread : pd.Series
        Daily spread levels.
    window : int, default 20
        Rolling window for normalization.
    
    Returns
    -------
    pd.Series
        Z-score normalized momentum signal.
    """

❌ DON'T: Add project overview or "This project provides..." in docstrings
```

---

## Anti-Patterns (What NOT to Do)

### ❌ Duplicating API Documentation

**Bad:** Creating `docs/api_reference.md` that copies function signatures from code

**Why:** Docstrings are the authoritative source. External docs go stale.

**Good:** Link to modules and rely on IDE/docstring rendering.

### ❌ Tutorial-Style Docs

**Bad:** Creating separate tutorial files with step-by-step code examples

**Why:** Duplicates `src/aponyx/examples/backtest_demo.py` which is executable and tested.

**Good:** Point users to the demo script and explain *why* in design docs.

### ❌ Implementation README Files

**Bad:** Creating `src/aponyx/models/README.md`

**Why:** Violates single source of truth. Details belong in docstrings.

**Good:** Module-level docstrings explain the layer's purpose.

### ❌ Mixing "Why" and "How"

**Bad:** Design docs with code examples showing how to use functions

**Why:** Confuses architecture rationale with usage instructions.

**Good:** Design docs explain decisions; demos show usage.

---

## Concrete Examples

### Example 1: Adding a New Signal

**Where to document:**
1. **Function docstring** (`signals.py`): Parameter types, return value, signal convention
2. **Catalog entry** (`signal_catalog.json`): Signal name, description, data requirements
3. **Design doc update** (if new pattern): *Only if* introducing new architecture concept

**Don't document:**
- ❌ Full usage tutorial in `docs/`
- ❌ API reference separate from docstring
- ❌ Duplicate catalog schema in multiple places

### Example 2: Changing Backtest Logic

**Where to document:**
1. **Docstring** (`engine.py`): Updated function signature and behavior
2. **Tests** (`test_engine.py`): New test cases demonstrating changed behavior
3. **Design doc** (`src/aponyx/docs/`): *Only if* architectural decision changed

**Don't document:**
- ❌ Changelog in multiple docs (keep git history)
- ❌ "How to run backtest" tutorial (use demo script)

### Example 3: New Data Provider

**Where to document:**
1. **Class docstring** (`providers/new_provider.py`): Provider-specific API details
2. **Demo script** (`src/aponyx/examples/data_demo.py`): Add example using new provider
3. **Design doc** (`adding_data_providers.md` in same directory): Architecture pattern for providers

**Don't document:**
- ❌ Provider list in multiple places (use code as source of truth)
- ❌ Step-by-step guide separate from demo (use demo script)

---

## Documentation Workflow Examples

### Scenario: User Wants to Run a Backtest

**Documentation Path:**
1. **Root README** → Points to `src/aponyx/examples/backtest_demo.py`
2. **Demo script** → Shows runnable code with comments
3. **Function docstrings** → Explains individual function contracts

**User never needs to:**
- Read design docs for basic usage
- Search for API reference outside code
- Follow tutorial-style guides

### Scenario: Contributor Wants to Add a Signal

**Documentation Path:**
1. **Root README** → Links to `signal_registry_usage.md` (in installed docs)
2. **Design doc** → Explains registry pattern and conventions
3. **Demo script** → Shows working example of signal usage
4. **Docstrings** → Reference for function signatures

**User never encounters:**
- Duplicate instructions in multiple places
- Out-of-sync code examples
- Ambiguity about authoritative source

---

## Maintenance Workflow

### When Adding a Feature

1. Implement with NumPy-style docstrings
2. Write unit tests
3. Add demo script (if new layer/capability)
4. Update root README (only if affects quickstart)
5. Update design doc (only if architectural change)

### Where to Document

| Question | Location |
|----------|----------|
| "How do I install?" | Root README |
| "How do I use function X?" | Function docstring |
| "How do I run a backtest?" | `backtest_demo.py` header + code |
| "Why this design?" | `src/aponyx/docs/*.md` |
| "What's the API?" | Module/function docstrings |

### What NOT to Do

❌ Create README files in implementation directories  
❌ Write "implementation summary" docs separate from code  
❌ Duplicate usage examples across files  
❌ Document API details outside docstrings  
❌ Create tutorial-style docs that duplicate demos

---

**Principle**: Executable code (demos, tests, docstrings) is the documentation. Design docs explain *why*, not *how*.
