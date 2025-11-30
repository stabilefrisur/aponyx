# Quickstart: Indicator-Signal Separation

**Feature**: Indicator-Signal Separation  
**Date**: 2025-11-30  
**Audience**: Developers implementing or using the indicator-signal separation feature

---

## Overview

This guide explains how to:
1. Define a new reusable indicator
2. Create a signal from indicators using transformations
3. Test indicator and signal computations independently
4. Migrate existing signals to the new pattern

---

## 1. Defining a New Indicator

### Step 1.1: Implement the Compute Function

Add your indicator computation function to `src/aponyx/models/indicators.py`:

```python
def compute_cdx_etf_spread_diff(
    cdx_df: pd.DataFrame,
    etf_df: pd.DataFrame,
    parameters: dict[str, Any],
) -> pd.Series:
    """
    Compute CDX spread minus ETF spread in basis points.
    
    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with 'spread' column
    etf_df : pd.DataFrame
        ETF spread data with 'spread' column
    parameters : dict[str, Any]
        Indicator parameters (unused for this simple indicator)
    
    Returns
    -------
    pd.Series
        Spread difference in basis points
        
    Notes
    -----
    Output units: basis_points
    Positive values: CDX spreads wider than ETF spreads
    Economic interpretation: Positive = CDX expensive vs ETF
    """
    logger.info(
        "Computing CDX-ETF spread difference: cdx_rows=%d, etf_rows=%d",
        len(cdx_df),
        len(etf_df),
    )
    
    # Align data to common dates
    cdx_spread = cdx_df["spread"]
    etf_spread = etf_df["spread"].reindex(cdx_df.index, method="ffill")
    
    # Compute raw difference (no normalization)
    spread_diff = cdx_spread - etf_spread
    
    valid_count = spread_diff.notna().sum()
    logger.debug("Generated %d valid spread difference values", valid_count)
    
    return spread_diff
```

**Key Guidelines**:
- **Output in interpretable units**: basis points, ratios, percentages (NOT z-scores)
- **No normalization**: Indicators compute raw metrics, signals apply normalization
- **Document economic meaning**: What does positive/negative mean?
- **Use logger**: INFO for user-facing operations, DEBUG for details

### Step 1.2: Register in Indicator Catalog

Add entry to `src/aponyx/models/indicator_catalog.json`:

```json
{
  "name": "cdx_etf_spread_diff",
  "description": "CDX spread minus ETF spread in basis points",
  "compute_function_name": "compute_cdx_etf_spread_diff",
  "data_requirements": {
    "cdx": "spread",
    "etf": "spread"
  },
  "default_securities": {
    "cdx": "cdx_ig_5y",
    "etf": "lqd"
  },
  "output_units": "basis_points",
  "parameters": {},
  "enabled": true
}
```

**Field Descriptions**:
- `name`: Unique identifier (lowercase, underscores only)
- `compute_function_name`: Function name in indicators.py
- `data_requirements`: What instrument types and fields are needed?
- `default_securities`: Which securities to use by default?
- `output_units`: What units for interpretation? (basis_points, ratio, percentage, etc.)
- `parameters`: Fixed computation parameters (empty if none)

### Step 1.3: Write Unit Test

Add test to `tests/models/test_indicators.py`:

```python
def test_compute_cdx_etf_spread_diff():
    """Test CDX-ETF spread difference computation."""
    # Create sample data
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    cdx_df = pd.DataFrame(
        {"spread": np.random.uniform(50, 150, 100)},
        index=dates
    )
    etf_df = pd.DataFrame(
        {"spread": np.random.uniform(40, 140, 100)},
        index=dates
    )
    
    # Compute indicator
    result = compute_cdx_etf_spread_diff(cdx_df, etf_df, {})
    
    # Validate
    assert isinstance(result, pd.Series)
    assert len(result) == len(cdx_df)
    assert result.notna().sum() > 0
    
    # Check economic interpretation
    # When CDX spread > ETF spread, difference should be positive
    test_idx = dates[50]
    cdx_val = cdx_df.loc[test_idx, "spread"]
    etf_val = etf_df.loc[test_idx, "spread"]
    expected = cdx_val - etf_val
    assert abs(result.loc[test_idx] - expected) < 0.01
```

