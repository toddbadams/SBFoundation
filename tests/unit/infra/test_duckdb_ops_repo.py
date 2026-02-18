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
    def ops_transaction(self) -> duckdb.DuckDBPyConnection:
        yield self.conn

    @contextmanager
    def read_connection(self) -> duckdb.DuckDBPyConnection:
        yield self.conn


def _create_connection() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(database=":memory:")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ops")
    conn.execute("DROP TABLE IF EXISTS ops.file_ingestions")
    conn.execute(
        """
        CREATE TABLE ops.file_ingestions (
            run_id VARCHAR,
            file_id VARCHAR,
            domain VARCHAR,
            source VARCHAR,
            dataset VARCHAR,
            discriminator VARCHAR,
            ticker VARCHAR,
            bronze_filename VARCHAR,
            bronze_error VARCHAR,
            bronze_rows INTEGER,
            bronze_from_date DATE,
            bronze_to_date DATE,
            bronze_injest_start_time TIMESTAMP,
            bronze_injest_end_time TIMESTAMP,
            bronze_can_promote BOOLEAN,
            bronze_payload_hash VARCHAR,
            silver_tablename VARCHAR,
            silver_errors VARCHAR,
            silver_rows_created INTEGER,
            silver_rows_updated INTEGER,
            silver_rows_failed INTEGER,
            silver_from_date DATE,
            silver_to_date DATE,
            silver_injest_start_time TIMESTAMP,
            silver_injest_end_time TIMESTAMP,
            silver_can_promote BOOLEAN
        )
        """
    )
    return conn


def _make_repo(conn: duckdb.DuckDBPyConnection) -> DuckDbOpsRepo:
    return DuckDbOpsRepo(bootstrap=_StubBootstrap(conn))


def test_upsert_updates_existing_row() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    ingestion = DatasetInjestion(run_id="run-1", file_id="file-1", domain="company", source="fmp", dataset="company-profile")
    repo.upsert_file_ingestion(ingestion)
    ingestion.bronze_rows = 5
    repo.upsert_file_ingestion(ingestion)
    row = conn.execute("SELECT bronze_rows FROM ops.file_ingestions").fetchall()[0][0]
    assert row == 5


def test_latest_dates_handle_nulls() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    ingestion = DatasetInjestion(
        run_id="run-2",
        file_id="file-2",
        domain="company",
        source="fmp",
        dataset="company-profile",
        bronze_to_date=date(2026, 1, 20),
        silver_to_date=date(2026, 1, 21),
        bronze_can_promote=True,
    )
    repo.upsert_file_ingestion(ingestion)
    assert repo.get_latest_bronze_to_date(domain="company", source="fmp", dataset="company-profile", discriminator="", ticker="") == date(2026, 1, 20)
    assert repo.get_latest_silver_to_date(domain="company", source="fmp", dataset="company-profile", discriminator="", ticker="") == date(2026, 1, 21)


def test_list_promotable_file_ingestions_filters() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    promotable = DatasetInjestion(
        run_id="run-3",
        file_id="file-3",
        domain="company",
        source="fmp",
        dataset="company-profile",
        bronze_can_promote=True,
    )
    repo.upsert_file_ingestion(promotable)
    blocked = DatasetInjestion(
        run_id="run-4",
        file_id="file-4",
        domain="company",
        source="fmp",
        dataset="company-profile",
        bronze_can_promote=False,
    )
    repo.upsert_file_ingestion(blocked)
    results = repo.list_promotable_file_ingestions()
    assert len(results) == 1
    assert results[0].file_id == "file-3"


def test_load_input_watermarks_serializes_identity() -> None:
    conn = _create_connection()
    repo = _make_repo(conn)
    ingestion = DatasetInjestion(
        run_id="run-5",
        file_id="file-5",
        domain="company",
        source="fmp",
        dataset="company-profile",
        silver_from_date=date(2026, 1, 1),
        silver_to_date=date(2026, 1, 2),
        bronze_can_promote=True,
    )
    repo.upsert_file_ingestion(ingestion)
    watermarks = repo.load_input_watermarks(conn, datasets={"company-profile"})
    assert watermarks
    assert "company|fmp|company-profile" in watermarks[0]
