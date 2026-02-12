from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing


from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanyDTO(BronzeToSilverDTO):
    """
    DTO for FMP company profile data.

    API docs: https://site.financialmodelingprep.com/developer/docs#profile-symbol
    """

    # listing
    ticker: str = field(default="_none_", metadata={"api": "symbol"})
    cik: str | None = field(default=None, metadata={"api": "cik"})
    isin: str | None = field(default=None, metadata={"api": "isin"})
    cusip: str | None = field(default=None, metadata={"api": "cusip"})

    exchange: str | None = field(default=None, metadata={"api": "exchange"})
    exchange_full_name: str | None = field(default=None, metadata={"api": "exchangeFullName"})
    currency: str | None = field(default=None, metadata={"api": "currency"})

    # Market snapshot fields
    price: float | None = field(default=None, metadata={"api": "price"})
    market_cap: int | None = field(default=None, metadata={"api": "marketCap"})
    beta: float | None = field(default=None, metadata={"api": "beta"})
    last_dividend: float | None = field(default=None, metadata={"api": "lastDividend"})
    range: str | None = field(default=None, metadata={"api": "range"})
    change: float | None = field(default=None, metadata={"api": "change"})
    change_percentage: float | None = field(default=None, metadata={"api": "changePercentage"})
    volume: int | None = field(default=None, metadata={"api": "volume"})
    average_volume: int | None = field(default=None, metadata={"api": "averageVolume"})

    # Company profile
    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    industry: str | None = field(default=None, metadata={"api": "industry"})
    sector: str | None = field(default=None, metadata={"api": "sector"})
    description: str | None = field(default=None, metadata={"api": "description"})
    website: str | None = field(default=None, metadata={"api": "website"})
    ceo: str | None = field(default=None, metadata={"api": "ceo"})
    country: str | None = field(default=None, metadata={"api": "country"})
    full_time_employees: int | None = field(default=None, metadata={"api": "fullTimeEmployees"})

    # Contact / address
    phone: str | None = field(default=None, metadata={"api": "phone"})
    address: str | None = field(default=None, metadata={"api": "address"})
    city: str | None = field(default=None, metadata={"api": "city"})
    state: str | None = field(default=None, metadata={"api": "state"})
    zip: str | None = field(default=None, metadata={"api": "zip"})

    # Media / flags
    image: str | None = field(default=None, metadata={"api": "image"})
    ipo_date: date | None = field(default=None, metadata={"api": "ipoDate"})
    default_image: bool | None = field(default=None, metadata={"api": "defaultImage"})
    is_etf: bool | None = field(default=None, metadata={"api": "isEtf"})
    is_actively_trading: bool | None = field(default=None, metadata={"api": "isActivelyTrading"})
    is_adr: bool | None = field(default=None, metadata={"api": "isAdr"})
    is_fund: bool | None = field(default=None, metadata={"api": "isFund"})

    @property
    def key_date(self) -> date:
        # Best available "date" in the payload is IPO date; fall back to a stable sentinel.
        return self.ipo_date or date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanyDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
