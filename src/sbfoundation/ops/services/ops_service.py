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
        enable_update_tickers: bool = True,
    ) -> RunContext:
        """Start a new orchestration run.

        Args:
            update_ticker_limit: Max tickers to process from already-ingested pool
            enable_update_tickers: Whether to include update tickers

        Returns:
            RunContext with ticker list
        """
        today = self._universe.today()

        update_tickers: list[str] = []

        if enable_update_tickers and update_ticker_limit > 0:
            update_tickers = self._universe.update_tickers(limit=update_ticker_limit)

        return RunContext(
            run_id=self._universe.run_id(),
            started_at=self._universe.now(),
            tickers=list(update_tickers),
            update_tickers=update_tickers,
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

    def get_bulk_ingestion_watermarks(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
    ) -> dict[str, tuple[date | None, date | None]]:
        """Return {ticker: (last_ingestion_date, watermark_date)} for all tickers in one query.

        Replaces N per-ticker calls to get_last_ingestion_date + get_watermark_date with a
        single GROUP BY scan.  watermark_date already has the +1 day offset applied.
        """
        raw = self._ops_repo.get_bulk_ingestion_watermarks(
            domain=domain, source=source, dataset=dataset, discriminator=discriminator
        )
        result: dict[str, tuple[date | None, date | None]] = {}
        for ticker, (last_time, last_to_date) in raw.items():
            last_ingestion_date = last_time.date() if last_time is not None else None
            watermark_date = (last_to_date + timedelta(days=1)) if last_to_date is not None else None
            result[ticker] = (last_ingestion_date, watermark_date)
        return result

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

    def refresh_coverage_index(self, *, run_id: str, universe_from_date: date, today: date) -> None:
        """Recompute ops.coverage_index from ops.file_ingestions. Non-fatal on failure.

        DEPRECATED: Superseded by DataIntegrityService / ops.run_integrity (Phase J).
        Kept for backward compatibility with existing callers and coverage_dashboard.
        """
        from sbfoundation.coverage.coverage_index_service import CoverageIndexService

        try:
            svc = CoverageIndexService(ops_repo=self._ops_repo, logger=self._logger)
            svc.refresh(run_id=run_id, universe_from_date=universe_from_date, today=today)
        except Exception as exc:
            self._logger.warning("Coverage index refresh failed (non-fatal): %s", exc, run_id=run_id)

    def record_integrity_event(
        self,
        *,
        run_id: str,
        layer: str,
        domain: str | None = None,
        source: str | None = None,
        dataset: str | None = None,
        discriminator: str = "",
        ticker: str = "",
        file_id: str | None = None,
        status: str,
        rows_in: int | None = None,
        rows_out: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """Record a data integrity event for Bronze, Silver, or Gold layer."""
        try:
            from sbfoundation.ops.services.data_integrity_service import DataIntegrityService
            svc = DataIntegrityService(logger=self._logger)
            svc.record(
                run_id=run_id, layer=layer, domain=domain, source=source,
                dataset=dataset, discriminator=discriminator, ticker=ticker,
                file_id=file_id, status=status,
                rows_in=rows_in, rows_out=rows_out, error_message=error_message,
            )
        except Exception as exc:
            self._logger.warning(f"record_integrity_event failed (non-fatal): {exc}", run_id=run_id)

    def get_tickers_with_bronze_error(self, *, dataset: str, error_contains: str) -> set[str]:
        """Get distinct tickers that have a bronze_error containing the specified string."""
        try:
            return self._ops_repo.get_tickers_with_bronze_error(
                dataset=dataset, error_contains=error_contains
            )
        except Exception as exc:
            self._logger.warning("Failed to get tickers with bronze error: %s", exc)
            return set()

    def get_earliest_bronze_from_date(
        self, domain: str, source: str, dataset: str, discriminator: str, ticker: str
    ) -> date | None:
        return self._ops_repo.get_earliest_bronze_from_date(
            domain=domain, source=source, dataset=dataset,
            discriminator=discriminator, ticker=ticker,
        )

    def get_backfill_floor_date(
        self, domain: str, source: str, dataset: str, discriminator: str, ticker: str
    ) -> date | None:
        return self._ops_repo.get_backfill_floor_date(
            domain=domain, source=source, dataset=dataset,
            discriminator=discriminator, ticker=ticker,
        )

    def set_backfill_floor_date(
        self, domain: str, source: str, dataset: str, discriminator: str, ticker: str,
        floor_date: date,
    ) -> None:
        self._ops_repo.upsert_backfill_floor_date(
            domain=domain, source=source, dataset=dataset,
            discriminator=discriminator, ticker=ticker, floor_date=floor_date,
        )

    def start_gold_build(self, *, run_id: str, model_version: str, started_at: datetime) -> int:
        return self._ops_repo.start_gold_build(run_id=run_id, model_version=model_version, started_at=started_at)

    def finish_gold_build(
        self,
        *,
        gold_build_id: int,
        finished_at: datetime,
        status: str,
        tables_built: list[str],
        row_counts: str,
        error_message: str | None = None,
    ) -> None:
        self._ops_repo.finish_gold_build(
            gold_build_id=gold_build_id,
            finished_at=finished_at,
            status=status,
            tables_built=tables_built,
            row_counts=row_counts,
            error_message=error_message,
        )


__all__ = ["OpsService"]
