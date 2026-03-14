# Moat Score — Data Ingestion Execution Plan

**Version**: 1.9
**Last Updated**: 2026-03-12
**Status**: ✅ COMPLETE — all phases and post-phase fixes validated. PR merged to `main`.
**Depends on**: Nothing (this is Phase 0 + Phase 1)
**Required by**: `moat-score-feature-dev-exec-plan.md` (cannot start until this plan is complete)

---

## Surprises & Discoveries

### S1 — FMP ratios-bulk CSV omits four expected fields (2026-03-12)

**Finding**: The FMP `/ratios-bulk?period=FY&datatype=csv` endpoint does not return `freeCashFlowToSalesRatio`, `returnOnAssets`, `returnOnEquity`, or `returnOnCapitalEmployed`. These fields appear in the FMP JSON ratios endpoint documentation but are absent from the bulk CSV response. The columns were removed from `fmp_ratios_bulk_annual`, `gold.fact_annual`, and the Gold fact service.

**Impact**: Four ratios columns cannot be ingested from this source. All four are straightforwardly computable from data already present in `fact_annual` (see recommendations below). The feature dev plan should derive them rather than read them from Gold.

**Proxy recommendations**:

| Missing column | Formula | Inputs already in `fact_annual` |
|---|---|---|
| `fcf_to_sales_ratio` | `free_cash_flow / revenue` | Both present |
| `return_on_assets` | `net_income / total_assets` | Both present |
| `return_on_equity` | `net_income / total_stockholders_equity` | Both present |
| `return_on_capital_employed` | `operating_income / (total_assets − total_current_liabilities)` | All present |

These derivations are straightforward enough that adding them as computed columns in `fact_annual` during the feature dev phase is preferable to ingesting them from a separate endpoint. No additional Bronze data required.

### S2 — FMP ratios-bulk CSV uses different field names than JSON docs (2026-03-12)

**Finding**: Several fields in the ratios-bulk CSV use different camelCase names than expected from the JSON API documentation:

| Expected (from JSON docs) | Actual (in CSV Bronze) | Fix applied |
|---|---|---|
| `calendarYear` | `fiscalYear` | Keymap `api:` corrected |
| `debtRatio` | `debtToAssetsRatio` | Keymap `api:` corrected |
| `interestCoverage` | `interestCoverageRatio` | Keymap `api:` corrected |

**Root cause**: DTOProjection uses the keymap `api:` field for column resolution, not the DTO metadata. Fixes were applied to `dataset_keymap.yaml` and the `RatiosBulkDTO`.

### S3 — Cashflow `dividends_paid` mapped to non-existent Bronze field (2026-03-12)

**Finding**: `CashflowBulkDTO.dividends_paid` was mapped to `"dividendsPaid"` via both the DTO metadata and keymap `api:` field. The FMP cashflow-bulk CSV response has no `dividendsPaid` key; it uses `netDividendsPaid` (common + preferred combined). Fixed in both `cashflow_bulk_dto.py` and `dataset_keymap.yaml` for annual and quarterly entries.

### S4 — Silver promotion uses keymap `api:` exclusively; DTO metadata is a secondary reference (2026-03-12)

**Finding**: `SilverService._promote_row` routes through `DTOProjection._project_from_schema` when the keymap entry has a `dto_schema`. In this path, the DTO's field-level `metadata={"api": ...}` is never consulted — only the keymap's `api:` field is used for column resolution. DTO metadata remains useful as documentation and for the `build_from_row` fallback path, but the authoritative source for Bronze→Silver column mapping is `dataset_keymap.yaml`.

### S5 — FMP key-metrics-bulk CSV omits four fields; four more use different names (2026-03-12)

**Finding**: The FMP `/key-metrics-bulk?datatype=csv` endpoint does not return `revenuePerEmployee`, `debtToEquity`, `assetTurnover`, or `receivablesTurnover`. Additionally, four fields that ARE present use different camelCase names than expected:

| Column | Wrong `api:` | Actual Bronze field |
|---|---|---|
| `ev_to_ebitda` | `enterpriseValueOverEBITDA` | `evToEBITDA` |
| `days_sales_outstanding` | `daysSalesOutstanding` | `daysOfSalesOutstanding` |
| `days_payables_outstanding` | `daysPayablesOutstanding` | `daysOfPayablesOutstanding` |
| `days_inventory` | `daysOfInventoryOnHand` | `daysOfInventoryOutstanding` |

The four wrong-name columns were fixed in both keymap entries (annual + quarterly), the DTO, Gold fact service, and migration. The four absent columns were removed.

**Note**: The key-metrics-bulk Bronze does contain `returnOnAssets`, `returnOnEquity`, and `returnOnCapitalEmployed` — the same fields absent from the ratios-bulk CSV (see S1). These could be sourced from key_metrics in a future pass if the feature dev plan requires them as ingested columns rather than computed ones.

**Proxy recommendations for removed columns**:

