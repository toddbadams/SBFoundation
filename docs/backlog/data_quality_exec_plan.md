# ExecPlan: Silver Layer Data Quality Metrics

**Status**: Pending implementation
**Branch**: `feature/silver-data-quality`
**Created**: 2026-03-14
**Author**: Todd Adams

---

## Purpose / Big Picture

Implement a measurable, automated data quality framework for the Silver layer. After each pipeline run, a `SilverQualityService` executes a suite of DuckDB SQL checks against every Silver table and writes the results to `ops.silver_quality_metrics`. The metrics cover four dimensions: **completeness**, **consistency**, **coverage**, and **timeliness**. This gives objective, per-dataset quality scores that can be tracked over time, compared across providers, and surfaced in the Streamlit dashboard.

**User-visible outcome**: Running `uv run python -m sbfoundation.quality` prints a data quality scorecard across all Silver tables. The `ops.silver_quality_metrics` table accumulates one row per (dataset, dimension, metric_name, run_date) so quality trends are queryable.

**Dimensions implemented in this plan:**

| # | Dimension | What it measures |
|---|---|---|
| 1 | **Completeness** | NULL rate per column per Silver table; rows present vs expected |
| 2 | **Consistency** | Business rule violations (OHLCV constraints, balance sheet identity, ratio sanity) |
| 3 | **Coverage** | Instrument × date × field density (extends existing `ops.coverage_index`) |
| 4 | **Timeliness** | Age of most recent row vs expected cadence per dataset |

**Out of scope for this plan** (future ExecPlans):
- Accuracy (cross-provider price comparison) — requires a second provider in-repo
- Survivorship bias measurement — requires delisted ticker registry
- API uptime / operational reliability metrics

---

## Progress

- [ ] Step 1 — Create feature branch
- [ ] Step 2 — Write migration `20260314_001_create_ops_silver_quality_metrics.sql`
- [ ] Step 3 — Implement `SilverQualityCheckRegistry` (SQL check definitions)
- [ ] Step 4 — Implement `SilverQualityService` (orchestrates checks, writes metrics)
- [ ] Step 5 — Implement `SilverQualityRepo` (DuckDB read/write for quality table)
- [ ] Step 6 — Implement CLI `python -m sbfoundation.quality` (scorecard output)
- [ ] Step 7 — Integrate into `SBFoundationAPI._promote_gold()` (runs after Silver)
- [ ] Step 8 — Unit tests for check registry and service
- [ ] Step 9 — Validation (all tiers)

---

## Surprises & Discoveries

*(Update as work proceeds)*

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-03-14 | Store metrics in `ops.silver_quality_metrics`, not Silver | Quality metadata is operational — same pattern as `ops.run_integrity`, `ops.coverage_index` |
| 2026-03-14 | All checks expressed as DuckDB SQL | Per CLAUDE.md constraint 9; pulling Silver tables into Python for row iteration is unacceptable at scale |
| 2026-03-14 | One row per (dataset, check_name, run_date) | Enables trend queries: `WHERE check_name = 'eod_ohlcv_consistency' ORDER BY run_date` |
| 2026-03-14 | Do not extend `ops.coverage_index` | That table is per-file ingestion aggregate; quality metrics are per-dataset SQL assertions |
| 2026-03-14 | Consistency checks are non-fatal | A violation writes a metric row with status='fail'; it does NOT block the Gold build. Gold operates on Silver as-is; quality is observational |
| 2026-03-14 | Completeness computed per-column via INFORMATION_SCHEMA | Avoids hardcoding column lists; survives schema migrations |

---

## Outcomes & Retrospective

*(Filled in upon completion)*

---

## Context and Orientation

### Current State

The Silver layer already has solid operational visibility via:
- `ops.coverage_index` — temporal coverage ratio (actual days / expected days) per dataset
- `ops.file_ingestions` — per-file Bronze/Silver audit (row counts, errors, hashes)
- `ops.run_integrity` — per-layer pass/fail events per run
- `ops.dataset_watermarks` — last successful ingestion date per dataset

What is **missing** is any measurement of the *content quality* of what was written to Silver:
- Are the values internally consistent (OHLCV logic, balance sheet identity)?
- Are key fields populated or riddled with NULLs?
- How stale is each Silver table relative to the expected cadence?

### Key Files

| File | Purpose |
|---|---|
| `src/sbfoundation/coverage/coverage_index_service.py` | Closest existing analog — refresh pattern to follow |
| `src/sbfoundation/ops/infra/duckdb_ops_repo.py` | Ops DuckDB repo — extend or parallel |
| `src/sbfoundation/api.py` | Integration point: call quality service after Silver, before Gold |
| `db/migrations/20260228_001_create_ops_coverage_index.sql` | Schema pattern to follow |
| `db/migrations/20260309_004_create_ops_run_integrity.sql` | Additional pattern reference |
| `config/dataset_keymap.yaml` | Source of truth for Silver table names, key_cols, row_date_col |

