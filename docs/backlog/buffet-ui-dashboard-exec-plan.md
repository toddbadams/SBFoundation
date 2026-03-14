# Warren Buffett-Style Investment Dashboard — Execution Plan

**Version**: 1.1
**Last Updated**: 2026-03-14
**Depends on**: Gold layer fully populated (`fact_eod`, `fact_annual`, `fact_moat_annual`, dims)
**Produces**: A Streamlit dashboard modelled on Warren Buffett's investment framework — ticker search, EOD candles, annual financials, economic moat scores, and intrinsic value / margin-of-safety metrics

---

## Purpose / Big Picture

Deliver a single-page Streamlit application that applies Warren Buffett's investment philosophy to any ticker in the universe. A user types a ticker symbol and immediately sees five analytical tabs — EOD, Annual, Segments, Moat, and Valuation — each with a graph/metrics toggle.

**Buffett's framework, operationalised:**

| Buffett Principle | Dashboard Tab | Key Metrics |
|---|---|---|
| Understand the business | Annual | Revenue trend, FCF conversion, capital intensity |
| Durable competitive advantage | Moat | Composite moat score + 6 pillar sub-scores |
| Able and trustworthy management | Annual | ROIC vs WACC, retained-earnings deployment |
| Buy at a sensible price | Valuation | Earnings yield, P/FCF, intrinsic value vs price |
| Long-term ownership mindset | EOD | Price history without noise; focus on multi-year trends |

The app reads exclusively from the Gold DuckDB layer; no Bronze/Silver access and no external API calls at runtime. Every metric displayed should be answerable from Gold SQL — no opaque black boxes.

---

## Progress

- [ ] Phase 0 — Data gap remediation (new tables / feature columns required by UI)
- [ ] Phase 1 — Project scaffolding (`src/sbdashboard/`)
- [ ] Phase 2 — Data access layer (`reader.py` per tab)
- [ ] Phase 3 — Streamlit app skeleton (sidebar + tab layout)
- [ ] Phase 4 — EOD tab (candlestick chart + volume + metrics)
- [ ] Phase 5 — Annual tab (revenue / net income / FCF line charts + metrics)
- [ ] Phase 6 — Segments tab (stacked bar per segment + metrics)
- [ ] Phase 7 — Moat tab (composite score line + pillar radar/bar + metrics)
- [ ] Phase 8 — Valuation tab (per-share metrics over time + key ratios)
- [ ] Phase 9 — Validation and acceptance testing

---

## Data Gap Analysis and Recommendations

This section documents what data is available in the Gold layer today, what gaps exist for each UI tab, and what new tables/columns must be built before Phase 1 begins.

### Tab 1 — EOD

**Available** (`gold.fact_eod` + `gold.dim_date`):
- `open`, `high`, `low`, `close`, `adj_close`, `volume` — sufficient for OHLCV candlestick chart
- `momentum_1m_f`, `momentum_3m_f`, `momentum_6m_f`, `momentum_12m_f`, `volatility_30d_f` — feature metrics

**Gaps**: None for MVP. `vwap`, `change`, `change_pct`, `unadjusted_volume` are schema columns but not yet populated by `GoldFactService` — these can be deferred.

**Verdict**: Ready as-is.

---

### Tab 2 — Annual

**Available** (`gold.fact_annual` + `gold.dim_date`):
- `revenue`, `net_income`, `free_cash_flow` — all present; sufficient for the primary chart
- `gross_profit`, `operating_income`, `ebitda`, `eps`, `eps_diluted`
- `operating_cash_flow`, `capital_expenditure`, `dividends_paid`
- Balance sheet: `total_assets`, `total_liabilities`, `total_stockholders_equity`, `long_term_debt`, `net_debt`
- Extended fields: `research_and_development_expenses`, `selling_general_and_administrative_expenses`, `interest_expense`, `depreciation_and_amortization`, `deferred_revenue`, `goodwill_and_intangible_assets`
- Ratios: `gross_profit_margin`, `operating_profit_margin`, `net_profit_margin`, `debt_ratio`, `interest_coverage`, `roic`, `ev_to_ebitda`, `capex_to_ocf`

**Gaps**: None for MVP. Growth rates (YoY %) are not persisted — compute in DuckDB SQL at query time using `LAG()`.

**Verdict**: Ready as-is.

---

### Tab 3 — Segments

**Available**: Nothing. FMP bulk endpoints aggregate at the company level only.

**Gap**: FMP provides segment-level endpoints:
- `/v4/revenue-product-segmentation?symbol=<ticker>` — revenue by product/service segment
- `/v4/revenue-geographic-segmentation?symbol=<ticker>` — revenue by geography

