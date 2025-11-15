# Caching Layer Design

## Overview

The caching layer provides transparent time-to-live (TTL) based caching for data fetching operations. It reduces redundant data loading while maintaining freshness guarantees for research workflows.

**Design Goal:** Simple file-based caching with explicit TTL control—no complex invalidation logic or distributed cache dependencies.

## Architecture

### Cache Location

```
data/
  cache/
    file/           # File-based provider cache
      cdx_ig_5y_abc123.parquet
      vix_def456.parquet
      hyg_ghi789.parquet
    bloomberg/      # Bloomberg provider cache
      cdx_ig_5y_jkl012.parquet
```

### Key Components

| Component | Module | Purpose |
|-----------|--------|---------|
| `Cache` | `data/cache.py` | TTL-based cache manager |
| `FileSource` | `data/providers/file.py` | Cached file loading |
| Cache keys | Hash-based | Deterministic cache key generation |

## How It Works

### Basic Flow

```python
from aponyx.data import fetch_cdx, FileSource
from aponyx.config import CACHE_ENABLED, CACHE_TTL_DAYS

# Caching is controlled by global config (default: enabled, 7 days TTL)
# First call: loads from file, caches result
source = FileSource("data/raw/cdx_data.parquet")
cdx_df = fetch_cdx(source, security="cdx_ig_5y")  # Cache miss → load + cache

# Second call within TTL: returns cached data
cdx_df = fetch_cdx(source, security="cdx_ig_5y")  # Cache hit → instant return

# After TTL expires: reloads and updates cache
# (Automatic based on cache file modification time)
```

### Cache Key Generation

Keys are generated from:
- Data source configuration
- Instrument identifier
- Query parameters (security, date range, etc.)

```python
# Deterministic hash-based keys generated internally
# Key structure: {instrument}_{cache_key}.parquet
# Example: cdx_ig_5y_abc123def456.parquet
# Cache keys are SHA-256 hashes of source + params
```

## When to Use Caching

### ✅ Use Cache For:

- **Repeated data loads** in iterative development
- **Expensive transformations** on raw data
- **Multiple signals** using the same base data
- **Jupyter notebook workflows** with cell re-execution
- **Bloomberg data** to avoid hitting rate limits

### ❌ Skip Cache For:

- **One-time scripts** or production runs
- **Real-time data** that changes frequently
- **Small files** (<1MB) where loading is instant
- **Debugging data issues** where you need fresh data

### Control Cache Usage

```python
# Use cache (default)
df = fetch_cdx(source, security="cdx_ig_5y")  # use_cache=True by default

# Skip cache for fresh data
df = fetch_cdx(source, security="cdx_ig_5y", use_cache=False)

# Intraday update: refresh only today's data point (Bloomberg only)
df = fetch_cdx(source, security="cdx_ig_5y", update_current_day=True)
```

### Intraday Cache Updates

**Problem:** During trading hours, you may want fresh data without re-fetching the entire historical series.

**Solution:** Use `update_current_day=True` to update only today's data point via Bloomberg's BDP function.

```python
from aponyx.data import fetch_cdx, BloombergSource

source = BloombergSource()

# Morning: Full history via BDH
cdx_df = fetch_cdx(source, security="cdx_ig_5y")

# Afternoon: Update only today via BDP (~10x faster)
cdx_df = fetch_cdx(source, security="cdx_ig_5y", update_current_day=True)
```

**Cache Decision Flow:**

```
┌─ use_cache=False ──→ Full fetch, no cache
│
└─ use_cache=True
   │
   ├─ Cache doesn't exist ──→ Full fetch, save cache
   │
   └─ Cache exists
      │
      ├─ Cache is stale (age ≥ TTL) ──→ Full fetch, update cache
      │
      └─ Cache is fresh (age < TTL)
         │
         ├─ update_current_day=False ──→ Return cache
         │
         └─ update_current_day=True
            │
            ├─ Bloomberg source ──→ Fetch today (BDP), merge, update cache
            │
            └─ Other source ──→ Return cache (parameter ignored)
```

**How it works:**
1. Loads existing cache
2. Fetches only current day's value using BDP
3. Replaces/appends today's row in cached data
4. Saves updated cache

