# ExecPlan: Run Statistics Reporter

**Status**: Complete
**Author**: Claude / Todd
**Created**: 2026-02-21
**Updated**: 2026-02-21

---

## Purpose / Big Picture

After every `SBFoundationAPI.run()` completes, print a structured per-dataset Bronze + Silver
summary to stdout and write the full report as a Markdown file to the logs folder. This surfaces
what happened in each run (which domains ran, how many files were written, how many Silver rows
were promoted, any errors) and a cross-run history view showing how the database has grown over
time.

**User-visible behaviour enabled:**
1. Inline console output — a human-readable Bronze/Silver breakdown with error list for the
   current run, written via the existing `SBLogger` so it appears in `logs_<YYYY-MM-DD>.txt`.
2. Persistent Markdown report — `$DATA_ROOT_FOLDER/logs/{run_id}_report.md` — a durable,
   navigable artifact showing the full current-run stats **plus** an all-runs history table and
   accumulated Silver table sizes.

**Design inspiration**: `GoldDimensionStatsReporter` in SBIntelligence (`gold_layer_dimensions.md`).
The same two-report pattern (current-build + all-builds history) is applied to SBFoundation's
`ops.file_ingestions` data, scoped to the current `run_id` for the per-run view and unscoped for
the history view.

---

## Progress

- [x] Create `src/sbfoundation/ops/services/run_stats_reporter.py` — `RunStatsReporter` class (2026-02-21)
- [x] Implement `report(run_id: str) -> str` — current-run Markdown section (2026-02-21)
- [x] Implement `history_report() -> str` — all-runs Markdown section (2026-02-21)
- [x] Implement `write_report(run_id: str) -> pathlib.Path` — assembles both sections, writes
      `{run_id}_report.md` to the logs folder, returns the written path (2026-02-21)
- [x] Update `api.py` `run()` to call `RunStatsReporter.write_report(run.run_id)` after `_close_run()` (2026-02-21)
- [x] Update `api.py` `run()` to log the written path via `self.logger.info(...)` (2026-02-21)
- [x] Create `tests/unit/ops/test_run_stats_reporter.py` — unit tests using in-memory DuckDB (2026-02-21)
- [x] `pytest tests/unit/ops/test_run_stats_reporter.py -v` → 24 passed (2026-02-21)
- [x] `pytest tests/unit/ -v` → 334 passed, 0 failures (2026-02-21)

---

## Surprises & Discoveries

*(Populated as work proceeds.)*

---

## Decision Log

- **2026-02-21**: Write the report as a Markdown file (not plain text). Markdown enables rendered
  tables in GitHub, VS Code preview, and any Markdown reader. The logs folder is the correct
  destination because `LoggerFactory` already writes `logs_<YYYY-MM-DD>.txt` there; the run
  report sits alongside it under the same folder.
- **2026-02-21**: The history report is **not** sourced from a separate `ops.run_summary` table.
  All data is derived from `ops.file_ingestions` grouped by `run_id`, consistent with the
  SBIntelligence pattern of querying the actual data tables rather than a separate build-metadata
  table. This avoids introducing a new table for an observability feature.
- **2026-02-21**: Accumulated Silver table sizes are computed by querying
  `information_schema.tables WHERE table_schema = 'silver'` and issuing one `COUNT(*)` per table.
  This gives the total rows regardless of run, which is the meaningful metric for Silver (UPSERT
  semantics mean rows accumulate across runs, not per run).
- **2026-02-21**: The current-run inline log message in `_close_run()` is preserved unchanged
  (`run.msg`). The reporter supplements it; it does not replace it.

---

## Outcomes & Retrospective

*(Populated after implementation is complete.)*

---

## Context and Orientation

### Key Files

| File | Role |
|---|---|
| `src/sbfoundation/api.py` | `SBFoundationAPI.run()` — entry point; `_close_run()` — run finalizer |
| `src/sbfoundation/ops/services/ops_service.py` | `OpsService` — wraps `DuckDbOpsRepo` |
| `src/sbfoundation/ops/infra/duckdb_ops_repo.py` | `DuckDbOpsRepo` — all `ops.file_ingestions` queries |
| `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py` | `DuckDbBootstrap` — connection factory |
| `src/sbfoundation/infra/logger.py` | `LoggerFactory`, `SBLogger` |
| `src/sbfoundation/folders.py` | `DATA_ROOT_FOLDER` and other path constants |

### `ops.file_ingestions` Schema (relevant columns)

