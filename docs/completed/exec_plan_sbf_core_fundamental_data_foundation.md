# SBFoundation: Data Foundation for Core Fundamental Features — ExecPlan

**Plan ID**: `sbf_core_fundamental_data_foundation_v1`
**Upstream Plan**: `SBIntelligence/docs/prompts/strats/exec_plan_core_fundamental_features.md`
**Author**: Todd Adams
**Created**: 2026-02-23
**Updated**: 2026-02-24
**Status**: Complete

---

## Purpose / Big Picture

The SBIntelligence `exec_plan_core_fundamental_features.md` declares: *"No new Bronze datasets required — all Phase 1 features derive from existing Gold tables."* This claim assumes SBFoundation's Silver layer already provides every column that the Gold builders need.

This ExecPlan audits that assumption and fixes any gaps. It is the SBFoundation prerequisite for the following SBIntelligence feature tables:

| SBIntelligence Feature | Primary Silver Source(s) |
|------------------------|-------------------------|
| `features.fundamental_quality` | `silver.fmp_income_statement`, `silver.fmp_balance_sheet_statement`, `silver.fmp_cashflow_statement` |
| `features.valuation` | `silver.fmp_key_metrics`, `silver.fmp_technicals_historical_price_eod_full` |
| `features.fundamental_growth` | `silver.fmp_income_statement`, `silver.fmp_cashflow_statement` |
| `features.fcf_quality` | `silver.fmp_cashflow_statement`, `silver.fmp_balance_sheet_statement` |
| `features.financial_strength` | `silver.fmp_income_statement`, `silver.fmp_balance_sheet_statement`, `silver.fmp_cashflow_statement`, `silver.fmp_technicals_historical_price_eod_full` |
| `screeners.fundamental_screen` | `silver.fmp_key_metrics` (market_cap) |

**What this plan does NOT cover**: Gold layer construction, feature computation, signals, screeners, or strategy. This plan ends at Bronze ingestion + Silver promotion.

**CRITICAL**: This project contains ONLY Bronze and Silver layers. All feature computation happens in the downstream SBIntelligence project.

---

## Progress

### Bronze & Silver
- [x] F1 — `company-shares-float` dataset + `CompanySharesFloatDTO` already exist; captures `outstanding_shares` ✅
- [x] F2 — Added `discriminator: quarter` to `key-metrics` keymap (min_age_days: 90); updated FY key_cols to include `period`
- [x] F3 — Confirmed: use `operating_cash_flow`; note added to exec plan for SBIntelligence
- [x] F4 — Verified: `balance-sheet-statement` and `cashflow-statement` both have FY + quarter discriminators ✅
- [x] F5 — Coverage audit run; Silver quarterly period values confirmed as `Q1/Q2/Q3/Q4`; all 500 tickers have <8Q (only 2024–2025 data ingested); added `force_from_date` to `RunCommand` + `BronzeService` for historical backfill
- [x] F6 — Created `company_compensation_dto.py`; YAML already pointed to correct endpoint ✅
- [x] Q3 — Added `discriminator: quarter` to `metric-ratios` keymap (min_age_days: 90)

### Validation
- [x] V1 — period string values confirmed: `Q1`, `Q2`, `Q3`, `Q4` in cashflow + income statement Silver tables
- [x] V2 — Coverage audit complete: 500 tickers, all <8 quarters; backfill required via `force_from_date="1990-01-01"`
- [x] V3 — UPSERT key_cols updated to `[ticker, date, period]` for all key-metrics and metric-ratios variants; `[ticker, date, period]` also matches income/cashflow/balance-sheet existing pattern

### Phase 2: Universe Definition Support (§0.1)
- [x] U1 — Created `src/sbfoundation/universe_definitions.py` with `UniverseDefinition` dataclass and `UNIVERSE_REGISTRY`
- [x] U2 — Added `universe_definition: UniverseDefinition | None = None` to `RunCommand`; `_get_filtered_universe()` derives exchanges/country from it
- [x] U3 — Added `min_market_cap_usd` / `max_market_cap_usd` to `UniverseService.get_filtered_tickers()`
- [x] U4 — Added market cap CTE+JOIN to `UniverseRepo.get_filtered_tickers()` SQL (all three tiers; uses QUALIFY ROW_NUMBER for latest date per ticker)
- [x] U5 — 7 new tests added across `test_run_command_validate.py` and `test_universe_filtered_tickers.py`

---

## Surprises & Discoveries

