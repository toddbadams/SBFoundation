# ExecPlan: Data Coverage Index & Dashboard

**Version**: 1.0
**Created**: 2026-02-28
**Status**: In Progress
**Author**: Claude + Todd

---

## Purpose / Big Picture

50 GB of bronze/silver data across 115 endpoints × 5,300 tickers × 30 years is unobservable without a control plane. This plan adds a **Data Coverage Index (DCI)** — a materialized `ops.coverage_index` table that answers four questions without touching raw files:

1. What datasets exist?
2. Which tickers are covered per dataset?
3. What date range exists per ticker?
4. Where are gaps relative to expectation?

The index is populated from `ops.file_ingestions` after every pipeline run and exposed via:
- A **CLI command** (`python -m sbfoundation.coverage`) for terminal queries
- A **Streamlit app** (`apps/coverage_dashboard/`) with 4 dashboard pages

---

## Progress

- [x] Step 1 — DuckDB migration: create `ops.coverage_index` *(2026-02-28)*
- [x] Step 2 — `CoverageIndexService`: compute and upsert coverage from `ops.file_ingestions` *(2026-02-28)*
- [x] Step 3 — Integrate refresh into `OpsService` + `SBFoundationAPI` *(2026-02-28)*
- [x] Step 4 — Unit tests for `CoverageIndexService` *(2026-02-28)*
- [x] Step 5 — CLI entry point (`src/sbfoundation/coverage/cli.py`) *(2026-02-28)*
- [x] Step 6 — Streamlit app scaffold (`apps/coverage_dashboard/`) *(2026-02-28)*
- [x] Step 7 — Page 1: Global Overview (Dataset Coverage Matrix) *(2026-02-28)*
- [x] Step 8 — Page 2: Dataset Drilldown *(2026-02-28)*
- [x] Step 9 — Page 3: Ticker Drilldown *(2026-02-28)*
- [x] Step 10 — Page 4: Ingestion Diagnostics *(2026-02-28)*
- [x] Step 11 — Validation: end-to-end smoke test *(2026-02-28)*
- [x] Step 12 — Split Home page into 4 tables (global/per-ticker × historical/snapshot) *(2026-02-28)*
- [x] Step 13 — Update Global Overview page with 4-section heatmap/chart layout *(2026-02-28)*

---

## Surprises & Discoveries

- **`ops.bronze_manifest` does not exist as a table** — the CLAUDE.md describes it, but the actual store is `ops.file_ingestions` via `DatasetInjestion`. The `upsert_file_ingestion` MERGE in `DuckDbOpsRepo` is the only path for tracking bronze+silver metadata. All aggregation must target `ops.file_ingestions`.
- **No existing CLI framework** — `pyproject.toml` has no `click` or `argparse`-based CLI entry point. A `__main__.py` pattern via `python -m sbfoundation.coverage` is the lowest-friction approach.
- **`is_timeseries` must come from the keymap** — `ops.file_ingestions` has no `date_key` column; `DatasetService` / `dataset_keymap.yaml` is the authoritative source. `CoverageIndexService` must accept the keymap to resolve this per dataset.
- **`is_historical` ≠ `is_timeseries`** — Some datasets have `row_date_col` (is_timeseries=True) but no from/to or limit in query_vars (e.g. technicals-sma-*). The user-visible distinction is `is_historical` (has date-range query vars), which is a stricter subset. Coverage ratio is now computed only for `is_historical=True` rows using 1990-01-01 as the fixed expected start date.
- **US_ALL_CAP universe size = 5,280** — Used as the denominator for ticker coverage % in the Home page and Global Overview page. Defined as `US_ALL_CAP_SIZE = 5_280` in both Streamlit files.
- **Streamlit not in `pyproject.toml`** — it must be declared only in `apps/coverage_dashboard/pyproject.toml` to keep the core package lean.

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-02-28 | `ops.coverage_index` (not `silver.coverage_index`) | Coverage is operational metadata; Silver is for business data |
| 2026-02-28 | Source: `ops.file_ingestions` | Already aggregates bronze + silver per file; avoids scanning raw JSON |
| 2026-02-28 | Streamlit app in `apps/coverage_dashboard/` with its own `pyproject.toml` | Keeps core package dependency-free; separate Poetry project inside monorepo |
| 2026-02-28 | Expected range = `universe.from_date` → today | Simple, consistent across all datasets; no per-dataset config edits |
| 2026-02-28 | Refresh after every pipeline run | Coverage is always current; no manual trigger required |
| 2026-02-28 | CLI via `python -m sbfoundation.coverage` | No new CLI framework dependency; consistent with Python stdlib conventions |

