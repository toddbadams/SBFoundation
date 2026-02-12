from dataclasses import dataclass
import typing


from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.settings import *


@dataclass(slots=True, kw_only=True, order=True)
class SilverInjestItem(BronzeToSilverDTO):

    domain: str  # the domain such as company, economics, fundamentals, technicals
    source: str  # the data source such as FMP, AV, BIS, FRED, Alpaca, Schwab
    dataset: str  # the internal dataset name such as company_profile, economic-indicators, etc.
    discriminator: str | None = None  # an optional discriminator to build deterministic filenames, partitions to avoid collisions
    ticker: str  # the stock symbol, otherwise None
    date: str  # ISO 8601 date representing the data date, as given by the date key
    table_name: str  # The silver table name
    dto_type: str  # The DTO class type
    status: str  # passed, failed, passed-gold (when moved to gold layer)
    error: str = None  # error description

    @property
    def msg(self) -> str:
        return f"domain={self.domain} | source={self.source} | dataset={self.dataset} | discriminator={self.discriminator}"

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "SilverInjestItem":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()
