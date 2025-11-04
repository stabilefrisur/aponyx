# Signal Registry Pattern - Usage Guide

## Overview

The signal registry infrastructure enables scalable signal research by decoupling signal definitions from backtest logic. Add new signals by editing a JSON catalog instead of modifying code. Each signal is evaluated independently to establish clear performance attribution.

## Quick Start

### Basic Usage

```python
from pathlib import Path
from aponyx.models import (
    SignalRegistry,
    SignalConfig,
    compute_registered_signals,
)
from aponyx.backtest import run_backtest, BacktestConfig

# Load signal catalog
registry = SignalRegistry("src/aponyx/models/signal_catalog.json")

# Prepare market data
market_data = {
    "cdx": cdx_df,  # Must have 'spread' column
    "vix": vix_df,  # Must have 'level' column  
    "etf": etf_df,  # Must have 'spread' column
}

# Compute all enabled signals
signal_config = SignalConfig(lookback=20, min_periods=10)
signals = compute_registered_signals(registry, market_data, signal_config)

# Evaluate each signal independently
backtest_config = BacktestConfig(entry_threshold=1.5, exit_threshold=0.75)

for signal_name, signal_series in signals.items():
    result = run_backtest(signal_series, cdx_df["spread"], backtest_config)
    # Compute metrics from result
    from aponyx.backtest.metrics import compute_performance_metrics
    metrics = compute_performance_metrics(result.pnl["net_pnl"], result.positions["position"])
    print(f"{signal_name}: Sharpe={metrics.sharpe_ratio:.2f}")
```

## Adding a New Signal

### Step 1: Implement Compute Function

Add to `src/aponyx/models/signals.py`:

```python
def compute_my_new_signal(
    cdx_df: pd.DataFrame,
    other_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    Compute my new signal.
    
    Signal convention: positive = long credit risk (buy CDX).
    """
    if config is None:
        config = SignalConfig()
    
    logger.info("Computing my new signal: lookback=%d", config.lookback)
    
    # Your signal logic here
    raw_signal = ...
    
    # Z-score normalize
    normalized = (raw_signal - mean) / std
    
    logger.debug("Generated %d valid signals", normalized.notna().sum())
    return normalized
```

### Step 2: Register in Catalog

Edit `src/aponyx/models/signal_catalog.json`:

```json
[
  {
    "name": "my_new_signal",
    "description": "Brief description of what this signal captures",
    "compute_function_name": "compute_my_new_signal",
    "data_requirements": {
      "cdx": "spread",
      "other": "column_name"
    },
    "arg_mapping": ["cdx", "other"],
    "enabled": true
  }
]
```

### Step 3: Evaluate Independently

```python
# Registry automatically picks up the new signal
signals = compute_registered_signals(registry, market_data, config)
# Now includes "my_new_signal"

# Run backtest to evaluate performance
from aponyx.backtest import run_backtest, BacktestConfig

backtest_config = BacktestConfig(entry_threshold=1.5, exit_threshold=0.75)
result = run_backtest(signals["my_new_signal"], cdx_df["spread"], backtest_config)
print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
```

## Signal Catalog Schema

### SignalMetadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique signal identifier (snake_case) |
| `description` | string | Human-readable signal description |
| `compute_function_name` | string | Function name in `signals.py` module |
| `data_requirements` | dict | Map of data keys to required column names |
| `arg_mapping` | list | Ordered list of data keys for function arguments |
| `enabled` | boolean | Whether to compute this signal |

### Example Entry

```json
{
  "name": "cdx_vix_gap",
  "description": "Cross-asset risk sentiment gap between credit and equity vol",
  "compute_function_name": "compute_cdx_vix_gap",
  "data_requirements": {
    "cdx": "spread",
    "vix": "level"
  },
  "arg_mapping": ["cdx", "vix"],
  "enabled": true
}
```

## Experimentation Workflows

### Disable a Signal

Set `"enabled": false` in catalog JSON, then reload registry.

### Evaluate All Signals

Run backtests for all enabled signals to compare performance:

```python
from aponyx.backtest import run_backtest, BacktestConfig
from aponyx.backtest.metrics import compute_performance_metrics

# Compute all enabled signals
signals = compute_registered_signals(registry, market_data, signal_config)

# Backtest configuration
backtest_config = BacktestConfig(
    entry_threshold=1.5,
    exit_threshold=0.75,
    position_size=10.0,
    transaction_cost_bps=1.0,
)

# Evaluate each signal independently
results = {}
for signal_name, signal_series in signals.items():
    result = run_backtest(signal_series, cdx_df["spread"], backtest_config)
    metrics = compute_performance_metrics(result.pnl["net_pnl"], result.positions["position"])
    results[signal_name] = metrics
    
    print(f"{signal_name}:")
    print(f"  Sharpe: {metrics.sharpe_ratio:.2f}")
    print(f"  Max DD: ${metrics.max_drawdown:,.0f}")
    print(f"  Hit Rate: {metrics.hit_rate:.1%}")
```

