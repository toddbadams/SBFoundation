from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketHoursDTO(BronzeToSilverDTO):
    """DTO for FMP all-exchange-market-hours endpoint.

    as_of_date is not returned by the API — it is injected at ingestion time
    (set to date.today() by default) to give this snapshot dataset a stable key.
    """

    KEY_COLS = ["exchange", "as_of_date"]

    exchange: str = field(default="", metadata={"api": "exchange"})
    name: str = field(default="", metadata={"api": "name"})
    opening_hour: str = field(default="", metadata={"api": "openingHour"})
    closing_hour: str = field(default="", metadata={"api": "closingHour"})
    timezone: str = field(default="", metadata={"api": "timezone"})
    is_market_open: bool = field(default=False, metadata={"api": "isMarketOpen"})
    opening_additional: str | None = field(default=None, metadata={"api": "openingAdditional"})
    closing_additional: str | None = field(default=None, metadata={"api": "closingAdditional"})
    as_of_date: _date = field(default_factory=_date.today)

    @property
    def key_date(self) -> _date:
        return self.as_of_date

    @classmethod
    def from_row(cls, row: typing.Mapping[str, Any], ticker: typing.Optional[str] = None) -> "MarketHoursDTO":
        return cls.build_from_row(row)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
