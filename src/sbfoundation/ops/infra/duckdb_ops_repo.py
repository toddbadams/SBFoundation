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

    # ---- PRIVATE METHODS ---#


__all__ = ["DuckDbOpsRepo"]
