# Moat Score — Feature Development Execution Plan

**Version**: 1.5
**Last Updated**: 2026-03-14
**Status**: COMPLETE — validated 2026-03-14; moved to `docs/completed/`
**Depends on**: `moat-score-data-ingestion-exec-plan.md` (must be complete before starting)
**Produces**: `gold.fact_moat_annual` populated with per-pillar sub-scores and composite moat score

---

## Corrections from Data Ingestion Review (v1.2)

The following issues were identified by cross-referencing this plan against the completed `moat-score-data-ingestion-exec-plan.md` (v1.9). All corrections are applied inline below.

| # | Severity | Issue | Correction |
|---|---|---|---|
| 1 | 🔴 | `gold.fact_key_metrics_annual` referenced in 3 places — this table does not exist | Key metrics columns (incl. `roic`) are merged into `gold.fact_annual` via optional LEFT JOIN in `GoldFactService._build_fact_annual()`. All references updated. |
| 2 | 🔴 | `revenue_per_employee` and `asset_turnover` listed as Gold inputs but absent from FMP bulk CSV | These must be **computed** in `MoatFeatureService`: `asset_turnover_f = revenue / total_assets` (from `fact_annual`); `rev_per_employee_f = revenue / full_time_employees` (joining `dim_company.full_time_employees`). |
| 3 | 🟡 | Computed ratio formulas not documented (e.g., `fcf_margin`, `deferred_rev_pct`, `sm_pct`) | Formulas added inline in Phase 2 and the pillar definitions. |
| 4 | 🟢 | `fact_eod` placeholder `_f` columns (`momentum_1m_f`, `volatility_30d_f`, etc.) not addressed | These are populated by a separate EOD feature step (Phase 2.5). Added to Progress and Phase 2. |
| 5 | 🟡 | Phase 3 step 6 wires moat into `annual_flow` after "`fact_annual + fact_key_metrics_annual`" | Corrected to `fact_annual` only. |

---

## Benchmarking Approach (Reference)

**Use FMP `industry` as the primary peer group, falling back to `sector` when n < 10.**

The full benchmark hierarchy:

1. **Primary**: FMP `industry` — the main cross-sectional peer group (target n ≥ 10)
2. **Fallback**: FMP `sector` — when industry peer count < 10
3. **Self-baseline**: Company's own trailing 5-year median — for trend and persistence signals
4. **Global scope**: All FMP-covered tickers regardless of exchange

`sector_sk` and `industry_sk` are available in `gold.dim_company` — no additional joins needed.

---

## Progress

- [x] Phase 2.1 — Implement `MoatFeatureService` skeleton (`src/sbfoundation/gold/moat_feature_service.py`)
- [x] Phase 2.2 — Implement `compute_wacc()` (inline DuckDB SQL in `raw` CTE)
- [x] Phase 2.3 — Implement per-pillar `compute_sub_scores()` (inline SQL in `scored` CTE)
- [x] Phase 2.4 — Implement `compute_moat_score()` (weighted composite in final SELECT)
- [x] Phase 2.5 — Implement EOD momentum and volatility features (`src/sbfoundation/gold/eod_feature_service.py`)
- [x] Phase 3.1 — `MoatFeatureService.build()` writes `gold.fact_moat_annual` (UPSERT)
- [x] Phase 3.2 — Wired into `SBFoundationAPI._promote_gold()` in `api.py`
- [x] Phase 3.3 — Add moat score to coverage dashboard
- [x] Phase 4.1 — Write `src/services/moat_score_validation.py`

---

## Part A — Six Pillar Definitions (Reference)

These are the six moat pillars computed by `MoatFeatureService`. All inputs come from Gold tables built by the data ingestion plan.

