"""
sbuniverse.api — Public entry point for the Universe data product.

UniverseAPI provides:
  tickers(universe_name, as_of_date)  → list[str]   for the ingestion pipeline
  snapshot_info(universe_name, ...)   → UniverseSnapshot | None
  run_universe_build(universe_names)  → trigger screener ingestion + snapshot

CLI usage:
  python -m sbuniverse.api tickers --universe us_large_cap
  python -m sbuniverse.api snapshot --universe us_large_cap [--date 2026-03-01]
  python -m sbuniverse.api run [--universe us_large_cap]

VS Code: launch via "sbuniverse: run universe build" config in .vscode/launch.json.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from sbfoundation.maintenance import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbuniverse.infra.universe_repo import UniverseRepo, UniverseSnapshot
from sbuniverse.services.universe_service import UniverseService
from sbuniverse.universe_definitions import UNIVERSE_REGISTRY


class UniverseAPI:
    """Public API for universe snapshot queries.

    Used by the ingestion pipeline to obtain the ticker list for a named
    universe, and by audit tooling to inspect snapshot history.
    """

    def __init__(
        self,
        logger: SBLogger | None = None,
        bootstrap: DuckDbBootstrap | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._repo = UniverseRepo(logger=self._logger, bootstrap=self._bootstrap)
        self._service = UniverseService(
            logger=self._logger,
            repo=self._repo,
            bootstrap=self._bootstrap,
        )

    def close(self) -> None:
        self._bootstrap.close()

    def __enter__(self) -> "UniverseAPI":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # -------------------------------------------------------------------------
    # Query API (used by ingestion pipeline and downstream)
    # -------------------------------------------------------------------------

    def tickers(
        self,
        universe_name: str,
        as_of_date: date | None = None,
    ) -> list[str]:
        """Return the ticker list for a named universe.

        Uses the latest versioned snapshot if as_of_date is not specified.
        Returns an empty list if no snapshot is available.

        Args:
            universe_name: Key in UNIVERSE_REGISTRY (e.g. "us_large_cap").
            as_of_date: Snapshot date. None = most recent available.
        """
        return self._service.tickers(universe_name, as_of_date)

    def snapshot_info(
        self,
        universe_name: str,
        as_of_date: date | None = None,
    ) -> UniverseSnapshot | None:
        """Return snapshot metadata for a named universe.

        Args:
            universe_name: Key in UNIVERSE_REGISTRY.
            as_of_date: Snapshot date. None = most recent available.
        """
        return self._service.snapshot_info(universe_name, as_of_date)

    # -------------------------------------------------------------------------
    # Build trigger (called from sbfoundation api.py after screener ingestion)
    # -------------------------------------------------------------------------

    def materialize_snapshots(
        self,
        as_of_date: date,
        run_id: str,
        universe_names: list[str] | None = None,
    ) -> dict[str, int]:
        """Materialize universe_member and universe_snapshot for each universe.

        Called by SBFoundationAPI._handle_market() after screener ingestion
        completes. Reads silver.fmp_market_screener and aggregates per universe.

        Args:
            as_of_date: The ingestion date for the snapshots.
            run_id: Current pipeline run ID (for lineage).
            universe_names: Subset of UNIVERSE_REGISTRY keys to process.
                            None = all registered universes.

        Returns:
            Dict mapping universe_name → member_count written.
        """
        targets = universe_names or list(UNIVERSE_REGISTRY.keys())
        results: dict[str, int] = {}
        for name in targets:
            ud = UNIVERSE_REGISTRY.get(name)
            if ud is None:
                self._logger.warning(f"Unknown universe '{name}' — skipping", run_id=run_id)
                continue
            count = self._service.materialize_snapshot(ud, as_of_date, run_id)
            results[name] = count
        return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m sbuniverse.api",
        description="sbuniverse CLI — query or trigger universe builds",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # tickers sub-command
    t = sub.add_parser("tickers", help="Print ticker list for a universe")
    t.add_argument("--universe", required=True, help="Universe name (e.g. us_large_cap)")
    t.add_argument("--date", dest="as_of_date", default=None, help="Snapshot date YYYY-MM-DD (default: latest)")

    # snapshot sub-command
    s = sub.add_parser("snapshot", help="Print snapshot metadata for a universe")
    s.add_argument("--universe", required=True, help="Universe name")
    s.add_argument("--date", dest="as_of_date", default=None, help="Snapshot date YYYY-MM-DD (default: latest)")

    # list sub-command
    sub.add_parser("list", help="List all registered universes")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv or sys.argv[1:])

    with UniverseAPI() as api:
        if args.command == "tickers":
            as_of = date.fromisoformat(args.as_of_date) if args.as_of_date else None
            tickers = api.tickers(args.universe, as_of)
            if not tickers:
                print(f"No snapshot found for universe='{args.universe}'", file=sys.stderr)
                sys.exit(1)
            for t in tickers:
                print(t)

        elif args.command == "snapshot":
            as_of = date.fromisoformat(args.as_of_date) if args.as_of_date else None
            snap = api.snapshot_info(args.universe, as_of)
            if snap is None:
                print(f"No snapshot found for universe='{args.universe}'", file=sys.stderr)
                sys.exit(1)
            print(f"universe   : {snap.universe_name}")
            print(f"as_of_date : {snap.as_of_date}")
            print(f"members    : {snap.member_count}")
            print(f"filter_hash: {snap.filter_hash}")
            print(f"run_id     : {snap.run_id}")
            print(f"created_at : {snap.created_at}")

        elif args.command == "list":
            for name, ud in UNIVERSE_REGISTRY.items():
                print(f"{name:<25} {ud.description}")


if __name__ == "__main__":
    main()
