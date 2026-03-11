from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class IncomeStatementBulkDTO(BronzeToSilverDTO):
    """DTO for FMP bulk income statement (quarterly and annual)."""

    KEY_COLS = ["symbol", "period", "calendar_year"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    date: date | None = field(default=None, metadata={"api": "date"})
    period: str = field(default="", metadata={"api": "period"})
    calendar_year: int = field(default=0, metadata={"api": "fiscalYear"})
    reported_currency: str | None = field(default=None, metadata={"api": "reportedCurrency"})
    revenue: float | None = field(default=None, metadata={"api": "revenue"})
    gross_profit: float | None = field(default=None, metadata={"api": "grossProfit"})
    operating_income: float | None = field(default=None, metadata={"api": "operatingIncome"})
    net_income: float | None = field(default=None, metadata={"api": "netIncome"})
    ebitda: float | None = field(default=None, metadata={"api": "ebitda"})
    eps: float | None = field(default=None, metadata={"api": "eps"})
    eps_diluted: float | None = field(default=None, metadata={"api": "epsdiluted"})

    @property
    def key_date(self) -> date:
        return self.date if self.date else date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "IncomeStatementBulkDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
