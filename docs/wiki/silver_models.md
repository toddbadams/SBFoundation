# Cashflow Model

This document describes the `Cashflow` data model used to ingest cash flow statement data, compute single‑period cash metrics, and derive trailing‑twelve‑month (TTM) aggregates and quality ratios. The model cleanly separates *reported inputs* (raw API fields) from *computed outputs* (formulas), with in‑place methods for validation and TTM derivations.

## Properties

| Human‑readable | Variable | Formula or Source | What it is & why it matters |
|:--------------:|:--------:|-------------------|-----------------------------|
| Ticker         | `ticker` | Raw (API)         | Identifier tying each row to a company. |
| Fiscal date ending | `fiscal_date_ending` | Raw (API) | Reporting period end date; drives ordering and TTM windows. |
| Period | `period` | Raw (API) | Denotes `"annual"` vs `"quarterly"`; impacts TTM logic. |
| Reported currency | `reported_currency` | Raw (API) | Currency code of reported values; normalizes casing. |
| Net income | `net_income` | Raw (API) | Profit after tax; basis for accruals and OCF comparison. |
| Depreciation & amortization | `depreciation_and_amortization` | Raw (API) | Non‑cash add‑back used in OCF and FCF derivations. |
| Δ Inventory | `change_in_inventory` | Raw (API) | Working‑capital delta; included in operating cash flow. |
| Δ Receivables | `change_in_receivables` | Raw (API) | Working‑capital delta; included in operating cash flow. |
| Δ Operating assets | `change_in_operating_assets` | Raw (API) | Working‑capital delta; included in operating cash flow. |
| Δ Operating liabilities | `change_in_operating_liabilities` | Raw (API) | Working‑capital delta; included in operating cash flow. |
| Operating cash flow (reported) | `operating_cashflow_reported` | Raw (API) | Direct OCF from source, used as fallback for computed OCF. |
| Capital expenditures (CapEx) | `capital_expenditures` | Raw (API) | Cash spent on long‑term assets; key to FCF and reinvestment. |
| Investing cash flow | `cash_flow_from_investment` | Raw (API) | Net cash from investing activities (often negative). |
| Dividends paid (common) | `dividend_payout_common_stock` | Raw (API) | Cash distributions to common shareholders. |
| Dividends paid (preferred) | `dividend_payout_preferred_stock` | Raw (API) | Cash distributions to preferred shareholders. |
| Equity repurchases (buybacks) | `proceeds_from_repurchase_of_equity` | Raw (API) | Cash used to repurchase equity (usually negative). |
| Financing cash flow (reported) | `cash_flow_from_financing_reported` | Raw (API) | Net cash from financing activities (source’s aggregate). |
| Δ Cash & equivalents (reported) | `change_in_cash_and_cash_equivalents_raw` | Raw (API) | Bridging line used when provided. |
| Δ FX rate effect | `change_in_exchange_rate` | Raw (API) | Currency translation effect; may explain bridge residuals. |
| Operating cash flow (computed) | `operating_cash_flow` | `net_income + depreciation_and_amortization + Δinventory + Δreceivables + Δoperating_assets + Δoperating_liabilities` (fallback to `operating_cashflow_reported` if core inputs missing) | Cash generated from operations; core quality signal and basis for FCF. |
| Financing cash flow (computed) | `financing_cash_flow` | `dividend_payout_common_stock + dividend_payout_preferred_stock + proceeds_from_repurchase_of_equity` (fallback to `cash_flow_from_financing_reported`) | Net cash returned to/raised from capital providers; informs distributions. |
| Net change in cash | `net_change_in_cash` | `operating_cash_flow + cash_flow_from_investment + financing_cash_flow` | Period cash bridge across sections; consistency check. |
| Δ Cash & equivalents (computed) | `change_in_cash_and_cash_equivalents` | `change_in_cash_and_cash_equivalents_raw` else `net_change_in_cash` | Reported bridge if available; else computed total change. |
| Free cash flow | `free_cashflow` | `operating_cash_flow - capital_expenditures` | Cash available after maintenance/growth CapEx; fuels buybacks/dividends. |
| OCF / Net income | `ocf_to_net_income` | `operating_cash_flow / net_income` | Cash earnings quality; >1 suggests conservative accruals. |
| CapEx reinvestment ratio | `capex_reinvestment_ratio` | `abs(capital_expenditures) / operating_cash_flow` | Share of OCF reinvested; context for growth vs. payout. |
| FCF / OCF | `fcf_to_ocf` | `free_cashflow / operating_cash_flow` | Fraction of OCF left after CapEx; capital intensity gauge. |
| Dividend coverage by OCF | `dividend_coverage_by_ocf` | `operating_cash_flow / (dividends_common + dividends_pref)` | Sustainability of dividend from operations. |
| Buyback coverage by OCF | `buyback_coverage_by_ocf` | `operating_cash_flow / abs(buybacks)` | Headroom to fund repurchases from operations. |
| TTM Net income | `ttm_net_income` | Sum of last 4 quarterly `net_income` | Smoother profitability over 12 months. |
| TTM D&A | `ttm_depreciation_and_amortization` | Sum of last 4 quarterly `depreciation_and_amortization` | Smoother non‑cash add‑backs. |
| TTM OCF | `ttm_operating_cash_flow` | Sum of last 4 quarterly `operating_cash_flow` | 12‑month operating cash power. |
| TTM CapEx | `ttm_capital_expenditures` | Sum of last 4 quarterly `capital_expenditures` | 12‑month reinvestment spend. |
| TTM FCF | `ttm_free_cash_flow` | `ttm_operating_cash_flow - ttm_capital_expenditures` | 12‑month cash available for distributions. |
| TTM Investing CF | `ttm_investing_cash_flow` | Sum of last 4 `cash_flow_from_investment` | 12‑month net investing cash usage. |
| TTM Financing CF | `ttm_financing_cash_flow` | Sum of last 4 `financing_cash_flow` | 12‑month net distributions/issuance. |
| TTM Dividends paid | `ttm_dividends_paid` | Sum of last 4 `(dividend_common + dividend_pref)` | 12‑month shareholder cash return (dividends). |
| TTM Buybacks | `ttm_buybacks` | Sum of last 4 `proceeds_from_repurchase_of_equity` | 12‑month buyback spend (use `abs` when comparing). |
| TTM Net change in cash | `ttm_net_change_in_cash` | Sum of last 4 `net_change_in_cash` | 12‑month cash bridge. |
| TTM Δ Cash & equiv. | `ttm_change_in_cash_and_cash_equivalents` | Sum of last 4 `change_in_cash_and_cash_equivalents` | 12‑month reported/computed delta. |
| TTM Cash return to shareholders | `ttm_cash_return_to_shareholders` | `ttm_dividends_paid + abs(ttm_buybacks)` | Aggregate cash distributions over 12 months. |
| TTM FCF after distributions | `ttm_free_cash_flow_after_distributions` | `ttm_free_cash_flow - ttm_cash_return_to_shareholders` | Residual FCF after dividends/buybacks. |
| TTM OCF – CapEx – Dividends | `ttm_operating_cash_flow_after_capex_and_dividends` | `ttm_operating_cash_flow - abs(ttm_capital_expenditures) - ttm_dividends_paid` | Operations’ capacity after mandatory outflows. |
| TTM OCF + Investing | `ttm_operating_cash_flow_minus_investing` | `ttm_operating_cash_flow + ttm_investing_cash_flow` | Combined operations and investing cash. |
| TTM OCF / TTM NI | `ttm_operating_cash_flow_to_net_income` | `ttm_operating_cash_flow / ttm_net_income` | 12‑month cash earnings quality. |
| TTM CapEx reinvestment | `ttm_capex_reinvestment_ratio` | `abs(ttm_capital_expenditures) / ttm_operating_cash_flow` | 12‑month reinvestment intensity. |
| TTM FCF / TTM OCF | `ttm_free_cash_flow_to_ocf` | `ttm_free_cash_flow / ttm_operating_cash_flow` | 12‑month free‑cash conversion. |
| TTM Dividend coverage by OCF | `ttm_dividend_coverage_by_ocf` | `ttm_operating_cash_flow / ttm_dividends_paid` | 12‑month dividend sustainability. |
| TTM Buyback coverage by OCF | `ttm_buyback_coverage_by_ocf` | `ttm_operating_cash_flow / abs(ttm_buybacks)` | 12‑month repurchase sustainability. |
| TTM Distribution ratio of OCF | `ttm_distribution_ratio_of_ocf` | `(ttm_dividends_paid + abs(ttm_buybacks)) / ttm_operating_cash_flow` | Share of OCF returned to holders. |
| TTM Accruals ratio (cash‑based) | `ttm_accruals_ratio_cash_based` | `(ttm_net_income - ttm_operating_cash_flow) / abs(ttm_net_income)` | Accruals intensity; lower is higher quality. |
| YoY growth: TTM OCF | `ttm_operating_cash_flow_yoy_growth` | `YoY(ttm OCF now, ttm OCF year‑ago window)` | Trend signal on operational cash. |
| YoY growth: TTM FCF | `ttm_free_cash_flow_yoy_growth` | `YoY(ttm FCF now, ttm FCF year‑ago window)` | Trend signal on free cash generation. |
| YoY growth: TTM dividends | `ttm_dividends_yoy_growth` | `YoY(ttm dividends now vs year‑ago)` | Trend in distributions. |
| YoY growth: TTM buybacks | `ttm_buybacks_yoy_growth` | `YoY(abs(ttm buybacks) now vs year‑ago)` | Trend in repurchase activity. |

