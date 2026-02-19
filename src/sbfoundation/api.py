from dataclasses import dataclass, field
from datetime import date, timedelta
import copy
import os
import traceback

from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.recovery.bronze_recovery_service import BronzeRecoveryService
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.dtos.run_request import RunRequest
from sbfoundation.run.services.orchestration_ticker_chunk_service import OrchestrationTickerChunkService
from sbfoundation.services.bronze.bronze_service import BronzeService
from sbfoundation.services.silver.silver_service import SilverService
from sbfoundation.services.universe_service import UniverseService
from sbfoundation.settings import *
from sbfoundation.settings import (
    COMMODITIES_DOMAIN,
    COMMODITIES_LIST_DATASET,
    COMMODITIES_PRICE_EOD_DATASET,
    COMPANY_DOMAIN,
    CRYPTO_DOMAIN,
    CRYPTO_LIST_DATASET,
    CRYPTO_PRICE_EOD_DATASET,
    FX_DOMAIN,
    FX_LIST_DATASET,
    FX_PRICE_EOD_DATASET,
    FUNDAMENTALS_DOMAIN,
    MARKET_ETF_HOLDINGS_DATASET,
    MARKET_ETF_LIST_DATASET,
    MARKET_INDEX_LIST_DATASET,
    MARKET_STOCK_LIST_DATASET,
    TECHNICALS_DOMAIN,
)


