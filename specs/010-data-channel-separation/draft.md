# Spec 010: Data Channel Separation

## Problem

Current design conflates three distinct data requirements:

1. **Indicator computation** - fields needed to calculate signals (usually spread)
2. **PnL calculation** - fields needed for backtest returns (spread-DV01 or price-return)
3. **Display/analysis** - fields shown in evaluation and visualization (prefer spread)

Additional complexity: Bloomberg has two patterns for spread data:
- **Dedicated ticker**: `CDX HY CDSI GEN 5Y SPRD Corp` → `PX_LAST` returns spread
- **Field on price ticker**: `HYG US Equity` → `YAS_ISPREAD` returns spread

## Solution: Data Channels with Usage Mapping

### Security Catalog Structure

Each security defines available **data channels** and their sources:

```json
{
  "cdx_hy_5y": {
    "description": "CDX North America High Yield 5Y",
    "primary_ticker": "CDX HY CDSI GEN 5Y Corp",
    "instrument_type": "cdx",
    "data_channels": {
      "spread": {
        "ticker": "CDX HY CDSI GEN 5Y SPRD Corp",
        "field": "PX_LAST"
      },
      "price": {
        "field": "PX_LAST"
      }
    },
    "quote_type": "price",
    "dv01_per_million": 425.0,
    "transaction_cost_bps": 8.0
  },
  "hyg": {
    "description": "iShares iBoxx High Yield Corporate Bond ETF",
    "primary_ticker": "HYG US Equity",
    "instrument_type": "etf",
    "data_channels": {
      "spread": {
        "field": "YAS_ISPREAD"
      },
      "price": {
        "field": "PX_LAST"
      }
    },
    "quote_type": "price"
  }
}
```

**Channel resolution**:
- If `ticker` specified → use that ticker with the field
- If only `field` specified → use `primary_ticker` with that field

### Instrument Type Defaults

Default usage preferences defined per instrument type:

```json
{
  "cdx": {
    "description": "CDX credit default swap indices",
    "default_usage": {
      "indicator": "spread",
      "display": "spread"
    }
  },
  "etf": {
    "description": "Credit ETFs",
    "default_usage": {
      "indicator": "spread",
      "display": "spread"
    }
  },
  "vix": {
    "description": "CBOE Volatility Index",
    "default_usage": {
      "indicator": "level",
      "display": "level"
    }
  }
}
```

**Note**: `pnl` usage is always derived from `pnl_method` on the security (no instrument-type default).

### Usage Purposes

| Purpose | Determined By | Consumer |
|---------|---------------|----------|
| `indicator` | Instrument type default | Indicator transformations |
| `pnl` | Security's `quote_type` | Backtest engine |
| `display` | Instrument type default | Evaluation, visualization |

**Note**: `quote_type` remains unchanged—it already controls PnL method (`spread` → spread-DV01, `price` → price-return).

## Validation Rules

| Field | Required | Constraint |
|-------|----------|------------|
| `dv01_per_million` | Only if `quote_type: spread` or override possible | Required for spread-DV01 calculation |
| `data_channels.spread` | No | Required if used in indicators or display |
| `data_channels.price` | No | Required if `quote_type: price` |

**Runtime validation**: If workflow specifies `quote_type_override: spread` but security lacks `dv01_per_million`, fail with clear error.

**Example**: ETFs have `data_channels.spread` (for indicators/display) but no `dv01_per_million` (PnL always price-based).

## Data Layer Resolution

The data layer is responsible for **hiding multi-ticker complexity** from consumers. When a security requires data from multiple Bloomberg tickers (e.g., CDX HY needs price from one ticker and spread from another), the data layer:

1. **Resolves** each channel to its ticker/field combination
2. **Fetches** data from each ticker independently
3. **Combines** all channels into a single DataFrame indexed by date
4. **Returns** unified security data with all requested columns

### Example: CDX HY 5Y

**Catalog definition:**
```json
{
  "cdx_hy_5y": {
    "primary_ticker": "CDX HY CDSI GEN 5Y Corp",
    "data_channels": {
      "spread": {
        "ticker": "CDX HY CDSI GEN 5Y SPRD Corp",
        "field": "PX_LAST"
      },
      "price": {
        "field": "PX_LAST"
      }
    }
  }
}
```

