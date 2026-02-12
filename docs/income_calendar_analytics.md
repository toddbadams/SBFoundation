**Problem**  
You want the “Income Calendar” functionality from DividendTracker—brokerage aggregation, dividend calendars, yield-on-cost, real-time dividend alerts, and forward income projections—baked into your analytics layer so your app can compute, store, and serve these insights reliably across unlimited accounts and holdings.  [oai_citation:0‡dividendtracker.com](https://dividendtracker.com/)

---

# Spec: Dividend “Income Calendar” Analytics (for Todd’s platform)

## 1) Scope & Feature Parity (analytics-layer only)
Replicate the following capabilities as data/compute services your UI can call:

- **Account aggregation** across multiple brokerages; portfolio-level rollups with no hard limits on accounts/holdings.  [oai_citation:1‡dividendtracker.com](https://dividendtracker.com/)  
- **Income calendar generation** (daily → monthly → annual summaries) showing payouts, ex-dates, record/payable dates.  [oai_citation:2‡dividendtracker.com](https://dividendtracker.com/)  
- **Yield on Cost (YoC)** per lot, per position, and portfolio; also current yield.  [oai_citation:3‡dividendtracker.com](https://dividendtracker.com/)  
- **Real-time/near-real-time dividend alerts** for declarations, ex-dates, and upcoming payouts.  [oai_citation:4‡dividendtracker.com](https://dividendtracker.com/)  
- **Forward income projections** using current & historical dividend data; prefer announced amounts when available, otherwise forecast.  [oai_citation:5‡dividendtracker.com](https://dividendtracker.com/)

Out of scope here: pricing, marketing pages, and any UI beyond the API contracts.

---

## 2) Architecture Overview
**Data sources**
- **Brokerage holdings/transactions**: via your existing connectors/CSV loaders; normalize to `Account`, `Position`, `Lot`, `Transaction(Dividend)`.
- **Corporate actions & dividends**: paid provider (e.g., IEX/Polygon/Tiingo/EDI) + your nightly feed; store in `DividendEvent` (declared, ex, record, payable, amount, currency, “special” flag).
- **Prices & FX**: end-of-day prices and FX rates for yield/YoC.
- **Security master**: ticker, ISIN/CUSIP/SEDOL, country, currency, dividend policy hints, pay frequency.

**Storage (Parquet/Lakehouse aligned with your bronze→silver→gold pattern)**
- **bronze**: raw vendor files (dividends, prices, FX), raw brokerage exports.  
- **silver**: cleaned `securities`, `dividend_events`, `prices_eod`, `fx_rates`, `positions`, `lots`.  
- **gold**: analytic marts: `income_calendar_daily`, `income_calendar_monthly`, `income_calendar_annual`, `yield_metrics`, `dividend_projections`, `alerts_outbox`.

**Compute**
- **Batch**: nightly enrichment & projections (default 12-month horizon).  
- **Streaming/near-real-time** (optional): small listener to ingest fresh declarations/ex-date updates and publish alerts.

**Interfaces**
- Python services (or a thin microservice) exposing functions & REST endpoints (see §5).

---

## 3) Data Model (gold highlights)
**Core**
- `securities(security_id, ticker, isin, currency, pay_frequency_hint, sector, …)`
- `dividend_events(security_id, event_type ENUM[declared, ex, record, payable], event_dt, amount, currency, is_special BOOL, source, vendor_event_id, created_at)`
- `positions(account_id, security_id, quantity, cost_basis_ccy, cost_basis_amount, accrual_method, drip_enabled BOOL, updated_at)`
- `lots(lot_id, position_id, open_dt, qty, cost_basis_ccy, cost_basis_amount, fx_at_purchase, corporate_actions_applied JSONB)`
- `prices_eod(security_id, dt, close, currency)`
- `fx_rates(dt, base_ccy, quote_ccy, rate)`
  
**Analytics**
- `dividend_projections(security_id, period_start, period_end, projected_amount_ccy, source ENUM[declared, forecast_model], confidence_pct, notes)`
- `income_calendar_daily(account_id, dt, security_id, shares, amount_ccy, amount_home_ccy, event_type, declared_id?, ex_id?, payable_id?)`
- `yield_metrics(date, security_id, current_yield, yoc_weighted, yoc_lot_min/max/median, payout_ratio?)`
- `alerts_outbox(alert_id, user_id, type ENUM[declaration, ex_date, upcoming_payment], security_id, event_dt, payload JSONB, status ENUM[pending, sent, error])`

All monetary fields tracked in **native currency** and **home currency (GBP)** for Europe/London reporting.

---

## 4) Algorithms & Calculations

### 4.1 Yield on Cost (YoC)
- **Per lot**: `YoC_lot = (Annualized_Dividend_per_Share_native / (Cost_Basis_native / Shares))`
- **Position YoC (weighted)**: share-weighted or cost-weighted across lots.
- **Portfolio YoC**: value-weighted across positions.
- **Current yield**: `Annualized_Div_per_Share / LastPrice`. Use latest announced forward run-rate if available; else trailing 12M normalized (handle specials).  [oai_citation:6‡dividendtracker.com](https://dividendtracker.com/)

### 4.2 Forward Dividend Projection
Priority of sources per security:
1) **Declared future dividends** (amount, currency, payable date) → deterministic.  
2) If none, **model forecast**:
   - Detect **pay frequency**: infer from last 12–24 months (monthly/quarterly/semi/annual); allow issuer overrides.
   - Estimate **next amount**:
     - For stable payers: last regular amount (exclude specials).  
     - For grower patterns: rolling median of last N regulars; apply trend cap (e.g., ±10%).  
     - For variable ETFs: rolling average of last 12 months with seasonality bucket (month-of-year).  
   - Create projected events for next 12 months on expected schedule (approximate ex/payable windows based on historical lags).  
   - Mark `source=forecast_model` and attach `confidence_pct` (coverage heuristics).
This matches the site’s promise of “accurate, realtime dividend projections” from current & historical data.  [oai_citation:7‡dividendtracker.com](https://dividendtracker.com/)

### 4.3 Income Calendars
- **Daily**: generate cashflow rows on payable dates (if record/ex needed for UX, include but don’t cashflow).  
- **Monthly/Annual**: rollups with totals, counts, and top payers. Mirrors “monthly and yearly income summaries.”  [oai_citation:8‡dividendtracker.com](https://dividendtracker.com/)

### 4.4 Alerts
- Trigger on:
  - **New declaration** for a held security.  
  - **Upcoming ex-date** within N days.  
  - **Upcoming payable** within N days.  
- Deduplicate by `(user_id, security_id, event_type, event_dt)`; publish to `alerts_outbox`. Aligns with “real-time dividend alerts.”  [oai_citation:9‡dividendtracker.com](https://dividendtracker.com/)

### 4.5 Brokerage Aggregation
- Support **unlimited** accounts/holdings; no per-account caps in queries or groupings.  [oai_citation:10‡dividendtracker.com](https://dividendtracker.com/)

---

## 5) API / Function Contracts (Python-first)

```python
# Income calendar
get_income_calendar(user_id: str,
                    start: date, end: date,
                    level: Literal["daily","monthly","annual"],
                    group_by: Literal["portfolio","account","security"]="portfolio"
                   ) -> List[CalendarRow]

# Projections
project_dividends(portfolio_id: str,
                  horizon_months: int = 12,
                  include_declared: bool = True,
                  include_forecast: bool = True
                 ) -> List[ProjectedDividend]

# Yield metrics
compute_yield_metrics(date: date, scope: Scope) -> YieldSummary  # scope = portfolio/account/position/lot

# Alerts
list_dividend_alerts(user_id: str, since: datetime) -> List[Alert]
subscribe_dividend_alerts(user_id: str, prefs: AlertPrefs) -> None

# Brokerage snapshot
aggregate_positions(user_id: str, as_of: date) -> PortfolioSnapshot
```

REST parity: `/income-calendar`, `/projections`, `/yield`, `/alerts`, `/positions`.

---

## 6) ETL/Jobs

- **Nightly 22:00 Europe/London**
  1) Load bronze vendor files (dividends, prices, FX).  
  2) Normalize to silver tables; reconcile identifiers.  
  3) Refresh projections & income calendars (gold).  
  4) Recompute YoC/current yield snapshots.  
  5) Generate alerts for tomorrow’s ex/payable and today’s new declarations.

- **Intraday (optional)**  
  Lightweight webhook/ingestor for dividend declarations → update `dividend_events` → recompute projections for impacted tickers → enqueue alerts. Matches the site’s “realtime” positioning.  [oai_citation:11‡dividendtracker.com](https://dividendtracker.com/)

---

## 7) Acceptance Criteria (Given/When/Then)

**A. Income Calendar**
- Given positions across 3 brokerages, when I call `get_income_calendar(..., level="monthly")`, then I receive monthly totals and constituent payouts for all accounts, with GBP-converted totals, within < 1.5s for portfolios ≤ 3k holdings.

**B. YoC**
- Given two lots with different costs, when computing YoC, then result equals the share-weighted YoC and matches manual check within 0.01%.

**C. Projections**
- Given a quarterly regular payer with last 8 dividends equal, when no forward declaration exists, then 4 projected payouts appear over the next 12 months on expected cadence with `source=forecast_model` and confidence ≥ 0.8.

**D. Alerts**
- Given a new declaration arrives at 11:30, then an alert is created in `alerts_outbox` within 1 minute and is not duplicated if re-ingested.

**E. Unlimited Accounts**
- Given 10 accounts and 5k holdings, monthly calendar generation completes within < 4s and memory stays < 1.5 GB. (Demonstrates “unlimited accounts/stocks/calendars” design intent.)  [oai_citation:12‡dividendtracker.com](https://dividendtracker.com/)

---

## 8) Edge Cases & Rules
- **Special dividends**: exclude from run-rate (YoC/current yield) but include as one-off cashflows; `is_special=True`.
- **Variable ETFs**: use rolling 12M with month-seasonality.
- **Suspended/cut dividends**: if a declaration of $0 or explicit suspension appears, zero out projections until reinstated.
- **Corporate actions** (splits, mergers): maintain lot cost adjustment history; backfill YoC.
- **Currency**: convert payouts to GBP using FX on **payable date**; YoC uses purchase-date FX for cost basis.
- **Tax/ADR**: (optional) model withholding at country-default rate per security for net income views.
- **Record vs ex**: ensure ex-date logic (must hold before ex to receive payout) for “eligibility” views.
- **Fractional shares/DRIP**: support fractional payouts; optional reinvested share calculation at payable-date price.
- **Rounding**: round cash to 0.01 in payout currency; keep high-precision internal decimals.

---

## 9) Performance & Reliability
- **SLOs**: p95 calendar/projection calls ≤ 1.5s (≤ 3k positions), alert enqueue < 60s post event.  
- **Idempotency**: upsert by `(security_id, event_type, event_dt, amount)` and vendor IDs.  
- **Provenance**: every row carries `source`, `ingested_at`, `vendor_ref`.  
- **Backfill**: ability to recompute projections after historical corrections.

---

## 10) Testing Strategy
- **Unit**: formulas (YoC, current yield, FX conversions), frequency detector, projection generator.  
- **Golden datasets**: hand-curated tickers (stable quarterly, monthly REIT, variable ETF, cutter, suspender, special payer).  
- **Property-based**: invariants (no negative payouts, declared beats forecast, totals = sum of parts).  
- **Time-zone**: calendars rendered in Europe/London; DST transitions validated.

---

## 11) Deliverables
1) **Schemas** (Parquet + migration scripts).  
2) **Analytics library** implementing §5.  
3) **Batch jobs** (nightly) + optional intraday ingestor.  
4) **Docs**: API reference, runbooks, data dictionary, and example notebooks (portfolio walkthrough).  
5) **Verification pack**: tests + golden datasets + performance report.

---

If you want, I can stub the Python package (data classes, projection engine, and a sample Parquet schema) so you can drop it straight into your pipeline.