| Date | Finding | Evidence | Resolution |
|------|---------|----------|------------|
| 2026-02-23 | `HistoricalPriceEodFullDTO` does NOT capture `outstanding_shares` | DTO file has only: `ticker`, `date`, `open`, `high`, `low`, `close`, `volume`, `change`, `change_percent`, `vwap` | Resolved: `company-shares-float` dataset + `CompanySharesFloatDTO.outstanding_shares` already exists — no price-level data needed |
| 2026-02-23 | `key_metrics` keymap entry uses only `FY` discriminator — no quarterly variant | YAML grep shows discriminator `"FY"` and single recipe per keymap entry; FMP supports `period=quarter` | Resolved: Added `discriminator: quarter` entry with `from/to` date range and `key_cols: [ticker, date, period]` |
| 2026-02-23 | Silver quarterly period values are `Q1/Q2/Q3/Q4`, not `'Q'` or `'quarter'` | DuckDB query `SELECT DISTINCT period FROM silver.fmp_cashflow_statement` | SBIntelligence Gold builders must filter with `period IN ('Q1','Q2','Q3','Q4')` — documented here |
| 2026-02-23 | All 500 tickers have <8 quarters of statement data (only 2024–2025 ingested) | DuckDB coverage audit: AAPL has 5 quarters earliest=2024-12-28 | Resolved: Added `force_from_date` to `RunCommand` + `BronzeService`; run with `force_from_date="1990-01-01"` to backfill |
| 2026-02-23 | `key-metrics quarterly` placeholder names in YAML were wrong (`__from_date__` instead of `__from__`) | `settings.py` shows `FROM_DATE_PLACEHOLDER = "__from__"`; initial quarterly entries used `__from_date__` | Fixed: corrected to `from: __from__` / `to: __to__` matching existing date-range datasets |
| 2026-02-23 | `CashflowStatementDTO` field is named `operating_cash_flow`, not `operating_activities` | `cashflow_statement_dto.py` line ~21: `KEY_COLS = ["ticker"]`; field rollup is `operating_cash_flow` | SBIntelligence Gold builder must reference `operating_cash_flow` (the Silver column name). Confirm in Gold builder before implementing. |
| 2026-02-23 | `CashflowStatementDTO.KEY_COLS = ["ticker"]` but YAML `key_cols` is `[ticker, filing_date, period]` | Both files examined | Per CLAUDE.md §10.4, YAML key_cols are authoritative for UPSERT. DTO `KEY_COLS` is informational. No bug — but the DTO's `KEY_COLS` field is misleading; note this in the SBIntelligence Gold builder docs. |
| 2026-02-23 | `features.valuation` requires `ev_to_ebitda` and `ev_to_sales` from key_metrics at quarterly cadence | Exec plan §Table: features.valuation: "Use most recent eligible period where period_end_date < as_of_date − 45 days" | If only annual key_metrics exist, valuation features are stale by up to 12 months. See Finding F2. |
| 2026-02-23 | `EnterpriseValuesDTO` captures `number_of_shares` as a point-in-time snapshot but this is annual, not daily | `enterprise_values_dto.py` fields: `stock_price`, `number_of_shares`, `market_capitalization`, etc. | Can serve as quarterly proxy for outstanding_shares if daily price-level data unavailable from FMP. See F1. |
| 2026-02-23 | `income_statement_dto.py` captures `weighted_average_shs_out` and `weighted_average_shs_out_dil` | DTO field list from exploration | Quarterly weighted average shares can serve as a proxy for outstanding_shares for dilution computation. See F1. |

---

## Decision Log

