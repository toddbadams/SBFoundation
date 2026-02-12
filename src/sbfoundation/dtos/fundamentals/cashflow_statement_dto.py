from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass(slots=True, kw_only=True, order=True)
class CashflowStatementDTO(BronzeToSilverDTO):
    """
    Silver DTO for FMP /stable/cashflow-statement (CASHFLOW_STATEMENT_DATASET).

    One payload row -> one DTO row.
    Pure row-mapper; no ingestion/persistence logic.

    API docs: https://site.financialmodelingprep.com/developer/docs#cashflow-statement
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

    # cashflow line items
    net_income: float | None = field(default=None, metadata={"api": "netIncome"})
    depreciation_and_amortization: float | None = field(default=None, metadata={"api": "depreciationAndAmortization"})
    deferred_income_tax: float | None = field(default=None, metadata={"api": "deferredIncomeTax"})
    stock_based_compensation: float | None = field(default=None, metadata={"api": "stockBasedCompensation"})
    change_in_working_capital: float | None = field(default=None, metadata={"api": "changeInWorkingCapital"})
    accounts_receivables: float | None = field(default=None, metadata={"api": "accountsReceivables"})
    inventory: float | None = field(default=None, metadata={"api": "inventory"})
    accounts_payables: float | None = field(default=None, metadata={"api": "accountsPayables"})
    other_working_capital: float | None = field(default=None, metadata={"api": "otherWorkingCapital"})
    other_non_cash_items: float | None = field(default=None, metadata={"api": "otherNonCashItems"})
    net_cash_provided_by_operating_activities: float | None = field(
        default=None,
        metadata={"api": "netCashProvidedByOperatingActivities"},
    )

    investments_in_property_plant_and_equipment: float | None = field(
        default=None,
        metadata={"api": "investmentsInPropertyPlantAndEquipment"},
    )
    acquisitions_net: float | None = field(default=None, metadata={"api": "acquisitionsNet"})
    purchases_of_investments: float | None = field(default=None, metadata={"api": "purchasesOfInvestments"})
    sales_maturities_of_investments: float | None = field(default=None, metadata={"api": "salesMaturitiesOfInvestments"})
    other_investing_activities: float | None = field(default=None, metadata={"api": "otherInvestingActivities"})
    net_cash_provided_by_investing_activities: float | None = field(
        default=None,
        metadata={"api": "netCashProvidedByInvestingActivities"},
    )

    net_debt_issuance: float | None = field(default=None, metadata={"api": "netDebtIssuance"})
    long_term_net_debt_issuance: float | None = field(default=None, metadata={"api": "longTermNetDebtIssuance"})
    short_term_net_debt_issuance: float | None = field(default=None, metadata={"api": "shortTermNetDebtIssuance"})
    net_stock_issuance: float | None = field(default=None, metadata={"api": "netStockIssuance"})
    net_common_stock_issuance: float | None = field(default=None, metadata={"api": "netCommonStockIssuance"})
    common_stock_issuance: float | None = field(default=None, metadata={"api": "commonStockIssuance"})
    common_stock_repurchased: float | None = field(default=None, metadata={"api": "commonStockRepurchased"})
    net_preferred_stock_issuance: float | None = field(default=None, metadata={"api": "netPreferredStockIssuance"})
    net_dividends_paid: float | None = field(default=None, metadata={"api": "netDividendsPaid"})
    common_dividends_paid: float | None = field(default=None, metadata={"api": "commonDividendsPaid"})
    preferred_dividends_paid: float | None = field(default=None, metadata={"api": "preferredDividendsPaid"})
    other_financing_activities: float | None = field(default=None, metadata={"api": "otherFinancingActivities"})
    net_cash_provided_by_financing_activities: float | None = field(
        default=None,
        metadata={"api": "netCashProvidedByFinancingActivities"},
    )

    effect_of_forex_changes_on_cash: float | None = field(default=None, metadata={"api": "effectOfForexChangesOnCash"})
    net_change_in_cash: float | None = field(default=None, metadata={"api": "netChangeInCash"})
    cash_at_end_of_period: float | None = field(default=None, metadata={"api": "cashAtEndOfPeriod"})
    cash_at_beginning_of_period: float | None = field(default=None, metadata={"api": "cashAtBeginningOfPeriod"})

    # rollups
    operating_cash_flow: float | None = field(default=None, metadata={"api": "operatingCashFlow"})
    capital_expenditure: float | None = field(default=None, metadata={"api": "capitalExpenditure"})
    free_cash_flow: float | None = field(default=None, metadata={"api": "freeCashFlow"})
    income_taxes_paid: float | None = field(default=None, metadata={"api": "incomeTaxesPaid"})
    interest_paid: float | None = field(default=None, metadata={"api": "interestPaid"})

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: str | None = None) -> "CashflowStatementDTO":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()

    @property
    def key_date(self) -> date:
        # key_date derived from vendor date field (or date.min)
        d = {"date": self.date}
        return self.d(d, "date") or date.min
