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
    - The canonical list of tradeable instruments
    - Filtering by instrument type, exchange, sector, etc.
    - Time/date utilities for orchestration

    The service provides two ticker retrieval modes:
    - update_tickers: Returns tickers already ingested into the data warehouse (from ops)
    - new_tickers: Returns tickers from instrument dimensions not yet ingested
    """

    def __init__(self, logger: SBLogger | None = None, repo: UniverseRepo | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._repo = repo or UniverseRepo(logger=self._logger)
        self._owns_repo = repo is None

    def close(self) -> None:
        if self._owns_repo:
            self._repo.close()

    def update_tickers(self, start: int = 0, limit: int = 50, instrument_type: str | None = None, is_active: bool = True) -> list[str]:
        """Return tickers already ingested into the data warehouse.

        Queries ops.file_ingestions for distinct tickers that have been
        successfully promoted to silver.

        Args:
            start: Starting offset
            limit: Maximum number of symbols to return
            instrument_type: Filter by type (applied via silver.instrument join)
            is_active: Only return active instruments (default True)

        Returns:
            List of instrument symbols already in the data warehouse
        """
        if limit <= 0:
            return []

        try:
            return self._repo.get_update_tickers(
                start=start,
                limit=limit,
                instrument_type=instrument_type,
                is_active=is_active,
            )
        except Exception as exc:
            self._logger.warning(f"Failed to query update tickers: {exc}")
            return []

    def new_tickers(self, start: int = 0, limit: int = 50, instrument_type: str | None = None, is_active: bool = True) -> list[str]:
        """Return tickers from instrument dimensions not yet ingested.

        Queries gold.dim_instrument for instruments that have no corresponding
        entries in ops.file_ingestions (new instruments to process).

        Args:
            start: Starting offset
            limit: Maximum number of symbols to return
            instrument_type: Filter by type ('equity', 'etf', 'index', 'crypto', 'forex')
            is_active: Only return active instruments (default True)

        Returns:
            List of new instrument symbols to ingest
        """
        if limit <= 0:
            return []

        try:
            return self._repo.get_new_tickers(
                start=start,
                limit=limit,
                instrument_type=instrument_type,
                is_active=is_active,
            )
        except Exception as exc:
            self._logger.warning(f"Failed to query new tickers: {exc}")
            return []

    def update_ticker_count(self, instrument_type: str | None = None) -> int:
        """Return count of tickers already ingested into the data warehouse.

        Args:
            instrument_type: Optional filter by type

        Returns:
            Count of ingested tickers
        """
        try:
            return self._repo.count_update_tickers(instrument_type=instrument_type)
        except Exception as exc:
            self._logger.warning(f"Failed to count update tickers: {exc}")
            return 0

    def new_ticker_count(self, instrument_type: str | None = None) -> int:
        """Return count of new tickers from instrument dimensions not yet ingested.

        Args:
            instrument_type: Optional filter by type

        Returns:
            Count of new tickers
        """
        try:
            return self._repo.count_new_tickers(instrument_type=instrument_type)
        except Exception as exc:
            self._logger.warning(f"Failed to count new tickers: {exc}")
            return 0

    def get_instrument(self, symbol: str) -> dict | None:
        """Retrieve instrument details by symbol.

        Args:
            symbol: The instrument symbol

        Returns:
            Instrument details as dict, or None if not found
        """
        try:
            return self._repo.get_instrument(symbol)
        except Exception:
            return None

    def get_instruments_by_type(self, instrument_type: str, limit: int = 1000, ticker_mode: str = "update") -> list[str]:
        """Get all symbols of a specific instrument type.

        Args:
            instrument_type: The type to filter by
            limit: Maximum number to return
            ticker_mode: 'update' for already-ingested, 'new' for not-yet-ingested

        Returns:
            List of symbols
        """
        if ticker_mode == "new":
            return self.new_tickers(start=0, limit=limit, instrument_type=instrument_type)
        return self.update_tickers(start=0, limit=limit, instrument_type=instrument_type)

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
    utickers = u.update_tickers(instrument_type=INSTRUMENT_TYPE_EQUITY)
    ntickers = u.new_tickers(instrument_type=INSTRUMENT_TYPE_EQUITY)
    x = 1
