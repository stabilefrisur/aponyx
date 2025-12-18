# CDX Knowledge Base

> Comprehensive reference for Credit Default Index Swaps (CDX) trading and P&L calculation

---

## Table of Contents

1. [What is CDX?](#what-is-cdx)
2. [CDX Index Family](#cdx-index-family)
3. [Key Terminology](#key-terminology)
4. [DV01 and Risk Metrics](#dv01-and-risk-metrics)
5. [P&L Calculation](#pnl-calculation)
6. [Transaction Costs](#transaction-costs)
7. [Trading Conventions](#trading-conventions)
8. [Signal Interpretation](#signal-interpretation)
9. [Project Implementation](#project-implementation)

---

## What is CDX?

**Credit Default Index Swaps (CDX)** are tradeable credit derivative indices that reference a basket of single-name credit default swaps (CDS). They provide standardized exposure to corporate credit risk in North American markets.

### How CDX Works

1. **Protection Buyer**: Pays periodic premium (spread) to protection seller
2. **Protection Seller**: Receives spread, pays out if credit event occurs
3. **Credit Events**: Bankruptcy, failure to pay, restructuring (for some contracts)

### Why Trade CDX?

- **Liquidity**: Most liquid credit derivatives (tight bid-ask spreads)
- **Standardization**: Fixed composition, maturity, coupon
- **Capital Efficiency**: Margin-based trading, no upfront principal
- **Hedging**: Efficiently hedge credit portfolio risk
- **Speculation**: Express directional views on credit markets

---

## CDX Index Family

### North American Indices

| Index | Description | Typical Spread Range | DV01 per $1MM |
|-------|-------------|---------------------|---------------|
| **CDX.NA.IG** | 125 Investment Grade names | 50-150 bps | ~$450-520 |
| **CDX.NA.HY** | 100 High Yield names | 300-600 bps | ~$350-450 |
| **CDX.NA.XO** | Crossover (BB-rated) | 200-400 bps | ~$400-480 |

### Tenors

- **5-Year**: Most liquid, primary trading vehicle
- **10-Year**: Less liquid, used for curve trades
- **3-Year, 7-Year**: Available but limited liquidity

### Index Rolls

- CDX indices roll **every 6 months** (March and September)
- New series issued with updated constituent list
- On-the-run series has best liquidity
- Off-the-run series trade at discount

---

## Key Terminology

### Spread

The **spread** is the annual premium paid by the protection buyer, quoted in basis points (bps).

```
Spread = 100 bps means paying 1% per year on notional
For $10MM notional: $100,000/year = ~$274/day
```

### Spread Movements

| Movement | What It Means | Market Sentiment |
|----------|---------------|------------------|
| **Spreads Widen** | Credit risk increasing | Risk-off, bearish credit |
| **Spreads Tighten** | Credit risk decreasing | Risk-on, bullish credit |

### Price vs. Spread

CDX can be quoted as **price** (like a bond) or **spread** (like CDS):

```
Price ≈ 100 - (Spread × Duration)

Example: If spread = 100 bps and duration = 5 years
Price ≈ 100 - (1.00 × 5) = 95
```

### Fixed Coupon

Modern CDX contracts have **fixed coupons**:
- **CDX IG**: 100 bps fixed coupon
- **CDX HY**: 500 bps fixed coupon

The difference between market spread and fixed coupon is settled upfront.

---

## DV01 and Risk Metrics

### What is DV01?

**DV01** (Dollar Value of 01) is the P&L impact of a 1 basis point move in spreads.

```
DV01 = Notional × Duration × 0.0001

For CDX IG 5Y with ~4.75 year duration:
DV01 per $1MM = $1,000,000 × 4.75 × 0.0001 = $475
```

### Typical DV01 Values

| Index | Tenor | DV01 per $1MM | Notes |
|-------|-------|---------------|-------|
| CDX IG | 5Y | ~$475 | Primary trading vehicle |
| CDX IG | 10Y | ~$850 | Higher duration exposure |
| CDX HY | 5Y | ~$400 | Lower due to wider spreads |

### DV01 in Aponyx

The project uses `dv01_per_million = 475.0` in the strategy catalog, representing the actual DV01 per $1MM for CDX IG 5Y:

```json
// strategy_catalog.json
{
  "name": "balanced",
  "dv01_per_million": 475.0,  // $475 per bp per $1MM
  ...
}
```

BacktestConfig reads DV01 from the strategy catalog (no hardcoded default).

---

## P&L Calculation

### Core P&L Formula

For a **long credit risk position** (sold protection / bought CDX):

```
Daily P&L = -Position × ΔSpread × DV01 × Notional_MM
```

Where:
- **Position**: +1 (long credit) or -1 (short credit)
- **ΔSpread**: Today's spread - Yesterday's spread (in bps)
- **DV01**: Dollar value per basis point per $1MM (~$475 for CDX IG 5Y)
- **Notional_MM**: Position size in millions (e.g., 10 for $10MM)

### Why the Negative Sign?

**Long credit risk** means you **profit when spreads tighten**:
- Spreads tighten (ΔSpread < 0) → P&L > 0 (profit)
- Spreads widen (ΔSpread > 0) → P&L < 0 (loss)

The negative sign converts spread direction to profit direction.

### P&L Examples

**Example 1: Long Position, Spreads Tighten**
```
Position: Long $10MM CDX IG 5Y
Yesterday's spread: 100 bps
Today's spread: 98 bps
ΔSpread: -2 bps
DV01: $475 per $1MM

P&L = -1 × (-2) × 475 × 10
P&L = +$9,500 (profit)
```

**Example 2: Long Position, Spreads Widen**
```
Position: Long $10MM CDX IG 5Y
Yesterday's spread: 100 bps
Today's spread: 103 bps
ΔSpread: +3 bps

P&L = -1 × (+3) × 475 × 10
P&L = -$14,250 (loss)
```

**Example 3: Short Position, Spreads Widen**
```
Position: Short $10MM CDX IG 5Y
Yesterday's spread: 100 bps
Today's spread: 105 bps
ΔSpread: +5 bps

P&L = -(-1) × (+5) × 475 × 10
P&L = +$23,750 (profit)
```

### Implementation in Aponyx

From `src/aponyx/backtest/engine.py`:

```python
if abs(position_before_update) > 1e-9:
    spread_change = spread_level - prev_spread_before_update
    if is_proportional:
        # Proportional: position_before_update is actual notional in MM
        spread_pnl = (
            -np.sign(position_before_update)
            * abs(position_before_update)
            * spread_change
            * config.dv01_per_million
        )
    else:
        # Binary: position_before_update is direction indicator (+1/-1)
        spread_pnl = (
            -position_before_update
            * spread_change
            * config.dv01_per_million
            * config.position_size_mm
        )
else:
    spread_pnl = 0.0
```

---

## Transaction Costs

### Components of CDX Trading Costs

1. **Bid-Ask Spread**: Primary cost, ~0.5-2 bps for CDX IG
2. **Clearing Fees**: CME/ICE clearing costs
3. **Commission**: Broker fees
4. **Market Impact**: For large trades

### Typical Transaction Costs

| Index | Bid-Ask (bps) | Round-Trip Cost |
|-------|---------------|-----------------|
| CDX IG 5Y | 0.5-1.0 | 1-2 bps |
| CDX IG 10Y | 1.0-2.0 | 2-4 bps |
| CDX HY 5Y | 2.0-4.0 | 4-8 bps |

### Cost Calculation in Aponyx

Transaction costs depend on sizing mode:

```python
# Binary mode: cost based on full position_size_mm
cost = transaction_cost_bps * position_size_mm * 100

# For $10MM position with 1 bps cost:
cost = 1.0 * 10.0 * 100 = $1,000 per entry/exit

# Proportional mode: cost based on actual traded notional
cost = abs(position_notional_mm) * transaction_cost_bps * 100

# For $5MM actual position with 1 bps cost:
cost = 5.0 * 1.0 * 100 = $500 per entry/exit
```

Note: Costs are applied on **each** entry and exit, not round-trip.

### Implementation

```python
@dataclass(frozen=True)
class BacktestConfig:
    transaction_cost_bps: float  # Per-trade cost (entry OR exit)
    
# Binary mode
entry_cost = config.transaction_cost_bps * config.position_size_mm * 100
exit_cost = config.transaction_cost_bps * config.position_size_mm * 100

# Proportional mode
entry_cost = abs(current_position) * config.transaction_cost_bps * 100
exit_cost = abs(current_position) * config.transaction_cost_bps * 100
```

---

## Trading Conventions

### Position Direction

| Action | Position | Credit Risk | Profit When |
|--------|----------|-------------|-------------|
| **Buy CDX** | Long | Long credit risk | Spreads tighten |
| **Sell CDX** | Short | Short credit risk | Spreads widen |
| **Sell Protection** | Long | Long credit risk | Spreads tighten |
| **Buy Protection** | Short | Short credit risk | Spreads widen |

### Market Quoting

CDX is typically quoted as spread in basis points:
- "CDX IG is offered at 75" means 75 bps spread
- "CDX IG traded 2 tighter" means spread narrowed by 2 bps

### Settlement

- **T+1 settlement** for standard trades
- **Central clearing** required (CME, ICE)
- **Daily margin** based on mark-to-market

---

## Signal Interpretation

### Aponyx Signal Convention

**CRITICAL**: All signals in Aponyx follow this convention:
- **Positive signal** → Long credit risk (buy CDX / sell protection)
- **Negative signal** → Short credit risk (sell CDX / buy protection)

### Signal Examples

| Signal | Signal Value | Position | Expectation |
|--------|--------------|----------|-------------|
| CDX-ETF Basis | +2.0 | Long | CDX cheap, expect tightening |
| CDX-ETF Basis | -1.5 | Short | CDX expensive, expect widening |
| Spread Momentum | +1.2 | Long | Tightening momentum continues |
| CDX-VIX Gap | -0.8 | Short | Credit stress exceeds equity stress |

### Signal-to-Position Logic

From the backtest engine:

```python
# Non-zero signal = enter position
if not signal_is_zero:
    if is_proportional:
        target_position = signal_val * config.position_size_mm
    else:  # Binary mode
        target_position = 1.0 if signal_val > 0 else -1.0

# Zero signal = exit position
if signal_is_zero:
    exit_reason = "signal"
    current_position = 0.0
```

---

## Project Implementation

### Key Files

| File | Purpose |
|------|---------|
| `backtest/engine.py` | P&L calculation, position management |
| `backtest/config.py` | BacktestConfig with DV01, costs |
| `backtest/strategy_catalog.json` | Pre-configured strategies |
| `docs/cdx_overlay_strategy.md` | Strategy design document |

### BacktestConfig Parameters

```python
@dataclass(frozen=True)
class BacktestConfig:
    position_size_mm: float           # Notional in $MM (required)
    sizing_mode: str                  # "proportional" or "binary" (required)
    stop_loss_pct: float | None       # % of position value
    take_profit_pct: float | None     # % of position value
    max_holding_days: int | None      # Forced exit
    transaction_cost_bps: float       # Per-trade cost in bps (required)
    dv01_per_million: float           # DV01 per $1MM (required, ~475 for CDX IG 5Y)
    signal_lag: int = 1               # Days to lag signal (0=same-day, 1=next-day)
    entry_threshold: float | None     # Min |signal| to enter (asymmetric entry/exit)
```

Note: All parameters except `signal_lag` and `entry_threshold` must be explicitly provided. Use `StrategyRegistry.get()` to load from catalog.

### Entry Threshold for Mean-Reversion

The `entry_threshold` parameter enables asymmetric entry/exit for mean-reversion strategies:
- **Entry**: Only when |signal| >= entry_threshold (e.g., 1.8)
- **Exit**: When signal returns to zero (via signal transformation's neutral_range)

This allows the reversion to run before closing the trade. Example configuration:
- `entry_threshold=1.8`: Enter at extreme signal values
- Signal transformation `neutral_range=[-0.5, 0.5]`: Exit when signal enters neutral zone

### Strategy Catalog

```json
{
  "name": "balanced",
  "description": "Balanced position sizing with moderate risk management",
  "position_size_mm": 10.0,
  "sizing_mode": "proportional",
  "stop_loss_pct": 5.0,
  "take_profit_pct": 10.0,
  "max_holding_days": null,
  "entry_threshold": 1.5,
  "enabled": true
}
```

Note: `signal_lag` defaults to 1 in BacktestConfig. Microstructure parameters (transaction_cost_bps, dv01_per_million) come from bloomberg_securities.json.

### Running a Backtest

```python
from aponyx.backtest import BacktestConfig, run_backtest

# DV01 comes from bloomberg_securities.json (475.0 for CDX IG 5Y)
config = BacktestConfig(
    position_size_mm=10.0,
    stop_loss_pct=5.0,
    dv01_per_million=475.0,
    entry_threshold=1.8,  # Enter only at extreme signals
)

result = run_backtest(signal, spread, config)

# Access results
print(f"Total P&L: ${result.pnl['cumulative_pnl'].iloc[-1]:,.0f}")
print(f"Number of trades: {result.metadata['summary']['n_trades']}")
```

---

## Quick Reference Card

### P&L Formula
```
Daily P&L = -Position × ΔSpread × DV01 × Notional_MM
```

### DV01 Approximation
```
DV01 per $1MM ≈ Duration × $100

CDX IG 5Y: ~4.75 × 100 = ~$475/bp per $1MM
For $10MM position: $475 × 10 = $4,750/bp
```

### Position Mapping
```
Positive Signal → Long Credit → Buy CDX → Profit on Tightening
Negative Signal → Short Credit → Sell CDX → Profit on Widening
```

### Cost Impact
```
Break-even move = Entry Cost (bps) + Exit Cost (bps)
With 1 bps per trade: need 2 bps total move to break even (1 entry + 1 exit)
```

---

## References

- S&P Global: CDS Indices Primer
- IHS Markit: CDX Index Methodology
- CME Group: CDX Index Futures Specifications
- Aponyx Strategy Design: `docs/cdx_overlay_strategy.md`

---

*Last Updated: December 2025*