**Resolution logic:**
| Channel | Ticker Resolution | Bloomberg Call |
|---------|-------------------|----------------|
| `spread` | Has explicit `ticker` → use it | `BDH("CDX HY CDSI GEN 5Y SPRD Corp", "PX_LAST")` |
| `price` | No `ticker` → use `primary_ticker` | `BDH("CDX HY CDSI GEN 5Y Corp", "PX_LAST")` |

**Resulting DataFrame:**
```
            price    spread
2024-01-02  99.25    325.0
2024-01-03  99.30    320.0
...
```

Consumer code sees only `cdx_hy_5y` with both columns—no awareness of underlying ticker complexity.

### Channel-Aware Fetch Flow

```
fetch_security(security="cdx_hy_5y", channels=["price", "spread"])
    │
    ├─► Lookup catalog: cdx_hy_5y.data_channels
    │
    ├─► For each channel:
    │       spread → ticker="CDX HY...SPRD", field="PX_LAST"
    │       price  → ticker="CDX HY...Corp", field="PX_LAST" (primary)
    │
    ├─► Batch Bloomberg request (or sequential if needed)
    │
    ├─► Merge results by date index
    │
    └─► Return DataFrame with columns: [price, spread, security]
```

### Default Channel Selection

If `channels` parameter not specified, the data layer fetches **all defined channels** for the security. This ensures downstream consumers always have complete data available.

## Fetch Interface

**Primary interface** (fetches all channels):

```python
def fetch_security_data(
    source: BloombergSource,
    security: str,
    channels: list[str] | None = None,  # None = all channels
) -> pd.DataFrame:
    """
    Fetch security data, combining multiple tickers if needed.
    
    Resolves each channel to its ticker/field, fetches from Bloomberg,
    and merges into a single DataFrame with one column per channel.
    """
```

**Purpose-aware interface** (for convenience):

```python
def fetch_for_purpose(
    source: BloombergSource,
    security: str,
    purpose: Literal["indicator", "pnl", "display"],
) -> pd.DataFrame:
    """Fetch data for specified purpose, resolving channel automatically."""
```

**Explicit channel interface** (single channel):

```python
def fetch_security_channel(
    source: BloombergSource,
    security: str,
    channel: str,  # "spread", "price", "level"
) -> pd.DataFrame:
    """Fetch specific data channel."""
```

## Workflow Override

Workflows can override display channel:

```yaml
label: hy_analysis
signal: cdx_etf_spread_diff
product: cdx_hy_5y
strategy: balanced
display_channel: price  # Override instrument-type default
```

## FileSource Compatibility

For FileSource (synthetic/local data), the same catalog structure applies but with simplified resolution:

- **No ticker field**: FileSource ignores `ticker` in channel definitions
- **Single file per security**: `cdx_hy_5y.parquet` must contain all channel columns
- **Validation**: FileSource validates that requested channels exist as columns in the parquet file

```python
# FileSource behavior
fetch_security_data(FileSource(data_path), "cdx_hy_5y", channels=["price", "spread"])
# → Loads cdx_hy_5y.parquet, validates columns [price, spread] exist
```

This maintains provider abstraction: same catalog, same fetch interface, different internal resolution.

## Layer Responsibilities

| Layer | Uses | Channel Source |
|-------|------|----------------|
| Indicator transformation | `indicator` purpose | Instrument type default |
| Score/signal transformation | Inherited from indicator | N/A |
| Backtest engine | `pnl` purpose | Security's `quote_type` → corresponding channel |
| Suitability evaluation | `display` purpose | Instrument type default |
| Performance analysis | `display` purpose | Instrument type default |
| Visualization | `display` purpose | Instrument type default (or workflow override) |

## File Changes

1. **Rename** `bloomberg_ticker` → `primary_ticker`
2. **Add** `data_channels` to each security (ticker/field mappings)
3. **Add** `instrument_defaults` section for instrument type usage preferences
4. **Keep** `quote_type` unchanged (already controls PnL method)
5. **Remove** `bloomberg_instruments.json` (field mappings move to `data_channels`)

## Migration

| Old Field | New Location |
|-----------|--------------|
| `bloomberg_ticker` | `primary_ticker` |
| `quote_type` | Unchanged |
| `bloomberg_fields` (instruments.json) | `data_channels` per security |
| `field_mapping` (instruments.json) | `data_channels` per security |
