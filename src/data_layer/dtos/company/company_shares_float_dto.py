from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanySharesFloatDTO(BronzeToSilverDTO):
    """
    DTO for FMP shares float data.

    API docs: https://site.financialmodelingprep.com/developer/docs#all-shares-float
    """

    # % of shares that are freely tradable (often ~0-100)
    free_float: float | None = field(default=None, metadata={"api": "freeFloat"})

    # Count of shares available to trade
    float_shares: int | None = field(default=None, metadata={"api": "floatShares"})

    # Total shares issued
    outstanding_shares: int | None = field(default=None, metadata={"api": "outstandingShares"})

    @property
    def key_date(self) -> date:
        # This endpoint is typically a current snapshot and does not reliably include a date.
        # Use a stable sentinel for partitioning/sorting.
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanySharesFloatDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
