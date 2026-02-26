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

    def get_delisted_tickers(self) -> list[str]:
        """Return distinct tickers from silver.fmp_company_delisted.

        Used to build a survivorship-bias-free backfill universe: tickers that were
        listed during the backtest period (2010–present) but have since delisted are
        included so their price and fundamental history can be ingested.

        Returns:
            Sorted list of distinct delisted ticker symbols, or [] if the table
            does not exist or is empty.
        """
        conn = self._bootstrap.connect()
        try:
            exists = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'silver' AND table_name = 'fmp_company_delisted'"
            ).fetchone()
            if not exists or exists[0] == 0:
                return []
            result = conn.execute(
                "SELECT DISTINCT ticker FROM silver.fmp_company_delisted "
                "WHERE ticker IS NOT NULL AND ticker <> '' "
                "ORDER BY ticker"
            ).fetchall()
            return [row[0] for row in result if row[0]]
        except Exception as exc:
            self._logger.warning(f"Could not query silver.fmp_company_delisted: {exc}")
            return []

    def get_filtered_tickers(
        self,
        *,
        exchanges: list[str],
        sectors: list[str],
        industries: list[str],
        countries: list[str],
        limit: int = 0,
        min_market_cap_usd: float | None = None,
        max_market_cap_usd: float | None = None,
    ) -> list[str]:
        """Return ticker symbols filtered by dimension lists and optional market-cap bounds.

        Filter semantics: OR within a dimension, AND across dimensions.
        An empty list for a dimension means no filter on that dimension.

        When min_market_cap_usd or max_market_cap_usd are set, tickers are joined
        to a CTE that selects the most recent market cap per ticker from
        silver.fmp_company_market_cap, and filtered by the bound(s).

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
            min_market_cap_usd: Minimum market cap in USD (inclusive). None = no lower bound.
            max_market_cap_usd: Maximum market cap in USD (inclusive). None = no upper bound.

        Returns:
            List of ticker symbols matching the filters.
        """
        conn = self._bootstrap.connect()
        limit_clause = f"LIMIT {limit}" if limit > 0 else ""
        use_market_cap = min_market_cap_usd is not None or max_market_cap_usd is not None

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

        def _market_cap_cte_and_join(ticker_col: str) -> tuple[str, str, list]:
            """Return (cte_sql, join_clause, param_values) for market-cap filtering.

            The CTE selects the single most recent market_cap row per ticker from
            silver.fmp_company_market_cap. The join filters by min/max bounds.
            """
            if not use_market_cap:
                return "", "", []

            mktcap_conds: list[str] = []
            mktcap_vals: list[float] = []
            if min_market_cap_usd is not None:
                mktcap_conds.append("mc.market_cap >= ?")
                mktcap_vals.append(min_market_cap_usd)
            if max_market_cap_usd is not None:
                mktcap_conds.append("mc.market_cap <= ?")
                mktcap_vals.append(max_market_cap_usd)

            mktcap_where = " AND ".join(mktcap_conds)

            cte = (
                "WITH latest_mktcap AS ("
                "  SELECT ticker, market_cap"
                "  FROM silver.fmp_company_market_cap"
                "  QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) = 1"
                ") "
            )
            join_clause = (
                f"JOIN latest_mktcap mc ON {ticker_col} = mc.ticker "
                f"AND {mktcap_where}"
            )
            return cte, join_clause, mktcap_vals

        # Tier 1: fmp_market_screener
        screener_exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'silver' AND table_name = 'fmp_market_screener'"
        ).fetchone()
        if screener_exists and screener_exists[0] > 0:
            screener_count = conn.execute("SELECT COUNT(*) FROM silver.fmp_market_screener").fetchone()
            if screener_count and screener_count[0] > 0:
                # Tier 1 uses the screener's own market_cap column directly.
                # fmp_company_market_cap is only populated for already-ingested
                # tickers, so an INNER JOIN would silently exclude the majority
                # of the universe before any company/fundamentals data is loaded.
                conds, vals = _build_conditions("", exchange_col="exchange_short_name")
                if min_market_cap_usd is not None:
                    conds.append("market_cap >= ?")
                    vals.append(min_market_cap_usd)
                if max_market_cap_usd is not None:
                    conds.append("market_cap <= ?")
                    vals.append(max_market_cap_usd)
                where_clause = ("WHERE " + " AND ".join(conds)) if conds else ""
                sql = (
                    f"SELECT DISTINCT symbol FROM silver.fmp_market_screener "
                    f"{where_clause} {limit_clause}"
                )
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
                cte, mc_join, mc_vals = _market_cap_cte_and_join("sl.symbol")
                sql = (
                    f"{cte}"
                    "SELECT sl.symbol "
                    "FROM silver.fmp_stock_list sl "
                    "JOIN silver.fmp_company_profile cp ON sl.symbol = cp.ticker "
                    f"{mc_join} {where_clause} {limit_clause}"
                )
                result = conn.execute(sql, mc_vals + vals).fetchall()
                return [row[0] for row in result if row[0]]

        # Tier 3: bootstrap fallback — market cap filter still applied if set
        self._logger.warning(
            "Neither fmp_market_screener nor fmp_company_profile populated — returning all fmp_stock_list symbols"
        )
        cte, mc_join, mc_vals = _market_cap_cte_and_join("fmp_stock_list.symbol")
        sql = (
            f"{cte}"
            f"SELECT fmp_stock_list.symbol FROM silver.fmp_stock_list "
            f"{mc_join} WHERE fmp_stock_list.symbol IS NOT NULL {limit_clause}"
        )
        result = conn.execute(sql, mc_vals).fetchall()
        return [row[0] for row in result if row[0]]


__all__ = ["UniverseRepo"]
