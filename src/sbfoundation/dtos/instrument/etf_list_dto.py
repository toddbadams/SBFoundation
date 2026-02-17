from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class ETFListDTO(BronzeToSilverDTO):
    """
    DTO for FMP ETF list data (ETF instrument discovery).

    API docs: https://site.financialmodelingprep.com/developer/docs#etf-list
    """

    KEY_COLS = ["symbol"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    company_name: str | None = field(default=None, metadata={"api": "name"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "ETFListDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
