from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any
import logging

import duckdb
import pytest

from sbfoundation.infra.duckdb.duckdb_bootstrap import (
    OPS_COVERAGE_INDEX_DDL,
    OPS_FILE_INGESTIONS_DDL,
    SCHEMA_DDL,
)
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo
from sbfoundation.coverage.coverage_index_service import CoverageIndexService


# ---------------------------------------------------------------------------
# In-memory infrastructure
# ---------------------------------------------------------------------------


class _StubBootstrap:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    @contextmanager
    def ops_transaction(self):
        yield self.conn

    @contextmanager
    def read_connection(self):
        yield self.conn


def _build_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    conn.execute(SCHEMA_DDL)
    conn.execute(OPS_FILE_INGESTIONS_DDL)
    conn.execute(OPS_COVERAGE_INDEX_DDL)
    return conn


def _build_repo(conn: duckdb.DuckDBPyConnection) -> DuckDbOpsRepo:
    repo = DuckDbOpsRepo.__new__(DuckDbOpsRepo)
    repo._bootstrap = _StubBootstrap(conn)
    repo._owns_bootstrap = False
    repo._logger = logging.getLogger("test")
    return repo


def _build_service(
    repo: DuckDbOpsRepo,
    is_timeseries_map: dict[tuple[str, str, str], bool],
) -> CoverageIndexService:
    svc = CoverageIndexService.__new__(CoverageIndexService)
    svc._logger = logging.getLogger("test")
    svc._ops_repo = repo
    svc._owns_ops_repo = False
    svc._is_timeseries_map = is_timeseries_map
    return svc


