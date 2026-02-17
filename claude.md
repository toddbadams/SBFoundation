# Strawberry Context

**Version**: 3.1
**Last Updated**: 2026-02-17
**Maintenance**: Update when changing architecture patterns, modifying dataset_keymap.yaml structure, or adding new domains/contracts.

## Purpose
Strawberry Foundation is a **Bronze + Silver ONLY data acquisition and validation package**. It ingests raw vendor data (Bronze) and promotes it to validated, typed, conformed datasets (Silver). The pipeline is executed via `src/sbfoundation/api.py` (`SBFoundationAPI`) and configured declaratively in `config/dataset_keymap.yaml`.

**CRITICAL**: This project contains **ONLY Bronze and Silver layers**. The Gold layer (dimension modeling, surrogate keys, star schemas, aggregations) exists in a separate downstream project that imports SBFoundation as a dependency.

---

## Quick Reference
- **Adding new dataset?** → Edit `config/dataset_keymap.yaml` (see Section 5.3)
- **Modifying data pipeline?** → `src/sbfoundation/api.py` + `config/dataset_keymap.yaml`
- **Complex refactor?** → Section 7 (ExecPlans)
- **Writing a DTO?** → Section 8 (DTO Contracts)
- **Writing a recipe?** → Section 9 (Recipe Contracts)
- **DuckDB schema?** → Section 10 (DuckDB Storage)
- **Before modifying `/src`?** → Section 11 (DDD Review Checklist)

---

## 1) Architecture

Strawberry implements **ONLY the first two layers** of a medallion/lakehouse architecture:

| Layer | Purpose | Description | In This Project? |
|---|---|---|---|
| **Bronze (Raw/Landing)** | Ingest & Preserve | Exact vendor payloads, append-only, immutable, fully traceable | ✅ YES |
| **Silver (Clean/Conformed)** | Clean & Standardize | Validated, normalized, deduplicated, schema-enforced datasets | ✅ YES |
| **Gold (Business/Analytics)** | Model & Aggregate | Star schemas, surrogate keys, dimensions, facts, rollups | ❌ NO - Separate project |

**What Silver Tables Contain:**
- Clean, typed business data from Bronze
- Natural business keys only (e.g., `ticker`, `symbol`, `date`)
- Lineage metadata: `bronze_file_id`, `run_id`, `ingested_at`
- **NO surrogate keys** (e.g., `instrument_sk`)
- **NO foreign key relationships**
- **NO cross-table joins or aggregations**

**What Belongs in Gold (NOT this project):**
- Surrogate key resolution (`instrument_sk`, `company_sk`, etc.)
- Dimension tables (`dim_instrument`, `dim_company`, etc.)
- Fact tables with foreign keys
- Star/snowflake schemas
- Cross-dataset aggregations and rollups

**Ingested data domains**: fundamentals, market data, analytical data, alternative data (macro/economics).

**Ticker-based execution order**: `instrument` → `company` → `fundamentals` → `technicals`

---

## 2) Hard Constraints (do not violate)

1. **Bronze is append-only**. Stores exact vendor payloads + required metadata. No business logic, interpretation, or correction in Bronze.

2. **All dataset mappings are declarative** and defined in `config/dataset_keymap.yaml` (authoritative). This defines dataset identity, Bronze→Silver mappings, DTO schemas, and DatasetRecipe definitions.

3. **Ingestion runtime behavior** is driven by `dataset_keymap.yaml`. Do not invent alternate URL construction, placeholder substitution, base-date/from-date logic, or cadence gating.

4. **DTOs are the only allowed boundary** between Bronze and Silver. Every Silver table is written and read via DTOs.

5. **Silver writes are idempotent** via DuckDB UPSERT/MERGE using KEY_COLS from the YAML keymap. No dataset may promote to Silver without a keymap entry.

6. **NO Gold layer operations in this project**. Silver must NOT:
   - Resolve surrogate keys (e.g., `instrument_sk`)
   - Query Gold tables (e.g., `gold.dim_instrument`)
   - Create dimension or fact tables
   - Add foreign key columns to Silver tables
   - Perform cross-dataset joins or aggregations

**Enforcement**: `DatasetService` validates keymap on load; `tests/unit/dataset/` validates config parsing; `tests/e2e/` verifies end-to-end behavior; mypy enforces types.