### Silver Tables in Scope

| Domain | Silver Table | Type | Key Quality Checks |
|---|---|---|---|
| EOD | `fmp_eod_bulk_price` | timeseries | OHLCV constraints, volume > 0, date gaps |
| EOD | `fmp_company_profile_bulk` | snapshot | Name/ticker nulls, staleness |
| Quarter | `fmp_income_statement_bulk_quarter` | timeseries | Revenue/income sign, NULL rates |
| Quarter | `fmp_balance_sheet_bulk_quarter` | timeseries | Assets = Liabilities + Equity identity |
| Quarter | `fmp_cashflow_bulk_quarter` | timeseries | NULL rates |
| Quarter | `fmp_key_metrics_bulk_quarter` | timeseries | Ratio sanity (P/E > 0, ROE bounds) |
| Annual | `fmp_income_statement_bulk_annual` | timeseries | Revenue/income sign, NULL rates |
| Annual | `fmp_balance_sheet_bulk_annual` | timeseries | Assets = Liabilities + Equity identity |
| Annual | `fmp_cashflow_bulk_annual` | timeseries | NULL rates |
| Annual | `fmp_ratios_bulk_annual` | timeseries | Ratio sanity |
| Economics | `fred_dgs10` | timeseries | Yield range (0–25%), date gaps |
| Economics | `fred_usrecm` | timeseries | Binary value (0 or 1 only) |
| Economics | `fmp_market_risk_premium` | timeseries | Range sanity |

---

## Plan of Work

### Step 1 — Feature Branch

```bash
git checkout -b feature/silver-data-quality
```

### Step 2 — Migration: `ops.silver_quality_metrics`

Create `db/migrations/20260314_001_create_ops_silver_quality_metrics.sql`.

The table stores one row per check execution. Each row records the check name, dimension, affected dataset, pass/fail status, numeric score, and supporting context. This design supports:
- Trend queries: quality over time per dataset
- Dimension rollups: aggregate completeness score across all datasets
- Drill-down: which specific column or rule failed

Schema:

```sql
CREATE TABLE IF NOT EXISTS ops.silver_quality_metrics (
    metric_id        VARCHAR   PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    run_id           VARCHAR   NOT NULL,
    run_date         DATE      NOT NULL,

    -- Dataset identity
    domain           VARCHAR   NOT NULL,
    source           VARCHAR   NOT NULL,
    dataset          VARCHAR   NOT NULL,
    silver_table     VARCHAR   NOT NULL,

    -- Check identity
    dimension        VARCHAR   NOT NULL,  -- 'completeness' | 'consistency' | 'coverage' | 'timeliness'
    check_name       VARCHAR   NOT NULL,  -- e.g. 'null_rate_close' | 'ohlcv_high_gte_close'
    check_scope      VARCHAR,             -- column name, rule name, or NULL if table-level

    -- Result
    status           VARCHAR   NOT NULL,  -- 'pass' | 'fail' | 'warn' | 'skip'
    score            DOUBLE,              -- 0.0–1.0; higher = better quality
    numerator        BIGINT,              -- e.g. null_count or violation_count
    denominator      BIGINT,              -- e.g. total_rows or total_values
    threshold        DOUBLE,             -- pass threshold (0.95 = 95% must be non-null)
    detail           VARCHAR,             -- human-readable description of violation

    checked_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sqm_run_id   ON ops.silver_quality_metrics (run_id);
CREATE INDEX IF NOT EXISTS idx_sqm_dataset  ON ops.silver_quality_metrics (domain, dataset);
CREATE INDEX IF NOT EXISTS idx_sqm_check    ON ops.silver_quality_metrics (check_name);
CREATE INDEX IF NOT EXISTS idx_sqm_status   ON ops.silver_quality_metrics (status);
CREATE INDEX IF NOT EXISTS idx_sqm_run_date ON ops.silver_quality_metrics (run_date);
```

### Step 3 — `SilverQualityCheckRegistry`

Create `src/sbfoundation/quality/check_registry.py`.

This module defines all quality checks as **pure dataclasses** containing the check metadata and a DuckDB SQL template. No execution logic here — the registry is a declarative catalog.