def _seed(conn: duckdb.DuckDBPyConnection, rows: list[dict[str, Any]]) -> None:
    """Insert rows into ops.file_ingestions."""
    for r in rows:
        conn.execute(
            """
            INSERT INTO ops.file_ingestions (
                run_id, file_id, domain, source, dataset, discriminator, ticker,
                bronze_from_date, bronze_to_date, bronze_rows, bronze_can_promote,
                bronze_injest_start_time, bronze_error,
                silver_rows_created, silver_rows_failed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                r.get("run_id", "run1"),
                r.get("file_id", "f1"),
                r.get("domain", "technicals"),
                r.get("source", "fmp"),
                r.get("dataset", "price-eod"),
                r.get("discriminator", ""),
                r.get("ticker", "AAPL"),
                r.get("bronze_from_date"),
                r.get("bronze_to_date"),
                r.get("bronze_rows", 100),
                r.get("bronze_can_promote", True),
                r.get("bronze_injest_start_time", datetime(2025, 1, 1, 10, 0)),
                r.get("bronze_error"),
                r.get("silver_rows_created", 0),
                r.get("silver_rows_failed", 0),
            ],
        )


def _fetch_index(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    cursor = conn.execute("SELECT * FROM ops.coverage_index ORDER BY dataset, ticker")
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


UNIVERSE_FROM = date(1990, 1, 1)
TODAY = date(2025, 1, 1)
TIMESERIES_MAP = {("technicals", "fmp", "price-eod"): True}
SNAPSHOT_MAP = {("company", "fmp", "company-profile"): False}


def test_refresh_returns_zero_when_no_data() -> None:
    conn = _build_conn()
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)

    count = svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    assert count == 0
    assert _fetch_index(conn) == []


def test_refresh_timeseries_coverage_ratio() -> None:
    conn = _build_conn()
    _seed(conn, [{"bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    rows = _fetch_index(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["is_timeseries"] is True
    assert row["coverage_ratio"] is not None
    assert 0 < row["coverage_ratio"] <= 1.0
    assert row["snapshot_count"] == 0
    assert row["last_snapshot_date"] is None
    assert row["age_days"] is None
    assert row["min_date"] == date(2020, 1, 1)
    assert row["max_date"] == date(2024, 12, 31)


def test_refresh_coverage_ratio_value() -> None:
    """coverage_ratio = (max_date - min_date).days / (today - universe_from_date).days"""
    conn = _build_conn()
    # Exactly 10 years of data in a 35-year expected window
    _seed(conn, [{"bronze_from_date": date(2015, 1, 1), "bronze_to_date": date(2025, 1, 1)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)

    svc.refresh(run_id="r1", universe_from_date=date(1990, 1, 1), today=date(2025, 1, 1))

    row = _fetch_index(conn)[0]
    actual_days = (date(2025, 1, 1) - date(2015, 1, 1)).days
    expected_days = (date(2025, 1, 1) - date(1990, 1, 1)).days
    assert row["coverage_ratio"] == round(actual_days / expected_days, 4)


def test_refresh_snapshot_age_days_from_ingestion_time() -> None:
    """Snapshot datasets (no bronze dates) fall back to ingestion timestamp for age_days."""
    ingest_ts = datetime(2024, 12, 22, 10, 0)  # 10 days before TODAY
    conn = _build_conn()
    _seed(
        conn,
        [
            {
                "domain": "company",
                "source": "fmp",
                "dataset": "company-profile",
                "bronze_from_date": None,
                "bronze_to_date": None,
                "bronze_injest_start_time": ingest_ts,
            }
        ],
    )
    repo = _build_repo(conn)
    svc = _build_service(repo, SNAPSHOT_MAP)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    rows = _fetch_index(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["is_timeseries"] is False
    assert row["coverage_ratio"] is None
    assert row["snapshot_count"] == 1
    assert row["last_snapshot_date"] == date(2024, 12, 22)
    assert row["age_days"] == 10


def test_refresh_error_rate_computed() -> None:
    conn = _build_conn()
    _seed(conn, [{"file_id": "f1", "bronze_error": None}])
    _seed(conn, [{"file_id": "f2", "bronze_error": "HTTP 429"}])
    _seed(conn, [{"file_id": "f3", "bronze_error": "timeout"}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    row = _fetch_index(conn)[0]
    assert row["total_files"] == 3
    assert row["error_count"] == 2
    assert row["error_rate"] == round(2 / 3, 4)


def test_refresh_promotable_files_counted() -> None:
    conn = _build_conn()
    _seed(conn, [{"file_id": "f1", "bronze_can_promote": True}])
    _seed(conn, [{"file_id": "f2", "bronze_can_promote": False}])
    _seed(conn, [{"file_id": "f3", "bronze_can_promote": True}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    row = _fetch_index(conn)[0]
    assert row["total_files"] == 3
    assert row["promotable_files"] == 2


def test_refresh_is_idempotent() -> None:
    conn = _build_conn()
    _seed(conn, [{"bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)
    svc.refresh(run_id="r2", universe_from_date=UNIVERSE_FROM, today=TODAY)

    rows = _fetch_index(conn)
    assert len(rows) == 1


def test_refresh_replaces_stale_values_on_second_call() -> None:
    """Second refresh with updated file_ingestions replaces old coverage values."""
    conn = _build_conn()
    _seed(conn, [{"file_id": "f1", "bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2022, 1, 1)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)
    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    # Add a second file that extends coverage
    _seed(conn, [{"file_id": "f2", "bronze_from_date": date(2022, 1, 2), "bronze_to_date": date(2024, 12, 31)}])
    svc.refresh(run_id="r2", universe_from_date=UNIVERSE_FROM, today=TODAY)

    rows = _fetch_index(conn)
    assert len(rows) == 1
    assert rows[0]["max_date"] == date(2024, 12, 31)
    assert rows[0]["total_files"] == 2


def test_refresh_multiple_tickers_produce_separate_rows() -> None:
    conn = _build_conn()
    _seed(conn, [{"file_id": "f1", "ticker": "AAPL", "bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    _seed(conn, [{"file_id": "f2", "ticker": "MSFT", "bronze_from_date": date(2018, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)

    count = svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    assert count == 2
    rows = _fetch_index(conn)
    tickers = {r["ticker"] for r in rows}
    assert tickers == {"AAPL", "MSFT"}


def test_unknown_dataset_defaults_to_timeseries() -> None:
    """Datasets not in is_timeseries_map are treated as timeseries (safe default)."""
    conn = _build_conn()
    _seed(conn, [{"bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, {})  # empty map — no known datasets

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    row = _fetch_index(conn)[0]
    assert row["is_timeseries"] is True
    assert row["coverage_ratio"] is not None


def test_refresh_expected_window_stored() -> None:
    conn = _build_conn()
    _seed(conn, [{"bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_MAP)

    svc.refresh(run_id="r1", universe_from_date=date(1990, 1, 1), today=date(2025, 6, 30))

    row = _fetch_index(conn)[0]
    assert row["expected_start_date"] == date(1990, 1, 1)
    assert row["expected_end_date"] == date(2025, 6, 30)


def test_load_timeseries_map_falls_back_on_keymap_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If DatasetKeymapLoader raises, _load_timeseries_map returns {} and does not crash."""
    from sbfoundation.dataset.loaders import dataset_keymap_loader

    monkeypatch.setattr(
        dataset_keymap_loader.DatasetKeymapLoader,
        "load_raw_datasets",
        staticmethod(lambda: (_ for _ in ()).throw(FileNotFoundError("no keymap"))),
    )

    conn = _build_conn()
    repo = _build_repo(conn)
    # Call __init__ properly so _load_timeseries_map runs via the real path
    svc = CoverageIndexService(ops_repo=repo)

    assert svc._is_timeseries_map == {}
