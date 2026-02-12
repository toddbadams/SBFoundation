# ExecPlan: Resolve orchestrator warnings from 2026-01-28 run

This ExecPlan addresses the warnings/errors that appear when running `src/data_layer/orchestrator.py` as logged on 2026-01-28 09:25–09:27. The dominant issues are: Bronze row persistence failing (“boom”), bronze requests rejected as “REQUEST IS TOO SOON”, invalid recipe definitions, and the repeated `OpsService` warnings (“No ingestions found for gold start/finish”). When followed, the plan ensures each dataset has a corresponding `ops.file_ingestions` row before gold jobs start, gold metadata is written without 43+ warnings, and the system gracefully surfaces the real causes (and fixes) of the warnings.

## Purpose / Big Picture

After executing this plan, orchestrator runs will finish without the flood of `OpsService` warnings, and the accompanying log will show gold builds binding to their bronze/silver ingestions. Bronze persistence failures will be recoverable or surfaced clearly, `RunRequest` will enforce timing properly, and the gold stage will only start for datasets that actually have harvested bronze rows. This makes the log readable, increases confidence in gold ingestion coverage, and keeps downstream dashboards (UI, ops tables) honest.

## Progress

- [x] (2026-01-29 00:00Z) Captured the log snippet showing missing ingestions for gold start/finish plus bronze/silver warnings.
- [ ] Confirm whether `ops.file_ingestions` rows exist per dataset after bronze and silver runs currently performed by the orchestrator.
- [ ] Implement repo/service helpers that let gold components load or create ingestion rows by dataset identity and persist gold metadata safely.
- [ ] Adjust bronze/silver starting points so every dataset the gold loader registers (dims and facts) has an entry before `start_gold_ingestion` runs.
- [ ] Add targeted unit/integration tests to prove the new helpers work and rerun affected test suites.

## Surprises & Discoveries

- Observation: `OpsService` repeatedly logs “No ingestions found for gold start/finish” for every dataset the gold loader registers. Evidence: log lines at 09:26:52 and 09:27:19–09:27:21 show the same message for ~45 datasets, meaning gold runs request metadata before the bronze row exists or after it was deleted.  
- Observation: Bronze ingestion once failed with `OpsService.insert_bronze_manifest` raising “boom”, but the run still proceeded. Evidence: `OpsService` warning at 09:25:39; this implies the repo call fails but is logged and ignored without remediation, so later stages lack canonical metadata.

## Decision Log

- Decision: Add an `OpsService` helper that either loads an existing `DatasetInjestion` by `DatasetIdentity` or creates a placeholder row with bronze metadata before gold starts. Rationale: The warnings show gold is asking for metadata per dataset, but the DAO can’t find rows because they were never written; creating or reusing a row ensures `start_gold_ingestion` always succeeds. Date/Author: 2026-01-29 / Codex.
- Decision: Treat bronze persistence failures (like “boom”) as actionable failures rather than silenced warnings. Rationale: if bronze manifest insert fails we lose the row that gold later needs, so the run should either retry or stop with a clearer error to avoid the 40x “No ingestions found” cascade. Date/Author: 2026-01-29 / Codex.

## Outcomes & Retrospective

- When this plan is implemented, the orchestrator log will show only real errors (network failures, invalid recipe rejections) and will no longer generate `OpsService` warnings for tens of datasets. At completion, update this section with what was fixed and any remaining cleanup tasks (e.g., backfill of missing ingestion rows).

## Context and Orientation

`src/data_layer/orchestrator.py` drives bronze → silver → gold runs via `BronzeService`, `SilverService`, and `GoldService`. `OpsService` is the facade that writes to `ops.file_ingestions`. The gold loader calls `OpsService.start_gold_ingestion`/`finish_gold_ingestion` for each `DatasetIdentity`, but the log says no rows exist, indicating that bronze/silver stages either never recorded the dataset or the identity keys don’t match. The fix requires touching `BronzeService`, `SilverService`, `GoldService`, `OpsService`, and `DuckDbOpsRepo`.

## Plan of Work

1. **Audit ingestion creation** – examine how bronze/silver stages currently call `OpsService.insert_bronze_manifest`/`start_silver_ingestion` and ensure each dataset’s identity (domain/source/dataset/discriminator/ticker) is persisted with the row before any gold task runs. Note mismatches between dataset names used by gold (e.g., `company-market-cap`) and the row data kept in `ops.file_ingestions`.
2. **Strengthen `OpsService` metadata helpers** – add methods to load/update `DatasetInjestion` rows by identity and to recover from missing rows by creating stub entries with minimal bronze metadata. Ensure `start_gold_ingestion` and `finish_gold_ingestion` call these helpers instead of failing.
3. **Update `GoldService`** – before the gold transaction, compute each dataset’s identity (reusing `_resolve_silver_entry`) and call the reinforced `OpsService.start_gold_ingestion`. After dims/facts finish, call `finish_gold_ingestion` with counts/coverage so the gold columns are no longer null. On exceptions, update the ingestion row with `gold_errors` instead of letting the warning flood continue.
4. **Handle persistence failures explicitly** – in `BronzeService._persist_bronze`, if `OpsService.insert_bronze_manifest` raises (e.g., “boom”), log the failure and either retry or escalate; document why bronze rows are critical for gold.
5. **Add tests** – extend `tests/unit/ops/test_ops_service.py` (and add a new test file near `gold_service` if needed) to cover the new loader/creator helpers and ensure they silence the “No ingestions found” path.
6. **Validation/observability** – rerun the orchestrator end-to-end (locally) and query `ops.file_ingestions` to verify there is always a row per dataset and that gold columns are populated; the log should no longer contain the repeated warnings.

## Concrete Steps

- `python -m pytest tests/unit/ops/test_ops_service.py` and `python -m pytest tests/unit/services/test_gold_service.py` (new) should pass; expect clean output with no new warnings.
- Run `python -m src.data_layer.orchestrator` (or the existing script) and confirm the log snippet no longer shows “No ingestions found for gold start/finish” nor the “File ingestion persistence failed: boom” line.
- Query DuckDB:
  ```python
  import duckdb
  conn = duckdb.connect("dataduckdbstrawberry.duckdb")
  rows = conn.execute("""
      SELECT dataset, gold_object_type, gold_rows_created FROM ops.file_ingestions
      WHERE gold_object_type IS NOT NULL
      ORDER BY run_id DESC LIMIT 10
  """).fetchall()
  print(rows)