**Test Guidelines**:
- Test with synthetic data (reproducible)
- Validate output type, length, non-NaN count
- Verify economic interpretation (spot check calculations)
- NO backtest or signal context needed

---

## 2. Creating a Signal from Indicators

### Step 2.1: Define Transformation (if needed)

If you need a new transformation, add to `src/aponyx/models/transformation_catalog.json`:

```json
{
  "name": "z_score_20d",
  "description": "Z-score normalization over 20-day rolling window",
  "transform_type": "z_score",
  "parameters": {
    "window": 20,
    "min_periods": 10
  },
  "enabled": true
}
```

**Common Transformations** (already available):
- `z_score`: Rolling z-score normalization
- `normalized_change`: Change divided by rolling volatility
- `diff`: First difference
- `pct_change`: Percent change
- `log_return`: Log returns

### Step 2.2: Register Signal in Catalog

Add entry to `src/aponyx/models/signal_catalog.json`:

```json
{
  "name": "cdx_etf_basis",
  "description": "Flow-driven mispricing signal from CDX-ETF basis",
  "indicator_dependencies": ["cdx_etf_spread_diff"],
  "transformations": ["z_score_20d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

**Field Descriptions**:
- `indicator_dependencies`: List of indicator names this signal uses
- `transformations`: List of transformations to apply (in order)
- `composition_logic`: Optional Python expression for combining multiple indicators
- `sign_multiplier`: +1 (no change) or -1 (invert sign)

**Example with Multiple Indicators**:

```json
{
  "name": "cdx_etf_ratio_signal",
  "description": "Ratio-based mispricing signal",
  "indicator_dependencies": ["cdx_spread", "etf_spread"],
  "transformations": ["z_score_20d"],
  "composition_logic": "cdx_spread / etf_spread",
  "enabled": true,
  "sign_multiplier": 1
}
```

### Step 2.3: Compute Signal

Use the high-level API:

```python
from aponyx.models.signal_composer import compose_signal

# Prepare market data
market_data = {
    "cdx": cdx_df,  # Must have 'spread' column
    "etf": etf_df,  # Must have 'spread' column
}

# Compose signal (indicators computed and cached automatically)
signal = compose_signal("cdx_etf_basis", market_data)

# Signal is z-score normalized, ready for backtesting
print(signal.head())
```

**What Happens Internally**:
1. SignalRegistry retrieves signal metadata
2. For each indicator dependency:
   - Check cache (if use_cache=True)
   - Compute if cache miss
   - Save to cache
3. Apply transformations in order
4. Apply sign_multiplier
5. Return signal series

---

## 3. Testing Indicator-Signal Separation

### Test Indicator Independently

```python
def test_indicator_independence():
    """Verify indicator can be computed without signal context."""
    # Load market data
    cdx_df = load_cdx_data()
    etf_df = load_etf_data()
    
    # Compute indicator directly
    indicator = compute_cdx_etf_spread_diff(cdx_df, etf_df, {})
    
    # Validate output units
    assert indicator.dtype == np.float64
    
    # Check interpretability (can you understand raw values?)
    mean_diff = indicator.mean()
    assert -50 < mean_diff < 50  # Reasonable bps range
```

### Test Signal Composition

```python
def test_signal_composition():
    """Verify signal correctly composes from indicators."""
    market_data = {"cdx": cdx_df, "etf": etf_df}
    
    # Compose signal
    signal = compose_signal("cdx_etf_basis", market_data)
    
    # Validate normalization applied
    assert abs(signal.mean()) < 0.5  # Should be near zero (z-score)
    assert 0.5 < signal.std() < 1.5   # Should be near 1.0 (z-score)
```

### Test Caching Behavior

```python
def test_indicator_caching():
    """Verify indicator caching works correctly."""
    market_data = {"cdx": cdx_df, "etf": etf_df}
    
    # Clear cache
    invalidate_indicator_cache()
    
    # First computation (cache miss)
    start = time.time()
    signal1 = compose_signal("cdx_etf_basis", market_data, use_cache=True)
    time1 = time.time() - start
    
    # Second computation (cache hit)
    start = time.time()
    signal2 = compose_signal("cdx_etf_basis", market_data, use_cache=True)
    time2 = time.time() - start
    
    # Verify cache speedup
    assert time2 < time1 * 0.5  # At least 50% faster
    
    # Verify identical results
    pd.testing.assert_series_equal(signal1, signal2)
