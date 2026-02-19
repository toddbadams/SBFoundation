from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class IncomeStatementDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/income-statement (INCOME_STATEMENT_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#income-statement
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    date: str | None = field(default=None, metadata={"api": "date"})
    reported_currency: str = field(default="", metadata={"api": "reportedCurrency"})
    cik: str = field(default="", metadata={"api": "cik"})
    filing_date: str | None = field(default=None, metadata={"api": "filingDate"})
    accepted_date: str = field(default="", metadata={"api": "acceptedDate"})
    fiscal_year: str = field(default="", metadata={"api": "fiscalYear"})
    period: str = field(default="", metadata={"api": "period"})

    # numerics
    revenue: float | None = field(default=None, metadata={"api": "revenue"})
    cost_of_revenue: float | None = field(default=None, metadata={"api": "costOfRevenue"})
    gross_profit: float | None = field(default=None, metadata={"api": "grossProfit"})
    research_and_development_expenses: float | None = field(default=None, metadata={"api": "researchAndDevelopmentExpenses"})
    general_and_administrative_expenses: float | None = field(default=None, metadata={"api": "generalAndAdministrativeExpenses"})
    selling_and_marketing_expenses: float | None = field(default=None, metadata={"api": "sellingAndMarketingExpenses"})
    selling_general_and_administrative_expenses: float | None = field(
        default=None,
        metadata={"api": "sellingGeneralAndAdministrativeExpenses"},
    )
    other_expenses: float | None = field(default=None, metadata={"api": "otherExpenses"})
    operating_expenses: float | None = field(default=None, metadata={"api": "operatingExpenses"})
    cost_and_expenses: float | None = field(default=None, metadata={"api": "costAndExpenses"})
    net_interest_income: float | None = field(default=None, metadata={"api": "netInterestIncome"})
    interest_income: float | None = field(default=None, metadata={"api": "interestIncome"})
    interest_expense: float | None = field(default=None, metadata={"api": "interestExpense"})
    depreciation_and_amortization: float | None = field(default=None, metadata={"api": "depreciationAndAmortization"})
    ebitda: float | None = field(default=None, metadata={"api": "ebitda"})
    ebit: float | None = field(default=None, metadata={"api": "ebit"})
    non_operating_income_excluding_interest: float | None = field(
        default=None,
        metadata={"api": "nonOperatingIncomeExcludingInterest"},
    )
    operating_income: float | None = field(default=None, metadata={"api": "operatingIncome"})
    total_other_income_expenses_net: float | None = field(default=None, metadata={"api": "totalOtherIncomeExpensesNet"})
    income_before_tax: float | None = field(default=None, metadata={"api": "incomeBeforeTax"})
    income_tax_expense: float | None = field(default=None, metadata={"api": "incomeTaxExpense"})
    net_income_from_continuing_operations: float | None = field(
        default=None,
        metadata={"api": "netIncomeFromContinuingOperations"},
    )
    net_income_from_discontinued_operations: float | None = field(
        default=None,
        metadata={"api": "netIncomeFromDiscontinuedOperations"},
    )
    other_adjustments_to_net_income: float | None = field(default=None, metadata={"api": "otherAdjustmentsToNetIncome"})
    net_income: float | None = field(default=None, metadata={"api": "netIncome"})
    net_income_deductions: float | None = field(default=None, metadata={"api": "netIncomeDeductions"})
    bottom_line_net_income: float | None = field(default=None, metadata={"api": "bottomLineNetIncome"})
    eps: float | None = field(default=None, metadata={"api": "eps"})
    eps_diluted: float | None = field(default=None, metadata={"api": "epsDiluted"})
    weighted_average_shs_out: float | None = field(default=None, metadata={"api": "weightedAverageShsOut"})
    weighted_average_shs_out_dil: float | None = field(default=None, metadata={"api": "weightedAverageShsOutDil"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "IncomeStatementDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
