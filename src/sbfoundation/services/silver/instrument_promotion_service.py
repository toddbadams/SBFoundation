"""Service for promoting instrument discovery data to unified instrument table."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import duckdb

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger


class InstrumentPromotionService:
    """Handles special promotion logic for instrument domain datasets.

    This service:
    1. Processes instrument discovery endpoints (CREATE behavior)
    2. Processes instrument enrichment endpoints (ENRICH behavior)
    3. Manages the unified silver.instrument table
    """

    # Maps dataset name to (source_table, instrument_type)
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

    def promote_to_unified_instrument(self, source_dataset: str, run_id: str) -> int:
        """Promote rows from a discovery source table to unified instrument table.

        Args:
            source_dataset: The source dataset name (e.g., 'stock-list')
            run_id: Current run ID for lineage

        Returns:
            Number of rows promoted (inserted or updated)
        """
        if source_dataset not in self.INSTRUMENT_SOURCE_TABLES:
            self._logger.debug(f"Dataset {source_dataset} is not an instrument discovery endpoint", run_id=run_id)
            return 0

        source_table, instrument_type = self.INSTRUMENT_SOURCE_TABLES[source_dataset]
        conn = self._bootstrap.connect()

        # Check if source table exists
        if not self._table_exists(conn, "silver", source_table):
            self._logger.debug(f"Source table silver.{source_table} does not exist yet", run_id=run_id)
            return 0

        # Build the MERGE statement
        # For forex pairs, derive base_currency and quote_currency from symbol
        # Note: Use just `symbol` here since we're inside the subquery, not referencing alias
        base_currency_expr = (
            f"CASE WHEN '{instrument_type}' = 'forex' AND length(symbol) = 6 "
            f"THEN left(symbol, 3) ELSE NULL END"
        )
        quote_currency_expr = (
            f"CASE WHEN '{instrument_type}' = 'forex' AND length(symbol) = 6 "
            f"THEN right(symbol, 3) ELSE NULL END"
        )

        # Get exchange column name - varies by source table
        exchange_col = "exchange" if instrument_type in ("equity", "etf") else "stock_exchange"

        # Currency column only exists in index, forex, and crypto DTOs
        # Stock and ETF lists don't have currency, so we use NULL
        currency_expr = "currency" if instrument_type in ("index", "forex", "crypto") else "NULL"

        sql = f"""
        MERGE INTO silver.instrument AS target
        USING (
            SELECT
                gen_random_uuid()::VARCHAR as instrument_id,
                symbol,
                '{instrument_type}' as instrument_type,
                '{source_dataset}' as source_endpoint,
                name,
                {exchange_col} as exchange,
                exchange_short_name,
                {currency_expr} as currency,
                {base_currency_expr} as base_currency,
                {quote_currency_expr} as quote_currency,
                TRUE as is_active,
                CURRENT_TIMESTAMP as discovered_at,
                bronze_file_id,
                run_id,
                ingested_at
            FROM silver.{source_table}
            WHERE run_id = ?
        ) AS source
        ON target.symbol = source.symbol AND target.instrument_type = source.instrument_type
        WHEN MATCHED THEN UPDATE SET
            name = COALESCE(source.name, target.name),
            exchange = COALESCE(source.exchange, target.exchange),
            exchange_short_name = COALESCE(source.exchange_short_name, target.exchange_short_name),
            currency = COALESCE(source.currency, target.currency),
            is_active = TRUE,
            last_enriched_at = CURRENT_TIMESTAMP
        WHEN NOT MATCHED THEN INSERT (
            instrument_id, symbol, instrument_type, source_endpoint, name, exchange,
            exchange_short_name, currency, base_currency, quote_currency, is_active,
            discovered_at, bronze_file_id, run_id, ingested_at
        ) VALUES (
            source.instrument_id, source.symbol, source.instrument_type, source.source_endpoint,
            source.name, source.exchange, source.exchange_short_name, source.currency,
            source.base_currency, source.quote_currency, source.is_active, source.discovered_at,
            source.bronze_file_id, source.run_id, source.ingested_at
        )
        """

        try:
            result = conn.execute(sql, [run_id])
            # DuckDB returns affected row count from MERGE
            count = result.fetchone()
            rows_affected = count[0] if count else 0
            self._logger.info(
                f"Promoted {rows_affected} instruments from {source_dataset} to unified instrument table",
                run_id=run_id,
            )
            return rows_affected
        except Exception as exc:
            self._logger.error(f"Failed to promote instruments from {source_dataset}: {exc}", run_id=run_id)
            raise

    def instrument_exists(self, symbol: str, instrument_type: str | None = None) -> bool:
        """Check if an instrument exists in the unified instrument table.

        For ENRICH behavior endpoints, this must return True before any data
        can be written. Prevents creation of orphan enrichment data.

        Args:
            symbol: The instrument symbol to check
            instrument_type: Optional instrument type filter

        Returns:
            True if instrument exists, False otherwise
        """
        conn = self._bootstrap.connect()

        # Check if instrument table exists
        if not self._table_exists(conn, "silver", "instrument"):
            return False

        sql = "SELECT COUNT(*) > 0 FROM silver.instrument WHERE symbol = ?"
        params: list = [symbol]

        if instrument_type:
            sql += " AND instrument_type = ?"
            params.append(instrument_type)

        result = conn.execute(sql, params).fetchone()
        return bool(result and result[0])

    def get_active_instruments(
        self,
        instrument_type: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict]:
        """Retrieve active instruments from the unified table.

        Args:
            instrument_type: Optional filter by type
            limit: Maximum number to return
            offset: Starting offset

        Returns:
            List of instrument dictionaries
        """
        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "silver", "instrument"):
            return []

        sql = "SELECT * FROM silver.instrument WHERE is_active = TRUE"
        params: list = []

        if instrument_type:
            sql += " AND instrument_type = ?"
            params.append(instrument_type)

        sql += f" ORDER BY symbol LIMIT {limit} OFFSET {offset}"

        result = conn.execute(sql, params)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    def count_instruments(self, instrument_type: str | None = None) -> int:
        """Count active instruments in the unified table.

        Args:
            instrument_type: Optional filter by type

        Returns:
            Count of matching instruments
        """
        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "silver", "instrument"):
            return 0

        sql = "SELECT COUNT(*) FROM silver.instrument WHERE is_active = TRUE"
        params: list = []

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