```

---

## 4. Migrating Existing Signals

### Step 4.1: Identify Indicator Logic

For existing signal `compute_cdx_vix_gap()`:

```python
# BEFORE: Everything in one function
def compute_cdx_vix_gap(cdx_df, vix_df, config):
    # 1. Compute deviations (INDICATOR LOGIC)
    cdx_dev = cdx_df["spread"] - cdx_df["spread"].rolling(20).mean()
    vix_dev = vix_df["level"] - vix_df["level"].rolling(20).mean()
    gap = cdx_dev - vix_dev
    
    # 2. Normalize (SIGNAL LOGIC)
    gap_mean = gap.rolling(20).mean()
    gap_std = gap.rolling(20).std()
    signal = (gap - gap_mean) / gap_std
    
    return signal
```

### Step 4.2: Extract Indicator

Create new indicator function:

```python
# NEW: Indicator computes raw gap
def compute_cdx_vix_deviation_gap(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    parameters: dict[str, Any],
) -> pd.Series:
    """
    Compute gap between CDX and VIX deviations from their means.
    
    Returns
    -------
    pd.Series
        Deviation gap in basis points
        
    Notes
    -----
    Output units: basis_points
    Positive values: Credit stress > equity stress
    """
    lookback = parameters.get("lookback", 20)
    
    # Compute deviations
    cdx_dev = cdx_df["spread"] - cdx_df["spread"].rolling(lookback).mean()
    vix_dev = vix_df["level"] - vix_df["level"].rolling(lookback).mean()
    
    # Return raw gap (no normalization)
    return cdx_dev - vix_dev