| Date | Decision | Rationale | Author |
|------|----------|-----------|--------|
| 2026-02-23 | Scope this plan to Bronze + Silver only | CLAUDE.md Hard Constraint 6: no Gold layer operations in this project | SBFoundation |
| 2026-02-23 | Treat YAML `key_cols` as authoritative for UPSERT per CLAUDE.md §10.4 | Prevents ambiguity between DTO.KEY_COLS and YAML key_cols | SBFoundation |
| 2026-02-23 | F1: Use existing `company-shares-float` dataset (no new dataset needed) | `CompanySharesFloatDTO.outstanding_shares` already captures shares data; endpoint is `shares-float` not `shares-outstanding` | Todd Adams |
| 2026-02-23 | F2: Add `key-metrics` quarterly discriminator with `min_age_days: 90`; update key_cols to `[ticker, date, period]` across all key-metrics variants | Q4 answer: 90-day cadence; period needed in key_cols to prevent FY/Q UPSERT collision on fiscal year-end dates | Todd Adams |
| 2026-02-23 | Q3: Add `metric-ratios` quarterly discriminator with `min_age_days: 90`; update key_cols to `[ticker, date, period]` across all metric-ratios variants | Mirrors key-metrics decision; fundamental_quality features need quarterly ratio data | Todd Adams |
| 2026-02-23 | F3: SBIntelligence Gold builders must reference `operating_cash_flow` (Silver column name) | Q5 answer: use `operating_cash_flow`; note to be added in SBIntelligence ExecPlan | Todd Adams |
| 2026-02-23 | F5: `FROM_DATE = "1980-01-01"` already set; exceeds 1990 target — no change needed | Settings already configured broader than required; historical backfill determined by universe `from_date` config | Todd Adams |
| 2026-02-23 | F6: Create `company_compensation_dto.py` using FMP `governance-executive-compensation` endpoint | Q9 answer: dedicated DTO needed; YAML already referenced correct endpoint and DTO class path | Todd Adams |
| 2026-02-23 | F5: Add `force_from_date` to `RunCommand` + `BronzeService` for historical backfill | All tickers only have 2024–2025 data; watermarks block re-ingestion from 1990; need explicit override | Todd Adams |
| 2026-02-23 | Quarterly period values are `Q1/Q2/Q3/Q4` in Silver — not `'Q'` or `'quarter'` | Confirmed via DuckDB `SELECT DISTINCT period`; critical for SBIntelligence Gold builder PIT filters | Todd Adams |
| 2026-02-23 | Quarterly key-metrics/metric-ratios use `from: __from__` / `to: __to__` date range, not `limit` | `limit: __limit__` = 5 records only; date-range approach fetches full history in one call for backfill | Todd Adams |

---

## Outcomes & Retrospective

### What Was Achieved

All Bronze/Silver prerequisites for SBIntelligence's core fundamental feature tables are now in place:

1. **`key-metrics` quarterly** — Added `discriminator: quarter` to YAML with `from/to` date range (not `limit`), `min_age_days: 90`, `key_cols: [ticker, date, period]`. All key-metrics variants updated for consistent UPSERT.
2. **`metric-ratios` quarterly** — Same pattern; `features.fundamental_quality` now has quarterly ratio data available after backfill.
3. **`company_compensation_dto.py`** — Created; YAML was already configured for `governance-executive-compensation` endpoint.
4. **`force_from_date` backfill mechanism** — Added to `RunCommand` and `BronzeService`; bypasses watermarks and duplicate-ingestion checks. Enables historical backfill from any date.
5. **Period values confirmed** — Silver quarterly rows use `Q1/Q2/Q3/Q4` strings; documented for SBIntelligence Gold builders.

### Gaps Remaining

- **Historical backfill not yet run**: All 500 tickers have only 2024–2025 quarterly data. Must run with `force_from_date="1990-01-01"` before `features.fcf_quality.fcf_positive_pct_8y` (32Q) is computable.
- **SBIntelligence note**: Gold builder PIT filters must use `period IN ('Q1','Q2','Q3','Q4')`, and Piotroski CFO signal must reference `operating_cash_flow` (not `operating_activities`).

---

## Context and Orientation

### Key Files

| File | Role |
|------|------|
| `config/dataset_keymap.yaml` | Authoritative dataset definitions — all changes start here |
| `src/sbfoundation/dtos/technicals/historical_price_eod_full_dto.py` | Price EOD DTO — missing outstanding_shares |
| `src/sbfoundation/dtos/fundamentals/cashflow_statement_dto.py` | Cashflow DTO — verify operating_cash_flow column name |
| `src/sbfoundation/dtos/fundamentals/income_statement_dto.py` | Income DTO — has weighted_average_shs_out (potential shares proxy) |
| `src/sbfoundation/dtos/fundamentals/key_metrics_dto.py` | Key metrics DTO — has ev_to_ebitda, ev_to_sales, market_cap ✅ |
| `src/sbfoundation/dtos/fundamentals/balance_sheet_statement_dto.py` | Balance sheet DTO — has all required columns ✅ |
| `src/sbfoundation/settings.py` | Domain and dataset constants |

### Term Definitions

| Term | Definition |
|------|-----------|
| **outstanding_shares** | Total shares issued and outstanding on a given date — needed for EPS and dilution computation in SBIntelligence Gold builders |
| **weighted_average_shs_out** | Average shares outstanding over a reporting period — quarterly proxy for outstanding_shares |
| **TTM** | Trailing Twelve Months — sum of 4 most recent quarterly periods |
| **PIT** | Point-In-Time — feature may only use data available as of the observation date |
| **quarterly discriminator** | A YAML entry variant with `discriminator: quarter` that ingests quarterly-period data from FMP |

---

## Findings & Recommendations

### Finding F1 — `outstanding_shares` Not in Silver Price Data

**Severity**: High — blocks `features.fundamental_growth.shares_dilution_yoy` and impacts EPS computation.

