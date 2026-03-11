from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class FredDgs10DTO(BronzeToSilverDTO):
    """DTO for FRED DGS10 — 10-year constant maturity Treasury yield.

    Used as the risk-free rate (Rf) in WACC cost-of-equity calculations.
    FRED returns "." for dates with no published value; those map to None.
    """

    KEY_COLS = ["date"]

    date: date | None = field(default=None, metadata={"api": "date"})
    rate: float | None = field(default=None, metadata={"api": "value"})

    @property
    def key_date(self) -> date:
        return self.date if self.date else date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "FredDgs10DTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