```

### Step 4.3: Register Indicator and Signal

**indicator_catalog.json**:
```json
{
  "name": "cdx_vix_deviation_gap_20d",
  "description": "Gap between CDX and VIX deviations from 20-day means",
  "compute_function_name": "compute_cdx_vix_deviation_gap",
  "data_requirements": {
    "cdx": "spread",
    "vix": "level"
  },
  "default_securities": {
    "cdx": "cdx_ig_5y",
    "vix": "vix"
  },
  "output_units": "basis_points",
  "parameters": {"lookback": 20},
  "enabled": true
}
```

**signal_catalog.json** (NEW pattern):
```json
{
  "name": "cdx_vix_gap",
  "description": "Cross-asset risk sentiment signal",
  "indicator_dependencies": ["cdx_vix_deviation_gap_20d"],
  "transformations": ["z_score_20d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

### Step 4.4: Maintain Backward Compatibility (Facade)

Keep old function as wrapper:

```python
# LEGACY: Backward compatibility facade
def compute_cdx_vix_gap(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    config: SignalConfig | None = None,
) -> pd.Series:
    """
    LEGACY: Compute CDX-VIX gap signal.
    
    This function is maintained for backward compatibility.
    New code should use: compose_signal("cdx_vix_gap", market_data)
    """
    market_data = {"cdx": cdx_df, "vix": vix_df}
    return compose_signal("cdx_vix_gap", market_data, use_cache=True)
```

### Step 4.5: Validate Migration

```python
def test_migration_produces_identical_results():
    """Verify refactored signal matches legacy implementation."""
    # Compute with legacy function
    legacy_signal = compute_cdx_vix_gap(cdx_df, vix_df, config)
    
    # Compute with new composition
    market_data = {"cdx": cdx_df, "vix": vix_df}
    new_signal = compose_signal("cdx_vix_gap", market_data)
    
    # Should be identical
    pd.testing.assert_series_equal(legacy_signal, new_signal)
```

---

## 5. Common Patterns

### Pattern: Single Indicator, Single Transformation

**Use Case**: Simple normalization of one indicator

```json
{
  "name": "spread_momentum",
  "indicator_dependencies": ["spread_change_5d"],
  "transformations": ["volatility_adjust_20d"],
  "enabled": true
}
```

### Pattern: Multiple Indicators, Combined

**Use Case**: Ratio or difference of two indicators

```json
{
  "name": "basis_ratio",
  "indicator_dependencies": ["cdx_spread", "etf_spread"],
  "transformations": ["z_score_20d"],
  "composition_logic": "cdx_spread / etf_spread",
  "enabled": true
}
```

### Pattern: Indicator with Different Parameters

**Use Case**: Test same indicator with different lookback windows

```json
// indicator_catalog.json - Define both versions
[
  {
    "name": "spread_momentum_5d",
    "compute_function_name": "compute_spread_momentum",
    "parameters": {"lookback": 5},
    ...
  },
  {
    "name": "spread_momentum_10d",
    "compute_function_name": "compute_spread_momentum",
    "parameters": {"lookback": 10},
    ...
  }
]

// signal_catalog.json - Create signals from each
[
  {
    "name": "momentum_fast",
    "indicator_dependencies": ["spread_momentum_5d"],
    "transformations": ["z_score_20d"]
  },
  {
    "name": "momentum_slow",
    "indicator_dependencies": ["spread_momentum_10d"],
    "transformations": ["z_score_20d"]
  }
]
```

---

## 6. Troubleshooting

### Issue: "Indicator not found in registry"

**Cause**: Indicator name in signal catalog doesn't match indicator_catalog.json

**Solution**: Verify exact name match (case-sensitive, underscores)

```python
# Check available indicators
registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
print(registry.get_enabled())  # List all enabled indicators
```

### Issue: "Compute function not found"

**Cause**: Function name in catalog doesn't match function in indicators.py

**Solution**: Verify function exists and name matches exactly

```python
# Check if function exists
from aponyx.models import indicators
assert hasattr(indicators, "compute_my_indicator")
```

### Issue: Cache not invalidating after indicator change

**Cause**: Cache uses data hash, not indicator definition hash

**Solution**: Manually invalidate cache after changing indicator code

```python
from aponyx.models.cache import invalidate_indicator_cache

# Invalidate specific indicator
invalidate_indicator_cache("my_indicator")

# Or invalidate all indicators
invalidate_indicator_cache()
```

### Issue: Signal produces unexpected values

**Cause**: Indicator outputs wrong units or transformation incorrect

**Solution**: Test indicator and transformation independently

```python
# Test indicator in isolation
indicator = compute_indicator("my_indicator", market_data, use_cache=False)
print(f"Indicator mean: {indicator.mean()}, std: {indicator.std()}")
print(f"Units: {registry.get_metadata('my_indicator').output_units}")

# Test transformation separately
from aponyx.data.transforms import apply_transform
normalized = apply_transform(indicator, "z_score", window=20)
print(f"Normalized mean: {normalized.mean()}, std: {normalized.std()}")
```

---

## 7. Best Practices

### ✅ DO

- **Define indicators in interpretable units** (bps, ratios, percentages)
- **Test indicators independently** before using in signals
- **Use descriptive names** that indicate economic meaning
- **Document output units** in indicator metadata
- **Cache aggressively** for performance
- **Write unit tests** for each indicator

### ❌ DON'T

- **Don't normalize in indicators** (use transformations in signals)
- **Don't skip catalog registration** (use the registry pattern)
- **Don't hardcode parameters** in functions (use catalog parameters)
- **Don't mix indicator and signal logic** in one function
- **Don't forget to invalidate cache** after changing indicator code
- **Don't test indicators through backtest** (test directly)

---

## 8. Next Steps

After implementing your indicator and signal:

1. **Run tests**: `pytest tests/models/test_indicators.py -v`
2. **Validate caching**: Check `data/cache/indicators/` for cache files
3. **Query dependencies**: Use `registry.get_dependent_signals()`
4. **Create backtest**: Use signal in workflow (see examples/)
5. **Monitor performance**: Check cache hit rates in logs

---

**Questions?** See:
- [data-model.md](./data-model.md) - Entity definitions and relationships
- [contracts/function_signatures.md](./contracts/function_signatures.md) - Complete API reference
- [research.md](./research.md) - Design decisions and rationale
