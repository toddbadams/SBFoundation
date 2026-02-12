from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanyDelistedDTO(BronzeToSilverDTO):
    """
    DTO for FMP delisted companies data.

    API docs: https://site.financialmodelingprep.com/developer/docs#delisted-companies
    """

    KEY_COLS = ["ticker", "delisted_date"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})
    symbol: str = field(default="", metadata={"api": "symbol"})

    # company info
    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    exchange: str | None = field(default=None, metadata={"api": "exchange"})

    # dates
    ipo_date: date | None = field(default=None, metadata={"api": "ipoDate"})
    delisted_date: date | None = field(default=None, metadata={"api": "delistedDate"})

    @property
    def key_date(self) -> date:
        return self.delisted_date or date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanyDelistedDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
