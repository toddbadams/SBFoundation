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
    dataset_meta_map: dict[tuple[str, str, str], dict[str, Any]],
) -> CoverageIndexService:
    """Construct a CoverageIndexService with a pre-built meta map (no keymap I/O)."""
    svc = CoverageIndexService.__new__(CoverageIndexService)
    svc._logger = logging.getLogger("test")
    svc._ops_repo = repo
    svc._owns_ops_repo = False
    svc._dataset_meta_map = dataset_meta_map
    # Backward-compat alias
    svc._is_timeseries_map = {k: v["is_timeseries"] for k, v in dataset_meta_map.items()}
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
# Shared test fixtures
# ---------------------------------------------------------------------------

UNIVERSE_FROM = date(1990, 1, 1)
TODAY = date(2025, 1, 1)

# per_ticker + historical: coverage_ratio is computed against 1990-01-01
TIMESERIES_META: dict[tuple[str, str, str], dict[str, Any]] = {
    ("technicals", "fmp", "price-eod"): {
        "is_timeseries": True,
        "ticker_scope": "per_ticker",
        "is_historical": True,
    }
}

# per_ticker + snapshot: no coverage_ratio, age_days tracked
SNAPSHOT_META: dict[tuple[str, str, str], dict[str, Any]] = {
    ("company", "fmp", "company-profile"): {
        "is_timeseries": False,
        "ticker_scope": "per_ticker",
        "is_historical": False,
    }
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_refresh_returns_zero_when_no_data() -> None:
    conn = _build_conn()
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_META)

    count = svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    assert count == 0
    assert _fetch_index(conn) == []


def test_refresh_historical_coverage_ratio() -> None:
    conn = _build_conn()
    _seed(conn, [{"bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_META)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    rows = _fetch_index(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["is_timeseries"] is True
    assert row["is_historical"] is True
    assert row["ticker_scope"] == "per_ticker"
    assert row["coverage_ratio"] is not None
    assert 0 < row["coverage_ratio"] <= 1.0
    assert row["snapshot_count"] == 0
    assert row["last_snapshot_date"] is None
    assert row["age_days"] is None
    assert row["min_date"] == date(2020, 1, 1)
    assert row["max_date"] == date(2024, 12, 31)


def test_refresh_coverage_ratio_uses_1990_as_expected_start() -> None:
    """coverage_ratio = (max_date - min_date).days / (today - 1990-01-01).days
    regardless of the universe_from_date passed in."""
    conn = _build_conn()
    # Exactly 10 years of data
    _seed(conn, [{"bronze_from_date": date(2015, 1, 1), "bronze_to_date": date(2025, 1, 1)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_META)

    # Pass a different universe_from_date — should NOT affect historical coverage_ratio
    svc.refresh(run_id="r1", universe_from_date=date(2000, 1, 1), today=date(2025, 1, 1))

    row = _fetch_index(conn)[0]
    actual_days = (date(2025, 1, 1) - date(2015, 1, 1)).days
    expected_days = (date(2025, 1, 1) - date(1990, 1, 1)).days  # always 1990-01-01
    assert row["coverage_ratio"] == round(actual_days / expected_days, 4)
    assert row["expected_start_date"] == date(1990, 1, 1)


def test_refresh_snapshot_age_days_from_ingestion_time() -> None:
    """Snapshot datasets (is_historical=False) fall back to ingestion timestamp for age_days."""
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
    svc = _build_service(repo, SNAPSHOT_META)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    rows = _fetch_index(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["is_timeseries"] is False
    assert row["is_historical"] is False
    assert row["ticker_scope"] == "per_ticker"
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
    svc = _build_service(repo, TIMESERIES_META)

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
    svc = _build_service(repo, TIMESERIES_META)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    row = _fetch_index(conn)[0]
    assert row["total_files"] == 3
    assert row["promotable_files"] == 2


def test_refresh_is_idempotent() -> None:
    conn = _build_conn()
    _seed(conn, [{"bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_META)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)
    svc.refresh(run_id="r2", universe_from_date=UNIVERSE_FROM, today=TODAY)

    rows = _fetch_index(conn)
    assert len(rows) == 1


def test_refresh_replaces_stale_values_on_second_call() -> None:
    """Second refresh with updated file_ingestions replaces old coverage values."""
    conn = _build_conn()
    _seed(conn, [{"file_id": "f1", "bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2022, 1, 1)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_META)
    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

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
    svc = _build_service(repo, TIMESERIES_META)

    count = svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    assert count == 2
    rows = _fetch_index(conn)
    tickers = {r["ticker"] for r in rows}
    assert tickers == {"AAPL", "MSFT"}


def test_unknown_dataset_defaults_to_historical_timeseries() -> None:
    """Datasets not in dataset_meta_map default to is_timeseries=True, is_historical=True."""
    conn = _build_conn()
    _seed(conn, [{"bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, {})  # empty map

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    row = _fetch_index(conn)[0]
    assert row["is_timeseries"] is True
    assert row["is_historical"] is True
    assert row["coverage_ratio"] is not None


def test_refresh_historical_expected_window_stored() -> None:
    """Historical rows always store 1990-01-01 as expected_start_date."""
    conn = _build_conn()
    _seed(conn, [{"bronze_from_date": date(2020, 1, 1), "bronze_to_date": date(2024, 12, 31)}])
    repo = _build_repo(conn)
    svc = _build_service(repo, TIMESERIES_META)

    svc.refresh(run_id="r1", universe_from_date=date(2000, 1, 1), today=date(2025, 6, 30))

    row = _fetch_index(conn)[0]
    assert row["expected_start_date"] == date(1990, 1, 1)
    assert row["expected_end_date"] == date(2025, 6, 30)


def test_ticker_scope_and_is_historical_stored() -> None:
    """ticker_scope and is_historical are written to the index row."""
    global_hist_meta: dict[tuple[str, str, str], dict[str, Any]] = {
        ("economics", "fmp", "economic-indicators"): {
            "is_timeseries": True,
            "ticker_scope": "global",
            "is_historical": True,
        }
    }
    conn = _build_conn()
    _seed(conn, [{
        "domain": "economics",
        "source": "fmp",
        "dataset": "economic-indicators",
        "ticker": "",
        "bronze_from_date": date(2000, 1, 1),
        "bronze_to_date": date(2024, 12, 31),
    }])
    repo = _build_repo(conn)
    svc = _build_service(repo, global_hist_meta)

    svc.refresh(run_id="r1", universe_from_date=UNIVERSE_FROM, today=TODAY)

    row = _fetch_index(conn)[0]
    assert row["ticker_scope"] == "global"
    assert row["is_historical"] is True
    assert row["coverage_ratio"] is not None


def test_load_dataset_meta_map_falls_back_on_keymap_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If DatasetKeymapLoader raises, _dataset_meta_map returns {} and does not crash."""
    from sbfoundation.dataset.loaders import dataset_keymap_loader

    monkeypatch.setattr(
        dataset_keymap_loader.DatasetKeymapLoader,
        "load_raw_datasets",
        staticmethod(lambda: (_ for _ in ()).throw(FileNotFoundError("no keymap"))),
    )

    conn = _build_conn()
    repo = _build_repo(conn)
    svc = CoverageIndexService(ops_repo=repo)

    assert svc._dataset_meta_map == {}
    assert svc._is_timeseries_map == {}
