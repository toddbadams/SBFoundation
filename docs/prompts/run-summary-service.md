# Consolidate Ops Repositories and Introduce OpsService

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

PLANS.md is checked into this repo at `docs/AI_context/PLANS.md`. Maintain this ExecPlan in accordance with that file.

## Purpose / Big Picture

The goal is to unify all DuckDB ops writes behind a single repository and service so that operational metadata (bronze manifests, silver promotion manifests, gold manifests, watermarks, and run summaries) flows through one consistent interface. After this change, a developer can run the orchestrator and see all ops tables updated through `OpsService`, while Bronze payloads are still written to disk by a dedicated file writer that is not part of the ops layer. Success is visible by running the orchestrator and querying the ops tables to confirm that the run summary and manifest tables are populated.

## Progress

- [x] (2026-01-16T10:41Z) Converted the prompt into a self-contained ExecPlan that reflects the answered questions.
- [x] (2026-01-16T11:07Z) Implement `DuckDbOpsRepo` and remove the legacy ops classes.
- [x] (2026-01-16T11:07Z) Add `BronzeFileWriter`, `OpsService`, and rewire Bronze/Silver/Gold services and the orchestrator.
- [ ] (2026-01-16T10:41Z) Validate behavior using orchestrator + DuckDB SQL checks.

## Surprises & Discoveries

No surprises yet. Update this section with any unexpected behaviors or failures observed during implementation, including evidence snippets.

## Decision Log

The following decisions are already made and must be followed.

- Decision: Remove all filesystem write logic from ops classes and move Bronze payload writes to a dedicated `BronzeFileWriter`.
  Rationale: Ops should only manage DuckDB state; Bronze files remain a separate concern.
  Date/Author: 2026-01-16 / Codex (from prompt answers)
- Decision: Inject `OpsService` into Bronze, Silver, and Gold services and keep ops writes inside those services via the facade.
  Rationale: Per-row ops updates must happen where the work occurs, not only at run close.
  Date/Author: 2026-01-16 / Codex (from prompt answers)
- Decision: Replace the legacy ops classes entirely with `DuckDbOpsRepo`, and use a shared `DuckDbBootstrap` inside it.
  Rationale: Simplifies ownership and ensures a single ops connection path.
  Date/Author: 2026-01-16 / Codex (from prompt answers)
- Decision: `OpsService.start_run()` returns a `RunContext` built with a `UniverseService`; `finish_run()` closes out and persists the summary.
  Rationale: Orchestrator should not hand-build run summaries anymore.
  Date/Author: 2026-01-16 / Codex (from prompt answers)

## Outcomes & Retrospective

No implementation outcomes yet. When a milestone completes, summarize what changed, what remains, and any lessons learned.

## Context and Orientation

This repo uses a Bronze -> Silver -> Gold pipeline. Bronze writes raw payload JSON files and logs manifest metadata to `ops.bronze_manifest`. Silver promotion reads promotable Bronze rows and writes to DuckDB silver tables, while recording promotion metadata in ops tables. Gold builds dims and facts in DuckDB and records manifest and build metadata in ops tables. The orchestrator now creates a `RunContext` via `OpsService`, and ops writes flow through `DuckDbOpsRepo` and the `OpsService` facade. The legacy ops classes referenced below have been removed and replaced by `C:\sb\SBFoundation\src\data_layer\infra\duckdb\duckdb_ops_repo.py`, `C:\sb\SBFoundation\src\data_layer\services\ops_service.py`, and `C:\sb\SBFoundation\src\data_layer\infra\bronze_file_writer.py`. For historical context, these were the previous classes:

`C:\sb\SBFoundation\src\data_layer\infra\bronze_manifest_service.py` (writes files and inserts ops.bronze_manifest),
`C:\sb\SBFoundation\src\data_layer\infra\duckdb\duckdb_data_dates_repo.py`,
`C:\sb\SBFoundation\src\data_layer\infra\duckdb\duckdb_gold_ops_repo.py`,
and `C:\sb\SBFoundation\src\data_layer\infra\duckdb\duckdb_silver_promotion_ops_repo.py`.

