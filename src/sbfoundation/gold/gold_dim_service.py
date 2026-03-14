from __future__ import annotations

import subprocess
from datetime import datetime, timezone

import duckdb

from sbfoundation.gold.moat_feature_service import MoatFeatureService
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance import DuckDbBootstrap


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
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

    def _table_exists(self, conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [schema, table],
        ).fetchone()
        return bool(row and row[0] > 0)

    def _build_dim_instrument(self, conn: duckdb.DuckDBPyConnection, gold_build_id: int | None, model_version: str, now: str) -> int:
        """Populate dim_instrument from available Silver sources.

        Priority (richest metadata first, ON CONFLICT DO NOTHING preserves first insert):
          1. silver.fmp_company_profile_bulk  — full metadata
          2. silver.fmp_eod_bulk_price        — symbol coverage
          3. silver.fmp_income_statement_bulk_annual   — symbol only (fallback)
          4. silver.fmp_income_statement_bulk_quarter  — symbol only (fallback)
        """
        profile_exists = self._table_exists(conn, "silver", "fmp_company_profile_bulk")
        eod_exists = self._table_exists(conn, "silver", "fmp_eod_bulk_price")
        annual_exists = self._table_exists(conn, "silver", "fmp_income_statement_bulk_annual")
        quarter_exists = self._table_exists(conn, "silver", "fmp_income_statement_bulk_quarter")

        if not any([profile_exists, eod_exists, annual_exists, quarter_exists]):
            self._logger.info("GoldDimService: no silver source tables for dim_instrument — skipping")
            row = conn.execute("SELECT COUNT(*) FROM gold.dim_instrument").fetchone()
            return row[0] if row else 0

        symbol_only_select = "symbol, 'stock' AS instrument_type, NULL AS exchange_code, NULL AS sector, NULL AS industry, NULL AS country_code, FALSE AS is_etf, TRUE AS is_actively_trading"

        parts = []
        if profile_exists:
            parts.append(
                """
                SELECT symbol,
                    CASE WHEN is_etf THEN 'etf' ELSE 'stock' END AS instrument_type,
                    exchange_short_name AS exchange_code,
                    sector, industry,
                    country AS country_code,
                    is_etf, is_actively_trading
                FROM silver.fmp_company_profile_bulk
                WHERE symbol IS NOT NULL AND symbol != ''"""
            )
        if eod_exists:
            parts.append(
                f"""
                SELECT {symbol_only_select}
                FROM silver.fmp_eod_bulk_price
                WHERE symbol IS NOT NULL AND symbol != ''"""
            )
        if annual_exists:
            parts.append(
                f"""
                SELECT {symbol_only_select}
                FROM silver.fmp_income_statement_bulk_annual
                WHERE symbol IS NOT NULL AND symbol != ''"""
            )
        if quarter_exists:
            parts.append(
                f"""
                SELECT {symbol_only_select}
                FROM silver.fmp_income_statement_bulk_quarter
                WHERE symbol IS NOT NULL AND symbol != ''"""
            )

        union_sql = " UNION ".join(parts)

        # Step 1: insert new symbols only — ON CONFLICT DO NOTHING preserves existing instrument_sk
        # (DuckDB treats DO UPDATE as delete+insert, which violates FK constraints from fact tables)
        conn.execute(
            f"""
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
            FROM ({union_sql}) src
            LEFT JOIN gold.dim_instrument_type dit ON dit.instrument_type = src.instrument_type
            LEFT JOIN gold.dim_exchange dex ON dex.exchange_code = src.exchange_code
            LEFT JOIN gold.dim_sector ds ON ds.sector = src.sector
            LEFT JOIN gold.dim_industry di ON di.industry = src.industry
            LEFT JOIN gold.dim_country dc ON dc.country_code = src.country_code
            ON CONFLICT (symbol) DO NOTHING
        """,
            [gold_build_id, model_version, now],
        )

        # Step 2: backfill NULL FK columns for existing rows using the richest available source.
        # A plain UPDATE does not trigger FK constraints from child tables referencing instrument_sk.
        conn.execute(
            f"""
            UPDATE gold.dim_instrument di
            SET
                instrument_type_sk  = COALESCE(di.instrument_type_sk,  src.instrument_type_sk),
                exchange_sk         = COALESCE(di.exchange_sk,          src.exchange_sk),
                sector_sk           = COALESCE(di.sector_sk,            src.sector_sk),
                industry_sk         = COALESCE(di.industry_sk,          src.industry_sk),
                country_sk          = COALESCE(di.country_sk,           src.country_sk),
                gold_build_id       = $1,
                model_version       = $2,
                updated_at          = $3::TIMESTAMP
            FROM (
                SELECT DISTINCT ON (src.symbol)
                    src.symbol,
                    dit.instrument_type_sk,
                    dex.exchange_sk,
                    ds.sector_sk,
                    di2.industry_sk,
                    dc.country_sk
                FROM ({union_sql}) src
                LEFT JOIN gold.dim_instrument_type dit ON dit.instrument_type = src.instrument_type
                LEFT JOIN gold.dim_exchange dex ON dex.exchange_code = src.exchange_code
                LEFT JOIN gold.dim_sector ds ON ds.sector = src.sector
                LEFT JOIN gold.dim_industry di2 ON di2.industry = src.industry
                LEFT JOIN gold.dim_country dc ON dc.country_code = src.country_code
                -- prioritise rows with the most FK data
                ORDER BY src.symbol,
                    (dit.instrument_type_sk IS NOT NULL)::INT +
                    (dex.exchange_sk IS NOT NULL)::INT +
                    (ds.sector_sk IS NOT NULL)::INT +
                    (di2.industry_sk IS NOT NULL)::INT +
                    (dc.country_sk IS NOT NULL)::INT DESC
            ) src
            WHERE di.symbol = src.symbol
              AND (
                  di.instrument_type_sk IS NULL OR di.exchange_sk IS NULL OR
                  di.sector_sk IS NULL OR di.industry_sk IS NULL OR di.country_sk IS NULL
              )
        """,
            [gold_build_id, model_version, now],
        )

        row = conn.execute("SELECT COUNT(*) FROM gold.dim_instrument").fetchone()
        return row[0] if row else 0

    def _build_dim_company(self, conn: duckdb.DuckDBPyConnection, gold_build_id: int | None, model_version: str, now: str) -> int:
        """Populate dim_company from silver.fmp_company_profile_bulk."""
        if not self._table_exists(conn, "silver", "fmp_company_profile_bulk"):
            self._logger.info("GoldDimService: silver.fmp_company_profile_bulk not found — skipping dim_company")
            row = conn.execute("SELECT COUNT(*) FROM gold.dim_company").fetchone()
            return row[0] if row else 0

        conn.execute(
            """
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
        """,
            [gold_build_id, model_version, now],
        )

        row = conn.execute("SELECT COUNT(*) FROM gold.dim_company").fetchone()
        return row[0] if row else 0


if __name__ == "__main__":
    from sbfoundation.maintenance import DuckDbBootstrap

    DuckDbBootstrap().connect()
    GoldDimService().build()
    MoatFeatureService().build()
