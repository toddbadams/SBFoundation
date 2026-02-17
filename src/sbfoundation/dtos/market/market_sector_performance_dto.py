from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketSectorPerformanceDTO(BronzeToSilverDTO):
    """DTO for FMP sector-performance-snapshot endpoint."""

    KEY_COLS = ["date", "sector", "exchange"]

    date: _date | None = field(default=None, metadata={"api": "date"})
    sector: str = field(default="", metadata={"api": "sector"})
    exchange: str = field(default="", metadata={"api": "exchange"})
    average_change: float | None = field(default=None, metadata={"api": "averageChange"})

    @property
    def key_date(self) -> _date:
        return self.date or _date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, Any], ticker: typing.Optional[str] = None) -> "MarketSectorPerformanceDTO":
        return cls.build_from_row(row)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
