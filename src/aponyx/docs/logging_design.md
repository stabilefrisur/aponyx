# Logging Design for Persistence Layer

## Overview

The persistence layer now includes comprehensive logging at INFO and DEBUG levels to provide visibility into data operations without compromising performance or test reliability.

## Design Principles

### 1. **Module-Level Loggers (Recommended Pattern)**

```python
import logging

logger = logging.getLogger(__name__)
```

**Why this approach?**

- ✅ **Hierarchical naming**: Logger names follow module structure (`aponyx.persistence.parquet_io`)
- ✅ **Configurable at any level**: Users can control logging for entire package, submodules, or individual modules
- ✅ **No global configuration in library code**: The library never calls `logging.basicConfig()` - that's the application's responsibility
- ✅ **Works with pytest**: Tests run cleanly without logging output unless explicitly enabled
- ✅ **Standard Python practice**: Follows official Python logging guidelines for library code

**Anti-pattern (what we avoided):**
```python
# DON'T DO THIS in library code
logging.basicConfig(level=logging.INFO)  # Forces configuration on users
```

### 2. **INFO vs DEBUG Levels**

#### INFO Level (User-Facing Operations)
Logged at INFO when:
- Files are saved or loaded
- Registry operations occur (register, update, remove)
- Operations complete successfully with summary statistics

**Examples:**
```python
logger.info("Saving DataFrame to Parquet: path=%s, rows=%d, columns=%d", path, len(df), len(df.columns))
logger.info("Registered dataset: name=%s, instrument=%s, rows=%s", name, instrument, row_count)
```

**Characteristics:**
- High-level operations
- Always relevant to users
- Should appear in production logs
- Includes key metrics (rows, columns, file sizes)

#### DEBUG Level (Developer Details)
Logged at DEBUG when:
- Low-level details about operations
- File sizes after writing
- Applied filters and transformations
- Non-existent directories

**Examples:**
```python
logger.debug("Successfully saved %d bytes to %s", path.stat().st_size, path)
logger.debug("Applied date filter: start=%s, end=%s, resulting_rows=%d", start_date, end_date, len(df))
```

**Characteristics:**
- Implementation details
- Useful for debugging
- Can be verbose
- Typically disabled in production

### 3. **Structured Logging with Parameters**

We use **%-formatting with parameters** instead of f-strings in log statements:

```python
# ✅ CORRECT: Lazy evaluation, structured logging
logger.info("Loaded %d rows from %s", len(df), path)

# ❌ AVOID: Eager evaluation, string concatenation
logger.info(f"Loaded {len(df)} rows from {path}")
```

**Benefits:**
- **Performance**: String formatting only happens if the log level is enabled
- **Structured logging**: Log aggregation tools can parse parameters
- **Consistency**: Standard Python logging best practice

### 4. **Warning Level for Recoverable Errors**

```python
logger.warning("Failed to extract stats from %s: %s", file_path, str(e))
```

Used when:
- An operation fails but execution continues
- Non-critical errors occur
- User should be aware but no exception is raised

## What We Log

### Parquet I/O (`parquet_io.py`)

| Operation | Level | Information Logged |
|-----------|-------|-------------------|
| `save_parquet()` | INFO | Path, rows, columns, compression |
| `save_parquet()` | DEBUG | File size after save |
| `load_parquet()` | INFO | Path, columns filter |
| `load_parquet()` | INFO | Rows and columns loaded |
| `load_parquet()` | DEBUG | Date filter details, resulting rows |
| `list_parquet_files()` | INFO | Number of files found, directory, pattern |
| `list_parquet_files()` | DEBUG | Directory not exists |

### JSON I/O (`json_io.py`)

| Operation | Level | Information Logged |
|-----------|-------|-------------------|
| `save_json()` | INFO | Path, number of top-level keys |
| `save_json()` | DEBUG | File size after save |
| `load_json()` | INFO | Path |
| `load_json()` | DEBUG | Number of top-level keys loaded |

### Registry (`registry.py`)

| Operation | Level | Information Logged |
|-----------|-------|-------------------|
| `__init__()` | INFO | Registry path, number of datasets (loaded/created) |
| `register_dataset()` | INFO | Name, instrument, row count |
| `register_dataset()` | WARNING | Failed to extract stats from file |
| `register_dataset()` | DEBUG | Registering non-existent file |
| `update_dataset_stats()` | INFO | Name, rows, date range after update |
| `remove_dataset()` | INFO | Name removed, file deleted (if applicable) |

## User Configuration Examples

### Application Setup (Demo/Scripts)

```python
import logging

# Basic configuration for scripts
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
```

### Fine-Grained Control

```python
import logging

# Enable DEBUG for parquet_io only
logging.getLogger("aponyx.persistence.parquet_io").setLevel(logging.DEBUG)

# Disable INFO for json_io
logging.getLogger("aponyx.persistence.json_io").setLevel(logging.WARNING)

# Enable all persistence layer at INFO
logging.getLogger("aponyx.persistence").setLevel(logging.INFO)
```

### Production Configuration

```python
import logging

# Production: INFO to file, WARNING to console
file_handler = logging.FileHandler("aponyx.log")
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

logging.getLogger("aponyx").addHandler(file_handler)
logging.getLogger("aponyx").addHandler(console_handler)
```

### Testing (Silence Logs)

```python
# In conftest.py or test setup
import logging

logging.getLogger("aponyx").setLevel(logging.CRITICAL)
```

Or use pytest's `caplog` fixture:
```python
def test_something(caplog):
    with caplog.at_level(logging.INFO, logger="aponyx.persistence"):
        # Test code
        pass
    
    assert "Saving DataFrame to Parquet" in caplog.text
```

## Benefits of This Design

### 1. **Non-Invasive**
- Library doesn't force logging configuration
- Users control what they see
- Tests run silently by default

### 2. **Observable**
- Users can track data operations
- Debugging is easier with detailed logs
- Production monitoring is straightforward

### 3. **Performance**
- Lazy evaluation (%-formatting)
- No overhead when logging is disabled
- Structured data for log aggregation

### 4. **Maintainable**
- Consistent logging pattern across modules
- Clear signal-to-noise ratio (INFO vs DEBUG)
- Easy to add more logging as code evolves

### 5. **Standards-Compliant**
- Follows Python logging best practices
- Compatible with enterprise logging infrastructure
- Works with popular logging frameworks (loguru, structlog)

## Example Output

With `logging.basicConfig(level=logging.INFO)`:

```
00:08:40 - aponyx.persistence.parquet_io - INFO - Saving DataFrame to Parquet: path=data/cdx_ig_5y.parquet, rows=215, columns=2, compression=snappy
00:08:41 - aponyx.data.registry - INFO - Loaded existing registry: path=data/.registries/registry.json, datasets=4
00:08:41 - aponyx.persistence.parquet_io - INFO - Loading Parquet file: path=data/cdx_ig_5y.parquet, columns=all
00:08:41 - aponyx.persistence.parquet_io - INFO - Loaded 215 rows, 2 columns from data/cdx_ig_5y.parquet
```

Clean, informative, and actionable.

## Future Enhancements

Potential additions as the project grows:

1. **Metrics Integration**: Add timing decorators for performance monitoring
2. **Structured Logging**: Migrate to `structlog` for JSON-formatted logs
3. **Audit Trail**: Add UUID tracking for data lineage
4. **Performance Logging**: Track I/O performance metrics

---

**Summary**: The logging design follows Python best practices for library code, providing visibility without imposing configuration, and maintaining clean separation between library and application concerns.

**Maintained by:** stabilefrisur  
**Last Updated:** December 13, 2025
