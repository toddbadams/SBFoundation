from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanyOfficerDTO(BronzeToSilverDTO):
    """
    DTO for FMP company executives data.

    API docs: https://site.financialmodelingprep.com/developer/docs#company-executives
    """

    title: str | None = field(default=None, metadata={"api": "title"})
    name: str | None = field(default=None, metadata={"api": "name"})
    pay: float | None = field(default=None, metadata={"api": "pay"})
    currency_pay: str | None = field(default=None, metadata={"api": "currencyPay"})
    gender: str | None = field(default=None, metadata={"api": "gender"})
    year_born: int | None = field(default=None, metadata={"api": "yearBorn"})
    active: bool | None = field(default=None, metadata={"api": "active"})

    @property
    def key_date(self) -> date:
        # No reliable business date in the payload; use a stable sentinel.
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanyOfficerDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
