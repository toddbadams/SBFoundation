"""Unit tests for UniverseRepo — uses an in-memory DuckDB."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import duckdb
import pytest

from sbuniverse.infra.universe_repo import UniverseRepo, UniverseSnapshot


@pytest.fixture()
def in_memory_bootstrap():
    """Provide a DuckDbBootstrap-alike backed by an in-memory DuckDB connection."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA silver")
    conn.execute(
        """
        CREATE TABLE silver.universe_snapshot (
            universe_name   VARCHAR     NOT NULL,
            as_of_date      DATE        NOT NULL,
            filter_hash     VARCHAR(64) NOT NULL,
            member_count    INTEGER     NOT NULL,
            run_id          VARCHAR     NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (universe_name, as_of_date)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE silver.universe_member (
            universe_name   VARCHAR     NOT NULL,
            as_of_date      DATE        NOT NULL,
            filter_hash     VARCHAR(64) NOT NULL,
            symbol          VARCHAR     NOT NULL,
            run_id          VARCHAR     NOT NULL,
            ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (universe_name, as_of_date, symbol)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE silver.universe_derived_metrics (
            symbol                  VARCHAR     NOT NULL,
            as_of_date              DATE        NOT NULL,
            computed_market_cap     DOUBLE      NULL,
            avg_dollar_volume_30d   DOUBLE      NULL,
            avg_dollar_volume_90d   DOUBLE      NULL,
            is_actively_trading     BOOLEAN     NULL,
            data_coverage_score     DOUBLE      NULL,
            run_id                  VARCHAR     NOT NULL,
            ingested_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (symbol, as_of_date)
        )
        """
    )

    bootstrap = MagicMock()
    bootstrap.connect.return_value = conn
    yield bootstrap
    conn.close()


@pytest.fixture()
def repo(in_memory_bootstrap):
    return UniverseRepo(bootstrap=in_memory_bootstrap)


class TestUpsertAndGetMembers:
    def test_upsert_and_retrieve(self, repo: UniverseRepo) -> None:
        today = date(2026, 3, 2)
        repo.upsert_members(
            universe_name="us_large_cap",
            as_of_date=today,
            filter_hash="abc123",
            symbols=["AAPL", "MSFT", "GOOGL"],
            run_id="run_001",
        )
        tickers = repo.get_tickers("us_large_cap", today)
        assert sorted(tickers) == ["AAPL", "GOOGL", "MSFT"]

    def test_upsert_is_idempotent(self, repo: UniverseRepo) -> None:
        today = date(2026, 3, 2)
        repo.upsert_members(
            universe_name="us_large_cap",
            as_of_date=today,
            filter_hash="abc123",
            symbols=["AAPL", "MSFT"],
            run_id="run_001",
        )
        # Re-upsert same symbols — should not duplicate
        repo.upsert_members(
            universe_name="us_large_cap",
            as_of_date=today,
            filter_hash="abc123",
            symbols=["AAPL", "MSFT"],
            run_id="run_002",
        )
        tickers = repo.get_tickers("us_large_cap", today)
        assert len(tickers) == 2

    def test_get_latest_when_multiple_dates(self, repo: UniverseRepo) -> None:
        d1 = date(2026, 3, 1)
        d2 = date(2026, 3, 2)
        repo.upsert_members(universe_name="u", as_of_date=d1, filter_hash="h1", symbols=["A"], run_id="r1")
        repo.upsert_members(universe_name="u", as_of_date=d2, filter_hash="h2", symbols=["B", "C"], run_id="r2")
        # No date → latest
        tickers = repo.get_tickers("u")
        assert sorted(tickers) == ["B", "C"]

    def test_empty_symbols_noop(self, repo: UniverseRepo) -> None:
        repo.upsert_members(
            universe_name="u", as_of_date=date(2026, 3, 2), filter_hash="h", symbols=[], run_id="r"
        )
        tickers = repo.get_tickers("u")
        assert tickers == []

    def test_unknown_universe_returns_empty(self, repo: UniverseRepo) -> None:
        tickers = repo.get_tickers("nonexistent")
        assert tickers == []


class TestUpsertAndGetSnapshot:
    def test_upsert_and_retrieve(self, repo: UniverseRepo) -> None:
        today = date(2026, 3, 2)
        repo.upsert_snapshot(
            universe_name="us_large_cap",
            as_of_date=today,
            filter_hash="deadbeef" * 8,
            member_count=450,
            run_id="run_001",
        )
        snap = repo.get_snapshot("us_large_cap", today)
        assert snap is not None
        assert snap.universe_name == "us_large_cap"
        assert snap.as_of_date == today
        assert snap.member_count == 450
        assert snap.run_id == "run_001"

    def test_idempotent_upsert_updates_count(self, repo: UniverseRepo) -> None:
        today = date(2026, 3, 2)
        repo.upsert_snapshot(universe_name="u", as_of_date=today, filter_hash="h", member_count=100, run_id="r1")
        repo.upsert_snapshot(universe_name="u", as_of_date=today, filter_hash="h", member_count=105, run_id="r2")
        snap = repo.get_snapshot("u", today)
        assert snap is not None
        assert snap.member_count == 105

    def test_get_latest_snapshot(self, repo: UniverseRepo) -> None:
        repo.upsert_snapshot(universe_name="u", as_of_date=date(2026, 3, 1), filter_hash="h", member_count=10, run_id="r1")
        repo.upsert_snapshot(universe_name="u", as_of_date=date(2026, 3, 2), filter_hash="h", member_count=20, run_id="r2")
        snap = repo.get_snapshot("u")
        assert snap is not None
        assert snap.member_count == 20

    def test_missing_universe_returns_none(self, repo: UniverseRepo) -> None:
        snap = repo.get_snapshot("nonexistent")
        assert snap is None


class TestUpsertDerivedMetrics:
    def test_upsert_and_count(self, repo: UniverseRepo, in_memory_bootstrap) -> None:
        today = date(2026, 3, 2)
        rows = [
            {"symbol": "AAPL", "as_of_date": today, "avg_dollar_volume_30d": 1e9, "is_actively_trading": True, "run_id": "r1"},
            {"symbol": "MSFT", "as_of_date": today, "avg_dollar_volume_30d": 8e8, "is_actively_trading": True, "run_id": "r1"},
        ]
        repo.upsert_derived_metrics(rows=rows)
        conn = in_memory_bootstrap.connect()
        count = conn.execute("SELECT COUNT(*) FROM silver.universe_derived_metrics").fetchone()[0]
        assert count == 2

    def test_idempotent_upsert(self, repo: UniverseRepo, in_memory_bootstrap) -> None:
        today = date(2026, 3, 2)
        row = {"symbol": "AAPL", "as_of_date": today, "avg_dollar_volume_30d": 1e9, "run_id": "r1"}
        repo.upsert_derived_metrics(rows=[row])
        row2 = {"symbol": "AAPL", "as_of_date": today, "avg_dollar_volume_30d": 2e9, "run_id": "r2"}
        repo.upsert_derived_metrics(rows=[row2])
        conn = in_memory_bootstrap.connect()
        val = conn.execute(
            "SELECT avg_dollar_volume_30d FROM silver.universe_derived_metrics WHERE symbol = 'AAPL'"
        ).fetchone()[0]
        assert val == 2e9  # updated
