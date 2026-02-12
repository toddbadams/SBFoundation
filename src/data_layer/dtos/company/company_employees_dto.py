from dataclasses import dataclass, field
from datetime import date
from typing import Any
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CompanyEmployeesDTO(BronzeToSilverDTO):
    """
    DTO for FMP historical employee count data.

    API docs: https://site.financialmodelingprep.com/developer/docs#historical-employee-count
    """

    cik: str | None = field(default=None, metadata={"api": "cik"})
    acceptance_time: str | None = field(default=None, metadata={"api": "acceptanceTime"})  # NOTE: payload format is "YYYY-MM-DD HH:MM:SS"
    period_of_report: date | None = field(default=None, metadata={"api": "periodOfReport"})

    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    form_type: str | None = field(default=None, metadata={"api": "formType"})
    filing_date: date | None = field(default=None, metadata={"api": "filingDate"})

    employee_count: int | None = field(default=None, metadata={"api": "employeeCount"})
    source: str | None = field(default=None, metadata={"api": "source"})

    @property
    def key_date(self) -> date:
        # Best business key date here is the period the employee count applies to.
        # If it's missing, fall back to filing date, else a stable sentinel.
        return self.period_of_report or self.filing_date or date.min

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "CompanyEmployeesDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, Any]:
        return self.build_to_dict()
