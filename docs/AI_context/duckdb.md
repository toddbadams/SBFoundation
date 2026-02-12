# Strawberry AI Context: Transition Structured Storage from Parquet to DuckDB

## Problem statement

Strawberry uses a Bronze → Silver → Gold medallion architecture. Today, structured data is persisted as Parquet datasets. We are transitioning structured storage to DuckDB while preserving replayability, auditability, lineage, incremental ingestion/watermarks, and existing RunProvider/DatasetRecipe semantics.

## Goals

1. Bronze remains immutable raw JSON files on disk (system of record).
2. DuckDB becomes the canonical store for all structured data (Silver + Gold) plus manifests, watermarks, and operational metadata.
3. End-to-end lineage is guaranteed: Bronze file → Silver row(s) → Gold build(s).
4. Incremental ingestion is controlled by dataset watermarks; Gold builds reference watermarks.
5. The medallion responsibilities remain:
   - Bronze = raw, immutable, append-only files.
   - Silver = typed/validated/conformed copies, mostly denormalized.
   - Gold = warehouse modeling (dims/facts, curated analytics).

## Decisions (authoritative)

1. Single DuckDB file for both dev and prod, stored at a config-driven location. It must be copyable from prod (Raspberry Pi) to dev (Windows).
2. All file paths stored in manifests are repo-root-relative so they work on both machines. Code resolves relative paths using a configured `repo_root_path`.
3. Silver rows must carry `bronze_file_id` (row-level lineage).
4. Silver writes are idempotent via UPSERT/MERGE, using a formal key mapping per dataset/table.
5. One dataset maps to exactly one Silver table (for now).
6. Watermarks and dates:
   - Bronze watermarks may require a date range (from/to) reflecting coverage.
   - Silver rows must include a per-row date where the DTO property `date_key` identifies the date field. When there is no dataset date field, the row must use `as_of_date`.
7. Gold builds reference watermarks as inputs, and transformations are versioned by git SHA.
8. DuckDB LIST types are used for arrays (inputs, row_counts, etc.). For `ops.gold_build.input_watermarks`, use `LIST<VARCHAR>`.
9. No concurrency: ingestion/promotions/builds run in a single process (single-writer).
10. Schemas are initialized dynamically on first connection using CREATE IF NOT EXISTS. The schema is stable and changes are rare.
11. The formal key mapping is stored in YAML.

## Non-goals

- Do not redesign business logic, scoring, or strategy behavior.
- Do not store Bronze payload bodies inside DuckDB as canonical.
- Do not introduce parallel writers or new orchestration layers.

## Configuration

Provide config values (via env/config file) for:
- `DUCKDB_FOLDER`: location of the DuckDB file (dev/prod differs).
- `repo_root_path`: absolute path to repo root (dev/prod differs).
- `BRONZE_FOLDER`: repo-relative base folder for bronze files (e.g., `data/bronze`).
- `MIGRATIONS_FOLDER`: repo-relative folder containing SQL migration files (e.g., `db/migrations`).
- `DATASET_KEYMAP_FOLDER`: repo-relative path to the YAML key map file.

All persisted file paths in DuckDB are repo-relative. Runtime resolves:
`absolute_path = repo_root_path / file_path_rel`

## Canonical storage model

### Bronze (filesystem)

- Each request/response result is saved as a JSON file at a repo-relative path.
- Bronze files are append-only and immutable; never rewrite them.
- DuckDB stores metadata and references to these files, not the payload as canonical storage.

### DuckDB

DuckDB stores:
- Bronze manifest rows referencing each Bronze JSON file.
- Silver tables with validated structured data.
- Gold dims/facts and curated outputs.
- Gold build manifests (inputs via watermarks, model_version via git SHA).
- Dataset watermarks for incremental gating.
- Schema migrations history.

## Dataset identity (canonical)

Dataset identity is used for manifests and watermarks. It consists of:
- `domain`
- `source`
- `dataset`
- `discriminator` (optional; empty string if unused)
- `ticker` (optional; empty string if unused)

Date is not part of the dataset identity. Dates apply to:
- Bronze: coverage ranges (`coverage_from_date`, `coverage_to_date`)
- Silver: per-row date field determined by DTO `date_key`; if no date field exists, use `as_of_date`.

This identity keys:
- ops.bronze_manifest rows (plus a specific file path)
- ops.dataset_watermarks rows
- ops.gold_build input watermark references (serialized)

