from __future__ import annotations

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.maintenance.migration_runner import MigrationRunner


class MaintenanceService:
    """Orchestrates database bootstrap, migration runner, and Gold dimension bootstrap.

    Run this before or after a pipeline run to ensure the DB schema is up to date.
    Idempotent — safe to call multiple times.

    Usage:
        python -m sbfoundation.maintenance
    """

    def __init__(self, logger: SBLogger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)

    def run(self) -> None:
        """Run full maintenance: bootstrap → migrations → Gold dim verification."""
        self._logger.info("Maintenance: start")
        bootstrap = DuckDbBootstrap(logger=self._logger)
        try:
            # 1. Bootstrap ensures ops/silver/gold schemas and core tables exist
            bootstrap.connect()
            self._logger.info("Maintenance: schema bootstrap complete")

            # 2. Apply pending SQL migrations
            runner = MigrationRunner(bootstrap=bootstrap, logger=self._logger)
            applied = runner.run()
            if applied:
                self._logger.info(f"Maintenance: applied {len(applied)} migration(s): {applied}")
            else:
                self._logger.info("Maintenance: no pending migrations")

            # 3. Verify Gold static dims are populated
            from sbfoundation.gold import GoldBootstrapService
            gold_svc = GoldBootstrapService(bootstrap=bootstrap, logger=self._logger)
            counts = gold_svc.verify()
            for table, count in counts.items():
                self._logger.info(f"Maintenance: {table} rows={count}")
        finally:
            bootstrap.close()

        self._logger.info("Maintenance: complete")
