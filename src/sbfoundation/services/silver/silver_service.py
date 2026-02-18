from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.dtos.bronze_result import BronzeResult
from sbfoundation.folders import Folders
from sbfoundation.settings import *
from sbfoundation.dataset.models.dataset_identity import DatasetIdentity
from sbfoundation.dataset.models.dataset_keymap import DatasetKeymap
from sbfoundation.dataset.models.dataset_keymap_entry import DatasetKeymapEntry
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.services.bronze.bronze_batch_reader import BronzeBatchReader
from sbfoundation.run.services.chunk_engine import ChunkEngine
from sbfoundation.run.services.dedupe_engine import DedupeEngine
from sbfoundation.dtos.dto_projection import DTOProjection
from sbfoundation.dtos.models import BronzeManifestRow
from sbfoundation.ops.requests.promotion_config import PromotionConfig
from sbfoundation.infra.result_file_adaptor import ResultFileAdapter
from sbfoundation.ops.services.ops_service import OpsService


class SilverService:
    """Promote Bronze manifest rows into Silver DuckDB tables."""

    def __init__(
        self,
        enabled: bool = True,
        logger: SBLogger | None = None,
        bootstrap: DuckDbBootstrap | None = None,
        keymap_service: DatasetService | None = None,
        result_file_adapter: ResultFileAdapter | None = None,
        promotion_config: PromotionConfig | None = None,
        bronze_batch_reader: BronzeBatchReader | None = None,
        dto_projection: DTOProjection | None = None,
        chunk_engine: ChunkEngine | None = None,
        dedupe_engine: DedupeEngine | None = None,
        ops_service: OpsService | None = None,
    ) -> None:
        self._enabled = enabled
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None
        self._result_file_adapter = result_file_adapter or ResultFileAdapter()
        self._promotion_config = promotion_config or PromotionConfig()
        self._bronze_batch_reader = bronze_batch_reader or BronzeBatchReader(self._result_file_adapter)
        self._dto_projection = dto_projection or DTOProjection()
        self._chunk_engine = chunk_engine or ChunkEngine(strategy=self._promotion_config.chunk_strategy)
        self._dedupe_engine = dedupe_engine or DedupeEngine(use_duckdb_engine=self._promotion_config.use_duckdb_engine)
        self._ops_service = ops_service or OpsService()
        self._owns_ops_service = ops_service is None
        keymap_service = keymap_service or DatasetService()
        self.keymap = keymap_service.load_dataset_keymap()

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()
        if self._owns_ops_service:
            self._ops_service.close()

    def promote(self, run: RunContext, domain: str | None = None) -> tuple[list[str], int]:
        prefix = "PROCESSING SILVER" if self._enabled else "DRY-RUN SILVER"
        ingestions = self._ops_service.load_promotable_file_ingestions()
        if domain is not None:
            ingestions = [i for i in ingestions if i.domain == domain]
        if not ingestions:
            self._logger.info("%s | No promotable Bronze rows found.", prefix, run_id=run.run_id)
            return [], 0

        if not self._enabled:
            self._logger.info("%s | %s files eligible (skipped)", prefix, len(ingestions), run_id=run.run_id)
            return [], 0

        self._logger.info("%s | %s files to promote", prefix, len(ingestions), run_id=run.run_id)

        promoted: list[str] = []
        promoted_rows = 0

        for ingestion in ingestions:
            self._logger.info(f"{prefix} | promoting | {ingestion.msg}", run_id=ingestion.run_id)
            self._ops_service.start_silver_ingestion(ingestion)
            manifest_row = ingestion.to_bronze_manifest_row()
            try:
                rows_seen, rows_written, coverage_from, coverage_to, table_name = self._promote_row(manifest_row, self.keymap)
            except Exception as exc:
                self._logger.warning(
                    "Silver promotion failed | file_id=%s | dataset=%s | error=%s",
                    ingestion.file_id,
                    ingestion.dataset,
                    exc,
                    run_id=ingestion.run_id,
                )
                self._ops_service.finish_silver_ingestion(
                    ingestion,
                    rows_seen=0,
                    rows_written=0,
                    rows_failed=0,
                    table_name=None,
                    coverage_from=None,
                    coverage_to=None,
                    error=str(exc),
                )
                continue
            self._ops_service.finish_silver_ingestion(
                ingestion,
                rows_seen=rows_seen,
                rows_written=rows_written,
                rows_failed=max(rows_seen - rows_written, 0),
                table_name=table_name,
                coverage_from=coverage_from,
                coverage_to=coverage_to,
                error=None,
            )
            promoted.append(ingestion.file_id)
            promoted_rows += rows_written

        self._logger.info(
            "PROCESSING SILVER | complete | bronze_files=%s | rows=%s",
            len(promoted),
            promoted_rows,
            run_id=run.run_id,
        )
        return promoted, promoted_rows

    def _resolve_keymap_entry_safe(self, row: BronzeManifestRow, keymap: DatasetKeymap) -> DatasetKeymapEntry | None:
        """Safely resolve keymap entry, returning None on failure."""
        try:
            return self._resolve_keymap_entry(row, keymap)
        except Exception:
            return None

    def _promote_row(self, row: BronzeManifestRow, keymap: DatasetKeymap) -> tuple[int, int, date | None, date | None, str]:
        entry = self._resolve_keymap_entry(row, keymap)

        # SILVER LAYER: Clean, standalone datasets only
        # NO surrogate keys (instrument_sk), NO relationships, NO Gold dependencies
        # Surrogate key resolution and relationships are Gold layer concerns

        batch = self._bronze_batch_reader.read(row)
        dto_schema = entry.dto_schema
        dto_type = None
        if dto_schema is None:
            dto_type = self._resolve_dto_type(row, batch.result)

        ticker_override = row.ticker if entry.ticker_scope == "per_ticker" and row.ticker else None
        df_projected = self._dto_projection.project(
            batch.df_content,
            dto_type=dto_type,
            dto_schema=dto_schema,
            ticker_override=ticker_override,
        )
        if df_projected.empty:
            return 0, 0, None, None, ""

        df_projected["bronze_file_id"] = row.bronze_file_id
        df_projected["run_id"] = row.run_id
        df_projected["ingested_at"] = row.ingested_at

        row_date_col = entry.row_date_col or "as_of_date"
        self._ensure_row_date(df_projected, row_date_col, row)
        self._ensure_key_cols_df(df_projected, entry.key_cols, row)
        self._coerce_numeric_columns(df_projected, ["market_cap"])

        watermark = self._ops_service.get_silver_watermark(
            domain=row.domain,
            source=row.source,
            dataset=row.dataset,
            discriminator=row.discriminator or "",
            ticker=row.ticker or "",
        )
        if watermark and self._promotion_config.watermark_mode != "none":
            df_projected = self._apply_watermark(df_projected, row_date_col, watermark)

        if df_projected.empty:
            return 0, 0, None, None, ""

        conn = self._bootstrap.connect()
        table_exists = self._table_exists(conn, entry.silver_schema, entry.silver_table)
        target_table = self._qualified_table(entry.silver_schema, entry.silver_table)
        df_projected = self._dedupe_engine.dedupe_against_table(
            conn,
            df_candidate=df_projected,
            key_cols=entry.key_cols,
            target_table=target_table,
            table_exists=table_exists,
        )

        rows_seen = len(df_projected)
        coverage_from, coverage_to = self._coverage_dates(df_projected, row_date_col)
        rows_written = 0
        for chunk in self._chunk_engine.chunk(df_projected, row_date_col=row_date_col):
            if chunk.df.empty:
                continue
            with self._bootstrap.silver_transaction() as txn:
                self._merge_rows(txn, entry, chunk.df, table_exists=table_exists)
            rows_written += len(chunk.df)
            table_exists = True

        return rows_seen, rows_written, coverage_from, coverage_to, target_table

    def _resolve_keymap_entry(self, row: BronzeManifestRow, keymap: DatasetKeymap) -> DatasetKeymapEntry:
        """Resolve the shared dataset keymap entry and enforce ticker requirements."""
        identity = DatasetIdentity(
            domain=row.domain,
            source=row.source,
            dataset=row.dataset,
            discriminator=row.discriminator or "",
            ticker=row.ticker or "",
        )
        entry = keymap.find(identity)
        # Fallback 1: strip runtime discriminator (e.g. snapshot date written by date-loop)
        if entry is None and row.discriminator:
            identity = DatasetIdentity(
                domain=row.domain,
                source=row.source,
                dataset=row.dataset,
                discriminator="",
                ticker=row.ticker or "",
            )
            entry = keymap.find(identity)
        # Fallback 2: strip ticker
        if entry is None and row.ticker:
            identity = DatasetIdentity(
                domain=row.domain,
                source=row.source,
                dataset=row.dataset,
                discriminator=row.discriminator or "",
                ticker="",
            )
            entry = keymap.find(identity)
        if entry is None:
            # The keymap is the single source of truth for dataset contracts.
            raise KeyError(f"Missing dataset keymap entry for {identity}")
        if entry.ticker_scope == "per_ticker" and not row.ticker:
            raise ValueError(f"Dataset keymap requires ticker for {identity}")
        return entry

    def _load_bronze_payload(self, row: BronzeManifestRow) -> BronzeResult:
        rel_path = Path(row.file_path_rel)
        abs_path = (Folders.data_absolute_path() / rel_path).resolve()
        if not abs_path.exists():
            raise FileNotFoundError(f"Bronze payload missing: {abs_path}")
        result = self._result_file_adapter.read(abs_path)
        if not isinstance(result, BronzeResult):
            raise ValueError(f"Bronze payload is not a BronzeResult: {abs_path}")
        return result

    def _resolve_dto_type(self, row: BronzeManifestRow, result: BronzeResult) -> type[BronzeToSilverDTO]:
        dto_type = None
        request = getattr(result, "request", None)
        if request is not None:
            dto_type = getattr(request, "dto_type", None)
        if dto_type is None:
            dto_type = DTO_REGISTRY.get(row.dataset)
        if dto_type is None or not issubclass(dto_type, BronzeToSilverDTO):
            raise ValueError(f"Missing DTO mapping for dataset {row.dataset}")
        return dto_type

    def _ensure_row_date(self, df: pd.DataFrame, row_date_col: str, row: BronzeManifestRow) -> None:
        if row_date_col not in df.columns:
            fallback = row.coverage_to_date or row.coverage_from_date or row.ingested_at
            df[row_date_col] = fallback
        df[row_date_col] = pd.to_datetime(df[row_date_col], errors="coerce")

    def _coerce_numeric_columns(self, df: pd.DataFrame, columns: list[str]) -> None:
        for column in columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce").astype("float64")

    def _ensure_key_cols_df(self, df: pd.DataFrame, key_cols: tuple[str, ...], row: BronzeManifestRow) -> None:
        missing = [col for col in key_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Silver rows missing key columns {missing} for {row.dataset}")

    def _merge_rows(
        self,
        conn: duckdb.DuckDBPyConnection,
        entry: DatasetKeymapEntry,
        df: pd.DataFrame,
        *,
        table_exists: bool,
    ) -> None:
        if df.empty:
            return
        conn.register("_silver_rows", df)
        try:
            full_table = self._qualified_table(entry.silver_schema, entry.silver_table)
            if not table_exists and not self._table_exists(conn, entry.silver_schema, entry.silver_table):
                conn.execute(f"CREATE TABLE {full_table} AS SELECT * FROM _silver_rows")
                return

            key_cols = entry.key_cols
            on_clause = " AND ".join(f"{self._qualified_ident('target', col)} = {self._qualified_ident('source', col)}" for col in key_cols)
            update_cols = list(df.columns)
            update_set = ", ".join(f"{self._quote_ident(col)} = {self._qualified_ident('source', col)}" for col in update_cols)
            insert_cols = ", ".join(self._quote_ident(col) for col in update_cols)
            insert_vals = ", ".join(self._qualified_ident("source", col) for col in update_cols)

            sql = (
                f"MERGE INTO {full_table} AS target "
                "USING _silver_rows AS source "
                f"ON {on_clause} "
                f"WHEN MATCHED THEN UPDATE SET {update_set} "
                f"WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})"
            )
            conn.execute(sql)
        finally:
            conn.unregister("_silver_rows")

    @staticmethod
    def _apply_watermark(df: pd.DataFrame, row_date_col: str, watermark: date) -> pd.DataFrame:
        if row_date_col not in df.columns:
            return df
        dates = pd.to_datetime(df[row_date_col], errors="coerce").dt.date
        return df.loc[dates > watermark].copy()

    @staticmethod
    def _coverage_dates(df: pd.DataFrame, row_date_col: str) -> tuple[date | None, date | None]:
        if row_date_col not in df.columns:
            return None, None
        dates = pd.to_datetime(df[row_date_col], errors="coerce").dt.date
        if dates.empty:
            return None, None
        return dates.min(), dates.max()

    @staticmethod
    def _quote_ident(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    def _qualified_table(self, schema: str, table: str) -> str:
        return f"{self._quote_ident(schema)}.{self._quote_ident(table)}"

    def _qualified_ident(self, alias: str, name: str) -> str:
        return f"{alias}.{self._quote_ident(name)}"

    @staticmethod
    def _table_exists(conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [schema, table],
        ).fetchone()
        return bool(row and row[0] > 0)