---

## Outcomes & Retrospective

All 11 steps completed 2026-02-28.

**What was delivered:**
- `ops.coverage_index` (24-column DuckDB table) populated after every pipeline run
- `CoverageIndexService.refresh()` aggregates `ops.file_ingestions` into the index; non-fatal on error
- 12 unit tests, 390 total tests passing
- CLI: `python -m sbfoundation.coverage [summary|dataset|ticker|stale]`
- Streamlit app at `apps/coverage_dashboard/` with 4 pages:
  - Home — global KPIs + dataset summary table
  - Page 1: Global Overview — heatmap + bottom-20 bar chart
  - Page 2: Dataset Drilldown — histogram, table, temporal presence heatmap
  - Page 3: Ticker Drilldown — completeness gauge, per-dataset bar + table
  - Page 4: Ingestion Diagnostics — error rates, latency, hash stability, error log

**Smoke test results (in-memory DuckDB):**
- coverage_index: 24 columns confirmed
- coverage_ratio = 1.0 for AAPL with full date coverage
- Snapshot rows: is_timeseries=False, coverage_ratio=NULL, age_days populated
- Idempotency confirmed (3 rows after two refreshes)
- All diagnostic queries (error_rates, latency, hash_stability, recent_errors) return correct data
- All Streamlit page .py files parse without syntax errors

**Lessons learned:**
- `ops.bronze_manifest` referenced in CLAUDE.md does not exist; real table is `ops.file_ingestions`
- `is_timeseries` must come from keymap (`row_date_col` field), not from `ops.file_ingestions`
- DuckDB 1.4 SQL: use `INTERVAL '7 days'` (quoted), `datediff()`, `current_date` — not `TODAY()`
- Deferred manifest queue in `BronzeService` requires explicit `_flush_manifest_inserts()` in tests
- `is_historical` (has from/to or limit query_vars) is the correct coverage discriminator for the UI; `is_timeseries` (has row_date_col) is broader and was replaced as the primary switch for coverage_ratio computation
- Fixed expected start date for all historical datasets: 1990-01-01 (hardcoded in `CoverageIndexService` as `_HISTORICAL_FROM_DATE`), not `universe_from_date`

---

## Context and Orientation

### Key Files

| File | Role |
|---|---|
| `src/sbfoundation/ops/services/ops_service.py` | `OpsService` — hook `refresh_coverage_index()` here after each run |
| `src/sbfoundation/ops/infra/duckdb_ops_repo.py` | `DuckDbOpsRepo` — add `upsert_coverage_index()` and `query_coverage_index()` |
| `src/sbfoundation/ops/dtos/file_injestion.py` | `DatasetInjestion` — source DTO for aggregation |
| `src/sbfoundation/api.py` | `SBFoundationAPI` — call `ops_service.refresh_coverage_index()` at end of `run()` |
| `src/sbfoundation/dataset/services/dataset_service.py` | Provides keymap → `date_key` lookup for `is_timeseries` |
| `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py` | Connection management; use `ops_transaction()` for writes |
| `config/dataset_keymap.yaml` | Authoritative for `date_key` (null = snapshot, string = timeseries) |
| `db/migrations/` | SQL migration files; new file needed |
| `apps/coverage_dashboard/` | Streamlit app (to be created) |

### Term Definitions

