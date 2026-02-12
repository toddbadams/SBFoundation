# 📊 Portfolio Tracker Specification

## 🚀 Overview

A unified tool to consolidate brokerage accounts, track holdings and transactions, compute performance, and surface insights on asset allocation and risk. The tracker prioritizes repeatable data ingestion, modular analytics, and an interactive dashboard for monitoring progress toward financial goals.

## 💻 Technical Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.11+ |
| Data Store | Parquet files via Pandas (core) or SQLite (optional) |
| APIs | Alpha Vantage for pricing, brokerage CSV/API exports |
| Scheduler | Prefect or cron |
| Dashboard | Streamlit + Altair charts |
| Alerts | Slack webhooks or email |

## 📐 Data Model

- **Account**: `{id, broker, name, currency}`
- **Transaction**: `{id, account_id, ticker, type, quantity, price, fees, date}`
- **Holding**: derived from transactions; `{account_id, ticker, quantity, cost_basis}`
- **PriceHistory**: `{ticker, date, close, adj_close, volume}`

## 📁 Epics

### 1. Ingestion & Synchronization
1. **As a user**, I can upload brokerage CSV exports or connect via API so the system captures transactions.
2. **As a system**, I normalize and deduplicate transactions across accounts into a unified schema.
3. **As a scheduler**, I refresh pricing data nightly to update portfolio valuations.

### 2. Portfolio Management
4. **As a user**, I can view current holdings with cost basis, market value, and unrealized gain/loss per ticker.
5. **As a user**, I can tag holdings with categories (e.g., retirement, taxable) for segmented views.
6. **As a user**, I can record cash deposits, dividends, and fees to maintain accurate account balances.

### 3. Performance & Analytics
7. **As a user**, I can see time-weighted and money-weighted returns for each account and the overall portfolio.
8. **As a system**, I compute asset allocation by sector, region, and asset class.
9. **As a user**, I can compare performance to benchmark indices such as the S&P 500.

### 4. Dashboard & Reporting
10. **As a user**, I get an interactive dashboard with charts for growth over time, allocation, and realized vs. unrealized gains.
11. **As a user**, I can export summary reports to CSV or PDF for record keeping.
12. **As a user**, I can set target allocations and visualize drift.

### 5. Notifications & Integrations
13. **As a user**, I receive Slack or email alerts when allocation drift exceeds a threshold or large cash movements occur.
14. **As a system**, I expose a REST API for retrieving holdings and performance metrics for other apps.
15. **As a user**, I can trigger rebalancing suggestions based on rules (e.g., threshold, calendar).

## 🔒 Out of Scope

- Options, futures, or other derivatives.
- Real-time intraday pricing.
- Tax-loss harvesting strategies.

