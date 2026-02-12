from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from typing import Any
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class RevenueSegmentationDTO(BronzeToSilverDTO):
    """
    DTO for FMP revenue segmentation data (product and geographic).

    API docs:
    - Product: https://site.financialmodelingprep.com/developer/docs#revenue-product-segmentation
    - Geographic: https://site.financialmodelingprep.com/developer/docs#revenue-geographic-segementation
    """

    KEY_COLS = ["ticker", "date"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})
    symbol: str = field(default="", metadata={"api": "symbol"})

    # period
    date: date_type | None = field(default=None, metadata={"api": "date"})

    # segmentation data
    segment: str | None = field(default=None, metadata={"api": "segment"})
    revenue: float | None = field(default=None, metadata={"api": "revenue"})

    @property
    def key_date(self) -> date_type:
        return self.date or date_type.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "RevenueSegmentationDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
