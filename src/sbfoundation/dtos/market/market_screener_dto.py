from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketScreenerDTO(BronzeToSilverDTO):
    """
    DTO for FMP company screener data.

    Provides authoritative symbol → exchange / sector / industry / country mapping.
    Run once per country (discriminated by country code).

    API docs: https://site.financialmodelingprep.com/developer/docs#company-screener
    """

    KEY_COLS = ["symbol"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    market_cap: int | None = field(default=None, metadata={"api": "marketCap"})
    sector: str | None = field(default=None, metadata={"api": "sector"})
    industry: str | None = field(default=None, metadata={"api": "industry"})
    beta: float | None = field(default=None, metadata={"api": "beta"})
    price: float | None = field(default=None, metadata={"api": "price"})
    last_annual_dividend: float | None = field(default=None, metadata={"api": "lastAnnualDividend"})
    volume: int | None = field(default=None, metadata={"api": "volume"})
    exchange: str | None = field(default=None, metadata={"api": "exchange"})
    exchange_short_name: str | None = field(default=None, metadata={"api": "exchangeShortName"})
    country: str | None = field(default=None, metadata={"api": "country"})
    is_etf: bool | None = field(default=None, metadata={"api": "isEtf"})
    is_actively_trading: bool | None = field(default=None, metadata={"api": "isActivelyTrading"})
    is_adr: bool | None = field(default=None, metadata={"api": "isAdr"})
    is_fund: bool | None = field(default=None, metadata={"api": "isFund"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "MarketScreenerDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