```python
# src/sbfoundation/quality/check_registry.py

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class QualityCheck:
    """Declarative definition of one Silver quality check."""
    domain: str
    source: str
    dataset: str
    silver_table: str          # e.g. 'silver.fmp_eod_bulk_price'
    dimension: str             # 'completeness' | 'consistency' | 'coverage' | 'timeliness'
    check_name: str            # stable identifier, snake_case
    check_scope: str | None    # column name or rule label; None = table-level
    threshold: float           # score below this → 'fail'; above → 'pass'
    sql: str                   # DuckDB SQL returning (numerator BIGINT, denominator BIGINT)
    detail_template: str       # f-string template for human description


def _eod_table() -> str:
    return "silver.fmp_eod_bulk_price"

def _bs_q() -> str:
    return "silver.fmp_balance_sheet_bulk_quarter"

def _bs_a() -> str:
    return "silver.fmp_balance_sheet_bulk_annual"


ALL_CHECKS: list[QualityCheck] = [

    # ── EOD: COMPLETENESS ──────────────────────────────────────────────
    QualityCheck(
        domain="technicals", source="fmp", dataset="eod-bulk-price",
        silver_table=_eod_table(), dimension="completeness",
        check_name="null_rate_close", check_scope="close",
        threshold=0.995,
        sql=f"""
            SELECT
                COUNT(*) FILTER (WHERE close IS NULL) AS numerator,
                COUNT(*) AS denominator
            FROM {_eod_table()}
        """,
        detail_template="{numerator} of {denominator} EOD rows have NULL close price ({pct:.2%})",
    ),
    QualityCheck(
        domain="technicals", source="fmp", dataset="eod-bulk-price",
        silver_table=_eod_table(), dimension="completeness",
        check_name="null_rate_volume", check_scope="volume",
        threshold=0.990,
        sql=f"""
            SELECT
                COUNT(*) FILTER (WHERE volume IS NULL) AS numerator,
                COUNT(*) AS denominator
            FROM {_eod_table()}
        """,
        detail_template="{numerator} of {denominator} EOD rows have NULL volume ({pct:.2%})",
    ),

    # ── EOD: CONSISTENCY ───────────────────────────────────────────────
    QualityCheck(
        domain="technicals", source="fmp", dataset="eod-bulk-price",
        silver_table=_eod_table(), dimension="consistency",
        check_name="ohlcv_high_gte_open_close", check_scope="high",
        threshold=0.999,
        sql=f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE high IS NOT NULL AND open IS NOT NULL AND close IS NOT NULL
                      AND high < GREATEST(open, close)
                ) AS numerator,
                COUNT(*) FILTER (
                    WHERE high IS NOT NULL AND open IS NOT NULL AND close IS NOT NULL
                ) AS denominator
            FROM {_eod_table()}
        """,
        detail_template="{numerator} rows violate high >= max(open,close) ({pct:.3%} violation rate)",
    ),
    QualityCheck(
        domain="technicals", source="fmp", dataset="eod-bulk-price",
        silver_table=_eod_table(), dimension="consistency",
        check_name="ohlcv_low_lte_open_close", check_scope="low",
        threshold=0.999,
        sql=f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE low IS NOT NULL AND open IS NOT NULL AND close IS NOT NULL
                      AND low > LEAST(open, close)
                ) AS numerator,
                COUNT(*) FILTER (
                    WHERE low IS NOT NULL AND open IS NOT NULL AND close IS NOT NULL
                ) AS denominator
            FROM {_eod_table()}
        """,
        detail_template="{numerator} rows violate low <= min(open,close) ({pct:.3%} violation rate)",
    ),
    QualityCheck(
        domain="technicals", source="fmp", dataset="eod-bulk-price",
        silver_table=_eod_table(), dimension="consistency",
        check_name="ohlcv_positive_prices", check_scope="close",
        threshold=0.9999,
        sql=f"""
            SELECT
                COUNT(*) FILTER (WHERE close IS NOT NULL AND close <= 0) AS numerator,
                COUNT(*) FILTER (WHERE close IS NOT NULL) AS denominator
            FROM {_eod_table()}
        """,
        detail_template="{numerator} rows have non-positive close price",
    ),
    QualityCheck(
        domain="technicals", source="fmp", dataset="eod-bulk-price",
        silver_table=_eod_table(), dimension="consistency",
        check_name="ohlcv_positive_volume", check_scope="volume",
        threshold=0.98,
        sql=f"""
            SELECT
                COUNT(*) FILTER (WHERE volume IS NOT NULL AND volume < 0) AS numerator,
                COUNT(*) FILTER (WHERE volume IS NOT NULL) AS denominator
            FROM {_eod_table()}
        """,
        detail_template="{numerator} rows have negative volume",
    ),

    # ── EOD: TIMELINESS ────────────────────────────────────────────────
    QualityCheck(
        domain="technicals", source="fmp", dataset="eod-bulk-price",
        silver_table=_eod_table(), dimension="timeliness",
        check_name="eod_max_date_staleness", check_scope=None,
        threshold=0.0,   # denominator=age_days; score = 1/(1+age); threshold unused (pass if age <= 3)
        sql=f"""
            SELECT
                DATEDIFF('day', MAX(date), CURRENT_DATE) AS numerator,
                1 AS denominator
            FROM {_eod_table()}
        """,
        detail_template="Most recent EOD date is {numerator} days old",
    ),

    # ── BALANCE SHEET QUARTERLY: CONSISTENCY ───────────────────────────
    QualityCheck(
        domain="fundamentals", source="fmp", dataset="balance-sheet-bulk-quarter",
        silver_table=_bs_q(), dimension="consistency",
        check_name="balance_sheet_identity_quarter", check_scope="assets",
        threshold=0.95,
        sql=f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE total_assets IS NOT NULL
                      AND total_liabilities IS NOT NULL
                      AND total_stockholders_equity IS NOT NULL
                      AND ABS(total_assets - (total_liabilities + total_stockholders_equity))
                          / NULLIF(total_assets, 0) > 0.01
                ) AS numerator,
                COUNT(*) FILTER (
                    WHERE total_assets IS NOT NULL
                      AND total_liabilities IS NOT NULL
                      AND total_stockholders_equity IS NOT NULL
                      AND total_assets != 0
                ) AS denominator
            FROM {_bs_q()}
        """,
        detail_template="{numerator} quarterly balance sheets violate assets = liabilities + equity (>1% deviation)",
    ),

    # ── BALANCE SHEET ANNUAL: CONSISTENCY ──────────────────────────────
    QualityCheck(
        domain="fundamentals", source="fmp", dataset="balance-sheet-bulk-annual",
        silver_table=_bs_a(), dimension="consistency",
        check_name="balance_sheet_identity_annual", check_scope="assets",
        threshold=0.95,
        sql=f"""
            SELECT
                COUNT(*) FILTER (
                    WHERE total_assets IS NOT NULL
                      AND total_liabilities IS NOT NULL
                      AND total_stockholders_equity IS NOT NULL
                      AND ABS(total_assets - (total_liabilities + total_stockholders_equity))
                          / NULLIF(total_assets, 0) > 0.01
                ) AS numerator,
                COUNT(*) FILTER (
                    WHERE total_assets IS NOT NULL
                      AND total_liabilities IS NOT NULL
                      AND total_stockholders_equity IS NOT NULL
                      AND total_assets != 0
                ) AS denominator
            FROM {_bs_a()}
        """,
        detail_template="{numerator} annual balance sheets violate assets = liabilities + equity (>1% deviation)",
    ),

    # ── FRED DGS10: CONSISTENCY ────────────────────────────────────────
    QualityCheck(
        domain="economics", source="fred", dataset="dgs10",
        silver_table="silver.fred_dgs10", dimension="consistency",
        check_name="dgs10_yield_range", check_scope="value",
        threshold=0.999,
        sql="""
            SELECT
                COUNT(*) FILTER (WHERE value IS NOT NULL AND (value < 0 OR value > 25)) AS numerator,
                COUNT(*) FILTER (WHERE value IS NOT NULL) AS denominator
            FROM silver.fred_dgs10
        """,
        detail_template="{numerator} DGS10 rows have yield outside [0, 25]%",
    ),

    # ── FRED USRECM: CONSISTENCY ───────────────────────────────────────
    QualityCheck(
        domain="economics", source="fred", dataset="usrecm",
        silver_table="silver.fred_usrecm", dimension="consistency",
        check_name="usrecm_binary_values", check_scope="value",
        threshold=1.0,
        sql="""
            SELECT
                COUNT(*) FILTER (WHERE value IS NOT NULL AND value NOT IN (0, 1)) AS numerator,
                COUNT(*) FILTER (WHERE value IS NOT NULL) AS denominator
            FROM silver.fred_usrecm
        """,
        detail_template="{numerator} USRECM rows have non-binary value (expected 0 or 1 only)",
    ),

    # ── COMPANY PROFILE: COMPLETENESS ─────────────────────────────────
    QualityCheck(
        domain="company", source="fmp", dataset="eod-bulk-company-profile",
        silver_table="silver.fmp_company_profile_bulk", dimension="completeness",
        check_name="null_rate_company_name", check_scope="company_name",
        threshold=0.95,
        sql="""
            SELECT
                COUNT(*) FILTER (WHERE company_name IS NULL OR company_name = '') AS numerator,
                COUNT(*) AS denominator
            FROM silver.fmp_company_profile_bulk
        """,
        detail_template="{numerator} company profiles have missing company_name ({pct:.1%})",
    ),

    # ── INCOME STATEMENT ANNUAL: COMPLETENESS ─────────────────────────
    QualityCheck(
        domain="fundamentals", source="fmp", dataset="income-statement-bulk-annual",
        silver_table="silver.fmp_income_statement_bulk_annual", dimension="completeness",
        check_name="null_rate_revenue_annual", check_scope="revenue",
        threshold=0.90,
        sql="""
            SELECT
                COUNT(*) FILTER (WHERE revenue IS NULL) AS numerator,
                COUNT(*) AS denominator
            FROM silver.fmp_income_statement_bulk_annual
        """,
        detail_template="{numerator} annual income rows have NULL revenue ({pct:.1%})",
    ),

    # ── INCOME STATEMENT ANNUAL: CONSISTENCY ──────────────────────────
    QualityCheck(
        domain="fundamentals", source="fmp", dataset="income-statement-bulk-annual",
        silver_table="silver.fmp_income_statement_bulk_annual", dimension="consistency",
        check_name="income_net_income_lte_revenue", check_scope="net_income",
        threshold=0.95,
        sql="""
            SELECT
                COUNT(*) FILTER (
                    WHERE revenue IS NOT NULL AND net_income IS NOT NULL
                      AND revenue > 0 AND net_income > revenue
                ) AS numerator,
                COUNT(*) FILTER (
                    WHERE revenue IS NOT NULL AND net_income IS NOT NULL AND revenue > 0
                ) AS denominator
            FROM silver.fmp_income_statement_bulk_annual
        """,
        detail_template="{numerator} annual rows have net_income > revenue (unusual; check for holding companies)",
    ),

    # ── COVERAGE: EOD INSTRUMENT COUNT ────────────────────────────────
    QualityCheck(
        domain="technicals", source="fmp", dataset="eod-bulk-price",
        silver_table=_eod_table(), dimension="coverage",
        check_name="eod_instrument_count", check_scope=None,
        threshold=0.0,   # informational: score = distinct_symbols / 5300
        sql=f"""
            SELECT COUNT(DISTINCT symbol) AS numerator, 5300 AS denominator
            FROM {_eod_table()}
        """,
        detail_template="{numerator} distinct symbols in EOD Silver (expected ~{denominator})",
    ),
]
```