**What SBIntelligence needs**: `gold.fact_price_eod.outstanding_shares` — a **daily** column representing shares outstanding at a given price date. The SBIntelligence Gold builder for `fact_price_eod` (v2) sources this from Silver.

**What SBFoundation currently provides**:
- `silver.fmp_technicals_historical_price_eod_full` — has only `ticker, date, open, high, low, close, volume, change, change_percent, vwap`. No shares data.
- `silver.fmp_enterprise_values` — has `number_of_shares` as a quarterly point-in-time value.
- `silver.fmp_income_statement` — has `weighted_average_shs_out` and `weighted_average_shs_out_dil` per quarterly filing.

**Options**:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Add FMP `shares-outstanding` historical endpoint as a new dataset | True daily shares data | Need to verify FMP has this endpoint; adds new keymap entry + DTO |
| B | Enhance `HistoricalPriceEodFullDTO` to capture shares if FMP returns it in the full endpoint | Minimal new infrastructure | FMP historical-price-eod/full does NOT include outstanding_shares |
| C | Use `fmp_enterprise_values.number_of_shares` as a quarterly proxy | No new ingestion | Quarterly granularity only; stale by up to 90 days |
| D | Use `fmp_income_statement.weighted_average_shs_out` as a quarterly proxy | Already ingested ✅ | Weighted average, not point-in-time; quarterly only |

**Recommendation**: Option A (preferred) if FMP provides historical shares outstanding. Option D as interim fallback while verifying FMP endpoint.

> **Question Q1**: Does FMP's API provide a historical `shares-outstanding` endpoint (e.g., `historical-shares-outstanding` or `shares-outstanding`)?
> **Question Q2**: Is daily granularity of outstanding shares required for `shares_dilution_yoy`, or is quarterly (weighted_average_shs_out from income_statement) acceptable?

**Answer**:  Company Share Float & Liquidity API
Understand the liquidity and volatility of a stock with the FMP Company Share Float and Liquidity API. Access the total number of publicly traded shares for any company to make informed investment decisions.

Endpoint: https://financialmodelingprep.com/stable/shares-float?symbol=AAPL
documentation: https://site.financialmodelingprep.com/developer/docs#shares-float


---

### Finding F2 — `key_metrics` Ingested at Annual Frequency Only

**Severity**: High — causes stale valuation features.

**What SBIntelligence needs**: `gold.fact_key_metrics` providing `ev_to_ebitda`, `ev_to_sales`, and `market_cap` at the most recent eligible period (PIT, 45-day lag). The feature builder uses `period_end_date < as_of_date − 45 days` to find the most recent eligible row.

**What SBFoundation currently provides**: `silver.fmp_key_metrics` ingested with `discriminator: FY` only — annual data.

**Impact**: If only annual FY data exists, the most recent eligible `ev_to_ebitda` on 2026-02-18 could be the 2024 annual filing — up to 14 months stale. This makes `features.valuation.ev_to_ebitda` unreliable for cross-sectional ranking.

**FMP capability**: FMP's `key-metrics` endpoint supports `period=quarter`. A quarterly variant with `discriminator: quarter` is needed in the keymap.

**Required YAML addition**:
```yaml
# Under the key-metrics dataset entries — add new quarterly entry:
- domain: fundamentals
  source: fmp
  dataset: key-metrics
  discriminator: 'quarter'
  ticker_scope: per_ticker
  silver_schema: silver
  silver_table: fmp_key_metrics
  key_cols: [ticker, date, period]
  row_date_col: date
  recipes:
    - plans: [basic]
      data_source_path: key-metrics
      query_vars:
        symbol: __ticker__
        period: quarter
        from: __from_date__
        to: __to_date__
      date_key: date
      cadence_mode: interval
      min_age_days: 90
      run_days: [sat, mon, tues, wed, thurs, fri]
      help_url: https://site.financialmodelingprep.com/developer/docs/key-metrics-api
  dto_schema:
    dto_type: sbfoundation.dtos.fundamentals.key_metrics_dto.KeyMetricsDTO
    columns: # (same schema as FY variant)
```

**Note**: `fmp_key_metrics` Silver table already exists with the right schema. Adding the quarterly discriminator writes to the same table, with UPSERT on `[ticker, date, period]`. No schema migration needed.

> **Question Q3**: Should we also add quarterly discriminators for `metric-ratios` (currently FY only)? The `features.fundamental_quality` consumes ratio data.
> **Question Q4**: Should the quarterly `key_metrics` run on the same `min_age_days: 90` cadence as the annual, or on a tighter `45`-day cadence to ensure quarterly filings are captured promptly?

