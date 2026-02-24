import os
import typing
from datetime import date, timedelta
import requests

from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.run.dtos.run_request import RunRequest
from sbfoundation.run.dtos.bronze_result import BronzeResult
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.services.universe_service import UniverseService
from sbfoundation.folders import Folders
from sbfoundation.settings import *
from sbfoundation.run.services.run_request_executor import RunRequestExecutor
from sbfoundation.infra.result_file_adaptor import ResultFileAdapter
from sbfoundation.infra.logger import LoggerFactory
from sbfoundation.ops.services.ops_service import OpsService


class BronzeService:
    """Coordinate Bronze ingestion for data runs."""

    def __init__(
        self,
        logger_factory: typing.Optional[LoggerFactory] = None,
        fmp_api_key: str = None,
        result_file_adapter: typing.Optional[ResultFileAdapter] = None,
        universe: typing.Optional[UniverseService] = None,
        request_executor: typing.Optional[RunRequestExecutor] = None,
        ops_service: typing.Optional[OpsService] = None,
        concurrent_requests: int = 1,
        force_from_date: str | None = None,
        backfill_to_1990: bool = False,
    ):
        """Initialize dependencies, run metadata, and storage repositories."""
        self.fmp_api_key = fmp_api_key or os.getenv("FMP_API_KEY")
        self.logger = (logger_factory or LoggerFactory()).create_logger(self.__class__.__name__)
        self.result_file_adapter = result_file_adapter or ResultFileAdapter()
        self.universe = universe or UniverseService()
        self.ops_service = ops_service or OpsService()
        self._owns_ops_service = ops_service is None
        self.recipes: list[DatasetRecipe] = []
        self.request_executor = request_executor or RunRequestExecutor(self.logger)
        self.run: RunContext = None
        self.concurrent_requests = max(1, concurrent_requests)  # Ensure >= 1
        self._force_from_date: str | None = force_from_date
        self._backfill_to_1990: bool = backfill_to_1990

    @property
    def summary(self) -> RunContext:
        return self.run

    @summary.setter
    def summary(self, value: RunContext) -> None:
        self.run = value

    def _result_bronze_error(self, result: BronzeResult, e: str) -> None:
        """Persist a Bronze failure and update summary counters/items."""
        result.error = e
        filename = self._persist_bronze(result)
        self.run.result_bronze_error(result, e, filename=filename)
        self.logger.warning(f"{result.msg} | {result.error}", run_id=self.run.run_id)

    def _process_run_request(self, request: RunRequest) -> None:
        """Execute a single request through Bronze write."""
        # Capture the Bronze payload and related metadata to support the
        # reproducibility and auditability properties of the medallion
        # architecture.
        result = BronzeResult(now=self.universe.now(), request=request)

        # Run request acceptance criteria to reject malformed upstream
        # definitions before attempting any network IO.
        domain, source, dataset, discriminator, ticker = request.ingest_identity()

        today = self.universe.today()

        if self._force_from_date:
            # Backfill mode: bypass duplicate-ingestion check and watermarks.
            # The caller has explicitly requested historical data from a fixed start date.
            request.from_date = self._force_from_date
        else:
            # Normal mode: skip if already ingested today, then advance from watermark.
            last_ingestion_date = self.ops_service.get_last_ingestion_date(
                domain=domain, source=source, dataset=dataset, discriminator=discriminator, ticker=ticker
            )
            if last_ingestion_date and last_ingestion_date >= today:
                self.logger.debug(
                    "Skipping duplicate ingestion | dataset=%s | ticker=%s | last_ingestion=%s",
                    dataset,
                    ticker,
                    last_ingestion_date,
                    run_id=self.run.run_id,
                )
                return

            last_to_date = self.ops_service.get_watermark_date(
                domain=domain, source=source, dataset=dataset, discriminator=discriminator, ticker=ticker
            )
            if last_to_date:
                request.from_date = last_to_date.isoformat()

        if not request.canRun():
            result.error = result.request.error
            # Skip file persistence and ops tracking for "too soon" requests
            if result.error == "REQUEST IS TOO SOON":
                self.logger.warning(f"{result.msg} | {result.error}", run_id=self.run.run_id)
                return
            self._result_bronze_error(result, result.error)
            return

        # Call source endpoint and create a BronzeResult
        try:
            response = self.request_executor.execute(
                lambda: requests.get(request.url, params=request.query_vars, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)),
                f"GET {request.url}",
            )
            result.add_response(response)

        except requests.Timeout:
            self._result_bronze_error(result, f"Connection to {request.url} timed out.")
            return
        except requests.ConnectionError:
            self._result_bronze_error(result, f"Connection to {request.url} failed:  DNS failure, or other connection related issue.")
            return
        except requests.TooManyRedirects:
            self._result_bronze_error(result, f"Request to {request.url} exceeds the maximum number of predefined redirections.")
            return
        except requests.RequestException as e:
            self._result_bronze_error(result, f"Request to {request.url} failed: {e}")
            return
        except Exception as e:
            self._result_bronze_error(result, f"A requests exception, Error: {e}")
            return

        # Bronze acceptance criteria enforce persistence of well-structured raw
        # payloads while still allowing non-200 responses to be archived.
        if not result.is_valid_bronze:
            self._result_bronze_error(result, f"Failed bronze acceptance: {result.error}")
            return

        # Write the bronze result
        filename = self._persist_bronze(result)

        # Update the summary report
        self.run.result_bronze_pass(result, filename=filename)

    def register_recipes(self, run: RunContext, recipes: list[DatasetRecipe]) -> "BronzeService":
        """Register recipes to be processed in the current run."""
        self.recipes.extend(recipes)
        self.logger.info(f"Recipes registered: count={len(recipes)}", run_id=run.run_id)
        return self

    def _persist_bronze(self, result: BronzeResult) -> str:
        """Write the Bronze payload and still record a manifest row so audits remain intact."""
        try:
            self.result_file_adapter.write(result)
        except Exception as exc:
            self.logger.error(f"Bronze persistence failed: {result.msg} | error={exc}", run_id=self.run.run_id)
            raise

        try:
            # Manifest insert must happen even when the blob was written so Ops can audit every run.
            self.ops_service.insert_bronze_manifest(result)
        except Exception as exc:
            self.logger.error("Bronze manifest insert failed: %s", exc, run_id=self.run.run_id)
            raise

        return str(Folders.duckdb_absolute_path)

    def _process_requests_concurrent(self, requests: list[RunRequest]) -> None:
        """Process requests concurrently using ThreadPoolExecutor.

        Args:
            requests: List of RunRequest objects to process in parallel

        Note:
            - Uses self.concurrent_requests for worker pool size
            - Shares RunRequestExecutor for throttling across all workers
            - Thread-safe RunContext updates via locks
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=self.concurrent_requests) as executor:
            # Submit all requests to thread pool
            futures = {executor.submit(self._process_run_request, req): req for req in requests}

            # Process results as they complete
            for future in as_completed(futures):
                request = futures[future]
                try:
                    future.result()  # Raise any exceptions from worker
                except Exception as exc:
                    # Already logged in _process_run_request, just log at executor level
                    self.logger.error(f"Worker exception for {request.msg}: {exc}", run_id=self.run.run_id)

    def execute_requests(self, requests: list[RunRequest], run: RunContext) -> RunContext:
        """Dispatch a pre-built flat list of RunRequests concurrently or sequentially.

        Used for non-ticker request batches (e.g., market date-loop snapshots across
        all dates × datasets) where concurrency must be applied at a higher level than
        individual recipes.
        """
        self.run = run
        self.request_executor.set_summary(self.run)

        if self.concurrent_requests > 1 and len(requests) > 1:
            self.logger.info(
                f"Dispatching {len(requests)} requests concurrently (workers={self.concurrent_requests})",
                run_id=run.run_id,
            )
            self._process_requests_concurrent(requests)
        else:
            for req in requests:
                self._process_run_request(req)

        if self._owns_ops_service:
            self.ops_service.close()

        return self.run

    _BACKFILL_START = date(1990, 1, 1)

    def _run_backward_fill_loop(self, request: RunRequest) -> None:
        """Work backward from the earliest loaded date toward Jan 1, 1990.

        Chunked API requests (one per loop iteration) page backward until either:
        - the API returns an empty response (no data before that point), or
        - we reach 1990-01-01.

        Progress is checkpointed in ops.dataset_watermarks.backfill_floor_date so
        interrupted runs resume from the last committed floor.
        """
        domain, source, dataset, discriminator, ticker = request.ingest_identity()

        # Skip if already fully backfilled
        floor = self.ops_service.get_backfill_floor_date(domain, source, dataset, discriminator, ticker)
        if floor is not None and floor <= self._BACKFILL_START:
            self.logger.debug(
                f"Backward fill complete for ticker={ticker} dataset={dataset}",
                run_id=self.run.run_id,
            )
            return

        # Need existing data to know where to start going backward
        earliest = self.ops_service.get_earliest_bronze_from_date(domain, source, dataset, discriminator, ticker)
        if earliest is None:
            self.logger.debug(
                f"No loaded data for ticker={ticker} dataset={dataset} — skipping backward fill",
                run_id=self.run.run_id,
            )
            return

        to_date = (floor - timedelta(days=1)) if floor is not None else (earliest - timedelta(days=1))

        while to_date > self._BACKFILL_START:
            bf_request = RunRequest.from_recipe(
                recipe=request.recipe,
                run_id=request.run_id,
                from_date=self._BACKFILL_START.isoformat(),
                today=request.injestion_date,
                api_key=self.fmp_api_key,
                ticker=request.ticker,
                to_date=to_date.isoformat(),
            )

            try:
                response = self.request_executor.execute(
                    lambda: requests.get(bf_request.url, params=bf_request.query_vars, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)),
                    f"GET {bf_request.url}",
                )
                result = BronzeResult(now=self.universe.now(), request=bf_request)
                result.add_response(response)
            except requests.Timeout:
                self.logger.warning(f"Backward fill timed out for ticker={ticker} dataset={dataset}", run_id=self.run.run_id)
                break
            except requests.ConnectionError:
                self.logger.warning(f"Backward fill connection error for ticker={ticker} dataset={dataset}", run_id=self.run.run_id)
                break
            except requests.RequestException as exc:
                self.logger.warning(f"Backward fill request failed for ticker={ticker} dataset={dataset}: {exc}", run_id=self.run.run_id)
                break
            except Exception as exc:
                self.logger.warning(f"Backward fill unexpected error for ticker={ticker} dataset={dataset}: {exc}", run_id=self.run.run_id)
                break

            if not result.content:
                # No data before to_date — mark sentinel and stop
                self.ops_service.set_backfill_floor_date(domain, source, dataset, discriminator, ticker, floor_date=self._BACKFILL_START)
                self.logger.info(
                    f"No data before {to_date} for ticker={ticker} dataset={dataset} — backfill complete",
                    run_id=self.run.run_id,
                )
                break

            # Persist bronze
            filename = self._persist_bronze(result)
            self.run.result_bronze_pass(result, filename=filename)

            # Advance floor backward using the earliest date in the response
            new_floor_str = result.first_date
            if new_floor_str is None:
                break
            try:
                new_floor = date.fromisoformat(new_floor_str)
            except ValueError:
                self.logger.warning(f"Backward fill: unparseable first_date '{new_floor_str}' for ticker={ticker}", run_id=self.run.run_id)
                break

            self.ops_service.set_backfill_floor_date(domain, source, dataset, discriminator, ticker, floor_date=new_floor)
            to_date = new_floor - timedelta(days=1)

            if to_date <= self._BACKFILL_START:
                self.ops_service.set_backfill_floor_date(domain, source, dataset, discriminator, ticker, floor_date=self._BACKFILL_START)
                self.logger.info(
                    f"Reached 1990 for ticker={ticker} dataset={dataset} — backfill complete",
                    run_id=self.run.run_id,
                )
                break

    def _process_dataset_recipe(self, recipe: DatasetRecipe):
        """Process a recipe for each ticker, or once if not ticker-based."""
        if recipe.is_ticker_based:
            # Build all requests upfront
            reqs = [
                RunRequest.from_recipe(
                    recipe=recipe,
                    run_id=self.run.run_id,
                    from_date=self.universe.from_date,
                    today=self.run.today,
                    api_key=self.fmp_api_key,
                    ticker=ticker,
                )
                for ticker in self.run.tickers
            ]

            if self._backfill_to_1990:
                # Backward fill runs sequentially per ticker (order matters)
                for request in reqs:
                    self._run_backward_fill_loop(request)
            elif self.concurrent_requests > 1:
                # Dispatch based on concurrency mode
                self.logger.info(
                    f"Processing {len(reqs)} requests concurrently (workers={self.concurrent_requests})",
                    run_id=self.run.run_id,
                )
                self._process_requests_concurrent(reqs)
            else:
                # Sequential mode (current behavior)
                for request in reqs:
                    self._process_run_request(request)
        else:
            # Non-ticker recipes always sequential (single request)
            req = RunRequest.from_recipe(
                recipe=recipe,
                run_id=self.run.run_id,
                from_date=self.universe.from_date,
                today=self.run.today,
                api_key=self.fmp_api_key,
            )
            if self._backfill_to_1990:
                self._run_backward_fill_loop(req)
            else:
                self._process_run_request(req)

    def process(self, run: RunContext) -> RunContext:
        """Run registered recipes, updating and returning the summary."""
        self.run = run
        self.request_executor.set_summary(self.run)

        for recipe in self.recipes:
            try:
                self._process_dataset_recipe(recipe)
            except Exception as e:
                # we should never end up here
                # todo: add this error to run summary
                self.logger.error(f"run recipe failure: {e}", run_id=self.run.run_id)

        if self._owns_ops_service:
            self.ops_service.close()

        return self.run
