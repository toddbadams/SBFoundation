# Strawberry Context

**Version**: 3.8
**Last Updated**: 2026-03-14
**Maintenance**: Update when changing architecture patterns, modifying dataset_keymap.yaml structure, or adding new domains/contracts.

## Purpose

Strawberry Foundation is a **Bronze + Silver + Gold data acquisition, validation, and modeling package**. It ingests raw vendor data (Bronze), promotes it to validated, typed, conformed datasets (Silver), and builds a star-schema analytics layer (Gold) from Silver. The pipeline is executed via `src/sbfoundation/api.py` (`SBFoundationAPI`) and configured declaratively in `config/dataset_keymap.yaml`.

---

## Quick Reference

- **Adding new dataset?** → Edit `config/dataset_keymap.yaml` (see Section 5.3)
- **Modifying data pipeline?** → `src/sbfoundation/api.py` + `config/dataset_keymap.yaml`
- **Complex refactor?** → Section 7 (ExecPlans); backlog in `docs/backlog/`, completed in `docs/completed/`
- **Writing a DTO?** → Section 8 (DTO Contracts)
- **Writing a recipe?** → Section 9 (Recipe Contracts)
- **DuckDB schema?** → Section 10 (DuckDB Storage)
- **Gold layer design?** → Section 10.4–10.6 (Gold Tables, dims, facts)
- **Feature column naming?** → Section 5.2 (all feature columns must end in `_f`)
- **Feature calculations?** → Section 2, constraint 9 (prefer DuckDB SQL over Python)
- **Before modifying `/src`?** → Section 11 (DDD Review Checklist)
- **Logging (format, levels, run_id)?** → Section 13 (Logging)
- **Historical data backfill / debug run?** → Section 14 (Backfill Entrypoints)

---

## 1) Architecture

Strawberry implements **all three layers** of a medallion/lakehouse architecture:

| Layer | Purpose | Description | In This Project? |
|---|---|---|---|
| **Bronze (Raw/Landing)** | Ingest & Preserve | Exact vendor payloads, append-only, immutable, fully traceable | ✅ YES |
| **Silver (Clean/Conformed)** | Clean & Standardize | Validated, normalized, deduplicated, schema-enforced datasets | ✅ YES |
| **Gold (Business/Analytics)** | Model & Aggregate | Star schemas, surrogate keys, dimensions, facts, rollups | ✅ YES |

**What Silver Tables Contain:**

- Clean, typed business data from Bronze
- Natural business keys only (e.g., `ticker`, `symbol`, `date`)
- Lineage metadata: `bronze_file_id`, `run_id`, `ingested_at`
- **NO surrogate keys** (e.g., `instrument_sk`)
- **NO foreign key relationships**
- **NO cross-table joins or aggregations**

**What Gold Contains:**

- Surrogate key resolution (`instrument_sk`, `company_sk`, etc.)
- Static dimension tables bootstrapped from code (`dim_date`, `dim_instrument_type`, `dim_country`, `dim_exchange`, `dim_industry`, `dim_sectors`)
- Data-derived dimension tables built from Silver (`dim_instrument`, `dim_company`)
- Fact tables with foreign keys to dimensions (`fact_eod`, `fact_quarter`, `fact_annual`)
- Placeholder columns for features (always NULL until the feature engine runs); all feature placeholder columns are suffixed `_f` (e.g., `momentum_1m_f`, `volatility_30d_f`)
- **Note**: datasets without an `instrument_sk` join (e.g., FRED series, market-risk-premium) remain Silver-only and are NOT promoted to Gold

**Ingested data domains**: fundamentals, market data, analytical data, alternative data (macro/economics).

**Ticker-based execution order**: `instrument` → `company` → `fundamentals` → `technicals`

---

## 2) Hard Constraints (do not violate)

1. **Bronze is append-only**. Stores exact vendor payloads + required metadata. No business logic, interpretation, or correction in Bronze.

2. **All dataset mappings are declarative** and defined in `config/dataset_keymap.yaml` (authoritative). This defines dataset identity, Bronze→Silver mappings, DTO schemas, and DatasetRecipe definitions.

