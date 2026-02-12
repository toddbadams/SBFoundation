# Ops ExecPlan

## Goal
- Replace the many ops tables and DTOs (run summary, bronze manifest, promotion/gold manifests, dataset watermarks) with a **single DuckDB table** that captures the full lifecycle of each file using the schema outlined in `src/data_layer/ops/dtos/file_injestion.py`.
- Ensure **all data translations and DTO mutation logic live inside `DatasetInjestion`** (`file_injestion.py`) so the service layer simply fills its fields and persists the object in one place.
- Keep the rest of the stack (orchestrator, bronze/silver/gold services, UI) working by wiring all operational metadata writes/reads through this consolidated table, then remove the redundant models and repositories (`RunContext`, `RunContextRow`, etc.).

## Current pain points
1. `ops.file_ingestions`, `ops.bronze_manifest`, `ops.dataset_watermarks`, `ops.gold_build`, `ops.gold_manifest`, and `ops.gold_watermarks` are duplicated in both the data and UI layers. Each table has its own DTO/repo/service wiring, and the orchestration flow has to juggle multiple lookups/updates when promoting files.
2. `RunContext` is used as a global status accumulator in `src/data_layer/ops/services/ops_service.py`, the orchestrator, tests, and the UI; removing it will require a new approach to tracking run state and surfacing run-level metrics.

## Single-table schema (draft)
Use `file_injestion.py` as the source of truth for the new table so we capture every column needed for the bronze → gold path:

| Column | Purpose |
| --- | --- |
| `run_id` (`TEXT`) and `file_id` (`TEXT`) | identify the run and the persisted payload. |
| `domain`, `source`, `dataset`, `discriminator`, `ticker` | recipe metadata plus deterministic partition keys. |
| Bronze columns: `bronze_rows`, `bronze_error`, `bronze_filename`, `bronze_from_date`, `bronze_to_date`, `bronze_injest_start_time`, `bronze_injest_end_time`, `bronze_can_promote`. |
| Silver columns: analogously named columns from the DTO (`silver_rows_created`, `silver_rows_updated`, `silver_injest_start_time`, etc.). |
| Gold columns: `gold_object_type`, `gold_tablename`, `gold_errors`, `gold_rows_created`, etc. |
| Add `timestamp` columns for each stage that can be used to derive run-level durations (`bronze_injest_start_time`, `silver_injest_finish_time`, etc.). |
| Additional helper columns such as `status` or `promoted_to` can be derived as needed from boolean flags or success vs. error strings.

The table will live in the `ops` schema (e.g., `ops.file_ingestions`). The primary key could be `(run_id, file_id)` or a dedicated surrogate if file IDs are not unique.

## Execution steps
1. **Schema/migrations**
   - Create a new migration that drops the existing ops tables (except any bootstrap tables we still need) and creates `ops.file_ingestions`.
   - Use the `file_injestion` column names as a checklist for the new schema, including column types and nullability/ defaults.
   - Capture any existing constraints (e.g., sequences for bronze/gold IDs) in comments until we decide whether they are still needed.

2. **Data-layer rewiring**
   - Replace `DuckDbOpsRepo` and `OpsService` with a lightweight repo/service that writes to `ops.file_ingestions` for every stage (bronze ingestion, silver/gold promotion) and removes dataset watermark or manifest-specific methods.
   - Have bronze ingestion call a single method such as `ops_service.record_file_ingestion(summary: DatasetInjestion)` instead of the current mix of manifest inserts and watermark updates.
   - Ensure the same service accumulates whatever run-level counts are still required (or recompute them on-demand by aggregating the new table).
   - Drop `RunContext`, `bronze_injest_item`, `silver_injest_item`, `gold_injest_item`, and any other DTOs/models that only exist to back the removed tables.
   - All data translation/aggregation logic (e.g., deriving bronze/silver/gold start/finish times, error status, promotion flags) should happen via helper methods on `DatasetInjestion` before the object is persisted.

3. **Orchestrator and pipeline updates**
   - Update `src/data_layer/orchestrator.py` so it no longer relies on `RunContext`; it may still need a lightweight run context, but all persistence should happen via the new table.
   - Refactor `BronzeService`, `SilverService`, and `GoldService` to call the single ops service with the updated DTO (likely a runtime view of `file_injestion` that gets filled as each stage runs).
   - Capture stage-level times/errors directly on that DTO and persist them after each stage completes.
   - Ensure every ops call inside those services is routed through `OpsService`, so the Bronze/Silver/Gold layers never talk to DuckDB directly.

4. **UI and supporting layers**
   - Rewrite `src/ui/infra/duckdb_ops_repo.py` and `src/ui/models/ops_models.py` (plus any UI settings referencing the old columns) so they read from `ops.file_ingestions`.
   - The runs calendar/table should aggregate per-run data (e.g., bronze counts, statuses) via SQL grouped by `run_id` (a `SELECT run_id, MAX(...)` style query).
   - Run Detail should pull all file-level rows for a given `run_id` and render bronze/silver/gold metadata columns in place of the manifest tables.
   - Remove `RunContextRow` and the table-specific row dataclasses now that there is just one source of ops truth.
   - Keep **all DuckDB-facing logic inside `src/ui/infra/duckdb_ops_repo.py`**, following repository best practices (single responsibility, parameterized queries, explicit pagination/filters) so that the UI layer doesn't repeat SQL.

5. **Testing and validation**
   - Update `tests/test_orchestrator.py` (and any other tests referencing `RunContext`) to align with the new data flow.
   - Add new tests that exercise the new ops repo/service contract (for example: when bronze run succeeds, a row with bronze timestamps is inserted).
   - Run existing suite (`poetry run pytest tests/test_orchestrator.py`, etc.) or targeted tests that touch the orchestrator/UI to confirm nothing breaks.

6. **Documentation and follow-up**
   - Update docs under `docs/prompts/` and `docs/AI_context/` (any references to the old ops tables) so that future readers know about the consolidated design.
   - Once the new table and flow are in place, retire the legacy JSON summary paths, if they still exist.

## Open questions
1. Should the new table still store dataset watermark information (formerly in `ops.dataset_watermarks`) needed to decide future `from_date` values, or is there another canonical source?

   Decide future dates using the `DatasetInjestion` class and `bronze_to_date` property.  It is this to date that computes the next from date.

2. Do we still need a concept of run-level summary metrics (bronze file counts, gold builds) for the UI, or can these be computed on-demand from `ops.file_ingestions` (for example, `COUNT(*) FILTER (WHERE bronze_can_promote)`)? If a summary table is required, should it be derived via a view?

   For the UI concerns create a repostiory method that creates the summary on-demand given a run_id.

3. What level of backward compatibility is required for existing DuckDB files/Streamlit dashboards? Should the migration drop the old tables in-place or keep them around during a transition phase?

   There is no need for backward compatibility.

This draft ExecPlan outlines the major structural changes. Let me know which assumptions should be adjusted before I make implementation changes or drop the legacy schemas.