| Column | Type | Notes |
|---|---|---|
| `run_id` | VARCHAR | Groups all files for one `SBFoundationAPI.run()` call |
| `file_id` | VARCHAR | One row per Bronze file |
| `domain` | VARCHAR | e.g. `company`, `fundamentals`, `market` |
| `source` | VARCHAR | e.g. `fmp` |
| `dataset` | VARCHAR | e.g. `company-profile`, `income-statement` |
| `discriminator` | VARCHAR | Empty for per-ticker datasets |
| `ticker` | VARCHAR | Null for global datasets |
| `bronze_rows` | INTEGER | Rows in the Bronze payload |
| `bronze_error` | VARCHAR | Null if successful |
| `bronze_injest_start_time` | TIMESTAMP | When Bronze request started |
| `bronze_can_promote` | BOOLEAN | True for promotable files |
| `silver_tablename` | VARCHAR | Target Silver table (null until promoted) |
| `silver_rows_created` | INTEGER | Rows UPSERT-inserted |
| `silver_rows_updated` | INTEGER | Rows UPSERT-updated |
| `silver_rows_failed` | INTEGER | Rows that failed Silver promotion |
| `silver_from_date` | DATE | Coverage start |
| `silver_to_date` | DATE | Coverage end |
| `silver_errors` | VARCHAR | Null if Silver promotion succeeded |

### Logs Folder

`LoggerFactory` writes `logs_<YYYY-MM-DD>.txt` to `$DATA_ROOT_FOLDER/logs/`. The run report
`{run_id}_report.md` is written alongside it. Resolve the path as:

```python
from sbfoundation.folders import DATA_ROOT_FOLDER
import pathlib
logs_dir = pathlib.Path(DATA_ROOT_FOLDER) / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
report_path = logs_dir / f"{run_id}_report.md"
```

---

## Plan of Work

### Step 1 — `RunStatsReporter` class (`run_stats_reporter.py`)

Create `src/sbfoundation/ops/services/run_stats_reporter.py`.

The class accepts an optional injected `DuckDbBootstrap` for testability. It owns a
`read_connection()` context internally.

```python
import duckdb
from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap

class RunStatsReporter:
    def __init__(self, bootstrap: DuckDbBootstrap | None = None) -> None:
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()
```

### Step 2 — `report(run_id: str) -> str` (current-run section)

Returns a Markdown string scoped to the given `run_id`. Never inflated by rows from other runs.

**Query group 1 — Bronze summary by domain:**
```sql
SELECT domain,
       COUNT(*) AS files_total,
       SUM(CASE WHEN bronze_error IS NULL THEN 1 ELSE 0 END) AS files_passed,
       SUM(CASE WHEN bronze_error IS NOT NULL THEN 1 ELSE 0 END) AS files_failed,
       SUM(COALESCE(bronze_rows, 0)) AS rows_ingested
FROM ops.file_ingestions
WHERE run_id = ?
GROUP BY domain
ORDER BY domain
```

**Query group 2 — Bronze breakdown by dataset:**
```sql
SELECT domain, dataset,
       COUNT(*) AS files_total,
       SUM(CASE WHEN bronze_error IS NULL THEN 1 ELSE 0 END) AS files_passed,
       SUM(CASE WHEN bronze_error IS NOT NULL THEN 1 ELSE 0 END) AS files_failed,
       SUM(COALESCE(bronze_rows, 0)) AS rows_ingested
FROM ops.file_ingestions
WHERE run_id = ?
GROUP BY domain, dataset
ORDER BY domain, dataset
```

**Query group 3 — Silver promotion by table:**
```sql
SELECT silver_tablename,
       SUM(COALESCE(silver_rows_created, 0)) AS rows_created,
       SUM(COALESCE(silver_rows_updated, 0)) AS rows_updated,
       SUM(COALESCE(silver_rows_failed, 0))  AS rows_failed,
       MIN(silver_from_date) AS coverage_from,
       MAX(silver_to_date)   AS coverage_to
FROM ops.file_ingestions
WHERE run_id = ? AND silver_tablename IS NOT NULL
GROUP BY silver_tablename
ORDER BY silver_tablename
```

**Query group 4 — Error summary (first 20):**
```sql
SELECT domain, dataset, COALESCE(ticker, '—') AS ticker, bronze_error
FROM ops.file_ingestions
WHERE run_id = ? AND bronze_error IS NOT NULL
ORDER BY domain, dataset, ticker
LIMIT 20
```