### Focus on Single Signal

Evaluate one signal in detail:

```python
# Compute and backtest single signal
signal = compute_registered_signals(registry, market_data, signal_config)["cdx_etf_basis"]
result = run_backtest(signal, cdx_df["spread"], backtest_config)

# Detailed analysis
from aponyx.visualization import plot_signal, plot_pnl

plot_signal(signal, title="CDX-ETF Basis").show()
plot_pnl(result.pnl["cumulative_pnl"], title="Cumulative P&L").show()
```

### Run Subset of Signals

Modify catalog to disable unwanted signals, or manually filter:

```python
# Compute all signals
all_signals = compute_registered_signals(registry, market_data, config)

# Evaluate subset
signal_names = ["cdx_etf_basis", "spread_momentum"]

for name in signal_names:
    result = run_backtest(all_signals[name], cdx_df["spread"], backtest_config)
    from aponyx.backtest.metrics import compute_performance_metrics
    metrics = compute_performance_metrics(result.pnl["net_pnl"], result.positions["position"])
    print(f"{name}: Sharpe={metrics.sharpe_ratio:.2f}")
```

## Architecture Benefits

### Before (Hardcoded)

- Adding signal requires:
  1. Modify `signals.py` (compute function)
  2. Update call sites to include new signal
  3. Modify backtest scripts to test new signal
  4. Update tests

### After (Registry Pattern)

- Adding signal requires:
  1. Modify `signals.py` (compute function)
  2. Edit `signal_catalog.json` (add entry)
  3. Done - automatically included in batch computations

### Scalability

- **3 signals**: Both approaches work fine
- **10 signals**: Registry pattern helps organize research
- **20+ signals**: Registry essential for managing signal portfolio

## Integration with Backtesting

The backtest layer accepts any signal series for independent evaluation:

```python
from aponyx.backtest import BacktestConfig, run_backtest
from aponyx.backtest.metrics import compute_performance_metrics

# Compute signals using registry
signals = compute_registered_signals(registry, market_data, signal_config)

# Backtest configuration
bt_config = BacktestConfig(
    entry_threshold=1.5,
    exit_threshold=0.75,
    position_size=10.0,
    transaction_cost_bps=1.0,
)

# Evaluate each signal independently
for signal_name, signal_series in signals.items():
    result = run_backtest(signal_series, cdx_df["spread"], bt_config)
    metrics = compute_performance_metrics(result.pnl["net_pnl"], result.positions["position"])
    
    print(f"\n{signal_name}:")
    print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"  Total Return: ${metrics.total_return:,.0f}")
    print(f"  Max Drawdown: ${metrics.max_drawdown:,.0f}")
```

## Testing New Signals

```python
import pytest
from aponyx.models.signals import compute_my_new_signal
from aponyx.models.config import SignalConfig

def test_my_new_signal():
    # Generate test data
    cdx_df = ...
    other_df = ...
    
    config = SignalConfig(lookback=10)
    signal = compute_my_new_signal(cdx_df, other_df, config)
    
    # Validate
    assert isinstance(signal, pd.Series)
    assert signal.notna().sum() > 0
    
    # Test signal convention: positive = long credit
    # (Add specific logic tests)
```

## Best Practices

1. **Evaluate signals independently** to establish clear performance attribution
2. **Always z-score normalize signals** for comparability across different data regimes
3. **Follow signal convention**: positive = long credit risk (buy CDX)
4. **Log operations** using module-level logger with %-formatting
5. **Validate data requirements** are met before computing
6. **Include signal description** in catalog for documentation
7. **Test determinism** to ensure reproducible results
8. **Use explicit arg_mapping** to avoid parameter order confusion
9. **Compare signals on same backtest config** for fair performance comparison

## Debugging Signals

### Common Issues

**Signal returns all NaN values**
```python
# Check data alignment
print(f"CDX rows: {len(cdx_df)}, ETF rows: {len(etf_df)}")
print(f"CDX index: {cdx_df.index.min()} to {cdx_df.index.max()}")
print(f"ETF index: {etf_df.index.min()} to {etf_df.index.max()}")

# Solution: Ensure date indices overlap
aligned_start = max(cdx_df.index.min(), etf_df.index.min())
aligned_end = min(cdx_df.index.max(), etf_df.index.max())
```

