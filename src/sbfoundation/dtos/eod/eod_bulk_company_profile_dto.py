from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class EodBulkCompanyProfileDTO(BronzeToSilverDTO):
    """DTO for FMP bulk company profile data (v4/profile/all)."""

    KEY_COLS = ["symbol"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    exchange: str | None = field(default=None, metadata={"api": "exchange"})
    exchange_short_name: str | None = field(default=None, metadata={"api": "exchangeShortName"})
    sector: str | None = field(default=None, metadata={"api": "sector"})
    industry: str | None = field(default=None, metadata={"api": "industry"})
    country: str | None = field(default=None, metadata={"api": "country"})
    currency: str | None = field(default=None, metadata={"api": "currency"})
    is_etf: bool | None = field(default=None, metadata={"api": "isEtf"})
    is_actively_trading: bool | None = field(default=None, metadata={"api": "isActivelyTrading"})
    market_cap: float | None = field(default=None, metadata={"api": "mktCap"})
    price: float | None = field(default=None, metadata={"api": "price"})
    beta: float | None = field(default=None, metadata={"api": "beta"})
    vol_avg: int | None = field(default=None, metadata={"api": "volAvg"})
    description: str | None = field(default=None, metadata={"api": "description"})
    website: str | None = field(default=None, metadata={"api": "website"})
    ceo: str | None = field(default=None, metadata={"api": "ceo"})
    full_time_employees: int | None = field(default=None, metadata={"api": "fullTimeEmployees"})
    ipo_date: date | None = field(default=None, metadata={"api": "ipoDate"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "EodBulkCompanyProfileDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