**Query group 5 — Silver errors (first 20):**
```sql
SELECT domain, dataset, COALESCE(ticker, '—') AS ticker, silver_errors
FROM ops.file_ingestions
WHERE run_id = ? AND silver_errors IS NOT NULL
ORDER BY domain, dataset, ticker
LIMIT 20
```

### Step 3 — `history_report() -> str` (all-runs section)

Returns a Markdown string covering every `run_id` present in `ops.file_ingestions`.

**Query group 1 — Per-run summary:**
```sql
SELECT run_id,
       MIN(bronze_injest_start_time) AS started_at,
       COUNT(DISTINCT file_id)       AS files_total,
       SUM(CASE WHEN bronze_error IS NULL THEN 1 ELSE 0 END) AS files_passed,
       SUM(CASE WHEN bronze_error IS NOT NULL THEN 1 ELSE 0 END) AS files_failed,
       SUM(COALESCE(bronze_rows, 0)) AS rows_ingested,
       SUM(COALESCE(silver_rows_created, 0)) AS silver_rows_created
FROM ops.file_ingestions
GROUP BY run_id
ORDER BY started_at DESC
```

**Query group 2 — Accumulated Silver table sizes:**

Enumerate Silver tables via `information_schema.tables WHERE table_schema = 'silver'`. For each
table, issue `SELECT COUNT(*) FROM silver.<table_name>`. Assemble results into a sorted Markdown
table. Gracefully skip tables that raise an exception (log a warning, continue).

### Step 4 — `write_report(run_id: str) -> pathlib.Path`

Assembles the full Markdown document and writes it to the logs folder.

```python
def write_report(self, run_id: str) -> pathlib.Path:
    from sbfoundation.folders import DATA_ROOT_FOLDER
    import pathlib, datetime

    current = self.report(run_id)
    history = self.history_report()

    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    doc = f"# SBFoundation Run Report\n\n**run_id**: `{run_id}`  \n**Generated**: {generated_at}\n\n---\n\n{current}\n\n---\n\n{history}\n"

    logs_dir = pathlib.Path(DATA_ROOT_FOLDER) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / f"{run_id}_report.md"
    report_path.write_text(doc, encoding="utf-8")
    return report_path
```

### Step 5 — `api.py` changes

In `SBFoundationAPI.run()`, after `self._close_run(run)`:

```python
try:
    reporter = RunStatsReporter()
    report_path = reporter.write_report(run.run_id)
    reporter.close()
    self.logger.info(f"Run report written: {report_path}", run_id=run.run_id)
except Exception as exc:
    self.logger.warning(f"Run stats reporter failed (non-fatal): {exc}", run_id=run.run_id)
```

The reporter failure is caught and logged as a warning — it must never crash the pipeline.

---

## Concrete Steps

```bash
# 1. Activate environment
cd C:/sb/SBFoundation
poetry shell

# 2. Verify clean baseline
black --check src/ tests/ && isort --check src/ tests/ && flake8 src/ tests/

# 3. Implement RunStatsReporter
# Create src/sbfoundation/ops/services/run_stats_reporter.py

# 4. Update api.py — add reporter call after _close_run()

# 5. Auto-format
black src/ tests/ && isort src/ tests/

# 6. Type-check
mypy src/sbfoundation/ops/services/run_stats_reporter.py src/sbfoundation/api.py

# 7. Unit tests
pytest tests/unit/ops/test_run_stats_reporter.py -v

# 8. Integration smoke test — verify report file is written
python -m sbfoundation.api  # (or equivalent invocation with a small ticker limit)
ls $DATA_ROOT_FOLDER/logs/
```

---

## Validation and Acceptance

| # | Check | Expected |
|---|-------|---------|
| 1 | Run any domain (e.g. `company` with `ticker_limit=5`) | `{run_id}_report.md` created in logs folder |
| 2 | Report file opens and renders as valid Markdown | All section headers, tables, code blocks present |
| 3 | Bronze domain table in report: `files_passed + files_failed = files_total` | Row sums consistent |
| 4 | Silver promotion table: row counts match `SELECT SUM(silver_rows_created) FROM ops.file_ingestions WHERE run_id = ?` | Exact match |
| 5 | Error section lists ≤ 20 rows; "… N more errors not shown" footer if > 20 | Truncation works |
| 6 | History table: most recent run appears first | `ORDER BY started_at DESC` |
| 7 | Accumulated Silver sizes: each row count matches `SELECT COUNT(*) FROM silver.<table>` | Exact match |
| 8 | Run two times back-to-back; second report shows 2 rows in history table | Accumulation works |
| 9 | Reporter failure (e.g. DB path wrong) does not raise from `run()` | Warning logged, `run()` returns normally |
| 10 | `pytest tests/unit/ops/test_run_stats_reporter.py -v` | All pass |

