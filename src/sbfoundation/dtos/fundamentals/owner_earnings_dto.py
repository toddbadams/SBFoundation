from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class OwnerEarningsDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP owner-earnings (OWNER_EARNINGS_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#owner-earnings
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    reported_currency: str = field(default="", metadata={"api": "reportedCurrency"})
    fiscal_year: str = field(default="", metadata={"api": "fiscalYear"})
    period: str = field(default="", metadata={"api": "period"})
    date: str | None = field(default=None, metadata={"api": "date"})

    average_ppe: float | None = field(default=None, metadata={"api": "averagePPE"})
    maintenance_capex: float | None = field(default=None, metadata={"api": "maintenanceCapex"})
    owners_earnings: float | None = field(default=None, metadata={"api": "ownersEarnings"})
    growth_capex: float | None = field(default=None, metadata={"api": "growthCapex"})
    owners_earnings_per_share: float | None = field(default=None, metadata={"api": "ownersEarningsPerShare"})

    @classmethod
    def from_row(
        cls,
        row: typing.Mapping[str, typing.Any],
        ticker: str | None = None,
    ) -> "OwnerEarningsDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
