from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class ExponentialMovingAverageDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/technical-indicators/ema.

    API docs: https://site.financialmodelingprep.com/developer/docs#exponential-moving-average
    """

    KEY_COLS = ["ticker"]

    ticker: str = field(default="_none_", metadata={"api": "symbol"})
    date: str | None = field(default=None, metadata={"api": "date"})
    open: float | None = field(default=None, metadata={"api": "open"})
    high: float | None = field(default=None, metadata={"api": "high"})
    low: float | None = field(default=None, metadata={"api": "low"})
    close: float | None = field(default=None, metadata={"api": "close"})
    volume: int | None = field(default=None, metadata={"api": "volume"})
    ema: float | None = field(default=None, metadata={"api": "ema"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "ExponentialMovingAverageDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        d = {"date": self.date}
        return self.d(d, "date") or date.min
