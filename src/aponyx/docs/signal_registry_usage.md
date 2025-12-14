````markdown
# Signal Registry Pattern - Usage Guide

## Overview

The signal registry infrastructure enables scalable signal research through a **four-stage transformation pipeline**:
1. **Indicator Transformations** — Raw economic metrics from market data
2. **Score Transformations** — Normalization (z-score, volatility adjustment)
3. **Signal Transformations** — Trading rules (bounds, neutral zones)
4. **Signals** — Composed from all three transformation stages

Add new signals by editing JSON catalogs instead of modifying code. Each signal is evaluated independently to establish clear performance attribution.

## Quick Start

### Basic Usage

```python
from aponyx.models import (
    IndicatorTransformationRegistry,
    ScoreTransformationRegistry,
    SignalTransformationRegistry,
    SignalRegistry,
)
from aponyx.models.signal_composer import compose_signal
from aponyx.config import (
    INDICATOR_TRANSFORMATION_PATH,
    SCORE_TRANSFORMATION_PATH,
    SIGNAL_TRANSFORMATION_PATH,
    SIGNAL_CATALOG_PATH,
)
from aponyx.backtest import run_backtest, BacktestConfig

# Load all four registries
indicator_reg = IndicatorTransformationRegistry(INDICATOR_TRANSFORMATION_PATH)
score_reg = ScoreTransformationRegistry(SCORE_TRANSFORMATION_PATH)
signal_trans_reg = SignalTransformationRegistry(SIGNAL_TRANSFORMATION_PATH)
signal_reg = SignalRegistry(SIGNAL_CATALOG_PATH)

# Prepare market data
market_data = {
    "cdx": cdx_df,  # Must have 'spread' column
    "vix": vix_df,  # Must have 'level' column  
    "etf": etf_df,  # Must have 'spread' column
}

# Compose a signal (four-stage pipeline)
signal = compose_signal(
    signal_name="cdx_etf_basis",
    market_data=market_data,
    indicator_registry=indicator_reg,
    score_registry=score_reg,
    signal_transformation_registry=signal_trans_reg,
    signal_registry=signal_reg,
)

# Run backtest
config = BacktestConfig(position_size_mm=10.0)
result = run_backtest(signal, cdx_df["spread"], config)
print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
```

## Adding a New Signal

### Step 1: Create Indicator Function (if needed)

Add to `src/aponyx/models/indicators.py`:

```python
def compute_my_new_indicator(
    cdx_df: pd.DataFrame,
    other_df: pd.DataFrame,
) -> pd.Series:
    """
    Compute my new indicator in basis points.
    
    Outputs economically interpretable values WITHOUT normalization.
    Score transformations are applied at signal composition layer.
    """
    # Return raw values in natural units (bps, ratio, etc.)
    return cdx_df["spread"] - other_df["spread"]
```

### Step 2: Register Indicator Transformation

Edit `src/aponyx/models/indicator_transformation.json`:

```json
{
  "name": "my_new_indicator",
  "description": "CDX-other spread differential in basis points",
  "compute_function_name": "compute_my_new_indicator",
  "data_requirements": {
    "cdx": "spread",
    "other": "spread"
  },
  "default_securities": {
    "cdx": "cdx_ig_5y",
    "other": "other_security"
  },
  "output_units": "basis_points",
  "parameters": {},
  "enabled": true
}
```

### Step 3: Define Signal (referencing all three transformations)

Edit `src/aponyx/models/signal_catalog.json`:

```json
{
  "name": "my_new_signal",
  "description": "Trading signal based on my indicator",
  "indicator_transformation": "my_new_indicator",
  "score_transformation": "z_score_20d",
  "signal_transformation": "passthrough",
  "enabled": true,
  "sign_multiplier": 1
}
```

### Step 4: Use the Signal

```python
# Registry automatically picks up the new signal
signal = compose_signal(
    signal_name="my_new_signal",
    market_data=market_data,
    indicator_registry=indicator_reg,
    score_registry=score_reg,
    signal_transformation_registry=signal_trans_reg,
    signal_registry=signal_reg,
)

# Run backtest to evaluate performance
config = BacktestConfig(position_size_mm=10.0)
result = run_backtest(signal, cdx_df["spread"], config)
print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
```

## Four-Stage Transformation Pipeline

Every signal is composed through four stages:

| Stage | Catalog | Purpose | Example |
|-------|---------|---------|---------|
| **Indicator** | `indicator_transformation.json` | Compute raw economic metric | Spread difference (bps) |
| **Score** | `score_transformation.json` | Normalize to common scale | Z-score over 20 days |
| **Signal** | `signal_transformation.json` | Apply trading rules | Bounds [-1.5, 1.5], neutral zone |
| **Composition** | `signal_catalog.json` | Reference all three | Links stages together |

### Transformation Catalog Files

**indicator_transformation.json** — Raw metrics:
```json
{
  "name": "cdx_etf_spread_diff",
  "compute_function_name": "compute_cdx_etf_spread_diff",
  "data_requirements": {"cdx": "spread", "etf": "spread"},
  "output_units": "basis_points"
}
```

**score_transformation.json** — Normalization:
```json
{
  "name": "z_score_20d",
  "transform_type": "z_score",
  "parameters": {"window": 20, "min_periods": 10}
}
```

