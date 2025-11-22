---
mode: agent
model: Claude Sonnet 4.5
description: 'Review the ${workspaceFolder} implementation layer'
---
# Layer Implementation Review

**Purpose:** Systematic code review focused on implementation quality, not project setup.  
**Assumption:** Agent has access to `copilot-instructions.md` for full project context.

---

## Review Checklist

### 1. Interface Quality
- [ ] Minimal, well-defined public API
- [ ] Single responsibility per module
- [ ] Uses `Protocol`/`ABC` for swappable components
- [ ] Extension points clearly marked
- [ ] Modern type syntax throughout

### 2. Architecture Compliance
- [ ] No upward layer dependencies
- [ ] No circular imports
- [ ] Governance pattern usage correct (config/registry/catalog)
- [ ] Workflow outputs to timestamped directories
- [ ] Registry uses relative paths, resolves to absolute

### 3. Code Quality
- [ ] Functions over classes (classes only for state/lifecycle)
- [ ] `@dataclass` for data containers (`frozen=True` for immutable)
- [ ] No global state
- [ ] Modules under 300 lines
- [ ] Complete type hints and docstrings
- [ ] Module-level loggers with %-formatting

### 4. Implementation Correctness
- [ ] Signal sign convention followed (models: positive = long credit)
- [ ] Pure, deterministic functions for core logic
- [ ] Fixed seeds for random operations
- [ ] No hardcoded paths (use `config/`)
- [ ] No authentication implementation (data layer)

### 5. Testing & Validation
- [ ] Unit tests exist and mirror structure
- [ ] Tests use `uv run pytest`
- [ ] Dependencies injected for testability
- [ ] Edge cases covered

### 6. Simplicity
- [ ] Minimum viable implementation
- [ ] Not reinventing standard library
- [ ] Error handling proportional to complexity
- [ ] No premature optimization

---

## Review Output Format

### ✅ Strengths
List 3-5 things done well with specific examples:
- Good interface design (e.g., clean Protocol definitions)
- Proper layer boundaries (e.g., no upward dependencies)
- Effective use of type hints and documentation
- Simple, testable implementation
- Correct governance pattern usage

### ⚠️ Critical Issues
**Must fix before merging**

For each:
- **Issue:** Description with specific file/line reference
- **Impact:** Why this blocks merging (correctness, safety, breaking change)
- **Fix:** Concrete code snippet or step-by-step instructions

Example:
- **Issue:** `data/loaders.py:45` uses `Optional[str]` instead of `str | None`
- **Impact:** Violates Python 3.12 type syntax standard
- **Fix:** Replace `from typing import Optional` with modern syntax:
  ```python
  def load_data(path: str | None = None) -> pd.DataFrame:
      ...
  ```

### ⚠️ Important Issues
**Should fix in this iteration**

For each:
- **Issue:** Description
- **Recommendation:** Suggested improvement

### 🔧 Top Refactoring Opportunities
2-3 concrete suggestions to improve modularity, simplicity, or testability

### 📋 Action Items
Prioritized list with specific tasks:

**Critical (blockers):**
1. [Specific file/function]: Description of fix needed
2. ...

**Important (this iteration):**
1. [Specific file/function]: Description of improvement
2. ...

**Nice-to-have (defer):**
1. [General area]: Suggestion for future iteration
2. ...

**Estimated effort:** [Small: <1hr | Medium: 1-3hr | Large: >3hr]

---

## Review Process

**1. Scan & Categorize**
- Apply checklist to layer/files
- Categorize: Critical / Important / Nice-to-have
- Note files, lines, snippets

**2. Fix Directly**
- Use `multi_replace_string_in_file`
- Apply critical and important fixes
- Defer nice-to-have

**3. Validate**
- Run: `uv run pytest tests/[layer]/`
- Check: `get_errors` tool
- Verify: imports, types, tests

**4. Report**
- Git commit message (Conventional Commits)
- Action items with priority/effort

---

## Usage

```
Review the [layer]/ implementation
Focus on: [specific checklist areas]
```

---

## Output Template

```markdown
# [Layer] Review

## Summary
[Scope and key findings]

## ✅ Strengths
- [Example 1]
- [Example 2]

## ⚠️ Critical Issues
1. **File:** `path:line` | **Fix:** [Applied/Pending]

## ⚠️ Important Issues
1. [Description] | **Rec:** [Improvement]

## 🔧 Refactoring
- [Suggestion 1]

## 📋 Actions
- **Critical:** [N] - [Status]
- **Important:** [N] - [Status]  
- **Effort:** [S/M/L]

## Commit
\```
[type]: [description]
\```
```

---

> **Version:** 1.3  
> **Optimized for:** Claude Sonnet 4.5 Agent Mode  
> **Last Updated:** November 22, 2025
