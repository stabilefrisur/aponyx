# Quick Start: Signal Creation (Post-Cleanup)

**Feature**: Remove Legacy Compatibility from Indicator-Signal Separation  
**Date**: December 1, 2025  
**Audience**: Researchers creating new trading signals

## Overview

This guide shows the **ONLY** way to create trading signals in aponyx after the legacy compatibility removal. All signals MUST use the indicator + transformation composition pattern.

## Legacy Pattern (NO LONGER SUPPORTED)

**❌ DO NOT DO THIS** - This pattern has been removed:

```python
# ❌ REMOVED - This function pattern no longer exists
def compute_my_signal(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    config: SignalConfig,
) -> pd.Series:
    """Compute my custom signal."""
    # ... signal computation logic ...
    return signal

# ❌ REMOVED - This catalog entry no longer works
{
  "name": "my_signal",
  "compute_function_name": "compute_my_signal",  # ❌ Field removed
  "data_requirements": {"cdx": "spread", "vix": "level"},  # ❌ Field removed
  "arg_mapping": ["cdx", "vix"],  # ❌ Field removed
  "enabled": true
}
```

**Why removed**: This pattern mixed indicator computation with signal transformation, making it impossible to reuse computations across different signals. Per Constitution Principle VIII, we do not support backward compatibility.

## Current Pattern (ONLY WAY TO CREATE SIGNALS)

### Three-Step Process

1. **Define Indicator** - Compute economically interpretable market metric
2. **Define Transformation** (optional) - Create reusable transformation if needed
3. **Define Signal** - Combine indicator + transformation in catalog

### Step 1: Define Indicator

**File**: `src/aponyx/models/indicator_catalog.json`

Add entry for your indicator:

```json
{
  "name": "my_custom_indicator",
  "description": "CDX-VIX deviation gap over 20-day window",
  "compute_function_name": "compute_my_custom_indicator",
  "data_requirements": {
    "cdx": "spread",
    "vix": "level"
  },
  "default_securities": {
    "cdx": "cdx_ig_5y",
    "vix": "vix"
  },
  "output_units": "basis_points",
  "parameters": {
    "lookback": 20
  },
  "enabled": true
}
```

**File**: `src/aponyx/models/indicators.py`

Implement the indicator function:

```python
def compute_my_custom_indicator(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    params: dict[str, Any],
) -> pd.Series:
    """
    Compute CDX-VIX deviation gap.
    
    Returns economically interpretable values in basis points.
    Does NOT apply z-score normalization (that's for transformations).
    
    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with 'spread' column.
    vix_df : pd.DataFrame
        VIX level data with 'level' column.
    params : dict[str, Any]
        Computation parameters from catalog.
        Expected keys: 'lookback'
    
    Returns
    -------
    pd.Series
        Deviation gap in basis points (interpretable units).
    """
    lookback = params["lookback"]
    
    # Compute CDX deviation from its rolling mean
    cdx_mean = cdx_df["spread"].rolling(lookback).mean()
    cdx_deviation = cdx_df["spread"] - cdx_mean
    
    # Compute VIX deviation from its rolling mean
    vix_mean = vix_df["level"].rolling(lookback).mean()
    vix_deviation = vix_df["level"] - vix_mean
    
    # Gap = CDX stress - VIX stress
    # Positive = credit stress exceeds equity stress
    gap = cdx_deviation - vix_deviation
    
    return gap
```

**Key principles**:
- Return economically interpretable values (basis points, ratios, percentage, etc.)
- Do NOT apply z-score normalization (that's for transformations)
- Use `params` dict for all computation parameters
- Follow signal sign convention (positive = long credit risk)

### Step 2: Define Transformation (Optional)

**Skip this step if you're using an existing transformation** (z_score_20d, z_score_60d, volatility_adjust_20d).

**File**: `src/aponyx/models/transformation_catalog.json`

```json
{
  "name": "my_custom_transform",
  "description": "Custom transformation with specific parameters",
  "transform_type": "z_score",
  "parameters": {
    "window": 30,
    "min_periods": 15
  },
  "enabled": true
}
```

Most signals can use existing transformations, so this step is rarely needed.

### Step 3: Define Signal

**File**: `src/aponyx/models/signal_catalog.json`

Add entry combining your indicator with transformation:

```json
{
  "name": "my_signal",
  "description": "Cross-asset risk sentiment divergence signal",
  "indicator_dependencies": ["my_custom_indicator"],
  "transformations": ["z_score_60d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

**That's it!** No Python code needed for the signal itself.

## Complete Example: Creating a New Signal

### Scenario

Create a signal that captures the percentile rank spread between CDX IG and CDX HY indices.

### Implementation

#### 1. Define Indicator

**Add to `indicator_catalog.json`**:

```json
{
  "name": "cdx_ig_hy_percentile_gap",
  "description": "Gap between CDX IG and HY percentile ranks over 60-day window",
  "compute_function_name": "compute_cdx_ig_hy_percentile_gap",
  "data_requirements": {
    "cdx_ig": "spread",
    "cdx_hy": "spread"
  },
  "default_securities": {
    "cdx_ig": "cdx_ig_5y",
    "cdx_hy": "cdx_hy_5y"
  },
  "output_units": "percentage",
  "parameters": {
    "window": 60
  },
  "enabled": true
}
```

**Add to `indicators.py`**:

```python
def compute_cdx_ig_hy_percentile_gap(
    cdx_ig_df: pd.DataFrame,
    cdx_hy_df: pd.DataFrame,
    params: dict[str, Any],
) -> pd.Series:
    """
    Compute gap between CDX IG and HY percentile ranks.
    
    Positive values → IG relatively wide (defensive positioning)
    Negative values → HY relatively wide (risk-on positioning)
    
    Parameters
    ----------
    cdx_ig_df : pd.DataFrame
        CDX IG spread data with 'spread' column.
    cdx_hy_df : pd.DataFrame
        CDX HY spread data with 'spread' column.
    params : dict[str, Any]
        Must contain 'window' key for percentile rank window.
    
    Returns
    -------
    pd.Series
        Percentile rank gap in percentage points (-100 to +100).
    """
    window = params["window"]
    
    # Compute percentile ranks over rolling window
    ig_pct = cdx_ig_df["spread"].rolling(window).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100
    )
    
    hy_pct = cdx_hy_df["spread"].rolling(window).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100
    )
    
    # Gap: positive when IG is at higher percentile than HY
    gap = ig_pct - hy_pct
    
    return gap