These are **per-ticker** (not bulk), annual cadence.

**Recommendation — New datasets required (Phase 0.1)**:

| Layer | Item | Detail |
|---|---|---|
| Silver | `silver.fmp_revenue_segment` | Key: `(symbol, date, segment_name)` |
| Silver | `silver.fmp_revenue_geo_segment` | Key: `(symbol, date, region_name)` |
| Gold | `gold.fact_segment_annual` | `(instrument_sk, date_sk, segment_type, segment_name, revenue)` |
| YAML | `revenue-segment` dataset entry | `per_ticker`, annual cadence, `min_age_days: 365` |
| YAML | `revenue-geo-segment` dataset entry | `per_ticker`, annual cadence, `min_age_days: 365` |

**Important**: FMP bulk CSV field names differ from JSON API docs (CLAUDE.md constraint #7). Verify actual field names against Bronze content before writing DTOs.

**Verdict**: **Blocked** until Phase 0.1 data is ingested and promoted. The Segments tab will render a "Data not yet available — check back after next ingestion run" message until `fact_segment_annual` is populated.

---

### Tab 4 — Moat

**Available** (`gold.fact_moat_annual`):
- `moat_score_s` — composite score [0, 1] — sufficient for the primary line chart
- 6 pillar sub-scores: `profitability_s`, `stability_s`, `competitive_s`, `lock_in_s`, `cost_advantage_s`, `reinvestment_s`
- 19 raw feature `_f` columns for drill-down (per-pillar inputs)
- `industry_peer_n`, `benchmark_level`

**Gaps**: No human-readable pillar descriptions — these are static text, not data. They will be hard-coded in the UI layer.

**Verdict**: Ready as-is.

---

### Tab 5 — Valuation

**Available** (partial):
- `ev_to_ebitda` (from `gold.fact_annual.ev_to_ebitda`)
- `roic` (from `gold.fact_annual.roic`)
- `gross_profit_margin`, `operating_profit_margin`, `net_profit_margin` (ratios)
- `wacc_f` (from `gold.fact_moat_annual`) — cost of capital for DCF denominator
- `eps`, `eps_diluted` (per-share earnings)

**Gaps — new `gold.fact_valuation_annual` required (Phase 0.2)**:

The following per-share valuation ratios require joining year-end EOD price (from `fact_eod`) with annual fundamentals (`fact_annual`). These cannot be queried cheaply at runtime without materialising them.

| Column | Formula | Source tables |
|---|---|---|
| `pe_ratio_f` | `year_end_close / eps_diluted` | `fact_eod` (Dec 31 close) + `fact_annual.eps_diluted` |
| `pb_ratio_f` | `market_cap / total_stockholders_equity` | `fact_eod.close * shares` + `fact_annual` |
| `ps_ratio_f` | `market_cap / revenue` | `fact_eod` + `fact_annual.revenue` |
| `pfcf_ratio_f` | `market_cap / free_cash_flow` | `fact_eod` + `fact_annual.free_cash_flow` |
| `earnings_yield_f` | `eps_diluted / year_end_close` | `fact_eod` + `fact_annual` |
| `roe_f` | `net_income / total_stockholders_equity` | `fact_annual` |
| `roa_f` | `net_income / total_assets` | `fact_annual` |
| `fcf_yield_f` | `free_cash_flow / market_cap` | `fact_eod` + `fact_annual` |

**Implementation note**: `fact_eod` does not store shares outstanding — FMP key_metrics has `market_cap` implicitly via EV; alternatively join `dim_company` for market cap via profile. Clarify source for `shares_outstanding` before building `fact_valuation_annual`.

**Simplest MVP path**: compute `roe_f`, `roa_f`, `earnings_yield_f` from `fact_annual` alone (no price join required); compute price ratios only after confirming shares/market-cap source.

**Verdict**: Partially blocked. `roe_f`, `roa_f`, `earnings_yield_f` can ship in MVP from `fact_annual` SQL. Price-based ratios (P/E, P/B, P/S, P/FCF) require Phase 0.2.

---

## Phase 0 — Data Gap Remediation

### Phase 0.1 — Segment Revenue Ingestion (new datasets)

**Work items**:
1. Add `revenue-segment` and `revenue-geo-segment` entries to `config/dataset_keymap.yaml`
2. Write DTOs: `RevenueSegmentDTO`, `RevenueGeoSegmentDTO`
3. Write migration: `gold.fact_segment_annual` with columns `(instrument_sk, date_sk, segment_type, segment_name, revenue, gold_build_id, model_version, updated_at)`
4. Extend `GoldFactService` to build `fact_segment_annual`
5. Add to `SBFoundationAPI` ingestion flow

### Phase 0.2 — Valuation Feature Table

**Work items**:
1. Write migration: `gold.fact_valuation_annual` with all `_f` valuation columns
2. Write `ValuationFeatureService` (SQL-only, joining `fact_annual` + `fact_eod` for year-end price)
3. Wire into `SBFoundationAPI._promote_gold()` after `fact_annual` is built

---

## Context and Orientation

### Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| UI framework | **Streamlit** (`>=1.32`) | Pure Python; trivial DuckDB integration; no JS build step |
| Charting | **Altair** (`>=5`) | Declarative, interactive, native Streamlit support |
| Data access | **DuckDB** (direct) | Same file as Gold layer; zero-copy; SQL pushdown |
| Packaging | Poetry (existing) | Consistent with repo conventions |

### Key files

| Path | Role |
|---|---|
| `src/sbdashboard/app.py` | Streamlit entry point |
| `src/sbdashboard/readers/` | One reader per tab (DuckDB SQL) |
| `src/sbdashboard/charts/` | Altair chart builders |
| `src/sbdashboard/tabs/` | One Streamlit tab module per analytical tab |
| `src/sbfoundation/maintenance/duckdb_bootstrap.py` | DB connection — reuse read_connection() |

---

## Plan of Work

### Phase 1 — Scaffolding

Create `src/sbdashboard/` package with `__init__.py`, `app.py`, and empty `readers/`, `charts/`, `tabs/` sub-packages. Add `streamlit` and `altair` to `pyproject.toml` dependencies.

Entry point: `streamlit run src/sbdashboard/app.py`

### Phase 2 — Data Access Layer

One reader module per tab. Each reader:
- Accepts a `symbol: str` argument
- Opens a DuckDB `read_connection()` via `DuckDbBootstrap`
- Returns a `pd.DataFrame`
- Contains **no business logic** — only SQL

Readers:
- `readers/eod_reader.py` — queries `fact_eod` + `dim_date` + `dim_instrument`
- `readers/annual_reader.py` — queries `fact_annual` + `dim_date` + `dim_instrument`
- `readers/segment_reader.py` — queries `fact_segment_annual` (stub until Phase 0.1)
- `readers/moat_reader.py` — queries `fact_moat_annual` + `dim_instrument`
- `readers/valuation_reader.py` — queries `fact_valuation_annual` (stub until Phase 0.2) + `fact_annual` for MVP ratios

### Phase 3 — App Skeleton

`app.py` layout:
```
st.set_page_config(layout="wide")
sidebar: st.sidebar → st.text_input("Ticker", value="AAPL")
main: st.tabs(["EOD", "Annual", "Segments", "Moat", "Valuation"])
```

Each tab module receives the resolved `symbol` string. If the symbol is not found in `dim_instrument`, show `st.warning("Ticker not found.")`.

### Phase 4 — EOD Tab

Buffett rarely fixates on short-term price moves, but price history anchors intrinsic-value comparisons. This tab is intentionally simple — no intraday noise, no technical indicators.

**Graph mode** (default): Altair layered chart
- Layer 1: OHLCV candlestick (open/high/low/close bars, colored by close > open)
- Layer 2: Volume bar chart on secondary y-axis
- X-axis: `date` from `dim_date`; date range selector (1M / 3M / 1Y / 5Y / All)
- Default view opens at **5Y** to reinforce the long-term ownership mindset

**Metrics mode**: `st.columns` grid showing:
- Latest close, 52-week high/low, avg volume
- Momentum 1M / 3M / 6M / 12M (formatted as % with delta indicator)
- Volatility 30D (annualized)

Toggle: `st.radio("View", ["Graph", "Metrics"], horizontal=True)` in upper-left of tab

### Phase 5 — Annual Tab

Buffett's first filter is understanding whether the business generates growing, predictable earnings and converts them into free cash. This tab surfaces the 10-year earnings and FCF record at a glance.

**Graph mode**: Multi-line Altair chart (revenue, net income, free cash flow) with years on x-axis. Optional YoY % growth line on secondary axis (computed via `LAG()` in SQL). **Default date range: 10 years** — Buffett cares about decade-level trends, not single-year spikes.

**Metrics mode**: Latest year key metrics grid:
- Revenue, Net Income, FCF (absolute + YoY %)
- Gross / Operating / Net margin
- ROIC vs WACC spread (Buffett's single most important capital-allocation metric)
- EV/EBITDA, Debt ratio, Interest coverage

**Buffett signal callout box** (top of tab): coloured badge — `Strong Franchise` / `Developing` / `Commodity` — based on 5-year average ROIC spread above WACC (sourced from `fact_moat_annual.wacc_f` and `fact_annual.roic`).

### Phase 6 — Segments Tab

**Graph mode**: Altair stacked bar chart — segment revenue by year, colored by `segment_name`.

**Metrics mode**: Latest year segment table: segment name, revenue, % of total.

If `fact_segment_annual` is empty for this ticker: show `st.info("Segment data not yet available.")`.

### Phase 7 — Moat Tab

This is the centrepiece of the Buffett dashboard. Buffett's most famous concept — the economic moat — is quantified here across 6 pillars. The tab answers: *"Does this business have a durable competitive advantage, and is it widening or narrowing?"*

**Graph mode**: Altair line chart of `moat_score_s` by year with a horizontal reference line at 0.6 (Buffett's implicit "wide moat" threshold). Optionally overlay all 6 pillar sub-scores as lighter lines.

**Metrics mode**: Latest year pillar breakdown:
- One row per pillar: name, score (formatted 0.00–1.00), description, color-coded bar (red < 0.4, amber 0.4–0.7, green ≥ 0.7)
- Industry peer percentile rank (`industry_peer_n` peers compared)

**Moat verdict badge** (top of tab): `Wide Moat (≥0.70)` / `Narrow Moat (0.50–0.69)` / `No Moat (<0.50)` — Buffett's own language.

**Pillar descriptions** (static, hard-coded in UI — framed in Buffett's vocabulary):
| Pillar | Column | Buffett Question |
|---|---|---|
| Excess Profitability | `profitability_s` | "Does it earn well above its cost of capital, year after year?" |
| Durability | `stability_s` | "Do margins hold up in bad years? Can it survive a recession?" |
| Market Power | `competitive_s` | "Can it raise prices without losing customers?" |
| Lock-in | `lock_in_s` | "Do customers stay because switching is painful?" |
| Cost Advantage | `cost_advantage_s` | "Can competitors undercut it on price and still profit?" |
| Innovation / Reinvestment | `reinvestment_s` | "Does it reinvest wisely — is incremental ROIC growing?" |

### Phase 8 — Valuation Tab (Intrinsic Value & Margin of Safety)

Buffett's golden rule: *"Price is what you pay; value is what you get."* This tab answers: *"Am I paying a fair price for the quality I see in the Moat and Annual tabs?"*

**Graph mode**: Altair line chart of valuation metrics by year. MVP shows `earnings_yield_f`, `roe_f`, `roa_f`. Extended shows `pe_ratio_f`, `pb_ratio_f`, `pfcf_ratio_f` when `fact_valuation_annual` is available.

**Metrics mode**: Latest year grid:
- **Earnings Yield** (Buffett's preferred P/E inverse — compare to 10-yr Treasury from `silver.fred_dgs10`)
- **FCF Yield** (owner earnings per dollar paid)
- **ROE** (Buffett's most-cited single metric)
- **ROA** (asset efficiency)
- P/E, P/B, P/FCF, EV/EBITDA (from `fact_valuation_annual` or `fact_annual.ev_to_ebitda`)

**Margin-of-safety indicator** (top of tab): Simple signal comparing current earnings yield to the risk-free rate (`fred_dgs10`):
- `Earnings yield > 2× risk-free rate` → green badge "Potentially Undervalued"
- `Earnings yield > risk-free rate` → amber badge "Fairly Valued"
- `Earnings yield < risk-free rate` → red badge "Expensive vs Risk-Free"

This is intentionally simple — Buffett himself uses earnings yield vs bond yield as a first-pass filter. The badge is not a buy recommendation; it is a conversation starter.

---

## Concrete Steps

### Step 1 — Branch

```bash
git checkout -b feature/ui-dashboard
```

### Step 2 — Add dependencies

```bash
poetry add streamlit altair
```

Verify `pyproject.toml` updated.

### Step 3 — Scaffold package

```bash
mkdir -p src/sbdashboard/{readers,charts,tabs}
touch src/sbdashboard/__init__.py
touch src/sbdashboard/app.py
touch src/sbdashboard/readers/__init__.py
touch src/sbdashboard/charts/__init__.py
touch src/sbdashboard/tabs/__init__.py
```

### Step 4 — Implement readers (one per tab)

Write SQL in each reader. All queries must:
- Join through `dim_instrument` on `symbol = ?` to resolve `instrument_sk`
- Return an empty `pd.DataFrame` (not raise) if the ticker is unknown

### Step 5 — Implement app skeleton

`app.py` with sidebar ticker input + 5 tabs. Each tab calls its reader and shows a placeholder.

### Step 6 — Implement tab modules (Phases 4–8)

Implement each tab in order: EOD → Annual → Moat (skipping Segments and full Valuation until Phase 0 data is available).

### Step 7 — Phase 0 data remediation (parallel track)

Run Phase 0.1 and 0.2 as a separate sub-plan (see Phase 0 above). Once `fact_segment_annual` and `fact_valuation_annual` are populated, complete Phases 6 and 8.

---

## Validation and Acceptance

### Tier 1 — Quick checks (no DB required)

```bash
# Import sanity
python -c "from sbdashboard.app import main; print('OK')"

# Streamlit help
streamlit run src/sbdashboard/app.py --help
```
Expected: no import errors.

### Tier 2 — DB checks (local DuckDB)

```python
from sbfoundation.maintenance import DuckDbBootstrap
b = DuckDbBootstrap()
with b.read_connection() as conn:
    row = conn.execute("SELECT COUNT(*) FROM gold.fact_moat_annual").fetchone()
    print(row)  # expect non-zero
    row2 = conn.execute("SELECT COUNT(*) FROM gold.fact_eod").fetchone()
    print(row2)  # expect non-zero
b.close()
```

### Tier 3 — Integration / dry-run

```bash
streamlit run src/sbdashboard/app.py
# Type "AAPL" in sidebar — all 5 tabs must render without error
# EOD graph: candlesticks visible for at least 1 year of data
# Annual graph: at least 3 years of revenue line
# Moat metrics: 6 pillar scores displayed
# Segments tab: shows "data not yet available" message (Phase 0.1 pending)
# Valuation tab: shows ROE, ROA, earnings yield; P/E stub shown if fact_valuation_annual absent
```

### Tier 4 — Post-live acceptance criteria

1. At least 500 distinct tickers render EOD graphs without error
2. Annual tab shows ≥ 10 years of data for AAPL, MSFT, GOOGL
3. Moat tab shows scores for ≥ 2 years for any ticker in the universe
4. Toggling graph ↔ metrics on all tabs produces no Streamlit exceptions
5. Entering an unknown ticker shows a warning, not a traceback

---

## Idempotence and Recovery

- The app is read-only — no DuckDB writes at runtime. Restarting is always safe.
- If `fact_valuation_annual` or `fact_segment_annual` do not exist, readers return empty DataFrames and tabs show informational messages — no crash.

---

## Interfaces and Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `streamlit` | `>=1.32` | UI framework |
| `altair` | `>=5.0` | Declarative charts |
| `duckdb` | existing | Gold layer data access |
| `pandas` | existing | DataFrame returned by readers |
| `sbfoundation.maintenance.DuckDbBootstrap` | internal | DB connection |

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-03-14 | Frame dashboard around Warren Buffett's investment philosophy | Gives the metrics context and a clear mental model for the user; Moat, Annual, and Valuation tabs map directly to Buffett's three filters: quality of business, quality of management, price |
| 2026-03-14 | Streamlit over Dash/Flask | Zero JS build overhead; DuckDB integration is trivial; team already Python-native |
| 2026-03-14 | Altair over Plotly | Declarative; handles candlesticks via mark_rule + mark_bar layering; interactive zoom native |
| 2026-03-14 | Default EOD date range = 5Y, Annual = 10Y | Buffett's 10-year earnings record is his standard screening horizon; short-term views are de-emphasised by default |
| 2026-03-14 | Moat verdict badge uses Buffett's own language ("Wide / Narrow / No Moat") | Directly maps to Morningstar moat taxonomy Buffett popularised; intuitive to value investors |
| 2026-03-14 | Margin-of-safety indicator compares earnings yield to `fred_dgs10` | Buffett's own public statements use this comparison ("stocks are cheap when earnings yield > bond yield") |
| 2026-03-14 | Segments tab shows stub until FMP segment data is ingested | FMP bulk endpoints don't provide segments; per-ticker segment API calls require new ingestion pipeline (Phase 0.1) |
| 2026-03-14 | Valuation MVP uses `fact_annual` SQL ratios, not `fact_valuation_annual` | Avoids blocking Phase 8 on Phase 0.2; ROE/ROA/earnings yield computable directly |
| 2026-03-14 | Readers return empty DataFrame rather than raising | Ensures tab renders gracefully for tickers with partial data coverage |