| Pillar | Sub-score column | Primary inputs |
|--------|-----------------|----------------|
| 1 — Excess Profitability vs Capital Cost | `profitability_s` | `fact_annual.{interest_expense, income_tax_expense, roic}` (roic merged from key_metrics_bulk), `silver.fred_dgs10` (Rf), `silver.fmp_market_risk_premium` (ERP by country), `dim_company.{beta, country}` |
| 2 — Profit and Cash-Flow Durability | `stability_s` | `fact_annual.{gross_profit, operating_income, free_cash_flow, revenue}`, `silver.fred_usrecm` |
| 3 — Market Power and Competitive Position | `competitive_s` | `fact_annual.revenue`, cross-sectional by `industry_sk` |
| 4 — Switching Costs and Customer Lock-In | `lock_in_s` | `fact_annual.{deferred_revenue, selling_general_and_administrative_expenses, research_and_development_expenses, revenue}` |
| 5 — Structural Cost Advantage | `cost_advantage_s` | `fact_annual.{revenue, gross_profit, total_assets, selling_general_and_administrative_expenses}`; **computed**: `asset_turnover_f = revenue / total_assets`; `rev_per_employee_f = revenue / dim_company.full_time_employees` |
| 6 — Innovation and Intangible Reinvestment | `reinvestment_s` | `fact_annual.{research_and_development_expenses, goodwill_and_intangible_assets, total_assets, revenue}` |

---

## Part B — Gold Schema: `gold.fact_moat_annual`

One row per `(instrument_sk, calendar_year)`. All feature columns end in `_f`. All signal/score columns end in `_s`. Features are winsorized at 1st/99th percentile and z-score normalized within industry group (with sector fallback).

```sql
CREATE TABLE gold.fact_moat_annual (
    instrument_sk                    INTEGER NOT NULL,
    calendar_year                    INTEGER NOT NULL,
    industry_peer_n                  INTEGER,    -- peer count used for normalization
    benchmark_level                  VARCHAR,    -- 'industry' or 'sector' (fallback flag)

    -- Pillar 1: Excess Profitability vs Capital Cost
    roic_f                           DOUBLE,     -- ROIC (winsorized, industry z-score)
    wacc_f                           DOUBLE,     -- estimated WACC (raw, not normalized)
    roic_spread_f                    DOUBLE,     -- ROIC − WACC (winsorized, industry z-score)
    roic_spread_5y_mean_f            DOUBLE,     -- 5Y mean of spread (persistence)
    roic_spread_trend_f              DOUBLE,     -- slope of spread over 5Y (trend)
    profitability_s                  DOUBLE,     -- composite sub-score [0–1]

    -- Pillar 2: Profit and Cash-Flow Durability
    gross_margin_f                   DOUBLE,
    operating_margin_f               DOUBLE,
    fcf_margin_f                     DOUBLE,
    margin_volatility_f              DOUBLE,     -- StdDev of operating margin over 5Y (lower = better, inverted)
    revenue_recession_resilience_f   DOUBLE,     -- revenue drawdown in USRECM years (inverted)
    stability_s                      DOUBLE,

    -- Pillar 3: Market Power and Competitive Position
    revenue_growth_f                 DOUBLE,     -- YoY revenue growth (industry z-score)
    gross_margin_vs_industry_f       DOUBLE,     -- gross margin percentile within industry
    operating_margin_vs_industry_f   DOUBLE,     -- operating margin percentile within industry
    competitive_s                    DOUBLE,

    -- Pillar 4: Switching Costs and Customer Lock-In
    deferred_rev_pct_f               DOUBLE,     -- deferred_revenue / revenue (industry z-score)
    sm_pct_f                         DOUBLE,     -- (SG&A − R&D) / revenue (lower → better efficiency, inverted)
    lock_in_s                        DOUBLE,

    -- Pillar 5: Structural Cost Advantage
    cogs_ratio_f                     DOUBLE,     -- COGS / revenue (inverted, industry z-score)
    sga_ratio_f                      DOUBLE,     -- SG&A / revenue (inverted, industry z-score)
    asset_turnover_f                 DOUBLE,     -- revenue / total_assets (industry z-score)
    rev_per_employee_f               DOUBLE,     -- revenue / headcount (industry z-score)
    cost_advantage_s                 DOUBLE,

    -- Pillar 6: Innovation and Intangible Reinvestment
    rd_pct_f                         DOUBLE,     -- R&D / revenue (industry z-score)
    intangibles_pct_f                DOUBLE,     -- goodwill_and_intangibles / total_assets
    incremental_roic_f               DOUBLE,     -- ΔNOPAT / ΔIC (rolling 3Y, industry z-score)
    reinvestment_s                   DOUBLE,

    -- Composite Moat Score
    moat_score_s                     DOUBLE,     -- weighted composite score [0–1] (signal, not feature — ends in _s)

    gold_build_id                    INTEGER,
    model_version                    VARCHAR,
    updated_at                       TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (instrument_sk, calendar_year)
);
```

