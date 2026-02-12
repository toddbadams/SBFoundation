from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class KeyMetricsDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP key-metrics (KEY_METRICS_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#key-metrics
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

    # valuation / ratios
    market_cap: float | None = field(default=None, metadata={"api": "marketCap"})
    enterprise_value: float | None = field(default=None, metadata={"api": "enterpriseValue"})
    ev_to_sales: float | None = field(default=None, metadata={"api": "evToSales"})
    ev_to_operating_cash_flow: float | None = field(default=None, metadata={"api": "evToOperatingCashFlow"})
    ev_to_free_cash_flow: float | None = field(default=None, metadata={"api": "evToFreeCashFlow"})
    ev_to_ebitda: float | None = field(default=None, metadata={"api": "evToEBITDA"})
    net_debt_to_ebitda: float | None = field(default=None, metadata={"api": "netDebtToEBITDA"})
    current_ratio: float | None = field(default=None, metadata={"api": "currentRatio"})
    income_quality: float | None = field(default=None, metadata={"api": "incomeQuality"})
    graham_number: float | None = field(default=None, metadata={"api": "grahamNumber"})
    graham_net_net: float | None = field(default=None, metadata={"api": "grahamNetNet"})
    tax_burden: float | None = field(default=None, metadata={"api": "taxBurden"})
    interest_burden: float | None = field(default=None, metadata={"api": "interestBurden"})

    # capital / returns
    working_capital: float | None = field(default=None, metadata={"api": "workingCapital"})
    invested_capital: float | None = field(default=None, metadata={"api": "investedCapital"})
    return_on_assets: float | None = field(default=None, metadata={"api": "returnOnAssets"})
    operating_return_on_assets: float | None = field(default=None, metadata={"api": "operatingReturnOnAssets"})
    return_on_tangible_assets: float | None = field(default=None, metadata={"api": "returnOnTangibleAssets"})
    return_on_equity: float | None = field(default=None, metadata={"api": "returnOnEquity"})
    return_on_invested_capital: float | None = field(default=None, metadata={"api": "returnOnInvestedCapital"})
    return_on_capital_employed: float | None = field(default=None, metadata={"api": "returnOnCapitalEmployed"})

    # yields / capex
    earnings_yield: float | None = field(default=None, metadata={"api": "earningsYield"})
    free_cash_flow_yield: float | None = field(default=None, metadata={"api": "freeCashFlowYield"})
    capex_to_operating_cash_flow: float | None = field(default=None, metadata={"api": "capexToOperatingCashFlow"})
    capex_to_depreciation: float | None = field(default=None, metadata={"api": "capexToDepreciation"})
    capex_to_revenue: float | None = field(default=None, metadata={"api": "capexToRevenue"})
    sales_general_and_administrative_to_revenue: float | None = field(
        default=None,
        metadata={"api": "salesGeneralAndAdministrativeToRevenue"},
    )
    research_and_developement_to_revenue: float | None = field(
        default=None,
        metadata={"api": "researchAndDevelopementToRevenue"},
    )
    stock_based_compensation_to_revenue: float | None = field(
        default=None,
        metadata={"api": "stockBasedCompensationToRevenue"},
    )
    intangibles_to_total_assets: float | None = field(default=None, metadata={"api": "intangiblesToTotalAssets"})

    # working-capital cycle
    average_receivables: float | None = field(default=None, metadata={"api": "averageReceivables"})
    average_payables: float | None = field(default=None, metadata={"api": "averagePayables"})
    average_inventory: float | None = field(default=None, metadata={"api": "averageInventory"})
    days_of_sales_outstanding: float | None = field(default=None, metadata={"api": "daysOfSalesOutstanding"})
    days_of_payables_outstanding: float | None = field(default=None, metadata={"api": "daysOfPayablesOutstanding"})
    days_of_inventory_outstanding: float | None = field(default=None, metadata={"api": "daysOfInventoryOutstanding"})
    operating_cycle: float | None = field(default=None, metadata={"api": "operatingCycle"})
    cash_conversion_cycle: float | None = field(default=None, metadata={"api": "cashConversionCycle"})

    # cash flow / value
    free_cash_flow_to_equity: float | None = field(default=None, metadata={"api": "freeCashFlowToEquity"})
    free_cash_flow_to_firm: float | None = field(default=None, metadata={"api": "freeCashFlowToFirm"})
    tangible_asset_value: float | None = field(default=None, metadata={"api": "tangibleAssetValue"})
    net_current_asset_value: float | None = field(default=None, metadata={"api": "netCurrentAssetValue"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "KeyMetricsDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
