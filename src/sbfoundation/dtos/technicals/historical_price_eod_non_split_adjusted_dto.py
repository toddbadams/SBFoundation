from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class HistoricalPriceEodNonSplitAdjustedDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/historical-price-eod/non-split-adjusted.

    API docs: https://site.financialmodelingprep.com/developer/docs#historical-price-eod-non-split-adjusted
    """

    KEY_COLS = ["ticker"]

    ticker: str = field(default="_none_", metadata={"api": "symbol"})
    date: str | None = field(default=None, metadata={"api": "date"})
    adj_open: float | None = field(default=None, metadata={"api": "adjOpen"})
    adj_high: float | None = field(default=None, metadata={"api": "adjHigh"})
    adj_low: float | None = field(default=None, metadata={"api": "adjLow"})
    adj_close: float | None = field(default=None, metadata={"api": "adjClose"})
    volume: int | None = field(default=None, metadata={"api": "volume"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "HistoricalPriceEodNonSplitAdjustedDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        d = {"date": self.date}
        return self.d(d, "date") or date.min
