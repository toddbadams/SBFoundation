from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MarketRiskPremiumDTO(BronzeToSilverDTO):
    """DTO for FMP Market Risk Premium — country-level equity risk premiums.

    Sourced from Damodaran's annual country risk premium dataset via FMP.
    Used in WACC cost-of-equity: Ke = Rf + β × (total_equity_risk_premium / 100).
    One row per country, snapshot updated monthly.
    """

    KEY_COLS = ["country"]

    country: str = field(default="", metadata={"api": "country"})
    continent: str | None = field(default=None, metadata={"api": "continent"})
    total_equity_risk_premium: float | None = field(default=None, metadata={"api": "totalEquityRiskPremium"})
    country_risk_premium: float | None = field(default=None, metadata={"api": "countryRiskPremium"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "MarketRiskPremiumDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
