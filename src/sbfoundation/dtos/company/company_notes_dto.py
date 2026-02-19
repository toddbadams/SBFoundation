from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanyNotesDTO(BronzeToSilverDTO):
    """
    DTO for FMP company notes data (debt/bond issuances).

    Payload: {"cik": "...", "symbol": "AAPL", "title": "1.000% Notes due 2022", "exchange": "NASDAQ"}

    API docs: https://site.financialmodelingprep.com/developer/docs#company-notes
    """

    KEY_COLS = ["ticker", "title"]

    cik: str | None = field(default=None, metadata={"api": "cik"})
    title: str | None = field(default=None, metadata={"api": "title"})
    exchange: str | None = field(default=None, metadata={"api": "exchange"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanyNotesDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
