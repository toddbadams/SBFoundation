"""
DerivedMetricsService — nightly compute of eligibility metrics per symbol.

Computes and persists to silver.universe_derived_metrics:
  - computed_market_cap   : price × shares_outstanding
  - avg_dollar_volume_30d : 30-trading-day avg(close × volume)
  - avg_dollar_volume_90d : 90-trading-day avg(close × volume)
  - is_actively_trading   : from silver.fmp_market_screener isActivelyTrading flag
  - data_coverage_score   : fraction of expected daily bars present (trailing 1 year)

All computations are tolerant of missing source tables — a symbol with no price
history will have NULLs for ADTV/coverage rather than raising an error.
"""

from __future__ import annotations

from datetime import date

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbuniverse.infra.universe_repo import UniverseRepo

# Expected trading days per year (approximate)
_TRADING_DAYS_PER_YEAR = 252


class DerivedMetricsService:
    """Compute and persist derived eligibility metrics for universe symbols."""

    def __init__(
        self,
        logger: SBLogger | None = None,
        repo: UniverseRepo | None = None,
        bootstrap: DuckDbBootstrap | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._repo = repo or UniverseRepo(logger=self._logger, bootstrap=self._bootstrap)
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    def compute_and_persist(
        self,
        symbols: list[str],
        as_of_date: date,
        run_id: str,
    ) -> int:
        """Compute derived metrics for all symbols and upsert into silver.

        Returns the number of rows written.
        """
        if not symbols:
            return 0

        rows = self._compute(symbols, as_of_date, run_id)
        if rows:
            self._repo.upsert_derived_metrics(rows=rows)
            self._logger.info(
                f"Derived metrics written: {len(rows)} symbols as_of={as_of_date}",
                run_id=run_id,
            )
        return len(rows)

    # -------------------------------------------------------------------------
    # Internal compute
    # -------------------------------------------------------------------------

    def _compute(
        self,
        symbols: list[str],
        as_of_date: date,
        run_id: str,
    ) -> list[dict]:
        """Return a list of metric dicts, one per symbol."""
        conn = self._bootstrap.connect()

        # Build a temporary VALUES table for the symbol list so we can JOIN once.
        # DuckDB supports VALUES(...) as an inline table.
        symbol_placeholders = ", ".join(f"('{s}')" for s in symbols if "'" not in s)
        if not symbol_placeholders:
            return []

        price_table_exists = self._table_exists("fmp_technicals_historical_price_eod_full")
        shares_table_exists = self._table_exists("fmp_company_shares_float")
        screener_table_exists = self._table_exists("fmp_market_screener")

        rows: list[dict] = []

        try:
            # ── ADTV (30d, 90d) + data coverage score ────────────────────────
            adtv_map: dict[str, dict] = {}
            if price_table_exists:
                adtv_sql = f"""
                    WITH symbols AS (
                        SELECT column0 AS ticker
                        FROM (VALUES {symbol_placeholders})
                    ),
                    price_data AS (
                        SELECT p.ticker,
                               p.date,
                               p.close * p.volume AS dollar_volume
                        FROM silver.fmp_technicals_historical_price_eod_full p
                        JOIN symbols s ON p.ticker = s.ticker
                        WHERE p.date <= '{as_of_date.isoformat()}'
                          AND p.close IS NOT NULL
                          AND p.volume IS NOT NULL
                    ),
                    adtv AS (
                        SELECT ticker,
                            AVG(CASE WHEN date >= '{as_of_date.isoformat()}'::DATE - INTERVAL 30 DAY
                                     THEN dollar_volume END) AS adtv_30d,
                            AVG(CASE WHEN date >= '{as_of_date.isoformat()}'::DATE - INTERVAL 90 DAY
                                     THEN dollar_volume END) AS adtv_90d,
                            COUNT(CASE WHEN date >= '{as_of_date.isoformat()}'::DATE - INTERVAL 365 DAY
                                       THEN 1 END) AS days_present_1y
                        FROM price_data
                        GROUP BY ticker
                    )
                    SELECT ticker, adtv_30d, adtv_90d,
                           ROUND(CAST(days_present_1y AS DOUBLE) / {_TRADING_DAYS_PER_YEAR}, 4)
                               AS coverage_score
                    FROM adtv
                """
                for row in conn.execute(adtv_sql).fetchall():
                    adtv_map[row[0]] = {
                        "avg_dollar_volume_30d": row[1],
                        "avg_dollar_volume_90d": row[2],
                        "data_coverage_score": min(float(row[3]), 1.0) if row[3] is not None else None,
                    }

            # ── Computed market cap (price × shares_outstanding) ──────────────
            mktcap_map: dict[str, float | None] = {}
            if price_table_exists and shares_table_exists:
                mktcap_sql = f"""
                    WITH symbols AS (
                        SELECT column0 AS ticker
                        FROM (VALUES {symbol_placeholders})
                    ),
                    latest_price AS (
                        SELECT ticker, close
                        FROM silver.fmp_technicals_historical_price_eod_full
                        WHERE date = '{as_of_date.isoformat()}'
                          AND close IS NOT NULL
                    ),
                    latest_shares AS (
                        SELECT ticker, outstanding_shares
                        FROM silver.fmp_company_shares_float
                        QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) = 1
                    )
                    SELECT s.ticker,
                           p.close * sh.outstanding_shares AS computed_market_cap
                    FROM symbols s
                    JOIN latest_price  p  ON s.ticker = p.ticker
                    JOIN latest_shares sh ON s.ticker = sh.ticker
                """
                for row in conn.execute(mktcap_sql).fetchall():
                    mktcap_map[row[0]] = row[1]

            # ── is_actively_trading from screener ─────────────────────────────
            active_map: dict[str, bool | None] = {}
            if screener_table_exists:
                active_sql = f"""
                    WITH symbols AS (
                        SELECT column0 AS ticker
                        FROM (VALUES {symbol_placeholders})
                    )
                    SELECT DISTINCT ON (ms.symbol) ms.symbol, ms.is_actively_trading
                    FROM silver.fmp_market_screener ms
                    JOIN symbols s ON ms.symbol = s.ticker
                    ORDER BY ms.symbol, ms.ingested_at DESC
                """
                for row in conn.execute(active_sql).fetchall():
                    active_map[row[0]] = row[1]

        except Exception as exc:
            self._logger.warning(f"Derived metrics compute error: {exc}", run_id=run_id)
            return []

        # ── Assemble one row per symbol ───────────────────────────────────────
        for symbol in symbols:
            adtv = adtv_map.get(symbol, {})
            rows.append(
                {
                    "symbol": symbol,
                    "as_of_date": as_of_date,
                    "computed_market_cap": mktcap_map.get(symbol),
                    "avg_dollar_volume_30d": adtv.get("avg_dollar_volume_30d"),
                    "avg_dollar_volume_90d": adtv.get("avg_dollar_volume_90d"),
                    "is_actively_trading": active_map.get(symbol),
                    "data_coverage_score": adtv.get("data_coverage_score"),
                    "run_id": run_id,
                }
            )

        return rows

    def _table_exists(self, table_name: str, schema: str = "silver") -> bool:
        conn = self._bootstrap.connect()
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = ? AND table_name = ?",
            [schema, table_name],
        ).fetchone()
        return bool(result and result[0] > 0)


__all__ = ["DerivedMetricsService"]
