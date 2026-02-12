from dataclasses import dataclass
import typing


from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.settings import *


@dataclass(slots=True, kw_only=True, order=True)
class BronzeInjestItem(BronzeToSilverDTO):
    KEY_COLS = ["filename"]

    domain: str  # the domain such as company, economics, fundamentals, technicals
    source: str  # the data source such as FMP, AV, BIS, FRED, Alpaca, Schwab
    dataset: str  # the internal dataset name such as company_profile, economic-indicators, etc.
    discriminator: str | None = None  # an optional discriminator to build deterministic filenames, partitions to avoid collisions
    ticker: str  # the stock symbol, otherwise None
    from_date: str  # ISO 8601 date representing the earliest data date, as given by the date key
    to_date: str  # ISO 8601 date representing the latest data date, as given by the date key
    filename: str  # A fully qualified bronze layer filename for the result
    status: str  # passed, failed, too-soon, passed-silver (when moved to silver layer)
    error: str = None  # error description

    @property
    def msg(self) -> str:
        return f"domain={self.domain} | source={self.source} | dataset={self.dataset} | discriminator={self.discriminator}"

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "BronzeInjestItem":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()