- **coverage_ratio**: `actual_calendar_days / expected_calendar_days` where actual = `(max_date - min_date).days` and expected = `(today - universe_from_date).days`. Only computed for timeseries datasets.
- **is_timeseries**: True when `date_key IS NOT NULL` in the keymap (i.e., the endpoint returns dated rows). False for snapshot endpoints (profile, peers, etc.).
- **age_days**: For snapshots only — `(today - last_snapshot_date).days`. Indicates staleness.
- **ticker_data_completeness_score**: Per-ticker weighted average of `coverage_ratio` across all timeseries datasets. Computed as a derived query (not stored), shown in Ticker Drilldown.

---

## Plan of Work

### Step 1 — DuckDB Migration

Create `db/migrations/20260228_001_create_ops_coverage_index.sql`:

```sql
CREATE TABLE IF NOT EXISTS ops.coverage_index (
    domain               VARCHAR NOT NULL,
    source               VARCHAR NOT NULL,
    dataset              VARCHAR NOT NULL,
    discriminator        VARCHAR NOT NULL DEFAULT '',
    ticker               VARCHAR NOT NULL DEFAULT '',

    -- Timeseries coverage
    min_date             DATE,
    max_date             DATE,
    coverage_ratio       DOUBLE,       -- actual_days / expected_days (NULL for snapshots)

    -- Expected window (universe.from_date → today at refresh time)
    expected_start_date  DATE,
    expected_end_date    DATE,

    -- Volume
    total_files          INTEGER NOT NULL DEFAULT 0,
    promotable_files     INTEGER NOT NULL DEFAULT 0,
    ingestion_runs       INTEGER NOT NULL DEFAULT 0,
    silver_rows_created  INTEGER NOT NULL DEFAULT 0,
    silver_rows_failed   INTEGER NOT NULL DEFAULT 0,

    -- Errors
    error_count          INTEGER NOT NULL DEFAULT 0,
    error_rate           DOUBLE,

    -- Recency
    last_ingested_at     TIMESTAMP,
    last_run_id          VARCHAR,

    -- Snapshot-specific
    snapshot_count       INTEGER NOT NULL DEFAULT 0,
    last_snapshot_date   DATE,
    age_days             INTEGER,

    -- Flags
    is_timeseries        BOOLEAN NOT NULL DEFAULT TRUE,

    -- Bookkeeping
    updated_at           TIMESTAMP NOT NULL,

    PRIMARY KEY (domain, source, dataset, discriminator, ticker)
);
```

Register this migration in `DuckDbBootstrap` so it applies on next startup.

---

### Step 2 — `CoverageIndexService`

Create `src/sbfoundation/coverage/coverage_index_service.py`.

**Constructor parameters:**
```python
def __init__(
    self,
    ops_repo: DuckDbOpsRepo | None = None,
    dataset_service: DatasetService | None = None,
    logger: SBLogger | None = None,
) -> None
```

**Key method:**
```python
def refresh(
    self,
    *,
    run_id: str,
    universe_from_date: date,
    today: date,
) -> int:  # returns rows upserted
```

**Computation logic:**

Issue one SQL query against `ops.file_ingestions` to aggregate per `(domain, source, dataset, discriminator, ticker)`:

```sql
SELECT
    domain,
    source,
    dataset,
    COALESCE(discriminator, '')  AS discriminator,
    COALESCE(ticker, '')         AS ticker,
    MIN(bronze_from_date)        AS min_date,
    MAX(bronze_to_date)          AS max_date,
    COUNT(*)                     AS total_files,
    COUNT(*) FILTER (WHERE bronze_can_promote = true)  AS promotable_files,
    COUNT(DISTINCT run_id)       AS ingestion_runs,
    COALESCE(SUM(silver_rows_created), 0)              AS silver_rows_created,
    COALESCE(SUM(silver_rows_failed), 0)               AS silver_rows_failed,
    COUNT(*) FILTER (WHERE bronze_error IS NOT NULL)   AS error_count,
    MAX(bronze_injest_start_time)                      AS last_ingested_at,
    MAX(run_id)                                        AS last_run_id
FROM ops.file_ingestions
GROUP BY domain, source, dataset, COALESCE(discriminator, ''), COALESCE(ticker, '')
```

