from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class FxListDTO(BronzeToSilverDTO):
    """
    DTO for FMP forex list data (forex pair discovery).

    API docs: https://site.financialmodelingprep.com/developer/docs#forex-list
    """

    KEY_COLS = ["symbol"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    from_currency: str | None = field(default=None, metadata={"api": "fromCurrency"})
    from_name: str | None = field(default=None, metadata={"api": "fromName"})
    to_currency: str | None = field(default=None, metadata={"api": "toCurrency"})
    to_name: str | None = field(default=None, metadata={"api": "toName"})

    @property
    def key_date(self) -> date:
        return date.min  # Snapshot endpoint, no time-series date

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "FxListDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
