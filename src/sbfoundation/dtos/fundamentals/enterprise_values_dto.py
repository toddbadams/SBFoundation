from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class EnterpriseValuesDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP enterprise-values (ENTERPRISE_VALUES_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#enterprise-values
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    symbol: str = field(default="", metadata={"api": "symbol"})
    date: str | None = field(default=None, metadata={"api": "date"})

    stock_price: float | None = field(default=None, metadata={"api": "stockPrice"})
    number_of_shares: float | None = field(default=None, metadata={"api": "numberOfShares"})
    market_capitalization: float | None = field(default=None, metadata={"api": "marketCapitalization"})
    minus_cash_and_cash_equivalents: float | None = field(default=None, metadata={"api": "minusCashAndCashEquivalents"})
    add_total_debt: float | None = field(default=None, metadata={"api": "addTotalDebt"})
    enterprise_value: float | None = field(default=None, metadata={"api": "enterpriseValue"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "EnterpriseValuesDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
