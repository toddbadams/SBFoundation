import os
import typing
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

        # Check if we already successfully ingested today to prevent duplicate downloads
        last_ingestion_date = self.ops_service.get_last_ingestion_date(
            domain=domain, source=source, dataset=dataset, discriminator=discriminator, ticker=ticker
        )
        today = self.universe.today()
        if last_ingestion_date and last_ingestion_date >= today:
            self.logger.debug(
                "Skipping duplicate ingestion | dataset=%s | ticker=%s | last_ingestion=%s",
                dataset,
                ticker,
                last_ingestion_date,
                run_id=self.run.run_id,
            )
            return

        last_to_date = self.ops_service.get_watermark_date(domain=domain, source=source, dataset=dataset, discriminator=discriminator, ticker=ticker)
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

    def _process_dataset_recipe(self, recipe: DatasetRecipe):
        """Process a recipe for each ticker, or once if not ticker-based."""
        if recipe.is_ticker_based:
            # Build all requests upfront
            requests = [
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

            # Dispatch based on concurrency mode
            if self.concurrent_requests > 1:
                self.logger.info(
                    f"Processing {len(requests)} requests concurrently (workers={self.concurrent_requests})",
                    run_id=self.run.run_id,
                )
                self._process_requests_concurrent(requests)
            else:
                # Sequential mode (current behavior)
                for request in requests:
                    self._process_run_request(request)
        else:
            # Non-ticker recipes always sequential (single request)
            self._process_run_request(
                RunRequest.from_recipe(
                    recipe=recipe,
                    run_id=self.run.run_id,
                    from_date=self.universe.from_date,
                    today=self.run.today,
                    api_key=self.fmp_api_key,
                )
            )

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
