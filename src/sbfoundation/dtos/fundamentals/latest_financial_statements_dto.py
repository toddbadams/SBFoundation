from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class LatestFinancialStatementsDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP latest-financial-statements (LATEST_FINANCIALS_DATASET).

    Global endpoint — one request returns the latest financial statement row
    for every company.  ticker is populated from the per-row 'symbol' field.

    API docs: https://site.financialmodelingprep.com/developer/docs#latest-financial-statements
    """

    KEY_COLS = ["date"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    date: date | None = field(default=None, metadata={"api": "date"})
    period: str | None = field(default=None, metadata={"api": "period"})
    filing_date: date | None = field(default=None, metadata={"api": "filingDate"})
    revenue: float | None = field(default=None, metadata={"api": "revenue"})
    net_income: float | None = field(default=None, metadata={"api": "netIncome"})
    eps: float | None = field(default=None, metadata={"api": "eps"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "LatestFinancialStatementsDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        return self.date or date.min


__all__ = ["LatestFinancialStatementsDTO"]