### Step 4 — `SilverQualityService`

Create `src/sbfoundation/quality/silver_quality_service.py`.

This service iterates over `ALL_CHECKS`, executes each SQL against DuckDB, computes the score, assigns pass/fail/warn, and writes metric rows via `SilverQualityRepo`.

```python
# src/sbfoundation/quality/silver_quality_service.py

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import duckdb

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.quality.check_registry import ALL_CHECKS, QualityCheck
from sbfoundation.quality.silver_quality_repo import SilverQualityRepo


class SilverQualityService:
    """Executes registered Silver quality checks and persists results."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        repo: SilverQualityRepo | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._conn = conn
        self._repo = repo or SilverQualityRepo(conn)
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)

    def run(self, *, run_id: str, run_date: date) -> list[dict[str, Any]]:
        """Execute all registered checks and write results to ops.silver_quality_metrics.

        Returns list of metric rows written.
        """
        self._logger.log_section(run_id, "Silver data quality checks")
        rows: list[dict[str, Any]] = []

        for check in ALL_CHECKS:
            row = self._execute_check(check, run_id=run_id, run_date=run_date)
            rows.append(row)
            level = "warning" if row["status"] == "fail" else "info"
            getattr(self._logger, level)(
                "[%s] %s → %s (score=%.4f)",
                check.dimension.upper(), check.check_name, row["status"], row["score"] or 0.0,
                run_id=run_id,
            )

        self._repo.upsert_metrics(rows)
        fail_count = sum(1 for r in rows if r["status"] == "fail")
        self._logger.info(
            "Quality checks complete: %d/%d passed", len(rows) - fail_count, len(rows),
            run_id=run_id,
        )
        return rows

    def _execute_check(
        self,
        check: QualityCheck,
        *,
        run_id: str,
        run_date: date,
    ) -> dict[str, Any]:
        """Run one SQL check and return a metric row dict."""
        try:
            result = self._conn.execute(check.sql.strip()).fetchone()
            numerator = int(result[0] or 0)
            denominator = int(result[1] or 0)

            if denominator == 0:
                score = 1.0  # no data to violate
                status = "skip"
                pct = 0.0
            else:
                # For completeness/consistency: score = 1 - (violation_rate)
                # For timeliness (eod_max_date_staleness): special handling below
                if check.check_name == "eod_max_date_staleness":
                    age_days = numerator
                    score = 1.0 / (1.0 + age_days)  # decay: age=0 → 1.0, age=3 → 0.25
                    status = "pass" if age_days <= 3 else ("warn" if age_days <= 7 else "fail")
                    pct = float(age_days)
                elif check.dimension in ("coverage",):
                    score = min(numerator / denominator, 1.0)
                    status = "pass" if score >= check.threshold else "warn"
                    pct = score
                else:
                    violation_rate = numerator / denominator
                    score = 1.0 - violation_rate
                    status = "pass" if score >= check.threshold else "fail"
                    pct = violation_rate

            detail = check.detail_template.format(
                numerator=numerator, denominator=denominator, pct=pct
            )
        except Exception as exc:
            numerator = 0
            denominator = 0
            score = 0.0
            status = "skip"
            detail = f"Check failed to execute: {exc}"

        return {
            "metric_id": str(uuid.uuid4()),
            "run_id": run_id,
            "run_date": run_date,
            "domain": check.domain,
            "source": check.source,
            "dataset": check.dataset,
            "silver_table": check.silver_table,
            "dimension": check.dimension,
            "check_name": check.check_name,
            "check_scope": check.check_scope,
            "status": status,
            "score": round(score, 6),
            "numerator": numerator,
            "denominator": denominator,
            "threshold": check.threshold,
            "detail": detail,
            "checked_at": datetime.now(tz=timezone.utc),
        }
```

