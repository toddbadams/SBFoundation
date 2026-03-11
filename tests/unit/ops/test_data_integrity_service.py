"""Unit tests for DataIntegrityService."""
from __future__ import annotations

import duckdb
import pytest

from sbfoundation.ops.services.data_integrity_service import DataIntegrityService
from sbfoundation.maintenance.duckdb_bootstrap import DuckDbBootstrap


@pytest.fixture
def mem_bootstrap():
    """In-memory DuckDB bootstrap for testing."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ops")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ops.run_integrity (
            integrity_id     VARCHAR     PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
            run_id           VARCHAR     NOT NULL,
            layer            VARCHAR     NOT NULL,
            domain           VARCHAR,
            source           VARCHAR,
            dataset          VARCHAR,
            discriminator    VARCHAR     NOT NULL DEFAULT '',
            ticker           VARCHAR     NOT NULL DEFAULT '',
            file_id          VARCHAR,
            status           VARCHAR     NOT NULL,
            rows_in          BIGINT,
            rows_out         BIGINT,
            error_message    VARCHAR,
            checked_at       TIMESTAMP   NOT NULL DEFAULT now()
        )
    """)
    bs = DuckDbBootstrap(conn=conn)
    bs._schema_initialized = True
    yield bs
    conn.close()


def test_record_and_summary(mem_bootstrap):
    svc = DataIntegrityService(bootstrap=mem_bootstrap)
    svc.record(
        run_id="test-run-1",
        layer="silver",
        domain="market",
        source="fmp",
        dataset="stock-list",
        status="ok",
        rows_in=100,
        rows_out=100,
    )
    svc.record(
        run_id="test-run-1",
        layer="silver",
        domain="market",
        source="fmp",
        dataset="etf-list",
        status="failed",
        rows_in=50,
        rows_out=0,
        error_message="Schema mismatch",
    )

    summary = svc.summary("test-run-1")
    assert summary.get("silver.ok") == 1
    assert summary.get("silver.failed") == 1


def test_record_nonexistent_table_is_nonfatal():
    """DataIntegrityService.record() must not raise even if table is missing."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ops")
    bs = DuckDbBootstrap(conn=conn)
    bs._schema_initialized = True
    svc = DataIntegrityService(bootstrap=bs)
    # Should not raise
    svc.record(run_id="x", layer="silver", status="ok")
    conn.close()
