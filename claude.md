# Strawberry Context

**Version**: 2.1
**Last Updated**: 2026-02-12
**Maintenance**: Update when adding/removing AI_context docs, changing architecture patterns, or modifying dataset_keymap.yaml structure

## Purpose
This file is the **entry point** for all AI context in `docs/AI_context` and `docs/prompts`. Use it to find the authoritative document for any task and to resolve conflicts between documents.

Strawberry Foundation is a **Bronze + Silver data acquisition and validation package**. It ingests raw vendor data (Bronze) and promotes it to validated, typed, conformed datasets (Silver). The pipeline is orchestrated via `src/data_layer/orchestrator.py` and configured declaratively in `config/dataset_keymap.yaml`. Start with the architecture and technology stack docs before making changes.

---

## Quick Reference
For common tasks, start here:
- **Adding new dataset?** → Edit `config/dataset_keymap.yaml` (see Section 5.3)
- **Modifying data pipeline?** → `src/data_layer/orchestrator.py` + `config/dataset_keymap.yaml`
- **Understanding recipe semantics?** → `docs/AI_context/recipe_contracts.md`
- **Complex refactor?** → Section 7 (ExecPlans)

---

## 1) Start here (primary sources)
Use these documents first, in order, for **discovering relevant context** when implementing or updating code:

1. **Architecture & layering**
   - `docs/AI_context/architecture.md`

2. **Repo/runtime/tooling defaults**
   - `docs/prompts/technology_stack.md`

3. **Structured storage (DuckDB)**
   - `docs/AI_context/duckdb.md`

4. **Dataset configuration (Bronze -> Silver mappings)**
   - `config/dataset_keymap.yaml` (authoritative configuration)
   - `docs/AI_context/recipe_contracts.md` (recipe semantics)
   - `docs/AI_context/bronze_to_silver_dto_contract.md` (legacy reference)

5. **Strategy system behavior**
   - `docs/prompts/trading_strategies.md`

---

## 2) Hard constraints (do not violate)
1. **Bronze is append-only** and stores exact vendor payloads with required metadata; no "fixing" or business logic in Bronze. See `docs/AI_context/bronze_data_contracts.md`.

2. **All dataset mappings are declarative** and defined in `config/dataset_keymap.yaml`. This single source of truth defines:
   - Dataset identity (domain/source/dataset/discriminator/ticker_scope)
   - Bronze → Silver mappings (silver_schema/silver_table/key_cols)
   - DTO schemas (columns, types, nullability)
   - DatasetRecipe definitions (data_source_path, query_vars, cadence_mode, etc.)

3. **Ingestion runtime behavior** is driven by configurations in `dataset_keymap.yaml`. Do not invent alternate URL construction, placeholder substitution, base-date/from-date logic, or cadence gating. See `docs/AI_context/recipe_contracts.md` for recipe semantics.

**Enforcement mechanisms:**
- `config/dataset_keymap.yaml` validation on load (via `DatasetService`)
- Unit tests in `tests/unit/data_layer/dataset/` validate config parsing
- Integration tests in `tests/e2e/` verify end-to-end behavior
- Type checking via mypy ensures schema compliance

---

