# Data Model: Signal Catalog Schema (Post-Cleanup)

**Feature**: Remove Legacy Compatibility from Indicator-Signal Separation  
**Date**: December 1, 2025  
**Status**: Complete

## Overview

This document specifies the cleaned-up signal catalog schema after removing all backward compatibility fields. The schema enforces the indicator + transformation composition pattern as the only way to define signals.

## Schema Evolution

### Before (Dual-Pattern Support)

SignalMetadata supported both legacy pattern (compute_function_name) and new pattern (indicator_dependencies):

```python
@dataclass(frozen=True)
class SignalMetadata:
    name: str
    description: str
    
    # New pattern fields (optional)
    indicator_dependencies: list[str] | None = None
    transformations: list[str] | None = None
    composition_logic: str | None = None
    
    # Legacy pattern fields (optional)
    compute_function_name: str | None = None
    data_requirements: dict[str, str] | None = None
    arg_mapping: list[str] | None = None
    default_securities: dict[str, str] | None = None
    
    enabled: bool = True
    sign_multiplier: int = 1
```

Validation allowed either pattern:
```python
has_legacy = self.compute_function_name is not None
has_new = self.indicator_dependencies is not None
if not has_legacy and not has_new:
    raise ValueError("Must specify one pattern")
```

### After (Single Pattern Only)

SignalMetadata enforces indicator + transformation composition:

```python
@dataclass(frozen=True)
class SignalMetadata:
    """
    Metadata for a registered signal computation.
    
    Signals are trading signals derived from indicators via transformations.
    All signals MUST use the indicator + transformation composition pattern.
    
    Attributes
    ----------
    name : str
        Unique signal identifier (lowercase with underscores).
        Example: "cdx_etf_basis", "spread_momentum"
    description : str
        Human-readable description of signal purpose and logic.
        Minimum 10 characters.
    indicator_dependencies : list[str]
        List of indicator names required for this signal (REQUIRED).
        All indicators must exist in indicator_catalog.json.
        Example: ["cdx_etf_spread_diff"]
    transformations : list[str]
        List of transformation names to apply to indicators (REQUIRED).
        All transformations must exist in transformation_catalog.json.
        Example: ["z_score_20d"]
    composition_logic : str | None
        Optional Python expression for combining multiple indicators.
        Used only for multi-indicator signals.
        Example: "cdx_spread / etf_spread"
        Default: None (single indicator, sequential transformations)
    enabled : bool
        Whether signal should be included in computation.
        Default: True
    sign_multiplier : int
        Multiplier to apply to signal output for sign correction.
        Use -1 to invert signals with negative Sharpe ratios.
        Must be -1 or 1.
        Default: 1 (no inversion)
    """
    
    name: str
    description: str
    indicator_dependencies: list[str]
    transformations: list[str]
    composition_logic: str | None = None
    enabled: bool = True
    sign_multiplier: int = 1
    
    def __post_init__(self) -> None:
        """Validate signal metadata."""
        # Validate name format
        if not self.name or not re.match(r"^[a-z][a-z0-9_]*$", self.name):
            raise ValueError(
                f"Signal name must be lowercase with underscores, got: {self.name}"
            )
        
        # Validate description
        if not self.description or len(self.description) < 10:
            raise ValueError(
                f"Signal description must be at least 10 characters, got: {len(self.description)}"
            )
        
        # Enforce indicator + transformation pattern (REQUIRED)
        if not self.indicator_dependencies:
            raise ValueError(
                f"Signal '{self.name}' requires indicator_dependencies (cannot be empty)"
            )
        
        if not self.transformations:
            raise ValueError(
                f"Signal '{self.name}' requires transformations (cannot be empty)"
            )
        
        # Validate sign_multiplier is ±1
        if self.sign_multiplier not in (-1, 1):
            raise ValueError(
                f"sign_multiplier must be -1 or 1, got {self.sign_multiplier}"
            )
```

