from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketHolidaysDTO(BronzeToSilverDTO):
    """DTO for FMP holidays-by-exchange endpoint.

    ticker is used to pass the exchange code (ticker_scope: per_ticker).
    """

    KEY_COLS = ["exchange", "date", "holiday"]

    exchange: str = field(default="", metadata={"api": "exchange"})
    date: _date | None = field(default=None, metadata={"api": "date"})
    holiday: str = field(default="", metadata={"api": "name"})

    @property
    def key_date(self) -> _date:
        return self.date or _date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, Any], ticker: typing.Optional[str] = None) -> "MarketHolidaysDTO":
        dto = cls.build_from_row(row)
        # exchange comes from the ticker (passed in as the exchange code)
        if ticker and not dto.exchange:
            dto.exchange = ticker
        return dto

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