**Benefits:**
- **~10x faster** than full refetch
- **500x less data transfer** (1 point vs 1800 days)
- Preserves historical data in cache

**Limitations:**
- Bloomberg source only (ignored for FileSource)
- Requires existing cache (falls back to full fetch if none)
- Returns cached data unchanged on weekends/holidays

**Timezone handling:** Uses US/Eastern (America/New_York) for "today" to match market hours.

## Configuration

### TTL Settings

```python
# TTL configured globally in config module
from aponyx.config import CACHE_ENABLED, CACHE_TTL_DAYS

# Default: 7 days TTL
print(f"Cache enabled: {CACHE_ENABLED}, TTL: {CACHE_TTL_DAYS} days")

# Override per fetch call
cdx_df = fetch_cdx(source, security="cdx_ig_5y", use_cache=False)  # Skip cache
cdx_df = fetch_cdx(source, security="cdx_ig_5y", use_cache=True)   # Use cache
```

### Cache Directory

```python
from pathlib import Path
from aponyx.data.cache import Cache

# Default: data/cache/file/
cache = Cache()

# Custom cache location
cache = Cache(cache_dir=Path("./custom_cache"))
```

## Cache Invalidation

### Automatic Invalidation

Cache entries automatically expire based on:
1. **TTL expiration:** Entry older than `CACHE_TTL_DAYS` (default: 1 day)
2. **Source modification:** Source file modified after cache entry created

**Note:** When cache is stale (age ≥ TTL), `update_current_day=True` is ignored and a full refetch occurs

### Manual Invalidation

```python
# Manual cache clearing via filesystem
from pathlib import Path
from aponyx.config import DATA_DIR

cache_dir = DATA_DIR / "cache" / "file"

# Clear entire provider cache
import shutil
shutil.rmtree(cache_dir)
cache_dir.mkdir(parents=True)

# Or remove specific cached files
for cached_file in cache_dir.glob("cdx_*"):
    cached_file.unlink()
```

## Example Usage

### Basic Caching

```python
from aponyx.data import fetch_cdx, FileSource
import time

# Caching is automatic when use_cache=True (default)
source = FileSource("data/raw/cdx.parquet")

# First load: reads from disk
start = time.time()
df1 = fetch_cdx(source, security="cdx_ig_5y")
print(f"First load: {time.time() - start:.2f}s")  # ~0.5s

# Second load: returns from cache
start = time.time()
df2 = fetch_cdx(source, security="cdx_ig_5y")
print(f"Cached load: {time.time() - start:.2f}s")  # ~0.01s
```

### Signal Research Workflow

```python
from aponyx.data import fetch_cdx, fetch_vix, fetch_etf, FileSource
from aponyx.models import compute_cdx_vix_gap, compute_cdx_etf_basis
from aponyx.models.config import SignalConfig

# Caching is automatic - load data once, reuse across iterations
cdx_df = fetch_cdx(FileSource("data/raw/cdx.parquet"), security="cdx_ig_5y")
vix_df = fetch_vix(FileSource("data/raw/vix.parquet"))
etf_df = fetch_etf(FileSource("data/raw/etf.parquet"), security="hyg")

# Compute multiple signals - data loads are cached
config = SignalConfig(lookback=20)
signal1 = compute_cdx_vix_gap(cdx_df, vix_df, config)
signal2 = compute_cdx_etf_basis(cdx_df, etf_df, config)
```

### Jupyter Notebook Pattern

```python
# Cell 1: Setup (run once)
from aponyx.data import fetch_cdx, FileSource
from aponyx.models import compute_spread_momentum
from aponyx.models.config import SignalConfig

source = FileSource("data/raw/cdx.parquet")

# Cell 2: Load data (fast re-execution via automatic caching)
cdx_df = fetch_cdx(source, security="cdx_ig_5y")  # Instant on re-run

# Cell 3: Experiment with signals (iterate quickly)
config = SignalConfig(lookback=20)  # Try different lookbacks
signal = compute_spread_momentum(cdx_df, config)
```

### Intraday Monitoring Workflow