Validation now enforces single pattern:
```python
# Both indicator_dependencies and transformations are REQUIRED
if not self.indicator_dependencies:
    raise ValueError(f"Signal {self.name} requires indicator_dependencies")
if not self.transformations:
    raise ValueError(f"Signal {self.name} requires transformations")
```

## Field Removal Summary

| Field | Status | Rationale |
|-------|--------|-----------|
| `name` | ✅ KEEP | Core identifier, required |
| `description` | ✅ KEEP | Documentation, required |
| `indicator_dependencies` | ✅ KEEP | Required (was optional), defines composition |
| `transformations` | ✅ KEEP | Required (was optional), defines signal processing |
| `composition_logic` | ✅ KEEP | Optional, for multi-indicator signals |
| `enabled` | ✅ KEEP | Optional, defaults to True |
| `sign_multiplier` | ✅ KEEP | Optional, defaults to 1 |
| **`compute_function_name`** | ❌ REMOVE | Legacy pattern field, no longer needed |
| **`data_requirements`** | ❌ REMOVE | Moved to indicator layer |
| **`arg_mapping`** | ❌ REMOVE | Only used by legacy pattern |
| **`default_securities`** | ❌ REMOVE | Moved to indicator layer |

## Signal Catalog Entry Format

### New Format (After Cleanup)