@dataclass(slots=True)
class RunCommand:

    domain: str  # Allows running a specific data category

    concurrent_requests: int  # Max concurrent workers for Bronze requests. Set to 1 for sync/debug mode.
    enable_bronze: bool  # True to load source APIs into json files, else logs a dry run of requests
    enable_silver: bool  # True promotes loaded bronze json files into silver database
    ticker_limit: int = 0  # Max tickers to process
    ticker_recipe_chunk_size: int = 0  # number of recipes to run per chunk

    exchanges: list[str] = field(default_factory=list)  # Filter by exchange (e.g., ["NASDAQ"]) data from dataset=available-exchanges
    sectors: list[str] = field(default_factory=list)  # Filter by sector (e.g., ["Energy"]) data from dataset=available-sector
    industries: list[str] = field(default_factory=list)  # Filter by industry (e.g., ["Oil & Gas Drilling"]) data from dataset=available-industries
    countries: list[str] = field(default_factory=list)  # Filter by country (e.g., ["NASDAQ"]) data from dataset=available-countries

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
        self.ops_service = ops_service or OpsService()
        self._dataset_service = dataset_service or DatasetService(today=today)
        self._universe_service = universe_service or UniverseService()
        self._recovery_service = recovery_service or BronzeRecoveryService()
        self._today = today or self._universe_service.today().isoformat()
        self._fmp_api_key = os.getenv("FMP_API_KEY")

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
        run = self._start_run(command)
        domain = command.domain
        if domain == MARKET_DOMAIN:
            run = self._handle_market(command, run)
        elif domain == ECONOMICS_DOMAIN:
            run = self._handle_economics(command, run)
        elif domain == COMPANY_DOMAIN:
            run = self._handle_company(command, run)
        elif domain == FUNDAMENTALS_DOMAIN:
            run = self._handle_fundamentals(command, run)
        elif domain == TECHNICALS_DOMAIN:
            run = self._handle_technicals(command, run)
        elif domain == COMMODITIES_DOMAIN:
            run = self._handle_commodities(command, run)
        elif domain == FX_DOMAIN:
            run = self._handle_fx(command, run)
        elif domain == CRYPTO_DOMAIN:
            run = self._handle_crypto(command, run)

        self._close_run(run)
        return run

    def _handle_economics(self, command: RunCommand, run: RunContext) -> RunContext:
        """
        Handle economics domain datasets.

        All economics datasets are global (non-ticker-based):
        - treasury-rates (daily U.S. Treasury yield curve)
        - market-risk-premium (annual market risk premium for CAPM)
        - economic-indicators (27 macroeconomic time series with discriminators)
        """
        self.logger.log_section(run.run_id, "Processing economics domain")

        # Get all economics recipes (all are global/non-ticker-based)
        recipes = [r for r in self._dataset_service.recipes if r.domain == ECONOMICS_DOMAIN]

        if not recipes:
            self.logger.warning("No economics recipes found", run_id=run.run_id)
            return run

        self.logger.info(
            f"{self._processing_msg(command.enable_bronze, 'BRONZE')} {len(recipes)} economics datasets",
            run_id=run.run_id,
        )

        # Process all economics recipes through bronze
        if command.enable_bronze:
            run = self._process_recipe_list(recipes, run)

        # Promote to silver
        run = self._promote_silver(run, ECONOMICS_DOMAIN)

        self.logger.info(f"Economics domain complete: {len(recipes)} datasets processed", run_id=run.run_id)
        return run

    def _handle_market(self, command: RunCommand, run: RunContext) -> RunContext:
        # Phase 0: stock-list, etf-list, index-list, etf-holdings (universe discovery)
        list_datasets = [
            MARKET_STOCK_LIST_DATASET,
            MARKET_ETF_LIST_DATASET,
            MARKET_INDEX_LIST_DATASET,
            MARKET_ETF_HOLDINGS_DATASET,
        ]
        run = self._run_market_baseline(list_datasets, command, run)
        run = self._promote_silver(run, MARKET_DOMAIN)

        # Phase 1a: countries (no dependencies — must run first)
        run = self._run_market_baseline([MARKET_COUNTRIES_DATASET], command, run)
        run = self._promote_silver(run, MARKET_DOMAIN)

        # Phase 1b: exchanges, sectors, industries
        run = self._run_market_baseline(
            [MARKET_EXCHANGES_DATASET, MARKET_SECTORS_DATASET, MARKET_INDUSTRIES_DATASET],
            command,
            run,
        )
        run = self._promote_silver(run, MARKET_DOMAIN)

        # Phase 1c: market-screener (per country — authoritative symbol→dimension mapping)
        run = self._run_market_screener(command, run)

        # Phase 2a: market-hours (daily snapshot, as_of_date = today from DTO default)
        run = self._run_market_baseline([MARKET_HOURS_DATASET], command, run)
        run = self._promote_silver(run, MARKET_DOMAIN)

        # Phase 2b: date-loop datasets (sector/industry performance + PE)
        date_datasets = [
            MARKET_SECTOR_PERFORMANCE_DATASET,
            MARKET_INDUSTRY_PERFORMANCE_DATASET,
            MARKET_SECTOR_PE_DATASET,
            MARKET_INDUSTRY_PE_DATASET,
        ]
        run = self._run_market_date_loop(date_datasets, command, run)

        # Phase 2c: market-holidays (per-exchange, exchange codes from silver)
        run = self._run_market_holidays(command, run)

        return run

    def _handle_company(self, command: RunCommand, run: RunContext) -> RunContext:
        """
        Handle company domain datasets.

        Tickers are filtered from silver via exchange/sector/industry/country dimension filters.
        All filters are optional; all empty returns the full universe.
        """
        self.logger.log_section(run.run_id, "Processing company domain")
        tickers = self._get_filtered_universe(command, run.run_id)
        if not tickers:
            self.logger.warning("No tickers found for company domain — skipping", run_id=run.run_id)
            return run
        run.tickers = tickers
        self.logger.info(f"Company domain: {len(tickers)} tickers", run_id=run.run_id)
        return self._process_domain(COMPANY_DOMAIN, command, run)

    def _handle_fundamentals(self, command: RunCommand, run: RunContext) -> RunContext:
        """
        Handle fundamentals domain datasets.

        Tickers are filtered from silver via exchange/sector/industry/country dimension filters.
        All filters are optional; all empty returns the full universe.
        """
        self.logger.log_section(run.run_id, "Processing fundamentals domain")
        tickers = self._get_filtered_universe(command, run.run_id)
        if not tickers:
            self.logger.warning("No tickers found for fundamentals domain — skipping", run_id=run.run_id)
            return run
        run.tickers = tickers
        self.logger.info(f"Fundamentals domain: {len(tickers)} tickers", run_id=run.run_id)
        return self._process_domain(FUNDAMENTALS_DOMAIN, command, run)

    def _handle_technicals(self, command: RunCommand, run: RunContext) -> RunContext:
        """
        Handle technicals domain datasets.

        Tickers are filtered from silver via exchange/sector/industry/country dimension filters.
        All filters are optional; all empty returns the full universe.
        """
        self.logger.log_section(run.run_id, "Processing technicals domain")
        tickers = self._get_filtered_universe(command, run.run_id)
        if not tickers:
            self.logger.warning("No tickers found for technicals domain — skipping", run_id=run.run_id)
            return run
        run.tickers = tickers
        self.logger.info(f"Technicals domain: {len(tickers)} tickers", run_id=run.run_id)
        return self._process_domain(TECHNICALS_DOMAIN, command, run)

    def _processing_msg(self, enabled: bool, layer: str) -> str:
        return f"PROCESSING {layer} | " if enabled else f"DRY-RUN {layer} |"

    def _string_list_msg(self, l: list[str], name: str) -> str:
        return f"{len(l)} {name}: {', '.join(l)}"

    def _run_market_baseline(self, dataset_names: list[str], command: RunCommand, run: RunContext) -> RunContext:
        """Process one or more global (non-ticker) market recipes through bronze."""
        recipes = [r for r in self._dataset_service.recipes if r.domain == MARKET_DOMAIN and r.dataset in dataset_names]
        if not recipes:
            self.logger.warning(f"No recipes found for market {self._string_list_msg(dataset_names, 'datasets')}", run_id=run.run_id)
            return run

        self.logger.info(
            f"{self._processing_msg(command.enable_bronze, 'BRONZE')} {self._string_list_msg(dataset_names, 'datasets')}", run_id=run.run_id
        )
        if command.enable_bronze:
            run = self._process_recipe_list(recipes, run)

        return run

    def _run_market_date_loop(self, dataset_names: list[str], command: RunCommand, run: RunContext) -> RunContext:
        """Fetch date-snapshot market datasets for each weekday from watermark to today.

        Collects ALL (date × recipe) requests upfront then dispatches them as a single
        concurrent batch, honouring concurrent_requests workers instead of running
        sequentially per calendar day.
        """
        recipes = [r for r in self._dataset_service.recipes if r.domain == MARKET_DOMAIN and r.dataset in dataset_names]
        if not recipes:
            self.logger.warning(f"No recipes found for {self._string_list_msg(dataset_names, 'datasets')}", run_id=run.run_id)
            return run

        # Determine the earliest watermark across datasets (start from default if no watermark).
        # Each calendar-date snapshot is stored under its own discriminator (e.g. "2013-01-01"),
        # so we must query MAX(silver_to_date) across ALL discriminators for the dataset rather
        # than filtering by discriminator="" which would never match.
        default_start = date(2013, 1, 1)
        watermarks: list[date] = []
        for dataset_name in dataset_names:
            w = self.ops_service.get_silver_watermark_for_dataset(
                domain=MARKET_DOMAIN,
                source=FMP_DATA_SOURCE,
                dataset=dataset_name,
            )
            watermarks.append(w if w else default_start)

        from_date = min(watermarks) if watermarks else default_start
        today = date.fromisoformat(self._today)
        market_days = self._market_weekdays(from_date, today)

        self.logger.info(
            f"Date-loop: {len(market_days)} market days × {len(recipes)} datasets = "
            f"{len(market_days) * len(recipes)} requests | workers={self._concurrent_requests}",
            run_id=run.run_id,
        )

        if command.enable_bronze and market_days:
            # Collect ALL requests across every (date × recipe) combination upfront so the
            # full batch can be dispatched concurrently rather than one date at a time.
            all_requests: list[RunRequest] = []
            for snapshot_date_val in market_days:
                snapshot_str = snapshot_date_val.isoformat()
                for r in recipes:
                    patched = copy.copy(r)
                    patched.query_vars = {k: snapshot_str if v == DATE_PLACEHOLDER else v for k, v in (r.query_vars or {}).items()}
                    patched.discriminator = snapshot_str
                    all_requests.append(
                        RunRequest.from_recipe(
                            recipe=patched,
                            run_id=run.run_id,
                            from_date=self._universe_service.from_date,
                            today=run.today,
                            api_key=self._fmp_api_key,
                        )
                    )

            bronze_service = BronzeService(
                ops_service=self.ops_service,
                concurrent_requests=self._concurrent_requests,
            )
            run = bronze_service.execute_requests(all_requests, run)

        run = self._promote_silver(run, MARKET_DOMAIN)
        return run

    def _run_market_holidays(self, command: RunCommand, run: RunContext) -> RunContext:
        """Fetch market-holidays for each exchange code found in silver.fmp_market_exchanges."""
        recipes = [r for r in self._dataset_service.recipes if r.domain == MARKET_DOMAIN and r.dataset == MARKET_HOLIDAYS_DATASET]
        if not recipes:
            self.logger.warning("No recipe found for market-holidays", run_id=run.run_id)
            return run

        # Query silver for exchange codes
        exchange_codes = self._get_silver_exchange_codes()
        if not exchange_codes:
            self.logger.info("No exchange codes found in silver.fmp_market_exchanges — skipping market-holidays", run_id=run.run_id)
            return run

        self.logger.info(
            f"{self._processing_msg(command.enable_bronze, 'BRONZE')} market-holidays for {len(exchange_codes)} exchanges", run_id=run.run_id
        )
        original_tickers = run.tickers
        run.tickers = exchange_codes

        chunk_service = OrchestrationTickerChunkService(
            chunk_size=10,
            logger=self.logger,
            process_chunk=self._process_recipe_list,
            promote_silver=lambda r: self._promote_silver(r, MARKET_DOMAIN),
            silver_enabled=command.enable_silver,
        )
        run = chunk_service.process(recipes, run)
        run.tickers = original_tickers
        return run

    def _get_silver_exchange_codes(self) -> list[str]:
        """Query silver.fmp_market_exchanges for exchange codes."""
        try:
            bootstrap = DuckDbBootstrap(logger=self.logger)
            with bootstrap.read_connection() as conn:
                exists = conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'silver' AND table_name = 'fmp_market_exchanges'"
                ).fetchone()
                if not exists or exists[0] == 0:
                    return []
                rows = conn.execute("SELECT exchange FROM silver.fmp_market_exchanges").fetchall()
            bootstrap.close()
            return [row[0] for row in rows if row[0]]
        except Exception as exc:
            self.logger.warning(f"Could not query silver.fmp_market_exchanges: {exc}")
            return []

    def _get_filtered_universe(self, command: RunCommand, run_id: str) -> list[str]:
        """Return ticker symbols filtered by all active dimension filters in command.

        Delegates to UniverseService.get_filtered_tickers() which uses a three-tier
        fallback: fmp_market_screener → company_profile join → all stock_list.
        """
        tickers = self._universe_service.get_filtered_tickers(
            exchanges=command.exchanges,
            sectors=command.sectors,
            industries=command.industries,
            countries=command.countries,
            limit=command.ticker_limit,
        )
        active_filters = {
            k: v
            for k, v in {
                "exchanges": command.exchanges,
                "sectors": command.sectors,
                "industries": command.industries,
                "countries": command.countries,
            }.items()
            if v
        }
        self.logger.info(
            f"Universe filter {active_filters}: {len(tickers)} tickers",
            run_id=run_id,
        )
        return tickers

    def _run_market_screener(self, command: RunCommand, run: RunContext) -> RunContext:
        """Fetch company-screener data for each country in silver.fmp_market_countries.

        Each country produces one request with country=<code> as query param and
        the country code as the discriminator. Uses TICKER_PLACEHOLDER substitution
        (country codes are temporarily loaded into run.tickers).
        """
        recipes = [r for r in self._dataset_service.recipes if r.domain == MARKET_DOMAIN and r.dataset == MARKET_SCREENER_DATASET]
        if not recipes:
            self.logger.warning("No recipe found for market-screener", run_id=run.run_id)
            return run

        country_codes = self._get_silver_country_codes()
        if not country_codes:
            self.logger.info(
                "No country codes found in silver.fmp_market_countries — skipping market-screener",
                run_id=run.run_id,
            )
            return run

        self.logger.info(
            f"{self._processing_msg(command.enable_bronze, 'BRONZE')} " f"market-screener for {len(country_codes)} countries",
            run_id=run.run_id,
        )

        original_tickers = run.tickers
        run.tickers = country_codes

        chunk_service = OrchestrationTickerChunkService(
            chunk_size=10,
            logger=self.logger,
            process_chunk=self._process_recipe_list,
            promote_silver=lambda r: self._promote_silver(r, MARKET_DOMAIN),
            silver_enabled=command.enable_silver,
        )
        run = chunk_service.process(recipes, run)
        run.tickers = original_tickers
        return run

    def _get_silver_country_codes(self) -> list[str]:
        """Query silver.fmp_market_countries for country codes."""
        try:
            bootstrap = DuckDbBootstrap(logger=self.logger)
            with bootstrap.read_connection() as conn:
                exists = conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables " "WHERE table_schema = 'silver' AND table_name = 'fmp_market_countries'"
                ).fetchone()
                if not exists or exists[0] == 0:
                    return []
                rows = conn.execute("SELECT country FROM silver.fmp_market_countries").fetchall()
            bootstrap.close()
            return [row[0] for row in rows if row[0]]
        except Exception as exc:
            self.logger.warning(f"Could not query silver.fmp_market_countries: {exc}")
            return []

    def _get_universe_from_silver(self, dataset: str, symbol_col: str = "symbol") -> list[str] | None:
        """
        Retrieve universe (list of symbols) from a silver table.

        Args:
            dataset: Dataset name (e.g., "commodities-list")
            symbol_col: Column name containing symbols (default: "symbol")

        Returns:
            List of symbol strings, or None if no symbols found
        """
        try:
            table_name = f"silver.fmp_{dataset.replace('-', '_')}"
            bootstrap = DuckDbBootstrap(logger=self.logger)
            with bootstrap.read_connection() as conn:
                exists = conn.execute(
                    f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'silver' AND table_name = 'fmp_{dataset.replace('-', '_')}'"
                ).fetchone()
                if not exists or exists[0] == 0:
                    self.logger.warning(f"Table {table_name} does not exist")
                    return None
                result = conn.execute(f"SELECT DISTINCT {symbol_col} FROM {table_name} WHERE {symbol_col} IS NOT NULL").fetchall()
            bootstrap.close()

            symbols = [row[0] for row in result if row[0]]
            if symbols:
                self.logger.info(f"Retrieved {len(symbols)} symbols from {table_name}")
                return symbols
            else:
                self.logger.warning(f"No symbols found in {table_name}")
                return None
        except Exception as exc:
            self.logger.error(f"Failed to retrieve universe from {dataset}: {exc}")
            return None

    @staticmethod
    def _market_weekdays(from_date: date, to_date: date) -> list[date]:
        """Return Mon–Fri dates in [from_date, to_date] inclusive."""
        days: list[date] = []
        current = from_date
        while current <= to_date:
            if current.weekday() < 5:  # 0=Mon … 4=Fri
                days.append(current)
            current += timedelta(days=1)
        return days

    def _handle_commodities(self, command: RunCommand, run: RunContext) -> RunContext:
        """
        Handle commodities domain datasets.

        Execution sequence:
        1. commodities-list (baseline, global, yearly)
        2. commodities-price-eod (ticker-based, daily)
        """
        self.logger.log_section(run.run_id, "Processing commodities domain")

        # Step 1: Load commodities list (baseline discovery)
        recipes = [r for r in self._dataset_service.recipes if r.domain == COMMODITIES_DOMAIN and r.dataset == COMMODITIES_LIST_DATASET]
        if recipes:
            self.logger.log_section(run.run_id, "Phase 1: Loading commodities list")
            run = self._process_recipe_list(recipes, run)
            run = self._promote_silver(run, COMMODITIES_DOMAIN)

        # Step 2: Load commodities price-eod data (ticker-based)
        recipes = [r for r in self._dataset_service.recipes if r.domain == COMMODITIES_DOMAIN and r.dataset == COMMODITIES_PRICE_EOD_DATASET]
        if recipes:
            self.logger.log_section(run.run_id, "Phase 2: Loading commodities price-eod data")
            universe = self._get_universe_from_silver(COMMODITIES_LIST_DATASET, "symbol")
            if universe:
                original_tickers = run.tickers
                run.tickers = universe
                run = self._process_ticker_recipes(recipes, command, run, label="commodities-price-eod", domain=COMMODITIES_DOMAIN)
                run.tickers = original_tickers

        return run

    def _handle_fx(self, command: RunCommand, run: RunContext) -> RunContext:
        """
        Handle FX domain datasets.

        Execution sequence:
        1. fx-list (baseline, global, yearly)
        2. fx-price-eod (ticker-based, daily)
        """
        self.logger.log_section(run.run_id, "Processing fx domain")

        # Step 1: Load fx list (baseline discovery)
        recipes = [r for r in self._dataset_service.recipes if r.domain == FX_DOMAIN and r.dataset == FX_LIST_DATASET]
        if recipes:
            self.logger.log_section(run.run_id, "Phase 1: Loading fx list")
            run = self._process_recipe_list(recipes, run)
            run = self._promote_silver(run, FX_DOMAIN)

        # Step 2: Load fx price-eod data (ticker-based)
        recipes = [r for r in self._dataset_service.recipes if r.domain == FX_DOMAIN and r.dataset == FX_PRICE_EOD_DATASET]
        if recipes:
            self.logger.log_section(run.run_id, "Phase 2: Loading fx price-eod data")
            universe = self._get_universe_from_silver(FX_LIST_DATASET, "symbol")
            if universe:
                original_tickers = run.tickers
                run.tickers = universe
                run = self._process_ticker_recipes(recipes, command, run, label="fx-price-eod", domain=FX_DOMAIN)
                run.tickers = original_tickers

        return run

    def _handle_crypto(self, command: RunCommand, run: RunContext) -> RunContext:
        """
        Handle crypto domain datasets.

        Execution sequence:
        1. crypto-list (baseline, global, yearly)
        2. crypto-price-eod (ticker-based, daily)
        """
        self.logger.log_section(run.run_id, "Processing crypto domain")

        # Step 1: Load crypto list (baseline discovery)
        recipes = [r for r in self._dataset_service.recipes if r.domain == CRYPTO_DOMAIN and r.dataset == CRYPTO_LIST_DATASET]
        if recipes:
            self.logger.log_section(run.run_id, "Phase 1: Loading crypto list")
            run = self._process_recipe_list(recipes, run)
            run = self._promote_silver(run, CRYPTO_DOMAIN)

        # Step 2: Load crypto price-eod data (ticker-based)
        recipes = [r for r in self._dataset_service.recipes if r.domain == CRYPTO_DOMAIN and r.dataset == CRYPTO_PRICE_EOD_DATASET]
        if recipes:
            self.logger.log_section(run.run_id, "Phase 2: Loading crypto price-eod data")
            universe = self._get_universe_from_silver(CRYPTO_LIST_DATASET, "symbol")
            if universe:
                original_tickers = run.tickers
                run.tickers = universe
                run = self._process_ticker_recipes(recipes, command, run, label="crypto-price-eod", domain=CRYPTO_DOMAIN)
                run.tickers = original_tickers

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

    def _company_profile(self, command: RunCommand, run: RunContext) -> RunContext:
        """Run company-profile recipes for the current run tickers.

        Tickers that previously failed with "INVALID TICKER" are excluded.
        """
        self.logger.log_section(run.run_id, "Loading company-profile data")

        if not run.tickers:
            self.logger.info("No tickers to process for company-profile", run_id=run.run_id)
            return run

        # Filter out tickers that previously failed with "INVALID TICKER" error
        invalid_tickers = self.ops_service.get_tickers_with_bronze_error(
            dataset=COMPANY_INFO_DATASET,
            error_contains="INVALID TICKER",
        )
        if invalid_tickers:
            original_count = len(run.tickers)
            run.tickers = [t for t in run.tickers if t not in invalid_tickers]
            removed_count = original_count - len(run.tickers)
            if removed_count > 0:
                self.logger.info(f"Filtered {removed_count} tickers with previous INVALID TICKER errors", run_id=run.run_id)

        if not run.tickers:
            self.logger.info("No valid tickers remaining for company-profile", run_id=run.run_id)
            return run

        # Find company-profile recipes
        company_profile_recipes = [r for r in self._dataset_service.recipes if r.dataset == COMPANY_INFO_DATASET]

        if not company_profile_recipes:
            self.logger.warning("No company-profile recipe found", run_id=run.run_id)
            return run

        run = self._process_ticker_recipes(company_profile_recipes, command, run, "company-profile", domain=COMPANY_DOMAIN)
        self.logger.info("Company-profile data loaded", run_id=run.run_id)
        return run

    def _process_domain(self, domain: str, command: RunCommand, run: RunContext) -> RunContext:
        """Process all recipes for a single domain through Bronze → Silver.

        For the company domain, company-profile is processed first (via _company_profile),
        then remaining company datasets are processed.
        """
        all_recipes = self._dataset_service.recipes
        domain_recipes = [r for r in all_recipes if r.domain == domain]

        if domain == COMPANY_DOMAIN:
            # Process company-profile first, then remaining datasets
            run = self._company_profile(command, run)
            domain_recipes = [r for r in domain_recipes if r.dataset != COMPANY_INFO_DATASET]

        non_ticker_recipes = [r for r in domain_recipes if not r.is_ticker_based]
        ticker_recipes = [r for r in domain_recipes if r.is_ticker_based]

        self.logger.info(f"Processing domain {domain}: {len(non_ticker_recipes)} non-ticker, {len(ticker_recipes)} ticker recipes", run_id=run.run_id)

        # Process non-ticker recipes for this domain
        if non_ticker_recipes:
            if command.enable_bronze:
                run = self._process_recipe_list(non_ticker_recipes, run)
            run = self._promote_silver(run, domain)

        # Process ticker recipes for this domain
        if ticker_recipes:
            run = self._process_ticker_recipes(ticker_recipes, command, run, domain, domain=domain)

        self.logger.info(f"Completed domain processing for: {domain}", run_id=run.run_id)
        return run

    def _process_ticker_recipes(
        self, recipes: list[DatasetRecipe], command: RunCommand, run: RunContext, label: str, domain: str | None = None
    ) -> RunContext:
        """Process ticker-based recipes using chunking for bronze → silver."""
        if not recipes:
            return run

        self.logger.info(f"Processing {len(recipes)} ticker recipes for: {label}", run_id=run.run_id)

        chunk_service = OrchestrationTickerChunkService(
            chunk_size=command.ticker_recipe_chunk_size,
            logger=self.logger,
            process_chunk=self._process_recipe_list,
            promote_silver=lambda r: self._promote_silver(r, domain),
            silver_enabled=command.enable_silver,
        )
        run = chunk_service.process(recipes, run)

        self.logger.info(f"Completed ticker recipe processing for: {label}", run_id=run.run_id)
        return run

    def _process_recipe_list(self, recipes: list[DatasetRecipe], run: RunContext) -> RunContext:
        """Process a list of recipes through the bronze layer."""
        if not recipes:
            return run

        bronze_service = BronzeService(
            ops_service=self.ops_service,
            concurrent_requests=self._concurrent_requests,
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


if __name__ == "__main__":
    #     COMMODITIES_DOMAIN, COMPANY_DOMAIN, CRYPTO_DOMAIN, FX_DOMAIN, FUNDAMENTALS_DOMAIN, MARKET_DOMAIN, TECHNICALS_DOMAIN
    command = RunCommand(
        domain=FUNDAMENTALS_DOMAIN,
        concurrent_requests=10,  # Default: 10 workers for optimal throughput
        enable_bronze=True,
        enable_silver=True,
        ticker_limit=100,
        ticker_recipe_chunk_size=10,
        exchanges=["NASDAQ"],
    )
    result = SBFoundationAPI(today=date.today().isoformat()).run(command)
    print(
        f"run_id={result.run_id}  bronze_passed={result.bronze_files_passed}  bronze_failed={result.bronze_files_failed}  silver_rows={result.silver_dto_count}"
    )
