from __future__ import annotations

import datetime
import logging
from typing import Any

import duckdb

from sbfoundation.dataset.models.dataset_identity import DatasetIdentity
from sbfoundation.dataset.models.dataset_watermark import DatasetWatermark
from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory
from sbfoundation.ops.dtos.file_injestion import DatasetInjestion


class DuckDbOpsRepo:
    """Aggregate root for the ops metadata stored in `ops.file_ingestions`.  Maintaining a single run/file row prevents Bronze duplication."""

    def __init__(self, logger: logging.Logger | None = None, bootstrap: DuckDbBootstrap | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None
        self._gold_build_counter = 0

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
            "? AS silver_to_date, ? AS silver_injest_start_time, ? AS silver_injest_end_time, ? AS silver_can_promote, "
            "? AS gold_object_type, ? AS gold_tablename, ? AS gold_errors, ? AS gold_rows_created, ? AS gold_rows_updated, "
            "? AS gold_rows_failed, ? AS gold_from_date, ? AS gold_to_date, ? AS gold_injest_start_time, ? AS gold_injest_end_time, "
            "? AS gold_can_promote"
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
            "silver_can_promote = src.silver_can_promote, gold_object_type = src.gold_object_type, "
            "gold_tablename = src.gold_tablename, gold_errors = src.gold_errors, gold_rows_created = src.gold_rows_created, "
            "gold_rows_updated = src.gold_rows_updated, gold_rows_failed = src.gold_rows_failed, "
            "gold_from_date = src.gold_from_date, gold_to_date = src.gold_to_date, "
            "gold_injest_start_time = src.gold_injest_start_time, gold_injest_end_time = src.gold_injest_end_time, "
            "gold_can_promote = src.gold_can_promote "
            "WHEN NOT MATCHED THEN INSERT ("
            "run_id, file_id, domain, source, dataset, discriminator, ticker, "
            "bronze_filename, bronze_error, bronze_rows, bronze_from_date, bronze_to_date, "
            "bronze_injest_start_time, bronze_injest_end_time, bronze_can_promote, bronze_payload_hash, "
            "silver_tablename, silver_errors, silver_rows_created, silver_rows_updated, "
            "silver_rows_failed, silver_from_date, silver_to_date, silver_injest_start_time, silver_injest_end_time, "
            "silver_can_promote, gold_object_type, gold_tablename, gold_errors, gold_rows_created, gold_rows_updated, "
            "gold_rows_failed, gold_from_date, gold_to_date, gold_injest_start_time, gold_injest_end_time, gold_can_promote"
            ") VALUES ("
            "src.run_id, src.file_id, src.domain, src.source, src.dataset, src.discriminator, src.ticker, "
            "src.bronze_filename, src.bronze_error, src.bronze_rows, src.bronze_from_date, src.bronze_to_date, "
            "src.bronze_injest_start_time, src.bronze_injest_end_time, src.bronze_can_promote, src.bronze_payload_hash, "
            "src.silver_tablename, src.silver_errors, src.silver_rows_created, "
            "src.silver_rows_updated, src.silver_rows_failed, src.silver_from_date, src.silver_to_date, "
            "src.silver_injest_start_time, src.silver_injest_end_time, src.silver_can_promote, src.gold_object_type, "
            "src.gold_tablename, src.gold_errors, src.gold_rows_created, src.gold_rows_updated, src.gold_rows_failed, "
            "src.gold_from_date, src.gold_to_date, src.gold_injest_start_time, src.gold_injest_end_time, src.gold_can_promote"
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
            ingestion.gold_object_type,
            ingestion.gold_tablename,
            ingestion.gold_errors,
            ingestion.gold_rows_created,
            ingestion.gold_rows_updated,
            ingestion.gold_rows_failed,
            ingestion.gold_from_date,
            ingestion.gold_to_date,
            ingestion.gold_injest_start_time,
            ingestion.gold_injest_end_time,
            ingestion.gold_can_promote,
        ]
        with self._bootstrap.ops_transaction() as conn:
            conn.execute(sql, params)

    def update_gold_ingestion_times(
        self,
        *,
        run_id: str,
        gold_injest_start_time: datetime.datetime | None = None,
        gold_injest_end_time: datetime.datetime | None = None,
    ) -> None:
        set_clauses = []
        params: list[Any] = []
        if gold_injest_start_time is not None:
            set_clauses.append("gold_injest_start_time = ?")
            params.append(gold_injest_start_time)
        if gold_injest_end_time is not None:
            set_clauses.append("gold_injest_end_time = ?")
            params.append(gold_injest_end_time)
        if not set_clauses:
            return
        sql = f"UPDATE ops.file_ingestions SET {', '.join(set_clauses)} WHERE run_id = ?"
        params.append(run_id)
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
        row = (
            self._bootstrap.connect()
            .execute(
                sql,
                [domain, source, dataset, discriminator_token, ticker_token],
            )
            .fetchone()
        )
        return row[0] if row else None

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
        row = (
            self._bootstrap.connect()
            .execute(
                sql,
                [domain, source, dataset, discriminator_token, ticker_token],
            )
            .fetchone()
        )
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
        conn = self._bootstrap.connect()
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
        row = (
            self._bootstrap.connect()
            .execute(
                sql,
                [domain, source, dataset, discriminator_token, ticker_token],
            )
            .fetchone()
        )
        return row[0] if row else None

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

    # --- BRONZE MANIFEST ---#
    # --- GOLD BUILD ---#
    def next_gold_build_id(self, conn: duckdb.DuckDBPyConnection) -> int:
        """Get next gold_build_id by querying max from ops.gold_builds table."""
        result = conn.execute("SELECT COALESCE(MAX(gold_build_id), 0) + 1 FROM ops.gold_builds").fetchone()
        return result[0] if result else 1

    def insert_gold_build(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        gold_build_id: int,
        run_id: str,
        model_version: str,
        started_at: datetime.datetime,
        finished_at: datetime.datetime,
        status: str,
        error_message: str | None,
        input_watermarks: list[str],
        row_counts: dict[str, int],
    ) -> None:
        """Insert gold build record into ops.gold_builds for lineage tracking."""
        import json

        conn.execute(
            """
            INSERT INTO ops.gold_builds (
                gold_build_id, run_id, model_version, started_at, finished_at,
                status, error_message, row_counts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                gold_build_id,
                run_id,
                model_version,
                started_at,
                finished_at,
                status,
                error_message,
                json.dumps(row_counts),
            ],
        )

    # --- GOLD MANIFEST ---#
    def start_gold_manifest(self, conn: duckdb.DuckDBPyConnection, *, gold_build_id: int, table_name: str) -> None:
        pass

    def finish_gold_manifest(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        gold_build_id: int,
        table_name: str,
        status: str,
        rows_seen: int,
        rows_written: int,
        error_message: str | None,
    ) -> None:
        pass

    # --- GOLD WATERMARK ---#
    def get_gold_watermark(self, conn: duckdb.DuckDBPyConnection, *, table_name: str) -> datetime.date | None:
        """Query max(gold_to_date) from ops.file_ingestions for incremental processing."""
        result = conn.execute(
            """
            SELECT MAX(gold_to_date)
            FROM ops.file_ingestions
            WHERE gold_tablename LIKE ?
            """,
            [f"%{table_name}%"],
        ).fetchone()
        return result[0] if result and result[0] else None

    def upsert_gold_watermark(self, conn: duckdb.DuckDBPyConnection, *, table_name: str, watermark_date: datetime.date | None) -> None:
        """Update gold_to_date in ops.file_ingestions for watermark tracking."""
        if watermark_date is None:
            return

        conn.execute(
            """
            UPDATE ops.file_ingestions
            SET gold_to_date = ?
            WHERE gold_tablename LIKE ?
              AND (gold_to_date IS NULL OR gold_to_date < ?)
            """,
            [watermark_date, f"%{table_name}%", watermark_date],
        )

    # ---- PRIVATE METHODS ---#


__all__ = ["DuckDbOpsRepo"]
