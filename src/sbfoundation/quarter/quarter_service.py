from __future__ import annotations

from datetime import date

from sbfoundation.infra.logger import LoggerFactory, SBLogger


class QuarterService:
    """Orchestrates bulk quarterly fundamental ingestion.

    Only runs during earnings seasons:
    - Jan 1 - Mar 31  (Q4 prior year filings)
    - Apr 1 - May 31  (Q1 filings)
    - Jul 1 - Aug 31  (Q2 filings)
    - Oct 1 - Nov 30  (Q3 filings)
    """

    QUARTER_DATASETS = [
        "income-statement-bulk-quarter",
        "balance-sheet-bulk-quarter",
        "cashflow-bulk-quarter",
    ]

    def __init__(self, logger: SBLogger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)

    @staticmethod
    def is_earnings_season(today: date) -> bool:
        """Return True if today falls within an earnings filing window."""
        m = today.month
        # Jan 1 - Mar 31
        if m in (1, 2, 3):
            return True
        # Apr 1 - May 31
        if m in (4, 5):
            return True
        # Jul 1 - Aug 31
        if m in (7, 8):
            return True
        # Oct 1 - Nov 30
        if m in (10, 11):
            return True
        return False
