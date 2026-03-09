from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class EodBulkPriceDTO(BronzeToSilverDTO):
    """DTO for FMP bulk end-of-day price data (v4/batch-request/end-of-day-prices)."""

    KEY_COLS = ["symbol", "date"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    date: date | None = field(default=None, metadata={"api": "date"})
    open: float | None = field(default=None, metadata={"api": "open"})
    high: float | None = field(default=None, metadata={"api": "high"})
    low: float | None = field(default=None, metadata={"api": "low"})
    close: float | None = field(default=None, metadata={"api": "close"})
    adj_close: float | None = field(default=None, metadata={"api": "adjClose"})
    volume: int | None = field(default=None, metadata={"api": "volume"})
    unadjusted_volume: int | None = field(default=None, metadata={"api": "unadjustedVolume"})
    change: float | None = field(default=None, metadata={"api": "change"})
    change_pct: float | None = field(default=None, metadata={"api": "changePercent"})
    vwap: float | None = field(default=None, metadata={"api": "vwap"})

    @property
    def key_date(self) -> date:
        return self.date if self.date else date.min

    @classmethod
    def from_row(cls, row: Any, ticker: Optional[str] = None) -> "EodBulkPriceDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
