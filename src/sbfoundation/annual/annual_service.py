from __future__ import annotations

from datetime import date

from sbfoundation.infra.logger import LoggerFactory, SBLogger


class AnnualService:
    """Orchestrates bulk annual fundamental ingestion.

    Only runs during the annual filing window: January through March (FY filings).
    """

    ANNUAL_DATASETS = [
        "income-statement-bulk-annual",
        "balance-sheet-bulk-annual",
        "cashflow-bulk-annual",
    ]

    def __init__(self, logger: SBLogger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)

    @staticmethod
    def is_annual_season(today: date) -> bool:
        """Return True if today falls within the annual filing window (Jan-Mar)."""
        return today.month in (1, 2, 3)
