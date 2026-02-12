from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class KeyMetricsTtmDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP key-metrics-ttm (KEY_METRICS_TTM_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#key-metrics-ttm
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    symbol: str = field(default="", metadata={"api": "symbol"})

    # valuation / ratios (TTM)
    market_cap: float | None = field(default=None, metadata={"api": "marketCap"})
    enterprise_value_ttm: float | None = field(default=None, metadata={"api": "enterpriseValueTTM"})
    ev_to_sales_ttm: float | None = field(default=None, metadata={"api": "evToSalesTTM"})
    ev_to_operating_cash_flow_ttm: float | None = field(default=None, metadata={"api": "evToOperatingCashFlowTTM"})
    ev_to_free_cash_flow_ttm: float | None = field(default=None, metadata={"api": "evToFreeCashFlowTTM"})
    ev_to_ebitda_ttm: float | None = field(default=None, metadata={"api": "evToEBITDATTM"})
    net_debt_to_ebitda_ttm: float | None = field(default=None, metadata={"api": "netDebtToEBITDATTM"})
    current_ratio_ttm: float | None = field(default=None, metadata={"api": "currentRatioTTM"})
    income_quality_ttm: float | None = field(default=None, metadata={"api": "incomeQualityTTM"})
    graham_number_ttm: float | None = field(default=None, metadata={"api": "grahamNumberTTM"})
    graham_net_net_ttm: float | None = field(default=None, metadata={"api": "grahamNetNetTTM"})
    tax_burden_ttm: float | None = field(default=None, metadata={"api": "taxBurdenTTM"})
    interest_burden_ttm: float | None = field(default=None, metadata={"api": "interestBurdenTTM"})

    # capital / returns (TTM)
    working_capital_ttm: float | None = field(default=None, metadata={"api": "workingCapitalTTM"})
    invested_capital_ttm: float | None = field(default=None, metadata={"api": "investedCapitalTTM"})
    return_on_assets_ttm: float | None = field(default=None, metadata={"api": "returnOnAssetsTTM"})
    operating_return_on_assets_ttm: float | None = field(default=None, metadata={"api": "operatingReturnOnAssetsTTM"})
    return_on_tangible_assets_ttm: float | None = field(default=None, metadata={"api": "returnOnTangibleAssetsTTM"})
    return_on_equity_ttm: float | None = field(default=None, metadata={"api": "returnOnEquityTTM"})
    return_on_invested_capital_ttm: float | None = field(default=None, metadata={"api": "returnOnInvestedCapitalTTM"})
    return_on_capital_employed_ttm: float | None = field(default=None, metadata={"api": "returnOnCapitalEmployedTTM"})

    # yields / capex (TTM)
    earnings_yield_ttm: float | None = field(default=None, metadata={"api": "earningsYieldTTM"})
    free_cash_flow_yield_ttm: float | None = field(default=None, metadata={"api": "freeCashFlowYieldTTM"})
    capex_to_operating_cash_flow_ttm: float | None = field(default=None, metadata={"api": "capexToOperatingCashFlowTTM"})
    capex_to_depreciation_ttm: float | None = field(default=None, metadata={"api": "capexToDepreciationTTM"})
    capex_to_revenue_ttm: float | None = field(default=None, metadata={"api": "capexToRevenueTTM"})
    sales_general_and_administrative_to_revenue_ttm: float | None = field(
        default=None,
        metadata={"api": "salesGeneralAndAdministrativeToRevenueTTM"},
    )
    # note: vendor uses "Developement" spelling
    research_and_developement_to_revenue_ttm: float | None = field(
        default=None,
        metadata={"api": "researchAndDevelopementToRevenueTTM"},
    )
    stock_based_compensation_to_revenue_ttm: float | None = field(
        default=None,
        metadata={"api": "stockBasedCompensationToRevenueTTM"},
    )
    intangibles_to_total_assets_ttm: float | None = field(
        default=None,
        metadata={"api": "intangiblesToTotalAssetsTTM"},
    )

    # working-capital cycle (TTM)
    average_receivables_ttm: float | None = field(default=None, metadata={"api": "averageReceivablesTTM"})
    average_payables_ttm: float | None = field(default=None, metadata={"api": "averagePayablesTTM"})
    average_inventory_ttm: float | None = field(default=None, metadata={"api": "averageInventoryTTM"})
    days_of_sales_outstanding_ttm: float | None = field(default=None, metadata={"api": "daysOfSalesOutstandingTTM"})
    days_of_payables_outstanding_ttm: float | None = field(default=None, metadata={"api": "daysOfPayablesOutstandingTTM"})
    days_of_inventory_outstanding_ttm: float | None = field(default=None, metadata={"api": "daysOfInventoryOutstandingTTM"})
    operating_cycle_ttm: float | None = field(default=None, metadata={"api": "operatingCycleTTM"})
    cash_conversion_cycle_ttm: float | None = field(default=None, metadata={"api": "cashConversionCycleTTM"})

    # cash flow / value (TTM)
    free_cash_flow_to_equity_ttm: float | None = field(default=None, metadata={"api": "freeCashFlowToEquityTTM"})
    free_cash_flow_to_firm_ttm: float | None = field(default=None, metadata={"api": "freeCashFlowToFirmTTM"})
    tangible_asset_value_ttm: float | None = field(default=None, metadata={"api": "tangibleAssetValueTTM"})
    net_current_asset_value_ttm: float | None = field(default=None, metadata={"api": "netCurrentAssetValueTTM"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "KeyMetricsTtmDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # No vendor date field in this payload; contract requires fallback to date.min
        return date.min
