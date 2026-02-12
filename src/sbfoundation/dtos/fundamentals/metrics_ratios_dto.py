from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class MetricsRatiosDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP metrics-ratios (METRICS_RATIOS_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#metrics-ratios
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    symbol: str = field(default="", metadata={"api": "symbol"})
    date: str | None = field(default=None, metadata={"api": "date"})
    fiscal_year: str = field(default="", metadata={"api": "fiscalYear"})
    period: str = field(default="", metadata={"api": "period"})
    reported_currency: str = field(default="", metadata={"api": "reportedCurrency"})

    gross_profit_margin: float | None = field(default=None, metadata={"api": "grossProfitMargin"})
    ebit_margin: float | None = field(default=None, metadata={"api": "ebitMargin"})
    ebitda_margin: float | None = field(default=None, metadata={"api": "ebitdaMargin"})
    operating_profit_margin: float | None = field(default=None, metadata={"api": "operatingProfitMargin"})
    pretax_profit_margin: float | None = field(default=None, metadata={"api": "pretaxProfitMargin"})
    continuous_operations_profit_margin: float | None = field(
        default=None,
        metadata={"api": "continuousOperationsProfitMargin"},
    )
    net_profit_margin: float | None = field(default=None, metadata={"api": "netProfitMargin"})
    bottom_line_profit_margin: float | None = field(default=None, metadata={"api": "bottomLineProfitMargin"})

    receivables_turnover: float | None = field(default=None, metadata={"api": "receivablesTurnover"})
    payables_turnover: float | None = field(default=None, metadata={"api": "payablesTurnover"})
    inventory_turnover: float | None = field(default=None, metadata={"api": "inventoryTurnover"})
    fixed_asset_turnover: float | None = field(default=None, metadata={"api": "fixedAssetTurnover"})
    asset_turnover: float | None = field(default=None, metadata={"api": "assetTurnover"})

    current_ratio: float | None = field(default=None, metadata={"api": "currentRatio"})
    quick_ratio: float | None = field(default=None, metadata={"api": "quickRatio"})
    solvency_ratio: float | None = field(default=None, metadata={"api": "solvencyRatio"})
    cash_ratio: float | None = field(default=None, metadata={"api": "cashRatio"})

    price_to_earnings_ratio: float | None = field(default=None, metadata={"api": "priceToEarningsRatio"})
    price_to_earnings_growth_ratio: float | None = field(default=None, metadata={"api": "priceToEarningsGrowthRatio"})
    forward_price_to_earnings_growth_ratio: float | None = field(
        default=None,
        metadata={"api": "forwardPriceToEarningsGrowthRatio"},
    )
    price_to_book_ratio: float | None = field(default=None, metadata={"api": "priceToBookRatio"})
    price_to_sales_ratio: float | None = field(default=None, metadata={"api": "priceToSalesRatio"})
    price_to_free_cash_flow_ratio: float | None = field(default=None, metadata={"api": "priceToFreeCashFlowRatio"})
    price_to_operating_cash_flow_ratio: float | None = field(
        default=None,
        metadata={"api": "priceToOperatingCashFlowRatio"},
    )

    debt_to_assets_ratio: float | None = field(default=None, metadata={"api": "debtToAssetsRatio"})
    debt_to_equity_ratio: float | None = field(default=None, metadata={"api": "debtToEquityRatio"})
    debt_to_capital_ratio: float | None = field(default=None, metadata={"api": "debtToCapitalRatio"})
    long_term_debt_to_capital_ratio: float | None = field(
        default=None,
        metadata={"api": "longTermDebtToCapitalRatio"},
    )
    financial_leverage_ratio: float | None = field(default=None, metadata={"api": "financialLeverageRatio"})

    working_capital_turnover_ratio: float | None = field(default=None, metadata={"api": "workingCapitalTurnoverRatio"})
    operating_cash_flow_ratio: float | None = field(default=None, metadata={"api": "operatingCashFlowRatio"})
    operating_cash_flow_sales_ratio: float | None = field(
        default=None,
        metadata={"api": "operatingCashFlowSalesRatio"},
    )
    free_cash_flow_operating_cash_flow_ratio: float | None = field(
        default=None,
        metadata={"api": "freeCashFlowOperatingCashFlowRatio"},
    )

    debt_service_coverage_ratio: float | None = field(default=None, metadata={"api": "debtServiceCoverageRatio"})
    interest_coverage_ratio: float | None = field(default=None, metadata={"api": "interestCoverageRatio"})
    short_term_operating_cash_flow_coverage_ratio: float | None = field(
        default=None,
        metadata={"api": "shortTermOperatingCashFlowCoverageRatio"},
    )
    operating_cash_flow_coverage_ratio: float | None = field(
        default=None,
        metadata={"api": "operatingCashFlowCoverageRatio"},
    )
    capital_expenditure_coverage_ratio: float | None = field(
        default=None,
        metadata={"api": "capitalExpenditureCoverageRatio"},
    )
    dividend_paid_and_capex_coverage_ratio: float | None = field(
        default=None,
        metadata={"api": "dividendPaidAndCapexCoverageRatio"},
    )

    dividend_payout_ratio: float | None = field(default=None, metadata={"api": "dividendPayoutRatio"})
    dividend_yield: float | None = field(default=None, metadata={"api": "dividendYield"})
    dividend_yield_percentage: float | None = field(default=None, metadata={"api": "dividendYieldPercentage"})

    revenue_per_share: float | None = field(default=None, metadata={"api": "revenuePerShare"})
    net_income_per_share: float | None = field(default=None, metadata={"api": "netIncomePerShare"})
    interest_debt_per_share: float | None = field(default=None, metadata={"api": "interestDebtPerShare"})
    cash_per_share: float | None = field(default=None, metadata={"api": "cashPerShare"})
    book_value_per_share: float | None = field(default=None, metadata={"api": "bookValuePerShare"})
    tangible_book_value_per_share: float | None = field(default=None, metadata={"api": "tangibleBookValuePerShare"})
    shareholders_equity_per_share: float | None = field(default=None, metadata={"api": "shareholdersEquityPerShare"})
    operating_cash_flow_per_share: float | None = field(default=None, metadata={"api": "operatingCashFlowPerShare"})
    capex_per_share: float | None = field(default=None, metadata={"api": "capexPerShare"})
    free_cash_flow_per_share: float | None = field(default=None, metadata={"api": "freeCashFlowPerShare"})

    net_income_per_ebt: float | None = field(default=None, metadata={"api": "netIncomePerEBT"})
    ebt_per_ebit: float | None = field(default=None, metadata={"api": "ebtPerEbit"})

    price_to_fair_value: float | None = field(default=None, metadata={"api": "priceToFairValue"})
    debt_to_market_cap: float | None = field(default=None, metadata={"api": "debtToMarketCap"})
    effective_tax_rate: float | None = field(default=None, metadata={"api": "effectiveTaxRate"})
    enterprise_value_multiple: float | None = field(default=None, metadata={"api": "enterpriseValueMultiple"})

    @classmethod
    def from_row(
        cls,
        row: typing.Mapping[str, typing.Any],
        ticker: str | None = None,
    ) -> "MetricsRatiosDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
