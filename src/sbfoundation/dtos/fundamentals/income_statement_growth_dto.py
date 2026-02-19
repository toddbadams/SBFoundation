from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class IncomeStatementGrowthDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP income-statement-growth (INCOME_STATEMENT_GROWTH_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#income-statement-growth
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    date: str | None = field(default=None, metadata={"api": "date"})
    fiscal_year: str = field(default="", metadata={"api": "fiscalYear"})
    period: str = field(default="", metadata={"api": "period"})
    reported_currency: str = field(default="", metadata={"api": "reportedCurrency"})

    # growth metrics
    growth_revenue: float | None = field(default=None, metadata={"api": "growthRevenue"})
    growth_cost_of_revenue: float | None = field(default=None, metadata={"api": "growthCostOfRevenue"})
    growth_gross_profit: float | None = field(default=None, metadata={"api": "growthGrossProfit"})
    growth_gross_profit_ratio: float | None = field(default=None, metadata={"api": "growthGrossProfitRatio"})
    growth_research_and_development_expenses: float | None = field(
        default=None,
        metadata={"api": "growthResearchAndDevelopmentExpenses"},
    )
    growth_general_and_administrative_expenses: float | None = field(
        default=None,
        metadata={"api": "growthGeneralAndAdministrativeExpenses"},
    )
    growth_selling_and_marketing_expenses: float | None = field(
        default=None,
        metadata={"api": "growthSellingAndMarketingExpenses"},
    )
    growth_other_expenses: float | None = field(default=None, metadata={"api": "growthOtherExpenses"})
    growth_operating_expenses: float | None = field(default=None, metadata={"api": "growthOperatingExpenses"})
    growth_cost_and_expenses: float | None = field(default=None, metadata={"api": "growthCostAndExpenses"})
    growth_interest_income: float | None = field(default=None, metadata={"api": "growthInterestIncome"})
    growth_interest_expense: float | None = field(default=None, metadata={"api": "growthInterestExpense"})
    growth_depreciation_and_amortization: float | None = field(
        default=None,
        metadata={"api": "growthDepreciationAndAmortization"},
    )
    growth_ebitda: float | None = field(default=None, metadata={"api": "growthEBITDA"})
    growth_operating_income: float | None = field(default=None, metadata={"api": "growthOperatingIncome"})
    growth_income_before_tax: float | None = field(default=None, metadata={"api": "growthIncomeBeforeTax"})
    growth_income_tax_expense: float | None = field(default=None, metadata={"api": "growthIncomeTaxExpense"})
    growth_net_income: float | None = field(default=None, metadata={"api": "growthNetIncome"})
    growth_eps: float | None = field(default=None, metadata={"api": "growthEPS"})
    growth_eps_diluted: float | None = field(default=None, metadata={"api": "growthEPSDiluted"})
    growth_weighted_average_shs_out: float | None = field(
        default=None,
        metadata={"api": "growthWeightedAverageShsOut"},
    )
    growth_weighted_average_shs_out_dil: float | None = field(
        default=None,
        metadata={"api": "growthWeightedAverageShsOutDil"},
    )
    growth_ebit: float | None = field(default=None, metadata={"api": "growthEBIT"})
    growth_non_operating_income_excluding_interest: float | None = field(
        default=None,
        metadata={"api": "growthNonOperatingIncomeExcludingInterest"},
    )
    growth_net_interest_income: float | None = field(default=None, metadata={"api": "growthNetInterestIncome"})
    growth_total_other_income_expenses_net: float | None = field(
        default=None,
        metadata={"api": "growthTotalOtherIncomeExpensesNet"},
    )
    growth_net_income_from_continuing_operations: float | None = field(
        default=None,
        metadata={"api": "growthNetIncomeFromContinuingOperations"},
    )
    growth_other_adjustments_to_net_income: float | None = field(
        default=None,
        metadata={"api": "growthOtherAdjustmentsToNetIncome"},
    )
    growth_net_income_deductions: float | None = field(default=None, metadata={"api": "growthNetIncomeDeductions"})

    @classmethod
    def from_row(
        cls,
        row: typing.Mapping[str, typing.Any],
        ticker: str | None = None,
    ) -> "IncomeStatementGrowthDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
