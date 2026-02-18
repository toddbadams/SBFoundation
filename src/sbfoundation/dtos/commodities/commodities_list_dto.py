from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CommoditiesListDTO(BronzeToSilverDTO):
    """
    DTO for FMP commodities list data (commodity instrument discovery).

    API docs: https://site.financialmodelingprep.com/developer/docs#Commoditiescurrency-list
    """

    KEY_COLS = ["symbol"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    name: str | None = field(default=None, metadata={"api": "name"})
    currency: str | None = field(default=None, metadata={"api": "currency"})
    exchange: str | None = field(default=None, metadata={"api": "exchange"})
    trade_month: str | None = field(default=None, metadata={"api": "tradeMonth"})

    @property
    def key_date(self) -> date:
        return date.min  # Snapshot endpoint, no time-series date

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CommoditiesListDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
