from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CashflowBulkDTO(BronzeToSilverDTO):
    """DTO for FMP bulk cash-flow statement (quarterly and annual)."""

    KEY_COLS = ["symbol", "period", "calendar_year"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    date: date | None = field(default=None, metadata={"api": "date"})
    period: str = field(default="", metadata={"api": "period"})
    calendar_year: int = field(default=0, metadata={"api": "fiscalYear"})
    reported_currency: str | None = field(default=None, metadata={"api": "reportedCurrency"})
    operating_cash_flow: float | None = field(default=None, metadata={"api": "operatingCashFlow"})
    capital_expenditure: float | None = field(default=None, metadata={"api": "capitalExpenditure"})
    free_cash_flow: float | None = field(default=None, metadata={"api": "freeCashFlow"})
    net_income: float | None = field(default=None, metadata={"api": "netIncome"})
    dividends_paid: float | None = field(default=None, metadata={"api": "netDividendsPaid"})

    @property
    def key_date(self) -> date:
        return self.date if self.date else date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "CashflowBulkDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