Then in Python, for each row:
1. Look up `is_timeseries` from `DatasetService.get_entry(domain, source, dataset).recipes[0].date_key is not None`
2. Compute `coverage_ratio`, `snapshot_count`, `last_snapshot_date`, `age_days` accordingly
3. Set `expected_start_date = universe_from_date`, `expected_end_date = today`
4. UPSERT (INSERT OR REPLACE) into `ops.coverage_index`

**`is_timeseries` lookup**: `DatasetService` already loads the full keymap. Add a method `get_date_key(domain, source, dataset) -> str | None` or use the existing `get_entry()` path. Cache the result since it's per-dataset, not per-row.

---

### Step 3 — `DuckDbOpsRepo` Extensions

Add to `src/sbfoundation/ops/infra/duckdb_ops_repo.py`:

```python
def aggregate_file_ingestions_for_coverage(self) -> list[dict]:
    """Return one aggregated row per (domain, source, dataset, discriminator, ticker)."""
    ...

def upsert_coverage_index(self, rows: list[dict]) -> int:
    """MERGE rows into ops.coverage_index. Returns row count."""
    ...

def query_coverage_index(
    self,
    *,
    domain: str | None = None,
    dataset: str | None = None,
    ticker: str | None = None,
) -> list[dict]:
    """Filter coverage_index for CLI / Streamlit queries."""
    ...
```

Use `ops_transaction()` context manager for the upsert.

---

### Step 4 — Pipeline Integration

In `src/sbfoundation/ops/services/ops_service.py`, add:

```python
def refresh_coverage_index(
    self,
    *,
    run_id: str,
    universe_from_date: date,
    today: date,
) -> None:
    rows = CoverageIndexService(ops_repo=self._ops_repo, ...).refresh(...)
    self._logger.info("Coverage index refreshed: %d rows", rows, run_id=run_id)
```

In `src/sbfoundation/api.py`, call `self._ops_service.refresh_coverage_index(...)` at the end of `SBFoundationAPI.run()`, after the main pipeline loop completes and before `finish_run()`.

---

### Step 5 — CLI Entry Point

Create `src/sbfoundation/coverage/__init__.py` and `src/sbfoundation/coverage/cli.py`.

The `__main__.py` pattern: `src/sbfoundation/coverage/__main__.py` calls `cli.main()`.

Invocation: `python -m sbfoundation.coverage [subcommand] [options]`

**Subcommands:**

| Command | Description | Output |
|---|---|---|
| `summary` | All datasets, sorted by coverage_ratio ASC | Table: domain, dataset, tickers_covered, avg_coverage_ratio, error_rate |
| `dataset <name>` | Tickers for one dataset, sorted by coverage_ratio ASC | Table: ticker, min_date, max_date, coverage_ratio, error_count |
| `ticker <symbol>` | All datasets for one ticker | Table: dataset, coverage_ratio, last_ingested_at, age_days |
| `stale [--days N]` | Snapshots older than N days (default 90) | Table: dataset, ticker, last_snapshot_date, age_days |

Use `argparse`. Format output with Python's `tabulate` or simple `str.ljust` padding (no new dependencies preferred — use stdlib `csv` writer for `-o csv` flag).

---

### Step 6 — Streamlit App Scaffold

Create `apps/coverage_dashboard/`:

```
apps/coverage_dashboard/
├── pyproject.toml          # separate Poetry project
├── .streamlit/
│   └── config.toml         # theme, port
├── Home.py                 # landing page with global stats cards
└── pages/
    ├── 1_Global_Overview.py
    ├── 2_Dataset_Drilldown.py
    ├── 3_Ticker_Drilldown.py
    └── 4_Ingestion_Diagnostics.py
```

**`pyproject.toml` dependencies:**
```toml
[tool.poetry.dependencies]
python = ">=3.11,<3.14"
streamlit = "^1.40"
plotly = "^5.24"
pandas = "^2.3"
duckdb = "^1.4"
sb-foundation = {path = "../../", develop = true}
```

The app reads from DuckDB directly using the same `DuckDbBootstrap` connection. Do not duplicate the query logic — import `DuckDbOpsRepo` from `sbfoundation`.

---

### Step 7 — Page 1: Global Overview

File: `pages/1_Global_Overview.py`

