from dataclasses import dataclass
import traceback

from data_layer.dataset.services.dataset_service import DatasetService
from settings import *
from data_layer.services.silver.silver_service import SilverService
from data_layer.infra.logger import LoggerFactory
from data_layer.services.bronze.bronze_service import BronzeService
from data_layer.run.dtos.run_context import RunContext
from data_layer.dataset.models.dataset_recipe import DatasetRecipe
from data_layer.ops.services.ops_service import OpsService
from data_layer.run.services.orchestration_ticker_chunk_service import OrchestrationTickerChunkService


# c:/sb/SBFoundation/data/duckdb/sb/SBFoundation.duckdb
@dataclass(frozen=True)
class OrchestrationSettings:
    # Domain enable switches
    enable_instrument: bool
    enable_economics: bool
    enable_company: bool
    enable_fundamentals: bool
    enable_technicals: bool
    # Layer enable switches
    enable_bronze: bool
    enable_silver: bool
    # Run type switches
    enable_non_ticker_run: bool
    enable_ticker_run: bool
    # Ticker mode switches (for ticker runs)
    enable_update_tickers: bool  # Process tickers already ingested
    enable_new_tickers: bool  # Process new tickers from instrument dimensions
    # Limits
    non_ticker_recipe_limit: int
    ticker_recipe_limit: int
    update_ticker_limit: int  # Max tickers to process in update mode
    new_ticker_limit: int  # Max tickers to process in new mode
    fmp_plan: str

    @property
    def ticker_limit(self) -> int:
        """Total ticker limit (sum of update and new limits when both enabled)."""
        total = 0
        if self.enable_update_tickers:
            total += self.update_ticker_limit
        if self.enable_new_tickers:
            total += self.new_ticker_limit
        return total

    def is_domain_enabled(self, domain: str) -> bool:
        """Check if a specific domain is enabled."""
        domain_switches = {
            INSTRUMENT_DOMAIN: self.enable_instrument,
            ECONOMICS_DOMAIN: self.enable_economics,
            COMPANY_DOMAIN: self.enable_company,
            FUNDAMENTALS_DOMAIN: self.enable_fundamentals,
            TECHNICALS_DOMAIN: self.enable_technicals,
        }
        return domain_switches.get(domain, False)

    def enabled_domains(self) -> list[str]:
        """Return list of enabled domains in execution order."""
        return [d for d in DOMAIN_EXECUTION_ORDER if self.is_domain_enabled(d)]


