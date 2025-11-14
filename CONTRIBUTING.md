# Contributing to Aponyx

> **Early-stage research framework** — Personal project, not community-maintained

**Breaking changes:** This project may introduce breaking changes between versions without deprecation warnings. No backward compatibility guarantees.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

---

## Getting Started

### Prerequisites

- **Python 3.12** (no backward compatibility with 3.11 or earlier)
- **uv** package manager ([installation guide](https://docs.astral.sh/uv/))
- Git for version control
- (Optional) Bloomberg Terminal with `blpapi` for data provider development

### Development Environment Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/aponyx.git
   cd aponyx
   ```

2. **Install dependencies:**
   ```bash
   uv sync --extra dev --extra viz
   ```

3. **Activate the virtual environment:**
   ```bash
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

4. **Verify installation:**
   ```bash
   pytest
   ```

---

## Development Workflow

### Branch Strategy

- `master` - Stable releases only
- Feature branches - `feat/description`
- Bug fixes - `fix/description`
- Documentation - `docs/description`

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes following code standards** (see below)

3. **Run tests and checks:**
   ```bash
   pytest                              # Unit tests
   pytest --cov=aponyx                # With coverage
   black src/ tests/                   # Format code
   ruff check src/ tests/              # Lint
   mypy src/                          # Type check
   ```

4. **Commit with conventional commit format** (see below)

5. **Push and create pull request:**
   ```bash
   git push origin feat/your-feature-name
   ```

---

## Code Standards

Aponyx follows **strict code quality standards**. Please review these documents before contributing:

### Primary References

- **[Python Guidelines](src/aponyx/docs/python_guidelines.md)** - Comprehensive code standards
- **[Copilot Instructions](.github/copilot-instructions.md)** - Development context and patterns

### Quick Standards Summary

#### Type Hints (Modern Python Syntax)
✅ **Use:**
```python
def process_data(
    data: dict[str, Any],
    filters: list[str] | None = None,
) -> pd.DataFrame | None:
    ...
```

❌ **Avoid:**
```python
from typing import Optional, Union, List, Dict  # Old syntax
```

#### Functions Over Classes
- Default to **pure functions** for transformations and calculations
- Use **`@dataclass`** for data containers (prefer `frozen=True` for immutability)
- Only use classes for: state management, lifecycle management, or plugin patterns

#### Logging Standards
```python
import logging
logger = logging.getLogger(__name__)

# Use %-formatting (not f-strings)
logger.info("Loaded %d rows from %s", len(df), path)

# Never in library code:
# logging.basicConfig(...)  # User's responsibility
```

#### Docstrings
All public functions require **NumPy-style docstrings**:
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
        
    Notes
    -----
    Signal sign convention: positive = long credit risk (buy CDX).
    """
```

#### Import Organization
```python
# Standard library
import logging
from datetime import datetime

# Third-party
import pandas as pd
import numpy as np

# Local
from aponyx.config import DATA_DIR
from aponyx.data import fetch_cdx
```

---

## Testing Requirements

### Test Coverage

- **All new features require unit tests**
- Maintain >85% test coverage
- Test determinism (fixed random seeds)
- Test edge cases and error handling

### Test Structure

```python
def test_feature():
    """Test description following docstring standards."""
    # Arrange
    input_data = generate_test_data(seed=42)
    
    # Act
    result = compute_feature(input_data)
    
    # Assert
    assert isinstance(result, pd.Series)
    assert len(result) == len(input_data)
    assert result.isna().sum() == 0
```

### Running Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=aponyx --cov-report=html

# Specific module
pytest tests/models/

# Specific test
pytest tests/models/test_signals.py::test_compute_cdx_etf_basis
```

---

## Documentation

### Documentation Requirements

All contributions must include appropriate documentation:

1. **Docstrings** - NumPy-style for all public functions/classes
2. **Type hints** - Full type annotations using modern syntax
3. **Inline comments** - For complex logic or non-obvious decisions
4. **Design docs** - For architectural changes (add to `src/aponyx/docs/`)

### Documentation Structure

Follow the **Single Source of Truth** principle:

| Doc Type | Location | Purpose |
|----------|----------|---------|
| **API Reference** | Module docstrings | Function/class contracts |
| **Quickstart** | `README.md` | Installation, examples, navigation |
| **Design Docs** | `src/aponyx/docs/*.md` | Architecture, standards, strategy |
| **Notebooks** | `src/aponyx/notebooks/*.ipynb` | Workflow demonstrations |

**See:** [Documentation Structure](src/aponyx/docs/documentation_structure.md)

### Updating Documentation

- Update `README.md` only if changing quickstart or installation
- Update design docs for architectural decisions
- Update `CHANGELOG.md` following Keep a Changelog format
- Do NOT create README files in implementation directories

---

## Commit Messages

Follow **Conventional Commits** format for consistency and automated changelog generation.

### Format
```
<type>: <description>

[optional body]
```

### Types
- `feat` - New feature or capability
- `fix` - Bug fix or correction
- `docs` - Documentation changes only
- `refactor` - Code restructuring without behavior change
- `test` - Adding or updating tests
- `perf` - Performance improvement
- `chore` - Maintenance (dependencies, tooling, config)
- `style` - Formatting (not CSS)

### Rules
- **Type**: Lowercase, from list above
- **Description**: Capitalize first letter, no period, imperative mood ("Add" not "Added")
- **Length**: Keep first line under 72 characters
- **Body**: Optional, explain *why* not *what*, wrap at 72 characters

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

---

## Pull Request Process

### Before Submitting

1. **Ensure all tests pass:**
   ```bash
   pytest --cov=aponyx
   ```

2. **Run code quality checks:**
   ```bash
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

3. **Update documentation** as needed

4. **Add entry to `CHANGELOG.md`** under "Unreleased" section

### PR Requirements

Your pull request must:
- Have a clear, descriptive title following conventional commit format
- Reference any related issues
- Include comprehensive tests for new features
- Maintain or improve test coverage
- Pass all CI checks
- Include updated documentation

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Tests pass locally
- [ ] Code formatted with black
- [ ] Linting passes (ruff)
- [ ] Type checking passes (mypy)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

### Review Process

PRs will be reviewed as time permits. No SLA or guaranteed response time.

---

## Questions?

If you have questions:
1. Check existing documentation in `src/aponyx/docs/`
2. Search closed issues
3. Open a new issue (response time varies)

**Thank you for contributing to aponyx!**

---

**Maintained by stabilefrisur**  
**Last Updated:** November 14, 2025