---

## Idempotence and Recovery

- Writing the report file is idempotent — if `run()` is called twice with the same `run_id` (e.g.
  a retry), `write_text()` overwrites the previous file. No append behaviour.
- If the logs folder does not exist it is created by `mkdir(parents=True, exist_ok=True)`.
- The reporter opens its own `read_connection()`; it does not share or close the main pipeline
  connection. Safe to call after `_close_run()`.

---

## Artifacts and Notes

*(Populated after implementation with transcripts, row counts, sample report output.)*

---

## Interfaces and Dependencies

### `RunStatsReporter` public interface

```python
class RunStatsReporter:
    def __init__(self, bootstrap: DuckDbBootstrap | None = None) -> None: ...
    def report(self, run_id: str) -> str: ...          # Markdown current-run section
    def history_report(self) -> str: ...               # Markdown all-runs section
    def write_report(self, run_id: str) -> pathlib.Path: ...  # Writes {run_id}_report.md
    def close(self) -> None: ...
```

### Dependencies

| Library / Module | Usage |
|---|---|
| `duckdb` | Read queries against `ops.file_ingestions` and `information_schema.tables` |
| `pathlib` | Report file path construction |
| `datetime` | `generated_at` timestamp in report header |
| `sbfoundation.infra.duckdb.duckdb_bootstrap.DuckDbBootstrap` | Connection factory |
| `sbfoundation.folders.DATA_ROOT_FOLDER` | Logs folder base path |

### Expected Markdown Output Format

**Current-run section** (rendered from `report(run_id)`):

```markdown
## Bronze Ingestion — run_id=`20260221.abc123`

| Domain        | Files | Passed | Failed | Bronze Rows |
|---------------|------:|-------:|-------:|------------:|
| company       |   245 |    242 |      3 |     245,000 |
| fundamentals  |   180 |    180 |      0 |     540,000 |
| technicals    |   180 |    177 |      3 |   1,260,000 |

### By Dataset

| Domain       | Dataset               | Files | Passed | Failed | Bronze Rows |
|--------------|----------------------|------:|-------:|-------:|------------:|
| company      | company-profile       |   245 |    242 |      3 |     245,000 |
| fundamentals | income-statement      |    90 |     90 |      0 |     270,000 |
| ...          | ...                   |   ... |    ... |    ... |         ... |

## Silver Promotion

| Table                  | Created | Updated | Failed | Coverage From | Coverage To |
|------------------------|--------:|--------:|-------:|---------------|-------------|
| fmp_company_profile    |   2,450 |       0 |      0 | —             | —           |
| fmp_income_statement   |  15,600 |       0 |      0 | 2010-01-01    | 2025-12-31  |
| fmp_technicals_sma     |   9,000 |       0 |      0 | 2015-01-01    | 2026-02-21  |

## Errors

### Bronze Errors (3)

| Domain    | Dataset         | Ticker | Error              |
|-----------|----------------|--------|--------------------|
| company   | company-profile | AAPL   | INVALID TICKER     |
| technicals | technicals-sma | BKLY  | HTTP 404           |
| technicals | technicals-sma | SPCE  | HTTP 429           |
```

**History section** (rendered from `history_report()`):

```markdown
## Run History — All Runs

| Run ID            | Started At           | Files | Passed | Failed | Bronze Rows | Silver Rows |
|-------------------|----------------------|------:|-------:|-------:|------------:|------------:|
| 20260221.abc123   | 2026-02-21 08:00:00  |   605 |    599 |      6 |   2,045,000 |      27,050 |
| 20260220.def456   | 2026-02-20 07:55:00  |   601 |    601 |      0 |   2,039,000 |      27,010 |

## Accumulated Silver Table Sizes

| Table                          | Total Rows |
|-------------------------------|-----------:|
| fmp_balance_sheet_statement    |     95,000 |
| fmp_cash_flow_statement        |     95,000 |
| fmp_company_profile            |      2,541 |
| fmp_income_statement           |    125,000 |
| fmp_technicals_sma             |    450,000 |
| ...                            |        ... |
```
