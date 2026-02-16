from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketExchangesDTO(BronzeToSilverDTO):
    """DTO for FMP available-exchanges endpoint."""

    KEY_COLS = ["exchange"]

    exchange: str = field(default="", metadata={"api": "exchange"})
    name: str = field(default="", metadata={"api": "name"})
    country: str | None = field(default=None, metadata={"api": "country"})
    currency: str | None = field(default=None, metadata={"api": "currency"})
    timezone: str | None = field(default=None, metadata={"api": "timezone"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, Any], ticker: typing.Optional[str] = None) -> "MarketExchangesDTO":
        return cls.build_from_row(row)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
