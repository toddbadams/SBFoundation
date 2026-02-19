from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanyPeersDTO(BronzeToSilverDTO):
    """
    DTO for FMP stock peers data.

    API docs: https://site.financialmodelingprep.com/developer/docs#peers
    """

    peer: str = field(metadata={"api": "symbol"})
    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    price: float | None = field(default=None, metadata={"api": "price"})
    mkt_cap: int | None = field(default=None, metadata={"api": "mktCap"})  # NOTE: payload uses "mktCap" (not "marketCap")

    @property
    def msg(self) -> str:
        name = self.company_name or "unknown"
        return f"peer={self.peer} | name={name}"

    @property
    def key_date(self) -> date:
        # Peers payload has no natural date; use a stable sentinel for partitioning/sorting.
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanyPeersDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
