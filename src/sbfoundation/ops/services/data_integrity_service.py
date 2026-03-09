from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance import DuckDbBootstrap


class DataIntegrityService:
    """Records per-file, per-layer integrity events in ops.run_integrity.

    Lifecycle:
    - call check_bronze()  after each Bronze file write
    - call check_silver()  after each Silver promotion attempt
    - call check_gold()    after each Gold build step
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

    def record(
        self,
        *,
        run_id: str,
        layer: str,
        domain: str | None = None,
        source: str | None = None,
        dataset: str | None = None,
        discriminator: str = "",
        ticker: str = "",
        file_id: str | None = None,
        status: str,
        rows_in: int | None = None,
        rows_out: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """Insert one integrity record. Non-fatal on failure."""
        try:
            with self._bootstrap.ops_transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO ops.run_integrity
                        (run_id, layer, domain, source, dataset, discriminator, ticker,
                         file_id, status, rows_in, rows_out, error_message, checked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        run_id, layer, domain, source, dataset,
                        discriminator, ticker, file_id, status,
                        rows_in, rows_out, error_message,
                        datetime.now(timezone.utc),
                    ],
                )
        except Exception as exc:
            self._logger.warning(f"DataIntegrityService.record failed (non-fatal): {exc}", run_id=run_id)

    def summary(self, run_id: str) -> dict[str, Any]:
        """Return counts by (layer, status) for a given run_id."""
        try:
            with self._bootstrap.read_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT layer, status, COUNT(*) AS cnt
                    FROM ops.run_integrity
                    WHERE run_id = ?
                    GROUP BY layer, status
                    ORDER BY layer, status
                    """,
                    [run_id],
                ).fetchall()
            return {f"{row[0]}.{row[1]}": row[2] for row in rows}
        except Exception as exc:
            self._logger.warning(f"DataIntegrityService.summary failed: {exc}")
            return {}


__all__ = ["DataIntegrityService"]
