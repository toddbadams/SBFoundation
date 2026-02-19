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

    def get_filtered_tickers(
        self,
        *,
        exchanges: list[str],
        sectors: list[str],
        industries: list[str],
        countries: list[str],
        limit: int = 0,
    ) -> list[str]:
        """Return ticker symbols filtered by dimension lists.

        Filter semantics: OR within a dimension, AND across dimensions.
        An empty list for a dimension means no filter on that dimension.

        Uses a three-tier fallback:
          1. silver.fmp_market_screener (preferred — authoritative dimension mapping)
          2. silver.fmp_company_profile joined to fmp_stock_list (secondary)
          3. All silver.fmp_stock_list symbols (bootstrap fallback)

        Args:
            exchanges: Exchange short names to include (e.g. ["NASDAQ", "NYSE"])
            sectors: Sectors to include (e.g. ["Technology"])
            industries: Industries to include (e.g. ["Software-Application"])
            countries: Countries to include (e.g. ["US"])
            limit: Maximum symbols to return (0 = no limit)

        Returns:
            List of ticker symbols matching the filters.
        """
        conn = self._bootstrap.connect()
        limit_clause = f"LIMIT {limit}" if limit > 0 else ""

        def _build_conditions(prefix: str, exchange_col: str = "exchange") -> tuple[list[str], list[str]]:
            conds: list[str] = []
            vals: list[str] = []
            for col, values in [
                (f"{prefix}{exchange_col}", exchanges),
                (f"{prefix}sector", sectors),
                (f"{prefix}industry", industries),
                (f"{prefix}country", countries),
            ]:
                if values:
                    placeholders = ", ".join("?" * len(values))
                    conds.append(f"{col} IN ({placeholders})")
                    vals.extend(values)
            return conds, vals

        # Tier 1: fmp_market_screener
        screener_exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'silver' AND table_name = 'fmp_market_screener'"
        ).fetchone()
        if screener_exists and screener_exists[0] > 0:
            screener_count = conn.execute("SELECT COUNT(*) FROM silver.fmp_market_screener").fetchone()
            if screener_count and screener_count[0] > 0:
                conds, vals = _build_conditions("", exchange_col="exchange_short_name")
                where_clause = ("WHERE " + " AND ".join(conds)) if conds else ""
                sql = f"SELECT DISTINCT symbol FROM silver.fmp_market_screener {where_clause} {limit_clause}"
                result = conn.execute(sql, vals).fetchall()
                return [row[0] for row in result if row[0]]

        # Tier 2: fmp_company_profile join
        profile_exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'silver' AND table_name = 'fmp_company_profile'"
        ).fetchone()
        if profile_exists and profile_exists[0] > 0:
            profile_count = conn.execute("SELECT COUNT(*) FROM silver.fmp_company_profile").fetchone()
            if profile_count and profile_count[0] > 0:
                self._logger.warning("fmp_market_screener not yet populated — falling back to fmp_company_profile join")
                conds, vals = _build_conditions("cp.")
                where_clause = ("WHERE " + " AND ".join(conds)) if conds else ""
                sql = (
                    "SELECT sl.symbol "
                    "FROM silver.fmp_stock_list sl "
                    "JOIN silver.fmp_company_profile cp ON sl.symbol = cp.ticker "
                    f"{where_clause} {limit_clause}"
                )
                result = conn.execute(sql, vals).fetchall()
                return [row[0] for row in result if row[0]]

        # Tier 3: bootstrap fallback
        self._logger.warning(
            "Neither fmp_market_screener nor fmp_company_profile populated — returning all fmp_stock_list symbols"
        )
        result = conn.execute(
            f"SELECT symbol FROM silver.fmp_stock_list WHERE symbol IS NOT NULL {limit_clause}"
        ).fetchall()
        return [row[0] for row in result if row[0]]


__all__ = ["UniverseRepo"]
