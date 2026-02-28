from __future__ import annotations

import datetime
from typing import Any

import duckdb

from sbfoundation.dataset.models.dataset_identity import DatasetIdentity
from sbfoundation.dataset.models.dataset_watermark import DatasetWatermark
from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.ops.dtos.file_injestion import DatasetInjestion


class DuckDbOpsRepo:
    """Aggregate root for the ops metadata stored in `ops.file_ingestions`.  Maintaining a single run/file row prevents Bronze duplication."""

    def __init__(self, logger: SBLogger | None = None, bootstrap: DuckDbBootstrap | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None
    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    def upsert_file_ingestion(self, ingestion: DatasetInjestion) -> None:
        sql = (
            "MERGE INTO ops.file_ingestions AS target "
            "USING ("
            "SELECT ? AS run_id, ? AS file_id, ? AS domain, ? AS source, ? AS dataset, ? AS discriminator, "
            "? AS ticker, ? AS bronze_filename, ? AS bronze_error, ? AS bronze_rows, ? AS bronze_from_date, "
            "? AS bronze_to_date, ? AS bronze_injest_start_time, ? AS bronze_injest_end_time, ? AS bronze_can_promote, "
            "? AS bronze_payload_hash, ? AS silver_tablename, ? AS silver_errors, "
            "? AS silver_rows_created, ? AS silver_rows_updated, ? AS silver_rows_failed, ? AS silver_from_date, "
            "? AS silver_to_date, ? AS silver_injest_start_time, ? AS silver_injest_end_time, ? AS silver_can_promote"
            ") AS src "
            "ON target.run_id = src.run_id AND target.file_id = src.file_id "
            "WHEN MATCHED THEN UPDATE SET "
            "domain = src.domain, source = src.source, dataset = src.dataset, discriminator = src.discriminator, ticker = src.ticker, "
            "bronze_filename = src.bronze_filename, bronze_error = src.bronze_error, bronze_rows = src.bronze_rows, "
            "bronze_from_date = src.bronze_from_date, bronze_to_date = src.bronze_to_date, "
            "bronze_injest_start_time = src.bronze_injest_start_time, bronze_injest_end_time = src.bronze_injest_end_time, "
            "bronze_can_promote = src.bronze_can_promote, bronze_payload_hash = src.bronze_payload_hash, "
            "silver_tablename = src.silver_tablename, "
            "silver_errors = src.silver_errors, silver_rows_created = src.silver_rows_created, "
            "silver_rows_updated = src.silver_rows_updated, silver_rows_failed = src.silver_rows_failed, "
            "silver_from_date = src.silver_from_date, silver_to_date = src.silver_to_date, "
            "silver_injest_start_time = src.silver_injest_start_time, silver_injest_end_time = src.silver_injest_end_time, "
            "silver_can_promote = src.silver_can_promote "
            "WHEN NOT MATCHED THEN INSERT ("
            "run_id, file_id, domain, source, dataset, discriminator, ticker, "
            "bronze_filename, bronze_error, bronze_rows, bronze_from_date, bronze_to_date, "
            "bronze_injest_start_time, bronze_injest_end_time, bronze_can_promote, bronze_payload_hash, "
            "silver_tablename, silver_errors, silver_rows_created, silver_rows_updated, "
            "silver_rows_failed, silver_from_date, silver_to_date, silver_injest_start_time, silver_injest_end_time, "
            "silver_can_promote"
            ") VALUES ("
            "src.run_id, src.file_id, src.domain, src.source, src.dataset, src.discriminator, src.ticker, "
            "src.bronze_filename, src.bronze_error, src.bronze_rows, src.bronze_from_date, src.bronze_to_date, "
            "src.bronze_injest_start_time, src.bronze_injest_end_time, src.bronze_can_promote, src.bronze_payload_hash, "
            "src.silver_tablename, src.silver_errors, src.silver_rows_created, "
            "src.silver_rows_updated, src.silver_rows_failed, src.silver_from_date, src.silver_to_date, "
            "src.silver_injest_start_time, src.silver_injest_end_time, src.silver_can_promote"
            ")"
        )
        params = [
            ingestion.run_id,
            ingestion.file_id,
            ingestion.domain,
            ingestion.source,
            ingestion.dataset,
            ingestion.discriminator,
            ingestion.ticker,
            ingestion.bronze_filename,
            ingestion.bronze_error,
            ingestion.bronze_rows,
            ingestion.bronze_from_date,
            ingestion.bronze_to_date,
            ingestion.bronze_injest_start_time,
            ingestion.bronze_injest_end_time,
            ingestion.bronze_can_promote,
            ingestion.bronze_payload_hash,
            ingestion.silver_tablename,
            ingestion.silver_errors,
            ingestion.silver_rows_created,
            ingestion.silver_rows_updated,
            ingestion.silver_rows_failed,
            ingestion.silver_from_date,
            ingestion.silver_to_date,
            ingestion.silver_injest_start_time,
            ingestion.silver_injest_end_time,
            ingestion.silver_can_promote,
        ]
        with self._bootstrap.ops_transaction() as conn:
            conn.execute(sql, params)

    def get_latest_bronze_to_date(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> datetime.date | None:
        discriminator_token = discriminator or ""
        ticker_token = ticker or ""
        sql = (
            "SELECT MAX(bronze_to_date) FROM ops.file_ingestions "
            "WHERE domain = ? AND source = ? AND dataset = ? "
            "AND COALESCE(discriminator, '') = ? AND COALESCE(ticker, '') = ?"
        )
        with self._bootstrap.read_connection() as conn:
            row = conn.execute(sql, [domain, source, dataset, discriminator_token, ticker_token]).fetchone()
        return row[0] if row else None

    def get_bulk_ingestion_watermarks(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
    ) -> dict[str, tuple[datetime.datetime | None, datetime.date | None]]:
        """Return ingestion watermarks for all tickers of a dataset in one query.

        Returns a dict keyed by ticker (empty string for global datasets).  Each
        value is (last_successful_ingestion_time, last_bronze_to_date), matching
        the semantics of get_latest_bronze_ingestion_time / get_latest_bronze_to_date
        respectively.  Replaces N per-ticker scans with a single GROUP BY query.
        """
        discriminator_token = discriminator or ""
        sql = (
            "SELECT "
            "    COALESCE(ticker, '') AS ticker, "
            "    MAX(CASE WHEN bronze_error IS NULL THEN bronze_injest_start_time END) AS last_ingestion_time, "
            "    MAX(bronze_to_date) AS last_to_date "
            "FROM ops.file_ingestions "
            "WHERE domain = ? AND source = ? AND dataset = ? AND COALESCE(discriminator, '') = ? "
            "GROUP BY COALESCE(ticker, '')"
        )
        with self._bootstrap.read_connection() as conn:
            rows = conn.execute(sql, [domain, source, dataset, discriminator_token]).fetchall()
        return {row[0]: (row[1], row[2]) for row in rows}

    def get_latest_bronze_ingestion_time(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> datetime.datetime | None:
        """Return the timestamp of the most recent successful bronze ingestion."""
        discriminator_token = discriminator or ""
        ticker_token = ticker or ""
        sql = (
            "SELECT MAX(bronze_injest_start_time) FROM ops.file_ingestions "
            "WHERE domain = ? AND source = ? AND dataset = ? "
            "AND COALESCE(discriminator, '') = ? AND COALESCE(ticker, '') = ? "
            "AND bronze_error IS NULL"
        )
        with self._bootstrap.read_connection() as conn:
            row = conn.execute(sql, [domain, source, dataset, discriminator_token, ticker_token]).fetchone()
        return row[0] if row else None

    def list_promotable_file_ingestions(self) -> list[DatasetInjestion]:
        sql = (
            "SELECT * FROM ops.file_ingestions "
            "WHERE bronze_can_promote = TRUE AND (silver_injest_start_time IS NULL OR COALESCE(silver_rows_created, 0) = 0) "
            "ORDER BY bronze_injest_start_time NULLS LAST, bronze_to_date DESC"
        )
        rows = self._fetch_dicts(sql, [])
        return [DatasetInjestion.from_row(row) for row in rows]

    def _fetch_dicts(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        with self._bootstrap.read_connection() as conn:
            cursor = conn.execute(sql, params)
            cols = [desc[0] for desc in cursor.description] if cursor.description else []
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_latest_silver_to_date(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> datetime.date | None:
        discriminator_token = discriminator or ""
        ticker_token = ticker or ""
        sql = (
            "SELECT MAX(silver_to_date) FROM ops.file_ingestions "
            "WHERE domain = ? AND source = ? AND dataset = ? "
            "AND COALESCE(discriminator, '') = ? AND COALESCE(ticker, '') = ?"
        )
        with self._bootstrap.read_connection() as conn:
            row = conn.execute(sql, [domain, source, dataset, discriminator_token, ticker_token]).fetchone()
        return row[0] if row else None

    def get_latest_silver_to_date_for_dataset(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
    ) -> datetime.date | None:
        """Return the MAX silver_to_date for a dataset across all discriminators and tickers.

        Used by date-loop ingestion (e.g. market-sector-performance) where each calendar
        day is stored under its own discriminator.  Filtering by discriminator would never
        match, so we intentionally ignore it here.
        """
        sql = (
            "SELECT MAX(silver_to_date) FROM ops.file_ingestions "
            "WHERE domain = ? AND source = ? AND dataset = ? "
            "AND silver_to_date IS NOT NULL"
        )
        with self._bootstrap.read_connection() as conn:
            row = conn.execute(sql, [domain, source, dataset]).fetchone()
        return row[0] if row else None

    def get_tickers_with_bronze_error(self, *, dataset: str, error_contains: str) -> set[str]:
        """Return distinct tickers that have a bronze_error containing the given substring."""
        sql = (
            "SELECT DISTINCT ticker FROM ops.file_ingestions "
            "WHERE dataset = ? AND bronze_error IS NOT NULL "
            "AND bronze_error LIKE ? AND ticker IS NOT NULL"
        )
        with self._bootstrap.read_connection() as conn:
            rows = conn.execute(sql, [dataset, f"%{error_contains}%"]).fetchall()
        return {row[0] for row in rows if row[0]}

    def load_input_watermarks(self, conn: duckdb.DuckDBPyConnection, *, datasets: set[str]) -> list[str]:
        params: list[object] = []
        where = ""
        if datasets:
            placeholders = ", ".join("?" for _ in datasets)
            where = f"WHERE dataset IN ({placeholders})"
            params.extend(sorted(datasets))

        sql = (
            "SELECT domain, source, dataset, discriminator, ticker, "
            "MAX(silver_from_date) AS coverage_from_date, MAX(silver_to_date) AS coverage_to_date "
            "FROM ops.file_ingestions "
            f"{where} "
            "GROUP BY domain, source, dataset, discriminator, ticker"
        )
        rows = conn.execute(sql, params).fetchall()
        watermarks: list[str] = []
        for row in rows:
            identity = DatasetIdentity(
                domain=row[0],
                source=row[1],
                dataset=row[2],
                discriminator=row[3] or "",
                ticker=row[4] or "",
            )
            watermark = DatasetWatermark(identity=identity, coverage_from_date=row[5], coverage_to_date=row[6])
            watermarks.append(watermark.serialize())
        return watermarks

    def load_file_ingestions(
        self,
        *,
        run_id: str,
        identity: DatasetIdentity,
        ticker_scope: str,
    ) -> list[DatasetInjestion]:
        discriminator_token = identity.discriminator or ""
        ticker_token = identity.ticker or ""
        params: list[Any] = [run_id, identity.domain, identity.source, identity.dataset, discriminator_token]
        where = "run_id = ? AND domain = ? AND source = ? AND dataset = ? " "AND COALESCE(discriminator, '') = ?"
        if ticker_scope == "global":
            where += " AND COALESCE(ticker, '') = ''"
        elif ticker_scope == "per_ticker":
            if ticker_token:
                where += " AND COALESCE(ticker, '') = ?"
                params.append(ticker_token)
            else:
                where += " AND COALESCE(ticker, '') <> ''"
        elif ticker_token:
            where += " AND COALESCE(ticker, '') = ?"
            params.append(ticker_token)

        sql = f"SELECT * FROM ops.file_ingestions WHERE {where}"
        rows = self._fetch_dicts(sql, params)
        return [DatasetInjestion.from_row(row) for row in rows]

    def get_earliest_bronze_from_date(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> datetime.date | None:
        """Return MIN(bronze_from_date) for successful ingestions of this identity."""
        sql = (
            "SELECT MIN(bronze_from_date) FROM ops.file_ingestions "
            "WHERE domain = ? AND source = ? AND dataset = ? "
            "AND COALESCE(discriminator, '') = ? AND COALESCE(ticker, '') = ? "
            "AND bronze_error IS NULL"
        )
        with self._bootstrap.read_connection() as conn:
            row = conn.execute(sql, [domain, source, dataset, discriminator, ticker]).fetchone()
        return row[0] if row and row[0] else None

    def get_backfill_floor_date(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> datetime.date | None:
        """Return backfill_floor_date from ops.dataset_watermarks (None if row absent)."""
        sql = (
            "SELECT backfill_floor_date FROM ops.dataset_watermarks "
            "WHERE domain = ? AND source = ? AND dataset = ? "
            "AND discriminator = ? AND ticker = ?"
        )
        with self._bootstrap.read_connection() as conn:
            row = conn.execute(sql, [domain, source, dataset, discriminator, ticker]).fetchone()
        return row[0] if row and row[0] else None

    def upsert_backfill_floor_date(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
        floor_date: datetime.date,
    ) -> None:
        """UPSERT a backfill_floor_date row into ops.dataset_watermarks."""
        sql = """
            INSERT INTO ops.dataset_watermarks
                (domain, source, dataset, discriminator, ticker, backfill_floor_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (domain, source, dataset, discriminator, ticker)
            DO UPDATE SET backfill_floor_date = EXCLUDED.backfill_floor_date
        """
        with self._bootstrap.ops_transaction() as conn:
            conn.execute(sql, [domain, source, dataset, discriminator, ticker, floor_date])

    # --- COVERAGE INDEX ---#

    _COVERAGE_COLS = (
        "domain", "source", "dataset", "discriminator", "ticker",
        "min_date", "max_date", "coverage_ratio",
        "expected_start_date", "expected_end_date",
        "total_files", "promotable_files", "ingestion_runs",
        "silver_rows_created", "silver_rows_failed",
        "error_count", "error_rate",
        "last_ingested_at", "last_run_id",
        "snapshot_count", "last_snapshot_date", "age_days",
        "is_timeseries", "updated_at",
    )

    def aggregate_file_ingestions_for_coverage(self) -> list[dict[str, Any]]:
        """Return one aggregated row per (domain, source, dataset, discriminator, ticker)."""
        sql = (
            "SELECT "
            "    domain, "
            "    source, "
            "    dataset, "
            "    COALESCE(discriminator, '') AS discriminator, "
            "    COALESCE(ticker, '')        AS ticker, "
            "    MIN(bronze_from_date)       AS min_date, "
            "    MAX(bronze_to_date)         AS max_date, "
            "    COUNT(*)                    AS total_files, "
            "    COUNT(*) FILTER (WHERE bronze_can_promote = TRUE)      AS promotable_files, "
            "    COUNT(DISTINCT run_id)                                  AS ingestion_runs, "
            "    COALESCE(SUM(silver_rows_created), 0)                  AS silver_rows_created, "
            "    COALESCE(SUM(silver_rows_failed), 0)                   AS silver_rows_failed, "
            "    COUNT(*) FILTER (WHERE bronze_error IS NOT NULL)       AS error_count, "
            "    MAX(bronze_injest_start_time)                          AS last_ingested_at, "
            "    MAX(run_id)                                            AS last_run_id "
            "FROM ops.file_ingestions "
            "GROUP BY domain, source, dataset, "
            "         COALESCE(discriminator, ''), COALESCE(ticker, '')"
        )
        return self._fetch_dicts(sql, [])

    def upsert_coverage_index(self, rows: list[dict[str, Any]]) -> int:
        """Replace all coverage index rows in a single transaction. Returns row count.

        Uses a pandas DataFrame so DuckDB can do a single vectorized INSERT
        instead of N individual parametrized statements (executemany is O(N)
        round-trips; DataFrame INSERT is a single scan).
        """
        if not rows:
            return 0
        import pandas as pd

        cols = list(self._COVERAGE_COLS)
        df = pd.DataFrame(rows, columns=cols)
        col_list = ", ".join(cols)
        with self._bootstrap.ops_transaction() as conn:
            conn.execute("DELETE FROM ops.coverage_index")
            conn.execute(f"INSERT INTO ops.coverage_index ({col_list}) SELECT {col_list} FROM df")
        return len(rows)

    # --- COVERAGE QUERIES ---#

    def get_coverage_summary(self) -> list[dict[str, Any]]:
        """One aggregated row per (domain, dataset), sorted weakest coverage first."""
        sql = (
            "SELECT "
            "    domain, "
            "    source, "
            "    dataset, "
            "    COUNT(DISTINCT ticker)                        AS tickers_covered, "
            "    ROUND(AVG(coverage_ratio), 4)                AS avg_coverage_ratio, "
            "    ROUND(AVG(error_rate), 4)                    AS avg_error_rate, "
            "    MAX(last_ingested_at)                        AS last_ingested_at "
            "FROM ops.coverage_index "
            "GROUP BY domain, source, dataset "
            "ORDER BY avg_coverage_ratio ASC NULLS LAST"
        )
        return self._fetch_dicts(sql, [])

    def get_distinct_datasets(self) -> list[str]:
        """Return all distinct dataset names in coverage_index, sorted."""
        sql = "SELECT DISTINCT dataset FROM ops.coverage_index ORDER BY dataset ASC"
        return [r["dataset"] for r in self._fetch_dicts(sql, [])]

    def get_distinct_tickers(self) -> list[str]:
        """Return all distinct non-empty ticker symbols in coverage_index, sorted."""
        sql = (
            "SELECT DISTINCT ticker FROM ops.coverage_index "
            "WHERE ticker <> '' "
            "ORDER BY ticker ASC"
        )
        return [r["ticker"] for r in self._fetch_dicts(sql, [])]

    def get_coverage_by_dataset(self, dataset: str) -> list[dict[str, Any]]:
        """Per-ticker coverage for a single dataset, weakest first."""
        sql = (
            "SELECT ticker, min_date, max_date, coverage_ratio, "
            "       total_files, error_count, error_rate, "
            "       last_ingested_at, is_timeseries "
            "FROM ops.coverage_index "
            "WHERE dataset = ? "
            "ORDER BY coverage_ratio ASC NULLS LAST"
        )
        return self._fetch_dicts(sql, [dataset])

    def get_coverage_by_ticker(self, ticker: str) -> list[dict[str, Any]]:
        """Per-dataset coverage for a single ticker, sorted by coverage_ratio ascending."""
        sql = (
            "SELECT dataset, is_timeseries, min_date, max_date, "
            "       coverage_ratio, total_files, error_count, error_rate, "
            "       last_ingested_at, age_days, last_snapshot_date "
            "FROM ops.coverage_index "
            "WHERE ticker = ? "
            "ORDER BY coverage_ratio ASC NULLS LAST"
        )
        return self._fetch_dicts(sql, [ticker])

    def get_stale_snapshots(self, min_age_days: int) -> list[dict[str, Any]]:
        """Snapshot datasets (is_timeseries=FALSE) with age_days >= min_age_days."""
        sql = (
            "SELECT dataset, ticker, last_snapshot_date, age_days "
            "FROM ops.coverage_index "
            "WHERE is_timeseries = FALSE AND age_days >= ? "
            "ORDER BY age_days DESC NULLS LAST"
        )
        return self._fetch_dicts(sql, [min_age_days])

    def get_coverage_matrix(self) -> list[dict[str, Any]]:
        """Per-dataset aggregated metrics for the Global Overview heatmap.

        Returns one row per dataset with:
          tickers_covered, avg_coverage_ratio, pct_updated_7d,
          median_history_years, oldest_max_date_age
        Sorted weakest coverage first.
        """
        sql = (
            "SELECT "
            "    dataset, "
            "    COUNT(DISTINCT ticker) AS tickers_covered, "
            "    AVG(coverage_ratio) AS avg_coverage_ratio, "
            "    CAST(COUNT(*) FILTER (WHERE last_ingested_at > NOW() - INTERVAL '7 days') AS DOUBLE)"
            "        / NULLIF(COUNT(*), 0) AS pct_updated_7d, "
            "    MEDIAN(datediff('year', min_date, max_date)) AS median_history_years, "
            "    MAX(datediff('day', max_date, current_date)) AS oldest_max_date_age "
            "FROM ops.coverage_index "
            "GROUP BY dataset "
            "ORDER BY avg_coverage_ratio ASC NULLS LAST"
        )
        return self._fetch_dicts(sql, [])

    # ---- Ingestion Diagnostics queries (ops.file_ingestions) ----

    def get_ingestion_error_rates(self) -> list[dict[str, Any]]:
        """Per-dataset error rates from ops.file_ingestions, worst first."""
        sql = (
            "SELECT "
            "    dataset, "
            "    COUNT(*) AS total_files, "
            "    COUNT(*) FILTER (WHERE bronze_error IS NOT NULL) AS error_count, "
            "    ROUND(100.0 * COUNT(*) FILTER (WHERE bronze_error IS NOT NULL) "
            "          / NULLIF(COUNT(*), 0), 2) AS error_rate_pct, "
            "    MAX(bronze_injest_start_time) AS last_seen "
            "FROM ops.file_ingestions "
            "GROUP BY dataset "
            "ORDER BY error_rate_pct DESC NULLS LAST"
        )
        return self._fetch_dicts(sql, [])

    def get_ingestion_latency(self) -> list[dict[str, Any]]:
        """Per-dataset bronze ingestion latency (ms) statistics, slowest first."""
        sql = (
            "SELECT "
            "    dataset, "
            "    COUNT(*) AS samples, "
            "    ROUND(AVG(datediff('millisecond', bronze_injest_start_time, "
            "              bronze_injest_end_time)), 0) AS avg_ms, "
            "    ROUND(QUANTILE_CONT(datediff('millisecond', bronze_injest_start_time, "
            "              bronze_injest_end_time), 0.95), 0) AS p95_ms, "
            "    MAX(datediff('millisecond', bronze_injest_start_time, "
            "        bronze_injest_end_time)) AS max_ms "
            "FROM ops.file_ingestions "
            "WHERE bronze_injest_start_time IS NOT NULL "
            "  AND bronze_injest_end_time IS NOT NULL "
            "  AND bronze_injest_end_time > bronze_injest_start_time "
            "GROUP BY dataset "
            "ORDER BY avg_ms DESC NULLS LAST"
        )
        return self._fetch_dicts(sql, [])

    def get_hash_stability(self) -> list[dict[str, Any]]:
        """Per-dataset payload hash stability.

        hash_change_pct = distinct_hashes / total_files * 100.
        Low % = data rarely changes (stable). High % = data changes often.
        """
        sql = (
            "SELECT "
            "    dataset, "
            "    COUNT(*) AS total_files, "
            "    COUNT(DISTINCT bronze_payload_hash) AS distinct_hashes, "
            "    ROUND(100.0 * COUNT(DISTINCT bronze_payload_hash) "
            "          / NULLIF(COUNT(*), 0), 1) AS hash_change_pct "
            "FROM ops.file_ingestions "
            "WHERE bronze_payload_hash IS NOT NULL "
            "GROUP BY dataset "
            "ORDER BY hash_change_pct DESC NULLS LAST"
        )
        return self._fetch_dicts(sql, [])

    def get_recent_errors(self, limit: int = 100) -> list[dict[str, Any]]:
        """Most recent bronze ingestion errors, newest first."""
        sql = (
            "SELECT "
            "    bronze_injest_start_time AS occurred_at, "
            "    dataset, "
            "    COALESCE(ticker, '') AS ticker, "
            "    run_id, "
            "    bronze_error AS error_message "
            "FROM ops.file_ingestions "
            "WHERE bronze_error IS NOT NULL "
            "ORDER BY bronze_injest_start_time DESC NULLS LAST "
            f"LIMIT {int(limit)}"
        )
        return self._fetch_dicts(sql, [])

    # ---- PRIVATE METHODS ---#


__all__ = ["DuckDbOpsRepo"]
