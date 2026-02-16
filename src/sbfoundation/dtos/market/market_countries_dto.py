from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketCountriesDTO(BronzeToSilverDTO):
    """DTO for FMP available-countries endpoint (list[str] normalized to list[dict])."""

    KEY_COLS = ["value"]

    value: str = field(default="", metadata={"api": "value"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, Any], ticker: typing.Optional[str] = None) -> "MarketCountriesDTO":
        return cls.build_from_row(row)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
