from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class BalanceSheetStatementGrowthDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP balance-sheet-statement-growth (BALANCE_SHEET_STATEMENT_GROWTH_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#balance-sheet-statement-growth
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

    growth_cash_and_cash_equivalents: float | None = field(default=None, metadata={"api": "growthCashAndCashEquivalents"})
    growth_short_term_investments: float | None = field(default=None, metadata={"api": "growthShortTermInvestments"})
    growth_cash_and_short_term_investments: float | None = field(
        default=None,
        metadata={"api": "growthCashAndShortTermInvestments"},
    )
    growth_net_receivables: float | None = field(default=None, metadata={"api": "growthNetReceivables"})
    growth_inventory: float | None = field(default=None, metadata={"api": "growthInventory"})
    growth_other_current_assets: float | None = field(default=None, metadata={"api": "growthOtherCurrentAssets"})
    growth_total_current_assets: float | None = field(default=None, metadata={"api": "growthTotalCurrentAssets"})
    growth_property_plant_equipment_net: float | None = field(
        default=None,
        metadata={"api": "growthPropertyPlantEquipmentNet"},
    )
    growth_goodwill: float | None = field(default=None, metadata={"api": "growthGoodwill"})
    growth_intangible_assets: float | None = field(default=None, metadata={"api": "growthIntangibleAssets"})
    growth_goodwill_and_intangible_assets: float | None = field(
        default=None,
        metadata={"api": "growthGoodwillAndIntangibleAssets"},
    )
    growth_long_term_investments: float | None = field(default=None, metadata={"api": "growthLongTermInvestments"})
    growth_tax_assets: float | None = field(default=None, metadata={"api": "growthTaxAssets"})
    growth_other_non_current_assets: float | None = field(default=None, metadata={"api": "growthOtherNonCurrentAssets"})
    growth_total_non_current_assets: float | None = field(default=None, metadata={"api": "growthTotalNonCurrentAssets"})
    growth_other_assets: float | None = field(default=None, metadata={"api": "growthOtherAssets"})
    growth_total_assets: float | None = field(default=None, metadata={"api": "growthTotalAssets"})

    growth_account_payables: float | None = field(default=None, metadata={"api": "growthAccountPayables"})
    growth_short_term_debt: float | None = field(default=None, metadata={"api": "growthShortTermDebt"})
    growth_tax_payables: float | None = field(default=None, metadata={"api": "growthTaxPayables"})
    growth_deferred_revenue: float | None = field(default=None, metadata={"api": "growthDeferredRevenue"})
    growth_other_current_liabilities: float | None = field(default=None, metadata={"api": "growthOtherCurrentLiabilities"})
    growth_total_current_liabilities: float | None = field(default=None, metadata={"api": "growthTotalCurrentLiabilities"})
    growth_long_term_debt: float | None = field(default=None, metadata={"api": "growthLongTermDebt"})
    growth_deferred_revenue_non_current: float | None = field(
        default=None,
        metadata={"api": "growthDeferredRevenueNonCurrent"},
    )
    growth_deferred_tax_liabilities_non_current: float | None = field(
        default=None,
        metadata={"api": "growthDeferredTaxLiabilitiesNonCurrent"},
    )
    growth_other_non_current_liabilities: float | None = field(
        default=None,
        metadata={"api": "growthOtherNonCurrentLiabilities"},
    )
    growth_total_non_current_liabilities: float | None = field(
        default=None,
        metadata={"api": "growthTotalNonCurrentLiabilities"},
    )
    growth_other_liabilities: float | None = field(default=None, metadata={"api": "growthOtherLiabilities"})
    growth_total_liabilities: float | None = field(default=None, metadata={"api": "growthTotalLiabilities"})

    growth_preferred_stock: float | None = field(default=None, metadata={"api": "growthPreferredStock"})
    growth_common_stock: float | None = field(default=None, metadata={"api": "growthCommonStock"})
    growth_retained_earnings: float | None = field(default=None, metadata={"api": "growthRetainedEarnings"})
    growth_accumulated_other_comprehensive_income_loss: float | None = field(
        default=None,
        metadata={"api": "growthAccumulatedOtherComprehensiveIncomeLoss"},
    )
    # note: payload key has casing/typo "growthOthertotalStockholdersEquity"
    growth_other_total_stockholders_equity: float | None = field(
        default=None,
        metadata={"api": "growthOthertotalStockholdersEquity"},
    )
    growth_total_stockholders_equity: float | None = field(default=None, metadata={"api": "growthTotalStockholdersEquity"})
    growth_minority_interest: float | None = field(default=None, metadata={"api": "growthMinorityInterest"})
    growth_total_equity: float | None = field(default=None, metadata={"api": "growthTotalEquity"})
    growth_total_liabilities_and_stockholders_equity: float | None = field(
        default=None,
        metadata={"api": "growthTotalLiabilitiesAndStockholdersEquity"},
    )

    growth_total_investments: float | None = field(default=None, metadata={"api": "growthTotalInvestments"})
    growth_total_debt: float | None = field(default=None, metadata={"api": "growthTotalDebt"})
    growth_net_debt: float | None = field(default=None, metadata={"api": "growthNetDebt"})

    growth_accounts_receivables: float | None = field(default=None, metadata={"api": "growthAccountsReceivables"})
    growth_other_receivables: float | None = field(default=None, metadata={"api": "growthOtherReceivables"})
    growth_prepaids: float | None = field(default=None, metadata={"api": "growthPrepaids"})
    growth_total_payables: float | None = field(default=None, metadata={"api": "growthTotalPayables"})
    growth_other_payables: float | None = field(default=None, metadata={"api": "growthOtherPayables"})
    growth_accrued_expenses: float | None = field(default=None, metadata={"api": "growthAccruedExpenses"})
    growth_capital_lease_obligations_current: float | None = field(
        default=None,
        metadata={"api": "growthCapitalLeaseObligationsCurrent"},
    )
    growth_additional_paid_in_capital: float | None = field(
        default=None,
        metadata={"api": "growthAdditionalPaidInCapital"},
    )
    growth_treasury_stock: float | None = field(default=None, metadata={"api": "growthTreasuryStock"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "BalanceSheetStatementGrowthDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
