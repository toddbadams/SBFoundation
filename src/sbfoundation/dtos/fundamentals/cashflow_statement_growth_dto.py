from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CashflowStatementGrowthDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP cashflow-statement-growth (CASHFLOW_STATEMENT_GROWTH_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#cashflow-statement-growth
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

    growth_net_income: float | None = field(default=None, metadata={"api": "growthNetIncome"})
    growth_depreciation_and_amortization: float | None = field(
        default=None,
        metadata={"api": "growthDepreciationAndAmortization"},
    )
    growth_deferred_income_tax: float | None = field(default=None, metadata={"api": "growthDeferredIncomeTax"})
    growth_stock_based_compensation: float | None = field(default=None, metadata={"api": "growthStockBasedCompensation"})
    growth_change_in_working_capital: float | None = field(default=None, metadata={"api": "growthChangeInWorkingCapital"})
    growth_accounts_receivables: float | None = field(default=None, metadata={"api": "growthAccountsReceivables"})
    growth_inventory: float | None = field(default=None, metadata={"api": "growthInventory"})
    growth_accounts_payables: float | None = field(default=None, metadata={"api": "growthAccountsPayables"})
    growth_other_working_capital: float | None = field(default=None, metadata={"api": "growthOtherWorkingCapital"})
    growth_other_non_cash_items: float | None = field(default=None, metadata={"api": "growthOtherNonCashItems"})

    # note: payload keys use "Activites" misspelling in several fields
    growth_net_cash_provided_by_operating_activites: float | None = field(
        default=None,
        metadata={"api": "growthNetCashProvidedByOperatingActivites"},
    )
    growth_investments_in_property_plant_and_equipment: float | None = field(
        default=None,
        metadata={"api": "growthInvestmentsInPropertyPlantAndEquipment"},
    )
    growth_acquisitions_net: float | None = field(default=None, metadata={"api": "growthAcquisitionsNet"})
    growth_purchases_of_investments: float | None = field(default=None, metadata={"api": "growthPurchasesOfInvestments"})
    growth_sales_maturities_of_investments: float | None = field(
        default=None,
        metadata={"api": "growthSalesMaturitiesOfInvestments"},
    )
    growth_other_investing_activites: float | None = field(
        default=None,
        metadata={"api": "growthOtherInvestingActivites"},
    )
    growth_net_cash_used_for_investing_activites: float | None = field(
        default=None,
        metadata={"api": "growthNetCashUsedForInvestingActivites"},
    )

    growth_debt_repayment: float | None = field(default=None, metadata={"api": "growthDebtRepayment"})
    growth_common_stock_issued: float | None = field(default=None, metadata={"api": "growthCommonStockIssued"})
    growth_common_stock_repurchased: float | None = field(default=None, metadata={"api": "growthCommonStockRepurchased"})
    growth_dividends_paid: float | None = field(default=None, metadata={"api": "growthDividendsPaid"})
    growth_other_financing_activites: float | None = field(default=None, metadata={"api": "growthOtherFinancingActivites"})
    growth_net_cash_used_provided_by_financing_activities: float | None = field(
        default=None,
        metadata={"api": "growthNetCashUsedProvidedByFinancingActivities"},
    )

    growth_effect_of_forex_changes_on_cash: float | None = field(
        default=None,
        metadata={"api": "growthEffectOfForexChangesOnCash"},
    )
    growth_net_change_in_cash: float | None = field(default=None, metadata={"api": "growthNetChangeInCash"})
    growth_cash_at_end_of_period: float | None = field(default=None, metadata={"api": "growthCashAtEndOfPeriod"})
    growth_cash_at_beginning_of_period: float | None = field(
        default=None,
        metadata={"api": "growthCashAtBeginningOfPeriod"},
    )

    growth_operating_cash_flow: float | None = field(default=None, metadata={"api": "growthOperatingCashFlow"})
    growth_capital_expenditure: float | None = field(default=None, metadata={"api": "growthCapitalExpenditure"})
    growth_free_cash_flow: float | None = field(default=None, metadata={"api": "growthFreeCashFlow"})

    growth_net_debt_issuance: float | None = field(default=None, metadata={"api": "growthNetDebtIssuance"})
    growth_long_term_net_debt_issuance: float | None = field(default=None, metadata={"api": "growthLongTermNetDebtIssuance"})
    growth_short_term_net_debt_issuance: float | None = field(default=None, metadata={"api": "growthShortTermNetDebtIssuance"})
    growth_net_stock_issuance: float | None = field(default=None, metadata={"api": "growthNetStockIssuance"})
    growth_preferred_dividends_paid: float | None = field(default=None, metadata={"api": "growthPreferredDividendsPaid"})
    growth_income_taxes_paid: float | None = field(default=None, metadata={"api": "growthIncomeTaxesPaid"})
    growth_interest_paid: float | None = field(default=None, metadata={"api": "growthInterestPaid"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "CashflowStatementGrowthDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
