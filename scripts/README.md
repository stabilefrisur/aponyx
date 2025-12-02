# Utility Scripts

This directory contains untracked utility scripts for local development.

## generate_synthetic.py

Generates synthetic market data for testing and development without Bloomberg Terminal access.

### Usage

```bash
# Generate synthetic data with registry
uv run python scripts/generate_synthetic.py
```

### What Gets Created

**Directory:** `data/raw/synthetic/`

**Files generated (8 securities):**
- `cdx_ig_5y_{hash}.parquet` - CDX IG 5Y spreads
- `cdx_ig_10y_{hash}.parquet` - CDX IG 10Y spreads
- `cdx_hy_5y_{hash}.parquet` - CDX HY 5Y spreads
- `itrx_eur_5y_{hash}.parquet` - iTraxx Europe 5Y spreads
- `itrx_xover_5y_{hash}.parquet` - iTraxx Crossover 5Y spreads
- `hyg_{hash}.parquet` - HYG ETF spreads
- `lqd_{hash}.parquet` - LQD ETF spreads
- `vix_{hash}.parquet` - VIX levels
- `registry.json` - Security-to-file mapping
- `{security}_{hash}.json` - Metadata sidecar for each file

**Data characteristics:**
- Date range: 2020-01-01 to 2025-01-01 (~1,306 trading days)
- Mean-reverting dynamics with realistic volatility
- Hash-based filenames ensure uniqueness across date ranges

### Registry Format

The `registry.json` file maps security IDs to filenames:
```json
{
  "cdx_ig_5y": "cdx_ig_5y_018e7bd4e20c.parquet",
  "vix": "vix_bbc75becc62b.parquet",
  "hyg": "hyg_e2a2be47ed61.parquet"
}
```

This enables FileSource to use security-based lookup like Bloomberg.

### Use Cases

- Generate test data for workflows without Bloomberg access
- Create reproducible datasets for testing
- Develop and test signals locally
- Verify workflow functionality before production deployment

---

## test_unified_interface.py

Tests the unified FileSource and BloombergSource interface to verify both providers work identically.

### Usage

```bash
# Run interface verification tests
uv run python scripts/test_unified_interface.py
```

### What Gets Tested

- FileSource registry-based security lookup
- fetch_cdx, fetch_vix, fetch_etf with identical interfaces
- Automatic security column enrichment
- Multi-security loading from single source

### Example Output

```
Testing unified interface with FileSource:

✓ CDX IG 5Y: 1306 rows, security=cdx_ig_5y
✓ CDX HY 5Y: 1306 rows, security=cdx_hy_5y
✓ HYG ETF: 1306 rows, security=hyg
✓ LQD ETF: 1306 rows, security=lqd
✓ VIX: 1306 rows

SUCCESS: All securities loaded with unified interface!
```

### Use Cases

- Verify FileSource refactoring after changes
- Confirm registry.json is properly formatted
- Validate security column enrichment logic
- Quick smoke test before running full workflows

---

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
- `data/raw/*` (includes `data/raw/synthetic/` - regenerate with `generate_synthetic.py`)
- `data/workflows/*`
- `data/cache/*`
- `logs/*`

**Files (runtime registries):**
- `data/.registries/registry.json`
- `data/.registries/suitability.json`
- `data/.registries/performance.json`

### What Gets Preserved

**Static configuration files (always preserved):**
- `src/aponyx/models/indicator_catalog.json` ✓
- `src/aponyx/models/transformation_catalog.json` ✓
- `src/aponyx/models/signal_catalog.json` ✓
- `src/aponyx/backtest/strategy_catalog.json` ✓
- `src/aponyx/data/bloomberg_securities.json` ✓
- `src/aponyx/data/bloomberg_instruments.json` ✓
- `src/aponyx/data/synthetic_params.json` ✓

### Use Cases

- Clean up before committing to ensure no runtime data is tracked
- Reset local environment to fresh state
- Remove old workflow results and cached data
- Free up disk space from generated files

**Note:** After running this script, regenerate synthetic data with:
```bash
uv run python scripts/generate_synthetic.py
```
