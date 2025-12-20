---
description: Create a new workflow step for the aponyx pipeline
name: Add Workflow Step
---

# Create New Workflow Step

Create a new step in the workflow pipeline following the WorkflowStep protocol.

## User Request

${input:step_description:Describe the workflow step you want to create}

## Implementation Steps

### Step 1: Create Step Class

Add to `src/aponyx/workflows/concrete_steps.py`:

```python
class MyStep(WorkflowStep):
    """Description of what this step does."""
    
    @property
    def name(self) -> str:
        return "my_step"
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute step logic."""
        logger.info("Executing %s", self.name)
        
        # Access previous step outputs
        signal = context["signal"]["signal"]
        
        # Your logic here
        my_output = process_signal(signal)
        
        # Save output
        output_dir = context["output_dir"]
        save_parquet(my_output, output_dir / "my_step" / "result.parquet")
        
        return {"my_output": my_output}
    
    def output_exists(self) -> bool:
        """Check if step output already exists."""
        return (self.output_dir / "my_step" / "result.parquet").exists()
    
    def load_cached_output(self) -> dict[str, Any]:
        """Load previously computed output."""
        my_output = load_parquet(self.output_dir / "my_step" / "result.parquet")
        return {"my_output": my_output}
```

### Step 2: Register Step

Add to `src/aponyx/workflows/registry.py` in `get_all_steps()`:

```python
def get_all_steps(self, config: WorkflowConfig) -> list[WorkflowStep]:
    """Get all workflow steps in dependency order."""
    return [
        DataStep(config),
        SignalStep(config),
        MyStep(config),  # Add at appropriate position
        SuitabilityStep(config),
        BacktestStep(config),
        PerformanceStep(config),
        VisualizationStep(config),
    ]
```

## Pipeline Order

Steps execute in fixed order:
1. **DataStep** - Load market data
2. **SignalStep** - Compute signal via four-stage pipeline
3. **SuitabilityStep** - Pre-backtest quality gate
4. **BacktestStep** - Simulate P&L
5. **PerformanceStep** - Post-backtest metrics
6. **VisualizationStep** - Generate charts

## Context Dict Pattern

Steps communicate via the shared `context` dict:

```python
# Step N produces output
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    return {"my_output": result}

# Step N+1 consumes it
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    previous_output = context["previous_step"]["my_output"]
```

## Cache Pattern

```python
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    if not self.config.force_rerun and self.output_exists():
        logger.info("Loading cached output for %s", self.name)
        return self.load_cached_output()
    
    result = self._compute_result(context)
    self._save_output(result)
    return result
```

## Validation

After implementation:
1. Run `uv run pytest tests/workflows/`
2. Run `uv run mypy src/aponyx/workflows/`
3. Test with workflow: `uv run aponyx run examples/workflow_minimal.yaml`
