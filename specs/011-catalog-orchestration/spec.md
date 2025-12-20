# Feature Specification: Unified YAML Catalog & CatalogManager

**Feature Branch**: `011-catalog-orchestration`  
**Created**: December 20, 2025  
**Status**: Draft  
**Input**: User description: "Unified YAML Catalog with CatalogManager for consolidating 5+ JSON catalogs into single source of truth with sync, validation, and CLI commands"

## Problem Statement

The aponyx framework currently has **5+ JSON catalogs scattered across layers**:
- `src/aponyx/models/signal_catalog.json`
- `src/aponyx/models/indicator_transformation.json`
- `src/aponyx/models/score_transformation.json`
- `src/aponyx/models/signal_transformation.json`
- `src/aponyx/backtest/strategy_catalog.json`

**Pain Points**:
1. JSON lacks comments, making catalogs hard to document and maintain
2. No unified API for catalog access—each registry loads its own file
3. Cross-catalog validation is manual and error-prone
4. Adding new entries requires editing multiple files across different directories
5. No centralized way to list or query all available configurations

## Solution Overview

**YAML as single source of truth** with JSON sync for runtime compatibility.

```
config/
└── catalogs.yaml    # Human-edited source (with comments)

src/aponyx/models/   # Generated JSON (runtime)
src/aponyx/backtest/ # Generated JSON (runtime)
```

A `CatalogManager` class provides a unified API for CRUD operations, validation, and synchronization.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Edit Catalog Configuration (Priority: P1)

A researcher wants to add a new signal to the framework. Instead of finding the correct JSON file and ensuring proper syntax, they edit a single YAML file with inline comments explaining each field.

**Why this priority**: This is the primary daily interaction—making catalog maintenance intuitive and error-resistant is the core value proposition.

**Independent Test**: Can be fully tested by creating `catalogs.yaml`, adding a signal entry, running sync, and verifying the JSON output matches expectations.

**Acceptance Scenarios**:

1. **Given** a valid `config/catalogs.yaml` file exists, **When** a user adds a new signal entry with comments, **Then** the entry is preserved with proper YAML syntax and comments remain intact.

2. **Given** a user adds a signal referencing a non-existent indicator transformation, **When** they run validation, **Then** a clear error message identifies the missing reference.

3. **Given** `catalogs.yaml` contains all catalog entries, **When** user runs `aponyx catalog sync`, **Then** all JSON catalog files are regenerated with correct content.

---

### User Story 2 - Validate Catalog Integrity (Priority: P1)

A developer wants to ensure all catalog references are valid before committing changes. They run a validation command that checks cross-references between signals, transformations, and strategies.

**Why this priority**: Validation prevents runtime errors and is essential for CI/CD integration—equal priority with editing.

**Independent Test**: Can be fully tested by creating a `catalogs.yaml` with intentional errors and verifying the validator catches them all.

**Acceptance Scenarios**:

1. **Given** a signal references `indicator_transformation: "invalid_name"`, **When** user runs `aponyx catalog validate`, **Then** error message shows: "Signal 'X' references unknown indicator_transformation 'invalid_name'".

2. **Given** all catalog entries have valid cross-references, **When** user runs `aponyx catalog validate`, **Then** output shows "All catalog references valid" with summary of entries checked.

3. **Given** a required field is missing from an entry, **When** validation runs, **Then** error identifies the entry and missing field.

---

### User Story 3 - Sync YAML to JSON (Priority: P2)

After editing `catalogs.yaml`, a user needs to regenerate the JSON files that the runtime uses. They run a sync command that generates all JSON catalogs from the YAML source.

**Why this priority**: Sync is the bridge between editing and runtime—critical but happens after editing.

**Independent Test**: Can be tested by modifying YAML, running sync, and comparing JSON output byte-for-byte with expected output.

**Acceptance Scenarios**:

1. **Given** `catalogs.yaml` has been modified, **When** user runs `aponyx catalog sync`, **Then** all JSON files are regenerated at their original locations.

2. **Given** sync completes successfully, **When** user runs existing workflows, **Then** the registries load the new JSON files without errors.

3. **Given** `catalogs.yaml` has syntax errors, **When** user runs sync, **Then** sync fails with clear error message and no JSON files are modified.

---

### User Story 4 - List Available Catalog Items (Priority: P2)

A researcher wants to see all available signals, strategies, or transformations without opening files. They use the CLI or CatalogManager API to query available items.

**Why this priority**: Discovery improves usability but isn't essential for core functionality.

**Independent Test**: Can be tested by calling `list_items()` API and verifying returned items match YAML content.

