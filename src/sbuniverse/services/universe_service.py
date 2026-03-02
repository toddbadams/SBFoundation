"""
UniverseService — snapshot materialization and ticker resolution.

Responsibilities:
  1. materialize_snapshot(): after screener ingestion, aggregate
     silver.fmp_market_screener results per universe and write versioned
     universe_snapshot + universe_member rows.
  2. tickers(): return the symbol list for a named universe from the latest
     (or specified) snapshot.
  3. snapshot_info(): return metadata for a named universe snapshot.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbuniverse.infra.universe_repo import UniverseRepo, UniverseSnapshot
from sbuniverse.universe_definition import UniverseDefinition


class UniverseService:
    """Materialization and query service for universe snapshots."""

    def __init__(
        self,
        logger: SBLogger | None = None,
        repo: UniverseRepo | None = None,
        bootstrap: DuckDbBootstrap | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._repo = repo or UniverseRepo(logger=self._logger, bootstrap=self._bootstrap)
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    # -------------------------------------------------------------------------
    # Snapshot materialization
    # -------------------------------------------------------------------------

    def materialize_snapshot(
        self,
        universe_def: UniverseDefinition,
        as_of_date: date,
        run_id: str,
    ) -> int:
        """Build universe_member and universe_snapshot for one UniverseDefinition.

        Reads silver.fmp_market_screener rows whose discriminator starts with
        "{universe_name}-" (written during per-universe screener ingestion) and
        aggregates them into the snapshot tables.

        Returns the number of members written.
        """
        if not self._repo.table_exists("fmp_market_screener"):
            self._logger.warning(
                f"silver.fmp_market_screener not found — skipping snapshot for {universe_def.name}",
                run_id=run_id,
            )
            return 0

        symbols = self._query_screener_symbols(universe_def, as_of_date)
        if not symbols:
            self._logger.warning(
                f"No symbols found in fmp_market_screener for universe={universe_def.name} "
                f"as_of={as_of_date}",
                run_id=run_id,
            )

        filter_hash = universe_def.filter_hash()

        self._repo.upsert_members(
            universe_name=universe_def.name,
            as_of_date=as_of_date,
            filter_hash=filter_hash,
            symbols=symbols,
            run_id=run_id,
        )
        self._repo.upsert_snapshot(
            universe_name=universe_def.name,
            as_of_date=as_of_date,
            filter_hash=filter_hash,
            member_count=len(symbols),
            run_id=run_id,
        )

        self._logger.info(
            f"Universe snapshot materialized: universe={universe_def.name} "
            f"as_of={as_of_date} members={len(symbols)} hash={filter_hash[:12]}...",
            run_id=run_id,
        )
        return len(symbols)

    def _query_screener_symbols(
        self, universe_def: UniverseDefinition, as_of_date: date
    ) -> list[str]:
        """Return distinct symbols from fmp_market_screener for this universe.

        Matches rows whose discriminator starts with "{universe_name}-", which
        is the prefix set during per-universe screener ingestion.
        """
        conn = self._bootstrap.connect()
        # fmp_market_screener rows for this universe are those ingested with
        # discriminator = "{universe_name}-{exchange}". Use a LIKE prefix match.
        discriminator_prefix = f"{universe_def.name}-%"
        try:
            rows = conn.execute(
                "SELECT DISTINCT symbol "
                "FROM silver.fmp_market_screener "
                "WHERE symbol IS NOT NULL "
                "AND discriminator LIKE ? "
                "ORDER BY symbol",
                [discriminator_prefix],
            ).fetchall()
            return [row[0] for row in rows if row[0]]
        except Exception as exc:
            self._logger.warning(f"Could not query fmp_market_screener: {exc}")
            return []

    # -------------------------------------------------------------------------
    # Ticker resolution
    # -------------------------------------------------------------------------

    def tickers(
        self,
        universe_name: str,
        as_of_date: date | None = None,
    ) -> list[str]:
        """Return the symbol list for the given universe (latest snapshot if no date)."""
        if not self._repo.table_exists("universe_member"):
            return []
        try:
            return self._repo.get_tickers(universe_name, as_of_date)
        except Exception as exc:
            self._logger.warning(f"Failed to get tickers for universe={universe_name}: {exc}")
            return []

    def snapshot_info(
        self,
        universe_name: str,
        as_of_date: date | None = None,
    ) -> UniverseSnapshot | None:
        """Return snapshot metadata for the given universe (latest if no date)."""
        if not self._repo.table_exists("universe_snapshot"):
            return None
        try:
            return self._repo.get_snapshot(universe_name, as_of_date)
        except Exception as exc:
            self._logger.warning(f"Failed to get snapshot for universe={universe_name}: {exc}")
            return None


__all__ = ["UniverseService"]