### Step 5 — `SilverQualityRepo`

Create `src/sbfoundation/quality/silver_quality_repo.py`.

Thin DuckDB write layer — mirrors the pattern of `DuckDbOpsRepo`.

```python
# src/sbfoundation/quality/silver_quality_repo.py

from __future__ import annotations

from typing import Any

import duckdb


class SilverQualityRepo:
    """DuckDB read/write for ops.silver_quality_metrics."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def upsert_metrics(self, rows: list[dict[str, Any]]) -> int:
        """Insert metric rows (no update — each run produces new rows by metric_id)."""
        if not rows:
            return 0
        placeholders = ", ".join(["(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"] * len(rows))
        values: list[Any] = []
        for r in rows:
            values.extend([
                r["metric_id"], r["run_id"], r["run_date"],
                r["domain"], r["source"], r["dataset"], r["silver_table"],
                r["dimension"], r["check_name"], r["check_scope"],
                r["status"], r["score"], r["numerator"], r["denominator"],
                r["threshold"], r["detail"], r["checked_at"],
            ])
        self._conn.execute(f"""
            INSERT INTO ops.silver_quality_metrics
            (metric_id, run_id, run_date, domain, source, dataset, silver_table,
             dimension, check_name, check_scope,
             status, score, numerator, denominator, threshold, detail, checked_at)
            VALUES {placeholders}
        """, values)
        return len(rows)

    def fetch_latest_by_dataset(self) -> list[dict[str, Any]]:
        """Return the most recent metric row per (dataset, check_name)."""
        return self._conn.execute("""
            SELECT DISTINCT ON (dataset, check_name)
                *
            FROM ops.silver_quality_metrics
            ORDER BY dataset, check_name, run_date DESC
        """).fetchdf().to_dict("records")

    def fetch_summary(self) -> list[dict[str, Any]]:
        """Return aggregate quality scores per (dataset, dimension)."""
        return self._conn.execute("""
            SELECT
                dataset,
                dimension,
                COUNT(*) AS total_checks,
                SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) AS passed,
                SUM(CASE WHEN status = 'fail' THEN 1 ELSE 0 END) AS failed,
                AVG(score) AS avg_score,
                MAX(run_date) AS last_run_date
            FROM ops.silver_quality_metrics
            GROUP BY dataset, dimension
            ORDER BY dataset, dimension
        """).fetchdf().to_dict("records")
```

