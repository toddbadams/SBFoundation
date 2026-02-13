from dataclasses import dataclass, field
import traceback

from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.settings import *
from sbfoundation.services.silver.silver_service import SilverService
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.services.bronze.bronze_service import BronzeService
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.run.services.orchestration_ticker_chunk_service import OrchestrationTickerChunkService
from sbfoundation.services.universe_service import UniverseService
from sbfoundation.services.instrument_resolution_service import InstrumentResolutionService


@dataclass(frozen=True)
class NewEquitiesOrchestrationSettings:
    """Settings for orchestrating ingestion of new equity instruments.

    This orchestrator focuses on ingesting data for tickers that have not yet
    been ingested. All ingested data should have instrument_type='equity'.
    """

    # Layer enable switches
    enable_bronze: bool
    enable_silver: bool
    # Limits
    ticker_limit: int  # Max tickers to process
    fmp_plan: str  # Only ingest recipes from this plan
    # Filters
    exchanges: list[str] = field(default_factory=list)  # Filter by exchange (e.g., ["NASDAQ"])

    @property
    def msg(self) -> str:
        return (
            f"enable_bronze={self.enable_bronze} | "
            f"enable_silver={self.enable_silver} | "
            f"ticker_limit={self.ticker_limit} | "
            f"fmp_plan={self.fmp_plan} | "
            f"exchanges={self.exchanges}"
        )


