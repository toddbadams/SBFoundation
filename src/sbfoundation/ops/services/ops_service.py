from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import duckdb


from sbfoundation.dataset.models.dataset_identity import DatasetIdentity
from sbfoundation.ops.dtos.file_injestion import DatasetInjestion
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo
from sbfoundation.infra.logger import LoggerFactory
from sbfoundation.run.dtos.run_result import RunResult
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.services.universe_service import UniverseService


class OpsService:
    def __init__(self, ops_repo: DuckDbOpsRepo | None = None, universe: UniverseService | None = None, logger: logging.Logger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._ops_repo = ops_repo or DuckDbOpsRepo()
        self._owns_ops_repo = ops_repo is None
        self._universe = universe or UniverseService()

    def close(self) -> None:
        if self._owns_ops_repo:
            self._ops_repo.close()

    # --- Run Summary ---#
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

    def finish_run(self, summary: RunContext) -> None:
        if summary is None:
            return
        summary.finished_at = self._universe.now()
        self.close()

    # --- BRONZE MANIFEST ---#
    def insert_bronze_manifest(self, result: RunResult) -> None:
        ingestion = DatasetInjestion.from_bronze(result=result)
        try:
            self._ops_repo.upsert_file_ingestion(ingestion)
        except Exception as exc:
            self._logger.error("File ingestion persistence failed: %s", exc)
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
            self._logger.warning("Silver start persistence failed: %s", exc)

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
            self._logger.warning("Silver finish persistence failed: %s", exc)

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

    def load_input_watermarks(self, conn: duckdb.DuckDBPyConnection, *, datasets: set[str]) -> list[str]:
        return self._ops_repo.load_input_watermarks(conn, datasets=datasets)

    def next_gold_build_id(self, conn: duckdb.DuckDBPyConnection) -> int:
        return self._ops_repo.next_gold_build_id(conn)

    def insert_gold_build(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        gold_build_id: int,
        run_id: str,
        model_version: str,
        started_at: datetime,
        finished_at: datetime,
        status: str,
        error_message: str | None,
        input_watermarks: list[str],
        row_counts: dict[str, int],
    ) -> None:
        self._ops_repo.insert_gold_build(
            conn,
            gold_build_id=gold_build_id,
            run_id=run_id,
            model_version=model_version,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            error_message=error_message,
            input_watermarks=input_watermarks,
            row_counts=row_counts,
        )

    def start_gold_manifest(self, conn: duckdb.DuckDBPyConnection, *, gold_build_id: int, table_name: str) -> None:
        self._ops_repo.start_gold_manifest(conn, gold_build_id=gold_build_id, table_name=table_name)

    def finish_gold_manifest(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        gold_build_id: int,
        table_name: str,
        status: str,
        rows_seen: int,
        rows_written: int,
        error_message: str | None,
    ) -> None:
        self._ops_repo.finish_gold_manifest(
            conn,
            gold_build_id=gold_build_id,
            table_name=table_name,
            status=status,
            rows_seen=rows_seen,
            rows_written=rows_written,
            error_message=error_message,
        )

    def get_gold_watermark(self, conn: duckdb.DuckDBPyConnection, *, table_name: str) -> date | None:
        return self._ops_repo.get_gold_watermark(conn, table_name=table_name)

    def upsert_gold_watermark(self, conn: duckdb.DuckDBPyConnection, *, table_name: str, watermark_date: date | None) -> None:
        self._ops_repo.upsert_gold_watermark(conn, table_name=table_name, watermark_date=watermark_date)

    def update_gold_ingestion_times(
        self, *, run_id: str, gold_injest_start_time: datetime | None = None, gold_injest_end_time: datetime | None = None
    ) -> None:
        try:
            self._ops_repo.update_gold_ingestion_times(
                run_id=run_id,
                gold_injest_start_time=gold_injest_start_time,
                gold_injest_end_time=gold_injest_end_time,
            )
        except Exception as exc:
            self._logger.warning("Failed to persist gold ingestion timestamps: %s", exc)

    def load_dataset_ingestions(self, *, run_id: str, identity: DatasetIdentity, ticker_scope: str) -> list[DatasetInjestion]:
        try:
            return self._ops_repo.load_file_ingestions(
                run_id=run_id,
                identity=identity,
                ticker_scope=ticker_scope,
            )
        except Exception as exc:
            self._logger.warning("Failed to load file ingestions for gold metadata: %s", exc)
            return []

    def ensure_dataset_ingestions(
        self,
        *,
        run_id: str,
        identity: DatasetIdentity,
        ticker_scope: str,
        tickers: list[str] | None = None,
    ) -> list[DatasetInjestion]:
        ingestions = self.load_dataset_ingestions(run_id=run_id, identity=identity, ticker_scope=ticker_scope)
        if ingestions:
            return ingestions
        created = self._create_stub_ingestions(
            run_id=run_id,
            identity=identity,
            ticker_scope=ticker_scope,
            tickers=tickers,
        )
        if created:
            return created
        return self.load_dataset_ingestions(run_id=run_id, identity=identity, ticker_scope=ticker_scope)

    def start_gold_ingestion(
        self,
        *,
        run_id: str,
        identity: DatasetIdentity,
        ticker_scope: str,
        started_at: datetime | None = None,
        tickers: list[str] | None = None,
    ) -> None:
        started_at = started_at or self._universe.now()
        ingestions = self.ensure_dataset_ingestions(
            run_id=run_id,
            identity=identity,
            ticker_scope=ticker_scope,
            tickers=tickers,
        )
        if not ingestions:
            self._logger.warning("No ingestions found for gold start: %s", identity)
            return
        for ingestion in ingestions:
            ingestion.gold_injest_start_time = started_at
            try:
                self._ops_repo.upsert_file_ingestion(ingestion)
            except Exception as exc:
                self._logger.warning("Gold start persistence failed: %s", exc)

    def finish_gold_ingestion(
        self,
        *,
        run_id: str,
        identity: DatasetIdentity,
        ticker_scope: str,
        object_types: list[str],
        table_names: list[str],
        rows_created: int,
        rows_updated: int,
        rows_failed: int,
        coverage_from: date | None,
        coverage_to: date | None,
        error: str | None,
        can_promote: bool,
        finished_at: datetime | None = None,
        tickers: list[str] | None = None,
    ) -> None:
        finished_at = finished_at or self._universe.now()
        ingestions = self.ensure_dataset_ingestions(
            run_id=run_id,
            identity=identity,
            ticker_scope=ticker_scope,
            tickers=tickers,
        )
        if not ingestions:
            self._logger.warning("No ingestions found for gold finish: %s", identity)
            return
        object_type_value = ", ".join(sorted(set(object_types))) if object_types else None
        table_name_value = ", ".join(sorted(set(table_names))) if table_names else None
        for ingestion in ingestions:
            ingestion.gold_object_type = object_type_value
            ingestion.gold_tablename = table_name_value
            ingestion.gold_rows_created = rows_created
            ingestion.gold_rows_updated = rows_updated
            ingestion.gold_rows_failed = rows_failed
            ingestion.gold_from_date = coverage_from
            ingestion.gold_to_date = coverage_to
            ingestion.gold_errors = error
            ingestion.gold_can_promote = can_promote and error is None
            ingestion.gold_injest_end_time = finished_at
            try:
                self._ops_repo.upsert_file_ingestion(ingestion)
            except Exception as exc:
                self._logger.warning("Gold finish persistence failed: %s", exc)

    def _create_stub_ingestions(
        self,
        *,
        run_id: str,
        identity: DatasetIdentity,
        ticker_scope: str,
        tickers: list[str] | None,
    ) -> list[DatasetInjestion]:
        resolved_tickers = self._resolve_stub_tickers(identity=identity, ticker_scope=ticker_scope, tickers=tickers)
        ingestions: list[DatasetInjestion] = []
        for ticker in resolved_tickers:
            ingestion = DatasetInjestion(
                run_id=run_id,
                file_id=self._stub_file_id(run_id=run_id, identity=identity, ticker=ticker),
                domain=identity.domain,
                source=identity.source,
                dataset=identity.dataset,
                discriminator=identity.discriminator or None,
                ticker=ticker or None,
            )
            try:
                self._ops_repo.upsert_file_ingestion(ingestion)
                ingestions.append(ingestion)
            except Exception as exc:
                self._logger.warning("Stub ingestion persistence failed: %s", exc)
        return ingestions

    def _resolve_stub_tickers(
        self,
        *,
        identity: DatasetIdentity,
        ticker_scope: str,
        tickers: list[str] | None,
    ) -> list[str]:
        if ticker_scope == "global":
            return [""]
        if identity.ticker:
            return [identity.ticker]
        if ticker_scope == "per_ticker":
            if tickers:
                return [ticker for ticker in tickers if ticker]
            return self._universe.update_tickers(limit=50)
        return [""]

    @staticmethod
    def _stub_file_id(*, run_id: str, identity: DatasetIdentity, ticker: str) -> str:
        discriminator = identity.discriminator or ""
        ticker_token = ticker or ""
        return f"gold-stub:{run_id}:{identity.domain}:{identity.source}:{identity.dataset}:{discriminator}:{ticker_token}"

    def get_tickers_with_bronze_error(self, *, dataset: str, error_contains: str) -> set[str]:
        """Get distinct tickers that have a bronze_error containing the specified string.

        Args:
            dataset: The dataset name to filter by (e.g., "company-profile")
            error_contains: The substring to search for in bronze_error (e.g., "INVALID TICKER")

        Returns:
            Set of ticker symbols that have the specified error
        """
        try:
            with self._bootstrap.ops_transaction() as conn:
                result = conn.execute(
                    """
                    SELECT DISTINCT ticker
                    FROM ops.file_ingestions
                    WHERE dataset = ?
                      AND bronze_error IS NOT NULL
                      AND bronze_error LIKE ?
                      AND ticker IS NOT NULL
                    """,
                    [dataset, f"%{error_contains}%"],
                ).fetchall()
                return {row[0] for row in result if row[0]}
        except Exception as exc:
            self._logger.warning("Failed to get tickers with bronze error: %s", exc)
            return set()


__all__ = ["OpsService"]