**Layout:**
- Top row: 4 metric cards — total datasets, total tickers, avg coverage_ratio, datasets with errors
- Heatmap (Plotly): rows = datasets, columns = [% tickers covered, % updated last 7 days, median history years, oldest max_date age]. Color scale: red → green.
- Bar chart: bottom 20 datasets by coverage_ratio

**SQL driving the heatmap:**
```sql
SELECT
    dataset,
    COUNT(DISTINCT ticker)                                                                     AS tickers_covered,
    AVG(coverage_ratio)                                                                        AS avg_coverage_ratio,
    COUNT(*) FILTER (WHERE last_ingested_at > NOW() - INTERVAL 7 DAYS) / COUNT(*)::DOUBLE     AS pct_updated_7d,
    MEDIAN(DATEDIFF('year', min_date, max_date))                                               AS median_history_years,
    MAX(DATEDIFF('day', max_date, TODAY()))                                                    AS oldest_max_date_age
FROM ops.coverage_index
GROUP BY dataset
ORDER BY avg_coverage_ratio ASC
```

---

### Step 8 — Page 2: Dataset Drilldown

File: `pages/2_Dataset_Drilldown.py`

**Controls:** dropdown to select dataset (populated from `coverage_index.dataset` distinct values)

**Layout:**
- Summary strip: ticker count, avg coverage_ratio, error_rate, last refreshed
- Histogram: distribution of coverage_ratio across tickers
- Table: ticker | min_date | max_date | coverage_ratio | error_count | last_ingested_at — sortable
- Temporal heatmap (for timeseries datasets only): X = year (1990–today), Y = ticker (sampled to top/bottom 50 by coverage), color = coverage_ratio per year. Use `px.density_heatmap` or a custom aggregation.

---

### Step 9 — Page 3: Ticker Drilldown

File: `pages/3_Ticker_Drilldown.py`

**Controls:** text input for ticker symbol

**Layout:**
- Ticker completeness score: `weighted_avg(coverage_ratio)` across all timeseries datasets (equal weights). Show as gauge chart (Plotly indicator).
- Table: dataset | is_timeseries | coverage_ratio | min_date | max_date | age_days | error_count
- Distribution histogram: where does this ticker fall vs all tickers on completeness score?

**ticker_data_completeness_score query:**
```sql
SELECT
    AVG(coverage_ratio) AS completeness_score
FROM ops.coverage_index
WHERE ticker = ?
  AND is_timeseries = TRUE
  AND coverage_ratio IS NOT NULL
```

---

### Step 10 — Page 4: Ingestion Diagnostics

File: `pages/4_Ingestion_Diagnostics.py`

Draws from `ops.file_ingestions` directly (not coverage_index) for run-level granularity.

**Layout:**
- Error rate by dataset (bar chart): `error_count / total_files`
- Non-200 response rate: group by `dataset`, show `COUNT(*) FILTER (WHERE bronze_error IS NOT NULL) / COUNT(*)`
- Avg latency by dataset: `AVG(DATEDIFF('millisecond', bronze_injest_start_time, bronze_injest_end_time))`
- Hash change frequency: `COUNT(DISTINCT bronze_payload_hash) / COUNT(*)` per dataset — measures how often vendor data actually changes vs. returns identical payloads

---

## Concrete Steps

### Step 1: Apply migration
```bash
# Run the app once after creating the migration file; DuckDbBootstrap auto-applies pending migrations
cd C:\sb\SBFoundation
python -c "from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap; DuckDbBootstrap().close()"
# Expected: migration 20260228_001 applied; ops.coverage_index created
```

### Step 2: Run the coverage refresh manually to verify
```bash
python -c "
from datetime import date
from sbfoundation.coverage.coverage_index_service import CoverageIndexService
svc = CoverageIndexService()
n = svc.refresh(run_id='manual-test', universe_from_date=date(1990, 1, 1), today=date.today())
print(f'Upserted {n} rows')
svc.close()
"
# Expected: prints row count > 0 (proportional to data in ops.file_ingestions)
```

