"""
UniverseRepo — DuckDB access for universe_snapshot, universe_member,
and universe_derived_metrics tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sbfoundation.maintenance import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger


@dataclass
class UniverseSnapshot:
    universe_name: str
    as_of_date: date
    filter_hash: str
    member_count: int
    run_id: str
    created_at: datetime


class UniverseRepo:
    """Repository for universe snapshot and member tables."""

    def __init__(
        self,
        logger: SBLogger | None = None,
        bootstrap: DuckDbBootstrap | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    # -------------------------------------------------------------------------
    # universe_member
    # -------------------------------------------------------------------------

    def upsert_members(
        self,
        *,
        universe_name: str,
        as_of_date: date,
        filter_hash: str,
        symbols: list[str],
        run_id: str,
    ) -> None:
        """UPSERT all symbols into silver.universe_member for (universe_name, as_of_date)."""
        if not symbols:
            return
        conn = self._bootstrap.connect()
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (universe_name, as_of_date.isoformat(), filter_hash, symbol, run_id, now)
            for symbol in symbols
        ]
        conn.executemany(
            """
            INSERT INTO silver.universe_member
                (universe_name, as_of_date, filter_hash, symbol, run_id, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (universe_name, as_of_date, symbol)
            DO UPDATE SET filter_hash = excluded.filter_hash,
                          run_id = excluded.run_id,
                          ingested_at = excluded.ingested_at
            """,
            rows,
        )

    def get_tickers(
        self,
        universe_name: str,
        as_of_date: date | None = None,
    ) -> list[str]:
        """Return symbol list for the given universe and date (latest if None)."""
        conn = self._bootstrap.connect()
        if as_of_date is not None:
            sql = (
                "SELECT symbol FROM silver.universe_member "
                "WHERE universe_name = ? AND as_of_date = ? "
                "ORDER BY symbol"
            )
            rows = conn.execute(sql, [universe_name, as_of_date.isoformat()]).fetchall()
        else:
            sql = (
                "SELECT symbol FROM silver.universe_member "
                "WHERE universe_name = ? "
                "AND as_of_date = ("
                "  SELECT MAX(as_of_date) FROM silver.universe_member "
                "  WHERE universe_name = ?"
                ") ORDER BY symbol"
            )
            rows = conn.execute(sql, [universe_name, universe_name]).fetchall()
        return [row[0] for row in rows if row[0]]

    def table_exists(self, table_name: str, schema: str = "silver") -> bool:
        """Return True if the given silver table exists."""
        conn = self._bootstrap.connect()
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = ? AND table_name = ?",
            [schema, table_name],
        ).fetchone()
        return bool(result and result[0] > 0)

    # -------------------------------------------------------------------------
    # universe_snapshot
    # -------------------------------------------------------------------------

    def upsert_snapshot(
        self,
        *,
        universe_name: str,
        as_of_date: date,
        filter_hash: str,
        member_count: int,
        run_id: str,
    ) -> None:
        """UPSERT a universe snapshot row."""
        conn = self._bootstrap.connect()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO silver.universe_snapshot
                (universe_name, as_of_date, filter_hash, member_count, run_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (universe_name, as_of_date)
            DO UPDATE SET filter_hash   = excluded.filter_hash,
                          member_count  = excluded.member_count,
                          run_id        = excluded.run_id,
                          created_at    = excluded.created_at
            """,
            [universe_name, as_of_date.isoformat(), filter_hash, member_count, run_id, now],
        )

    def get_snapshot(
        self,
        universe_name: str,
        as_of_date: date | None = None,
    ) -> UniverseSnapshot | None:
        """Return the snapshot for the given universe and date (latest if None)."""
        conn = self._bootstrap.connect()
        if as_of_date is not None:
            sql = (
                "SELECT universe_name, as_of_date, filter_hash, member_count, run_id, created_at "
                "FROM silver.universe_snapshot "
                "WHERE universe_name = ? AND as_of_date = ?"
            )
            row = conn.execute(sql, [universe_name, as_of_date.isoformat()]).fetchone()
        else:
            sql = (
                "SELECT universe_name, as_of_date, filter_hash, member_count, run_id, created_at "
                "FROM silver.universe_snapshot "
                "WHERE universe_name = ? "
                "ORDER BY as_of_date DESC LIMIT 1"
            )
            row = conn.execute(sql, [universe_name]).fetchone()
        if not row:
            return None
        return UniverseSnapshot(
            universe_name=row[0],
            as_of_date=row[1],
            filter_hash=row[2],
            member_count=row[3],
            run_id=row[4],
            created_at=row[5],
        )

    # -------------------------------------------------------------------------
    # universe_derived_metrics
    # -------------------------------------------------------------------------

    def upsert_derived_metrics(
        self,
        *,
        rows: list[dict],
    ) -> None:
        """UPSERT rows into silver.universe_derived_metrics.

        Each dict must have keys: symbol, as_of_date (date), run_id.
        Optional: computed_market_cap, avg_dollar_volume_30d, avg_dollar_volume_90d,
                  is_actively_trading, data_coverage_score.
        """
        if not rows:
            return
        conn = self._bootstrap.connect()
        now = datetime.now(timezone.utc).isoformat()
        params = [
            (
                r["symbol"],
                r["as_of_date"].isoformat() if isinstance(r["as_of_date"], date) else r["as_of_date"],
                r.get("computed_market_cap"),
                r.get("avg_dollar_volume_30d"),
                r.get("avg_dollar_volume_90d"),
                r.get("is_actively_trading"),
                r.get("data_coverage_score"),
                r["run_id"],
                now,
            )
            for r in rows
        ]
        conn.executemany(
            """
            INSERT INTO silver.universe_derived_metrics
                (symbol, as_of_date, computed_market_cap, avg_dollar_volume_30d,
                 avg_dollar_volume_90d, is_actively_trading, data_coverage_score,
                 run_id, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (symbol, as_of_date)
            DO UPDATE SET computed_market_cap   = excluded.computed_market_cap,
                          avg_dollar_volume_30d = excluded.avg_dollar_volume_30d,
                          avg_dollar_volume_90d = excluded.avg_dollar_volume_90d,
                          is_actively_trading   = excluded.is_actively_trading,
                          data_coverage_score   = excluded.data_coverage_score,
                          run_id                = excluded.run_id,
                          ingested_at           = excluded.ingested_at
            """,
            params,
        )


__all__ = ["UniverseRepo", "UniverseSnapshot"]
