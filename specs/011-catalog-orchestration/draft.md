# Spec 011: YAML Catalog & CatalogManager

## Problem

- 5+ JSON catalogs scattered across layers
- JSON lacks comments, hard to maintain
- No unified API for catalog access

## Solution

**YAML as single source of truth** with JSON sync for runtime compatibility.

```
config/
└── catalogs.yaml    # Human-edited source

src/aponyx/models/   # Generated JSON (runtime)
src/aponyx/backtest/ # Generated JSON (runtime)
```

## Deliverables

1. `config/catalogs.yaml` - Unified YAML with all catalog entries
2. `src/aponyx/catalog/manager.py` - CatalogManager class
3. CLI commands: `aponyx catalog sync`, `aponyx catalog validate`

## CatalogManager API

| Method | Purpose |
|--------|---------|
| `load()` | Load from YAML source |
| `save()` | Save changes to YAML |
| `sync()` | Generate JSON catalogs from YAML |
| `get(category, name)` | Retrieve catalog item |
| `list_items(category)` | List available items |
| `add_signal(...)` | Add new signal |
| `remove(category, name)` | Remove item |
| `validate()` | Cross-reference validation |

## Migration Path

1. Generate initial `catalogs.yaml` from existing JSON files
2. Implement CatalogManager with sync
3. Add CLI commands
4. Update CI to run `catalog validate`

## File Structure

```
config/
└── catalogs.yaml              # Single source of truth
src/aponyx/
└── catalog/
    └── manager.py             # CatalogManager (CRUD + sync)
```
