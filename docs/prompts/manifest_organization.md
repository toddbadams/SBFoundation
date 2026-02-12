# Ops Manifest Organization Review

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/AI_context/PLANS.md` from the repository root. Maintain this document in accordance with that file.

## Purpose / Big Picture

After completing this plan, the ops schema will be simpler and aligned to three operational layers so the UI can show Bronze, Silver, and Gold tabs that map directly to ops tables. Promotion tracking will be merged into the Bronze manifest, incremental ingestion dates will live in dataset watermarks, and Gold details will surface through a single, consistent table. All DuckDB-facing logic will be isolated to `src/data_layer/infra/duckdb/duckdb_ops_repo.py` in the data layer and `src/ui/infra/duckdb_ops_repo.py` in the UI. The user-visible outcome is that the UI continues to show run summaries and per-layer details without missing data while the ops schema removes redundant tables.

## Findings

All ops tables created in `db/migrations/20260112_002_create_ops_tables.sql` are referenced in the active codebase, so removals require coordinated schema and code updates. The references live in `src/data_layer/infra/duckdb/duckdb_ops_repo.py`, `src/data_layer/services/ops_service.py`, `src/data_layer/services/bronze/bronze_service.py`, `src/data_layer/services/silver/silver_service.py`, `src/data_layer/services/gold/gold_service.py`, and the UI repo `src/ui/infra/duckdb_ops_repo.py`.

The Run Detail UI now uses three tabs (Bronze, Silver, Gold), so the UI queries must align with the consolidated ops tables and the ops.silver_manifest view.

The incremental ingestion key used by Bronze (`RunRequest.data_date_key`) is derived from dataset identity and ticker, but it is encoded as a hyphenated string, so backfill requires a safe mapping strategy rather than naive string splitting.

## Questions (Resolved)

Question: Do you want to surface ops.gold_manifest in the UI (to justify its existence), or should it be removed in favor of ops.gold_build only? Answer: The Run Detail UI should have Bronze, Silver, and Gold tabs, and the Gold tab should map to the Gold ops table.

Question: Is it acceptable to merge ops.promotion_manifest into ops.bronze_manifest by adding promotion columns, or do you prefer to keep a strict separation between ingestion and promotion tracking? Answer: Merge ops.promotion_manifest into ops.bronze_manifest.

Question: Should ops.data_dates be normalized into ops.dataset_watermarks (if a data_date_key can be mapped to dataset identity), or should it remain a separate key-value store for incremental ingestion? Answer: Normalize ops.data_dates into ops.dataset_watermarks.

Question: Are there any external consumers of the ops tables beyond the UI that would be impacted by table merges or renames? Answer: No, but the data layer producers must be updated: `src/data_layer/services/bronze/bronze_service.py`, `src/data_layer/services/silver/silver_service.py`, and `src/data_layer/services/gold/gold_service.py`.

## Progress

- [x] (2026-01-16 20:20Z) Reviewed ops table usage in data layer and UI code, and mapped each table to a layer.
- [x] (2026-01-16 20:31Z) Captured user decisions on table consolidation, UI tab layout, and producer updates.
- [x] (2026-01-16 20:31Z) Updated ops migrations and code paths to merge promotion tracking into bronze_manifest, move ingestion dates into dataset_watermarks, and switch the UI to Bronze/Silver/Gold tabs.
- [ ] (2026-01-16 20:31Z) Rebuild DuckDB, run a new pipeline cycle, and validate the UI and ops data on fresh data.

## Surprises & Discoveries

- Observation: ops.gold_manifest is written during gold loads but not read by the UI today.
  Evidence: `src/data_layer/services/gold/gold_service.py`, `src/ui/infra/duckdb_ops_repo.py`.

- Observation: ops.data_dates stores a free-form key rather than dataset identity, so a deterministic backfill needs a mapping step.
  Evidence: `src/data_layer/dtos/manifest/run_request.py`, `src/data_layer/services/bronze/bronze_service.py`.

## Decision Log

- Decision: Merge ops.promotion_manifest into ops.bronze_manifest by adding promotion columns and removing the separate promotion table after backfill.
  Rationale: Promotion data is 1:1 with bronze manifest rows, so a single table removes redundancy and simplifies the UI.
  Date/Author: 2026-01-16 / Codex.

- Decision: Normalize ops.data_dates into ops.dataset_watermarks by adding explicit ingestion date columns keyed by dataset identity.
  Rationale: Dataset identity is already stored in dataset watermarks, and keeping ingestion state there removes a parallel key-value table.
  Date/Author: 2026-01-16 / Codex.

- Decision: Use ops.gold_manifest as the Gold tab data source, and keep ops.gold_build for run-level summary metrics.
  Rationale: ops.gold_manifest provides per-table detail, while ops.gold_build is already used for summarizing a run.
  Date/Author: 2026-01-16 / Codex.

- Decision: Introduce an ops.silver_manifest view over ops.bronze_manifest promotion columns to preserve a three-tab UI while keeping bronze_manifest as the single source of truth.
  Rationale: The UI expects three layers; a view provides the silver layer without duplicating storage.
  Date/Author: 2026-01-16 / Codex.

- Decision: Keep ops.file_ingestions as a physical table for now.
  Rationale: It is used heavily in the UI and avoids complex aggregation queries during page loads.
  Date/Author: 2026-01-16 / Codex.

- Decision: Update existing migration files instead of adding new migrations because the platform data will be wiped before changes are applied.
  Rationale: A clean database allows edits to the original migration files without needing forward-only migrations.
  Date/Author: 2026-01-16 / Codex.

## Outcomes & Retrospective

Schema consolidation is implemented in the migration file, data-layer writers now target bronze_manifest promotion columns and dataset_watermarks ingestion dates, and the UI Run Detail page now uses Bronze/Silver/Gold tabs. Validation against a freshly rebuilt DuckDB file is still outstanding.

## Context and Orientation

Ops tables live in the DuckDB ops schema and are created in `db/migrations/20260112_002_create_ops_tables.sql`. The data layer writes ops rows via `src/data_layer/infra/duckdb/duckdb_ops_repo.py` and `src/data_layer/services/ops_service.py`. Bronze ingestion writes ops.bronze_manifest and updates ingestion dates in ops.dataset_watermarks via `src/data_layer/services/bronze/bronze_service.py`. Silver promotion writes promotion columns into ops.bronze_manifest (surfaced through the ops.silver_manifest view) and updates ops.dataset_watermarks in `src/data_layer/services/silver/silver_service.py`. Gold loading writes ops.gold_build and ops.gold_manifest and updates ops.gold_watermarks in `src/data_layer/services/gold/gold_service.py`.

The UI reads ops tables via `src/ui/infra/duckdb_ops_repo.py` and displays run summaries and detail tabs in `src/ui/pages/2_Runs.py`, `src/ui/pages/3_Run_Detail.py`, and dataset watermarks in `src/ui/pages/4_Datasets.py`. Any schema change must preserve these reads or update them in lockstep.

The target layering after consolidation is Bronze: ops.bronze_manifest and ops.dataset_watermarks (including ingestion date fields), Silver: ops.silver_manifest view, and Gold: ops.gold_manifest. Run-level aggregation now comes from `ops.file_ingestions`, while `ops.gold_build` continues to capture per-build metadata.

## Plan of Work

Start by updating the existing migration files under `db/migrations` to reflect the consolidated ops schema, since the platform data will be removed and a clean rebuild will apply the updated migrations. Then add new columns to ops.bronze_manifest to capture promotion status and metrics, and add ingestion tracking columns to ops.dataset_watermarks. Add an ops.silver_manifest view that exposes only rows with promotion data, shaped similarly to the old promotion_manifest so the UI can present a Silver tab without extra storage.

Because the DuckDB file will be rebuilt from scratch, no backfill is required for the consolidated schema. If you must migrate an existing database, backfill promotion columns by joining ops.promotion_manifest on bronze_file_id; ingestion date backfill should be skipped unless you can provide a safe mapping for data_date_key values.

Then update data layer producers. Modify `DuckDbOpsRepo` and `OpsService` to write promotion status directly into ops.bronze_manifest and to read/write ingestion dates from ops.dataset_watermarks using dataset identity rather than data_date_key. Update Bronze ingestion to call the new ingestion-date methods. Update Silver promotion to call the new promotion status updates. Keep Gold loading behavior unchanged except for any UI-driven adjustments to ops.gold_manifest usage.

Finally, update the UI. Replace promotion_manifest queries with ops.silver_manifest view queries. Collapse the Run Detail page into three tabs (Bronze, Silver, Gold) and wire them to ops.bronze_manifest, ops.silver_manifest, and ops.gold_manifest respectively. Remove the Data Dates and Gold Watermarks tabs if the data is now visible in the Bronze or Gold tabs, and ensure the Datasets page includes the ingestion date fields from ops.dataset_watermarks.

Once the new flow is validated, remove ops.promotion_manifest and ops.data_dates from the existing migration files so fresh environments do not create them.

## Tasks

Task 1 is to update the existing ops migration files to reflect the new schema, then add promotion columns to ops.bronze_manifest, add ingestion date columns to ops.dataset_watermarks, and create the ops.silver_manifest view.

Task 2 is optional for legacy databases: backfill promotion data into bronze_manifest and document any ingestion-date gaps caused by ambiguous data_date_key values.

Task 3 is to update `data_layer` writers and readers to use the merged schema, including `bronze_service.py`, `silver_service.py`, and `duckdb_ops_repo.py`.

Task 4 is to update the UI to show Bronze, Silver, and Gold tabs and to query the new tables or view.

Task 5 is to remove or deprecate ops.promotion_manifest and ops.data_dates after validation passes.

## Concrete Steps

Work in `c:/strawberry`. Use search to confirm references before changing schema or code.

    PS C:\sb\SBFoundation> rg -n "ops\\.file_ingestions|bronze_manifest|promotion_manifest|dataset_watermarks|data_dates|gold_build|gold_manifest|gold_watermarks" src

When you update the existing migrations, rebuild the DuckDB file so the new schema is applied from scratch.

    PS C:\sb\SBFoundation> python -m data_layer.infra.duckdb.duckdb_migration_service

If you need to migrate an existing database, run any backfill steps after migrations and before validating the UI, and keep a log of skipped keys.

## Validation and Acceptance

A successful consolidation keeps the pipeline operational and the UI stable. Run the orchestrator to produce a new run summary, then open the UI and confirm that the Runs page lists the new run, the Run Detail page shows Bronze, Silver, and Gold tabs with data, and the Datasets page still renders without errors and includes the ingestion date columns.

Acceptance checks include: promotion status and counts appear in the Silver tab for rows that were promoted, ingestion date tracking persists across runs, and Gold table statuses appear in the Gold tab. If any tab is empty for a run that should have data, verify the new queries and backfill step.

## Idempotence and Recovery

Schema changes should be additive first. Update the existing migrations, rebuild the DuckDB file, and then update writers and readers to match. If a rebuild fails, fix the migration file and recreate the database. Keep a backup of the DuckDB file before destructive changes even if you intend to wipe it.

## Artifacts and Notes

Key usage references: `db/migrations/20260112_002_create_ops_tables.sql`, `src/data_layer/infra/duckdb/duckdb_ops_repo.py`, `src/data_layer/services/ops_service.py`, `src/data_layer/services/bronze/bronze_service.py`, `src/data_layer/services/silver/silver_service.py`, `src/data_layer/services/gold/gold_service.py`, `src/ui/infra/duckdb_ops_repo.py`, `src/ui/pages/3_Run_Detail.py`, `src/ui/pages/4_Datasets.py`.

## Interfaces and Dependencies

Any schema change must update both ops repositories: `data_layer.infra.duckdb.duckdb_ops_repo.DuckDbOpsRepo` for writes and `ui.infra.duckdb_ops_repo.DuckDbOpsRepo` for reads. The OpsService interface in `src/data_layer/services/ops_service.py` is the only writer used by higher-level services, so prefer changing its internals rather than its public method names. The UI depends on `src/ui/services/ops_data.py` and expects the column sets defined in `src/ui/ui_settings.py`, so column changes must be coordinated there as well.

Change Note: Updated the ExecPlan to reflect completed schema/UI changes, the optional backfill stance after a data wipe, and the remaining validation step.