**Answer**:  Yes add quarterly discriminators for `metric-ratios` with `min_age_days: 90`

---

### Finding F3 — `operating_cash_flow` Column Name Must Align with Gold Builders

**Severity**: Medium — naming mismatch would cause silent NULLs in features.

**What SBIntelligence needs**: The `features.financial_strength` Piotroski `fs_cfo` signal uses `operating_activities` (the term used in the academic paper and SBIntelligence's plan). The Surprises section of `exec_plan_core_fundamental_features.md` notes: *"Piotroski CFO signal requires operating_activities from cashflow statement; not listed in CLAUDE.md §5.3 key columns. Use free_cash_flow as conservative proxy."*

**What SBFoundation currently provides**: `CashflowStatementDTO` captures:
- `net_cash_provided_by_operating_activities` — the full-name version
- `operating_cash_flow` — a rollup alias

**Column names in Silver table**: Both will be present as snake_case columns.

**Resolution**: No SBFoundation change needed. SBIntelligence Gold builder should reference `operating_cash_flow` (the shorter alias). This should be documented in the SBIntelligence Gold builder. The `net_cash_provided_by_operating_activities` column is also available if the Gold builder prefers the explicit name.

> **Question Q5**: Does the SBIntelligence Gold builder for `fact_fundamentals` already reference the specific column name from Silver? If not, confirm which of `operating_cash_flow` or `net_cash_provided_by_operating_activities` will be used so we can ensure the Silver column name is stable.

**Answer**: Use `operating_cash_flow` and create a note to add this information to SBIntelligence.

---

### Finding F4 — Quarterly Balance Sheet and Cashflow Discriminators: Verify Completeness

**Severity**: Medium — verify that quarterly variants exist for all three statement types.

**What we know**: The YAML explorer confirmed `income_statement` has both `FY` and `quarter` discriminators. The `balance_sheet_statement` and `cashflow_statement` entries appear to follow the same pattern (same domain, same cadence approach), but this was not explicitly verified for all three.

**Action**: Run the following verification against the keymap:

```bash
grep -A5 "dataset: balance-sheet-statement" config/dataset_keymap.yaml | grep discriminator
grep -A5 "dataset: cashflow-statement" config/dataset_keymap.yaml | grep discriminator
```

Expected output for each: two entries — `discriminator: 'FY'` and `discriminator: 'quarter'`.

> **Question Q6**: Are balance-sheet-statement and cashflow-statement configured with both FY and quarterly discriminators in the YAML? If not, which is missing?

**Answer**: validate FY and quarterly discriminators in the YAML and code.

---

### Finding F5 — Historical Coverage Depth for 32-Quarter Lookbacks

**Severity**: High — blocks `features.fcf_quality.fcf_positive_pct_8y` and `features.value_durability` (32Q required).

**What SBIntelligence needs**: `fcf_positive_pct_8y` requires 32 eligible quarterly cashflow rows per ticker. `value_durability_min_quarters` for large cap is 32 quarters (8 years). This means SBFoundation must have quarterly cashflow data back to approximately Q1 2018 for a 2026 computation.

**What SBFoundation currently has**: Unknown — the ingestion history determines coverage depth. The YAML `from_date` for each ticker comes from `RunDataDatesDTO` (stored watermarks) or `universe.from_date`.

**Verification query**:
```sql
-- Check minimum and median quarterly cashflow coverage per ticker
SELECT
    MIN(date) AS earliest_quarter,
    MAX(date) AS latest_quarter,
    COUNT(DISTINCT date) AS quarter_count,
    COUNT(DISTINCT ticker) AS ticker_count
FROM silver.fmp_cashflow_statement
WHERE period = 'Q'  -- or period = 'quarter' — verify value
  AND ticker IN ('AAPL', 'MSFT', 'GOOGL');

-- Distribution: how many tickers have >= 32 quarterly rows?
SELECT
    CASE
        WHEN quarter_count >= 32 THEN '32+ quarters (8Y ready)'
        WHEN quarter_count >= 20 THEN '20-31 quarters (5-7Y)'
        WHEN quarter_count >= 8  THEN '8-19 quarters (2-5Y)'
        ELSE '< 8 quarters'
    END AS coverage_tier,
    COUNT(*) AS ticker_count
FROM (
    SELECT ticker, COUNT(*) AS quarter_count
    FROM silver.fmp_cashflow_statement
    WHERE period = 'Q'
    GROUP BY ticker
) t
GROUP BY 1
ORDER BY 1;
```

> **Question Q7**: What is the actual `from_date` configured in the universe for historical backfill? Has a full historical backfill been run to capture pre-2020 quarterly data for S&P 500 constituents?
> **Question Q8**: What is the `period` value stored in `silver.fmp_cashflow_statement` for quarterly rows — is it `'Q'`, `'quarter'`, or something else? (Critical for the PIT filter in feature computations.)

**Answer**:  set the `from_date` to 1990 Jan, 1. Ensure the code allows ingestion of data for missing dates.  Verify YAML and code for cashflow period, ensure annual and quarterly are ingested.

---

### Finding F6 — `company_compensation` DTO Gap

**Severity**: Low — not directly required by the core feature tables, but a data consistency concern.

**What was found**: The YAML lists `company-compensation` as a dataset (silver_table: `fmp_company_compensation`, data_source_path: `governance/executive_compensation`). However, the DTO explorer did not surface a `company_compensation_dto.py` in `src/sbfoundation/dtos/company/`. The company domain has `company_officers_dto.py` which may serve a similar endpoint.

**Impact on this plan**: Not directly consumed by SBIntelligence's core fundamental feature tables. No action required for this ExecPlan.

> **Question Q9**: Is `company-compensation` intentionally sharing the `company_officers_dto.py` DTO, or is there a missing `company_compensation_dto.py`?

**answer**:  Use Executive Compensation API 
Retrieve comprehensive compensation data for company executives with the FMP Executive Compensation API. This API provides detailed information on salaries, stock awards, total compensation, and other relevant financial data, including filing details and links to official documents.

Endpoint: https://financialmodelingprep.com/stable/governance-executive-compensation?symbol=AAPL
Documentation: https://site.financialmodelingprep.com/developer/docs#executive-compensation

Ensure the YAML and code ingest this endpoint as part of the company domain.

---

## Finding §0.1 — Universe Definition Support in RunCommand

**Severity**: Medium — enables callers to run ingestion scoped to a named universe (e.g. `US_LARGE_CAP`) without manually specifying exchanges, countries, and market-cap bounds.

**Source**: `SBIntelligence/docs/prompts/strats/exec_plan_core_fundamental_features.md §0.1`

**What SBIntelligence defines** (`UniverseDefinition`):
```python
@dataclass(frozen=True)
class UniverseDefinition:
    name: str
    country: str
    exchanges: list[str]
    min_market_cap_usd: float
    max_market_cap_usd: float | None    # None = no upper bound
    min_instruments_per_sector: int     # strategy-level — NOT in SBFoundation
    rebalance_months: list[int]         # strategy-level — NOT in SBFoundation
```

**SBFoundation subset** (ingestion-relevant fields only):
```python
@dataclass(frozen=True)
class UniverseDefinition:
    name: str
    country: str
    exchanges: list[str]
    min_market_cap_usd: float
    max_market_cap_usd: float | None
```

**Registered universes** (mirroring SBIntelligence §0.1):

| Name | Exchanges | Market Cap Range |
|------|-----------|-----------------|
| `us_large_mid_cap` | NYSE, NASDAQ | $2B+ |
| `us_large_cap` | NYSE, NASDAQ | $10B+ |
| `us_mid_cap` | NYSE, NASDAQ, AMEX | $2B–$10B |
| `us_small_mid_cap` | NYSE, NASDAQ, AMEX | $500M–$10B |
| `us_small_cap` | NYSE, NASDAQ, AMEX | $300M–$2B |
| `us_all_cap` | NYSE, NASDAQ, AMEX | $300M+ |

**Design decisions** (confirmed with user 2026-02-24):
- `UniverseDefinition` lives in `src/sbfoundation/universe_definitions.py` (not `settings.py`)
- SBFoundation's `UniverseDefinition` is ingestion-fields only; SBIntelligence extends it with strategy fields
- When `RunCommand.universe_definition` is set, its `exchanges` and `country` **replace** `RunCommand.exchanges` / `RunCommand.countries`; `sectors`/`industries` still apply independently
- Market cap filter applied via SQL JOIN to `silver.fmp_company_market_cap` (latest date per ticker) in `UniverseRepo.get_filtered_tickers()`

**Files to change**:
- `src/sbfoundation/universe_definitions.py` — **NEW**
- `src/sbfoundation/api.py` — `RunCommand` + `_get_filtered_universe()`
- `src/sbfoundation/services/universe_service.py` — `get_filtered_tickers()`
- `src/sbfoundation/infra/universe_repo.py` — `get_filtered_tickers()` SQL
- `tests/unit/services/test_universe_filtered_tickers.py` — new test cases

---

## Plan of Work

1. **Resolve Q1/Q2 (outstanding_shares)** — Determine the right ingestion path. If FMP has a dedicated endpoint, add the dataset to `config/dataset_keymap.yaml` and create a new DTO. If quarterly income statement proxy is acceptable, document this as a Gold builder concern and skip new ingestion.

2. **Add quarterly key_metrics (F2)** — Add `discriminator: quarter` variant to keymap for `key-metrics` dataset. Verify same Silver table accepts both FY and quarterly rows via UPSERT on `[ticker, date, period]`. Run test ingestion for a sample ticker.

3. **Verify quarterly balance_sheet and cashflow discriminators (F4)** — Run grep verification. If missing, add the quarterly discriminator entries to the keymap following the same pattern as `income-statement`.

4. **Run historical coverage audit (F5)** — Execute the SQL coverage audit against the live DuckDB. Document the results in Artifacts. If coverage is insufficient, determine and execute a backfill strategy.

5. **Confirm column name alignment (F3)** — Coordinate with SBIntelligence to confirm Gold builder will use `operating_cash_flow` from Silver cashflow table.

6. **Update CLAUDE.md** — If new datasets are added (outstanding_shares endpoint), update CLAUDE.md Section 5.3 with the new dataset entry.

---

## Concrete Steps

### Step 1: YAML verification for quarterly statements

```bash
grep -B2 -A10 "dataset: balance-sheet-statement" config/dataset_keymap.yaml | grep -E "discriminator|dataset:"
grep -B2 -A10 "dataset: cashflow-statement" config/dataset_keymap.yaml | grep -E "discriminator|dataset:"
grep -B2 -A10 "dataset: key-metrics" config/dataset_keymap.yaml | grep -E "discriminator|dataset:"
```

### Step 2: Coverage audit (run against live DuckDB)

```sql
-- Quarterly cashflow coverage
SELECT
    CASE WHEN q >= 32 THEN '32+' WHEN q >= 20 THEN '20-31' WHEN q >= 8 THEN '8-19' ELSE '<8' END AS tier,
    COUNT(*) AS tickers
FROM (
    SELECT ticker, COUNT(*) AS q
    FROM silver.fmp_cashflow_statement
    WHERE period IN ('Q', 'quarter', 'quarterly')  -- check all possible values
    GROUP BY ticker
) t GROUP BY 1 ORDER BY 1;

-- Verify period column values actually used
SELECT DISTINCT period FROM silver.fmp_cashflow_statement LIMIT 20;

-- Key metrics quarterly check
SELECT DISTINCT period FROM silver.fmp_key_metrics LIMIT 20;
```

### Step 3: Add quarterly key_metrics to keymap (after Q3/Q4 answered)

After confirming FMP supports quarterly key_metrics:
1. Add new YAML entry in `config/dataset_keymap.yaml` under `key-metrics` with `discriminator: quarter` and `query_vars: {symbol: __ticker__, period: quarter, from: __from_date__, to: __to_date__}`
2. No DTO changes needed — `KeyMetricsDTO` already handles both periods
3. Run test: `python -m sbfoundation [or however API is invoked] --domain fundamentals --datasets key-metrics`
4. Verify: `SELECT DISTINCT period FROM silver.fmp_key_metrics` shows both `FY` and `Q` (or quarterly equivalent)

### Step 4: Verify outstanding_shares option (after Q1/Q2 answered)

If FMP has `shares-outstanding` endpoint:
```bash
# Test FMP endpoint manually
curl "https://financialmodelingprep.com/stable/shares-outstanding?symbol=AAPL&apikey=$FMP_API_KEY" | head -100
```

If response is valid:
1. Add new keymap entry: `domain: company`, `dataset: shares-outstanding`, `silver_table: fmp_shares_outstanding`, `key_cols: [ticker, date]`
2. Create new DTO `src/sbfoundation/dtos/company/shares_outstanding_dto.py`
3. Add to `settings.py` DATASETS constant

---

## Validation and Acceptance

### Phase 1
- [x] All three statement types (income, balance, cashflow) have both `FY` and `quarterly` discriminators in keymap ✅
- [x] `key_metrics` quarterly discriminator added to keymap ✅
- [x] Outstanding shares path resolved: `company-shares-float` dataset exists ✅
- [ ] Coverage audit shows ≥ 80% of S&P 500 tickers have 32+ quarterly cashflow rows — **requires backfill run**
- [x] Period values confirmed: `Q1`, `Q2`, `Q3`, `Q4` ✅
- [x] `operating_cash_flow` column name confirmed ✅
- [x] All Phase 1 changes compile/pass unit tests (337 passing) ✅

### Phase 2 (§0.1 Universe Definitions)
- [x] `universe_definitions.py` exists with all 6 `UniverseDefinition` instances and `UNIVERSE_REGISTRY` ✅
- [x] `RunCommand(universe_definition=US_LARGE_CAP)` correctly sets exchanges=["NYSE","NASDAQ"], country="US", min_market_cap=$10B ✅
- [x] When `universe_definition` is set, `exchanges`/`countries` on the command are replaced; `sectors`/`industries` still apply ✅
- [x] `UniverseRepo.get_filtered_tickers()` applies market cap bounds via CTE+JOIN to `silver.fmp_company_market_cap` ✅
- [x] All Phase 2 changes compile/pass unit tests (344 passing) ✅

---

## Questions Summary

| # | Question | Blocking |
|---|----------|---------|
| Q1 | Does FMP's API provide a historical `shares-outstanding` endpoint? | F1 |
| Q2 | Is daily granularity of outstanding_shares required, or is quarterly `weighted_average_shs_out` acceptable? | F1 |
| Q3 | Should quarterly discriminator also be added for `metric-ratios`? | F2 (scope) |
| Q4 | What `min_age_days` should the quarterly `key_metrics` use — 45 or 90? | F2 |
| Q5 | Which column name will the SBIntelligence Gold builder use: `operating_cash_flow` or `net_cash_provided_by_operating_activities`? | F3 |
| Q6 | Are balance-sheet-statement and cashflow-statement already configured with quarterly discriminators? | F4 |
| Q7 | What `from_date` is configured for historical backfill? Has 8-year history been loaded? | F5 |
| Q8 | What is the exact string value of `period` in Silver quarterly rows — `'Q'`, `'quarter'`, or other? | F5 |
| Q9 | Is `company_compensation` intentionally sharing `company_officers_dto.py`, or is the DTO missing? | F6 (low priority) |

---

## Interfaces and Dependencies

### SBFoundation Silver Tables Required by SBIntelligence

| Silver Table | Required Columns | Quarterly Data Needed? | Status |
|--------------|-----------------|----------------------|--------|
| `silver.fmp_income_statement` | `ticker`, `date`, `period`, `filing_date`, `revenue`, `gross_profit`, `operating_income`, `net_income`, `interest_expense`, `weighted_average_shs_out` | Yes — `period IN ('Q', 'quarter')` | ✅ Likely complete |
| `silver.fmp_balance_sheet_statement` | `ticker`, `date`, `period`, `filing_date`, `total_current_assets`, `total_current_liabilities`, `cash_and_cash_equivalents`, `total_assets`, `total_equity`, `total_debt` | Yes | ✅ Likely complete |
| `silver.fmp_cashflow_statement` | `ticker`, `date`, `period`, `filing_date`, `free_cash_flow`, `operating_cash_flow` (or `net_cash_provided_by_operating_activities`) | Yes | ✅ Likely complete (verify col name) |
| `silver.fmp_key_metrics` | `ticker`, `date`, `period`, `ev_to_ebitda`, `ev_to_sales`, `market_cap` | Yes | ✅ Quarterly discriminator added to keymap; backfill needed |
| `silver.fmp_company_shares_float` | `ticker`, `outstanding_shares`, `float_shares`, `free_float` | Snapshot | ✅ Dataset + DTO already existed |
| `silver.fmp_company_market_cap` | `ticker`, `date`, `market_cap` | Daily (historical) | ✅ Present |

---

## Artifacts and Notes

### Coverage Audit — 2026-02-23

**DuckDB: Silver quarterly period values** (confirmed via `SELECT DISTINCT period`):
- `silver.fmp_cashflow_statement`: `FY`, `Q1`, `Q2`, `Q3`, `Q4`
- `silver.fmp_income_statement`: `FY`, `Q1`, `Q2`, `Q3`, `Q4`
- `silver.fmp_key_metrics`: `FY` only (quarterly ingestion not yet run)

**SBIntelligence filter clause**: Use `period IN ('Q1','Q2','Q3','Q4')` not `period = 'Q'`

**Quarterly cashflow coverage distribution** (2026-02-23):
```
<8 quarters  | 500 tickers (100%)
```
AAPL: 5 quarters, earliest=2024-12-28, latest=2025-12-27

**Root cause**: Initial ingestion started ~Feb 2026 with `limit=5` (5 most recent records).
**Fix**: Run with `force_from_date="1990-01-01"` for fundamentals domain to backfill history.

### Backfill Command

```python
from sbfoundation.api import SBFoundationAPI, RunCommand
from sbfoundation.settings import FUNDAMENTALS_DOMAIN

api = SBFoundationAPI()
run = api.run(RunCommand(
    domain=FUNDAMENTALS_DOMAIN,
    enable_bronze=True,
    enable_silver=True,
    concurrent_requests=10,
    force_from_date="1990-01-01",
))
```