class Orchestrator:
    TICKER_RECIPE_CHUNK_SIZE = 10

    def __init__(self, switches: OrchestrationSettings, today: str, logger=None, ops_service: OpsService | None = None) -> None:
        self.switches = switches or OrchestrationSettings()
        self.logger = logger or LoggerFactory().create_logger(__name__)
        self.ops_service = ops_service or OpsService()
        self._today = today
        self._dataset_service = DatasetService(today=today, plan=switches.fmp_plan, logger=self.logger)

    def run(self) -> RunContext:
        # start the run summary to capture ops metrics during the run
        run_summary = self.ops_service.start_run(
            update_ticker_limit=self.switches.update_ticker_limit,
            new_ticker_limit=self.switches.new_ticker_limit,
            enable_update_tickers=self.switches.enable_update_tickers,
            enable_new_tickers=self.switches.enable_new_tickers,
        )

        self.logger.info(
            f"Starting orchestration: update_tickers={len(run_summary.update_tickers)}, "
            f"new_tickers={len(run_summary.new_tickers)}, total={len(run_summary.tickers)}"
        )

        # process each domain in order, completing Bronze -> Silver before next domain
        for domain in DOMAIN_EXECUTION_ORDER:
            if not self.switches.is_domain_enabled(domain):
                self.logger.info(f"Skipping disabled domain: {domain}")
                continue

            self.logger.info(f"Processing domain: {domain}")
            run_summary = self._process_domain(domain, run_summary)

        # close out the ops metrics
        self.ops_service.finish_run(run_summary)
        self.logger.info(f"Orchestration complete. {run_summary.msg}  Elapsed time: {run_summary.formatted_elapsed_time}")

        return run_summary

    def _process_domain(self, domain: str, run_summary: RunContext) -> RunContext:
        """Process all recipes for a single domain through Bronze -> Silver."""
        all_recipes = self._dataset_service.recipes
        domain_recipes = [r for r in all_recipes if r.domain == domain]

        non_ticker_recipes = [r for r in domain_recipes if not r.is_ticker_based]
        ticker_recipes = [r for r in domain_recipes if r.is_ticker_based]

        # Process non-ticker recipes for this domain
        if self.switches.enable_non_ticker_run and non_ticker_recipes:
            run_summary = self._process_domain_non_ticker(domain, non_ticker_recipes, run_summary)

        # Process ticker recipes for this domain
        if self.switches.enable_ticker_run and ticker_recipes:
            run_summary = self._process_domain_ticker(domain, ticker_recipes, run_summary)

        return run_summary

    def _process_domain_non_ticker(self, domain: str, recipes: list[DatasetRecipe], run_summary: RunContext) -> RunContext:
        """Process non-ticker recipes for a domain with Bronze -> Silver."""
        self.logger.info(f"Processing {len(recipes)} non-ticker recipes for domain: {domain}")

        # Special handling for instrument domain: respect execution phases
        if domain == INSTRUMENT_DOMAIN:
            # Phase 1: instrument_discovery recipes
            discovery_recipes = [r for r in recipes if r.execution_phase == EXECUTION_PHASE_INSTRUMENT_DISCOVERY]
            if discovery_recipes and self.switches.enable_bronze:
                limited = discovery_recipes[: self.switches.non_ticker_recipe_limit]
                self.logger.info(f"Processing {len(limited)} instrument discovery recipes (phase 1)")
                run_summary = self._process_recipe_list(limited, run_summary)
                if self.switches.enable_silver:
                    run_summary = self._promote_silver(run_summary)

            # Phase 2: data_acquisition recipes
            acquisition_recipes = [r for r in recipes if r.execution_phase == EXECUTION_PHASE_DATA_ACQUISITION]
            if acquisition_recipes and self.switches.enable_bronze:
                limited = acquisition_recipes[: self.switches.non_ticker_recipe_limit]
                self.logger.info(f"Processing {len(limited)} instrument data acquisition recipes (phase 2)")
                run_summary = self._process_recipe_list(limited, run_summary)
        else:
            # Standard non-ticker processing for other domains
            if self.switches.enable_bronze:
                limited = recipes[: self.switches.non_ticker_recipe_limit]
                run_summary = self._process_recipe_list(limited, run_summary)

        # Silver promotion for this domain
        if self.switches.enable_silver:
            run_summary = self._promote_silver(run_summary)

        self.logger.info(f"Completed non-ticker processing for domain: {domain}")
        return run_summary

    def _process_domain_ticker(self, domain: str, recipes: list[DatasetRecipe], run_summary: RunContext) -> RunContext:
        """Process ticker recipes for a domain using chunking."""
        self.logger.info(f"Processing {len(recipes)} ticker recipes for domain: {domain}")
        limited = recipes[: self.switches.ticker_recipe_limit]

        if not limited:
            return run_summary

        chunk_service = OrchestrationTickerChunkService(
            chunk_size=self.TICKER_RECIPE_CHUNK_SIZE,
            logger=self.logger,
            process_chunk=self._process_recipe_list,
            promote_silver=self._promote_silver,
            silver_enabled=self.switches.enable_silver,
        )
        run_summary = chunk_service.process(limited, run_summary)
        self.logger.info(f"Completed ticker processing for domain: {domain}")
        return run_summary

    def _process_recipe_list(self, recipes: list[DatasetRecipe], run_summary: RunContext) -> RunContext:
        if not recipes:
            return run_summary

        bronze_service = BronzeService(ops_service=self.ops_service)
        try:
            return bronze_service.register_recipes(recipes).process(run_summary)
        except Exception as exc:
            self.logger.error("Bronze ingestion failed: %s", exc)
            traceback.print_exc()
            return run_summary

    def _promote_silver(self, run_summary: RunContext) -> RunContext:
        silver_service = SilverService(ops_service=self.ops_service, keymap_service=self._dataset_service)
        try:
            promoted_ids, promoted_rows = silver_service.promote()
        except Exception as e:
            self.logger.error(f"Silver promotion: {e}")
            promoted_ids = []
            promoted_rows = 0
            traceback.print_exc()
        finally:
            silver_service.close()

        if promoted_ids:
            self.logger.info("Silver promotion complete. bronze_files=%s | rows=%s", len(promoted_ids), promoted_rows)
            run_summary.silver_dto_count += promoted_rows
        else:
            self.logger.info("Silver promotion skipped (no promotable Bronze rows).")

        return run_summary


if __name__ == "__main__":
    from datetime import date

    orchestrator = Orchestrator(
        switches=OrchestrationSettings(
            enable_instrument=False,
            enable_economics=False,
            enable_company=True,
            enable_fundamentals=False,
            enable_technicals=False,
            enable_bronze=True,
            enable_silver=False,
            enable_non_ticker_run=False,
            enable_ticker_run=True,
            enable_update_tickers=False,
            enable_new_tickers=True,
            non_ticker_recipe_limit=99,
            ticker_recipe_limit=99,
            update_ticker_limit=0,
            new_ticker_limit=10,
            fmp_plan=FMP_STARTER_PLAN,
        ),
        today=date.today().isoformat(),
    ).run()