**Acceptance Scenarios**:

1. **Given** `catalogs.yaml` contains 3 signals, **When** user runs `catalog.list_items("signals")`, **Then** all 3 signal names are returned.

2. **Given** some entries have `enabled: false`, **When** user lists items with filter, **Then** disabled items can be included or excluded based on filter.

---

### User Story 5 - Migrate Existing JSON to YAML (Priority: P3)

An administrator needs to bootstrap the new YAML catalog from existing JSON files. They run a migration command that consolidates all JSON catalogs into a single YAML file.

**Why this priority**: One-time migration—essential for adoption but only runs once per project.

**Independent Test**: Can be tested by running migration on existing JSON files and verifying YAML output contains all entries.

**Acceptance Scenarios**:

1. **Given** existing JSON catalogs contain valid entries, **When** migration runs, **Then** `catalogs.yaml` is created with all entries properly categorized.

2. **Given** migration completes, **When** user runs sync, **Then** regenerated JSON files match original JSON files.

---

### Edge Cases

- What happens when `catalogs.yaml` doesn't exist? → Error with instructions to run migration or create file.
- How does system handle duplicate entry names within a category? → Validation error identifying duplicates.
- What happens if JSON files are manually edited after sync? → Next sync overwrites changes (YAML is source of truth).
- How are entries with special characters in names handled? → YAML escaping rules apply; validation ensures compatibility.
- What happens during sync if a JSON file is locked/read-only? → Sync fails with clear error identifying the file.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a single `config/catalogs.yaml` file as the source of truth for all catalog entries.

- **FR-002**: System MUST preserve YAML comments when loading and saving the catalog file.

- **FR-003**: System MUST provide a `CatalogManager` class with methods: `load()`, `save()`, `sync()`, `get(category, name)`, `list_items(category)`, `add(category, entry)`, `remove(category, name)`, `validate()`.

- **FR-004**: System MUST validate cross-references between catalog categories (e.g., signals referencing indicator_transformations).

- **FR-005**: System MUST generate JSON catalog files at their existing locations during sync to maintain backward compatibility.

- **FR-006**: System MUST provide CLI commands: `aponyx catalog sync` and `aponyx catalog validate`.

- **FR-007**: System MUST provide a migration utility to generate initial `catalogs.yaml` from existing JSON files.

- **FR-008**: System MUST fail sync if YAML validation fails, leaving existing JSON files unchanged.

- **FR-009**: System MUST support all existing catalog categories: `indicator_transformations`, `score_transformations`, `signal_transformations`, `signals`, `strategies`.

- **FR-010**: System MUST maintain the exact JSON structure expected by existing registries (array of objects format).

### Key Entities

- **CatalogManager**: Central class for all catalog operations; holds in-memory catalog state and manages file I/O.

- **CatalogEntry**: Generic representation of a catalog item with category, name, and category-specific attributes.

- **ValidationResult**: Contains validation status (pass/fail), list of errors, and summary statistics.

- **Catalog Categories**: Logical groupings within the YAML file—`indicator_transformations`, `score_transformations`, `signal_transformations`, `signals`, `strategies`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can add a new signal entry in under 2 minutes using YAML with inline documentation comments.

- **SC-002**: Validation catches 100% of cross-reference errors before runtime (broken references between signals and transformations).

- **SC-003**: Sync command regenerates all 5 JSON catalog files in under 5 seconds.

- **SC-004**: Existing workflows continue to function without modification after migration (backward compatibility).

- **SC-005**: Developers can discover all available signals/strategies via a single command or API call.

- **SC-006**: CI pipeline can validate catalog integrity, failing builds on reference errors.

- **SC-007**: Round-trip migration (JSON → YAML → JSON) produces identical output to original JSON files.

---

## Assumptions

1. **YAML library choice**: A YAML library that preserves comments will be used (e.g., `ruamel.yaml`).

2. **File location**: The canonical `catalogs.yaml` file lives at `config/catalogs.yaml` relative to project root.

3. **Git workflow**: Generated JSON files remain in version control for runtime compatibility; YAML is the edited source.

4. **No runtime YAML parsing**: Runtime code continues to load JSON files; YAML is only used at development/build time.

5. **Entry schemas**: Existing JSON schemas remain unchanged; YAML entries map 1:1 to JSON structures.

---

## Out of Scope

- Database-backed catalog storage
- Web UI for catalog editing
- Automatic schema migration between catalog versions
- Real-time catalog reloading (restart required)
- Multi-file YAML support (splitting catalogs across files)