3. **Ingestion runtime behavior** is driven by `dataset_keymap.yaml`. Do not invent alternate URL construction, placeholder substitution, base-date/from-date logic, or cadence gating.

4. **DTOs are the only allowed boundary** between Bronze and Silver. Every Silver table is written and read via DTOs.

5. **Silver writes are idempotent** via DuckDB UPSERT/MERGE using KEY_COLS from the YAML keymap. No dataset may promote to Silver without a keymap entry.

6. **Silver must NOT contain Gold-layer concerns**. Silver tables must NOT:
   - Resolve surrogate keys (e.g., `instrument_sk`)
   - Reference Gold tables (e.g., `gold.dim_instrument`)
   - Add foreign key columns
   - Perform cross-dataset joins or aggregations

   Gold promotion is handled exclusively by `GoldDimService` and `GoldFactService` in the `gold/` package, which read from Silver and write to the `gold` DuckDB schema.

7. **FMP bulk CSV field names differ from JSON API docs**. When adding or modifying bulk-endpoint DTOs (e.g., `eod-bulk-price`, `income-bulk`, `key-metrics-bulk`, `ratios-bulk`), always verify field names against actual Bronze file content — the CSV column headers returned by the bulk endpoint frequently differ from the field names documented in the FMP JSON API reference. Do not assume JSON doc field names apply to bulk CSV responses.

9. **Feature calculations must be implemented in DuckDB SQL where possible**. Window functions, cross-sectional aggregations (percentile, z-score, rank), ratio computations, and rolling statistics should be expressed as DuckDB SQL (executed via `duckdb.DuckDBPyConnection`) rather than pulled into Python/pandas. Use Python only when the computation cannot be expressed in SQL (e.g., iterative optimization, external model inference). This is mandatory for performance — pulling large Gold tables into memory for row-by-row Python computation is not acceptable. `EodFeatureService` and `MoatFeatureService` must follow this constraint.

8. **`BronzeService` resolves API keys per source**. `BronzeService` stores only `fmp_api_key` and passes `api_key=self.fmp_api_key if recipe.source == FMP_DATA_SOURCE else None` at every `RunRequest.from_recipe()` call site. Non-FMP sources (e.g., FRED) must have their API keys injected via their own environment variables (e.g., `FRED_API_KEY`), which `RunProvider._get_query_vars()` resolves from `DATA_SOURCES_CONFIG[source][API_KEY]`.

**Enforcement**: `DatasetService` validates keymap on load; `tests/unit/dataset/` validates config parsing; `tests/e2e/` verifies end-to-end behavior; mypy enforces types.

---

## 3) Conflict Resolution

When documents conflict, priority order:

1. `config/dataset_keymap.yaml` — authoritative for all dataset definitions and mappings
2. Recipe contracts (Section 9) — for recipe semantics and behavior
3. Bronze contracts (Section 6) — for Bronze storage format
4. ExecPlans in `docs/backlog/` — runtime/tooling defaults and in-progress decisions
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
- **Gold feature column naming**: all feature placeholder columns in Gold fact tables must end in `_f` (e.g., `momentum_1m_f`, `volatility_30d_f`). Signal/score columns end in `_s`. This suffix is mandatory — do not add feature columns without it.

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

- Purpose / Big Picture       — user-visible behavior enabled by this change
- Progress                    — checkbox list, timestamped, always current state
- Surprises & Discoveries     — unexpected behaviors, bugs, insights + evidence
- Decision Log                — every decision with rationale and date/author
- Outcomes & Retrospective    — what was achieved, gaps, lessons learned
- Context and Orientation     — current state, key files, term definitions
- Plan of Work                — prose sequence of edits (file + location + change)
- Concrete Steps              — exact commands with expected output transcripts
- Validation and Acceptance   — see required structure below
- Idempotence and Recovery    — safe retry/rollback instructions
- Artifacts and Notes         — concise transcripts/diffs proving success
- Interfaces and Dependencies — libraries, types, function signatures required

### Validation and Acceptance — Required Structure

Every ExecPlan **must** include a `Validation and Acceptance` section structured into the following four tiers. Include only the tiers that apply; mark inapplicable tiers as "N/A — not applicable for this change."

