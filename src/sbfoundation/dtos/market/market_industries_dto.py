from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketIndustriesDTO(BronzeToSilverDTO):
    """DTO for FMP available-industries endpoint (list[str] normalized to list[dict])."""

    KEY_COLS = ["industry"]

    industry: str = field(default="", metadata={"api": "industry"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, Any], ticker: typing.Optional[str] = None) -> "MarketIndustriesDTO":
        return cls.build_from_row(row)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