### Step 6 — CLI Module

Create `src/sbfoundation/quality/__init__.py` and `src/sbfoundation/quality/__main__.py`.

`__main__.py` opens the DuckDB connection, runs quality checks on the current Silver state, and prints a formatted scorecard.

```python
# src/sbfoundation/quality/__main__.py
"""
Entry point: python -m sbfoundation.quality

Runs all Silver quality checks against the current DuckDB and prints a
scorecard. Does NOT trigger Bronze or Silver ingestion.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import duckdb

from sbfoundation.quality.check_registry import ALL_CHECKS
from sbfoundation.quality.silver_quality_repo import SilverQualityRepo
from sbfoundation.quality.silver_quality_service import SilverQualityService
from sbfoundation.settings import Settings


def _open_conn() -> duckdb.DuckDBPyConnection:
    settings = Settings()
    db_path = Path(settings.DUCKDB_FOLDER) / "sbfoundation.duckdb"
    return duckdb.connect(str(db_path))


def main() -> None:
    run_id = f"quality-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    today = date.today()

    conn = _open_conn()
    svc = SilverQualityService(conn)
    rows = svc.run(run_id=run_id, run_date=today)

    # Print scorecard
    print(f"\n{'='*70}")
    print(f"  SILVER DATA QUALITY SCORECARD — {today}")
    print(f"{'='*70}")
    print(f"{'Check':<42} {'Dim':<14} {'Status':<7} {'Score':>6}")
    print(f"{'-'*42} {'-'*14} {'-'*7} {'-'*6}")
    for r in sorted(rows, key=lambda x: (x["dimension"], x["check_name"])):
        symbol = "✓" if r["status"] == "pass" else ("!" if r["status"] == "warn" else "✗")
        print(f"{symbol} {r['check_name']:<40} {r['dimension']:<14} {r['status']:<7} {r['score']:>6.4f}")
    print(f"{'='*70}")

    fail_count = sum(1 for r in rows if r["status"] == "fail")
    print(f"\n{len(rows) - fail_count}/{len(rows)} checks passed")
    if fail_count:
        print("\nFailures:")
        for r in rows:
            if r["status"] == "fail":
                print(f"  [{r['check_name']}] {r['detail']}")

    conn.close()
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
```

