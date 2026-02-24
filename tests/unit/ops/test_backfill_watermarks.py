"""Tests for DuckDbOpsRepo backfill watermark methods."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import duckdb

from sbfoundation.ops.dtos.file_injestion import DatasetInjestion
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo


class _StubBootstrap:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    def connect(self) -> duckdb.DuckDBPyConnection:
        return self.conn

    @contextmanager
    def ops_transaction(self):
        yield self.conn

    @contextmanager
    def read_connection(self):
        yield self.conn


_IDENTITY = dict(domain="fundamentals", source="fmp", dataset="income-statement", discriminator="", ticker="AAPL")


def _create_connection() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=":memory:")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ops")
    conn.execute(
        """
        CREATE TABLE ops.file_ingestions (
            run_id VARCHAR, file_id VARCHAR, domain VARCHAR, source VARCHAR, dataset VARCHAR,
            discriminator VARCHAR, ticker VARCHAR, bronze_filename VARCHAR, bronze_error VARCHAR,
            bronze_rows INTEGER, bronze_from_date DATE, bronze_to_date DATE,
            bronze_injest_start_time TIMESTAMP, bronze_injest_end_time TIMESTAMP,
            bronze_can_promote BOOLEAN, bronze_payload_hash VARCHAR, silver_tablename VARCHAR,
            silver_errors VARCHAR, silver_rows_created INTEGER, silver_rows_updated INTEGER,
            silver_rows_failed INTEGER, silver_from_date DATE, silver_to_date DATE,
            silver_injest_start_time TIMESTAMP, silver_injest_end_time TIMESTAMP,
            silver_can_promote BOOLEAN
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE ops.dataset_watermarks (
            domain        VARCHAR NOT NULL,
            source        VARCHAR NOT NULL,
            dataset       VARCHAR NOT NULL,
            discriminator VARCHAR NOT NULL DEFAULT '',
            ticker        VARCHAR NOT NULL DEFAULT '',
            backfill_floor_date DATE,
            PRIMARY KEY (domain, source, dataset, discriminator, ticker)
        )
        """
    )
    return conn


def _make_repo(conn: duckdb.DuckDBPyConnection) -> DuckDbOpsRepo:
    return DuckDbOpsRepo(bootstrap=_StubBootstrap(conn))


# ── get_backfill_floor_date ─────────────────────────────────────────────────


def test_get_backfill_floor_date_returns_none_when_absent() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    result = repo.get_backfill_floor_date(**_IDENTITY)
    assert result is None


def test_upsert_and_get_backfill_floor_date() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    floor = date(2020, 6, 15)
    repo.upsert_backfill_floor_date(**_IDENTITY, floor_date=floor)
    assert repo.get_backfill_floor_date(**_IDENTITY) == floor


def test_upsert_updates_existing_row() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    repo.upsert_backfill_floor_date(**_IDENTITY, floor_date=date(2020, 6, 15))
    repo.upsert_backfill_floor_date(**_IDENTITY, floor_date=date(1990, 1, 1))
    assert repo.get_backfill_floor_date(**_IDENTITY) == date(1990, 1, 1)


# ── get_earliest_bronze_from_date ──────────────────────────────────────────


def _insert_ingestion(conn, *, run_id: str, file_id: str, from_date: date, error: str | None = None) -> None:
    conn.execute(
        "INSERT INTO ops.file_ingestions (run_id, file_id, domain, source, dataset, discriminator, ticker, "
        "bronze_from_date, bronze_error) VALUES (?, ?, 'fundamentals', 'fmp', 'income-statement', '', 'AAPL', ?, ?)",
        [run_id, file_id, from_date, error],
    )


def test_get_earliest_bronze_from_date_returns_min() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    _insert_ingestion(conn, run_id="r1", file_id="f1", from_date=date(2022, 1, 1))
    _insert_ingestion(conn, run_id="r2", file_id="f2", from_date=date(2020, 6, 15))
    _insert_ingestion(conn, run_id="r3", file_id="f3", from_date=date(2023, 9, 1))
    result = repo.get_earliest_bronze_from_date(**_IDENTITY)
    assert result == date(2020, 6, 15)


def test_get_earliest_bronze_from_date_ignores_error_rows() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    # Only the error row has an early date — must be excluded
    _insert_ingestion(conn, run_id="r1", file_id="f1", from_date=date(1995, 1, 1), error="TIMEOUT")
    _insert_ingestion(conn, run_id="r2", file_id="f2", from_date=date(2022, 3, 1))
    result = repo.get_earliest_bronze_from_date(**_IDENTITY)
    assert result == date(2022, 3, 1)


def test_get_earliest_bronze_from_date_returns_none_when_no_rows() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    result = repo.get_earliest_bronze_from_date(**_IDENTITY)
    assert result is None
