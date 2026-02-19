from __future__ import annotations


from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger


class UniverseRepo:
    """Repository for universe/instrument data access.

    Handles all DuckDB operations for instrument universe queries including:
    - Querying ingested tickers from ops.file_ingestions
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
    ) -> list[str]:
        """Return tickers already ingested into the data warehouse.

        Queries ops.file_ingestions for distinct tickers that have been
        successfully promoted to silver.

        Args:
            start: Starting offset
            limit: Maximum number of symbols to return

        Returns:
            List of instrument symbols already in the data warehouse
        """
        conn = self._bootstrap.connect()
        sql = (
            "SELECT DISTINCT ticker FROM ops.file_ingestions "
            "WHERE ticker IS NOT NULL AND ticker <> '' "
            "AND silver_can_promote = TRUE "
            f"ORDER BY ticker LIMIT {limit} OFFSET {start}"
        )
        result = conn.execute(sql).fetchall()
        return [row[0] for row in result if row[0]]

    def count_update_tickers(self) -> int:
        """Return count of tickers already ingested into the data warehouse.

        Returns:
            Count of ingested tickers
        """
        conn = self._bootstrap.connect()
        sql = (
            "SELECT COUNT(DISTINCT ticker) FROM ops.file_ingestions "
            "WHERE ticker IS NOT NULL AND ticker <> '' "
            "AND silver_can_promote = TRUE"
        )
        result = conn.execute(sql).fetchone()
        return result[0] if result else 0


__all__ = ["UniverseRepo"]
