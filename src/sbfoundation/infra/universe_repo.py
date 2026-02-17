from __future__ import annotations


from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger


class UniverseRepo:
    """Repository for universe/instrument data access.

    Handles all DuckDB operations for instrument universe queries including:
    - Querying ingested tickers from ops.file_ingestions
    - Querying new tickers from gold.dim_instrument
    - Retrieving instrument details from ops.instrument_catalog
    """

    def __init__(
        self,
        logger: SBLogger | None = None,
        bootstrap: DuckDbBootstrap | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    def get_update_tickers(
        self,
        *,
        start: int = 0,
        limit: int = 50,
        instrument_type: str | None = None,
        is_active: bool = True,
    ) -> list[str]:
        """Return tickers already ingested into the data warehouse.

        Queries ops.file_ingestions for distinct tickers that have been
        successfully promoted to silver.

        Args:
            start: Starting offset
            limit: Maximum number of symbols to return
            instrument_type: Filter by type (applied via ops.instrument_catalog join)
            is_active: Only return active instruments (default True)

        Returns:
            List of instrument symbols already in the data warehouse
        """
        conn = self._bootstrap.connect()

        if instrument_type or is_active:
            sql = """
                SELECT DISTINCT fi.ticker
                FROM ops.file_ingestions fi
                INNER JOIN ops.instrument_catalog ic ON fi.ticker = ic.symbol
                WHERE fi.ticker IS NOT NULL AND fi.ticker <> ''
                AND fi.silver_can_promote = TRUE
            """
            params: list = []

            if is_active:
                sql += " AND ic.is_active = TRUE"

            if instrument_type:
                sql += " AND ic.instrument_type = ?"
                params.append(instrument_type)

            sql += f" ORDER BY fi.ticker LIMIT {limit} OFFSET {start}"
            result = conn.execute(sql, params).fetchall()
            return [row[0] for row in result if row[0]]
        else:
            sql = (
                "SELECT DISTINCT ticker FROM ops.file_ingestions "
                "WHERE ticker IS NOT NULL AND ticker <> '' "
                "AND silver_can_promote = TRUE "
                f"ORDER BY ticker LIMIT {limit} OFFSET {start}"
            )
            result = conn.execute(sql).fetchall()
            return [row[0] for row in result if row[0]]

    def get_new_tickers(
        self,
        *,
        start: int = 0,
        limit: int = 50,
        instrument_type: str | None = None,
        is_active: bool = True,
    ) -> list[str]:
        """Return tickers from instrument dimensions not yet ingested.

        Queries gold.dim_instrument for instruments that have no corresponding
        entries in ops.file_ingestions (new instruments to process).

        Args:
            start: Starting offset
            limit: Maximum number of symbols to return
            instrument_type: Filter by type ('equity', 'etf', 'index', 'crypto', 'forex')
            is_active: Only return active instruments (default True)

        Returns:
            List of new instrument symbols to ingest
        """
        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "gold", "dim_instrument"):
            return []

        sql = """
            SELECT di.symbol
            FROM gold.dim_instrument di
            WHERE di.is_current = TRUE
            AND NOT EXISTS (
                SELECT 1 FROM ops.file_ingestions fi
                WHERE fi.ticker = di.symbol
                AND fi.ticker IS NOT NULL AND fi.ticker <> ''
                AND fi.silver_can_promote = TRUE
            )
        """
        params: list = []

        if is_active:
            sql += " AND di.is_active = TRUE"

        if instrument_type:
            sql += " AND di.instrument_type = ?"
            params.append(instrument_type)

        sql += f" ORDER BY di.symbol LIMIT {limit} OFFSET {start}"

        result = conn.execute(sql, params).fetchall()
        return [row[0] for row in result if row[0]]

    def count_update_tickers(self, instrument_type: str | None = None) -> int:
        """Return count of tickers already ingested into the data warehouse.

        Args:
            instrument_type: Optional filter by type

        Returns:
            Count of ingested tickers
        """
        conn = self._bootstrap.connect()

        if instrument_type:
            sql = """
                SELECT COUNT(DISTINCT fi.ticker)
                FROM ops.file_ingestions fi
                INNER JOIN ops.instrument_catalog ic ON fi.ticker = ic.symbol
                WHERE fi.ticker IS NOT NULL AND fi.ticker <> ''
                AND fi.silver_can_promote = TRUE
                AND ic.instrument_type = ?
            """
            result = conn.execute(sql, [instrument_type]).fetchone()
        else:
            sql = (
                "SELECT COUNT(DISTINCT ticker) FROM ops.file_ingestions "
                "WHERE ticker IS NOT NULL AND ticker <> '' "
                "AND silver_can_promote = TRUE"
            )
            result = conn.execute(sql).fetchone()

        return result[0] if result else 0

    def count_new_tickers(self, instrument_type: str | None = None) -> int:
        """Return count of new tickers from instrument dimensions not yet ingested.

        Args:
            instrument_type: Optional filter by type

        Returns:
            Count of new tickers
        """
        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "gold", "dim_instrument"):
            return 0

        sql = """
            SELECT COUNT(di.symbol)
            FROM gold.dim_instrument di
            WHERE di.is_current = TRUE
            AND di.is_active = TRUE
            AND NOT EXISTS (
                SELECT 1 FROM ops.file_ingestions fi
                WHERE fi.ticker = di.symbol
                AND fi.ticker IS NOT NULL AND fi.ticker <> ''
                AND fi.silver_can_promote = TRUE
            )
        """
        params: list = []

        if instrument_type:
            sql += " AND di.instrument_type = ?"
            params.append(instrument_type)

        result = conn.execute(sql, params).fetchone()
        return result[0] if result else 0

    def get_instrument(self, symbol: str) -> dict | None:
        """Retrieve instrument details by symbol.

        Args:
            symbol: The instrument symbol

        Returns:
            Instrument details as dict, or None if not found
        """
        conn = self._bootstrap.connect()

        if not self._table_exists(conn, "ops", "instrument_catalog"):
            return None

        result = conn.execute(
            "SELECT * FROM ops.instrument_catalog WHERE symbol = ?",
            [symbol],
        ).fetchone()

        if result:
            columns = [desc[0] for desc in conn.description]
            return dict(zip(columns, result))
        return None

    def _table_exists(self, conn, schema: str, table: str) -> bool:
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


__all__ = ["UniverseRepo"]
