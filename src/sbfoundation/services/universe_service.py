from __future__ import annotations

from datetime import date, datetime, timezone
import typing
import uuid

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.infra.universe_repo import UniverseRepo
from sbfoundation.settings import *


class UniverseService:
    """Service for managing the instrument universe.

    This service provides access to:
    - The canonical list of tradeable instruments already ingested into the data warehouse
    - Time/date utilities for orchestration
    """

    def __init__(self, logger: SBLogger | None = None, repo: UniverseRepo | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._repo = repo or UniverseRepo(logger=self._logger)
        self._owns_repo = repo is None

    def close(self) -> None:
        if self._owns_repo:
            self._repo.close()

    def update_tickers(self, start: int = 0, limit: int = 50) -> list[str]:
        """Return tickers already ingested into the data warehouse.

        Queries ops.file_ingestions for distinct tickers that have been
        successfully promoted to silver.

        Args:
            start: Starting offset
            limit: Maximum number of symbols to return

        Returns:
            List of instrument symbols already in the data warehouse
        """
        if limit <= 0:
            return []

        try:
            return self._repo.get_update_tickers(start=start, limit=limit)
        except Exception as exc:
            self._logger.warning(f"Failed to query update tickers: {exc}")
            return []

    def update_ticker_count(self) -> int:
        """Return count of tickers already ingested into the data warehouse.

        Returns:
            Count of ingested tickers
        """
        try:
            return self._repo.count_update_tickers()
        except Exception as exc:
            self._logger.warning(f"Failed to count update tickers: {exc}")
            return 0

    def get_filtered_tickers(
        self,
        *,
        exchanges: list[str],
        sectors: list[str],
        industries: list[str],
        countries: list[str],
        limit: int = 0,
    ) -> list[str]:
        """Return ticker symbols filtered by the given dimension lists.

        Filter semantics: OR within a dimension, AND across dimensions.
        An empty list for a dimension means no filter on that dimension.
        All four lists empty returns the full universe.

        Uses a three-tier fallback: fmp_market_screener → company_profile join → all stock_list.
        """
        try:
            return self._repo.get_filtered_tickers(
                exchanges=exchanges,
                sectors=sectors,
                industries=industries,
                countries=countries,
                limit=limit,
            )
        except Exception as exc:
            self._logger.warning(f"Failed to query filtered tickers: {exc}")
            return []

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def today() -> date:
        return UniverseService.now().date()

    @staticmethod
    def run_id() -> str:
        date_part = datetime.now(timezone.utc).strftime("%y%m%d")
        rand_part = uuid.uuid4().hex[:6]
        return f"{date_part}.{rand_part}"

    @property
    def from_date(self) -> str:
        return FROM_DATE

    def last_quarter_end(self, today: typing.Optional[date] = date.today()) -> str:
        if today is None:
            today = date.today()

        month = today.month

        if month <= 3:
            # Last quarter was Q4 of previous year
            return date(today.year - 1, 12, 31).isoformat()
        elif month <= 6:
            return date(today.year, 3, 31).isoformat()
        elif month <= 9:
            return date(today.year, 6, 30).isoformat()
        else:
            return date(today.year, 9, 30).isoformat()

    def next_market_day(self, today: typing.Optional[date] = date.today()) -> str:
        start = pd.Timestamp(today)
        holidays = USFederalHolidayCalendar().holidays(start=start, end=start + pd.Timedelta(days=365))
        cbd = CustomBusinessDay(holidays=holidays)
        return (start + cbd).date()


if __name__ == "__main__":
    u = UniverseService()
    utickers = u.update_tickers()
    x = 1
