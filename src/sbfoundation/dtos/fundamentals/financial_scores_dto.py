from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class FinancialScoresDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP financial-scores (FINANCIAL_SCORES_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#financial-scores
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    reported_currency: str = field(default="", metadata={"api": "reportedCurrency"})

    # scores / components
    altman_z_score: float | None = field(default=None, metadata={"api": "altmanZScore"})
    piotroski_score: float | None = field(default=None, metadata={"api": "piotroskiScore"})

    working_capital: float | None = field(default=None, metadata={"api": "workingCapital"})
    total_assets: float | None = field(default=None, metadata={"api": "totalAssets"})
    retained_earnings: float | None = field(default=None, metadata={"api": "retainedEarnings"})
    ebit: float | None = field(default=None, metadata={"api": "ebit"})
    market_cap: float | None = field(default=None, metadata={"api": "marketCap"})
    total_liabilities: float | None = field(default=None, metadata={"api": "totalLiabilities"})
    revenue: float | None = field(default=None, metadata={"api": "revenue"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "FinancialScoresDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # No vendor date field in this payload; contract requires fallback to date.min
        return date.min
