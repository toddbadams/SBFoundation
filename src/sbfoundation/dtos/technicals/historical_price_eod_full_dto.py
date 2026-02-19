from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class HistoricalPriceEodFullDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/historical-price-eod/full.

    API docs: https://site.financialmodelingprep.com/developer/docs#historical-price-eod-full
    """

    KEY_COLS = ["ticker"]

    ticker: str = field(default="_none_", metadata={"api": "symbol"})
    date: str | None = field(default=None, metadata={"api": "date"})
    open: float | None = field(default=None, metadata={"api": "open"})
    high: float | None = field(default=None, metadata={"api": "high"})
    low: float | None = field(default=None, metadata={"api": "low"})
    close: float | None = field(default=None, metadata={"api": "close"})
    volume: int | None = field(default=None, metadata={"api": "volume"})
    change: float | None = field(default=None, metadata={"api": "change"})
    change_percent: float | None = field(default=None, metadata={"api": "changePercent"})
    vwap: float | None = field(default=None, metadata={"api": "vwap"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "HistoricalPriceEodFullDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        d = {"date": self.date}
        return self.d(d, "date") or date.min