```

#### 2. Define Signal

**Add to `signal_catalog.json`**:

```json
{
  "name": "ig_hy_spread_signal",
  "description": "Relative value signal between IG and HY credit",
  "indicator_dependencies": ["cdx_ig_hy_percentile_gap"],
  "transformations": ["z_score_20d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

#### 3. Use the Signal

```python
from aponyx.models import SignalRegistry, compute_registered_signals, SignalConfig
from aponyx.data import fetch_cdx, FileSource

# Load data
cdx_ig_df = fetch_cdx(FileSource("data/raw/cdx_ig.parquet"), security="cdx_ig_5y")
cdx_hy_df = fetch_cdx(FileSource("data/raw/cdx_hy.parquet"), security="cdx_hy_5y")

market_data = {
    "cdx_ig": cdx_ig_df,
    "cdx_hy": cdx_hy_df,
}

# Compute signal
registry = SignalRegistry(SIGNAL_CATALOG_PATH)
signals = compute_registered_signals(registry, market_data, SignalConfig())

# Access your signal
my_signal = signals["ig_hy_spread_signal"]
```

## Multi-Indicator Signals

For signals that combine multiple indicators:

### Example: Relative Value Signal

**Indicators** (already defined):
- `cdx_ig_spread` - CDX IG 5Y spread level
- `cdx_hy_spread` - CDX HY 5Y spread level

**Signal Definition**:

```json
{
  "name": "ig_hy_ratio_signal",
  "description": "IG/HY spread ratio for relative value",
  "indicator_dependencies": ["cdx_ig_spread", "cdx_hy_spread"],
  "transformations": ["z_score_20d"],
  "composition_logic": "cdx_ig_spread / cdx_hy_spread",
  "enabled": true,
  "sign_multiplier": 1
}
```

**How it works**:
1. Compute both indicators independently
2. Apply `composition_logic` to combine them (division creates ratio)
3. Apply transformations to the combined result (z-score normalization)

**`composition_logic` rules**:
- Python expression evaluated with indicator outputs as variables
- Variable names match indicator names from `indicator_dependencies`
- Result must be a pd.Series
- Common operations: `+`, `-`, `*`, `/`, `**`

## Sign Convention

All signals MUST follow the aponyx sign convention:
- **Positive values** → Long credit risk (buy CDX = sell protection)
- **Negative values** → Short credit risk (sell CDX = buy protection)

If your indicator naturally produces the inverse sign:
- Use `sign_multiplier: -1` in signal catalog entry
- Do NOT negate in indicator code (keep indicator interpretable)

Example:
```json
{
  "name": "inverse_vix_signal",
  "description": "Inverted VIX for short-vol strategy",
  "indicator_dependencies": ["vix_level_deviation"],
  "transformations": ["z_score_60d"],
  "enabled": true,
  "sign_multiplier": -1  // ← Inverts sign after transformation
}
```

## Testing Your Signal

### 1. Test Indicator Computation

```python
def test_my_custom_indicator():
    """Test indicator computes correctly."""
    from aponyx.models.indicators import compute_my_custom_indicator
    
    # Create synthetic data
    cdx_df = pd.DataFrame({"spread": [100, 102, 104]}, index=pd.date_range("2024-01-01", periods=3))
    vix_df = pd.DataFrame({"level": [15, 16, 17]}, index=pd.date_range("2024-01-01", periods=3))
    
    # Compute indicator
    result = compute_my_custom_indicator(cdx_df, vix_df, {"lookback": 2})
    
    # Verify output type and shape
    assert isinstance(result, pd.Series)
    assert len(result) == 3
    
    # Verify economically interpretable units (not z-scores)
    assert result.abs().max() < 1000  # Should be in basis points, not z-scores
```

### 2. Test Signal Registry

```python
def test_my_signal_in_registry():
    """Test signal loads from registry."""
    from aponyx.models import SignalRegistry
    from aponyx.config import SIGNAL_CATALOG_PATH
    
    registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    
    # Verify signal exists
    assert "my_signal" in registry.get_all()
    
    # Verify metadata
    metadata = registry.get_metadata("my_signal")
    assert metadata.indicator_dependencies == ["my_custom_indicator"]
    assert metadata.transformations == ["z_score_60d"]
```

### 3. Test End-to-End Signal Computation

```python
def test_my_signal_computation():
    """Test signal computes end-to-end."""
    from aponyx.models import SignalRegistry, compute_registered_signals, SignalConfig
    
    # Create synthetic market data
    market_data = {
        "cdx": generate_synthetic_cdx(n_days=252),
        "vix": generate_synthetic_vix(n_days=252),
    }
    
    # Compute signals
    registry = SignalRegistry(SIGNAL_CATALOG_PATH)
    signals = compute_registered_signals(registry, market_data, SignalConfig())
    
    # Verify signal computed
    assert "my_signal" in signals
    assert signals["my_signal"].notna().sum() > 0
    
    # Verify z-score normalization applied
    valid_signal = signals["my_signal"].dropna()
    assert abs(valid_signal.mean()) < 0.5  # Should have mean ~0
    assert 0.7 < valid_signal.std() < 1.5  # Should have std ~1
```

## Common Mistakes

### ❌ Mistake 1: Z-Score in Indicator

```python
# ❌ WRONG - Don't normalize in indicator
def compute_my_indicator(cdx_df, params):
    raw_value = cdx_df["spread"].pct_change(5)
    # ❌ DON'T DO THIS:
    z_score = (raw_value - raw_value.mean()) / raw_value.std()
    return z_score
```

**Why wrong**: Indicators should return economically interpretable values. Z-score normalization is a transformation's job.

**✅ Correct**:
```python
def compute_my_indicator(cdx_df, params):
    # Return interpretable percentage change
    return cdx_df["spread"].pct_change(5) * 100  # In percentage points
```

### ❌ Mistake 2: Using compute_function_name

```json
{
  "name": "my_signal",
  "compute_function_name": "compute_my_signal",  // ❌ Field removed
  "enabled": true
}
```

**Why wrong**: This field has been removed. System will raise ValueError on catalog load.

**✅ Correct**:
```json
{
  "name": "my_signal",
  "indicator_dependencies": ["my_indicator"],  // ✅ Use indicators
  "transformations": ["z_score_20d"],          // ✅ Use transformations
  "enabled": true
}
```

### ❌ Mistake 3: Empty Dependencies

```json
{
  "name": "my_signal",
  "indicator_dependencies": [],  // ❌ Cannot be empty
  "transformations": [],          // ❌ Cannot be empty
  "enabled": true
}
```

**Why wrong**: Both fields are now required and must have at least one element.

**✅ Correct**:
```json
{
  "name": "my_signal",
  "indicator_dependencies": ["my_indicator"],  // ✅ At least one
  "transformations": ["z_score_20d"],          // ✅ At least one
  "enabled": true
}
```

## Reference: Existing Transformations

You can use these transformations without defining new ones:

| Name | Transform Type | Parameters | Use Case |
|------|----------------|------------|----------|
| `z_score_20d` | z_score | window=20, min_periods=10 | Short-term normalization |
| `z_score_60d` | z_score | window=60, min_periods=30 | Medium-term normalization |
| `volatility_adjust_20d` | normalized_change | window=20 | Volatility-scaled momentum |

See `transformation_catalog.json` for complete list.

## Reference: Existing Indicators

Reuse these indicators in your signals:

| Name | Output Units | Data Requirements | Use Case |
|------|--------------|-------------------|----------|
| `cdx_etf_spread_diff` | basis_points | cdx, etf | Flow-driven mispricing |
| `cdx_vix_deviation_gap_20d` | basis_points | cdx, vix | Cross-asset risk sentiment |
| `spread_momentum_5d` | basis_points | cdx | Short-term momentum |

See `indicator_catalog.json` for complete list.

## Next Steps

1. ✅ Define your indicator in `indicator_catalog.json` and `indicators.py`
2. ✅ Add signal entry to `signal_catalog.json`
3. ✅ Write unit tests for indicator computation
4. ✅ Test signal via `compute_registered_signals()`
5. ✅ Run signal evaluation: `aponyx run --signal my_signal --strategy balanced`

## Getting Help

- **Indicator examples**: See `src/aponyx/models/indicators.py`
- **Signal examples**: See `src/aponyx/models/signal_catalog.json`
- **Full workflow example**: See `examples/workflow_basic.yaml`
- **Architecture docs**: See `.github/copilot-instructions.md`
