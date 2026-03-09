from __future__ import annotations

from sbfoundation.infra.logger import LoggerFactory, SBLogger


class EodService:
    """Orchestrates daily bulk EOD + company profile bulk ingestion.

    Both datasets are global (ticker_scope: global) — a single API call
    returns data for all symbols. No ticker loop is required.
    Cadence: daily on weekdays.
    """

    EOD_DATASETS = ["eod-bulk-price", "company-profile-bulk"]

    def __init__(self, logger: SBLogger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
