"""Service for managing ops.instrument_catalog (operational instrument metadata)."""

from __future__ import annotations

from datetime import datetime, timezone

import duckdb

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger


class InstrumentCatalogService:
    """Manages the ops.instrument_catalog table.

    This service populates and maintains the operational instrument catalog
    from Silver instrument list tables (stock-list, etf-list, index-list, etc.).

    The catalog is used by UniverseRepo to filter tickers by instrument_type
    and is_active status during orchestration.
    """

    # Maps dataset name to (silver_table, instrument_type)
    INSTRUMENT_SOURCE_TABLES: dict[str, tuple[str, str]] = {
        "stock-list": ("fmp_stock_list", "equity"),
        "etf-list": ("fmp_etf_list", "etf"),
        "index-list": ("fmp_index_list", "index"),
        "cryptocurrency-list": ("fmp_cryptocurrency_list", "crypto"),
        "forex-list": ("fmp_forex_list", "forex"),
    }

    def __init__(
        self,
        bootstrap: DuckDbBootstrap | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    def sync_from_silver_tables(self, run_id: str) -> int:
        """Sync ops.instrument_catalog from all Silver instrument list tables.

        Reads from silver.fmp_stock_list, silver.fmp_etf_list, etc. and
        merges into ops.instrument_catalog.

        Args:
            run_id: Current run ID for logging

        Returns:
            Total number of instruments synced (inserted or updated)
        """
        conn = self._bootstrap.connect()
        total_synced = 0

        for dataset, (silver_table, instrument_type) in self.INSTRUMENT_SOURCE_TABLES.items():
            try:
                count = self._sync_from_table(conn, dataset, silver_table, instrument_type, run_id)
                total_synced += count
                self._logger.info(
                    f"Synced {count} instruments from {silver_table} ({instrument_type})",
                    run_id=run_id,
                )
            except Exception as exc:
                self._logger.warning(
                    f"Failed to sync from {silver_table}: {exc}",
                    run_id=run_id,
                )

        self._logger.info(f"Total instruments synced: {total_synced}", run_id=run_id)
        return total_synced

    def _sync_from_table(
        self,
        conn: duckdb.DuckDBPyConnection,
        dataset: str,
        silver_table: str,
        instrument_type: str,
        run_id: str,
    ) -> int:
        """Sync instruments from a single Silver table.

        Args:
            conn: DuckDB connection
            dataset: Dataset name (e.g., 'stock-list')
            silver_table: Silver table name (e.g., 'fmp_stock_list')
            instrument_type: Instrument type (e.g., 'equity')
            run_id: Current run ID

        Returns:
            Number of rows affected (inserted or updated)
        """
        # Check if source table exists
        if not self._table_exists(conn, "silver", silver_table):
            self._logger.debug(f"Silver table {silver_table} does not exist yet", run_id=run_id)
            return 0

        # Build MERGE statement to upsert into ops.instrument_catalog
        sql = f"""
        MERGE INTO ops.instrument_catalog AS target
        USING (
            SELECT
                symbol,
                '{instrument_type}' as instrument_type,
                '{dataset}' as source_endpoint,
                TRUE as is_active,
                CURRENT_TIMESTAMP as discovered_at
            FROM silver.{silver_table}
            WHERE symbol IS NOT NULL AND symbol <> ''
            QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ingested_at DESC) = 1
        ) AS source
        ON target.symbol = source.symbol AND target.instrument_type = source.instrument_type
        WHEN MATCHED THEN UPDATE SET
            is_active = TRUE,
            last_enriched_at = CURRENT_TIMESTAMP
        WHEN NOT MATCHED THEN INSERT (
            symbol, instrument_type, source_endpoint, is_active, discovered_at, last_enriched_at
        ) VALUES (
            source.symbol, source.instrument_type, source.source_endpoint,
            source.is_active, source.discovered_at, NULL
        )
        """

        try:
            result = conn.execute(sql)
            # DuckDB MERGE returns affected row count
            count = result.fetchone()
            return count[0] if count else 0
        except Exception as exc:
            self._logger.error(f"MERGE failed for {silver_table}: {exc}", run_id=run_id)
            raise

    def mark_inactive(self, symbol: str, instrument_type: str | None = None) -> int:
        """Mark an instrument as inactive in the catalog.

        Args:
            symbol: Instrument symbol
            instrument_type: Optional instrument type (marks all types if None)

        Returns:
            Number of rows updated
        """
        conn = self._bootstrap.connect()

        if instrument_type:
            sql = """
                UPDATE ops.instrument_catalog
                SET is_active = FALSE, last_enriched_at = CURRENT_TIMESTAMP
                WHERE symbol = ? AND instrument_type = ?
            """
            result = conn.execute(sql, [symbol, instrument_type])
        else:
            sql = """
                UPDATE ops.instrument_catalog
                SET is_active = FALSE, last_enriched_at = CURRENT_TIMESTAMP
                WHERE symbol = ?
            """
            result = conn.execute(sql, [symbol])

        count = result.fetchone()
        return count[0] if count else 0

    def get_instrument_count(self, instrument_type: str | None = None, is_active: bool = True) -> int:
        """Count instruments in the catalog.

        Args:
            instrument_type: Optional filter by type
            is_active: Filter by active status (default True)

        Returns:
            Count of matching instruments
        """
        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "ops", "instrument_catalog"):
            return 0

        sql = "SELECT COUNT(*) FROM ops.instrument_catalog WHERE is_active = ?"
        params: list = [is_active]

        if instrument_type:
            sql += " AND instrument_type = ?"
            params.append(instrument_type)

        result = conn.execute(sql, params).fetchone()
        return result[0] if result else 0

    def _table_exists(self, conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
        """Check if a table exists in the database."""
        result = conn.execute(
            """
            SELECT COUNT(*) > 0
            FROM information_schema.tables
            WHERE table_schema = ? AND table_name = ?
            """,
            [schema, table],
        ).fetchone()
        return bool(result and result[0])


__all__ = ["InstrumentCatalogService"]
