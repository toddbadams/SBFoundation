from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class BalanceSheetStatementDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/balance-sheet-statement (BALANCE_SHEET_STATEMENT_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#balance-sheet-statement
    """

    KEY_COLS = ["ticker"]

    # identifiers
    ticker: str = field(default="_none_", metadata={"api": "symbol"})

    # vendor fields (snake_case)
    date: str | None = field(default=None, metadata={"api": "date"})
    symbol: str = field(default="", metadata={"api": "symbol"})
    reported_currency: str = field(default="", metadata={"api": "reportedCurrency"})
    cik: str = field(default="", metadata={"api": "cik"})
    filing_date: str | None = field(default=None, metadata={"api": "filingDate"})
    accepted_date: str = field(default="", metadata={"api": "acceptedDate"})
    fiscal_year: str = field(default="", metadata={"api": "fiscalYear"})
    period: str = field(default="", metadata={"api": "period"})

    # assets
    cash_and_cash_equivalents: float | None = field(default=None, metadata={"api": "cashAndCashEquivalents"})
    short_term_investments: float | None = field(default=None, metadata={"api": "shortTermInvestments"})
    cash_and_short_term_investments: float | None = field(
        default=None,
        metadata={"api": "cashAndShortTermInvestments"},
    )
    net_receivables: float | None = field(default=None, metadata={"api": "netReceivables"})
    accounts_receivables: float | None = field(default=None, metadata={"api": "accountsReceivables"})
    other_receivables: float | None = field(default=None, metadata={"api": "otherReceivables"})
    inventory: float | None = field(default=None, metadata={"api": "inventory"})
    prepaids: float | None = field(default=None, metadata={"api": "prepaids"})
    other_current_assets: float | None = field(default=None, metadata={"api": "otherCurrentAssets"})
    total_current_assets: float | None = field(default=None, metadata={"api": "totalCurrentAssets"})
    property_plant_equipment_net: float | None = field(default=None, metadata={"api": "propertyPlantEquipmentNet"})
    goodwill: float | None = field(default=None, metadata={"api": "goodwill"})
    intangible_assets: float | None = field(default=None, metadata={"api": "intangibleAssets"})
    goodwill_and_intangible_assets: float | None = field(
        default=None,
        metadata={"api": "goodwillAndIntangibleAssets"},
    )
    long_term_investments: float | None = field(default=None, metadata={"api": "longTermInvestments"})
    tax_assets: float | None = field(default=None, metadata={"api": "taxAssets"})
    other_non_current_assets: float | None = field(default=None, metadata={"api": "otherNonCurrentAssets"})
    total_non_current_assets: float | None = field(default=None, metadata={"api": "totalNonCurrentAssets"})
    other_assets: float | None = field(default=None, metadata={"api": "otherAssets"})
    total_assets: float | None = field(default=None, metadata={"api": "totalAssets"})

    # liabilities
    total_payables: float | None = field(default=None, metadata={"api": "totalPayables"})
    account_payables: float | None = field(default=None, metadata={"api": "accountPayables"})
    other_payables: float | None = field(default=None, metadata={"api": "otherPayables"})
    accrued_expenses: float | None = field(default=None, metadata={"api": "accruedExpenses"})
    short_term_debt: float | None = field(default=None, metadata={"api": "shortTermDebt"})
    capital_lease_obligations_current: float | None = field(
        default=None,
        metadata={"api": "capitalLeaseObligationsCurrent"},
    )
    tax_payables: float | None = field(default=None, metadata={"api": "taxPayables"})
    deferred_revenue: float | None = field(default=None, metadata={"api": "deferredRevenue"})
    other_current_liabilities: float | None = field(default=None, metadata={"api": "otherCurrentLiabilities"})
    total_current_liabilities: float | None = field(default=None, metadata={"api": "totalCurrentLiabilities"})
    long_term_debt: float | None = field(default=None, metadata={"api": "longTermDebt"})
    deferred_revenue_non_current: float | None = field(
        default=None,
        metadata={"api": "deferredRevenueNonCurrent"},
    )
    deferred_tax_liabilities_non_current: float | None = field(
        default=None,
        metadata={"api": "deferredTaxLiabilitiesNonCurrent"},
    )
    other_non_current_liabilities: float | None = field(default=None, metadata={"api": "otherNonCurrentLiabilities"})
    total_non_current_liabilities: float | None = field(default=None, metadata={"api": "totalNonCurrentLiabilities"})
    other_liabilities: float | None = field(default=None, metadata={"api": "otherLiabilities"})
    capital_lease_obligations: float | None = field(default=None, metadata={"api": "capitalLeaseObligations"})
    total_liabilities: float | None = field(default=None, metadata={"api": "totalLiabilities"})

    # equity / other
    treasury_stock: float | None = field(default=None, metadata={"api": "treasuryStock"})
    preferred_stock: float | None = field(default=None, metadata={"api": "preferredStock"})
    common_stock: float | None = field(default=None, metadata={"api": "commonStock"})
    retained_earnings: float | None = field(default=None, metadata={"api": "retainedEarnings"})
    additional_paid_in_capital: float | None = field(default=None, metadata={"api": "additionalPaidInCapital"})
    accumulated_other_comprehensive_income_loss: float | None = field(
        default=None,
        metadata={"api": "accumulatedOtherComprehensiveIncomeLoss"},
    )
    other_total_stockholders_equity: float | None = field(
        default=None,
        metadata={"api": "otherTotalStockholdersEquity"},
    )
    total_stockholders_equity: float | None = field(default=None, metadata={"api": "totalStockholdersEquity"})
    total_equity: float | None = field(default=None, metadata={"api": "totalEquity"})
    minority_interest: float | None = field(default=None, metadata={"api": "minorityInterest"})
    total_liabilities_and_total_equity: float | None = field(
        default=None,
        metadata={"api": "totalLiabilitiesAndTotalEquity"},
    )

    # rollups
    total_investments: float | None = field(default=None, metadata={"api": "totalInvestments"})
    total_debt: float | None = field(default=None, metadata={"api": "totalDebt"})
    net_debt: float | None = field(default=None, metadata={"api": "netDebt"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "BalanceSheetStatementDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
