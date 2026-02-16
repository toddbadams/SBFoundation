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
    # FMP may return either changesPercentage or averageChange
    changes_percentage: float | None = field(default=None, metadata={"api": "changesPercentage"})

    @property
    def key_date(self) -> _date:
        return self.date or _date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, Any], ticker: typing.Optional[str] = None) -> "MarketSectorPerformanceDTO":
        dto = cls.build_from_row(row)
        # Fallback alias: some FMP responses use averageChange instead of changesPercentage
        if dto.changes_percentage is None:
            raw = row.get("averageChange") or row.get("average_change")
            if raw is not None:
                try:
                    dto.changes_percentage = float(raw)
                except (TypeError, ValueError):
                    pass
        return dto

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
