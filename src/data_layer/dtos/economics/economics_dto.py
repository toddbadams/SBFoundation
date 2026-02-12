from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class EconomicsDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/economic-indicators.

    API docs: https://site.financialmodelingprep.com/developer/docs#economics-indicators
    """

    KEY_COLS = ["ticker"]

    ticker: str = field(default="_none_", metadata={"api": "ticker"})
    name: str = field(default="", metadata={"api": "name"})
    date: str | None = field(default=None, metadata={"api": "date"})
    value: float | None = field(default=None, metadata={"api": "value"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "EconomicsDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    @classmethod
    def from_series_row(cls, row: typing.Any) -> "EconomicsDTO":
        data = row.to_dict() if hasattr(row, "to_dict") else dict(row)
        return cls.from_row(data)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        d = {"date": self.date}
        return self.d(d, "date") or date.min

    @property
    def fiscal_date(self) -> date:
        return self.key_date
