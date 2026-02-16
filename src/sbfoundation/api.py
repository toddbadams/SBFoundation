from enum import StrEnum
from dataclasses import dataclass, field
import traceback

from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services.orchestration_ticker_chunk_service import OrchestrationTickerChunkService
from sbfoundation.services.bronze.bronze_service import BronzeService
from sbfoundation.services.instrument_resolution_service import InstrumentResolutionService
from sbfoundation.services.silver.silver_service import SilverService
from sbfoundation.services.universe_service import UniverseService
from sbfoundation.settings import *


@dataclass(slots=True)
class RunCommand:

    domain: str  # Allows running a specific data category

    concurent_requests: int  # the max number of concurrent requests, set to 1 to debug in sync mode
    enable_bronze: bool  # True to load source APIs into json files, else logs a dry run of requests
    enable_silver: bool  # True promotes loaded bronze json files into silver database
    ticker_limit: int  # Max tickers to process
    ticker_recipe_chunk_size: int  # number of recipes to run per chunk

    exchanges: list[str] = field(default_factory=list)  # Filter by exchange (e.g., ["NASDAQ"]) data from dataset=available-exchanges
    sectors: list[str] = field(default_factory=list)  # Filter by sector (e.g., ["Energy"]) data from dataset=available-sector
    industries: list[str] = field(default_factory=list)  # Filter by industry (e.g., ["Oil & Gas Drilling"]) data from dataset=available-industries
    countries: list[str] = field(default_factory=list)  # Filter by country (e.g., ["NASDAQ"]) data from dataset=available-countries


@dataclass(slots=True)
class RunResult:
    run_id: str
    domain: str
    started_at: str
    completed_at: str | None
    status: str
    records_processed: int
    errors: list[str]


