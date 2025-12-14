---
description: 'Test CLI workflows and update documentation'
---
# CLI Workflow Testing & Documentation Sync

**Purpose:** Systematically test all CLI commands, example workflows, and ensure documentation reflects the actual implementation.  
**Assumption:** Agent has access to `copilot-instructions.md` for full project context.

---

## Testing Scope

### 1. Example Workflows
Test all YAML configs in `examples/`:
- [ ] `workflow_minimal.yaml` - Required fields only
- [ ] `workflow_complete.yaml` - All explicit fields

### 2. CLI Commands

**Core commands:**
- [ ] `aponyx run <config>` - Execute workflow
- [ ] `aponyx report --workflow <label|index> [--format console|markdown|html]`
- [ ] `aponyx clean --workflows [--all|--older-than Nd] [--dry-run]`
- [ ] `aponyx clean --indicators [--dry-run]`

**List subcommands:**
- [ ] `aponyx list signals`
- [ ] `aponyx list products`
- [ ] `aponyx list indicators`
- [ ] `aponyx list score-transformations`
- [ ] `aponyx list signal-transformations`
- [ ] `aponyx list securities`
- [ ] `aponyx list strategies`
- [ ] `aponyx list datasets`
- [ ] `aponyx list steps`
- [ ] `aponyx list workflows [--signal X] [--product Y] [--strategy Z]`

### 3. Documentation Files
Sync with actual implementation:
- [ ] `src/aponyx/docs/cli_guide.md`
- [ ] Example YAML configs match documented schema
- [ ] Command options match `--help` output

---

## Test Execution Process

### Step 1: Run Example Workflows
```bash
cd c:/Users/ROG3003/PythonProjects/aponyx
uv run aponyx run examples/workflow_minimal.yaml
uv run aponyx run examples/workflow_complete.yaml
```

**Verify output includes:**
- Configuration display with source tags (`[config]`, `[from signal]`, `[from indicator]`, `[default]`)
- Step completion count and duration
- Output directory path

### Step 2: Test All List Commands
```bash
uv run aponyx list signals
uv run aponyx list products
uv run aponyx list indicators
uv run aponyx list score-transformations
uv run aponyx list signal-transformations
uv run aponyx list securities
uv run aponyx list strategies
uv run aponyx list datasets
uv run aponyx list steps
uv run aponyx list workflows
uv run aponyx list workflows --signal spread_momentum
```

### Step 3: Test Report Command
```bash
# By label (stable reference)
uv run aponyx report --workflow minimal_test

# By index (ephemeral)
uv run aponyx report --workflow 0

# Different formats
uv run aponyx report --workflow minimal_test --format markdown
uv run aponyx report --workflow minimal_test --format html
```

### Step 4: Test Clean Command (Dry Run)
```bash
# Preview workflow cleanup
uv run aponyx clean --workflows --all --dry-run
uv run aponyx clean --workflows --older-than 30d --dry-run

# Preview indicator cache cleanup
uv run aponyx clean --indicators --dry-run
```

### Step 5: Verify Command Help
```bash
uv run aponyx --help
uv run aponyx run --help
uv run aponyx report --help
uv run aponyx list --help
uv run aponyx clean --help
```

---

## Documentation Audit Checklist

### YAML Schema Accuracy
Compare `cli_guide.md` YAML Configuration Schema table against:
1. `WorkflowConfig` dataclass in `src/aponyx/workflows/config.py`
2. `run.py` command parsing in `src/aponyx/cli/commands/run.py`

**Check for:**
- [ ] All documented fields exist in code
- [ ] No undocumented fields in code
- [ ] Default values match
- [ ] Required/optional status correct

### Command Options Accuracy
For each command, compare docs against `--help` output:
- [ ] All options documented
- [ ] No undocumented options
- [ ] Option types and defaults correct
- [ ] Examples use valid options

### Feature Implementation Status
Identify features that are:
- **Documented but NOT implemented** → Remove from docs
- **Implemented but NOT documented** → Add to docs
- **Implemented differently than documented** → Update docs

Common discrepancies:
- Runtime overrides (e.g., `sizing_mode_override`) that don't exist
- Command options that were removed
- Default values that changed

---

## Output Format

### Test Results Summary

```markdown
## CLI Test Results

### Workflows Tested
| Workflow | Status | Notes |
|----------|--------|-------|
| workflow_minimal.yaml | ✅ Pass | 6 steps, 1.8s |
| workflow_complete.yaml | ✅ Pass | 6 steps, 2.1s |

### Commands Tested
| Command | Status | Notes |
|---------|--------|-------|
| `list signals` | ✅ Pass | 3 signals |
| `list products` | ✅ Pass | 5 products |
| ... | ... | ... |

### Documentation Issues Found
| File | Issue | Fix Applied |
|------|-------|-------------|
| cli_guide.md | `sizing_mode_override` not implemented | ✅ Removed |
| cli_guide.md | `--output` option doesn't exist | ✅ Removed |
```

### Documentation Updates

For each fix, provide:
- **File:** Path to documentation file
- **Issue:** What was wrong
- **Fix:** What was changed
- **Verification:** How to confirm the fix

---

## Common Issues to Watch For

### 1. Undocumented Defaults
Check `strategy_catalog.json` for actual defaults:
- `sizing_mode`: All strategies use `"proportional"` by default
- `position_size_mm`: Varies by strategy
- `stop_loss_pct`, `take_profit_pct`: May be `null`

### 2. Missing Runtime Overrides
The CLI may not support all theoretically possible overrides:
- Check `run.py` for actual YAML fields parsed
- Check `WorkflowConfig` for actual override fields
- Remove docs for overrides that aren't implemented

### 3. Deprecated Options
Options that were removed but still documented:
- `--output` for report command (saves to workflow's reports/ folder automatically)
- `--verbose` vs `-v` inconsistencies

### 4. Path Differences
- Docs may show Unix paths (`data/workflows/`)
- Windows shows `C:\Users\...\data\workflows\`
- Use relative paths in docs where possible

---

## Automation Hooks

### Pre-commit Check
Add to CI/CD or run manually before releases:
```bash
# Verify example workflows execute
uv run aponyx run examples/workflow_minimal.yaml
uv run aponyx run examples/workflow_complete.yaml

# Verify all list commands work
for item in signals products indicators score-transformations signal-transformations securities strategies datasets steps workflows; do
  uv run aponyx list $item > /dev/null || echo "FAIL: list $item"
done
```

### Documentation Freshness
Track when docs were last verified:
- Add `**Last Verified:** YYYY-MM-DD` to cli_guide.md footer
- Update on each test run

---

## Usage

```
Test all CLI workflows and update documentation
Focus on: [specific area if needed, e.g., "clean command options"]
```

Or to run full test suite:
```
Run complete CLI workflow tests per test-cli-workflows.prompt.md
```

---

> **Version:** 1.0  
> **Optimized for:** Claude Opus 4.5 (Preview) Agent Mode  
> **Last Updated:** December 13, 2025
