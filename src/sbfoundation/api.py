from dataclasses import dataclass
from datetime import date
import os
import traceback

from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.maintenance import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.infra.universe_repo import UniverseRepo
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.ops.services.run_stats_reporter import RunStatsReporter
from sbfoundation.recovery.bronze_recovery_repo import BronzeRecoveryRepo
from sbfoundation.recovery.bronze_recovery_service import BronzeRecoveryService
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.bronze import BronzeService
from sbfoundation.gold import GoldDimService, GoldFactService
from sbfoundation.silver import SilverService
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

        self._enable_silver = command.enable_silver
        self._concurrent_requests = command.concurrent_requests
        self._force_from_date: str | None = command.force_from_date
        run = self._start_run(command)
        domain = command.domain
        if domain == EOD_DOMAIN:
            run = self._handle_eod(command, run)
        elif domain == QUARTER_DOMAIN:
            run = self._handle_quarter(command, run)
        elif domain == ANNUAL_DOMAIN:
            run = self._handle_annual(command, run)

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

    def _handle_eod(self, command: RunCommand, run: RunContext) -> RunContext:
        """Handle EOD bulk domain — daily bulk price and company profile snapshots."""
        self.logger.log_section(run.run_id, "Processing EOD bulk domain")
        recipes = [r for r in self._dataset_service.recipes if r.domain == EOD_DOMAIN]
        if not recipes:
            self.logger.warning("No EOD bulk recipes found", run_id=run.run_id)
            return run
        self.logger.info(
            f"{self._processing_msg(command.enable_bronze, 'BRONZE')} {len(recipes)} EOD bulk datasets",
            run_id=run.run_id,
        )
        if command.enable_bronze:
            run = self._process_recipe_list(recipes, run)
        run = self._promote_silver(run, EOD_DOMAIN)
        self.logger.info("EOD bulk domain complete", run_id=run.run_id)
        return run

    def _handle_quarter(self, command: RunCommand, run: RunContext) -> RunContext:
        """Handle quarterly bulk domain — bulk income statement, balance sheet, cashflow.

        Execution is gated: only runs during earnings seasons (Jan-Mar, Apr-May, Jul-Aug, Oct-Nov).
        """
        from sbfoundation.quarter import QuarterService

        self.logger.log_section(run.run_id, "Processing quarter bulk domain")
        today = date.fromisoformat(self._today)
        if not QuarterService.is_earnings_season(today):
            self.logger.info(
                f"Quarter bulk: outside earnings season ({today}) — skipping",
                run_id=run.run_id,
            )
            return run
        recipes = [r for r in self._dataset_service.recipes if r.domain == QUARTER_DOMAIN]
        if not recipes:
            self.logger.warning("No quarterly bulk recipes found", run_id=run.run_id)
            return run
        self.logger.info(
            f"{self._processing_msg(command.enable_bronze, 'BRONZE')} {len(recipes)} quarterly bulk datasets",
            run_id=run.run_id,
        )
        if command.enable_bronze:
            run = self._process_recipe_list(recipes, run)
        run = self._promote_silver(run, QUARTER_DOMAIN)
        self.logger.info("Quarter bulk domain complete", run_id=run.run_id)
        return run

    def _handle_annual(self, command: RunCommand, run: RunContext) -> RunContext:
        """Handle annual bulk domain — bulk income statement, balance sheet, cashflow (FY).

        Execution is gated: only runs Jan-Mar (annual filing window).
        """
        from sbfoundation.annual import AnnualService

        self.logger.log_section(run.run_id, "Processing annual bulk domain")
        today = date.fromisoformat(self._today)
        if not AnnualService.is_annual_season(today):
            self.logger.info(
                f"Annual bulk: outside annual filing season ({today}) — skipping",
                run_id=run.run_id,
            )
            return run
        recipes = [r for r in self._dataset_service.recipes if r.domain == ANNUAL_DOMAIN]
        if not recipes:
            self.logger.warning("No annual bulk recipes found", run_id=run.run_id)
            return run
        self.logger.info(
            f"{self._processing_msg(command.enable_bronze, 'BRONZE')} {len(recipes)} annual bulk datasets",
            run_id=run.run_id,
        )
        if command.enable_bronze:
            run = self._process_recipe_list(recipes, run)
        run = self._promote_silver(run, ANNUAL_DOMAIN)
        self.logger.info("Annual bulk domain complete", run_id=run.run_id)
        return run

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
        # Close out the run
        run.finished_at = self._universe_service.now()
        self.ops_service.finish_run(run)
        self._universe_service.close()
        self.logger.log_section(run.run_id, "Run complete")
        self.logger.info(f"Run context: {run.msg}  Elapsed time: {run.formatted_elapsed_time}", run_id=run.run_id)

    def _processing_msg(self, enabled: bool, layer: str) -> str:
        return f"PROCESSING {layer} | " if enabled else f"DRY-RUN {layer} |"

    def _process_recipe_list(self, recipes: list[DatasetRecipe], run: RunContext) -> RunContext:
        """Process a list of recipes through the bronze layer."""
        if not recipes:
            return run
        bronze_service = BronzeService(
            ops_service=self.ops_service,
            concurrent_requests=self._concurrent_requests,
            force_from_date=self._force_from_date,
        )
        try:
            return bronze_service.register_recipes(run, recipes).process(run)
        except Exception as exc:
            self.logger.error("Bronze ingestion failed: %s", exc, run_id=run.run_id)
            traceback.print_exc()
            return run

    def _promote_silver(self, run: RunContext, domain: str | None = None) -> RunContext:
        """Promote bronze data to silver layer, restricted to files whose domain matches."""
        silver_service = SilverService(
            enabled=self._enable_silver,
            ops_service=self.ops_service,
            keymap_service=self._dataset_service,
            bootstrap=self._bootstrap,
        )
        try:
            promoted_ids, promoted_rows = silver_service.promote(run, domain=domain)
        except Exception as e:
            self.logger.error(f"Silver promotion: {e}", run_id=run.run_id)
            promoted_ids = []
            promoted_rows = 0
            traceback.print_exc()
        finally:
            silver_service.close()

        run.silver_dto_count += promoted_rows
        return run

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
    )
    result = SBFoundationAPI(today=date.today().isoformat()).run(command)
    print(
        f"run_id={result.run_id}  bronze_passed={result.bronze_files_passed}  bronze_failed={result.bronze_files_failed}  silver_rows={result.silver_dto_count}"
    )

