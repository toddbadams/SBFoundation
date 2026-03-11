from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class KeyMetricsBulkDTO(BronzeToSilverDTO):
    """DTO for FMP bulk key metrics (quarterly and annual).

    Covers pre-computed ratios from /key-metrics-bulk: ROIC, invested capital,
    capital efficiency, valuation, and working-capital metrics.
    """

    KEY_COLS = ["symbol", "period", "calendar_year"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    date: date | None = field(default=None, metadata={"api": "date"})
    period: str = field(default="", metadata={"api": "period"})
    calendar_year: int = field(default=0, metadata={"api": "fiscalYear"})
    roic: float | None = field(default=None, metadata={"api": "returnOnInvestedCapital"})
    invested_capital: float | None = field(default=None, metadata={"api": "investedCapital"})
    revenue_per_employee: float | None = field(default=None, metadata={"api": "revenuePerEmployee"})
    capex_to_ocf: float | None = field(default=None, metadata={"api": "capexToOperatingCashFlow"})
    ev_to_ebitda: float | None = field(default=None, metadata={"api": "enterpriseValueOverEBITDA"})
    debt_to_equity: float | None = field(default=None, metadata={"api": "debtToEquity"})
    asset_turnover: float | None = field(default=None, metadata={"api": "assetTurnover"})
    days_sales_outstanding: float | None = field(default=None, metadata={"api": "daysSalesOutstanding"})
    days_payables_outstanding: float | None = field(default=None, metadata={"api": "daysPayablesOutstanding"})
    days_inventory: float | None = field(default=None, metadata={"api": "daysOfInventoryOnHand"})
    receivables_turnover: float | None = field(default=None, metadata={"api": "receivablesTurnover"})

    @property
    def key_date(self) -> date:
        return self.date if self.date else date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "KeyMetricsBulkDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
