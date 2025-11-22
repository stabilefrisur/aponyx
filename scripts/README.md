# Utility Scripts

This directory contains untracked utility scripts for local development.

## clean_pycache.py

Deletes all `__pycache__` directories and `.pyc` files from the project.

### Usage

```bash
# Preview what would be deleted
python scripts/clean_pycache.py --dry-run

# Delete with verbose output
python scripts/clean_pycache.py --verbose

# Just delete without details
python scripts/clean_pycache.py

# Specify custom root directory
python scripts/clean_pycache.py --root /path/to/directory
```

### What Gets Deleted

- All `__pycache__` directories (recursively)
- All `.pyc` files

### Use Cases

- Clean up before committing
- Resolve import caching issues
- Free up disk space
- Reset Python bytecode after refactoring

---

## clean_runtime_data.py

Deletes all runtime-generated data while preserving static configuration files.

### Usage

```bash
# Dry run (show what would be deleted)
python scripts/clean_runtime_data.py --dry-run

# Dry run with detailed output
python scripts/clean_runtime_data.py --dry-run --verbose

# Actually delete runtime data
python scripts/clean_runtime_data.py

# Delete with detailed output
python scripts/clean_runtime_data.py --verbose
```

### What Gets Deleted

**Directories (all contents):**
- `data/raw/*`
- `data/processed/*`
- `data/cache/*`
- `logs/*`
- `reports/suitability/*`
- `reports/performance/*`

**Files (runtime registries):**
- `data/registry.json`
- `src/aponyx/evaluation/suitability/suitability_registry.json`
- `src/aponyx/evaluation/performance/performance_registry.json`

### What Gets Preserved

**Static configuration files:**
- `src/aponyx/models/signal_catalog.json` ✓
- `src/aponyx/backtest/strategy_catalog.json` ✓
- `src/aponyx/data/bloomberg_securities.json` ✓
- `src/aponyx/data/bloomberg_instruments.json` ✓

### Use Cases

- Clean up before committing to ensure no runtime data is tracked
- Reset local environment to fresh state
- Remove old evaluation results and reports
- Free up disk space from cached data