**Tier 1 — Quick checks** (no DB or network required; runnable in < 1 minute)
: Unit tests, import sanity, CLI `--help`, backward-compat assertions, hash/serialization stability. Each check must include the exact command to run and the expected output.

**Tier 2 — DB checks** (requires local DuckDB; no external API calls)
: Confirm migrations ran, tables exist, UPSERT idempotency, query returns expected shape. Each check must include the exact Python snippet or SQL and the expected output.

**Tier 3 — Integration / dry-run check** (requires config + DB; no live API writes)
: Run the affected domain or service with `enable_bronze=False` / `enable_silver=False`. Confirm log output, request counts, and discriminator patterns match the new design. This is the **key gate** — must pass before PR approval.

**Tier 4 — Post-live-run checks** (requires a real pipeline run with live API)
: Confirm Silver tables are populated, row counts are non-zero, and re-running the same date is idempotent. These are listed as numbered acceptance criteria (not necessarily run before PR approval, but must be checked before merging to `main`).

### ExecPlan Execution Rules

**First step — always**: Before any code changes, create a feature branch:

```
git checkout -b feature/<short-kebab-description>
```

All work for the ExecPlan must be committed to this branch. Do not commit to `main`.

**Last step — always**: When all Concrete Steps are complete and Validation and Acceptance criteria are met, stop and prompt the user in Claude with:

> "ExecPlan `<name>` is complete and fully tested. All code is committed to branch `feature/<name>`. Please confirm you are satisfied and I will create a PR for your approval."

Only after the user confirms: commit any remaining changes to the feature branch, then create a PR targeting `main` with a descriptive title and summary of what was changed and why. Do not merge the PR.

ExecPlans are stored as `.md` files under `docs/backlog/` (pending implementation) or `docs/completed/` (fully implemented and closed out). They are living documents — update all sections as work proceeds. When closing out an ExecPlan, move the file from `docs/backlog/` to `docs/completed/`.

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

**Note**: This project creates and manages all three schemas — `ops`, `silver`, and `gold`. The Gold layer (dims + facts) is built from Silver data by `GoldDimService` and `GoldFactService` in the `gold/` package.

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
gold    — star schema: static dims, data-derived dims, fact tables (managed by this project)
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

**Static dimension tables** (bootstrapped via SQL, never updated by ingestion):
`dim_date`, `dim_instrument_type`, `dim_country`, `dim_exchange`, `dim_industry`, `dim_sectors`

**Data-derived dimension tables** (built from Silver by `GoldDimService`):
`dim_instrument` — ticker + instrument type/exchange/sector/industry/country FKs + `instrument_sk` PK
`dim_company` — ticker + `instrument_sk` FK + company profile fields + dim FKs + `company_sk` PK

**Fact tables** (built from Silver + dims by `GoldFactService`):
`fact_eod` — one row per (instrument_sk, date_sk); EOD pricing (open, high, low, close, adj_close, volume); placeholder `_f` columns for momentum/volatility features (always NULL until feature dev runs)
`fact_quarter` — one row per (instrument_sk, period_date_sk, period); quarterly fundamentals from income/balance/cashflow bulk Silver tables
`fact_annual` — one row per (instrument_sk, period_date_sk); annual (FY) fundamentals merged from income bulk, balance sheet bulk, key metrics bulk, and ratios bulk Silver tables via optional LEFT JOINs

**Silver-only datasets** (no Gold promotion — no `instrument_sk` FK available):
`silver.fred_dgs10`, `silver.fred_usrecm`, `silver.fmp_market_risk_premium` — these stay in Silver and are consumed directly by the feature engine

**Rules for all Gold tables**:
- Every table includes: `gold_build_id`, `model_version` (git SHA)
- Gold outputs are reproducible given: referenced input watermarks + git SHA
- SK assignment uses DuckDB `SEQUENCE` or stable `ROW_NUMBER()` on first build; subsequent builds MERGE on natural keys to preserve existing SKs
- Silver tables must NOT be modified to add Gold-layer columns — Gold builds are strictly read-Silver, write-gold