class SBFoundationAPI:

    def __init__(
        self,
        today: str | None = None,
        logger: SBLogger | None = None,
        ops_service: OpsService | None = None,
        dataset_service: DatasetService | None = None,
        universe_service: UniverseService | None = None,
        instrument_service: InstrumentResolutionService | None = None,
    ) -> None:
        self.logger = logger or LoggerFactory().create_logger(__name__)
        self.ops_service = ops_service or OpsService()
        self._dataset_service = dataset_service or DatasetService(today=today)
        self._universe_service = universe_service or UniverseService()
        self._instrument_resolver = instrument_service or InstrumentResolutionService()
        self._today = today or self._universe_service.today().isoformat()

    def run(self, command: RunCommand) -> RunResult:
        """
        Executes a domain-action command through the ingestion engine.
        """
        run = self._start_run(command)
        match command.domain:

            case INSTRUMENT_DOMAIN:
                run = self._handle_instruments(command, run)

            case ECONOMICS_DOMAIN:
                run = self._handle_economics(command, run)

            case MARKET_DOMAIN:
                run = self._handle_market(command, run)

            case COMMODITIES_DOMAIN:
                run = self._handle_commodities(command, run)

            case FX_DOMAIN:
                run = self._handle_fx(command, run)

            case CRYPTO_DOMAIN:
                run = self._handle_crypto(command, run)

            case _:
                pass

        self._close_run(run)
        return run

    def _handle_instruments(self, command: RunCommand, run: RunContext) -> RunResult:

        # Step 1: Load instrument via stock-list recipe
        run = self._load_instrument(command, run)

        # Step 2: Run company-profile recipes
        run = self._company_profile(command, run)

        # Step 3: Run domain recipes (company, fundamentals, technicals)
        run = self._domain_recipes(command, run)
        return run

    def _handle_economics(self, command: RunCommand, run: RunContext) -> RunResult:
        return run  # todo: add method to handle

    def _handle_market(self, command: RunCommand, run: RunContext) -> RunResult:
        return run  # todo: add method to handle

    def _handle_commodities(self, command: RunCommand, run: RunContext) -> RunResult:
        return run  # todo: add method to handle

    def _handle_fx(self, command: RunCommand, run: RunContext) -> RunResult:
        return run  # todo: add method to handle

    def _handle_crypto(self, command: RunCommand, run: RunContext) -> RunResult:
        return run  # todo: add method to handle

    def _start_run(self, command: RunCommand) -> RunContext:
        run = RunContext(
            run_id=self._universe_service.run_id(),
            started_at=self._universe_service.now(),
            tickers=self._get_tickers(command),
            update_tickers=[],
            today=self._today,
        )
        self.logger.log_section("Run Start", run_id=run.run_id)
        self.logger.info(f"new_tickers={len(run.new_tickers)}", run_id=run.run_id)
        self.logger.info(f"{command.msg}", run_id=run.run_id)

    def _close_run(self, run: RunContext):
        # Close out the run
        self.ops_service.finish_run(run)
        self._universe_service.close()
        self._instrument_resolver.close()
        self.logger.log_section("Run complete", run_id=run.run_id)
        self.logger.info(f"Run context: {run.msg}  Elapsed time: {run.formatted_elapsed_time}", run_id=run.run_id)

    def _get_tickers(self, command: RunCommand) -> list[str]:
        if command.domain == INSTRUMENT_DOMAIN:
            return self._universe_service.new_tickers(
                limit=command.ticker_limit,
                instrument_type=INSTRUMENT_TYPE_EQUITY,
                is_active=True,
            )

        return None

    def _load_instrument(self, command: RunCommand, run: RunContext) -> RunContext:
        """Load instrument via stock-list recipe to bronze → silver."""
        self.logger.log_section(run.run_id, "Loading instrument data via stock-list recipe")

        # Find the stock-list recipe (domain: instrument, source: fmp, dataset: stock-list)
        stock_list_recipes = [r for r in self._dataset_service.recipes if r.domain == INSTRUMENT_DOMAIN and r.dataset == STOCK_LIST_DATASET]

        if not stock_list_recipes:
            self.logger.warning("No stock-list recipe found, skipping instrument discovery", run_id=run.run_id)
            return run

        # Process bronze
        if command.enable_bronze:
            self.logger.info(f"Processing {len(stock_list_recipes)} stock-list recipes for bronze", run_id=run.run_id)
            run = self._process_recipe_list(stock_list_recipes, run)

        # Promote to silver
        if command.enable_silver:
            run = self._promote_silver(run)

        self.logger.info("Step 1 complete: Instrument data loaded", run_id=run.run_id)
        return run

    def _company_profile(self, command: RunCommand, run: RunContext) -> RunContext:
        """Run company-profile recipes with instrument_sk linkage.

        This populates company profile data and links to instruments via instrument_sk.
        Tickers that previously failed with "INVALID TICKER" are excluded and replaced
        with additional tickers to maintain the ticker_limit.
        """
        self.logger.log_section(run.run_id, "Loading company-profile data")

        # Refresh tickers from the newly populated dim_instrument
        if not run.new_tickers:
            new_tickers = self._universe_service.new_tickers(
                limit=command.ticker_limit,
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
                if len(valid_tickers) < command.ticker_limit:
                    # Get more tickers, excluding both already selected and invalid ones
                    exclude_tickers = set(valid_tickers) | invalid_tickers
                    additional_needed = command.ticker_limit - len(valid_tickers)
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

        self.logger.info("Company-profile data loaded", run_id=run.run_id)
        return run

    def _domain_recipes(self, command: RunCommand, run: RunContext) -> RunContext:
        """Run domain recipes (company, fundamentals, technicals).

        These all relate back to the instrument via instrument_sk.
        If settings.exchanges is specified, tickers are filtered to only include
        instruments on those exchanges.
        """
        self.logger.log_section(run.run_id, "Loading domain data (company, fundamentals, technicals)")

        # Filter tickers by exchange if exchanges filter is specified
        if command.exchanges:
            self.logger.info(f"Filtering tickers by exchanges: {command.exchanges}", run_id=run.run_id)
            exchange_tickers = self._instrument_resolver.get_tickers_by_exchanges(
                exchanges=command.exchanges,
                instrument_type=INSTRUMENT_TYPE_EQUITY,
                limit=command.ticker_limit,
            )
            if exchange_tickers:
                filtered_tickers = [ticker for ticker, _ in exchange_tickers]
                self.logger.info(f"Found {len(filtered_tickers)} tickers on exchanges {command.exchanges}", run_id=run.run_id)
                run.tickers = filtered_tickers
            else:
                self.logger.warning(f"No tickers found for exchanges {command.exchanges}", run_id=run.run_id)
                run.tickers = []

        if not run.tickers:
            self.logger.info("No tickers to process for domain recipes", run_id=run.run_id)
            return run

        # Process domains in order: company, fundamentals, technicals
        domains_to_process = [COMPANY_DOMAIN, FUNDAMENTALS_DOMAIN, TECHNICALS_DOMAIN]

        for domain in domains_to_process:
            run = self._process_domain(domain, run)

        self.logger.info("Domain data loaded", run_id=run.run_id)
        return run

    def _process_domain(self, domain: str, command: RunCommand, run: RunContext) -> RunContext:
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
            if command.enable_bronze:
                run = self._process_recipe_list(non_ticker_recipes, run)
            if command.enable_silver:
                run = self._promote_silver(run)

        # Process ticker recipes for this domain
        if ticker_recipes:
            run = self._process_ticker_recipes(ticker_recipes, run, domain)

        self.logger.info(f"Completed domain processing for: {domain}", run_id=run.run_id)
        return run

    def _process_ticker_recipes(self, recipes: list[DatasetRecipe], command: RunCommand, run: RunContext, label: str) -> RunContext:
        """Process ticker-based recipes using chunking for bronze → silver."""
        if not recipes:
            return run

        self.logger.info(f"Processing {len(recipes)} ticker recipes for: {label}", run_id=run.run_id)

        # Use chunk service for ticker processing
        chunk_service = OrchestrationTickerChunkService(
            chunk_size=command.ticker_recipe_chunk_size,
            logger=self.logger,
            process_chunk=self._process_recipe_list,
            promote_silver=self._promote_silver,
            silver_enabled=command.enable_silver,
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
            return bronze_service.register_recipes(run, recipes).process(run)
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
            promoted_ids, promoted_rows = silver_service.promote(run)
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
