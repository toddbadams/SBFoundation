from dataclasses import dataclass, field
from datetime import date, timedelta
import copy
import os
import traceback

from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.maintenance import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.ops.services.run_stats_reporter import RunStatsReporter
from sbfoundation.recovery.bronze_recovery_service import BronzeRecoveryService
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.dtos.run_request import RunRequest
from sbfoundation.run.services.orchestration_ticker_chunk_service import OrchestrationTickerChunkService
from sbfoundation.bronze import BronzeService
from sbfoundation.silver import SilverService
from sbfoundation.services.universe_service import UniverseService
from sbfoundation.universe_definitions import US_ALL_CAP, UniverseDefinition
from sbfoundation.settings import *
from sbfoundation.settings import (
    ANNUAL_DOMAIN,
    COMMODITIES_DOMAIN,
    COMMODITIES_LIST_DATASET,
    COMMODITIES_PRICE_EOD_DATASET,
    COMPANY_DOMAIN,
    CRYPTO_DOMAIN,
    CRYPTO_LIST_DATASET,
    CRYPTO_PRICE_EOD_DATASET,
    EOD_DOMAIN,
    FX_DOMAIN,
    FX_LIST_DATASET,
    FX_PRICE_EOD_DATASET,
    FUNDAMENTALS_DOMAIN,
    MARKET_ETF_HOLDINGS_DATASET,
    MARKET_ETF_LIST_DATASET,
    MARKET_INDEX_LIST_DATASET,
    MARKET_STOCK_LIST_DATASET,
    QUARTER_DOMAIN,
    TECHNICALS_DOMAIN,
)

# Domains that support backward fill toward Jan 1, 1990.
# company is snapshot-based; market/commodities/fx/crypto use different cadences.
_BACKFILL_DOMAINS: frozenset[str] = frozenset({FUNDAMENTALS_DOMAIN, TECHNICALS_DOMAIN, ECONOMICS_DOMAIN})


