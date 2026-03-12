from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class RatiosBulkDTO(BronzeToSilverDTO):
    """DTO for FMP bulk ratios (annual only).

    Covers pre-computed profitability, efficiency, and leverage ratios
    from /ratios-bulk.
    """

    KEY_COLS = ["symbol", "calendar_year"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    date: date | None = field(default=None, metadata={"api": "date"})
    period: str = field(default="", metadata={"api": "period"})
    calendar_year: int = field(default=0, metadata={"api": "fiscalYear"})
    gross_profit_margin: float | None = field(default=None, metadata={"api": "grossProfitMargin"})
    operating_profit_margin: float | None = field(default=None, metadata={"api": "operatingProfitMargin"})
    net_profit_margin: float | None = field(default=None, metadata={"api": "netProfitMargin"})
    effective_tax_rate: float | None = field(default=None, metadata={"api": "effectiveTaxRate"})
    debt_ratio: float | None = field(default=None, metadata={"api": "debtToAssetsRatio"})
    interest_coverage: float | None = field(default=None, metadata={"api": "interestCoverageRatio"})

    @property
    def key_date(self) -> date:
        return self.date if self.date else date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "RatiosBulkDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