### Step 3: Test CLI
```bash
python -m sbfoundation.coverage summary
python -m sbfoundation.coverage dataset fmp-price-eod
python -m sbfoundation.coverage ticker AAPL
python -m sbfoundation.coverage stale --days 90
```

### Step 4: Install and run Streamlit app
```bash
cd apps/coverage_dashboard
poetry install
poetry run streamlit run Home.py
# Expected: browser opens at http://localhost:8501
```

### Step 5: Run unit tests
```bash
cd C:\sb\SBFoundation
poetry run pytest tests/unit/coverage/ -v
```

---

## Validation and Acceptance

- [ ] `ops.coverage_index` exists with correct schema; `DESCRIBE ops.coverage_index` shows all columns
- [ ] After a pipeline run, `SELECT COUNT(*) FROM ops.coverage_index` increases (or stays same for re-runs)
- [ ] `coverage_ratio` is between 0.0 and 1.0+ (may exceed 1 if data predates universe start)
- [ ] Snapshot datasets have `is_timeseries = FALSE`, `coverage_ratio IS NULL`, `age_days` populated
- [ ] CLI `summary` prints tabular output with no Python exceptions
- [ ] Streamlit app loads all 4 pages without errors on a real DuckDB file
- [ ] Refresh is idempotent: running twice with the same data yields same row values
- [ ] Pipeline run completes without errors; last log line includes `Coverage index refreshed: N rows`

---

## Idempotence and Recovery

- `ops.coverage_index` uses `INSERT OR REPLACE` (keyed on PK `domain, source, dataset, discriminator, ticker`) — safe to run refresh multiple times.
- If `CoverageIndexService.refresh()` fails, the pipeline run still completes; failure is logged as `WARNING` and does not raise (same pattern as `finish_silver_ingestion`).
- Migration is guarded by `IF NOT EXISTS` — re-applying is a no-op.
- Streamlit is read-only — no writes to DuckDB from the dashboard.
- To rebuild from scratch: `DELETE FROM ops.coverage_index;` then trigger a refresh.

---

## Artifacts and Notes

*To be filled in as steps are completed — paste relevant log lines, row counts, and diff summaries here.*

---

## Interfaces and Dependencies

### New Internal Interfaces

| Interface | File | Consumed By |
|---|---|---|
| `CoverageIndexService.refresh(run_id, universe_from_date, today)` | `src/sbfoundation/coverage/coverage_index_service.py` | `OpsService`, CLI |
| `DuckDbOpsRepo.aggregate_file_ingestions_for_coverage()` | `src/sbfoundation/ops/infra/duckdb_ops_repo.py` | `CoverageIndexService` |
| `DuckDbOpsRepo.upsert_coverage_index(rows)` | same | `CoverageIndexService` |
| `DuckDbOpsRepo.query_coverage_index(...)` | same | CLI, Streamlit |
| `OpsService.refresh_coverage_index(...)` | `src/sbfoundation/ops/services/ops_service.py` | `SBFoundationAPI` |

### External Dependencies

| Library | Where | Version | Notes |
|---|---|---|---|
| `streamlit` | `apps/coverage_dashboard/pyproject.toml` only | `^1.40` | NOT in core package |
| `plotly` | `apps/coverage_dashboard/pyproject.toml` only | `^5.24` | NOT in core package |
| `duckdb` | Already in `pyproject.toml` | `^1.4.3` | Shared |
| `pandas` | Already in `pyproject.toml` | `^2.3.3` | Shared |

### Types Required

```python
# CoverageIndexRow (internal dataclass, not a DTO)
@dataclass
class CoverageIndexRow:
    domain: str
    source: str
    dataset: str
    discriminator: str
    ticker: str
    min_date: date | None
    max_date: date | None
    coverage_ratio: float | None
    expected_start_date: date | None
    expected_end_date: date | None
    total_files: int
    promotable_files: int
    ingestion_runs: int
    silver_rows_created: int
    silver_rows_failed: int
    error_count: int
    error_rate: float | None
    last_ingested_at: datetime | None
    last_run_id: str | None
    snapshot_count: int
    last_snapshot_date: date | None
    age_days: int | None
    is_timeseries: bool
    updated_at: datetime
```