**signal_transformation.json** — Trading rules:
```json
{
  "name": "bounded_1_5",
  "scaling": 1.0,
  "floor": -1.5,
  "cap": 1.5,
  "neutral_range": [-0.25, 0.25]
}
```

**signal_catalog.json** — Composition:
```json
{
  "name": "cdx_etf_basis",
  "indicator_transformation": "cdx_etf_spread_diff",
  "score_transformation": "z_score_20d",
  "signal_transformation": "passthrough",
  "sign_multiplier": 1
}
```

## Signal Catalog Schema

### SignalMetadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique signal identifier (snake_case) |
| `description` | string | Human-readable signal description |
| `indicator_transformation` | string | Reference to indicator_transformation.json |
| `score_transformation` | string | Reference to score_transformation.json |
| `signal_transformation` | string | Reference to signal_transformation.json |
| `enabled` | boolean | Whether to compute this signal |
| `sign_multiplier` | int | Sign adjustment (1 or -1) |

## Integration with Backtesting

The backtest layer accepts any signal series. Current `BacktestConfig` parameters:

```python
from aponyx.backtest import BacktestConfig, run_backtest

# Backtest configuration
config = BacktestConfig(
    position_size_mm=10.0,           # Notional in millions
    sizing_mode="proportional",       # 'binary' or 'proportional' (default)
    stop_loss_pct=5.0,               # Optional: stop at 5% loss
    take_profit_pct=10.0,            # Optional: take profit at 10%
    max_holding_days=None,           # Optional: max holding period
    transaction_cost_bps=1.0,        # Round-trip cost in bps
    dv01_per_million=475.0,          # DV01 for risk calculations ($475 per $1MM)
    signal_lag=1,                    # Days to lag signal (prevent look-ahead)
)

result = run_backtest(signal, cdx_df["spread"], config)
```

### Position Sizing Modes

**Proportional (default):** Position scales with signal magnitude
```python
config = BacktestConfig(
    position_size_mm=10.0,
    sizing_mode="proportional",  # Default: position = signal × 10MM
)
```

**Binary:** Full position for any non-zero signal
```python
config = BacktestConfig(
    position_size_mm=10.0,
    sizing_mode="binary",  # Position = ±10MM regardless of signal magnitude
)
```

## Runtime Overrides

Override transformation stages at compose time:

```python
# Use 60-day z-score instead of default 20-day
signal = compose_signal(
    signal_name="cdx_etf_basis",
    market_data=market_data,
    indicator_registry=indicator_reg,
    score_registry=score_reg,
    signal_transformation_registry=signal_trans_reg,
    signal_registry=signal_reg,
    score_transformation_override="z_score_60d",
)

# With intermediate stage inspection
result = compose_signal(
    signal_name="cdx_etf_basis",
    market_data=market_data,
    indicator_registry=indicator_reg,
    score_registry=score_reg,
    signal_transformation_registry=signal_trans_reg,
    signal_registry=signal_reg,
    include_intermediates=True,
)
print(result["indicator"].tail())  # Raw indicator
print(result["score"].tail())      # Normalized score
print(result["signal"].tail())     # Final signal
```

## Using Strategy Registry

Load strategy configurations from catalog:

```python
from aponyx.backtest import StrategyRegistry
from aponyx.config import STRATEGY_CATALOG_PATH

# Load strategies from catalog
strategy_reg = StrategyRegistry(STRATEGY_CATALOG_PATH)

# Get strategy metadata and convert to config
metadata = strategy_reg.get_metadata("balanced")
config = metadata.to_config()

# Override specific parameters
config = metadata.to_config(
    position_size_mm_override=20.0,  # Use 20MM instead of catalog default
)

result = run_backtest(signal, cdx_df["spread"], config)
```

## Best Practices

1. **Follow four-stage pipeline** — All signals use compose_signal() (no exceptions)
2. **Follow signal convention** — Positive = long credit risk (buy CDX)
3. **Log operations** using module-level logger with %-formatting
4. **Validate data requirements** are met before computing
5. **Include signal description** in catalog for documentation
6. **Test determinism** to ensure reproducible results
7. **Use runtime overrides** for experimentation without modifying catalogs

## Debugging Signals

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Signal computations will log details:
# DEBUG - Computing indicator: cdx_etf_spread_diff
# DEBUG - Applying score transformation: z_score_20d
# DEBUG - Applying signal transformation: passthrough
```

### Inspect Intermediate Values

```python
result = compose_signal(
    signal_name="cdx_etf_basis",
    market_data=market_data,
    indicator_registry=indicator_reg,
    score_registry=score_reg,
    signal_transformation_registry=signal_trans_reg,
    signal_registry=signal_reg,
    include_intermediates=True,
)

print("Indicator (raw bps):", result["indicator"].describe())
print("Score (normalized):", result["score"].describe())
print("Signal (final):", result["signal"].describe())
```

### Common Issues

**Signal returns all NaN values:**
```python
# Check data alignment
print(f"CDX: {cdx_df.index.min()} to {cdx_df.index.max()}")
print(f"ETF: {etf_df.index.min()} to {etf_df.index.max()}")

# Ensure indices overlap
```

**Signal not found in registry:**
```python
# List all enabled signals
enabled = signal_reg.get_enabled()
print(f"Enabled signals: {list(enabled.keys())}")
```

---

**Maintained by:** stabilefrisur  
**Last Updated:** December 13, 2025

````
