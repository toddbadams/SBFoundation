from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class TreasuryRatesDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/treasury-rates.

    API docs: https://site.financialmodelingprep.com/developer/docs#treasury-rates
    """

    KEY_COLS = ["date"]

    date: str | None = field(default=None, metadata={"api": "date"})
    month1: float | None = field(default=None, metadata={"api": "month1"})
    month2: float | None = field(default=None, metadata={"api": "month2"})
    month3: float | None = field(default=None, metadata={"api": "month3"})
    month6: float | None = field(default=None, metadata={"api": "month6"})
    year1: float | None = field(default=None, metadata={"api": "year1"})
    year2: float | None = field(default=None, metadata={"api": "year2"})
    year3: float | None = field(default=None, metadata={"api": "year3"})
    year5: float | None = field(default=None, metadata={"api": "year5"})
    year7: float | None = field(default=None, metadata={"api": "year7"})
    year10: float | None = field(default=None, metadata={"api": "year10"})
    year20: float | None = field(default=None, metadata={"api": "year20"})
    year30: float | None = field(default=None, metadata={"api": "year30"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "TreasuryRatesDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        d = {"date": self.date}
        return self.d(d, "date") or date.min
