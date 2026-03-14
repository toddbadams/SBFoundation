from __future__ import annotations

import duckdb

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance import DuckDbBootstrap


class EodFeatureService:
    """Computes and backfills EOD feature columns in gold.fact_eod.

    All computations are performed entirely in DuckDB SQL — no Python loops,
    no pandas. A single UPDATE ... FROM (nested subquery) statement computes:

    - momentum_1m_f  = adj_close / LAG(adj_close, 21)  − 1  (~1 month)
    - momentum_3m_f  = adj_close / LAG(adj_close, 63)  − 1  (~3 months)
    - momentum_6m_f  = adj_close / LAG(adj_close, 126) − 1  (~6 months)
    - momentum_12m_f = adj_close / LAG(adj_close, 252) − 1  (~12 months)
    - volatility_30d_f = rolling 30-day annualised StdDev of daily log returns
                        (STDDEV over 29-preceding window × √252)

    The inner subquery first computes per-row log returns, then the outer
    subquery applies LAG-based momentum and rolling STDDEV — avoiding
    the nested window function restriction in SQL.
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

    def build(self, run_id: str | None = None) -> int:
        """Compute and write EOD features to gold.fact_eod. Returns updated row count."""
        self._logger.info("EodFeatureService: computing EOD features", run_id=run_id)
        with self._bootstrap.gold_transaction() as conn:
            if not self._table_exists(conn, "gold", "fact_eod"):
                self._logger.info("EodFeatureService: gold.fact_eod not found — skipping", run_id=run_id)
                return 0
            rows = self._compute_features(conn)
        self._logger.info(f"EodFeatureService: rows with momentum_1m_f={rows}", run_id=run_id)
        return rows

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _table_exists(self, conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [schema, table],
        ).fetchone()
        return bool(row and row[0] > 0)

    def _compute_features(self, conn: duckdb.DuckDBPyConnection) -> int:
        # Step 1: inner subquery computes per-row log return (requires one LAG level).
        # Step 2: outer subquery applies momentum LAGs and rolling STDDEV of log_return.
        # This two-level nesting avoids placing a window function inside another window.
        conn.execute("""
            UPDATE gold.fact_eod AS dst
            SET
                momentum_1m_f    = src.momentum_1m_f,
                momentum_3m_f    = src.momentum_3m_f,
                momentum_6m_f    = src.momentum_6m_f,
                momentum_12m_f   = src.momentum_12m_f,
                volatility_30d_f = src.volatility_30d_f
            FROM (
                SELECT
                    instrument_sk,
                    date_sk,
                    adj_close / NULLIF(LAG(adj_close, 21)  OVER w, 0) - 1  AS momentum_1m_f,
                    adj_close / NULLIF(LAG(adj_close, 63)  OVER w, 0) - 1  AS momentum_3m_f,
                    adj_close / NULLIF(LAG(adj_close, 126) OVER w, 0) - 1  AS momentum_6m_f,
                    adj_close / NULLIF(LAG(adj_close, 252) OVER w, 0) - 1  AS momentum_12m_f,
                    STDDEV(log_return) OVER (
                        PARTITION BY instrument_sk
                        ORDER BY date_sk
                        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                    ) * SQRT(252) AS volatility_30d_f
                FROM (
                    SELECT
                        instrument_sk,
                        date_sk,
                        adj_close,
                        LN(adj_close / NULLIF(
                            LAG(adj_close) OVER (PARTITION BY instrument_sk ORDER BY date_sk), 0
                        )) AS log_return
                    FROM gold.fact_eod
                    WHERE adj_close IS NOT NULL AND adj_close > 0
                ) lr
                WINDOW w AS (PARTITION BY instrument_sk ORDER BY date_sk)
            ) src
            WHERE dst.instrument_sk = src.instrument_sk
              AND dst.date_sk = src.date_sk
        """)

        row = conn.execute(
            "SELECT COUNT(*) FROM gold.fact_eod WHERE momentum_1m_f IS NOT NULL"
        ).fetchone()
        return row[0] if row else 0
