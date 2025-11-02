# Governance Design Plan for Coding Agents — aponyx Framework

**Purpose:**  
This document defines the governance architecture for the *aponyx* research framework. It serves as guidance for coding agents and contributors to maintain a consistent, modular, and evolvable system without introducing unnecessary complexity or coupling.

---

## 1. Design Intent

The governance system exists to:
- Provide **structure without friction** for researchers.  
- Keep **layers isolated yet interoperable** through clear conventions.  
- Ensure **consistency and reproducibility** across data, models, and backtests.  
- Remain **simple enough to discard or refactor** as the project evolves.

This framework is pre-production and rapidly evolving. Governance should therefore be lightweight, explicit, and disposable.

---

## 2. High-Level Governance Model

Governance in *aponyx* is organized around three pillars:

| Pillar | Scope | Persistence | Description |
|--------|--------|--------------|--------------|
| **Config** | Paths, constants, defaults | Hardcoded in `config/` | Declares static project settings and directory locations. |
| **Registry** | Data and metadata tracking | JSON file | Tracks datasets and their lineage. |
| **Catalog** | Model and signal definitions | JSON file | Declares signals and computational assets available for research. |

Each pillar owns a single JSON or constant source of truth. No automatic merging or runtime inference is allowed.

---

## 3. Core Design Principles

1. **Single Source of Truth per Concern**  
   Each governance domain (config, registry, catalog) has exactly one canonical file.

2. **Flat, Readable Metadata**  
   All metadata should be inspectable and editable by hand in JSON format.

3. **Functional and Stateless**  
   Governance components load and return plain data structures. They do not hold runtime state.

4. **Pure Dependencies**  
   Governance modules never import from higher layers (e.g., models or backtest).

5. **Determinism**  
   Loading a governance object from disk must always yield the same in-memory representation.

6. **Replaceability**  
   Governance constructs should be easy to replace later (e.g., switch JSON → database) without rewriting other layers.

7. **Convention over Abstraction**  
   Avoid frameworks, inheritance, or dependency injection. Use naming and directory conventions instead.

---

## 4. Governance Layers

### 4.1 Configuration (`config/`)

- Declares constant paths, project root, and cache directories.
- Must be deterministic at import time.  
- No dynamic configuration or environment-variable logic.
- Used by all layers for locating data, cache, and registries.

### 4.2 Registry (`data/registry.py`)

- Tracks datasets produced or consumed by the framework.
- Maintains lightweight metadata such as instrument, source, and date range.
- Each dataset is uniquely identified by name and stored in a single JSON registry.
- Supports basic operations: register, lookup, list.

### 4.3 Catalog (`models/registry.py`, `models/signal_catalog.json`)

- Enumerates all available signal definitions.
- Each entry specifies: name, description, data requirements, and whether it is enabled.
- The catalog acts as the research “menu” from which signals are selected for computation.
- Catalog edits are manual and version-controlled; no runtime mutation.

---

## 5. Governance Spine

Governance is unified conceptually through a shared minimal pattern, not through shared code.  
Each domain (config, registry, catalog) follows the same lifecycle:

1. **Load** from a static source (constants or JSON file).  
2. **Inspect** or query (e.g., list enabled signals).  
3. **Use** in downstream processes (fetching data, computing signals).  
4. **Optionally Save** if new metadata is produced.  

This pattern forms the “governance spine” across all layers.

---

## 6. Layer Boundaries and Import Rules

| Layer | May Import From | Must Not Import From |
|-------|-----------------|----------------------|
| `config/` | None | All others |
| `persistence/` | `config` | `data`, `models`, `backtest` |
| `data/` | `config`, `persistence`, `data` (own modules) | `models`, `backtest`, `visualization` |
| `models/` | `config`, `data` (schemas only) | `backtest`, `visualization` |
| `backtest/` | `config`, `models` | `data`, `visualization` |
| `visualization/` | None | All others |

This ensures acyclic dependency flow and reproducible behavior.

---

## 7. Governance Behavior Expectations

- **Immutability:** Governance objects (config, registry, catalog) are treated as immutable within a session.
- **Transparency:** All governance files are stored in plain text (JSON) and version-controlled.
- **Deterministic I/O:** Loading or saving governance files must yield identical structures across systems.
- **No Runtime Globals:** All governance data must be passed explicitly between functions.

---

## 8. Extensibility Guidelines

1. To add new governance types (e.g., metrics catalog), mirror the same pattern: flat JSON + loader functions.
2. New layers must define their own canonical registry or catalog file.
3. If a governance artifact becomes large, split it into multiple JSON files within a single directory and merge deterministically at load time.
4. Governance code should never depend on external libraries; built-in `json` and `pathlib` are sufficient.

---

## 9. Future-Proofing

Although backward compatibility is not a concern, good governance discipline enables smoother evolution. Future versions can introduce:
- Schema validation (via JSON Schema or Pydantic)
- Catalog composition (base + user overlay)
- Version tagging for metadata records
- A unified CLI for inspecting governance state

These are deferred until the framework stabilizes.

---

## 10. Summary

| Goal | Approach |
|------|-----------|
| Simplicity | Single JSON per domain, no frameworks |
| Consistency | Shared structure and conventions |
| Transparency | Human-readable governance data |
| Isolation | Layer boundaries enforced |
| Replaceability | Stateless, functional patterns |
| Reproducibility | Deterministic loading and saving |

The result is a governance system that provides **clarity, safety, and composability**, without adding unnecessary abstraction or operational weight.

---

**End of Document**