## Formal key mapping (required)

Maintain an explicit mapping of dataset → Silver table name → KEY_COLS for idempotent UPSERT.

This mapping must be authoritative and machine-readable as YAML (config-driven path). It must include:
- dataset identity fields (domain/source/dataset + optional discriminator and ticker scope)
- `silver_schema` and `silver_table`
- `key_cols: list[str]`
- optional `row_date_col` (e.g., `date`, `as_of_date`) when applicable

No dataset may be promoted to Silver until its key mapping exists.

### YAML shape (authoritative)

File: `DATASET_KEYMAP_FOLDER`  
Repo-relative path (authoritative): `config/dataset_keymap.yaml`

```yaml
version: 1
datasets:
  - domain: fundamentals
    source: fmp
    dataset: income_statement
    discriminator: ""           # optional, default ""
    ticker_scope: "per_ticker"  # one of: per_ticker | global
    silver_schema: silver
    silver_table: fmp_income_statement
    key_cols:
      - symbol
      - date
      - period
    row_date_col: date          # optional
````

Notes:

* `ticker` itself is not stored in the mapping; it’s provided at runtime where applicable.
* `ticker_scope: per_ticker` means the ingestion identity includes a ticker value at runtime.
* `ticker_scope: global` means ticker is empty for identity purposes.

## Lineage and idempotency

### Lineage (row-level)

Every Silver table row MUST include:

* `bronze_file_id` (FK to ops.bronze_manifest)
* `run_id`
* `ingested_at`

Every Silver table row MUST include a row date column:

* If the DTO defines `date_key`, use that field as the row date column.
* If there is no dataset date field, use `as_of_date`.

### Idempotency (UPSERT)

Silver writes MUST be idempotent:

* Use DuckDB MERGE (or equivalent) keyed by the dataset’s KEY_COLS from the YAML key mapping.
* Reprocessing the same Bronze file must not duplicate Silver rows.

If upstream data changes, UPSERT updates non-key columns deterministically.

## Watermarks

### Watermark record semantics

Watermarks are stored per dataset identity.

Coverage watermarks track the data coverage window for the most recent successful ingestion:

* `coverage_from_date`, `coverage_to_date` (nullable where not applicable)

Also store:

* `last_success_at` (timestamp)
* `last_run_id` (nullable)
* `last_bronze_file_id` (nullable)

Gold builds use dataset watermarks as inputs.

## DuckDB schema layout

Use schemas:

* `ops` for manifests/watermarks/migrations/run summaries
* `silver` for conformed datasets
* `gold` for warehouse tables

### ops.schema_migrations

Tracks applied migrations.

Columns:

* `version` (PK, timestamped sortable string, e.g., `20260112_001`)
* `name` (string)
* `applied_at` (timestamp)
* `checksum` (string)

Migration runner behavior:

* reads migrations from `MIGRATIONS_FOLDER`
* sorts by `version`
* applies in order
* records each applied migration transactionally

### ops.bronze_manifest

One row per Bronze JSON file.

Columns (minimum):

* `bronze_file_id` (PK, generated)
* `run_id`
* `domain`, `source`, `dataset`, `discriminator`, `ticker`
* `request_ts`, `response_ts`, `ingested_at`
* `status_code`
* `error_message` (nullable)
* `file_path_rel` (repo-relative)
* `payload_hash`
* `coverage_from_date` (nullable)
* `coverage_to_date` (nullable)
* `content_length_bytes` (nullable)
* `is_promotable` (boolean)

### ops.dataset_watermarks

Composite PK on dataset identity.

Columns:

* `domain`, `source`, `dataset`, `discriminator`, `ticker`
* `coverage_from_date` (nullable)
* `coverage_to_date` (nullable)
* `last_success_at` (timestamp)
* `last_run_id` (nullable)
* `last_bronze_file_id` (nullable)
* `notes` (nullable)

### ops.gold_build

One row per Gold build.

Columns:

* `gold_build_id` (PK)
* `run_id`
* `model_version` (git SHA)
* `started_at`, `finished_at`
* `status`, `error_message` (nullable)
* `input_watermarks` (LIST<VARCHAR>)   # serialized dataset-identity watermark keys
* `tables_built` (LIST<VARCHAR>)
* `row_counts` (LIST<STRUCT<table_name VARCHAR, row_count BIGINT>>)

#### input_watermarks serialization (authoritative)

Each element of `input_watermarks` is a stable string:

`domain|source|dataset|discriminator|ticker@coverage_from=YYYY-MM-DD;coverage_to=YYYY-MM-DD`

Rules:

* `discriminator` and `ticker` are empty strings when not used, but separators remain.
* coverage_from/to may be blank if not applicable:
  `...@coverage_from=;coverage_to=`

### ops.file_ingestions (required)

Captures every bronze/silver/gold step so run-level metrics can be derived without a separate summary table.

Columns:

* `run_id`, `file_id`
* bronze metadata: coverage range, payload hash, rows, timestamps, errors, promotion flag
* silver metadata: table name, coverage, row counts, errors, watermark/ingestion timestamps
* gold metadata: object type, table, row counts, errors, coverage, timestamps, throttle status

## Silver tables

* Each dataset has one table in `silver`.
* Tables are typed and validated copies of Bronze payload data.
* Required columns in every silver table:

  * `bronze_file_id`, `run_id`, `ingested_at`
* Required row date column:

  * dataset row date column per keymap `row_date_col` when present; otherwise `as_of_date`.

## Gold tables

* Star-schema modeling allowed (dims/facts).
* Each Gold table includes:

  * `gold_build_id`
  * `model_version` (git SHA)
  * optionally snapshot/as-of date fields

Gold outputs must be reproducible given:

* the referenced input watermarks
* the git SHA model version

## Operational rules

### Transactions

* Bronze: write file first, then insert manifest row. If manifest insert fails, surface an actionable error and leave file for replay.
* Silver promotion: MERGE/UPSERT + watermark updates must be in one DuckDB transaction.
* Gold build: write gold tables + ops.gold_build record must be in one DuckDB transaction.

### Reprocessing

* Reprocessing is supported by selecting Bronze files (by identity/date/run_id) and re-running promotions/builds.
* Reprocessing must not create duplicates due to UPSERT semantics.
* Watermarks prevent “too-soon” ingestion and enable incremental windows.

## Codex deliverables (what to generate)

1. DuckDB migration system:

   * ops.schema_migrations table
   * migration runner (Python) to apply SQL migrations by version + checksum
2. Initial migrations:

   * schemas: ops/silver/gold
   * ops tables: schema_migrations, bronze_manifest, dataset_watermarks, gold_build, file_ingestions
3. Config-driven DB bootstrap:

   * open/create DuckDB file at `DUCKDB_FOLDER`
   * apply migrations on startup
4. Bronze manifest writer:

   * persist JSON file to repo-relative path
   * insert ops.bronze_manifest row with file_path_rel, payload_hash, coverage dates
5. YAML key map loader + validator:

   * loads mappings from `config/dataset_keymap.yaml`
   * enforces that Silver promotion requires a mapping
6. Silver promotion pipeline:

   * reads promotable ops.bronze_manifest rows
   * transforms to DTO rows
   * MERGE/UPSERT into the dataset’s silver table using YAML KEY_COLS
   * ensures required row date column exists (DTO `date_key` else `as_of_date`)
   * updates ops.dataset_watermarks on success
7. Gold build pipeline:

   * reads ops.dataset_watermarks as inputs
   * builds dims/facts
   * records ops.gold_build with:

     * model_version = git SHA
     * input_watermarks = LIST<VARCHAR> using the authoritative serialization
8. Tests:

   * migration runner correctness
   * bronze manifest path resolution (repo-relative, config root)
   * silver UPSERT idempotency using keymap KEY_COLS
   * lineage correctness (bronze_file_id exists on all silver rows)
   * gold build records reference watermarks + git SHA

## Acceptance criteria (definition of done)

1. A Bronze ingestion creates:

   * a JSON file on disk (repo-relative path)
   * a row in ops.bronze_manifest referencing that path
2. Silver promotion creates:

   * validated rows in the correct silver table
   * no duplicates on replay
   * bronze_file_id present on all promoted rows
   * required row date column populated (DTO `date_key` else `as_of_date`)
   * ops.dataset_watermarks updated with coverage range for the dataset identity
3. Gold build creates:

   * dims/facts in gold schema
   * ops.gold_build record with git SHA model_version and watermarks as inputs
4. Copying the DuckDB file from prod to dev works without changes:

   * because all file references are repo-root-relative and resolved via config.

