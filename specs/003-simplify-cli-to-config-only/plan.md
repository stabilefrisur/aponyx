# CLI Simplification: Config-Only Run Command

## Objective

Refactor the `aponyx run` command to accept only a single positional argument (YAML config file path) instead of multiple CLI options and flags. This change makes the CLI more user-friendly by requiring all workflow parameters to be specified in YAML configuration files.

## Current State

The `run` command currently accepts multiple options:
- `--signal` (signal name)
- `--strategy` (strategy name)
- `--config` (optional YAML config file)
- Various other flags and overrides

This creates a poor UX when users need to specify 5+ flags for a single workflow run.

## Target State

### CLI Interface

```bash
# New simple interface
aponyx run workflow.yaml
aponyx run examples/workflow_bloomberg.yaml

# No longer supported (remove all flags)
aponyx run --signal spread_momentum --strategy balanced --force
```

### YAML Configuration Schema

All workflow configurations must be specified in YAML files with the following structure:

**Required Fields:**
- `product`: Product identifier (e.g., "cdx_ig_5y")
- `signal`: Signal name (must exist in signal_catalog.json)

**Optional Fields (with defaults):**
- `indicator`: Indicator override (default: from signal's indicator_dependencies)
- `securities`: Security mapping dictionary (default: from indicator's default_securities)
  - Format: `{instrument_type: security_id}`
- `transformation`: Transformation override (default: from signal's transformations)
- `strategy`: Strategy name (default: "balanced")
- `data`: Data source (default: "synthetic")
- `steps`: List of steps to execute (default: all steps)
- `force`: Boolean flag to force re-run (default: false)

### Configuration Display Requirements

**CRITICAL:** Every workflow run must display ALL configuration values in the terminal, including:
1. User-specified values (marked as `[config]`)
2. Default values that were not specified (marked as `[default]`)
3. Values inherited from catalog metadata (marked as `[from signal]`, `[from indicator]`, etc.)

This ensures complete transparency about what configuration is being used for each run.

**Example Terminal Output:**

```
=== Workflow Configuration ===
Product:         cdx_ig_5y
Signal:          cdx_etf_basis
Indicator:       cdx_etf_spread_diff [from signal]
Securities:      cdx:cdx_ig_5y, etf:lqd [from indicator]
Transformation:  z_score_20d [from signal]
Strategy:        balanced [default]
Data:            synthetic [default]
Steps:           all (data, signal, suitability, backtest, performance, visualization) [default]
Force re-run:    False [default]
========================================

Completed 6 steps in 15.2s
Results: data/workflows/cdx_etf_basis_balanced_20251201_143230/
```

## Implementation Requirements

### 1. Modify `src/aponyx/cli/commands/run.py`

**Changes:**
- Replace `@click.option` decorators with single `@click.argument` for config file path
- Remove all individual parameter options (--signal, --strategy, --force, etc.)
- Update docstring to reflect config-only usage
- Add YAML loading and parsing logic
- Add required field validation (signal, product)
- Extract optional fields with appropriate defaults
- Call validation helper before creating WorkflowConfig
- Call display helper after creating WorkflowConfig
- Update error messages to reference YAML config structure

**New Helper Functions to Add:**

1. `_validate_config_references()`:
   - Validate signal exists in signal_catalog.json
   - Validate indicator override exists in indicator_catalog.json (if provided)
   - Validate transformation override exists in transformation_catalog.json (if provided)
   - Validate securities exist in bloomberg_instruments.json (if provided)
   - Provide helpful error messages listing available options when validation fails

2. `_display_workflow_config()`:
   - Display complete configuration with ALL fields
   - Show source of each value: [config], [default], [from signal], [from indicator]
   - Format output as shown in terminal example above
   - Retrieve defaults from signal and indicator metadata when showing inherited values

### 2. Update Example YAML Files

**Create/Update in `examples/` directory:**

1. `workflow_minimal.yaml`:
   - Only required fields (product, signal)
   - Demonstrates minimum viable config

2. `workflow_complete.yaml`:
   - All fields specified (including optional ones)
   - Serves as comprehensive reference

3. `workflow_custom_indicator.yaml`:
   - Override indicator while keeping signal's transformation
   - Demonstrates partial override pattern

4. `workflow_custom_securities.yaml`:
   - Override security mapping
   - Shows instrument-to-security mapping

5. Update existing workflow YAML files to match new schema

### 3. Update Documentation

**Files to update:**

1. `src/aponyx/docs/cli_guide.md`:
   - Remove multi-flag examples
   - Add config-only examples
   - Document YAML schema with all fields
   - Show terminal output examples
   - Explain default value resolution logic

2. `README.md`:
   - Update quick start examples
   - Replace CLI flag examples with config file examples

### 4. Update Tests

**Files to update:**

1. `tests/cli/test_commands.py`:
   - Remove tests for individual CLI options
   - Add tests for config file loading
   - Add tests for required field validation
   - Add tests for catalog reference validation
   - Add tests for default value resolution
   - Test error messages for missing/invalid config fields

2. `tests/cli/test_integration.py`:
   - Update integration tests to use config files
   - Test complete workflow execution with various config combinations

## Validation Requirements

All config references must be validated before workflow execution:

1. **Signal validation**: Must exist in signal_catalog.json
2. **Indicator validation**: Must exist in indicator_catalog.json (if override provided)
3. **Transformation validation**: Must exist in transformation_catalog.json (if override provided)
4. **Securities validation**: Each security_id must exist in bloomberg_instruments.json for its instrument_type (if mapping provided)
5. **Strategy validation**: Already handled by StrategyRegistry

When validation fails, provide helpful error messages that:
- Clearly state what's wrong
- List available valid options from the relevant catalog
- Guide users to fix their config file

## Default Resolution Logic

The display helper must resolve defaults in this priority order:

1. **User-specified in config** → Mark as `[config]`
2. **From signal metadata** → Mark as `[from signal]` (for indicator, transformation)
3. **From indicator metadata** → Mark as `[from indicator]` (for securities)
4. **System default** → Mark as `[default]` (for strategy, data, steps, force)

## Backward Compatibility

**Breaking Changes:**
- All existing CLI flag usage will break (intentional)
- Users must migrate to YAML config files

**Migration Path:**
- Provide clear error messages directing users to use config files
- Include example configs in error output or documentation references

## Success Criteria

1. ✅ `aponyx run <config.yaml>` works with only config file argument
2. ✅ All CLI flags removed (no `--signal`, `--strategy`, etc.)
3. ✅ Required fields (product, signal) validated with clear error messages
4. ✅ Optional field overrides validated against catalogs
5. ✅ Every run displays complete configuration with default resolution sources
6. ✅ All example YAML files work correctly
7. ✅ Documentation updated to reflect config-only approach
8. ✅ All tests pass with new config-based approach
9. ✅ Error messages guide users to valid options when validation fails

## Files to Modify

- `src/aponyx/cli/commands/run.py` (major refactor)
- `examples/workflow.yaml` (update to new schema)
- `examples/workflow_minimal.yaml` (create)
- `examples/workflow_complete.yaml` (create)
- `examples/workflow_custom_indicator.yaml` (create)
- `examples/workflow_custom_securities.yaml` (update/verify)
- `examples/workflow_bloomberg.yaml` (update to new schema)
- `src/aponyx/docs/cli_guide.md` (update documentation)
- `README.md` (update quick start)
- `tests/cli/test_commands.py` (refactor tests)
- `tests/cli/test_integration.py` (update integration tests)

## Testing Strategy

1. Test minimal config (only required fields)
2. Test complete config (all fields specified)
3. Test partial overrides (indicator only, transformation only, securities only)
4. Test invalid signal reference
5. Test invalid indicator override
6. Test invalid transformation override
7. Test invalid security mapping
8. Test missing required fields (signal, product)
9. Test default value display formatting
10. Test workflow execution with various configs