| Removed column | Formula | Inputs available |
|---|---|---|
| `revenue_per_employee` | `revenue / full_time_employees` | `revenue` in `fact_annual`; `full_time_employees` in `dim_company` (from company profile) |
| `debt_to_equity` | `total_debt / total_stockholders_equity` | Both in `fact_annual` |
| `asset_turnover` | `revenue / total_assets` | Both in `fact_annual` |
| `receivables_turnover` | `revenue / net_receivables` | `revenue` in `fact_annual`; `net_receivables` not currently ingested — proxy with `revenue / total_current_assets` |

### S6 — FMP bulk CSV returns `fiscalYear`, not `calendarYear` — NULL calendar_year in Silver (2026-03-12)

**Finding**: All FMP bulk CSV endpoints (`income-statement-bulk`, `balance-sheet-bulk`, `cashflow-bulk`, `ratios-bulk`) return the calendar year field as `fiscalYear`, not `calendarYear` as implied by the JSON API documentation. All four DTOs had `calendar_year` mapped to `"calendarYear"` via `metadata={"api": ...}` and the keymap `api:` fields, causing `calendar_year` to be NULL for every promoted Silver row in all annual tables.

**Cascade**: Three sequential cleanup migrations were required to purge bad Silver rows and restore promotability:

1. `20260310_001` — `DELETE FROM silver.fmp_income_statement_bulk_annual WHERE calendar_year IS NULL` (swallowed by a `CatalogException` on the missing quarterly table, so only partially effective)
2. `20260310_002` — Same DELETE across all three annual tables (income statement + balance sheet + cashflow)
3. `20260310_005` — DELETE + `UPDATE ops.file_ingestions SET bronze_can_promote = TRUE ... WHERE silver_rows_created = 0` to reset Bronze promotion flags so all annual files would re-promote with correct values