@dataclass(slots=True)
class RunCommand:

    domain: str  # Allows running a specific data category

    concurrent_requests: int  # Max concurrent workers for Bronze requests. Set to 1 for sync/debug mode.
    enable_bronze: bool  # True to load source APIs into json files, else logs a dry run of requests
    enable_silver: bool  # True promotes loaded bronze json files into silver database
    ticker_limit: int = 0  # Max tickers to process
    ticker_recipe_chunk_size: int = 0  # number of recipes to run per chunk

    include_indexes: bool = False  # If True, also run technicals for index symbols from silver.fmp_index_list
    include_delisted: bool = False  # If True, run a second pass for delisted tickers from silver.fmp_company_delisted
    force_from_date: str | None = None  # ISO date (e.g. "1990-01-01"); bypasses watermarks for historical backfill
    backfill_to_1990: bool = False  # When True, fills historical data backward toward Jan 1, 1990
    universe_definition: UniverseDefinition | None = (
        None  # When set, overrides exchanges/countries with definition values and applies market-cap filter
    )

    def validate(self) -> None:
        """Validate this RunCommand. Raises ValueError on invalid input."""
        if self.domain not in DOMAINS:
            raise ValueError(f"Invalid domain '{self.domain}'. Must be one of: {DOMAINS}")
        if self.backfill_to_1990 and self.domain not in _BACKFILL_DOMAINS:
            raise ValueError(f"backfill_to_1990 is only supported for domains: {sorted(_BACKFILL_DOMAINS)}")


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
        self._universe_service = universe_service or UniverseService()
        self._recovery_service = recovery_service or BronzeRecoveryService()
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
        self._backfill_to_1990: bool = command.backfill_to_1990
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
        elif domain == EOD_DOMAIN:
            run = self._handle_eod(command, run)
        elif domain == QUARTER_DOMAIN:
            run = self._handle_quarter(command, run)
        elif domain == ANNUAL_DOMAIN:
            run = self._handle_annual(command, run)

        self.ops_service.refresh_coverage_index(
            run_id=run.run_id,
            universe_from_date=date.fromisoformat(self._universe_service.from_date),
            today=self._universe_service.today(),
        )

        self._close_run(run)

        try:
            reporter = RunStatsReporter()
            report_path = reporter.write_report(
                run.run_id,
                universe_tickers=run.tickers or None,
            )
            reporter.close()
            self.logger.info(f"Run report written: {report_path}", run_id=run.run_id)
        except Exception as exc:
            self.logger.warning(f"Run stats reporter failed (non-fatal): {exc}", run_id=run.run_id)

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

        # Phase 1c: market-screener (per universe × exchange — authoritative symbol→dimension mapping)
        run = self._run_market_screener(command, run)

        # Phase 1d: materialize universe snapshots from screener results
        self._materialize_universe_snapshots(run)

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
        run = self._process_domain(FUNDAMENTALS_DOMAIN, command, run)

        if command.include_delisted:
            run = self._run_for_delisted_tickers(command, run, FUNDAMENTALS_DOMAIN)

        return run

    def _handle_technicals(self, command: RunCommand, run: RunContext) -> RunContext:
        """
        Handle technicals domain datasets.

        Tickers are filtered from silver via exchange/sector/industry/country dimension filters.
        All filters are optional; all empty returns the full universe.

        If command.include_indexes is True, a second pass runs all technicals recipes
        for index symbols sourced from silver.fmp_index_list.
        """
        self.logger.log_section(run.run_id, "Processing technicals domain")
        tickers = self._get_filtered_universe(command, run.run_id)
        if not tickers:
            self.logger.warning("No tickers found for technicals domain — skipping", run_id=run.run_id)
            return run
        run.tickers = tickers
        self.logger.info(f"Technicals domain: {len(tickers)} tickers", run_id=run.run_id)
        run = self._process_domain(TECHNICALS_DOMAIN, command, run)

        if command.include_indexes:
            run = self._run_technicals_for_indexes(command, run)

        if command.include_delisted:
            run = self._run_for_delisted_tickers(command, run, TECHNICALS_DOMAIN)

        # Derived metrics (ADTV, computed market cap, coverage score) require price data.
        self._compute_derived_metrics(run)

        return run

    def _run_technicals_for_indexes(self, command: RunCommand, run: RunContext) -> RunContext:
        """Run all technicals recipes for index symbols from silver.fmp_index_list."""
        self.logger.log_section(run.run_id, "Processing technicals for indexes")

        index_symbols = self._get_silver_index_symbols()
        if not index_symbols:
            self.logger.info("No index symbols found in silver.fmp_index_list — skipping", run_id=run.run_id)
            return run

        self.logger.info(f"Technicals indexes: {len(index_symbols)} symbols", run_id=run.run_id)

        original_tickers = run.tickers
        run.tickers = index_symbols
        ticker_recipes = [r for r in self._dataset_service.recipes if r.domain == TECHNICALS_DOMAIN and r.is_ticker_based]
        if ticker_recipes:
            run = self._process_ticker_recipes(ticker_recipes, command, run, label="technicals-indexes", domain=TECHNICALS_DOMAIN)
        run.tickers = original_tickers
        return run

    def _run_for_delisted_tickers(self, command: RunCommand, run: RunContext, domain: str) -> RunContext:
        """Run domain recipes for delisted tickers sourced from silver.fmp_company_delisted.

        Provides survivorship-bias-free backfill: tickers that were listed during the
        backtest period but have since delisted are included in price and fundamental
        history ingestion. Combine with backfill_to_1990=True for full history.
        """
        self.logger.log_section(run.run_id, f"Processing {domain} for delisted tickers")

        delisted_tickers = self._universe_service.get_delisted_tickers()
        if not delisted_tickers:
            self.logger.info(
                "No delisted tickers found in silver.fmp_company_delisted — skipping",
                run_id=run.run_id,
            )
            return run

        self.logger.info(f"{domain} delisted: {len(delisted_tickers)} tickers", run_id=run.run_id)

        original_tickers = run.tickers
        run.tickers = delisted_tickers
        ticker_recipes = [r for r in self._dataset_service.recipes if r.domain == domain and r.is_ticker_based]
        if ticker_recipes:
            run = self._process_ticker_recipes(ticker_recipes, command, run, label=f"{domain}-delisted", domain=domain)
        run.tickers = original_tickers
        return run

    def _get_silver_index_symbols(self) -> list[str]:
        """Query silver.fmp_index_list for index symbols."""
        try:
            bootstrap = DuckDbBootstrap(logger=self.logger)
            with bootstrap.read_connection() as conn:
                exists = conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'silver' AND table_name = 'fmp_index_list'"
                ).fetchone()
                if not exists or exists[0] == 0:
                    return []
                rows = conn.execute("SELECT DISTINCT symbol FROM silver.fmp_index_list WHERE symbol IS NOT NULL").fetchall()
            bootstrap.close()
            return [row[0] for row in rows if row[0]]
        except Exception as exc:
            self.logger.warning(f"Could not query silver.fmp_index_list: {exc}")
            return []

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

    def _get_silver_sector_names(self) -> list[str]:
        """Query silver.fmp_market_sectors for sector names."""
        try:
            bootstrap = DuckDbBootstrap(logger=self.logger)
            with bootstrap.read_connection() as conn:
                exists = conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables " "WHERE table_schema = 'silver' AND table_name = 'fmp_market_sectors'"
                ).fetchone()
                if not exists or exists[0] == 0:
                    return []
                rows = conn.execute("SELECT sector FROM silver.fmp_market_sectors").fetchall()
            bootstrap.close()
            return [row[0] for row in rows if row[0]]
        except Exception as exc:
            self.logger.warning(f"Could not query silver.fmp_market_sectors: {exc}")
            return []

    def _get_filtered_universe(self, command: RunCommand, run_id: str) -> list[str]:
        """Return ticker symbols for the command's universe definition.

        Primary path: queries silver.universe_member for the latest snapshot of
        the named universe. This is populated by _materialize_universe_snapshots()
        after each market-screener run.

        Fallback path: when no snapshot exists (cold start / bootstrap), delegates
        to UniverseService.get_filtered_tickers() which uses a three-tier query
        against silver screener and profile tables.
        """
        ud = command.universe_definition

        # Primary: versioned snapshot from silver.universe_member
        if ud is not None:
            tickers = self._universe_api.tickers(ud.name)
            if tickers:
                if command.ticker_limit > 0:
                    tickers = tickers[: command.ticker_limit]
                self.logger.info(
                    f"Universe: {ud.name} | snapshot | tickers={len(tickers)}",
                    run_id=run_id,
                )
                return tickers

        # Fallback: three-tier repo query (bootstrap / no snapshot yet)
        if ud is not None:
            exchanges = ud.exchanges
            countries = [ud.country] if ud.country else []
            min_market_cap = ud.min_market_cap_usd
            max_market_cap = ud.max_market_cap_usd
        else:
            exchanges = []
            countries = []
            min_market_cap = None
            max_market_cap = None

        tickers = self._universe_service.get_filtered_tickers(
            exchanges=exchanges,
            sectors=[],
            industries=[],
            countries=countries,
            limit=command.ticker_limit,
            min_market_cap_usd=min_market_cap,
            max_market_cap_usd=max_market_cap,
        )

        min_cap_str = f"${min_market_cap:,.0f}" if min_market_cap is not None else "none"
        max_cap_str = f"${max_market_cap:,.0f}" if max_market_cap is not None else "unlimited"
        self.logger.info(
            f"Universe: {ud.name if ud else '(none)'} | fallback | "
            f"country={', '.join(countries) if countries else 'all'} | "
            f"exchanges={', '.join(exchanges) if exchanges else 'all'} | "
            f"market_cap={min_cap_str}-{max_cap_str} | "
            f"tickers={len(tickers)}",
            run_id=run_id,
        )
        return tickers

    def _run_market_screener(self, command: RunCommand, run: RunContext) -> RunContext:
        """Fetch company-screener data for each (universe × exchange) pair.

        Replaces the prior global exchange×sector Cartesian product approach.
        Each UniverseDefinition in UNIVERSE_REGISTRY drives per-exchange calls
        using its eligibility filter params (market cap, country, ETF flags, etc.)
        as FMP query parameters. Sector is NOT used as a per-request filter —
        sector-based selection belongs in the downstream Gold project.

        The FMP company-screener caps responses at 1000 rows per request;
        iterating per-exchange keeps each response within that limit.

        discriminator = "{universe_name}-{exchange}"
        """
        recipes = [r for r in self._dataset_service.recipes if r.domain == MARKET_DOMAIN and r.dataset == MARKET_SCREENER_DATASET]
        if not recipes:
            self.logger.warning("No recipe found for market-screener", run_id=run.run_id)
            return run

        all_requests: list[RunRequest] = []
        for universe_def in self._universe_registry.values():
            base_params = universe_def.to_screener_params()
            for exchange in universe_def.exchanges:
                discriminator = f"{universe_def.name}-{exchange}"
                query_vars = {**base_params, "exchange": exchange}
                for recipe in recipes:
                    patched = copy.copy(recipe)
                    patched.query_vars = query_vars
                    patched.discriminator = discriminator
                    all_requests.append(
                        RunRequest.from_recipe(
                            recipe=patched,
                            run_id=run.run_id,
                            from_date=self._universe_service.from_date,
                            today=run.today,
                            api_key=self._fmp_api_key,
                        )
                    )

        universe_count = len(self._universe_registry)
        self.logger.info(
            f"{self._processing_msg(command.enable_bronze, 'BRONZE')} market-screener: "
            f"{universe_count} universes × per-exchange = {len(all_requests)} requests",
            run_id=run.run_id,
        )

        if command.enable_bronze:
            bronze_service = BronzeService(
                ops_service=self.ops_service,
                concurrent_requests=self._concurrent_requests,
            )
            run = bronze_service.execute_requests(all_requests, run)

        run = self._promote_silver(run, MARKET_DOMAIN)
        return run

    def _materialize_universe_snapshots(self, run: RunContext) -> None:
        """Materialize universe_member and universe_snapshot for all registered universes.

        Called after screener ingestion completes. Reads silver.fmp_market_screener
        rows (discriminator prefixed by universe name) and writes versioned snapshots.
        """
        self.logger.log_section(run.run_id, "Materializing universe snapshots")
        as_of_date = date.fromisoformat(run.today) if isinstance(run.today, str) else run.today
        results = self._universe_api.materialize_snapshots(
            as_of_date=as_of_date,
            run_id=run.run_id,
        )
        for name, count in results.items():
            self.logger.info(
                f"Universe snapshot: {name} → {count} members",
                run_id=run.run_id,
            )

    def _compute_derived_metrics(self, run: RunContext) -> None:
        """Compute and persist derived eligibility metrics for all universe members.

        Called after technicals ingestion so that price data is available for
        ADTV and data-coverage calculations. Gracefully skips if price tables
        are not yet populated.
        """
        self.logger.log_section(run.run_id, "Computing universe derived metrics")
        as_of_date = date.fromisoformat(run.today) if isinstance(run.today, str) else run.today

        # Collect the union of all universe members for today's snapshots.
        all_symbols: set[str] = set()
        for name in self._universe_registry:
            all_symbols.update(self._universe_api.tickers(name, as_of_date))

        if not all_symbols:
            self.logger.warning("No universe members found — skipping derived metrics", run_id=run.run_id)
            return

        symbols = sorted(all_symbols)
        from sbuniverse.services.derived_metrics_service import DerivedMetricsService

        svc = DerivedMetricsService(logger=self.logger)
        try:
            count = svc.compute_and_persist(symbols=symbols, as_of_date=as_of_date, run_id=run.run_id)
            self.logger.info(f"Derived metrics: {count} rows written for {len(symbols)} symbols", run_id=run.run_id)
        finally:
            svc.close()

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
            force_from_date=self._force_from_date,
            backfill_to_1990=self._backfill_to_1990,
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
        domain=MARKET_DOMAIN,
        concurrent_requests=10,  # Default: 10 workers for optimal throughput
        enable_bronze=True,
        enable_silver=True,
        ticker_limit=5300,
        ticker_recipe_chunk_size=1000,
        include_indexes=False,
        universe_definition=US_ALL_CAP,
        backfill_to_1990=False,
    )
    result = SBFoundationAPI(today=date.today().isoformat()).run(command)
    print(
        f"run_id={result.run_id}  bronze_passed={result.bronze_files_passed}  bronze_failed={result.bronze_files_failed}  silver_rows={result.silver_dto_count}"
    )