class NewEquitiesOrchestrationService:
    """Orchestrator for ingesting new equity instruments.

    This service ingests equity data for tickers that have not yet been ingested.
    All ingested data has instrument_type='equity'.

    Ingestion steps:
    1. Load the instrument via recipe (domain: instrument, source: fmp, dataset: stock-list)
       into bronze and promote to silver
    2. Run recipes for dataset=company-profile via recipe into bronze and promote to silver
    3. Run recipes for domain=company, then fundamentals, then technicals
    """

    TICKER_RECIPE_CHUNK_SIZE = 10

    def __init__(
        self, settings: NewEquitiesOrchestrationSettings, today: str, logger: SBLogger | None = None, ops_service: OpsService | None = None
    ) -> None:
        self.settings = settings
        self.logger = logger or LoggerFactory().create_logger(__name__)
        self.ops_service = ops_service or OpsService()
        self._today = today
        self._dataset_service = DatasetService(today=today, plan=settings.fmp_plan, logger=self.logger)
        self._universe_service = UniverseService(logger=self.logger)
        self._instrument_resolver = InstrumentResolutionService(logger=self.logger)

    def run(self) -> RunContext:
        """Execute the new equities orchestration pipeline.

        Returns:
            RunContext with metrics from the orchestration run
        """
        # Start the run - we only care about new tickers for this orchestrator
        run = self._start_run()

        self.logger.log_section(
            run.run_id,
            f"Starting new equities orchestration: new_tickers={len(run.new_tickers)}, " f"ticker_limit={self.settings.ticker_limit}",
        )
        self.logger.info(f"new_tickers={len(run.new_tickers)}", run_id=run.run_id)
        self.logger.info(f"{self.settings.msg}", run_id=run.run_id)

        # Step 1: Load instrument via stock-list recipe
        run = self._step1_load_instrument(run)

        # Step 2: Run company-profile recipes
        run = self._step2_company_profile(run)

        # Step 3: Run domain recipes (company, fundamentals, technicals)
        run = self._step3_domain_recipes(run)

        # Close out the ops metrics
        self.ops_service.finish_run(run)
        self._universe_service.close()
        self._instrument_resolver.close()
        self.logger.info(f"New equities orchestration complete. {run.msg}  Elapsed time: {run.formatted_elapsed_time}", run_id=run.run_id)

        return run

    def _start_run(self) -> RunContext:
        """Start a new orchestration run for new equity tickers."""
        # Get new tickers that haven't been ingested yet, filtered by equity type
        new_tickers = self._universe_service.new_tickers(
            limit=self.settings.ticker_limit,
            instrument_type=INSTRUMENT_TYPE_EQUITY,
            is_active=True,
        )

        return RunContext(
            run_id=self._universe_service.run_id(),
            started_at=self._universe_service.now(),
            tickers=new_tickers,
            update_tickers=[],
            new_tickers=new_tickers,
            today=self._universe_service.today().isoformat(),
        )

    def _step1_load_instrument(self, run: RunContext) -> RunContext:
        """Step 1: Load instrument via stock-list recipe to bronze → silver."""
        self.logger.log_section(run.run_id, "Step 1: Loading instrument data via stock-list recipe")

        # Find the stock-list recipe (domain: instrument, source: fmp, dataset: stock-list)
        stock_list_recipes = [r for r in self._dataset_service.recipes if r.domain == INSTRUMENT_DOMAIN and r.dataset == STOCK_LIST_DATASET]

        if not stock_list_recipes:
            self.logger.warning("No stock-list recipe found, skipping instrument discovery", run_id=run.run_id)
            return run

        # Process bronze
        if self.settings.enable_bronze:
            self.logger.info(f"Processing {len(stock_list_recipes)} stock-list recipes for bronze", run_id=run.run_id)
            run = self._process_recipe_list(stock_list_recipes, run)

        # Promote to silver
        if self.settings.enable_silver:
            run = self._promote_silver(run)

        self.logger.info("Step 1 complete: Instrument data loaded", run_id=run.run_id)
        return run

    def _step2_company_profile(self, run: RunContext) -> RunContext:
        """Step 2: Run company-profile recipes with instrument_sk linkage.

        This populates company profile data and links to instruments via instrument_sk.
        Tickers that previously failed with "INVALID TICKER" are excluded and replaced
        with additional tickers to maintain the ticker_limit.
        """
        self.logger.log_section(run.run_id, "Step 2: Loading company-profile data")

        # Refresh tickers from the newly populated dim_instrument
        if not run.new_tickers:
            new_tickers = self._universe_service.new_tickers(
                limit=self.settings.ticker_limit,
                instrument_type=INSTRUMENT_TYPE_EQUITY,
                is_active=True,
            )
            run.new_tickers = new_tickers
            run.tickers = new_tickers

        # Filter out tickers that previously failed with "INVALID TICKER" error
        invalid_tickers = self.ops_service.get_tickers_with_bronze_error(
            dataset=COMPANY_INFO_DATASET,
            error_contains="INVALID TICKER",
        )
        if invalid_tickers:
            original_count = len(run.tickers)
            valid_tickers = [t for t in run.tickers if t not in invalid_tickers]
            removed_count = original_count - len(valid_tickers)

            if removed_count > 0:
                self.logger.info(f"Filtered {removed_count} tickers with previous INVALID TICKER errors", run_id=run.run_id)

                # Backfill with additional tickers to reach ticker_limit
                if len(valid_tickers) < self.settings.ticker_limit:
                    # Get more tickers, excluding both already selected and invalid ones
                    exclude_tickers = set(valid_tickers) | invalid_tickers
                    additional_needed = self.settings.ticker_limit - len(valid_tickers)
                    additional_tickers = self._universe_service.new_tickers(
                        limit=additional_needed + len(exclude_tickers),  # Request extra to account for exclusions
                        instrument_type=INSTRUMENT_TYPE_EQUITY,
                        is_active=True,
                    )
                    # Filter out excluded tickers and take only what we need
                    backfill_tickers = [t for t in additional_tickers if t not in exclude_tickers][:additional_needed]

                    if backfill_tickers:
                        self.logger.info(f"Backfilled {len(backfill_tickers)} additional tickers", run_id=run.run_id)
                        valid_tickers.extend(backfill_tickers)

                run.new_tickers = valid_tickers
                run.tickers = valid_tickers

        if not run.tickers:
            self.logger.info("No new tickers to process for company-profile", run_id=run.run_id)
            return run

        # Find company-profile recipes
        company_profile_recipes = [r for r in self._dataset_service.recipes if r.dataset == COMPANY_INFO_DATASET]

        if not company_profile_recipes:
            self.logger.warning("No company-profile recipe found", run_id=run.run_id)
            return run

        # Process ticker-based recipes for company-profile
        run = self._process_ticker_recipes(company_profile_recipes, run, "company-profile")

        self.logger.info("Step 2 complete: Company-profile data loaded", run_id=run.run_id)
        return run

    def _step3_domain_recipes(self, run: RunContext) -> RunContext:
        """Step 3: Run domain recipes (company, fundamentals, technicals).

        These all relate back to the instrument via instrument_sk.
        If settings.exchanges is specified, tickers are filtered to only include
        instruments on those exchanges.
        """
        self.logger.log_section(run.run_id, "Step 3: Loading domain data (company, fundamentals, technicals)")

        # Filter tickers by exchange if exchanges filter is specified
        if self.settings.exchanges:
            self.logger.info(f"Filtering tickers by exchanges: {self.settings.exchanges}", run_id=run.run_id)
            exchange_tickers = self._instrument_resolver.get_tickers_by_exchanges(
                exchanges=self.settings.exchanges,
                instrument_type=INSTRUMENT_TYPE_EQUITY,
                limit=self.settings.ticker_limit,
            )
            if exchange_tickers:
                filtered_tickers = [ticker for ticker, _ in exchange_tickers]
                self.logger.info(f"Found {len(filtered_tickers)} tickers on exchanges {self.settings.exchanges}", run_id=run.run_id)
                run.tickers = filtered_tickers
            else:
                self.logger.warning(f"No tickers found for exchanges {self.settings.exchanges}", run_id=run.run_id)
                run.tickers = []

        if not run.tickers:
            self.logger.info("No tickers to process for domain recipes", run_id=run.run_id)
            return run

        # Process domains in order: company, fundamentals, technicals
        domains_to_process = [COMPANY_DOMAIN, FUNDAMENTALS_DOMAIN, TECHNICALS_DOMAIN]

        for domain in domains_to_process:
            run = self._process_domain(domain, run)

        self.logger.info("Step 3 complete: Domain data loaded", run_id=run.run_id)
        return run

    def _process_domain(self, domain: str, run: RunContext) -> RunContext:
        """Process all recipes for a single domain through Bronze → Silver.

        This excludes company-profile which is handled in step 2.
        """
        all_recipes = self._dataset_service.recipes
        domain_recipes = [r for r in all_recipes if r.domain == domain]

        # For company domain, exclude company-profile (already processed in step 2)
        if domain == COMPANY_DOMAIN:
            domain_recipes = [r for r in domain_recipes if r.dataset != COMPANY_INFO_DATASET]

        non_ticker_recipes = [r for r in domain_recipes if not r.is_ticker_based]
        ticker_recipes = [r for r in domain_recipes if r.is_ticker_based]

        self.logger.info(f"Processing domain {domain}: {len(non_ticker_recipes)} non-ticker, {len(ticker_recipes)} ticker recipes", run_id=run.run_id)

        # Process non-ticker recipes for this domain
        if non_ticker_recipes:
            if self.settings.enable_bronze:
                run = self._process_recipe_list(non_ticker_recipes, run)
            if self.settings.enable_silver:
                run = self._promote_silver(run)

        # Process ticker recipes for this domain
        if ticker_recipes:
            run = self._process_ticker_recipes(ticker_recipes, run, domain)

        self.logger.info(f"Completed domain processing for: {domain}", run_id=run.run_id)
        return run

    def _process_ticker_recipes(
        self,
        recipes: list[DatasetRecipe],
        run: RunContext,
        label: str,
    ) -> RunContext:
        """Process ticker-based recipes using chunking for bronze → silver."""
        if not recipes:
            return run

        self.logger.info(f"Processing {len(recipes)} ticker recipes for: {label}", run_id=run.run_id)

        # Use chunk service for ticker processing
        chunk_service = OrchestrationTickerChunkService(
            chunk_size=self.TICKER_RECIPE_CHUNK_SIZE,
            logger=self.logger,
            process_chunk=self._process_recipe_list,
            promote_silver=self._promote_silver,
            silver_enabled=self.settings.enable_silver,
        )
        run = chunk_service.process(recipes, run)

        self.logger.info(f"Completed ticker recipe processing for: {label}", run_id=run.run_id)
        return run

    def _process_recipe_list(self, recipes: list[DatasetRecipe], run: RunContext) -> RunContext:
        """Process a list of recipes through the bronze layer."""
        if not recipes:
            return run

        bronze_service = BronzeService(ops_service=self.ops_service)
        try:
            return bronze_service.register_recipes(recipes).process(run)
        except Exception as exc:
            self.logger.error("Bronze ingestion failed: %s", exc, run_id=run.run_id)
            traceback.print_exc()
            return run

    def _promote_silver(self, run: RunContext) -> RunContext:
        """Promote bronze data to silver layer."""
        silver_service = SilverService(
            ops_service=self.ops_service,
            keymap_service=self._dataset_service,
            instrument_resolver=self._instrument_resolver,
        )
        try:
            promoted_ids, promoted_rows = silver_service.promote()
        except Exception as e:
            self.logger.error(f"Silver promotion: {e}", run_id=run.run_id)
            promoted_ids = []
            promoted_rows = 0
            traceback.print_exc()
        finally:
            silver_service.close()

        if promoted_ids:
            self.logger.info("Silver promotion complete. bronze_files=%s | rows=%s", len(promoted_ids), promoted_rows, run_id=run.run_id)
            run.silver_dto_count += promoted_rows
        else:
            self.logger.info("Silver promotion skipped (no promotable Bronze rows).", run_id=run.run_id)

        return run


if __name__ == "__main__":
    from datetime import date

    orchestrator = NewEquitiesOrchestrationService(
        settings=NewEquitiesOrchestrationSettings(
            enable_bronze=True,
            enable_silver=True,
            ticker_limit=1,
            fmp_plan=FMP_PREMIUM_PLAN,
            exchanges=["NASDAQ"],
        ),
        today=date.today().isoformat(),
    ).run()