## Methods

| Inputs | Purpose & importance | Output |
|---|---|---|
| `self, other: Cashflow` (`__lt__`) | Order instances by `fiscal_date_ending` for sorting and TTM windowing. | `bool` |
| `self` (`validate`) | Reconciles OCF components vs reported and checks `ΔCash ≈ OCF + ICF + FCFIN`; surfaces data issues. | `list[str]` |
| `self` (`to_dict`) | Serializes identifiers, inputs, and computed outputs for storage/analysis. | `dict[str, Any]` |
| `self` (`as_series`) | Convenience wrapper over `to_dict()` for pandas workflows. | `pd.Series` |
| `cls, ticker: str, period: Literal["annual","quarterly"], row: dict` (`_map_json_row`) | Maps a single API row to a `Cashflow`, filling only non‑readonly inputs. | `Cashflow` |
| `cls, data: dict` (`from_json_many`) | Builds a list of `Cashflow` items from payload (`annualReports`, `quarterlyReports`) and computes single‑period ratios on annuals. | `list[Cashflow]` |
| `cls, s: pd.Series|dict` (`from_dataframe`) | Hydrates a `Cashflow` from a row/series with normalized types. | `Cashflow` |
| `items: list[Cashflow], n: int` (`_last_n`) | Utility to slice the last `n` items (used by TTM logic). | `list[Cashflow]` |
| `items: list[Cashflow], getter: Callable` (`_sum4`) | Utility to sum last 4 quarterly values when all present. | `int|float|None` |
| `self, history: Iterable[Cashflow]` (`compute_ttms`) | Computes and assigns all `ttm_*` aggregates, coverage, distribution, accrual, and YoY metrics in place. | `None` |
| `self` (`_compute_single_period_ratios`) | Computes single‑period quality & coverage ratios once per item. | `None` |

---

**Notes**  
- Coverage ratios use `abs(buybacks)` in denominators to treat repurchases as outflows.  
- When reported bridge lines exist (e.g., `operating_cashflow_reported`, `change_in_cash_and_cash_equivalents_raw`), they’re used as fallbacks to preserve source fidelity.