---

## 3) Conflict Resolution

When documents conflict, priority order:
1. `config/dataset_keymap.yaml` — authoritative for all dataset definitions and mappings
2. Recipe contracts (Section 9) — for recipe semantics and behavior
3. Bronze contracts (Section 6) — for Bronze storage format
4. `docs/prompts/technology_stack.md` — runtime/tooling defaults
5. Architecture (Section 1) — conceptual intent

---

## 4) Canonical Definitions (Key Terms)

- **Asset**: tradable financial instrument (equity, ETF, bond, etc.)
- **Instrument**: concrete tradeable representation of an asset (e.g., AAPL on NASDAQ)
- **Universe**: defined, versioned set of instruments for a strategy
- **Dataset**: structured collection of data with defined schema; immutable within a run
- **Feature**: measured property of an instrument at a specific time (descriptive, not prescriptive)
- **Factor**: hypothesis about expected returns (cross-sectional, directional, validated)
- **Signal**: converts features into investment intent (encodes opinion)
- **Screener**: binary eligibility filter (in/out gate, defensive not predictive)
- **Strategy**: decision framework combining universe + screeners + signals + portfolio construction rules
- **Run**: single execution of a pipeline with unique ID, immutable inputs/outputs

**Canonical data flow**: Data → Datasets → Features → Screeners → Signals → Portfolio → Orders → Trades → Positions → Monitoring → Feedback

**Guiding principle**: Facts are not opinions. Opinions are not allocations. Allocations are not executions.

---

## 5) Working Rules for Generated Changes

### 5.1 Style and Typing
- **Python**: `>=3.11,<3.14`
- **Packaging**: Poetry (primary), uv (local dev)
- **Type system**: Built-in generics (`list[...]`, `dict[...]`), strict typing with mypy
- **Code style**: Black (formatting), isort (imports), flake8 (linting)
- **Testing**: pytest with fixtures in `tests/unit/` and `tests/e2e/`
- Keep functions deterministic and testable; avoid hidden side effects

### 5.2 Repo Patterns
- Bronze: raw results + metadata only
- Silver: validated, typed, conformed datasets
- All layer mappings defined in `config/dataset_keymap.yaml`

### 5.3 Adding a New Dataset
All dataset definitions live in `config/dataset_keymap.yaml`:

**Required fields**:
- `domain`: company | economics | fundamentals | technicals
- `source`: Data source identifier (e.g., fmp, fred)
- `dataset`: Internal dataset name (stable identifier)
- `discriminator`: Empty string or unique discriminator for partitioning
- `ticker_scope`: per_ticker | global
- `silver_schema`: Target Silver schema name
- `silver_table`: Target Silver table name
- `key_cols`: Columns forming the unique key
- `row_date_col`: Column name for row-level dates (or null)

**Recipe definition** (nested under `recipes`):
- `plans`: List of FMP plans (e.g., ["basic"])
- `data_source_path`: Relative API path (no base URL)
- `query_vars`: Query params using `__ticker__`, `__from_date__`, `__to_date__` placeholders
- `date_key`: Observation date field name (null for snapshots)
- `cadence_mode`: "interval"
- `min_age_days`: Minimum age before re-fetching
- `run_days`: Weekdays to run (e.g., ["sat"])
- `help_url`: Vendor documentation link

**DTO Schema** (nested under `dto_schema`):
- `dto_type`: Python import path to DTO class
- `columns`: List of `{name, type, nullable}` definitions

**Example**:
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
    dto_type: sbfoundation.dtos.company.company_dto.CompanyDTO
    columns:
      - {name: ticker, type: str, nullable: false}
      - {name: company_name, type: str, nullable: true}
