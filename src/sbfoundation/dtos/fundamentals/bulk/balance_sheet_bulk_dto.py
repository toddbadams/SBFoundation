from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class BalanceSheetBulkDTO(BronzeToSilverDTO):
    """DTO for FMP bulk balance sheet (quarterly and annual)."""

    KEY_COLS = ["symbol", "period", "calendar_year"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    date: date | None = field(default=None, metadata={"api": "date"})
    period: str = field(default="", metadata={"api": "period"})
    calendar_year: int = field(default=0, metadata={"api": "fiscalYear"})
    reported_currency: str | None = field(default=None, metadata={"api": "reportedCurrency"})
    total_assets: float | None = field(default=None, metadata={"api": "totalAssets"})
    total_current_assets: float | None = field(default=None, metadata={"api": "totalCurrentAssets"})
    total_liabilities: float | None = field(default=None, metadata={"api": "totalLiabilities"})
    total_current_liabilities: float | None = field(default=None, metadata={"api": "totalCurrentLiabilities"})
    total_stockholders_equity: float | None = field(default=None, metadata={"api": "totalStockholdersEquity"})
    cash_and_cash_equivalents: float | None = field(default=None, metadata={"api": "cashAndCashEquivalents"})
    long_term_debt: float | None = field(default=None, metadata={"api": "longTermDebt"})
    total_debt: float | None = field(default=None, metadata={"api": "totalDebt"})
    net_debt: float | None = field(default=None, metadata={"api": "netDebt"})

    @property
    def key_date(self) -> date:
        return self.date if self.date else date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "BalanceSheetBulkDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