### 10.6 Dataset Identity (for manifests and watermarks)

Identity = `domain` + `source` + `dataset` + `discriminator` (empty string if unused) + `ticker` (empty string if unused)

`input_watermarks` serialization format:
`domain|source|dataset|discriminator|ticker@coverage_from=YYYY-MM-DD;coverage_to=YYYY-MM-DD`

### 10.7 Transactions

- Bronze: write file → insert manifest row (actionable error if manifest insert fails; leave file for replay)
- Silver promotion: MERGE/UPSERT + watermark updates in one transaction
- Gold build: MERGE/UPSERT dims + facts + `ops.gold_build` log entry, in one transaction per build

---

## 11) DDD Review Checklist (Before Modifying `/src`)

Before modifying production code, review the target classes against:

1. **Aggregate boundaries** — Identify aggregate root(s); confirm they own transactional invariants while collaborators stay read-only
2. **Invariants** — Enumerate explicit, testable runtime checks (config validation, identifier limits, timing)
3. **Context map consistency** — Verify domain/source/dataset/cadence values come from shared constants, not redefined locally
4. **Dependency direction** — Classes depend only on lower-level contracts (DTOs, config, helpers); no circular references
5. **Entity vs. value-object** — Immutable data carriers (value objects) vs. stateful aggregates (entities)

**Good Python Practices to check**: clear structure + comments; explicit type annotations + dataclasses; docstrings for behavior; context managers for resources; consistent naming.

Record findings in the ExecPlan's `Surprises & Discoveries` and `Review Findings` sections before changing code. Save the resulting ExecPlan under `docs/backlog/`.

---

## 12) Hardware / Ops Telemetry Domain

The `ops/telemetry` domain samples host performance metrics and persists them as Silver time-series. Runs on **Raspberry Pi** (primary, Linux) and **Windows** (secondary dev).

**Silver Dataset** (`OPS_HOST_METRICS_DATASET`): append-only, one row per sample per host.
Required: `as_of` (UTC timestamp), `host_id`, `os`, `arch`, `cpu_pct`, `cpu_count_logical`, `ram_*_mb`, `swap_*_mb`, `disk_root_*_gb`, `net_rx_bytes`, `net_tx_bytes`
Optional (nullable): `cpu_temp_c`, `throttle_flags` (Pi only), `cpu_freq_mhz`, `process_rss_mb`, `process_cpu_pct`

**Gold Rollups** (e.g., 5-minute aggregations): Implemented in `gold/` as a `GoldFactService` variant, building `gold.fact_host_metrics` from Silver telemetry rows.

**Implementation structure** (`src/sb/SBFoundation/ops/telemetry/`):
`config.py`, `providers/base.py`, `providers/portable_psutil.py`, `providers/linux_pi_sensors.py`, `schemas.py`, `writer.py`, `rollups.py`, `flow.py`

**Cross-platform**: use `psutil` for portable metrics (CPU/RAM/disk/network). Temperature and throttle flags are Linux-only and optional; failures must degrade gracefully (return null, never raise).

**Config**: `enabled`, `host_id` (default: hostname), `sample_interval_seconds` (default: 10), `rollup_interval_minutes` (default: 5), `disk_mount`, `network_interface`.

---

## 13) Logging

All logging is centralised in `src/sbfoundation/infra/logger.py`.

### 13.1 Key Types

- **`LoggerFactory`** — creates and configures loggers. Accepts optional `log_path` and `log_level` overrides.
- **`SBLogger`** — a `@runtime_checkable` Protocol that extends standard `logging.Logger` with `log_section` and an optional `run_id` keyword argument on every log method. Use `SBLogger` as the type annotation for injected loggers.

### 13.2 Creating a Logger

Each class creates its own named logger in `__init__`, accepting an injectable `SBLogger | None` parameter for testability:

```python
from sbfoundation.infra.logger import LoggerFactory, SBLogger

class MyService:
    def __init__(self, logger: SBLogger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
```

Use `self.__class__.__name__` (for class-level loggers) or `__name__` (for module-level loggers). Both styles exist in the codebase.

### 13.3 run_id Correlation