### Step 7 — Pipeline Integration

Modify `src/sbfoundation/api.py` to call `SilverQualityService.run()` after Silver promotion completes and before Gold build. Add to `_promote_gold()` (or a new `_check_silver_quality()` method):

**Location**: `api.py` in `SBFoundationAPI`, after `silver_service.promote()` and before `GoldDimService.build()`.

**Change**: In the `run()` method, after silver promotion and before gold, add:

```python
if command.enable_silver and command.enable_quality:
    from sbfoundation.quality.silver_quality_service import SilverQualityService
    quality_svc = SilverQualityService(self._conn)
    quality_svc.run(run_id=run.run_id, run_date=date.today())
```

Add `enable_quality: bool = True` field to `RunCommand`.

### Step 8 — Unit Tests

Create `tests/unit/quality/test_check_registry.py`:
- Assert all checks have non-empty SQL, check_name, threshold in [0,1]
- Assert no duplicate (silver_table, check_name) pairs

Create `tests/unit/quality/test_silver_quality_service.py`:
- Use an in-memory DuckDB with a minimal Silver table fixture
- Assert pass/fail status matches expected for known-good and known-bad data

---

## Concrete Steps

```bash
# Step 1: Create branch
git checkout -b feature/silver-data-quality

# Step 2: Migration
# Write db/migrations/20260314_001_create_ops_silver_quality_metrics.sql
# (content above)

# Step 3-6: Create Python files
# Write src/sbfoundation/quality/__init__.py  (empty)
# Write src/sbfoundation/quality/check_registry.py
# Write src/sbfoundation/quality/silver_quality_service.py
# Write src/sbfoundation/quality/silver_quality_repo.py
# Write src/sbfoundation/quality/__main__.py

# Step 7: Integrate into api.py
# Edit RunCommand to add enable_quality: bool = True
# Edit SBFoundationAPI.run() to call SilverQualityService after silver

# Step 8: Tests
# Write tests/unit/quality/test_check_registry.py
# Write tests/unit/quality/test_silver_quality_service.py

# Apply migration
python -m sbfoundation.maintenance

# Run quality standalone
python -m sbfoundation.quality

# Run full pipeline with quality enabled (default)
python -c "
from sbfoundation.api import SBFoundationAPI, RunCommand
api = SBFoundationAPI()
api.run(RunCommand(domain='technicals', enable_bronze=False, enable_silver=False, enable_gold=False, enable_quality=True))
"
```

---

## Validation and Acceptance

### Tier 1 — Quick checks (no DB or network)

```bash
# 1a. Import sanity
python -c "from sbfoundation.quality.check_registry import ALL_CHECKS; print(f'{len(ALL_CHECKS)} checks loaded')"
# Expected: "N checks loaded" (no ImportError)

# 1b. No duplicate check names
python -c "
from sbfoundation.quality.check_registry import ALL_CHECKS
names = [(c.silver_table, c.check_name) for c in ALL_CHECKS]
dups = [n for n in names if names.count(n) > 1]
assert not dups, f'Duplicate checks: {dups}'
print('No duplicates')
"
# Expected: "No duplicates"

# 1c. All thresholds in valid range
python -c "
from sbfoundation.quality.check_registry import ALL_CHECKS
bad = [c.check_name for c in ALL_CHECKS if not (0.0 <= c.threshold <= 1.0)]
assert not bad, f'Bad thresholds: {bad}'
print('All thresholds valid')
"
# Expected: "All thresholds valid"

# 1d. Unit tests
pytest tests/unit/quality/ -v
# Expected: all pass, no errors
```

### Tier 2 — DB checks (requires local DuckDB; no API)