"""
# Fundamentals — fill income statements, balance sheets, etc. back to 1990
  result = api.run(RunCommand(
      domain=FUNDAMENTALS_DOMAIN,
      concurrent_requests=5,
      enable_bronze=True,
      enable_silver=True,
      ticker_limit=10,                  # start small to verify
      universe_definition=US_LARGE_CAP,
      backfill_to_1990=True,
  ))

  # Technicals — fill price history, indicators, etc. back to 1990
  result = api.run(RunCommand(
      domain=TECHNICALS_DOMAIN,
      concurrent_requests=5,
      enable_bronze=True,
      enable_silver=True,
      ticker_limit=10,
      universe_definition=US_LARGE_CAP,
      backfill_to_1990=True,
  ))

  # Economics — fill macro indicators (GDP, CPI, etc.) back to 1990
  result = api.run(RunCommand(
      domain=ECONOMICS_DOMAIN,
      concurrent_requests=5,
      enable_bronze=True,
      enable_silver=True,
      backfill_to_1990=True,
  ))

  Key points:

  - Run a normal (non-backfill) pass first if you haven't yet — backfill skips any ticker with no existing bronze data
  - Each run checkpoints progress in ops.dataset_watermarks; you can re-run safely and it picks up where it left off
  - Tickers already fully backfilled (floor = 1990-01-01) are skipped immediately on subsequent runs
  - Check progress with:

  SELECT domain, dataset, ticker, backfill_floor_date
  FROM ops.dataset_watermarks
  ORDER BY backfill_floor_date DESC NULLS LAST
  LIMIT 50;

  - backfill_floor_date = NULL → not started
  - backfill_floor_date = '1990-01-01' → complete (either reached 1990 or API returned empty before then)
  - Any other date → in progress, next run resumes from that date
"""
