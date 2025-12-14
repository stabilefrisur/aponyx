---
mode: agent
model: Claude Sonnet 4.5
description: 'Reset the development environment by cleaning caches, runtime data, and regenerating synthetic test data.'
---
# Reset Development Environment

Reset the development environment by cleaning caches, runtime data, and regenerating synthetic test data.

## Sequence

Run the following scripts in order:

1. **Clean Python cache files** - Remove all `__pycache__` directories and `.pyc` files
2. **Clean runtime data** - Delete all generated data (raw, cache, workflows, registries, logs)
3. **Generate synthetic data** - Create fresh synthetic test data with registry

## Commands

```bash
# Step 1: Clean Python cache
uv run python scripts/clean_pycache.py

# Step 2: Clean runtime data
uv run python scripts/clean_runtime_data.py

# Step 3: Generate fresh synthetic data
uv run python scripts/generate_synthetic.py
```

## Optional Flags

- `--dry-run` - Preview what would be deleted without actually deleting (available for clean scripts)
- `--verbose` or `-v` - Show detailed information about each file/directory

## Expected Output

After running all three scripts:
- All `__pycache__` directories removed
- `data/raw/`, `data/cache/`, `data/workflows/`, `data/.registries/`, and `logs/` cleaned
- Fresh synthetic data generated in `data/raw/synthetic/`
- New `registry.json` created for FileSource lookup