```python
import duckdb

# 2a. Migration ran — table exists
conn = duckdb.connect("path/to/sbfoundation.duckdb")
result = conn.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'ops' AND table_name = 'silver_quality_metrics'
    ORDER BY ordinal_position
""").fetchall()
print([r[0] for r in result])
# Expected: ['metric_id', 'run_id', 'run_date', 'domain', 'source', 'dataset', ...]

# 2b. Run quality checks against live Silver and confirm rows are written
from sbfoundation.quality.silver_quality_service import SilverQualityService
svc = SilverQualityService(conn)
rows = svc.run(run_id="test-001", run_date=date.today())
print(f"{len(rows)} metric rows produced")
# Expected: len(rows) == len(ALL_CHECKS), all rows in ops.silver_quality_metrics

# 2c. Re-running is non-destructive (new metric_ids, old rows preserved)
rows2 = svc.run(run_id="test-002", run_date=date.today())
total = conn.execute("SELECT COUNT(*) FROM ops.silver_quality_metrics").fetchone()[0]
assert total >= len(rows) + len(rows2)
print("Re-run preserved prior rows")
```

### Tier 3 — Integration / dry-run check

```bash
# Run quality module standalone against real Silver data
python -m sbfoundation.quality
```

Expected output (format):
```
======================================================================
  SILVER DATA QUALITY SCORECARD — 2026-03-14
======================================================================
Check                                      Dim            Status  Score
------------------------------------------ -------------- ------- ------
✓ balance_sheet_identity_annual            consistency    pass    0.9987
✓ balance_sheet_identity_quarter           consistency    pass    0.9981
...
✗ null_rate_revenue_annual                 completeness   fail    0.8712
======================================================================
14/15 checks passed
```

- No Python exceptions
- All checks produce status in {'pass', 'fail', 'warn', 'skip'}
- Rows present in `ops.silver_quality_metrics` after run

### Tier 4 — Post-live-run checks

1. After a full pipeline run (`enable_quality=True`), `ops.silver_quality_metrics` contains rows with the current `run_id`.
2. Running the same pipeline twice on the same day produces two sets of rows (different `metric_id`s, same `run_date`).
3. `python -m sbfoundation.quality` exits with code 0 if all checks pass; code 1 if any fail.
4. EOD OHLCV consistency checks pass at ≥ 99.9% for the full 30-year Silver history.
5. Balance sheet identity checks pass at ≥ 95% (accounting for holding companies and financial firms where the identity formula may not directly apply).

---

## Idempotence and Recovery

- Each quality run inserts new rows with unique `metric_id` (UUID). No UPDATE or DELETE of prior rows. Re-running is always safe and additive.
- If a check's SQL fails (Silver table does not exist yet), the check is marked `status='skip'` with `detail` describing the error. No exception propagates.
- The quality step is a separate, non-blocking phase. A quality failure does NOT prevent the Gold build from running. Set `enable_quality=False` in `RunCommand` to skip entirely.
- To roll back: simply `DELETE FROM ops.silver_quality_metrics WHERE run_id = '<run_id>'` — no other state is affected.

---

## Artifacts and Notes

*(Filled in upon completion — include sample output, row counts, any check failures and resolutions)*

---

## Interfaces and Dependencies

### New Files

| File | Purpose |
|---|---|
| `db/migrations/20260314_001_create_ops_silver_quality_metrics.sql` | Table DDL |
| `src/sbfoundation/quality/__init__.py` | Package marker |
| `src/sbfoundation/quality/check_registry.py` | Declarative check catalog |
| `src/sbfoundation/quality/silver_quality_service.py` | Executes checks, writes metrics |
| `src/sbfoundation/quality/silver_quality_repo.py` | DuckDB read/write |
| `src/sbfoundation/quality/__main__.py` | CLI scorecard |
| `tests/unit/quality/test_check_registry.py` | Registry invariant tests |
| `tests/unit/quality/test_silver_quality_service.py` | Service unit tests |

### Modified Files

| File | Change |
|---|---|
| `src/sbfoundation/api.py` | Add `enable_quality: bool = True` to `RunCommand`; call `SilverQualityService` after silver promotion |

### Library Dependencies

- `duckdb` — already a project dependency; no new packages required
- `uuid` — stdlib
- All DuckDB SQL executes via `duckdb.DuckDBPyConnection`; no pandas required for quality metrics

### Quality Check SQL Contracts

Each `QualityCheck.sql` must return exactly two columns:
- `numerator BIGINT` — count of violations (or relevant numerator for score computation)
- `denominator BIGINT` — total eligible rows

Score is computed in `SilverQualityService._execute_check()`:
- Completeness/Consistency: `score = 1 - (numerator / denominator)`
- Coverage: `score = numerator / denominator` (higher = more coverage)
- Timeliness (`eod_max_date_staleness`): `score = 1 / (1 + age_days)` (age in numerator, denominator=1)
