from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class ETFHoldingsDTO(BronzeToSilverDTO):
    """
    DTO for FMP ETF holdings data (relationship data, not instrument creation).

    This endpoint is used to create relationships between ETF instruments and
    their held instruments. It should NEVER be used to create new instruments.

    API docs: https://site.financialmodelingprep.com/developer/docs#etf-holdings
    """

    KEY_COLS = ["ticker", "asset", "as_of_date"]

    ticker: str = field(default="_none_", metadata={"api": "symbol"})
    asset: str = field(default="_none_", metadata={"api": "asset"})
    name: str | None = field(default=None, metadata={"api": "name"})
    shares_number: int | None = field(default=None, metadata={"api": "sharesNumber"})
    weight_percentage: float | None = field(default=None, metadata={"api": "weightPercentage"})
    market_value: float | None = field(default=None, metadata={"api": "marketValue"})
    as_of_date: date | None = field(default=None, metadata={"api": "updated"})

    @property
    def key_date(self) -> date:
        return self.as_of_date or date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "ETFHoldingsDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