**Composite weights**:

| Sub-score | Weight | Rationale |
|---|---|---|
| `profitability_s` | 30% | Foundation — without excess returns there is no moat |
| `stability_s` | 25% | Persistence evidence — moat must hold through cycles |
| `competitive_s` | 15% | Market position confirms the spread |
| `cost_advantage_s` | 15% | Explains persistence via structural advantage |
| `lock_in_s` | 10% | Customer embeddedness (data sparse for non-SaaS) |
| `reinvestment_s` | 5% | Forward indicator — lowest confidence, lowest weight |

---

## Part C — Implementation Phases

### Phase 2 — Moat Feature Service (qs-learn)

**File**: `src/services/moat_feature_service.py`

> **DuckDB-first rule**: All feature calculations that can be expressed as SQL **must** be implemented as DuckDB SQL executed via `duckdb.DuckDBPyConnection`. This includes ratio computations, window-function aggregations (rolling averages, LAG-based returns), cross-sectional percentile/rank/z-score calculations, and MERGE writes. Pull data into Python/pandas only for logic that cannot be expressed in SQL (e.g., iterative WACC solver, external model calls). Never load a full Gold table into a pandas DataFrame just to apply a row-wise formula.

1. Implement `MoatFeatureService` skeleton:
   - Reads from `gold.fact_annual` (includes key metrics and ratios merged via LEFT JOIN), `gold.dim_company`, `silver.fred_dgs10`, `silver.fred_usrecm`, `silver.fmp_market_risk_premium`
   - `gold.fact_key_metrics_annual` does NOT exist — key metrics are in `gold.fact_annual` (columns from `fmp_key_metrics_bulk_annual` merged in `GoldFactService._build_fact_annual()`)
   - Produces a DataFrame at `(instrument_sk, calendar_year)` grain

2. Implement `MoatFeatureService.compute_wacc()`:
   ```
   WACC = (E/V) × (rf + β × ERP) + (D/V) × (interest_expense / total_debt) × (1 − tax_rate)
   ```
   - `rf` = FRED DGS10 annual average for the calendar year (not point-in-time, to avoid noise)
   - `β` = `dim_company.beta`
   - `ERP` = `silver.fmp_market_risk_premium.total_equity_risk_premium / 100` for the company's country of domicile (`dim_company.country`); fall back to `United States` if country not found
   - `tax_rate` = `income_tax_expense / income_before_tax` (floor at 0, cap at 0.5)

