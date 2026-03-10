from dataclasses import dataclass
from datetime import date
import os
import traceback

from sbfoundation.annual import AnnualService
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.eod import EodService
from sbfoundation.gold import GoldDimService, GoldFactService
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.infra.universe_repo import UniverseRepo
from sbfoundation.maintenance import DuckDbBootstrap
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.ops.services.run_stats_reporter import RunStatsReporter
from sbfoundation.quarter import QuarterService
from sbfoundation.recovery.bronze_recovery_repo import BronzeRecoveryRepo
from sbfoundation.recovery.bronze_recovery_service import BronzeRecoveryService
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services import BulkPipelineService
from sbfoundation.services.universe_service import UniverseService
from sbfoundation.settings import *


@dataclass(slots=True)
class RunCommand:

    domain: str  # Allows running a specific data category

    concurrent_requests: int  # Max concurrent workers for Bronze requests. Set to 1 for sync/debug mode.
    enable_bronze: bool  # True to load source APIs into json files, else logs a dry run of requests
    enable_silver: bool  # True promotes loaded bronze json files into silver database
    enable_gold: bool = True  # True promotes silver data into gold dims + facts (runs only when enable_silver is True)
    ticker_limit: int = 0  # Max tickers to process
    ticker_recipe_chunk_size: int = 0  # number of recipes to run per chunk

    force_from_date: str | None = None  # ISO date (e.g. "1990-01-01"); bypasses watermarks for historical backfill
    year: int | None = None  # Optional calendar year filter passed to annual bulk datasets

    def validate(self) -> None:
        """Validate this RunCommand. Raises ValueError on invalid input."""
        if self.domain not in DOMAINS:
            raise ValueError(f"Invalid domain '{self.domain}'. Must be one of: {DOMAINS}")


