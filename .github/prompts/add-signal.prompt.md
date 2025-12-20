---
description: Create a new trading signal using the four-stage transformation pipeline
name: Add Signal
---

# Create New Signal

Create a new trading signal following the **four-stage transformation pipeline**:

1. **Indicator Transformation** - Compute raw economic metric from securities
2. **Score Transformation** - Normalize to common scale (z-score)
3. **Signal Transformation** - Apply trading rules (floor, cap, neutral_range)
4. **Signal Catalog Entry** - Reference all three transformations

## User Request

${input:signal_description:Describe the signal you want to create}

## Implementation Steps

### Step 1: Indicator Function (if needed)

Add to `src/aponyx/models/indicators.py`:

```python
def compute_my_indicator(
    cdx_df: pd.DataFrame,
    vix_df: pd.DataFrame,
) -> pd.Series:
    """
    Compute indicator in economically interpretable units.
    
    Outputs raw values (bps, ratios) WITHOUT normalization.
    Score transformations are applied at signal composition layer.
    
    Signal Convention
    -----------------
    After sign_multiplier is applied:
    Positive values → Long credit risk (CDX relatively cheap)
    Negative values → Short credit risk (CDX relatively expensive)
    """
    # Compute raw indicator in meaningful units
    return indicator_series
```

### Step 2: Indicator Transformation Entry

Add to `src/aponyx/models/indicator_transformation.json`:

```json
{
  "name": "my_indicator",
  "description": "Description of the indicator",
  "compute_function_name": "compute_my_indicator",
  "data_requirements": {
    "cdx": "spread",
    "vix": "level"
  },
  "default_securities": {
    "cdx": "cdx_ig_5y",
    "vix": "vix"
  },
  "output_units": "basis_points",
  "parameters": {},
  "enabled": true
}
```

### Step 3: Signal Catalog Entry

Add to `src/aponyx/models/signal_catalog.json`:

```json
{
  "name": "my_signal",
  "description": "Signal description with normalization and bounds",
  "indicator_transformation": "my_indicator",
  "score_transformation": "z_score_20d",
  "signal_transformation": "passthrough",
  "enabled": true,
  "sign_multiplier": 1
}
```

### Step 4: Tests

Add to `tests/models/test_signal_composer.py`:

```python
def test_my_signal():
    """Test signal via four-stage pipeline."""
    cdx_df = generate_sample_cdx(n_obs=252)
    vix_df = generate_sample_vix(n_obs=252)
    
    signal = compose_signal(
        signal_name="my_signal",
        market_data={"cdx": cdx_df, "vix": vix_df},
        indicator_registry=indicator_reg,
        score_registry=score_reg,
        signal_transformation_registry=signal_trans_reg,
        signal_registry=signal_reg,
    )
    
    assert isinstance(signal, pd.Series)
    assert len(signal.dropna()) > 0
```

## Validation

After implementation:
1. Run `uv run pytest tests/models/test_signal_composer.py -v`
2. Run `uv run mypy src/aponyx/models/`
3. Test with workflow: `uv run aponyx run src/aponyx/examples/configs/01_workflow_minimal.yaml`
