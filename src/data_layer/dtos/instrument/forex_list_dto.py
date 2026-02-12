from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class ForexListDTO(BronzeToSilverDTO):
    """
    DTO for FMP forex list data (forex instrument discovery).

    Each FX pair is modeled as one instrument with base_currency and quote_currency.
    Do not split currencies into standalone instruments.

    API docs: https://site.financialmodelingprep.com/developer/docs#forex-list
    """

    KEY_COLS = ["symbol"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    name: str | None = field(default=None, metadata={"api": "name"})
    currency: str | None = field(default=None, metadata={"api": "currency"})
    stock_exchange: str | None = field(default=None, metadata={"api": "stockExchange"})
    exchange_short_name: str | None = field(default=None, metadata={"api": "exchangeShortName"})

    # Derived fields for currency pair decomposition
    base_currency: str | None = field(default=None, metadata={"api": "_base_currency_"})
    quote_currency: str | None = field(default=None, metadata={"api": "_quote_currency_"})

    # Override ticker since this is a global list, not per-ticker
    ticker: str = field(default="", metadata={"api": "_ticker_"})

    def __post_init__(self) -> None:
        # Parse symbol like "EURUSD" into base="EUR", quote="USD"
        if self.symbol and len(self.symbol) == 6 and self.symbol.isalpha():
            object.__setattr__(self, "base_currency", self.symbol[:3])
            object.__setattr__(self, "quote_currency", self.symbol[3:])

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "ForexListDTO":
        dto = cls.build_from_row(row, ticker_override=ticker)
        # Trigger post_init logic for base/quote currency parsing
        dto.__post_init__()
        return dto

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