class SBFoundationAPI:

    def __init__(
        self,
        today: str | None = None,
        logger: SBLogger | None = None,
        ops_service: OpsService | None = None,
        dataset_service: DatasetService | None = None,
        universe_service: UniverseService | None = None,
        recovery_service: BronzeRecoveryService | None = None,
    ) -> None:
        self.logger = logger or LoggerFactory().create_logger(__name__)
        self._bootstrap = DuckDbBootstrap(logger=self.logger)
        universe_repo = UniverseRepo(logger=self.logger, bootstrap=self._bootstrap)
        self._universe_service = universe_service or UniverseService(repo=universe_repo)
        ops_repo = DuckDbOpsRepo(logger=self.logger, bootstrap=self._bootstrap)
        self.ops_service = ops_service or OpsService(ops_repo=ops_repo, logger=self.logger, universe=self._universe_service)
        recovery_repo = BronzeRecoveryRepo(bootstrap=self._bootstrap)
        self._recovery_service = recovery_service or BronzeRecoveryService(repo=recovery_repo)
        self._today = today or self._universe_service.today().isoformat()
        self._dataset_service = dataset_service or DatasetService(today=self._today)
        self._fmp_api_key = os.getenv("FMP_API_KEY")
        # Lazy import to avoid circular dependency:
        # sbfoundation.__init__ → sbfoundation.api → sbuniverse.api → sbuniverse.infra.universe_repo
        #   → sbfoundation.infra.duckdb_bootstrap → sbfoundation (partially initialized)
        from sbuniverse.api import UniverseAPI
        from sbuniverse.universe_definitions import UNIVERSE_REGISTRY as _UNIVERSE_REGISTRY

        self._universe_api = UniverseAPI(logger=self.logger)
        self._universe_registry = _UNIVERSE_REGISTRY

    def run(self, command: RunCommand) -> RunContext:
        """
        Executes a domain-action command through the ingestion engine.
        """
        command.validate()

        if self._recovery_service.needs_recovery():
            self.logger.info("ops.file_ingestions is empty — recovering from bronze files")
            self._recovery_service.recover()

        run = self._start_run(command)
        service = self._build_service(command)
        if isinstance(service, AnnualService):
            run = service.run(run, year=command.year)
        else:
            run = service.run(run)

        if command.enable_silver and command.enable_gold:
            self._promote_gold(run)

        self.ops_service.refresh_coverage_index(
            run_id=run.run_id,
            universe_from_date=date.fromisoformat(self._universe_service.from_date),
            today=self._universe_service.today(),
        )

        # Log run-level integrity summary (non-fatal)
        try:
            from sbfoundation.ops.services.data_integrity_service import DataIntegrityService

            integrity_svc = DataIntegrityService(logger=self.logger, bootstrap=self._bootstrap)
            summary = integrity_svc.summary(run.run_id)
            if summary:
                self.logger.info(f"Integrity summary: {summary}", run_id=run.run_id)
            integrity_svc.close()
        except Exception as exc:
            self.logger.warning(f"Integrity summary failed (non-fatal): {exc}", run_id=run.run_id)

        self._close_run(run)

        try:
            reporter = RunStatsReporter(bootstrap=self._bootstrap)
            report_path = reporter.write_report(
                run.run_id,
                universe_tickers=run.tickers or None,
            )
            reporter.close()
            self.logger.info(f"Run report written: {report_path}", run_id=run.run_id)
        except Exception as exc:
            self.logger.warning(f"Run stats reporter failed (non-fatal): {exc}", run_id=run.run_id)

        return run

    def _build_service(self, command: RunCommand) -> BulkPipelineService:
        """Factory: instantiate the correct domain service for this command."""
        # When year is specified without an explicit force_from_date, derive one so the
        # watermark gate (last_ingestion_date >= today) doesn't skip the year-specific fetch.
        force_from_date = command.force_from_date
        if command.year is not None and force_from_date is None:
            force_from_date = f"{command.year}-01-01"

        kwargs: dict = dict(
            ops_service=self.ops_service,
            dataset_service=self._dataset_service,
            bootstrap=self._bootstrap,
            logger=self.logger,
            enable_bronze=command.enable_bronze,
            enable_silver=command.enable_silver,
            concurrent_requests=command.concurrent_requests,
            force_from_date=force_from_date,
            today=self._today,
        )
        if command.domain == EOD_DOMAIN:
            return EodService(**kwargs)
        if command.domain == QUARTER_DOMAIN:
            return QuarterService(**kwargs)
        if command.domain == ANNUAL_DOMAIN:
            return AnnualService(**kwargs)
        raise ValueError(f"Unknown domain: {command.domain}")

    def _start_run(self, command: RunCommand) -> RunContext:
        run = RunContext(
            run_id=self._universe_service.run_id(),
            started_at=self._universe_service.now(),
            tickers=[],
            update_tickers=[],
            today=self._today,
        )
        self.logger.log_section(run.run_id, "Run Start")
        self.logger.info(f"{command}", run_id=run.run_id)
        return run

    def _close_run(self, run: RunContext):
        run.finished_at = self._universe_service.now()
        self.ops_service.finish_run(run)
        self._universe_service.close()
        self.logger.log_section(run.run_id, "Run complete")
        self.logger.info(f"Run context: {run.msg}  Elapsed time: {run.formatted_elapsed_time}", run_id=run.run_id)

    def _promote_gold(self, run: RunContext) -> None:
        """Promote Silver data into Gold dims and facts. Non-fatal on error."""
        self.logger.log_section(run.run_id, "Promoting to Gold")
        try:
            dim_svc = GoldDimService(bootstrap=self._bootstrap, logger=self.logger)
            dim_counts = dim_svc.build(run_id=run.run_id)
            self.logger.info(f"Gold dims: {dim_counts}", run_id=run.run_id)
        except Exception as exc:
            self.logger.error(f"Gold dim promotion failed: {exc}", run_id=run.run_id)
            traceback.print_exc()

        try:
            fact_svc = GoldFactService(bootstrap=self._bootstrap, logger=self.logger)
            fact_counts = fact_svc.build(run_id=run.run_id)
            self.logger.info(f"Gold facts: {fact_counts}", run_id=run.run_id)
        except Exception as exc:
            self.logger.error(f"Gold fact promotion failed: {exc}", run_id=run.run_id)
            traceback.print_exc()


if __name__ == "__main__":
    command = RunCommand(
        domain="eod",
        concurrent_requests=1,  # global datasets: no per-ticker parallelism needed
        enable_bronze=True,
        enable_silver=True,
        enable_gold=True,
    )
    result = SBFoundationAPI(today=date.today().isoformat()).run(command)
    print(
        f"run_id={result.run_id}  bronze_passed={result.bronze_files_passed}  bronze_failed={result.bronze_files_failed}  silver_rows={result.silver_dto_count}"
    )
