from dataclasses import dataclass, field
import datetime
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanyMarketCapDTO(BronzeToSilverDTO):
    """
    DTO for FMP historical market cap data.

    API docs: https://site.financialmodelingprep.com/developer/docs#historical-market-cap
    """

    date: datetime.date = field(metadata={"api": "date"})
    market_cap: int | None = field(default=None, metadata={"api": "marketCap"})

    @property
    def key_date(self) -> datetime.date:
        # Natural business key for market cap snapshots
        return self.date

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanyMarketCapDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
