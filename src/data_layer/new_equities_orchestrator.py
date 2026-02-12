from dataclasses import dataclass, field
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
from data_layer.services.universe_service import UniverseService
from data_layer.services.instrument_resolution_service import InstrumentResolutionService


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

    def __init__(self, settings: NewEquitiesOrchestrationSettings, today: str, logger=None, ops_service: OpsService | None = None) -> None:
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
        run_summary = self._start_run()

        self.logger.info(
            f"Starting new equities orchestration: new_tickers={len(run_summary.new_tickers)}, " f"ticker_limit={self.settings.ticker_limit}"
        )

        # Step 1: Load instrument via stock-list recipe
        run_summary = self._step1_load_instrument(run_summary)

        # Step 2: Run company-profile recipes
        run_summary = self._step2_company_profile(run_summary)

        # Step 3: Run domain recipes (company, fundamentals, technicals)
        run_summary = self._step3_domain_recipes(run_summary)

        # Close out the ops metrics
        self.ops_service.finish_run(run_summary)
        self._universe_service.close()
        self._instrument_resolver.close()
        self.logger.info(f"New equities orchestration complete. {run_summary.msg}  Elapsed time: {run_summary.formatted_elapsed_time}")

        return run_summary

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

    def _step1_load_instrument(self, run_summary: RunContext) -> RunContext:
        """Step 1: Load instrument via stock-list recipe to bronze → silver."""
        self.logger.info("Step 1: Loading instrument data via stock-list recipe")

        # Find the stock-list recipe (domain: instrument, source: fmp, dataset: stock-list)
        stock_list_recipes = [r for r in self._dataset_service.recipes if r.domain == INSTRUMENT_DOMAIN and r.dataset == STOCK_LIST_DATASET]

        if not stock_list_recipes:
            self.logger.warning("No stock-list recipe found, skipping instrument discovery")
            return run_summary

        # Process bronze
        if self.settings.enable_bronze:
            self.logger.info(f"Processing {len(stock_list_recipes)} stock-list recipes for bronze")
            run_summary = self._process_recipe_list(stock_list_recipes, run_summary)

        # Promote to silver
        if self.settings.enable_silver:
            run_summary = self._promote_silver(run_summary)

        self.logger.info("Step 1 complete: Instrument data loaded")
        return run_summary

    def _step2_company_profile(self, run_summary: RunContext) -> RunContext:
        """Step 2: Run company-profile recipes with instrument_sk linkage.

        This populates company profile data and links to instruments via instrument_sk.
        Tickers that previously failed with "INVALID TICKER" are excluded and replaced
        with additional tickers to maintain the ticker_limit.
        """
        self.logger.info("Step 2: Loading company-profile data")

        # Refresh tickers from the newly populated dim_instrument
        if not run_summary.new_tickers:
            new_tickers = self._universe_service.new_tickers(
                limit=self.settings.ticker_limit,
                instrument_type=INSTRUMENT_TYPE_EQUITY,
                is_active=True,
            )
            run_summary.new_tickers = new_tickers
            run_summary.tickers = new_tickers

        # Filter out tickers that previously failed with "INVALID TICKER" error
        invalid_tickers = self.ops_service.get_tickers_with_bronze_error(
            dataset=COMPANY_INFO_DATASET,
            error_contains="INVALID TICKER",
        )
        if invalid_tickers:
            original_count = len(run_summary.tickers)
            valid_tickers = [t for t in run_summary.tickers if t not in invalid_tickers]
            removed_count = original_count - len(valid_tickers)

            if removed_count > 0:
                self.logger.info(f"Filtered {removed_count} tickers with previous INVALID TICKER errors")

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
                        self.logger.info(f"Backfilled {len(backfill_tickers)} additional tickers")
                        valid_tickers.extend(backfill_tickers)

                run_summary.new_tickers = valid_tickers
                run_summary.tickers = valid_tickers

        if not run_summary.tickers:
            self.logger.info("No new tickers to process for company-profile")
            return run_summary

        # Find company-profile recipes
        company_profile_recipes = [r for r in self._dataset_service.recipes if r.dataset == COMPANY_INFO_DATASET]

        if not company_profile_recipes:
            self.logger.warning("No company-profile recipe found")
            return run_summary

        # Process ticker-based recipes for company-profile
        run_summary = self._process_ticker_recipes(company_profile_recipes, run_summary, "company-profile")

        self.logger.info("Step 2 complete: Company-profile data loaded")
        return run_summary

    def _step3_domain_recipes(self, run_summary: RunContext) -> RunContext:
        """Step 3: Run domain recipes (company, fundamentals, technicals).

        These all relate back to the instrument via instrument_sk.
        If settings.exchanges is specified, tickers are filtered to only include
        instruments on those exchanges.
        """
        self.logger.info("Step 3: Loading domain data (company, fundamentals, technicals)")

        # Filter tickers by exchange if exchanges filter is specified
        if self.settings.exchanges:
            self.logger.info(f"Filtering tickers by exchanges: {self.settings.exchanges}")
            exchange_tickers = self._instrument_resolver.get_tickers_by_exchanges(
                exchanges=self.settings.exchanges,
                instrument_type=INSTRUMENT_TYPE_EQUITY,
                limit=self.settings.ticker_limit,
            )
            if exchange_tickers:
                filtered_tickers = [ticker for ticker, _ in exchange_tickers]
                self.logger.info(f"Found {len(filtered_tickers)} tickers on exchanges {self.settings.exchanges}")
                run_summary.tickers = filtered_tickers
            else:
                self.logger.warning(f"No tickers found for exchanges {self.settings.exchanges}")
                run_summary.tickers = []

        if not run_summary.tickers:
            self.logger.info("No tickers to process for domain recipes")
            return run_summary

        # Process domains in order: company, fundamentals, technicals
        domains_to_process = [COMPANY_DOMAIN, FUNDAMENTALS_DOMAIN, TECHNICALS_DOMAIN]

        for domain in domains_to_process:
            run_summary = self._process_domain(domain, run_summary)

        self.logger.info("Step 3 complete: Domain data loaded")
        return run_summary

    def _process_domain(self, domain: str, run_summary: RunContext) -> RunContext:
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

        self.logger.info(f"Processing domain {domain}: {len(non_ticker_recipes)} non-ticker, {len(ticker_recipes)} ticker recipes")

        # Process non-ticker recipes for this domain
        if non_ticker_recipes:
            if self.settings.enable_bronze:
                run_summary = self._process_recipe_list(non_ticker_recipes, run_summary)
            if self.settings.enable_silver:
                run_summary = self._promote_silver(run_summary)

        # Process ticker recipes for this domain
        if ticker_recipes:
            run_summary = self._process_ticker_recipes(ticker_recipes, run_summary, domain)

        self.logger.info(f"Completed domain processing for: {domain}")
        return run_summary

    def _process_ticker_recipes(
        self,
        recipes: list[DatasetRecipe],
        run_summary: RunContext,
        label: str,
    ) -> RunContext:
        """Process ticker-based recipes using chunking for bronze → silver."""
        if not recipes:
            return run_summary

        self.logger.info(f"Processing {len(recipes)} ticker recipes for: {label}")

        # Use chunk service for ticker processing
        chunk_service = OrchestrationTickerChunkService(
            chunk_size=self.TICKER_RECIPE_CHUNK_SIZE,
            logger=self.logger,
            process_chunk=self._process_recipe_list,
            promote_silver=self._promote_silver,
            silver_enabled=self.settings.enable_silver,
        )
        run_summary = chunk_service.process(recipes, run_summary)

        self.logger.info(f"Completed ticker recipe processing for: {label}")
        return run_summary

    def _process_recipe_list(self, recipes: list[DatasetRecipe], run_summary: RunContext) -> RunContext:
        """Process a list of recipes through the bronze layer."""
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
        """Promote bronze data to silver layer."""
        silver_service = SilverService(
            ops_service=self.ops_service,
            keymap_service=self._dataset_service,
            instrument_resolver=self._instrument_resolver,
        )
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

    orchestrator = NewEquitiesOrchestrationService(
        settings=NewEquitiesOrchestrationSettings(
            enable_bronze=True,
            enable_silver=True,
            ticker_limit=20,
            fmp_plan=FMP_STARTER_PLAN,
            exchanges=["NASDAQ"],
        ),
        today=date.today().isoformat(),
    ).run()