3. Implement `MoatFeatureService.compute_sub_scores()` — one method per pillar. Key derived formulas:
   - `roic_f` = `fact_annual.roic` (pre-computed by FMP, available in `fact_annual`)
   - `fcf_margin_f` = `free_cash_flow / revenue`
   - `gross_margin_f` = `gross_profit / revenue`
   - `operating_margin_f` = `operating_income / revenue`
   - `deferred_rev_pct_f` = `deferred_revenue / revenue`
   - `sm_pct_f` = `(selling_general_and_administrative_expenses - research_and_development_expenses) / revenue`
   - `cogs_ratio_f` = `(revenue - gross_profit) / revenue`
   - `sga_ratio_f` = `selling_general_and_administrative_expenses / revenue`
   - `asset_turnover_f` = `revenue / total_assets` (**computed** — not in FMP bulk CSV)
   - `rev_per_employee_f` = `revenue / dim_company.full_time_employees` (**computed** — `full_time_employees` from `dim_company`, which sources from `silver.fmp_company_profile`)
   - `rd_pct_f` = `research_and_development_expenses / revenue`
   - `intangibles_pct_f` = `goodwill_and_intangible_assets / total_assets`
   - Winsorize, normalize, scale, and invert entirely in DuckDB SQL using window functions (`PERCENTILE_CONT`, `AVG() OVER`, `STDDEV() OVER` partitioned by `industry_sk` / `sector_sk`)
   - Winsorize each raw feature at 1st/99th percentile within the industry cohort
   - Z-score normalize within industry cohort (fallback to sector if `industry_peer_n < 10`)
   - Scale to [0–1] via `(z + 3) / 6` (clips beyond 3σ)
   - Invert features where lower is better (COGS ratio, SG&A ratio, margin volatility, etc.)
   - Aggregate component features to sub-score using equal weighting within pillar

4. Implement `MoatFeatureService.compute_moat_score()`:
   - Weighted average of 6 sub-scores using weights from Part B
   - Returns `moat_score_s` in [0–1] (this is a score/signal — suffix is `_s`, not `_f`)

### Phase 2.5 — EOD Feature Columns (populate `fact_eod` placeholder `_f` columns)

`gold.fact_eod` already contains placeholder columns (`momentum_1m_f`, `momentum_3m_f`, `momentum_6m_f`, `momentum_12m_f`, `volatility_30d_f`) which are always NULL until this phase runs.

**File**: `src/services/eod_feature_service.py`

Implement `EodFeatureService` to compute and backfill these columns:

- `momentum_1m_f` = `adj_close / LAG(adj_close, 21) - 1` (21 trading days ≈ 1 month)
- `momentum_3m_f` = `adj_close / LAG(adj_close, 63) - 1`
- `momentum_6m_f` = `adj_close / LAG(adj_close, 126) - 1`
- `momentum_12m_f` = `adj_close / LAG(adj_close, 252) - 1`
- `volatility_30d_f` = rolling 30-day annualized std dev of daily log returns (`STDDEV(LN(adj_close / LAG(adj_close))) OVER (PARTITION BY instrument_sk ORDER BY date ROWS 29 PRECEDING) * SQRT(252)`)

Updates are MERGEd into `gold.fact_eod` on `(instrument_sk, date_sk)` via a single DuckDB SQL `UPDATE ... FROM (SELECT ... window functions ...)` — no Python loop, no pandas. This is the required pattern for all EOD feature columns.

### Phase 3 — Gold Population & Orchestration

5. Add `MoatFactService` to SBFoundation (or invoke `MoatFeatureService` from qs-learn as a post-Gold step):
   - Reads computed DataFrame from `MoatFeatureService`
   - MERGEs into `gold.fact_moat_annual` keyed on `(instrument_sk, calendar_year)`
   - Writes `ops.gold_build` log entry

6. Wire into `annual_flow` Prefect flow:
   - Run after `GoldFactService` completes `fact_annual` (key metrics are already merged into `fact_annual` — there is no separate `fact_key_metrics_annual`)
   - Confirm ordering: dims → `fact_annual` → moat scores

7. Add `moat_score_s` and `profitability_s` to the coverage dashboard.

### Phase 4 — Validation Script

