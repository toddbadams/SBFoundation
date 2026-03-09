from __future__ import annotations

from pathlib import Path

import duckdb

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance.duckdb_bootstrap import DuckDbBootstrap


class GoldBootstrapService:
    """Applies Gold-layer migrations and verifies static dim tables are populated.

    Called by MaintenanceService after the migration runner completes. Idempotent —
    safe to call multiple times.
    """

    def __init__(
        self,
        bootstrap: DuckDbBootstrap | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap(logger=self._logger)
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    def verify(self) -> dict[str, int]:
        """Return row counts for each static Gold dim table."""
        tables = [
            "gold.dim_date",
            "gold.dim_instrument_type",
            "gold.dim_country",
            "gold.dim_exchange",
            "gold.dim_sector",
            "gold.dim_industry",
        ]
        counts: dict[str, int] = {}
        with self._bootstrap.read_connection() as conn:
            for table in tables:
                try:
                    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                    counts[table] = row[0] if row else 0
                except Exception as exc:
                    self._logger.warning(f"Could not count {table}: {exc}")
                    counts[table] = -1
        return counts
