# Documentation Structure

## Single Source of Truth Principle

| Doc Type | Location | Purpose | Audience |
|----------|----------|---------|----------|
| **API Reference** | Module docstrings | Function/class contracts | Developers (in-editor) |
| **Quickstart** | `README.md` | Installation, examples, overview | New users |
| **Design Docs** | `src/aponyx/docs/*.md` | Architecture, standards, strategy | Contributors |

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
✅ DO: "Install with `uv sync` and run tests with `pytest`"
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

**Why:** Code examples should be in docstrings or design docs, not separate tutorials.

**Good:** Use docstrings for usage examples and design docs to explain *why*.

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
2. **Design doc** (`adding_data_providers.md` in same directory): Architecture pattern for providers

**Don't document:**
- ❌ Provider list in multiple places (use code as source of truth)

---

## Documentation Workflow Examples

### Scenario: User Wants to Run a Backtest

**Documentation Path:**
1. **Root README** → Shows Quick Start code example
2. **Function docstrings** → Explains individual function contracts
3. **Notebooks** → Complete workflow demonstrations

**User never needs to:**
- Read design docs for basic usage
- Search for API reference outside code
- Follow tutorial-style guides

### Scenario: Contributor Wants to Add a Signal

**Documentation Path:**
1. **Root README** → Links to `signal_registry_usage.md` (in installed docs)
2. **Design doc** → Explains registry pattern and conventions
3. **Docstrings** → Reference for function signatures and usage examples

**User never encounters:**
- Duplicate instructions in multiple places
- Out-of-sync code examples
- Ambiguity about authoritative source

---

## Maintenance Workflow

### When Adding a Feature

1. Implement with NumPy-style docstrings
2. Write unit tests
3. Update root README (only if affects quickstart)
4. Update design doc (only if architectural change)

### Where to Document

| Question | Location |
|----------|----------|
| "How do I install?" | Root README |
| "How do I use function X?" | Function docstring |
| "How do I run a backtest?" | Root README Quick Start + notebooks |
| "Why this design?" | `src/aponyx/docs/*.md` |
| "What's the API?" | Module/function docstrings |

### What NOT to Do

❌ Create README files in implementation directories  
❌ Write "implementation summary" docs separate from code  
❌ Duplicate usage examples across files  
❌ Document API details outside docstrings

---

**Principle**: Executable code (tests, docstrings, notebooks) is the documentation. Design docs explain *why*, not *how*.