```

Also add the dataset to `DATASETS` and `DTO_TYPES` constants. If a new domain or source is introduced, add it to `DOMAINS` / `DATA_SOURCES`.

---

## 6) Bronze Layer Contracts

### 6.1 BronzeResult JSON Contract
Every stored Bronze file MUST contain:

| Field | Type | Notes |
|---|---|---|
| `request` | dict | Serialized RunRequest |
| `now` | str (ISO8601) | Processing timestamp |
| `elapsed_microseconds` | int | Latency |
| `headers` | str\|None | Response headers |
| `status_code` | int | HTTP status |
| `reason` | str | HTTP reason phrase |
| `content` | list[dict] | Always a list (may be empty) |
| `error` | str\|None | Populated for non-200 or invalid payloads |

`BronzeResult` computes `hash`, `first_date`, `last_date` in memory but does **not** serialize them.

### 6.2 File Naming & Partitioning
```
/bronze/<domain>/<source>/<dataset>/<ticker_or_none>/<injestion_date>-<uuid>.json
```
- One JSON file per API response, UTF-8, deterministic serialization (`sort_keys=True`)
- Append-only: no overwrites; re-ingestion always creates a new file

### 6.3 Promotion Gate
Bronze → Silver promotion requires (checked in `BronzeResult.canPromoteToSilverWith`):
- `status_code == 200`
- `error is None`
- `content` is non-empty OR dataset `allows_empty_content`

### 6.4 Run Summary Manifest
One manifest per run at: `/bronze/manifests/summary-<RUN_ID>-<YYYY-MM-DD>.json`

Required fields: `run_id`, `started_at`, `finished_at`, `records_written`, `records_failed`, `filenames`, `failed_filenames`

---

## 7) ExecPlans

Use an ExecPlan for complex features or significant refactors. An ExecPlan is a **self-contained, living document** that enables a complete novice to implement a feature end-to-end.

**Use when**:
- Adding a new domain or layer
- Changing core contracts (DTO, Recipe, Bronze storage format)
- Multi-file refactors affecting 5+ modules
- Adding new external integrations or data sources
- Implementing new strategy or portfolio rules

**Do NOT use for**: single-file bug fixes, adding fields to DTOs, simple test additions, documentation updates.

### ExecPlan Required Sections
```
## Purpose / Big Picture       — user-visible behavior enabled by this change
## Progress                    — checkbox list, timestamped, always current state
## Surprises & Discoveries     — unexpected behaviors, bugs, insights + evidence
## Decision Log                — every decision with rationale and date/author
## Outcomes & Retrospective    — what was achieved, gaps, lessons learned
## Context and Orientation     — current state, key files, term definitions
## Plan of Work                — prose sequence of edits (file + location + change)
## Concrete Steps              — exact commands with expected output transcripts
## Validation and Acceptance   — observable behavior to verify (not just "compiles")
## Idempotence and Recovery    — safe retry/rollback instructions
## Artifacts and Notes         — concise transcripts/diffs proving success
## Interfaces and Dependencies — libraries, types, function signatures required
```

ExecPlans are stored as `.md` files under `docs/prompts/`. They are living documents — update all sections as work proceeds.

---

## 8) DTO Contracts (Bronze ↔ Silver Boundary)

DTOs are the **only allowed contract surface** between Bronze and Silver. All DTOs inherit from `BronzeToSilverDTO`.

### 8.1 Required Methods

| Method | Direction | Notes |
|---|---|---|
| `from_row(cls, row: Mapping[str, Any], ticker: str \| None) -> Self` | Bronze → DTO | Parses one row; classmethod |
| `to_dict(self) -> dict[str, Any]` | DTO → Silver | Emits JSON-serializable primitives only |
| `key_date` (property) | — | Vendor date or `date.min` for snapshots |

Optional: `from_series_row(cls, row: pd.Series) -> Self` for Silver → DTO round-trip.

### 8.2 DTO Rules
- **One endpoint → one DTO**; class name: `<DatasetNamePascalCase>DTO`
- All attributes and `to_dict()` keys are **snake_case**
- Declare `KEY_COLS: list[str]` (typically `["ticker"]`; composite for multi-key datasets)
- `ticker` is passed in by the ingestion loop — DTOs must NOT fetch or compute it
- `to_dict()` must emit: primitives, ISO 8601 strings for dates, `None` for missing values (not `"null"`)
- Missing strings → `""`; missing booleans → `False`; numeric failures → `None`
- Discriminator-based datasets set `is_ticker_based=False` in the recipe
- `key_date`: return parsed vendor date if available; otherwise `date.min`

### 8.3 Naming Convention
`from_row` must match the call site exactly. Use `BronzeToSilverDTO` helper methods for safe type parsing — do not hand-cast inline.

---

## 9) Recipe Contracts (DatasetRecipe Semantics)

A `DatasetRecipe` is a declarative spec for ingesting exactly one source endpoint.

### 9.1 URL Construction (authoritative)
```
url = f"{DATA_SOURCES_CONFIG[source][BASE_URL]}{recipe.data_source_path}"
```
Never embed the base URL in `data_source_path`.

### 9.2 Placeholder Substitution
`RunProvider._get_query_vars()` substitutes in `recipe.query_vars`:
- `TICKER_PLACEHOLDER` → current ticker
- `FROM_DATE_PLACEHOLDER` → computed `from_date` (see §9.3)
- `TO_DATE_PLACEHOLDER` → today
- `apikey` → injected from config; `None`-valued params removed

### 9.3 from_date / Base-Date Semantics
`from_date` is computed from prior ingested data, not the recipe:
- Stored as `RunDataDatesDTO.to_date` keyed by `"{domain}-{source}-{dataset}-{ticker}"`
- If found: `from_date = stored to_date` (continue from last end date)
- If not found: `from_date = universe.from_date`

**Due-ness** (interval mode): `injestion_date >= base_date + min_age_days`

### 9.4 Ticker-Based vs Global
- `is_ticker_based=True`: `RunProvider` loops over `universe.tickers()`; include `"symbol": TICKER_PLACEHOLDER`
- `is_ticker_based=False`: single request with `ticker=None` (e.g., economics indicators)

### 9.5 Discriminators (Shared Datasets)
When many logical series share one dataset (e.g., economics indicators), every recipe must define `discrimnator` (typo preserved in code for compatibility) to ensure deterministic filenames/partitions. Example: `{"name": "gdp"}`, `{"name": "cpi"}`.

### 9.6 snapshot vs Timeseries `date_key`
- Timeseries: set `date_key` to the row field containing the observation date (e.g., `"date"`, `"periodOfReport"`)
- Snapshot/metadata endpoints (e.g., profile, peers): `date_key=None` → runtime falls back to today's date for cadence progression

### 9.7 Failure Semantics
A failed run request does NOT crash the run. A `BronzeResult` is still created with `error` set, written via `ResultFileAdapter`, and `RunContext` counters are updated. The system is "audit-first".

---

## 10) DuckDB Storage

DuckDB is the canonical store for Silver data plus manifests, watermarks, and operational metadata. Bronze remains immutable raw JSON files on disk.

**Note**: While DuckDB supports a `gold` schema, **this project does not create or manage Gold tables**. The Gold layer is implemented in a separate downstream project.

### 10.1 Configuration
- `DUCKDB_FOLDER`: location of the DuckDB file (dev/prod differs)
- `repo_root_path`: absolute path to repo root
- `BRONZE_FOLDER`: repo-relative base folder for bronze files (e.g., `data/bronze`)
- `MIGRATIONS_FOLDER`: repo-relative folder for SQL migrations (e.g., `db/migrations`)
- `DATASET_KEYMAP_FOLDER`: repo-relative path to `config/dataset_keymap.yaml`

All file paths stored in DuckDB are **repo-root-relative**. Single DuckDB file for dev and prod (copyable from Raspberry Pi to Windows).

### 10.2 Schema Layout
```
ops     — manifests, watermarks, migrations, run summaries (managed by this project)
silver  — conformed datasets, one table per dataset (managed by this project)
gold    — NOT MANAGED BY THIS PROJECT (downstream Gold project only)
```

### 10.3 ops Tables

**ops.bronze_manifest** (one row per Bronze JSON file):
`bronze_file_id` (PK), `run_id`, `domain`, `source`, `dataset`, `discriminator`, `ticker`, `request_ts`, `response_ts`, `ingested_at`, `status_code`, `error_message`, `file_path_rel` (repo-relative), `payload_hash`, `coverage_from_date`, `coverage_to_date`, `content_length_bytes`, `is_promotable`

**ops.dataset_watermarks** (composite PK on dataset identity):
`domain`, `source`, `dataset`, `discriminator`, `ticker`, `coverage_from_date`, `coverage_to_date`, `last_success_at`, `last_run_id`, `last_bronze_file_id`, `notes`

**ops.gold_build** (one row per Gold build):
`gold_build_id` (PK), `run_id`, `model_version` (git SHA), `started_at`, `finished_at`, `status`, `error_message`, `input_watermarks` (LIST\<VARCHAR\>), `tables_built` (LIST\<VARCHAR\>), `row_counts`

**ops.schema_migrations**: `version` (PK, e.g., `20260112_001`), `name`, `applied_at`, `checksum`

**ops.file_ingestions**: per-step metrics for bronze/silver/gold (run_id, file_id, coverage, hashes, row counts, errors, timestamps)

### 10.4 Silver Tables
- One table per dataset in `silver` schema
- Required columns on every silver row: `bronze_file_id`, `run_id`, `ingested_at`
- Required row date: use DTO `date_key` field if defined; otherwise `as_of_date`
- UPSERT/MERGE keyed by `KEY_COLS` from `config/dataset_keymap.yaml` — idempotent on replay

### 10.5 Gold Tables
- Star-schema modeling (dims/facts)
- Every Gold table includes: `gold_build_id`, `model_version` (git SHA)
- Gold outputs reproducible given: referenced input watermarks + git SHA

### 10.6 Dataset Identity (for manifests and watermarks)
Identity = `domain` + `source` + `dataset` + `discriminator` (empty string if unused) + `ticker` (empty string if unused)

`input_watermarks` serialization format:
`domain|source|dataset|discriminator|ticker@coverage_from=YYYY-MM-DD;coverage_to=YYYY-MM-DD`

### 10.7 Transactions
- Bronze: write file → insert manifest row (actionable error if manifest insert fails; leave file for replay)
- Silver promotion: MERGE/UPSERT + watermark updates in one transaction
- Gold build: **NOT in this project** (handled by downstream Gold project)

---

## 11) DDD Review Checklist (Before Modifying `/src`)

Before modifying production code, review the target classes against:

1. **Aggregate boundaries** — Identify aggregate root(s); confirm they own transactional invariants while collaborators stay read-only
2. **Invariants** — Enumerate explicit, testable runtime checks (config validation, identifier limits, timing)
3. **Context map consistency** — Verify domain/source/dataset/cadence values come from shared constants, not redefined locally
4. **Dependency direction** — Classes depend only on lower-level contracts (DTOs, config, helpers); no circular references
5. **Entity vs. value-object** — Immutable data carriers (value objects) vs. stateful aggregates (entities)

**Good Python Practices to check**: clear structure + comments; explicit type annotations + dataclasses; docstrings for behavior; context managers for resources; consistent naming.

Record findings in the ExecPlan's `Surprises & Discoveries` and `Review Findings` sections before changing code. Save the resulting ExecPlan under `docs/prompts/`.

---

## 12) Hardware / Ops Telemetry Domain

The `ops/telemetry` domain samples host performance metrics and persists them as Silver time-series. Runs on **Raspberry Pi** (primary, Linux) and **Windows** (secondary dev).

**Silver Dataset** (`OPS_HOST_METRICS_DATASET`): append-only, one row per sample per host.
Required: `as_of` (UTC timestamp), `host_id`, `os`, `arch`, `cpu_pct`, `cpu_count_logical`, `ram_*_mb`, `swap_*_mb`, `disk_root_*_gb`, `net_rx_bytes`, `net_tx_bytes`
Optional (nullable): `cpu_temp_c`, `throttle_flags` (Pi only), `cpu_freq_mhz`, `process_rss_mb`, `process_cpu_pct`

**Gold Rollups** (e.g., 5-minute aggregations): **NOT in this project** (handled by downstream Gold project).

**Implementation structure** (`src/sb/SBFoundation/ops/telemetry/`):
`config.py`, `providers/base.py`, `providers/portable_psutil.py`, `providers/linux_pi_sensors.py`, `schemas.py`, `writer.py`, `rollups.py`, `flow.py`

**Cross-platform**: use `psutil` for portable metrics (CPU/RAM/disk/network). Temperature and throttle flags are Linux-only and optional; failures must degrade gracefully (return null, never raise).

**Config**: `enabled`, `host_id` (default: hostname), `sample_interval_seconds` (default: 10), `rollup_interval_minutes` (default: 5), `disk_mount`, `network_interface`.

---

## 13) What "Done" Looks Like
- Changes compile/type-check (mypy-friendly)
- Formatting consistent with repo standards (Black/isort/flake8)
- No contract violations (DTO purity, Bronze immutability, recipe semantics)
- Silver writes are idempotent via UPSERT with KEY_COLS from keymap
- Where meaningful, include a test fixture or example usage

---

END OF DOCUMENT
