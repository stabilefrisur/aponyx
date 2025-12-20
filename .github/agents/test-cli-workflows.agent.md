---
description: 'Test CLI workflows and update documentation'
---
# CLI Workflow Testing & Documentation Sync

**Purpose:** Systematically test all CLI commands, example workflows, and ensure documentation reflects the actual implementation.  
**Assumption:** Agent has access to `copilot-instructions.md` for full project context.

---

## Testing Scope

### 1. Example Workflows
Test all YAML configs in `src/aponyx/examples/configs/`:

**Workflows (01-03):**
- [ ] `01_workflow_minimal.yaml` - Quick start with minimal required fields
- [ ] `02_workflow_complete.yaml` - Full configuration reference with all overrides
- [ ] `03_workflow_etf_price_backtest.yaml` - Price-quoted product backtest

**Sweeps (04-06):**
- [ ] `04_sweep_indicator_lookback.yaml` - Indicator mode (8 combinations)
- [ ] `05_sweep_strategy_optimization.yaml` - Backtest mode (27 combinations)
- [ ] `06_sweep_comprehensive.yaml` - Full pipeline (200 combinations)

### 2. CLI Commands

**Core commands:**
- [ ] `aponyx run <config>` - Execute workflow
- [ ] `aponyx sweep <config> [--dry-run]` - Run parameter sweeps
- [ ] `aponyx report --workflow <label|index> [--format console|markdown|html]`
- [ ] `aponyx clean --workflows [--all|--older-than Nd] [--dry-run]`
- [ ] `aponyx clean --indicators [--dry-run]`

**Catalog management:**
- [ ] `aponyx catalog validate` - Check YAML catalog integrity
- [ ] `aponyx catalog sync [--dry-run]` - Regenerate JSON from YAML
- [ ] `aponyx catalog migrate [--force]` - One-time JSON to YAML migration

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

# Phase 1: Workflows
uv run aponyx run src/aponyx/examples/configs/01_workflow_minimal.yaml
uv run aponyx run src/aponyx/examples/configs/02_workflow_complete.yaml
uv run aponyx run src/aponyx/examples/configs/03_workflow_etf_price_backtest.yaml
```

**Verify output includes:**
- Configuration display with source tags (`[config]`, `[from signal]`, `[from indicator]`, `[default]`)
- Step completion count and duration (~5s per workflow)
- Output directory path in `data/workflows/<label>_<timestamp>/`

### Step 2: Run Parameter Sweeps
```bash
# Phase 2: Indicator sweep (fast)
uv run aponyx sweep src/aponyx/examples/configs/04_sweep_indicator_lookback.yaml --dry-run
uv run aponyx sweep src/aponyx/examples/configs/04_sweep_indicator_lookback.yaml

# Phase 3: Backtest sweeps
uv run aponyx sweep src/aponyx/examples/configs/05_sweep_strategy_optimization.yaml --dry-run
uv run aponyx sweep src/aponyx/examples/configs/05_sweep_strategy_optimization.yaml

# Comprehensive sweep (takes ~18s)
uv run aponyx sweep src/aponyx/examples/configs/06_sweep_comprehensive.yaml
```

**Verify output includes:**
- Sweep configuration display (name, mode, signal, combinations)
- Parameter list with values
- Progress bar with combo/s rate
- Summary with success rate and duration
- Output directory path in `data/sweeps/<name>_<timestamp>/`
- Files: `config.json`, `summary.json`, `results.parquet`

### Step 3: Test All List Commands
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

### Step 4: Test Report Command
```bash
# By label (stable reference)
uv run aponyx report --workflow minimal_test

# By index (ephemeral)
uv run aponyx report --workflow 0

# Different formats
uv run aponyx report --workflow minimal_test --format markdown
uv run aponyx report --workflow minimal_test --format html
```

### Step 5: Test Clean Command (Dry Run)
```bash
# Preview workflow cleanup
uv run aponyx clean --workflows --all --dry-run
uv run aponyx clean --workflows --older-than 30d --dry-run

# Preview indicator cache cleanup
uv run aponyx clean --indicators --dry-run
```

### Step 6: Test Catalog Commands
```bash
# Validate YAML catalogs
uv run aponyx catalog validate

# Preview sync (no changes)
uv run aponyx catalog sync --dry-run

# Actual sync (if needed)
# uv run aponyx catalog sync
```

**Verify output includes:**
- Validation status for each catalog (signals, strategies, securities)
- Cross-reference validation results
- Sync preview showing changed/unchanged file counts

### Step 7: Verify Command Help
```bash
uv run aponyx --help
uv run aponyx run --help
uv run aponyx sweep --help
uv run aponyx report --help
uv run aponyx list --help
uv run aponyx catalog --help
uv run aponyx catalog validate --help
uv run aponyx catalog sync --help
uv run aponyx catalog migrate --help
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

### Examples Tested
| Example | Type | Status | Notes |
|---------|------|--------|-------|
| 01_workflow_minimal.yaml | Workflow | ✅ Pass | 6 steps, ~5s |
| 02_workflow_complete.yaml | Workflow | ✅ Pass | 6 steps, ~5s |
| 03_workflow_etf_price_backtest.yaml | Workflow | ✅ Pass | 6 steps, ~5s |
| 04_sweep_indicator_lookback.yaml | Sweep | ✅ Pass | 8 combos, ~5s |
| 05_sweep_strategy_optimization.yaml | Sweep | ✅ Pass | 27 combos, ~6s |
| 06_sweep_comprehensive.yaml | Sweep | ✅ Pass | 200 combos, ~18s |

### Commands Tested
| Command | Status | Notes |
|---------|--------|-------|
| `run` | ✅ Pass | 3 workflows executed |
| `sweep` | ✅ Pass | 3 sweeps executed |
| `report` | ✅ Pass | console/markdown/html |
| `catalog validate` | ✅ Pass | All catalogs valid |
| `catalog sync --dry-run` | ✅ Pass | Preview mode works |
| `list signals` | ✅ Pass | 3 signals |
| `list products` | ✅ Pass | 5 products |
| `list workflows` | ✅ Pass | Filtering works |
| `clean --workflows --dry-run` | ✅ Pass | Preview mode works |

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
uv run aponyx run src/aponyx/examples/configs/01_workflow_minimal.yaml
uv run aponyx run src/aponyx/examples/configs/02_workflow_complete.yaml
uv run aponyx run src/aponyx/examples/configs/03_workflow_etf_price_backtest.yaml

# Verify sweeps execute (quick ones only)
uv run aponyx sweep src/aponyx/examples/configs/04_sweep_indicator_lookback.yaml

# Verify catalog validation
uv run aponyx catalog validate

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

> **Version:** 1.1  
> **Optimized for:** Claude Sonnet 4.5 Agent Mode  
> **Last Updated:** December 20, 2025