```python
from aponyx.data import fetch_cdx, BloombergSource
from aponyx.models import compute_spread_momentum
from aponyx.models.config import SignalConfig
import time

source = BloombergSource()
config = SignalConfig(lookback=20)

# Run monitoring loop
while True:
    # Efficient intraday update (BDP only)
    cdx_df = fetch_cdx(source, security="cdx_ig_5y", update_current_day=True)
    
    # Compute signal
    signal = compute_spread_momentum(cdx_df, config)
    print(f"Latest signal: {signal.iloc[-1]:.3f}")
    
    # Wait 15 minutes
    time.sleep(15 * 60)
```

## Implementation Details

### Cache Storage Format

- **Format:** Parquet (same as source data for consistency)
- **Metadata:** Stored in cache entry filename
- **Structure:** Flat directory, hash-based names prevent collisions

### Performance Characteristics

| Operation | Time | Data Transfer | Use Case |
|-----------|------|---------------|----------|
| **File (uncached)** | 50-5000ms | Varies | First load |
| **File (cached)** | 5-20ms | None | Subsequent loads |
| **Bloomberg BDH** | 2-5 sec | ~500KB (1800 days) | Full history |
| **Bloomberg BDP** | 0.2-0.5 sec | ~1KB (1 point) | Current day only |
| **Intraday update** | 0.2-0.5 sec | ~1KB | Morning → afternoon |

**Speedup: Intraday update vs full refetch:** ~10x faster, 500x less data.

**Note:** Performance depends on disk I/O, network latency, and Bloomberg server load.

### Memory Considerations

- Cache stores data on disk (not RAM)
- Each cached file adds disk space overhead
- Default cache cleared manually or via TTL expiration
- No automatic LRU eviction (simple time-based only)

## Limitations

### Not Implemented

- **LRU eviction:** No automatic cache size limits
- **Distributed cache:** Single machine only
- **Compression:** No additional compression beyond Parquet
- **Cache warming:** No pre-population mechanism
- **Partial cache hits:** All-or-nothing caching (no incremental updates)

### Design Trade-Offs

| Feature | Status | Rationale |
|---------|--------|-----------|
| TTL-based expiration | ✅ Implemented | Simple, predictable behavior |
| LRU eviction | ❌ Not implemented | Adds complexity; manual cleanup sufficient |
| Multi-level cache | ❌ Not implemented | Single file layer adequate for research |
| Cache statistics | ❌ Not implemented | Logging provides visibility |
| Distributed cache | ❌ Not implemented | Single researcher workflows assumed |

## Best Practices

1. **Use consistent TTL** across a research session (e.g., 1 hour)
2. **Clear cache** when switching to new data sources
3. **Monitor cache size** periodically (`du -sh data/cache/`)
4. **Don't cache sensitive data** (API keys, credentials)
5. **Log cache hits/misses** for debugging (already implemented)
6. **Use short TTL** for frequently updated data sources

## Troubleshooting

### Cache Not Working

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Look for cache-related log messages:
# INFO - Cache hit: cdx_ig_5y_abc123.parquet
# DEBUG - Cache miss or stale: vix_def456.parquet
```

### Stale Data Issues

```python
# Force cache bypass for fresh data
df = fetch_cdx(source, security="cdx_ig_5y", use_cache=False)

# Or manually clear cache directory
from pathlib import Path
from aponyx.config import DATA_DIR
import shutil

cache_dir = DATA_DIR / "cache" / "file"
shutil.rmtree(cache_dir)
cache_dir.mkdir(parents=True)
```

### Disk Space Issues

```bash
# Check cache size
du -sh data/cache/

# Clear old entries
rm -rf data/cache/file/*
```

### Intraday Update Not Refreshing

**Symptom:** `update_current_day=True` returns stale data

**Possible causes:**
1. Cache doesn't exist yet (first call creates full cache)
2. Cache is stale (age ≥ TTL triggers full refetch)
3. Non-Bloomberg source (parameter ignored for FileSource)
4. Weekend/holiday (no current data available, returns cache unchanged)

**Solution:**
```python
import logging
logging.basicConfig(level=logging.INFO)

# Check log messages
df = fetch_cdx(source, security="cdx_ig_5y", update_current_day=True)
# INFO - Cache hit: cdx_abc123.parquet
# INFO - Updating current day data from Bloomberg
# INFO - No current data available (non-trading day)  # ← Weekend
```

---

**Maintained by stabilefrisur**  
**Last Updated:** October 31, 2025