All three cleanup migrations were deleted from the repo after being applied on the dev DB (they'd served their purpose and are already recorded in `ops.schema_migrations`).

**Fix applied**: Updated `api:` from `"calendarYear"` → `"fiscalYear"` in:
- `IncomeStatementBulkDTO`, `BalanceSheetBulkDTO`, `CashflowBulkDTO` (annual and quarterly variants via keymap)
- `RatiosBulkDTO` (also had the same bug: `calendarYear` → `fiscalYear`)
- All four `dataset_keymap.yaml` entries for annual bulk datasets

**Root cause pattern**: FMP bulk CSV column names do not always match their JSON endpoint equivalents. Treat any `camelCase` field name from FMP JSON docs as unverified until confirmed in an actual Bronze CSV file. Always inspect Bronze content before finalising keymap `api:` values.

### S7 — FRED API key must be 32-character all-lowercase alphanumeric (2026-03-12)

**Finding**: Both FRED requests (`fred-dgs10`, `fred-usrecm`) returned HTTP 400:

> `"Bad Request. The value for variable api_key is not a 32 character alpha-numeric lower-case string."`

The key being sent contained uppercase letters. FRED API keys are lowercase hex strings only.

**Fix**: Replace `FRED_API_KEY` in `.env` with the correct lowercase key from your FRED account at fred.stlouisfed.org. No code change required — the key injection path is correct.

**Prerequisite**: A valid FRED API key is required before Tier 4 checks 2 and 3 can be completed.

### S8 — `BronzeService` passed FMP API key to all sources, breaking FRED authentication (2026-03-12)

**Finding**: `BronzeService` stores only `self.fmp_api_key` and passed it as `api_key=self.fmp_api_key` in all 4 `RunRequest.from_recipe()` call sites — regardless of recipe source. `DatasetRecipe.get_query_vars()` resolves `api_key_value = api_key if api_key else os.getenv(...)`, so a truthy FMP key always won, and FRED requests received the FMP key instead of the FRED key.

**Fix**: All 4 call sites in `bronze_service.py` changed to `api_key=self.fmp_api_key if recipe.source == FMP_DATA_SOURCE else None`. Passing `None` causes `get_query_vars` to fall back to `os.getenv("FRED_API_KEY")` as designed. FMP behaviour is unchanged.

**Pattern**: `BronzeService` is now source-agnostic at the recipe loop level. Any new non-FMP source added in the future will work correctly without further changes.

### S9 — FMP eod-bulk endpoint omits four expected fields (2026-03-12)

**Finding**: The FMP `/eod-bulk` CSV response only returns `symbol`, `date`, `open`, `high`, `low`, `close`, `adjClose`, `volume`. The fields `unadjustedVolume`, `change`, `changePercent`, and `vwap` are absent from the bulk endpoint. All four were in `EodBulkPriceDTO` and `dataset_keymap.yaml` but produced NULL Silver and Gold rows.

**Disposition of each field**:

| Column | Decision | Rationale |
|---|---|---|
| `unadjusted_volume` | Removed | Redundant — splits do not adjust volume; `volume` IS unadjusted |
| `change` | Removed | Derivable as `adj_close − LAG(adj_close)` in feature dev |
| `change_pct` | Removed | Derivable as `(adj_close − LAG(adj_close)) / LAG(adj_close)` in feature dev |
| `vwap` | Removed | Requires intraday tick data; not computable from EOD; not used in any moat pillar |

**Fix applied**: Removed from `EodBulkPriceDTO`, `dataset_keymap.yaml`, `GoldFactService._build_fact_eod`. Migration `20260312_003_drop_fact_eod_unavailable_columns.sql` drops the four columns from `gold.fact_eod`.

---

## Benchmarking Recommendation: Industry over Sector

**Use FMP `industry` as the primary peer group, falling back to `sector` when n < 10.**

The case for industry over sector is compelling. GICS has four levels: Sector (11 groups), Industry Group (25), Industry (69), and Sub-Industry (158). Benchmarking at the Sector level is too coarse — it groups software, semiconductors, and IT services into a single pool with structurally different economics. At the Industry level you get meaningful separation: "Software" is distinct from "Semiconductors" is distinct from "Electronic Equipment & Instruments." FMP's `industry` field in the company profile bulk maps approximately to GICS Industry (69 groups), which achieves ~80% of the precision of full GICS Sub-Industry without requiring a GICS license or additional data.

The full benchmark hierarchy for the moat model is:

1. **Primary**: FMP `industry` — the main cross-sectional peer group (target n ≥ 10)
2. **Fallback**: FMP `sector` — when industry peer count < 10
3. **Self-baseline**: Company's own trailing 5-year median — for trend and persistence signals
4. **Global scope**: All FMP-covered tickers regardless of exchange — moats are competed globally

This hierarchy already lives in `gold.dim_company` via `sector_sk` and `industry_sk`, making it directly addressable without additional joins.

---

## Progress

- [x] Phase 0.1 — Expand `IncomeStatementBulkDTO` (6 fields)
- [x] Phase 0.2 — Expand `BalanceSheetBulkDTO` (2 fields)
- [x] Phase 0.3 — Re-promote Bronze → Silver (no new API calls)
- [x] Phase 0.4 — Add `key-metrics-bulk-annual` and `key-metrics-bulk-quarter`
- [x] Phase 0.5 — Add `ratios-bulk-annual`
- [x] Phase 0.6 — Add FRED DGS10 ingestion
- [x] Phase 0.7 — Add FRED USRECM ingestion
- [x] Phase 0.8 — Add FMP Market Risk Premium ingestion (monthly, global)
- [x] Phase 1.1 — Migration: expand `fact_annual` (income/balance fields + key metrics + ratios columns)
- [x] Phase 1.2 — Migration: expand `fact_quarter` (income/balance fields)
- [x] Phase 1.3 — Update `GoldFactService` for expanded columns and optional key metrics / ratios joins

**Post-phase fixes (discovered during validation):**

- [x] Fix S6 — Correct `calendarYear` → `fiscalYear` in all annual bulk DTOs and keymap; run three cleanup migrations to purge NULL `calendar_year` Silver rows and reset Bronze promotion flags
- [x] Fix S8 — `BronzeService` multi-source API key routing: all 4 `from_recipe` call sites updated to pass `None` for non-FMP sources so `get_query_vars` resolves the correct env var per source
- [x] Fix S9 — Remove four unavailable EOD columns (`unadjusted_volume`, `change`, `change_pct`, `vwap`) from DTO, keymap, Gold service, and `gold.fact_eod` via migration `20260312_003`
- [x] Fix S7 — Add valid lowercase `FRED_API_KEY` to `.env` and re-run EOD domain to ingest `fred-dgs10` and `fred-usrecm`

---

## Part A — Six Pillar Data Requirements

### Pillar 1 — Excess Profitability vs Capital Cost

**What we compute**: ROIC, WACC, ROIC − WACC spread, persistence of spread over trailing 5 years, and trend direction.

**Data required**:

| Item | Source | Derivation | Available now? |
|------|---------|-----------|----------------|
| Invested capital | Silver fact_annual | `total_stockholders_equity + total_debt − cash_and_cash_equivalents` | ✓ computable |
| NOPAT | Silver fact_annual | `operating_income × (1 − effective_tax_rate)` | Partial — needs `income_tax_expense` and `income_before_tax` |
| ROIC | FMP key-metrics-bulk | Provided directly | ✗ new dataset |
| Cost of equity | FRED DGS10 + FMP profile beta + FMP Market Risk Premium | `rf + β × ERP` where ERP = `totalEquityRiskPremium` for company's country | ✗ needs DGS10 + market-risk-premium |
| Cost of debt | Silver fact_annual | `interest_expense / total_debt` | ✗ needs `interest_expense` |
| Effective tax rate | Silver fact_annual | `income_tax_expense / income_before_tax` | ✗ needs both fields |
| WACC | Computed | `(E/V) × Ke + (D/V) × Kd × (1−t)` | ✗ depends on above |

**Cadence**: Annual

---

### Pillar 2 — Profit and Cash-Flow Durability

**What we compute**: Gross margin, operating margin, FCF margin, rolling standard deviation of each, and revenue resilience in recession years.

**Data required**:

| Item | Source | Derivation | Available now? |
|------|---------|-----------|----------------|
| Gross margin | Silver fact_annual | `gross_profit / revenue` | ✓ computable |
| Operating margin | Silver fact_annual | `operating_income / revenue` | ✓ computable |
| FCF margin | Silver fact_annual | `free_cash_flow / revenue` | ✓ computable |
| Margin volatility | Gold (computed) | Rolling 5Y std dev of margins | ✓ computable from above |
| Recession flag | FRED (USRECM or NBER dates) | Binary indicator by calendar year | ✗ new dataset |
| Revenue resilience | Silver + FRED | Revenue drawdown in USRECM periods | ✗ needs recession flag |

**Cadence**: Annual

---

### Pillar 3 — Market Power and Competitive Position

**What we compute**: Revenue growth (company vs industry median), gross margin vs industry median, and revenue per unit proxies.

**Data required**:

| Item | Source | Derivation | Available now? |
|------|---------|-----------|----------------|
| Revenue growth | Silver fact_annual | YoY `revenue` | ✓ computable |
| Industry median revenue growth | Gold (cross-sectional) | Median over `industry_sk` | ✓ computable once revenue in Gold |
| Gross margin vs peers | Gold (cross-sectional) | Company percentile within industry | ✓ computable |
| Operating margin vs peers | Gold (cross-sectional) | Company percentile within industry | ✓ computable |

**Cadence**: Annual

---

### Pillar 4 — Switching Costs and Customer Lock-In

**What we compute**: Deferred revenue as % of revenue (stickiness proxy), SG&A as % of revenue (acquisition cost efficiency), and contract embeddedness.

**Data required**:

| Item | Source | Derivation | Available now? |
|------|---------|-----------|----------------|
| Deferred revenue | FMP balance sheet (full) | `deferred_revenue` field | ✗ not in current DTO |
| SG&A | FMP income statement (full) | `selling_general_and_administrative_expenses` | ✗ not in current DTO |
| R&D | FMP income statement (full) | `research_and_development_expenses` | ✗ not in current DTO |
| Revenue per employee | FMP key-metrics-bulk | Provided directly | ✗ new dataset |
| Net revenue retention | Not available in FMP/FRED/BIS | SaaS-specific; no bulk source | ✗ not buildable |

**Note**: Net revenue retention (NRR) and contract length are not available from any bulk FMP, BIS, or FRED endpoint. These remain qualitative for non-SaaS companies. The best available proxies are deferred revenue, SG&A efficiency, and R&D intensity.

**Cadence**: Annual

---

### Pillar 5 — Structural Cost Advantage

**What we compute**: COGS/revenue, SG&A/revenue, asset turnover, and revenue per employee — all relative to industry peers.

**Data required**:

| Item | Source | Derivation | Available now? |
|------|---------|-----------|----------------|
| COGS ratio | Silver fact_annual | `(revenue − gross_profit) / revenue` | ✓ computable |
| SG&A ratio | FMP income statement (full) | `selling_general_and_administrative_expenses / revenue` | ✗ needs SG&A field |
| Asset turnover | Silver fact_annual | `revenue / total_assets` | ✓ computable |
| Revenue per employee | FMP key-metrics-bulk or profile | Company profile has `full_time_employees`; revenue in Silver | ✓ computable with join |

**Cadence**: Annual

---

### Pillar 6 — Innovation and Intangible Reinvestment

**What we compute**: R&D as % of revenue, intangible/goodwill as % of total assets, and incremental ROIC (change in NOPAT / change in invested capital).

**Data required**:

| Item | Source | Derivation | Available now? |
|------|---------|-----------|----------------|
| R&D / revenue | FMP income statement (full) | `research_and_development_expenses / revenue` | ✗ needs R&D field |
| Goodwill + intangibles | FMP balance sheet (full) | `goodwill_and_intangible_assets` | ✗ not in current DTO |
| D&A | FMP income statement (full) | `depreciation_and_amortization` | ✗ not in current DTO |
| Incremental ROIC | Gold (computed) | `ΔNOPAT / ΔInvested Capital` (rolling) | ✗ depends on NOPAT |
| Patent counts | Not available in FMP/FRED/BIS | USPTO API is per-ticker, no bulk | ✗ not buildable at scale |

**Cadence**: Annual

---

## Part B — New Data Ingestion Required

### B1. Expand Existing FMP DTOs (Quarterly + Annual)

The current `IncomeStatementBulkDTO` and `BalanceSheetBulkDTO` are trimmed. The FMP bulk endpoints already return these additional fields — we just need to capture them in the DTOs and Silver schema.

**Add to `IncomeStatementBulkDTO`**:

| Field | FMP API Name | Pillar |
|-------|-------------|--------|
| `research_and_development_expenses` | `researchAndDevelopmentExpenses` | 4, 6 |
| `selling_general_and_administrative_expenses` | `sellingGeneralAndAdministrativeExpenses` | 4, 5 |
| `interest_expense` | `interestExpense` | 1 (WACC) |
| `income_before_tax` | `incomeBeforeTax` | 1 (tax rate) |
| `income_tax_expense` | `incomeTaxExpense` | 1 (tax rate) |
| `depreciation_and_amortization` | `depreciationAndAmortization` | 6 |

**Add to `BalanceSheetBulkDTO`**:

| Field | FMP API Name | Pillar |
|-------|-------------|--------|
| `deferred_revenue` | `deferredRevenue` | 4 |
| `goodwill_and_intangible_assets` | `goodwillAndIntangibleAssets` | 6 |

These expansions affect both quarterly and annual variants. Since the existing Bronze files already contain the full API response, Silver can be re-promoted from existing Bronze without new API calls.

---

### B2. New FMP Datasets

**FMP Key Metrics Bulk** — `Annual` cadence

Provides pre-computed ROIC, invested capital, revenue per employee, and capital efficiency metrics. Avoids recomputing ROIC from scratch.

| Dataset name | FMP endpoint | Cadence | Silver table |
|---|---|---|---|
| `key-metrics-bulk-annual` | `/key-metrics-bulk?period=FY&datatype=csv` | Annual | `fmp_key_metrics_bulk_annual` |
| `key-metrics-bulk-quarter` | `/key-metrics-bulk?period=quarter&datatype=csv` | Quarterly | `fmp_key_metrics_bulk_quarter` |

Key fields confirmed in bulk CSV response: `roic` (from `returnOnInvestedCapital`), `invested_capital`, `capex_to_ocf` (from `capexToOperatingCashFlow`), `ev_to_ebitda` (from `evToEBITDA`), `days_sales_outstanding` (from `daysOfSalesOutstanding`), `days_payables_outstanding` (from `daysOfPayablesOutstanding`), `days_inventory` (from `daysOfInventoryOutstanding`).

**Not available in bulk CSV** (see S5): `revenue_per_employee`, `debt_to_equity`, `asset_turnover`, `receivables_turnover`. All four are computable from existing `fact_annual` columns — see proxy recommendations in S5.

**Also present in Bronze but not yet ingested**: `returnOnAssets`, `returnOnEquity`, `returnOnCapitalEmployed` — same fields absent from ratios-bulk (see S1). Could be sourced here instead of computed if needed.

**FMP Ratios Bulk** — `Annual` cadence

Provides pre-computed profitability, efficiency, and leverage ratios.

| Dataset name | FMP endpoint | Cadence | Silver table |
|---|---|---|---|
| `ratios-bulk-annual` | `/ratios-bulk?period=FY&datatype=csv` | Annual | `fmp_ratios_bulk_annual` |

Key fields available in the bulk CSV response: `gross_profit_margin`, `operating_profit_margin`, `net_profit_margin`, `effective_tax_rate`, `debt_ratio` (mapped from `debtToAssetsRatio`), `interest_coverage` (mapped from `interestCoverageRatio`).

**Not available in bulk CSV** (see S1): `free_cash_flow_to_sales_ratio`, `return_on_assets`, `return_on_equity`, `return_on_capital_employed`. These are computable from `fact_annual` — see proxy recommendations in S1.

---

### B3. New FMP Global Dataset — Market Risk Premium

**FMP Market Risk Premium** — `Monthly` ingestion cadence (data updates annually each January from Damodaran)

Provides country-level equity risk premiums sourced from Damodaran's annual country risk premium dataset. Used in WACC cost-of-equity to supply a country-appropriate ERP instead of a hardcoded constant. A single API call returns all ~180 countries with no ticker loop.

| Dataset name | FMP endpoint | Cadence | Silver table |
|---|---|---|---|
| `market-risk-premium` | `/stable/market-risk-premium` | Monthly | `fmp_market_risk_premium` |

**Key fields**:

| Field | FMP API Name | Notes |
|-------|-------------|-------|
| `country` | `country` | KEY — one row per country |
| `continent` | `continent` | Geographic grouping |
| `total_equity_risk_premium` | `totalEquityRiskPremium` | ERP as a percentage (e.g., `5.0` = 5.0%); US base case ≈ 4.5–5.5% |
| `country_risk_premium` | `countryRiskPremium` | Additive premium over US base ERP; 0.0 for US |

**Keymap design**:
- `ticker_scope: global` — single request, no ticker loop; `ticker = None`
- `discriminator: ''` — no partitioning needed; one snapshot covers all countries
- `key_cols: [country]` — upsert keyed by country name
- `row_date_col: null` — snapshot; `as_of_date` defaults to ingestion date
- `min_age_days: 30` — re-fetch monthly; effective change occurs only in January but monthly polling catches any mid-year corrections FMP may apply
- `run_days: [sat]`
- `cadence_mode: interval`

**WACC usage**: For a company domiciled in country C, look up `silver.fmp_market_risk_premium WHERE country = C` (most recent row) to get `total_equity_risk_premium`. Then: `Ke = Rf + β × (total_equity_risk_premium / 100)`. US-listed companies with no explicit country override use `country = 'United States'`.

**Plan tier**: Free/Starter — no premium tier required.

---

### B4. New FRED Datasets

BIS and FRED are registered as data sources in `settings.py` but have no active keymap entries. FRED is the priority.

**FRED DGS10** — `EOD` cadence

The 10-year constant maturity Treasury yield. Used as the risk-free rate in WACC cost-of-equity (CAPM). Published daily by the Federal Reserve.

| Dataset name | FRED series | Cadence | Silver table |
|---|---|---|---|
| `fred-dgs10` | `DGS10` | EOD | `fred_dgs10` |

FMP also offers a risk-free rate via its economics endpoint (`/economic?name=10Y`). Either works; FRED is the more authoritative source for research.

**FRED USRECM** — `EOD` or `Monthly` cadence

The NBER recession indicator (0/1 binary by month). Used to flag recession windows for revenue resilience testing in Pillar 2. Published monthly.

| Dataset name | FRED series | Cadence | Silver table |
|---|---|---|---|
| `fred-usrecm` | `USRECM` | Monthly → `EOD` join | `fred_usrecm` |

---

### B5. BIS Assessment

BIS provides aggregate banking, credit, and property data at the country or sector level. Available datasets include total credit to private non-financial sectors (series: `credit_to_gdp` gap) and residential property prices.

**Recommendation**: Defer BIS ingestion. BIS data is country-level macro and does not map to individual stock moat signals without complex transmission assumptions. The only potential use case is cycle-adjusted benchmarking — using BIS credit cycles to weight multi-year moat averages. This is a Phase 2+ enhancement. The FRED recession indicator (USRECM) covers the primary use case for stress-period identification.

---

## Part C — Dataset Cadence Summary

| Dataset | Source | Cadence | Scope | New / Existing |
|---------|--------|---------|-------|---------------|
| `eod-bulk-price` | FMP | **EOD** | Global bulk | Existing |
| `company-profile-bulk` | FMP | **EOD** | Global bulk | Existing |
| `fred-dgs10` | FRED | **EOD** | US only | New |
| `fred-usrecm` | FRED | **Monthly** | US only | New |
| `market-risk-premium` | FMP | **Monthly** | ~180 countries | New |
| `income-statement-bulk-quarter` | FMP | **Quarterly** | Global bulk | Existing (expand DTO) |
| `balance-sheet-bulk-quarter` | FMP | **Quarterly** | Global bulk | Existing (expand DTO) |
| `cashflow-bulk-quarter` | FMP | **Quarterly** | Global bulk | Existing |
| `key-metrics-bulk-quarter` | FMP | **Quarterly** | Global bulk | New |
| `income-statement-bulk-annual` | FMP | **Annual** | Global bulk | Existing (expand DTO) |
| `balance-sheet-bulk-annual` | FMP | **Annual** | Global bulk | Existing (expand DTO) |
| `cashflow-bulk-annual` | FMP | **Annual** | Global bulk | Existing |
| `key-metrics-bulk-annual` | FMP | **Annual** | Global bulk | New |
| `ratios-bulk-annual` | FMP | **Annual** | Global bulk | New |

**Monthly cadence note**: `fred-usrecm` and `market-risk-premium` both run on a monthly schedule (`min_age_days: 30`, `run_days: [sat]`). The USRECM series is published monthly by NBER; the FMP market risk premium data updates annually in January but is polled monthly to capture any mid-cycle corrections. Both use `cadence_mode: interval`.

---

## Part D — Gold Layer Schema

### D1. Expand `fact_annual` and `fact_quarter`

Add the new DTO fields directly to the existing fact tables via migration. No new fact table needed for raw financials.

**New columns in `fact_annual` / `fact_quarter`**:

```sql
-- From expanded income statement
research_and_development_expenses          DOUBLE,
selling_general_and_administrative_expenses DOUBLE,
interest_expense                           DOUBLE,
income_before_tax                          DOUBLE,
income_tax_expense                         DOUBLE,
depreciation_and_amortization              DOUBLE,
-- From expanded balance sheet
deferred_revenue                           DOUBLE,
goodwill_and_intangible_assets             DOUBLE,
```

### D2. Add key metrics columns to `gold.fact_annual`

`key-metrics-bulk-annual` and `ratios-bulk-annual` share the same grain as `fact_annual` — both key on `(instrument_sk, calendar_year)`. Creating a separate fact table at the same primary key is a star-schema anti-pattern that forces unnecessary joins in every feature query. Instead, their columns are added to `fact_annual` as nullable `DOUBLE` columns populated via an optional `LEFT JOIN` on the respective Silver tables.

`GoldFactService._build_fact_annual` already uses this pattern for balance sheet and cashflow (both optional joins). Key metrics and ratios are a third and fourth optional join on the same model.

**New columns in `fact_annual`** (via migration, in addition to those in D1):

```sql
-- From fmp_key_metrics_bulk_annual (fields confirmed present in CSV response)
roic                      DOUBLE,
invested_capital          DOUBLE,
capex_to_ocf              DOUBLE,
ev_to_ebitda              DOUBLE,
days_sales_outstanding    DOUBLE,
days_payables_outstanding DOUBLE,
days_inventory            DOUBLE,
-- NOTE: revenue_per_employee, debt_to_equity, asset_turnover, receivables_turnover
-- are NOT in the FMP bulk CSV response. Derive in feature dev (see S5).
-- From fmp_ratios_bulk_annual (fields confirmed present in CSV response)
gross_profit_margin       DOUBLE,
operating_profit_margin   DOUBLE,
net_profit_margin         DOUBLE,
effective_tax_rate        DOUBLE,
debt_ratio                DOUBLE,   -- sourced from debtToAssetsRatio
interest_coverage         DOUBLE,   -- sourced from interestCoverageRatio
-- NOTE: fcf_to_sales_ratio, return_on_assets, return_on_equity,
-- return_on_capital_employed are NOT in the FMP bulk CSV response.
-- Derive in feature dev from existing fact_annual columns (see S1).
```

These columns are NULL for any instrument/year where the respective Silver table has not yet been populated. A re-run of `GoldFactService` after Silver is populated fills them in via the `ON CONFLICT DO UPDATE` UPSERT, without touching the income/balance/cashflow columns.

---

## Part E — Implementation Phases

### Phase 0 — Prerequisites (SBFoundation)

1. **Expand `IncomeStatementBulkDTO`** — add 6 new fields: `research_and_development_expenses`, `selling_general_and_administrative_expenses`, `interest_expense`, `income_before_tax`, `income_tax_expense`, `depreciation_and_amortization`. Update both quarterly and annual `dataset_keymap.yaml` entries.
2. **Expand `BalanceSheetBulkDTO`** — add 2 new fields: `deferred_revenue`, `goodwill_and_intangible_assets`. Update both quarterly and annual keymap entries.
3. **Re-promote Bronze → Silver** — existing Bronze files contain all these fields already. Run a Silver re-promotion pass without new API calls.
4. **Add `key-metrics-bulk-annual` and `key-metrics-bulk-quarter`** — new DTO, new keymap entry, new Silver table, new Bronze ingest.
5. **Add `ratios-bulk-annual`** — new DTO, new keymap entry, new Silver table.
6. **Add FRED DGS10 ingestion** — implement FRED HTTP client (or reuse existing pattern), new keymap entry, new Silver table `fred_dgs10` (date, value).
7. **Add FRED USRECM** — new keymap entry, Silver table `fred_usrecm` (date, recession_flag INT).
8. **Add FMP Market Risk Premium** — new `MarketRiskPremiumDTO` capturing `country`, `continent`, `total_equity_risk_premium`, `country_risk_premium`; global endpoint (no ticker loop); `ticker_scope: global`; new keymap entry; new Silver table `fmp_market_risk_premium` keyed on `country`; monthly cadence (`min_age_days: 30`). No new HTTP client needed — reuses FMP adapter.

### Phase 1 — Gold Schema Migration (SBFoundation)

8. Write migration `20260312_001_expand_fact_annual_income_bs_fields.sql` — `ALTER TABLE gold.fact_annual ADD COLUMN` for the 8 income/balance fields from D1 plus the key metrics and ratios columns from D2 (all nullable `DOUBLE`).
9. Write migration `20260312_002_expand_fact_quarter_income_bs_fields.sql` — `ALTER TABLE gold.fact_quarter ADD COLUMN` for the same 8 income/balance fields (key metrics and ratios are annual-only; no quarter expansion needed).
10. Update `GoldFactService._build_fact_annual` to add two additional optional `LEFT JOIN`s:
    - `silver.fmp_key_metrics_bulk_annual` on `(symbol, calendar_year)` → populate key metrics columns
    - `silver.fmp_ratios_bulk_annual` on `(symbol, calendar_year)` → populate ratios columns

    Extend the `ON CONFLICT DO UPDATE SET` clause to include the new columns. Follow the existing pattern used for balance sheet and cashflow (skip join gracefully if Silver table does not yet exist).

---

## Part F — Data Gap Summary by Pillar

| Pillar | Computable from existing Silver | Requires DTO expansion | Requires new dataset |
|--------|-------------------------------|------------------------|---------------------|
| 1 Profitability | Invested capital (approx) | `interest_expense`, `income_tax_expense`, `income_before_tax` | FRED DGS10 (Rf); FMP market-risk-premium (ERP by country); FMP key-metrics-bulk (ROIC direct) |
| 2 Durability | Gross/op/FCF margin | — | FRED USRECM (recession flag) |
| 3 Competitive | Revenue growth | — | None — peer stats computed cross-sectionally |
| 4 Lock-in | — | `deferred_revenue`, `selling_general_and_administrative_expenses` | None |
| 5 Cost advantage | COGS ratio, asset turnover, rev/employee (approx) | `selling_general_and_administrative_expenses` | None |
| 6 Reinvestment | — | `research_and_development_expenses`, `goodwill_and_intangible_assets`, `depreciation_and_amortization` | None |

The critical path is: **DTO expansion → re-promote Silver → FRED DGS10 ingest + FMP market-risk-premium ingest → Gold schema migration → (unblocks feature dev plan)**. Pillars 2, 3, 4, 5, and 6 are fully unblocked once DTO expansion and re-promotion complete. Pillar 1 (WACC) additionally requires FRED DGS10 (Rf) and FMP market-risk-premium (ERP) — both are independent ingestions that can run in parallel.

---

## Validation and Acceptance

### Tier 1 — Quick checks

```bash
# Confirm DTO fields parse without error
python -c "from sbfoundation.dtos.fundamentals.income_statement_bulk_dto import IncomeStatementBulkDTO; print('OK')"
python -c "from sbfoundation.dtos.fundamentals.balance_sheet_bulk_dto import BalanceSheetBulkDTO; print('OK')"
python -c "from sbfoundation.dtos.fundamentals.key_metrics_bulk_dto import KeyMetricsBulkDTO; print('OK')"
python -c "from sbfoundation.dtos.economics.fred_dgs10_dto import FredDgs10DTO; print('OK')"
python -c "from sbfoundation.dtos.economics.market_risk_premium_dto import MarketRiskPremiumDTO; print('OK')"

# Confirm keymap parses with new entries
python -c "from sbfoundation.config.dataset_keymap import DatasetKeymap; k = DatasetKeymap(); print(len(k.datasets), 'datasets loaded')"
```

### Tier 2 — DB checks

```python
import duckdb
con = duckdb.connect("path/to/dev.duckdb")

# Expanded income/balance columns exist in Gold fact tables
con.execute("SELECT research_and_development_expenses, interest_expense FROM gold.fact_annual LIMIT 1").fetchall()
con.execute("SELECT research_and_development_expenses, interest_expense FROM gold.fact_quarter LIMIT 1").fetchall()

# Key metrics and ratios columns exist in fact_annual (no separate table)
con.execute("SELECT roic, invested_capital, gross_profit_margin, effective_tax_rate FROM gold.fact_annual LIMIT 1").fetchall()

# fact_eod schema: removed columns must not exist; placeholder feature columns must exist
con.execute("SELECT momentum_1m, momentum_3m, momentum_6m, momentum_12m, volatility_30d FROM gold.fact_eod LIMIT 1").fetchall()
# The following must raise BinderException (columns no longer exist):
# con.execute("SELECT unadjusted_volume, change, change_pct, vwap FROM gold.fact_eod LIMIT 1")

# Silver tables exist
con.execute("SELECT COUNT(*) FROM silver.fmp_key_metrics_bulk_annual").fetchone()
con.execute("SELECT COUNT(*) FROM silver.fred_dgs10").fetchone()   -- requires Fix S7 (valid FRED key + re-run)
con.execute("SELECT COUNT(*) FROM silver.fred_usrecm").fetchone()  -- requires Fix S7
con.execute("SELECT COUNT(*) FROM silver.fmp_market_risk_premium").fetchone()

# US ERP is present and in a plausible range (4–8%)
con.execute("""
    SELECT total_equity_risk_premium FROM silver.fmp_market_risk_premium
    WHERE country = 'United States'
""").fetchone()  -- expect value between 4.0 and 8.0
```

### Tier 3 — Integration / dry-run check

```bash
# Dry-run Silver re-promotion from existing Bronze (no API calls)
python -m sbfoundation.api repromote --domain fundamentals --enable_bronze=false

# Dry-run FRED ingest (verify request shape, no write)
python -m sbfoundation.api ingest --domain economics --enable_silver=false
```

Expected: log lines show correct request URLs, no errors, row counts non-zero.

### Tier 4 — Post-live-run checks

**Prerequisite for checks 2–3**: Fix S7 complete — valid lowercase `FRED_API_KEY` confirmed in `.env`; EOD domain re-run successful.

1. `silver.fmp_key_metrics_bulk_annual` has rows for all tickers in universe
2. `silver.fred_dgs10` has daily rows from at least 2010-01-01 to present *(blocked until Fix S7)*
3. `silver.fred_usrecm` has monthly rows from at least 2000-01-01 to present *(blocked until Fix S7)*
4. `silver.fmp_market_risk_premium` has ~150+ country rows; `country = 'United States'` has `total_equity_risk_premium` between 4.0 and 8.0
5. `gold.fact_annual` has non-null `research_and_development_expenses` for AAPL (Apple reports R&D)
6. `gold.fact_annual` has non-null `interest_expense` for a leveraged company (e.g., BA)
7. `gold.fact_annual` has non-null `roic` and `invested_capital` for AAPL after key-metrics-bulk ingest
8. `gold.fact_annual` has non-null `gross_profit_margin`, `effective_tax_rate`, `debt_ratio`, `interest_coverage` after ratios-bulk ingest; `fcf_to_sales_ratio`, `return_on_assets`, `return_on_equity`, `return_on_capital_employed` are intentionally absent (computed in feature dev — see S1)
9. `gold.fact_eod` has no `unadjusted_volume`, `change`, `change_pct`, or `vwap` columns (dropped via migration `20260312_003`); placeholder feature columns `momentum_1m/3m/6m/12m` and `volatility_30d` exist and are NULL (populated by feature dev plan)
10. Re-running the same date produces identical row counts (idempotency)
