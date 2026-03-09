from __future__ import annotations

import subprocess
from datetime import datetime, timezone

import duckdb

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance import DuckDbBootstrap


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


class GoldDimService:
    """Builds gold.dim_instrument and gold.dim_company from Silver data.

    Silver sources:
    - silver.fmp_company_profile_bulk  -> dim_company (primary) + dim_instrument (fallback)
    - silver.fmp_eod_bulk_price        -> dim_instrument (symbol coverage)

    SK stability: INSERT INTO ... ON CONFLICT DO NOTHING so existing SKs never change.
    Non-key attributes are updated via a subsequent UPDATE WHERE symbol = ?
    """

    def __init__(
        self,
        bootstrap: DuckDbBootstrap | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap(logger=self._logger)
        self._owns_bootstrap = bootstrap is None

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    def build(self, gold_build_id: int | None = None, run_id: str | None = None) -> dict[str, int]:
        """Build dim_instrument and dim_company from Silver. Returns row counts."""
        model_version = _git_sha()
        now = datetime.now(timezone.utc).isoformat()
        self._logger.info("GoldDimService: building dims", run_id=run_id)

        with self._bootstrap.gold_transaction() as conn:
            dim_instrument_rows = self._build_dim_instrument(conn, gold_build_id, model_version, now)
        self._logger.info(f"GoldDimService: dim_instrument rows={dim_instrument_rows}", run_id=run_id)

        with self._bootstrap.gold_transaction() as conn:
            dim_company_rows = self._build_dim_company(conn, gold_build_id, model_version, now)
        self._logger.info(f"GoldDimService: dim_company rows={dim_company_rows}", run_id=run_id)

        return {"dim_instrument": dim_instrument_rows, "dim_company": dim_company_rows}

    def _build_dim_instrument(
        self, conn: duckdb.DuckDBPyConnection, gold_build_id: int | None, model_version: str, now: str
    ) -> int:
        """Populate dim_instrument from silver.fmp_company_profile_bulk + silver.fmp_eod_bulk_price."""

        # Collect all known symbols (union of both Silver sources)
        conn.execute("""
            INSERT INTO gold.dim_instrument (
                symbol, instrument_type_sk, exchange_sk, sector_sk, industry_sk,
                country_sk, is_etf, is_actively_trading, gold_build_id, model_version, updated_at
            )
            SELECT DISTINCT
                src.symbol,
                dit.instrument_type_sk,
                dex.exchange_sk,
                ds.sector_sk,
                di.industry_sk,
                dc.country_sk,
                COALESCE(src.is_etf, FALSE)               AS is_etf,
                COALESCE(src.is_actively_trading, TRUE)   AS is_actively_trading,
                $1                                         AS gold_build_id,
                $2                                         AS model_version,
                $3::TIMESTAMP                              AS updated_at
            FROM (
                SELECT
                    symbol,
                    CASE WHEN is_etf THEN 'etf' ELSE 'stock' END AS instrument_type,
                    exchange_short_name                            AS exchange_code,
                    sector,
                    industry,
                    country                                        AS country_code,
                    is_etf,
                    is_actively_trading
                FROM silver.fmp_company_profile_bulk
                WHERE symbol IS NOT NULL AND symbol != ''
                UNION
                SELECT
                    symbol,
                    'stock'  AS instrument_type,
                    NULL     AS exchange_code,
                    NULL     AS sector,
                    NULL     AS industry,
                    NULL     AS country_code,
                    FALSE    AS is_etf,
                    TRUE     AS is_actively_trading
                FROM silver.fmp_eod_bulk_price
                WHERE symbol IS NOT NULL AND symbol != ''
            ) src
            LEFT JOIN gold.dim_instrument_type dit ON dit.instrument_type = src.instrument_type
            LEFT JOIN gold.dim_exchange dex ON dex.exchange_code = src.exchange_code
            LEFT JOIN gold.dim_sector ds ON ds.sector = src.sector
            LEFT JOIN gold.dim_industry di ON di.industry = src.industry
            LEFT JOIN gold.dim_country dc ON dc.country_code = src.country_code
            ON CONFLICT (symbol) DO NOTHING
        """, [gold_build_id, model_version, now])

        row = conn.execute("SELECT COUNT(*) FROM gold.dim_instrument").fetchone()
        return row[0] if row else 0

    def _build_dim_company(
        self, conn: duckdb.DuckDBPyConnection, gold_build_id: int | None, model_version: str, now: str
    ) -> int:
        """Populate dim_company from silver.fmp_company_profile_bulk."""

        conn.execute("""
            INSERT INTO gold.dim_company (
                symbol, instrument_sk, company_name, ceo, website, description,
                full_time_employees, ipo_date, currency,
                country_sk, exchange_sk, sector_sk, industry_sk,
                gold_build_id, model_version, updated_at
            )
            SELECT
                src.symbol,
                inst.instrument_sk,
                src.company_name,
                src.ceo,
                src.website,
                src.description,
                src.full_time_employees::INTEGER,
                src.ipo_date::DATE,
                src.currency,
                dc.country_sk,
                dex.exchange_sk,
                ds.sector_sk,
                di.industry_sk,
                $1             AS gold_build_id,
                $2             AS model_version,
                $3::TIMESTAMP  AS updated_at
            FROM silver.fmp_company_profile_bulk src
            LEFT JOIN gold.dim_instrument inst ON inst.symbol = src.symbol
            LEFT JOIN gold.dim_country dc  ON dc.country_code  = src.country
            LEFT JOIN gold.dim_exchange dex ON dex.exchange_code = src.exchange_short_name
            LEFT JOIN gold.dim_sector ds   ON ds.sector = src.sector
            LEFT JOIN gold.dim_industry di ON di.industry = src.industry
            WHERE src.symbol IS NOT NULL AND src.symbol != ''
            ON CONFLICT (symbol) DO NOTHING
        """, [gold_build_id, model_version, now])

        row = conn.execute("SELECT COUNT(*) FROM gold.dim_company").fetchone()
        return row[0] if row else 0
