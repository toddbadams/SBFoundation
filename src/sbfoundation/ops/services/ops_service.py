from __future__ import annotations

from datetime import date, datetime, timedelta

import duckdb


from sbfoundation.ops.dtos.file_injestion import DatasetInjestion
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.run.dtos.bronze_result import BronzeResult
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.services.universe_service import UniverseService


class OpsService:
    def __init__(self, ops_repo: DuckDbOpsRepo | None = None, universe: UniverseService | None = None, logger: SBLogger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._ops_repo = ops_repo or DuckDbOpsRepo()
        self._owns_ops_repo = ops_repo is None
        self._universe = universe or UniverseService()

    def close(self) -> None:
        if self._owns_ops_repo:
            self._ops_repo.close()

    # --- Run run ---#
    def start_run(
        self,
        *,
        update_ticker_limit: int = 0,
        new_ticker_limit: int = 0,
        enable_update_tickers: bool = True,
        enable_new_tickers: bool = False,
    ) -> RunContext:
        """Start a new orchestration run with separate update and new ticker lists.

        Args:
            update_ticker_limit: Max tickers to process from already-ingested pool
            new_ticker_limit: Max tickers to process from new instrument dimensions
            enable_update_tickers: Whether to include update tickers
            enable_new_tickers: Whether to include new tickers

        Returns:
            RunContext with combined ticker list
        """
        today = self._universe.today()

        tickers: list[str] = []
        update_tickers: list[str] = []
        new_tickers: list[str] = []

        if enable_update_tickers and update_ticker_limit > 0:
            update_tickers = self._universe.update_tickers(limit=update_ticker_limit)
            tickers.extend(update_tickers)

        if enable_new_tickers and new_ticker_limit > 0:
            new_tickers = self._universe.new_tickers(limit=new_ticker_limit)
            tickers.extend(new_tickers)

        return RunContext(
            run_id=self._universe.run_id(),
            started_at=self._universe.now(),
            tickers=tickers,
            update_tickers=update_tickers,
            new_tickers=new_tickers,
            today=today.isoformat(),
        )

    def finish_run(self, run: RunContext) -> None:
        if run is None:
            return
        run.finished_at = self._universe.now()
        self.close()

    # --- BRONZE MANIFEST ---#
    def insert_bronze_manifest(self, result: BronzeResult, run: RunContext | None = None) -> None:
        ingestion = DatasetInjestion.from_bronze(result=result)
        try:
            self._ops_repo.upsert_file_ingestion(ingestion)
        except Exception as exc:
            run_id = run.run_id if run is not None else "unknown"
            self._logger.error("File ingestion persistence failed: %s", exc, run_id=run_id)
            raise

    def get_watermark_date(self, domain: str, source: str, dataset: str, discriminator: str, ticker: str) -> date | None:
        last_to_date = self._ops_repo.get_latest_bronze_to_date(
            domain=domain, source=source, dataset=dataset, discriminator=discriminator, ticker=ticker
        )
        if last_to_date is None:
            return None
        return last_to_date + timedelta(days=1)

    def get_last_ingestion_date(self, domain: str, source: str, dataset: str, discriminator: str, ticker: str) -> date | None:
        """Return the date of the most recent successful bronze ingestion."""
        last_time = self._ops_repo.get_latest_bronze_ingestion_time(
            domain=domain, source=source, dataset=dataset, discriminator=discriminator, ticker=ticker
        )
        if last_time is None:
            return None
        return last_time.date()

    def load_promotable_file_ingestions(self) -> list[DatasetInjestion]:
        return self._ops_repo.list_promotable_file_ingestions()

    def start_silver_ingestion(self, ingestion: DatasetInjestion) -> None:
        ingestion.silver_injest_start_time = self._universe.now()
        try:
            self._ops_repo.upsert_file_ingestion(ingestion)
        except Exception as exc:
            self._logger.warning("Silver start persistence failed: %s", exc, run_id=ingestion.run_id)

    def finish_silver_ingestion(
        self,
        ingestion: DatasetInjestion,
        *,
        rows_seen: int,
        rows_written: int,
        rows_failed: int,
        table_name: str | None,
        coverage_from: date | None,
        coverage_to: date | None,
        error: str | None,
    ) -> None:
        ingestion.silver_rows_created = rows_written
        ingestion.silver_rows_updated = 0
        ingestion.silver_rows_failed = rows_failed
        ingestion.silver_errors = error
        ingestion.silver_tablename = table_name
        ingestion.silver_from_date = coverage_from
        ingestion.silver_to_date = coverage_to
        ingestion.silver_injest_end_time = self._universe.now()
        ingestion.silver_can_promote = error is None
        if error is None:
            ingestion.bronze_can_promote = False
        try:
            self._ops_repo.upsert_file_ingestion(ingestion)
        except Exception as exc:
            self._logger.warning("Silver finish persistence failed: %s", exc, run_id=ingestion.run_id)

    def get_silver_watermark(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> date | None:
        return self._ops_repo.get_latest_silver_to_date(
            domain=domain,
            source=source,
            dataset=dataset,
            discriminator=discriminator,
            ticker=ticker,
        )

    def get_silver_watermark_for_dataset(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
    ) -> date | None:
        """Return the latest silver_to_date across all discriminators for a dataset.

        Use this instead of get_silver_watermark when each row of the date loop is
        stored under its own discriminator (e.g. market-sector-performance stores one
        discriminator per calendar day).  Filtering by discriminator=''" would never
        match those records, so this method intentionally omits that filter.
        """
        return self._ops_repo.get_latest_silver_to_date_for_dataset(
            domain=domain,
            source=source,
            dataset=dataset,
        )

    def load_input_watermarks(self, conn: duckdb.DuckDBPyConnection, *, datasets: set[str]) -> list[str]:
        return self._ops_repo.load_input_watermarks(conn, datasets=datasets)

    def get_tickers_with_bronze_error(self, *, dataset: str, error_contains: str) -> set[str]:
        """Get distinct tickers that have a bronze_error containing the specified string."""
        try:
            return self._ops_repo.get_tickers_with_bronze_error(
                dataset=dataset, error_contains=error_contains
            )
        except Exception as exc:
            self._logger.warning("Failed to get tickers with bronze error: %s", exc)
            return set()


__all__ = ["OpsService"]