**Signal not appearing in compute_registered_signals output**
```python
# Check if signal is enabled in catalog
registry = SignalRegistry("src/aponyx/models/signal_catalog.json")
catalog = registry.get_catalog()
enabled_signals = [s for s in catalog if s["enabled"]]
print(f"Enabled signals: {[s['name'] for s in enabled_signals]}")

# Check if function exists
from aponyx.models import signals as sig_module
print(f"Has function: {hasattr(sig_module, 'compute_my_signal')}")
```

**Data requirements not met**
```python
# Registry validates data requirements before computing
# Check error message for missing columns:
# ValueError: Missing required column 'spread' in data['cdx']

# Solution: Ensure data dict has all required DataFrames
market_data = {
    "cdx": cdx_df,  # Must have columns specified in data_requirements
    "vix": vix_df,
    "etf": etf_df,
}
```

### Debugging Tips

**Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now signal computations will log details:
# DEBUG - Computing CDX-ETF basis: cdx_rows=252, etf_rows=252
# DEBUG - Generated 242 valid signals (10 NaN due to rolling window)
```

**Inspect intermediate values:**
```python
# Modify signal function temporarily to log intermediate steps
def compute_my_signal(cdx_df, etf_df, config=None):
    logger.info("Computing signal...")
    
    raw_diff = cdx_df['spread'] - etf_df['spread']
    logger.debug("Raw diff range: %.2f to %.2f", raw_diff.min(), raw_diff.max())
    
    zscore = (raw_diff - raw_diff.rolling(20).mean()) / raw_diff.rolling(20).std()
    logger.debug("Z-score range: %.2f to %.2f", zscore.min(), zscore.max())
    
    return zscore
```

**Test with synthetic data:**
```python
# Create simple test case
import pandas as pd
import numpy as np

dates = pd.date_range('2024-01-01', periods=100)
cdx_df = pd.DataFrame({'spread': np.arange(100)}, index=dates)
etf_df = pd.DataFrame({'spread': np.arange(100) * 0.5}, index=dates)

# Signal should produce predictable pattern
signal = compute_my_signal(cdx_df, etf_df)
print(signal.describe())
```

## Versioning Signals

### When to Version

Create a new signal version when:
- Changing calculation methodology significantly
- Modifying normalization approach
- Updating data requirements

**Don't version for:**
- Minor bug fixes (fix in place)
- Performance optimizations (same output)
- Code refactoring (same logic)

### Versioning Strategy

**Option 1: Suffix versioning (recommended)**
```json
{
  "name": "cdx_etf_basis_v2",
  "description": "CDX-ETF basis with improved normalization (v2)",
  "compute_function_name": "compute_cdx_etf_basis_v2",
  ...
}
```

**Option 2: Deprecation pattern**
```json
{
  "name": "cdx_etf_basis_old",
  "description": "DEPRECATED: Use cdx_etf_basis_v2",
  "enabled": false,
  ...
},
{
  "name": "cdx_etf_basis_v2",
  "description": "CDX-ETF basis with improved normalization",
  "enabled": true,
  ...
}
```

### Backtest Comparison Across Versions

```python
# Load historical catalog with old version
old_registry = SignalRegistry("archive/signal_catalog_2024_q3.json")
old_signals = compute_registered_signals(old_registry, market_data, config)

# Compare with current version
new_registry = SignalRegistry("src/aponyx/models/signal_catalog.json")
new_signals = compute_registered_signals(new_registry, market_data, config)

# Backtest both for performance comparison
for signal_name in ["cdx_etf_basis", "cdx_etf_basis_v2"]:
    if signal_name in old_signals:
        result_old = run_backtest(old_signals[signal_name], cdx_df["spread"], config)
        print(f"{signal_name} (old): Sharpe={result_old.metrics['sharpe_ratio']:.2f}")
    
    if signal_name in new_signals:
        result_new = run_backtest(new_signals[signal_name], cdx_df["spread"], config)
        print(f"{signal_name} (new): Sharpe={result_new.metrics['sharpe_ratio']:.2f}")
```

## Direct Signal Computation

You can also call compute functions directly without the registry:

```python
# Direct computation (bypassing registry)
from aponyx.models.signals import compute_cdx_etf_basis
from aponyx.models.config import SignalConfig

config = SignalConfig(lookback=20, min_periods=10)
signal = compute_cdx_etf_basis(cdx_df, etf_df, config)

# Then backtest directly
from aponyx.backtest import run_backtest, BacktestConfig

bt_config = BacktestConfig(entry_threshold=1.5, exit_threshold=0.75)
result = run_backtest(signal, cdx_df["spread"], bt_config)
```

This is useful for quick experiments or when you need more control over signal parameters.

---

**Maintained by stabilefrisur**  
Last Updated: October 31, 2025