## 3) Conflict resolution
When documents appear to conflict, use these **resolution priorities** (distinct from Section 1's discovery order):

1. **Configuration in `config/dataset_keymap.yaml`** is authoritative for all dataset definitions, schemas, and mappings.
2. DatasetRecipe / ingestion contract docs (`recipe_contracts.md`) for recipe semantics and behavior.
3. Bronze data contracts (`bronze_data_contracts.md`) for Bronze layer storage format.
4. Technology stack for runtime/tooling defaults.
5. Architecture doc for conceptual intent.

**Example**: If `config/dataset_keymap.yaml` defines a dataset with `silver_table: "company-profile"` but documentation suggests a different table name, use the keymap configuration (Rule 1 - configuration is authoritative).

---

## 4) Full context documentation index

### Core Configuration:
- **`config/dataset_keymap.yaml`** - **AUTHORITATIVE** source for all dataset definitions, schemas, and Bronze→Silver mappings

### By Architecture Layer:
**Bronze Layer**:
- `docs/AI_context/bronze_data_contracts.md` - Storage format and metadata requirements
- `docs/AI_context/recipe_contracts.md` - Recipe semantics and ingestion behavior

**Silver Layer**:
- `config/dataset_keymap.yaml` (datasets section) - Table mappings and DTO schemas
- `docs/AI_context/silver_data_contracts.md` - Silver layer patterns
- `docs/AI_context/bronze_to_silver_dto_contract.md` - Legacy DTO contract reference

### Infrastructure & Cross-Cutting:
- `docs/AI_context/architecture.md` - Overall system design
- `docs/prompts/technology_stack.md` - Runtime, tooling, dependencies
- `docs/AI_context/duckdb.md` - Database layer
- `docs/AI_context/test_context.md` - Testing patterns
- `docs/AI_context/hardware_ops.md` - Operational requirements
- `docs/AI_context/PLANS.md` - ExecPlan methodology

### Strategy & Domain Knowledge:
- `docs/prompts/trading_strategies.md` - Strategy behavior rules
- `docs/AI_context/hyman_minsky.md` - Economic framework
- `docs/AI_context/quant_value.md` - Valuation methodology
- `docs/AI_context/cononical_definitions.md` - Term definitions

---

## 5) Working rules for generated changes
### 5.1 Style and typing
- **Python**: `>=3.11,<3.14` (see `docs/prompts/technology_stack.md` for full stack)
- **Packaging**: Poetry (primary), uv (local dev)
- **Type system**: Built-in generics (`list[...]`, `dict[...]`), strict typing with mypy
- **Code style**: Black (formatting), isort (imports), flake8 (linting)
- **Testing**: pytest with fixtures in `tests/unit/` and `tests/e2e/`
- Keep functions deterministic and testable; avoid hidden side effects

### 5.2 Repo patterns
- Keep layering boundaries clean:
  - Bronze: raw results + metadata only
  - Silver: validated, typed, conformed datasets (dedupe planned)
- All layer mappings are defined in `config/dataset_keymap.yaml`

### 5.3 Adding a new dataset (configuration-based approach)
All dataset definitions live in `config/dataset_keymap.yaml`. To add a new dataset, add an entry to the `datasets` section with:

**Required fields**:
- `domain`: Logical domain (company, economics, fundamentals, technicals)
- `source`: Data source identifier (e.g., fmp, fred)
- `dataset`: Internal dataset name (stable identifier)
- `discriminator`: Empty string or unique discriminator for partitioning
- `ticker_scope`: Either "per_ticker" or "global"
- `silver_schema`: Target Silver schema name
- `silver_table`: Target Silver table name
- `key_cols`: List of columns that form the unique key
- `row_date_col`: Column name for row-level dates (or null)

**Recipe definition** (nested under `recipes`):
- `plans`: List of FMP plans this recipe runs under (e.g., ["basic"])
- `data_source_path`: Relative API path
- `query_vars`: Query parameters (use `__ticker__`, `__from_date__`, `__to_date__` placeholders)
- `date_key`: Field name for observation date (or null for snapshots)
- `cadence_mode`: Usually "interval"
- `min_age_days`: Minimum age before re-fetching
- `run_days`: List of weekdays to run (e.g., ["sat"])
- `help_url`: Link to vendor documentation

**DTO Schema definition** (nested under `dto_schema`):
- `dto_type`: Python import path to DTO class (e.g., "data_layer.dtos.company.company_dto.CompanyDTO")
- `columns`: List of column definitions with `name`, `type`, `nullable`

**Example entry structure**:
```yaml
- domain: company
  source: fmp
  dataset: company-profile
  discriminator: ''
  ticker_scope: per_ticker
  silver_schema: silver
  silver_table: fmp_company_profile
  key_cols: [ticker]
  row_date_col: null
  recipes:
    - plans: [basic]
      data_source_path: profile
      query_vars: {symbol: __ticker__}
      date_key: null
      cadence_mode: interval
      min_age_days: 365
      run_days: [sat]
      help_url: https://example.com/docs
  dto_schema:
    dto_type: data_layer.dtos.company.company_dto.CompanyDTO
    columns:
      - {name: ticker, type: str, nullable: false}
      - {name: company_name, type: str, nullable: true}
```

---

## 6) What "done" looks like
For code changes produced by Codex:
- Changes compile/type-check at a reasonable baseline (mypy-friendly)
- Formatting consistent with repo standards (Black/isort/flake8)
- No contract violations (DTO purity, Bronze immutability, recipe semantics)
- Where meaningful, include a small test fixture or example usage


## 7) ExecPlans

When writing complex features or significant refactors, use an ExecPlan (as described in `docs/AI_context/PLANS.md`) from design to implementation.

**Use an ExecPlan when**:
- Adding a new domain or layer to the architecture
- Changing core contracts (DTO, Recipe, Bronze storage format)
- Multi-file refactors affecting 5+ modules
- Adding new external integrations or data sources
- Implementing new strategy logic or portfolio rules
- Significant performance optimizations requiring proof-of-concept

**Do NOT use ExecPlan for**:
- Single-file bug fixes
- Adding fields to existing DTOs
- Simple test additions
- Documentation updates

END OF DOCUMENT
