from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketRiskPremiumDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/market-risk-premium.

    API docs: https://site.financialmodelingprep.com/developer/docs#market-risk-premium
    """

    KEY_COLS = ["ticker"]

    ticker: str = field(default="_none_", metadata={"api": "ticker"})
    country: str = field(default="", metadata={"api": "country"})
    continent: str = field(default="", metadata={"api": "continent"})
    country_risk_premium: float | None = field(default=None, metadata={"api": "countryRiskPremium"})
    total_equity_risk_premium: float | None = field(default=None, metadata={"api": "totalEquityRiskPremium"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "MarketRiskPremiumDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        return date.min
