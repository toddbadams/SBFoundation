from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanyCompensationDTO(BronzeToSilverDTO):
    """
    DTO for FMP executive compensation data.

    API docs: https://site.financialmodelingprep.com/developer/docs#executive-compensation
    Endpoint: /stable/governance-executive-compensation?symbol=<ticker>
    """

    year: int | None = field(default=None, metadata={"api": "year"})
    name_and_position: str | None = field(default=None, metadata={"api": "nameAndPosition"})
    year_fiscal_year_ending: str | None = field(default=None, metadata={"api": "yearFiscalYearEnding"})
    salary: float | None = field(default=None, metadata={"api": "salary"})
    bonus: float | None = field(default=None, metadata={"api": "bonus"})
    stock_award: float | None = field(default=None, metadata={"api": "stockAward"})
    incentive_plan_compensation: float | None = field(default=None, metadata={"api": "incentivePlanCompensation"})
    all_other_compensation: float | None = field(default=None, metadata={"api": "allOtherCompensation"})
    total: float | None = field(default=None, metadata={"api": "total"})
    url: str | None = field(default=None, metadata={"api": "url"})

    @property
    def key_date(self) -> date:
        if self.year is not None:
            return date(self.year, 12, 31)
        return date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanyCompensationDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
