---
description: Create a new backtest strategy configuration
name: Add Strategy
---

# Create New Backtest Strategy

Create a new backtest strategy by adding an entry to the strategy catalog.

## User Request

${input:strategy_description:Describe the strategy you want to create (risk parameters, sizing mode, etc.)}

## Implementation

### Strategy Catalog Entry

Add to `src/aponyx/backtest/strategy_catalog.json`:

```json
{
  "name": "my_strategy",
  "description": "Custom risk management configuration",
  "position_size_mm": 10.0,
  "sizing_mode": "proportional",
  "stop_loss_pct": 5.0,
  "take_profit_pct": 10.0,
  "max_holding_days": null,
  "transaction_cost_bps": 1.0,
  "dv01_per_million": 475.0,
  "enabled": true
}
```

## Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | required | Unique strategy identifier |
| `description` | str | required | Human-readable description |
| `position_size_mm` | float | 10.0 | Position size in millions (must be > 0) |
| `sizing_mode` | str | "proportional" | "binary" or "proportional" |
| `stop_loss_pct` | float | null | Stop loss percentage (0, 100] |
| `take_profit_pct` | float | null | Take profit percentage (0, 100] |
| `max_holding_days` | int | null | Maximum holding period |
| `transaction_cost_bps` | float | 1.0 | Transaction cost in basis points |
| `dv01_per_million` | float | 475.0 | DV01 per million notional |
| `enabled` | bool | true | Whether strategy is active |

## Sizing Modes

- **proportional** (default): Position size scales with signal magnitude
- **binary**: Full position on any entry signal

## P&L Calculation

```python
pnl = position * (-spread_change) * dv01_per_million * position_size / 1_000_000
```

Long profits when spreads tighten, short profits when spreads widen.

## Validation

After adding the strategy:
1. Run `uv run pytest tests/backtest/` 
2. Test with workflow: Create a workflow YAML referencing your strategy
