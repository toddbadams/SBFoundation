from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CryptocurrencyListDTO(BronzeToSilverDTO):
    """
    DTO for FMP cryptocurrency list data (crypto instrument discovery).

    Note: Treats crypto assets (not trading pairs) as the primary instrument.
    Pairs become relationships.

    API docs: https://site.financialmodelingprep.com/developer/docs#cryptocurrency-list
    """

    KEY_COLS = ["symbol"]

    symbol: str = field(default="_none_", metadata={"api": "symbol"})
    company_name: str | None = field(default=None, metadata={"api": "name"})
    currency: str | None = field(default=None, metadata={"api": "currency"})
    stock_exchange: str | None = field(default=None, metadata={"api": "stockExchange"})
    exchange_short_name: str | None = field(default=None, metadata={"api": "exchangeShortName"})

    @property
    def key_date(self) -> date:
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CryptocurrencyListDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