Every log method (`info`, `debug`, `warning`, `error`, `critical`, `exception`, `log`) accepts an optional `run_id: str | None = None` keyword argument. When provided, the message is automatically prefixed with `run_id=<value> |`:

```python
self._logger.info("Processing 42 items", run_id=run.run_id)
# → 2026-02-20 07:15:32 | INFO    | MyService      | run_id=abc123 | Processing 42 items
```

Always pass `run_id` for any log message emitted during a pipeline run so messages are grep-filterable.

### 13.4 log_section

Use `log_section` to emit a prominent banner at each major pipeline phase:

```python
self._logger.log_section(run.run_id, "Processing economics domain")
# → run_id=abc123 | ========== Processing economics domain ==========
```

### 13.5 Log Format and Output

**Format**: `%(asctime)s | %(levelname)-7s | %(name)-15s | %(message)s`

- `levelname` padded to 7 chars; `name` padded to 15 chars (enforced by `_FixedWidthFormatter`)

**Handlers** (both always active, deduplication is automatic):

- `StreamHandler` → `sys.stdout`
- `FileHandler` → `$DATA_ROOT_FOLDER/logs/logs_<YYYY-MM-DD>.txt`, append mode, UTF-8

`logger.propagate = False` prevents double-writes via the root logger.

### 13.6 Log Level

| Condition | Effective level |
|---|---|
| `ENV=DEV` | `INFO` |
| `ENV` unset / other value | `WARN` |
| `LoggerFactory(log_level="DEBUG")` passed explicitly | `DEBUG` (overrides env) |

Set `ENV=DEV` in your `.env` for development; leave it unset in production to suppress `INFO` noise.

### 13.7 Testing

Inject a standard `logging.Logger` or a mock to capture output without touching the filesystem:

```python
import logging
logger = logging.getLogger("test")
service = MyService(logger=logger)
```

`SBLogger` is `@runtime_checkable`, so `isinstance(logger, SBLogger)` works in assertions.

---

## 14) Historical Data Backfill Entrypoints

Each service file contains an `if __name__ == "__main__"` block that acts as the entrypoint for backfilling historical data. Running the file directly in VS Code (or any Python runner) also enables full debugger support.

| Service | File | Backfill granularity | Key parameter(s) |
|---|---|---|---|
| EOD prices | `src/sbfoundation/eod/eod_service.py` | One trading day at a time, iterates a date range (Mon–Fri) | `eod_date` (ISO 8601 date string) passed to `RunCommand` |
| Annual fundamentals | `src/sbfoundation/annual/annual_service.py` | One fiscal year at a time, iterates a year range | `year` (int) passed to `RunCommand` |
| Quarterly fundamentals | `src/sbfoundation/quarter/quarter_service.py` | One quarter at a time, iterates year × period (Q1–Q4) | `quarter_year` (int) + `quarter_period` (str, e.g. `"Q2"`) passed to `RunCommand` |

**Common pattern** — all three use `concurrent_requests=1` (synchronous, safe for debugging) and pass `enable_bronze=True, enable_silver=True, enable_gold=True`:

```python
# eod_service.py — backfill a date range
_start = date(2026, 3, 13)
_end   = date(2026, 3, 14)

# annual_service.py — backfill multiple fiscal years
for _year in range(2020, 2026): ...

# quarter_service.py — backfill year × quarter combinations
for _year in range(2019, 2026):
    for _period in ("Q1", "Q2", "Q3", "Q4"): ...
```

**Season gates**: `AnnualService` skips runs outside Jan–Mar; `QuarterService` skips outside earnings windows. Both gates are bypassed when `year` / `year+period` are provided explicitly.

To adjust the backfill range, edit the `_start`/`_end` dates or year ranges directly in the `if __name__ == "__main__"` block before running.

---

## 15) What "Done" Looks Like

- Changes compile/type-check (mypy-friendly)
- Formatting consistent with repo standards (Black/isort/flake8)
- No contract violations (DTO purity, Bronze immutability, recipe semantics)
- Silver writes are idempotent via UPSERT with KEY_COLS from keymap
- Where meaningful, include a test fixture or example usage

---

END OF DOCUMENT
