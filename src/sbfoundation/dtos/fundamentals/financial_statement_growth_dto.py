from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class FinancialStatementGrowthDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP financial-statement-growth (FINANCIAL_STATEMENT_GROWTH_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#financial-statement-growth
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    date: str | None = field(default=None, metadata={"api": "date"})
    fiscal_year: str = field(default="", metadata={"api": "fiscalYear"})
    period: str = field(default="", metadata={"api": "period"})
    reported_currency: str = field(default="", metadata={"api": "reportedCurrency"})

    revenue_growth: float | None = field(default=None, metadata={"api": "revenueGrowth"})
    gross_profit_growth: float | None = field(default=None, metadata={"api": "grossProfitGrowth"})
    ebit_growth: float | None = field(default=None, metadata={"api": "ebitgrowth"})
    operating_income_growth: float | None = field(default=None, metadata={"api": "operatingIncomeGrowth"})
    net_income_growth: float | None = field(default=None, metadata={"api": "netIncomeGrowth"})
    eps_growth: float | None = field(default=None, metadata={"api": "epsgrowth"})
    eps_diluted_growth: float | None = field(default=None, metadata={"api": "epsdilutedGrowth"})
    weighted_average_shares_growth: float | None = field(default=None, metadata={"api": "weightedAverageSharesGrowth"})
    weighted_average_shares_diluted_growth: float | None = field(
        default=None,
        metadata={"api": "weightedAverageSharesDilutedGrowth"},
    )
    dividends_per_share_growth: float | None = field(default=None, metadata={"api": "dividendsPerShareGrowth"})
    operating_cash_flow_growth: float | None = field(default=None, metadata={"api": "operatingCashFlowGrowth"})
    receivables_growth: float | None = field(default=None, metadata={"api": "receivablesGrowth"})
    inventory_growth: float | None = field(default=None, metadata={"api": "inventoryGrowth"})
    asset_growth: float | None = field(default=None, metadata={"api": "assetGrowth"})
    book_value_per_share_growth: float | None = field(default=None, metadata={"api": "bookValueperShareGrowth"})
    debt_growth: float | None = field(default=None, metadata={"api": "debtGrowth"})
    rd_expense_growth: float | None = field(default=None, metadata={"api": "rdexpenseGrowth"})
    sga_expenses_growth: float | None = field(default=None, metadata={"api": "sgaexpensesGrowth"})
    free_cash_flow_growth: float | None = field(default=None, metadata={"api": "freeCashFlowGrowth"})

    ten_y_revenue_growth_per_share: float | None = field(default=None, metadata={"api": "tenYRevenueGrowthPerShare"})
    five_y_revenue_growth_per_share: float | None = field(default=None, metadata={"api": "fiveYRevenueGrowthPerShare"})
    three_y_revenue_growth_per_share: float | None = field(default=None, metadata={"api": "threeYRevenueGrowthPerShare"})

    ten_y_operating_cf_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "tenYOperatingCFGrowthPerShare"},
    )
    five_y_operating_cf_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "fiveYOperatingCFGrowthPerShare"},
    )
    three_y_operating_cf_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "threeYOperatingCFGrowthPerShare"},
    )

    ten_y_net_income_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "tenYNetIncomeGrowthPerShare"},
    )
    five_y_net_income_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "fiveYNetIncomeGrowthPerShare"},
    )
    three_y_net_income_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "threeYNetIncomeGrowthPerShare"},
    )

    ten_y_shareholders_equity_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "tenYShareholdersEquityGrowthPerShare"},
    )
    five_y_shareholders_equity_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "fiveYShareholdersEquityGrowthPerShare"},
    )
    three_y_shareholders_equity_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "threeYShareholdersEquityGrowthPerShare"},
    )

    ten_y_dividend_per_share_growth_per_share: float | None = field(default=None, metadata={"api": "tenYDividendperShareGrowthPerShare"})
    five_y_dividend_per_share_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "fiveYDividendperShareGrowthPerShare"},
    )
    three_y_dividend_per_share_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "threeYDividendperShareGrowthPerShare"},
    )

    ebitda_growth: float | None = field(default=None, metadata={"api": "ebitdaGrowth"})
    growth_capital_expenditure: float | None = field(default=None, metadata={"api": "growthCapitalExpenditure"})

    ten_y_bottom_line_net_income_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "tenYBottomLineNetIncomeGrowthPerShare"},
    )
    five_y_bottom_line_net_income_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "fiveYBottomLineNetIncomeGrowthPerShare"},
    )
    three_y_bottom_line_net_income_growth_per_share: float | None = field(
        default=None,
        metadata={"api": "threeYBottomLineNetIncomeGrowthPerShare"},
    )

    @classmethod
    def from_row(
        cls,
        row: typing.Mapping[str, typing.Any],
        ticker: str | None = None,
    ) -> "FinancialStatementGrowthDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