The target design replaces those with `DuckDbOpsRepo` at `src/data_layer/infra/duckdb/duckdb_ops_repo.py`, introduces `OpsService` as the facade used by the Bronze/Silver/Gold services, and adds `BronzeFileWriter` (outside ops) to persist Bronze payloads.

Definitions used in this plan:
Ops tables are DuckDB tables under the `ops` schema that store metadata such as manifests, watermarks, and run summaries. Bronze payloads are raw JSON files written to disk under the bronze folder path configured by `DuckDbConfig`.

## Plan of Work

The ops stack now aggregates run metadata through `RunContext` entries persisted to `ops.file_ingestions`. Keep reinforcing that flow:

1. Confirm `DuckDbOpsRepo` continues to write merge rows into `ops.file_ingestions` at every bronze/silver/gold transition so downstream tiles can query the single source of truth.
2. Keep the UI/table builders focused on `ops.file_ingestions` for run overviews and the bronze/silver/gold tabs, and retire any helper code or docs that expect `RunSummary` or the old JSON files.
3. Run the orchestrator end to end to produce a `RunContext`, then verify via SQL that the run_id, timestamps, and counters show up inside `ops.file_ingestions`.

## Concrete Steps

For validation, run the orchestrator and query the consolidated table:

    python data_layer/orchestrator.py

    SELECT run_id, started_at, finished_at, status
    FROM ops.file_ingestions
    ORDER BY started_at DESC
    LIMIT 5;

    SELECT run_id, COUNT(*) AS bronze_files
    FROM ops.file_ingestions
    WHERE bronze_rows IS NOT NULL
    GROUP BY run_id
    ORDER BY bronze_files DESC;

## Validation and Acceptance

Validation must prove that ops writes still happen and that the orchestrator uses `OpsService`.

Run the orchestrator with a small ticker limit and then query DuckDB ops tables. For example, from `C:\sb\SBFoundation\src`, run:

    python data_layer/orchestrator.py

Then query DuckDB using the CLI or a Python snippet. If using the DuckDB CLI from `C:\sb\SBFoundation`, connect to the configured DuckDB file and run:

    SELECT run_id, started_at, finished_at, status
    FROM ops.file_ingestions
    ORDER BY started_at DESC
    LIMIT 5;

    SELECT run_id, COUNT(*) AS bronze_files
    FROM ops.bronze_manifest
    GROUP BY run_id
    ORDER BY bronze_files DESC;

    SELECT status, COUNT(*) AS count
    FROM ops.promotion_manifest
    GROUP BY status;

    SELECT status, COUNT(*) AS count
    FROM ops.gold_manifest
    GROUP BY status;

Acceptance is met when a run produces a new `ops.file_ingestions` row, at least one `ops.bronze_manifest` row for that run, and non-empty results for the promotion and gold manifest counts when those steps are enabled.

## Idempotence and Recovery

All changes should be safe to apply multiple times as long as you update imports consistently. If a step fails, revert to the last known-good state using version control (for example, `git restore <file>` from `C:\sb\SBFoundation`) and re-apply the step. The ops tables are written using MERGE/UPSERT semantics, so re-running the orchestrator should update rather than duplicate run summary rows.

## Artifacts and Notes

Use these short artifacts as reference when validating:

    Example log lines after orchestrator run:
      Injestion complete. run_id=... | elapsed_seconds=...
      Orchestration complete. Elapsed time: ...

    Example SQL output shape:
      run_id | started_at | finished_at | status
      ------ | ---------- | ----------- | -------

## Interfaces and Dependencies

Define the following interfaces and keep the signatures stable:

In `C:\sb\SBFoundation\src\data_layer\infra\duckdb\duckdb_ops_repo.py`, define:

    class DuckDbOpsRepo:
        def __init__(self, config: DuckDbConfig | None = None, logger: logging.Logger | None = None, bootstrap: DuckDbBootstrap | None = None) -> None
        def close(self) -> None
        def insert_bronze_manifest(self, *, result: RunResult, rel_path: Path, payload_hash: str, content_length_bytes: int) -> None
        def get_data_date(self, key: str) -> date | None
        def upsert_data_date(self, *, key: str, to_date: date) -> None
        def load_promotable_rows(self) -> list[BronzeManifestRow]
        def start_promotion_manifest(self, row: BronzeManifestRow) -> None
        def finish_promotion_manifest(self, row: BronzeManifestRow, *, status: str, rows_seen: int, rows_written: int, error: str | None) -> None
        def get_watermark(self, conn: duckdb.DuckDBPyConnection, row: BronzeManifestRow, entry: DatasetKeymapEntry) -> date | None
        def upsert_watermark(self, conn: duckdb.DuckDBPyConnection, row: BronzeManifestRow, entry: DatasetKeymapEntry, *, coverage_from: date | None, coverage_to: date | None) -> None
        def start_gold_manifest(self, conn: duckdb.DuckDBPyConnection, *, gold_build_id: int, table_name: str) -> None
        def finish_gold_manifest(self, conn: duckdb.DuckDBPyConnection, *, gold_build_id: int, table_name: str, status: str, rows_seen: int, rows_written: int, error_message: str | None) -> None
        def get_gold_watermark(self, conn: duckdb.DuckDBPyConnection, *, table_name: str) -> date | None
        def upsert_gold_watermark(self, conn: duckdb.DuckDBPyConnection, *, table_name: str, watermark_date: date | None) -> None

In `C:\sb\SBFoundation\src\data_layer\infra\bronze_file_writer.py`, define:

    class BronzeFileWriter:
        def __init__(self, config: DuckDbConfig | None = None, logger: logging.Logger | None = None) -> None
        def write(self, result: RunResult) -> tuple[Path, str, int]

In `C:\sb\SBFoundation\src\data_layer\services\ops_service.py`, define:

    class OpsService:
        def __init__(self, ops_repo: DuckDbOpsRepo | None = None, universe: UniverseService | None = None, logger: logging.Logger | None = None) -> None
        def start_run(self, *, ticker_limit: int) -> RunContext
        def finish_run(self, summary: RunContext) -> None
        def close(self) -> None
        def insert_bronze_manifest(self, *, result: RunResult, rel_path: Path, payload_hash: str, content_length_bytes: int) -> None
        def get_data_date(self, key: str) -> date | None
        def upsert_data_date(self, *, key: str, to_date: date) -> None
        def load_promotable_rows(self) -> list[BronzeManifestRow]
        def start_promotion_manifest(self, row: BronzeManifestRow) -> None
        def finish_promotion_manifest(self, row: BronzeManifestRow, *, status: str, rows_seen: int, rows_written: int, error: str | None) -> None
        def get_watermark(self, conn: duckdb.DuckDBPyConnection, row: BronzeManifestRow, entry: DatasetKeymapEntry) -> date | None
        def upsert_watermark(self, conn: duckdb.DuckDBPyConnection, row: BronzeManifestRow, entry: DatasetKeymapEntry, *, coverage_from: date | None, coverage_to: date | None) -> None
        def start_gold_manifest(self, conn: duckdb.DuckDBPyConnection, *, gold_build_id: int, table_name: str) -> None
        def finish_gold_manifest(self, conn: duckdb.DuckDBPyConnection, *, gold_build_id: int, table_name: str, status: str, rows_seen: int, rows_written: int, error_message: str | None) -> None
        def get_gold_watermark(self, conn: duckdb.DuckDBPyConnection, *, table_name: str) -> date | None
        def upsert_gold_watermark(self, conn: duckdb.DuckDBPyConnection, *, table_name: str, watermark_date: date | None) -> None

Change Note: 2026-01-16T10:41Z Updated `docs/prompts/run-summary-service.md` into a full ExecPlan aligned with `docs/AI_context/PLANS.md`, including detailed steps, interfaces, and validation guidance.
Change Note: 2026-01-16T11:07Z Updated the Progress section after implementing the ops repo, ops service, bronze file writer, and service rewiring.
Change Note: 2026-01-16T11:09Z Updated Context and Plan of Work to reflect that implementation is complete and only validation remains.
Change Note: 2026-01-16T11:10Z Updated Concrete Steps to reflect that implementation is complete and validation commands remain.
