# Synthetic Data for Development

When Bloomberg Terminal is not available, use the synthetic data generator to create test data for workflow stages 2-5.

## Quick Start

```bash
# Generate 5 years of synthetic data
python src/aponyx/notebooks/generate_synthetic_data.py
```

Or from within Python/notebooks:

```python
from aponyx.notebooks.generate_synthetic_data import setup_synthetic_data

# Generate 5 years of data silently
setup_synthetic_data(years_of_history=5)
```

## Two Modes

### Bloomberg Mode (Production)
- Run `01_data_download.ipynb` to fetch real market data
- Cache saved to `data/cache/bloomberg/`
- Requires active Bloomberg Terminal session

### Synthetic Mode (Development)  
- Run `generate_synthetic_data.py` script
- Cache saved to `data/cache/file/`
- No Bloomberg required

## Auto-Detection

Notebooks `02_signal_computation.ipynb` and beyond automatically detect which cache is available:

1. Checks for Bloomberg cache first (`data/cache/bloomberg/`)
2. Falls back to file cache (`data/cache/file/`)
3. Raises clear error if neither exists

## Synthetic Data Properties

Generated data matches production schemas exactly:

- **CDX IG 5Y**: Mean-reverting spreads (~60 bps base, 5 bps volatility)
- **VIX**: Mean-reverting with spikes (~18 base, occasional jumps)
- **HYG ETF**: Geometric Brownian motion (~350 bps base, 15 bps volatility)

All data:
- ✓ DatetimeIndex with business day frequency
- ✓ Matches `CDXSchema`, `VIXSchema`, `ETFSchema`
- ✓ Fixed random seed (42) for reproducibility
- ✓ 5 years of history by default

## Development Workflow

```bash
# Step 0: Generate synthetic data (replaces step 1)
python src/aponyx/notebooks/generate_synthetic_data.py

# Step 2: Run signal computation
# (open 02_signal_computation.ipynb and run all cells)

# Step 3: Run suitability evaluation  
# (open 03_suitability_evaluation.ipynb and run all cells)

# Step 4-5: Continue as notebooks become available
```

## Customization

To modify parameters, call the script with different values:

```python
from aponyx.notebooks.generate_synthetic_data import setup_synthetic_data

# Generate 10 years instead of 5
setup_synthetic_data(years_of_history=10)
```

Or modify `src/aponyx/data/sample_data.py` for different statistical properties (volatility, mean levels, etc.).

## Production Deployment

When Bloomberg Terminal becomes available:

1. Install Bloomberg extra: `uv sync --extra bloomberg`
2. Run `01_data_download.ipynb` to fetch real data
3. Delete synthetic cache if desired: `rm -rf data/cache/file/`
4. Notebooks auto-detect Bloomberg cache and use it

Both caches can coexist — Bloomberg takes precedence when both exist.

## Benefits

- **Simple replacement** — One script replaces notebook 01  
- **No code changes** — Notebooks 02+ work identically  
- **Reproducible** — Fixed random seed ensures consistency  
- **Realistic** — Statistical properties match real market data  
- **Schema-compatible** — Ready for production data swap