```json
{
  "name": "cdx_etf_basis",
  "description": "Flow-driven mispricing signal from CDX-ETF basis divergence",
  "indicator_dependencies": ["cdx_etf_spread_diff"],
  "transformations": ["z_score_20d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

**Field-by-field explanation**:

- **`name`**: Snake_case identifier, matches signal registry key
- **`description`**: Explains economic intuition and signal purpose
- **`indicator_dependencies`**: List of indicator names from indicator_catalog.json
  - System validates that all referenced indicators exist
  - Indicators computed in order listed
  - Each indicator must be enabled
- **`transformations`**: List of transformation names from transformation_catalog.json
  - System validates that all referenced transformations exist
  - Applied sequentially to indicator outputs
  - Each transformation must be enabled
- **`enabled`**: Boolean flag for including signal in batch computation
- **`sign_multiplier`**: ±1 multiplier for sign convention alignment

### Multi-Indicator Signal Example

For signals that combine multiple indicators:

```json
{
  "name": "relative_value_signal",
  "description": "Relative value between two credit indices",
  "indicator_dependencies": ["cdx_ig_spread", "cdx_hy_spread"],
  "transformations": ["z_score_20d"],
  "composition_logic": "cdx_ig_spread / cdx_hy_spread",
  "enabled": true,
  "sign_multiplier": 1
}
```

**`composition_logic`**: Python expression combining indicator outputs
- Variable names match indicator names from indicator_dependencies
- Executed after indicators computed but before transformations applied
- Result is a single pd.Series that then goes through transformations

## Validation Rules

### Schema Validation (Enforced at Load Time)

1. **Required fields**: name, description, indicator_dependencies, transformations
2. **Field types**:
   - `name`: string, lowercase, underscores only, pattern: `^[a-z][a-z0-9_]*$`
   - `description`: string, minimum 10 characters
   - `indicator_dependencies`: array of strings, minimum 1 element
   - `transformations`: array of strings, minimum 1 element
   - `composition_logic`: string or null
   - `enabled`: boolean, defaults to true
   - `sign_multiplier`: integer, enum: [-1, 1], defaults to 1
3. **No additional properties**: Catalog entries with unknown fields will fail validation

### Cross-Reference Validation (Enforced at Registry Load Time)

1. **Indicator existence**: All entries in `indicator_dependencies` must exist in `indicator_catalog.json`
2. **Transformation existence**: All entries in `transformations` must exist in `transformation_catalog.json`
3. **Indicator enabled check**: All referenced indicators must have `enabled: true`
4. **Transformation enabled check**: All referenced transformations must have `enabled: true`

### Duplicate Detection

1. **Signal names must be unique** across catalog
2. **Case-sensitive matching** (but schema enforces lowercase)

## Migration from Dual-Pattern to Single-Pattern

### Catalog Entry Migration

For each signal in `signal_catalog.json`:

**Before**:
```json
{
  "name": "spread_momentum",
  "description": "Short-term volatility-adjusted momentum in CDX spreads",
  "compute_function_name": "compute_spread_momentum",
  "data_requirements": {"cdx": "spread"},
  "arg_mapping": ["cdx"],
  "default_securities": {"cdx": "cdx_ig_5y"},
  "indicator_dependencies": ["spread_momentum_5d"],
  "transformations": ["volatility_adjust_20d"],
  "composition_logic": null,
  "enabled": true,
  "sign_multiplier": 1
}
```

**After**:
```json
{
  "name": "spread_momentum",
  "description": "Short-term volatility-adjusted momentum in CDX spreads",
  "indicator_dependencies": ["spread_momentum_5d"],
  "transformations": ["volatility_adjust_20d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

**Changes**:
1. ❌ Remove `compute_function_name` line
2. ❌ Remove `data_requirements` line
3. ❌ Remove `arg_mapping` line
4. ❌ Remove `default_securities` line (now in indicator catalog)
5. ❌ Remove `composition_logic` line (if null)
6. ✅ Keep `indicator_dependencies`
7. ✅ Keep `transformations`
8. ✅ Keep `enabled`
9. ✅ Keep `sign_multiplier`

### Code Changes

**metadata.py** - Remove 4 fields from SignalMetadata dataclass:
```python
# DELETE these field definitions:
compute_function_name: str | None = None
data_requirements: dict[str, str] | None = None
arg_mapping: list[str] | None = None
default_securities: dict[str, str] | None = None

# UPDATE __post_init__ validation:
# Remove: dual-pattern "either/or" logic
# Add: enforce indicator_dependencies and transformations required
```

**orchestrator.py** - Remove legacy pattern support:
```python
# DELETE function: _compute_signal_legacy_pattern()
# DELETE function: _validate_data_requirements()
# UPDATE function: _compute_signal() to only call _compute_signal_new_pattern()
```

**registry.py** - Update validation:
```python
# UPDATE: _validate_catalog() method
# Remove: compute_function_name existence check
# Add: indicator_dependencies non-empty check
# Add: transformations non-empty check
```

## Dependencies

### Upstream Dependencies (Required for Signal Computation)

1. **Indicator Catalog** (`indicator_catalog.json`)
   - Must contain all referenced indicator names
   - Indicators define data_requirements and default_securities
   - Example: `cdx_etf_spread_diff`, `spread_momentum_5d`, `cdx_vix_deviation_gap_20d`

2. **Transformation Catalog** (`transformation_catalog.json`)
   - Must contain all referenced transformation names
   - Transformations define parameters (window, min_periods)
   - Example: `z_score_20d`, `z_score_60d`, `volatility_adjust_20d`

### Downstream Dependencies (Consumers of Signal Metadata)

1. **Signal Composer** (`signal_composer.py`)
   - Reads indicator_dependencies to determine computation order
   - Reads transformations to apply sequential processing
   - Reads composition_logic for multi-indicator combination

2. **Workflow Engine** (`workflows/concrete_steps.py`)
   - Uses signal metadata to determine required data
   - Passes metadata to orchestrator for batch computation

3. **Backtest Engine** (`backtest/engine.py`)
   - Consumes signal outputs (not metadata directly)
   - No changes needed for signal metadata cleanup

## Examples

### Example 1: Single-Indicator Signal

```json
{
  "name": "spread_momentum",
  "description": "Short-term momentum in CDX spreads",
  "indicator_dependencies": ["spread_momentum_5d"],
  "transformations": ["volatility_adjust_20d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

**Computation flow**:
1. Load `spread_momentum_5d` indicator from cache or compute
2. Apply `volatility_adjust_20d` transformation
3. Multiply result by sign_multiplier (1, no change)
4. Return signal Series

### Example 2: Multi-Indicator Signal

```json
{
  "name": "cdx_etf_basis",
  "description": "Flow-driven mispricing from CDX-ETF basis divergence",
  "indicator_dependencies": ["cdx_etf_spread_diff"],
  "transformations": ["z_score_20d"],
  "enabled": true,
  "sign_multiplier": 1
}
```

**Computation flow**:
1. Load `cdx_etf_spread_diff` indicator (already computes CDX - ETF)
2. Apply `z_score_20d` transformation for normalization
3. Return normalized signal Series

### Example 3: Sign-Inverted Signal

```json
{
  "name": "inverse_vix_signal",
  "description": "Inverted VIX deviation for short-vol strategy",
  "indicator_dependencies": ["vix_deviation_20d"],
  "transformations": ["z_score_60d"],
  "enabled": true,
  "sign_multiplier": -1
}
```

**Computation flow**:
1. Load `vix_deviation_20d` indicator
2. Apply `z_score_60d` transformation
3. Multiply result by -1 to invert sign
4. Return inverted signal Series

## Testing

### Schema Validation Tests

```python
def test_signal_metadata_requires_indicators():
    """Signal metadata must have indicator_dependencies."""
    with pytest.raises(ValueError, match="requires indicator_dependencies"):
        SignalMetadata(
            name="test_signal",
            description="Test signal without indicators",
            indicator_dependencies=[],  # Empty list not allowed
            transformations=["z_score_20d"],
        )

def test_signal_metadata_requires_transformations():
    """Signal metadata must have transformations."""
    with pytest.raises(ValueError, match="requires transformations"):
        SignalMetadata(
            name="test_signal",
            description="Test signal without transformations",
            indicator_dependencies=["test_indicator"],
            transformations=[],  # Empty list not allowed
        )

def test_signal_metadata_rejects_legacy_fields():
    """Signal metadata should not accept legacy fields."""
    # This test ensures legacy fields cause TypeError
    with pytest.raises(TypeError):
        SignalMetadata(
            name="test_signal",
            description="Test signal",
            indicator_dependencies=["test_indicator"],
            transformations=["z_score_20d"],
            compute_function_name="compute_test",  # Unknown field
        )
```

### Cross-Reference Validation Tests

```python
def test_registry_validates_indicator_exists():
    """Registry must validate that referenced indicators exist."""
    catalog = [
        {
            "name": "test_signal",
            "description": "Test signal",
            "indicator_dependencies": ["nonexistent_indicator"],
            "transformations": ["z_score_20d"],
            "enabled": True,
        }
    ]
    
    with pytest.raises(ValueError, match="indicator.*not found"):
        SignalRegistry._validate_catalog(catalog)

def test_registry_validates_transformation_exists():
    """Registry must validate that referenced transformations exist."""
    catalog = [
        {
            "name": "test_signal",
            "description": "Test signal",
            "indicator_dependencies": ["test_indicator"],
            "transformations": ["nonexistent_transform"],
            "enabled": True,
        }
    ]
    
    with pytest.raises(ValueError, match="transformation.*not found"):
        SignalRegistry._validate_catalog(catalog)
```

## Backward Incompatibility

### Breaking Changes

1. **Catalog format changed**: Old signal_catalog.json entries with compute_function_name will fail validation
2. **API changed**: SignalMetadata constructor no longer accepts legacy fields
3. **Validation changed**: Missing indicator_dependencies or transformations now raises ValueError

### Migration Required

Users MUST:
1. Update all signal catalog entries to remove legacy fields
2. Ensure all signals have indicator_dependencies and transformations
3. Re-run workflows to generate new results with updated metadata

### No Deprecation Period

Per Constitution Principle VIII:
- No deprecation warnings issued
- No compatibility layer provided
- Old catalog format immediately fails validation
- Users must migrate before running system

## Summary

This schema cleanup removes 4 legacy fields from SignalMetadata, simplifies validation logic, and enforces the indicator + transformation composition pattern as the only way to define signals. The new schema is cleaner, more explicit, and aligned with the architectural vision of reusable indicators and composable signals.