8. Write `src/services/moat_score_validation.py` (runnable as `python -m services.moat_score_validation`):
   - Distribution checks for each `_f` column (should be approximately normal after normalization) — print min/max/mean/stddev/null-count per column
   - Rank correlation between `moat_score_s` and forward 1-year returns (sanity check) — print Spearman ρ
   - Quintile analysis: top vs bottom `moat_score_s` quintile by sector — print mean forward return per quintile
   - Comparison of `wacc_f` vs industry-published estimates (Damodaran tables) — print out-of-range tickers
   - Identify symbols with implausible WACC values (negative tax rate, beta < 0) — print flagged tickers
   - All queries executed in DuckDB SQL; results printed to stdout in tabular form (use `tabulate` or `duckdb`'s built-in `.fetchdf().to_string()`)

---

## Validation and Acceptance

### Tier 1 — Quick checks

```bash
# Service imports cleanly
python -c "from services.moat_feature_service import MoatFeatureService; print('OK')"
python -c "from sbfoundation.gold.moat_fact_service import MoatFactService; print('OK')"

# mypy passes on new files
mypy src/services/moat_feature_service.py
```

### Tier 2 — DB checks

```python
import duckdb
con = duckdb.connect("path/to/dev.duckdb")

# Migration applied
con.execute("SELECT COUNT(*) FROM gold.fact_moat_annual").fetchone()

# Columns exist
con.execute("DESCRIBE gold.fact_moat_annual").fetchdf()

# No nulls on composite score where data is available
con.execute("""
    SELECT COUNT(*) FROM gold.fact_moat_annual
    WHERE moat_score_s IS NULL AND industry_peer_n >= 10
""").fetchone()  -- expect 0

# Sub-score range sanity
con.execute("""
    SELECT MIN(moat_score_s), MAX(moat_score_s),
           MIN(profitability_s), MAX(profitability_s)
    FROM gold.fact_moat_annual
""").fetchone()  -- all values in [0, 1]
```

### Tier 3 — Integration / dry-run check

```bash
# Run moat computation without writing (dry-run)
python -m sbfoundation.api build_moat --dry_run=true --calendar_year=2023

# Confirm log output shows:
# - industry peer counts loaded
# - WACC computed for sample tickers (AAPL, MSFT, BA)
# - moat_score_s in [0, 1] for top 10 tickers printed to stdout
```

### Tier 4 — Post-live-run checks

1. `gold.fact_moat_annual` has rows for all tickers in universe for at least the last 3 calendar years
2. AAPL has `profitability_s > 0.6` (known high ROIC company)
3. `benchmark_level = 'sector'` appears in < 20% of rows (most industries have n ≥ 10)
4. Re-running the same calendar year produces identical `moat_score_s` values (idempotency)
5. WACC values for US large-caps fall between 6–12% (cross-check vs Damodaran sector averages)
6. `gold.fact_eod` `_f` columns (`momentum_1m_f`, `volatility_30d_f`, etc.) are non-NULL for at least 252 trailing rows per instrument (requires 1 year of EOD history)

---

## Outcomes & Retrospective

**Status**: Complete — validated by user on 2026-03-14.

**What was achieved**:
- `MoatFeatureService` implemented in `src/sbfoundation/gold/moat_feature_service.py` — all six moat pillars computed in DuckDB SQL with winsorization, z-score normalization, industry/sector fallback, and composite `moat_score_s` weighting
- `EodFeatureService` implemented in `src/sbfoundation/gold/eod_feature_service.py` — momentum (1m/3m/6m/12m) and volatility (30d) columns backfilled into `gold.fact_eod` via single DuckDB UPDATE
- Gold schema migration `20260312_005_create_gold_fact_moat_annual.sql` adds `gold.fact_moat_annual`
- Migration `20260312_004_rename_fact_eod_feature_columns.sql` aligns `_f` column names in `fact_eod`
- Migration `20260312_006_drop_dim_company_instrument_fk.sql` removes stale FK
- `SBFoundationAPI._promote_gold()` wired to invoke moat feature computation after Gold fact build
- Coverage CLI updated to report moat score coverage
- `src/services/moat_score_validation.py` written for distribution, WACC, and quintile sanity checks

**Gaps / follow-on work**:
- Tier 4 live-run acceptance criteria (post-live checks) deferred to a future backfill run
- EOD feature backfill for full history will require a dedicated scheduled run
