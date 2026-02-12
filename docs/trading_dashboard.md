# Trading Analytics Dashboard Specification

## Purpose
Build a dashboard for an individual algorithmic trader to ingest data, warehouse it, run multi-factor asset pricing, compute technical momentum and volatility, optimize portfolios, and backtest strategies. The dashboard is driven by existing gold dims and facts, with derived feature sets layered on top.

## Audience
- Primary user: individual algorithmic trader
- Secondary use: auditing data coverage, verifying factor inputs, and validating strategy backtests

## Scope and assumptions
- Universe: US equities
- Technicals: end-of-day bars
- Baseline factor model: Fama-French 5 (FF5)
- Optimizer constraints: TBD

## Core workflows
- Data ingest status and warehouse coverage
- Multi-factor modeling and factor exposure analysis
- Technical momentum and volatility signals
- Portfolio optimization and risk monitoring
- Strategy backtesting and scenario analysis
- Ticker search and drilldown
- Screeners for idea generation

## Data model foundation (dims and facts)
Dims:
- dim_date
- dim_company_profile
- dim_company_peer
- dim_company_officer
- dim_share_float

Facts:
- fact_market_cap_snapshot
- fact_employee_filing
- fact_balance_sheet
- fact_balance_sheet_growth
- fact_cashflow_statement
- fact_cashflow_growth
- fact_income_statement
- fact_income_statement_growth
- fact_financial_statement_growth
- fact_financial_scores
- fact_key_metrics
- fact_key_metrics_ttm
- fact_metrics_ratios
- fact_enterprise_values
- fact_owner_earnings

Derived feature sets (computed in the analytics layer):
- Technicals: returns, moving averages, RSI, ATR, realized volatility, beta
- Factor exposures: value, size, quality, momentum, low volatility, profitability, investment
- Risk: drawdowns, VaR/CVaR, correlation clusters
- Portfolio: weights, turnover, constraints, contribution to risk

## Information architecture
1) Overview
- Pipeline status, dataset coverage, and latest ingest times
- Factor regime summary
- Portfolio summary: performance, drawdown, risk, exposure

2) Screener Hub
- Prebuilt screeners with quick filters
- Custom screener builder using dims and facts

3) Factor Lab
- Factor definitions, exposures, and cross-sectional ranks
- Factor returns and attribution
- Model diagnostics (R^2, t-stats, stability)

4) Technicals
- Momentum, trend, and volatility indicators
- Signal heatmaps by sector or universe

5) Portfolio
- Allocation, risk contribution, constraints
- Efficient frontier and optimizer outputs

6) Backtest Studio
- Strategy configs, walk-forward tests, scenario runs
- Performance and risk summaries, trade logs

7) Ticker Drilldown
- Profile, fundamentals, technicals, factor exposures, and peers

## Chart sets by dim and fact
| Source | Chart set | Notes |
| --- | --- | --- |
| dim_company_profile | Profile header, sector/industry badges, exchange/currency chips | Key identity panel for drilldown |
| dim_company_peer | Peer list, valuation scatter, percentile rank | Compare vs peers |
| dim_company_officer | Officer table, compensation distribution | Governance context |
| dim_share_float | Float vs outstanding shares bar | Liquidity context |
| dim_date | Global time axis and calendar controls | Shared filters |
| fact_market_cap_snapshot | Market cap series | Size and liquidity |
| fact_employee_filing | Employee count series | Growth and scale |
| fact_income_statement | Revenue, EBIT, net income series | Core performance |
| fact_income_statement_growth | YoY growth bars | Growth screeners |
| fact_balance_sheet | Assets, liabilities, equity stacked series | Balance health |
| fact_balance_sheet_growth | Growth rates for balance items | Trend checks |
| fact_cashflow_statement | CFO/CFI/CFF series | Cash quality |
| fact_cashflow_growth | Growth in cash metrics | Momentum in cash |
| fact_financial_scores | Scorecards and radar | Quality summary |
| fact_key_metrics | Ratios table and trends | Valuation/quality |
| fact_key_metrics_ttm | TTM metrics spotlight cards | Most recent snapshot |
| fact_metrics_ratios | Ratio trend lines | Screening inputs |
| fact_enterprise_values | EV and EV-based ratios | Value signals |
| fact_owner_earnings | Owner earnings trend | Value and quality |
| fact_financial_statement_growth | Composite growth dashboard | Growth factor |

## Screeners (starter set)
- Value: low EV/EBITDA, high FCF yield, low P/B, high earnings yield
- Quality: high ROIC, strong margins, low net debt/EBITDA
- Momentum: 1M/3M/6M/12M returns, above 200D MA
- Volatility: low 30D and 90D realized vol, low beta
- Growth: revenue and earnings growth above thresholds
- Size and liquidity: market cap and float filters

Each screener should allow:
- Universe filter (US equities)
- Date range and as-of date
- Threshold sliders and rank ordering
- Export to CSV and watchlist

## Ticker drilldown layout
- Header: ticker, name, sector, market cap, price, volume, key badges
- Fundamentals: income, balance, cashflow trends
- Factors: exposure bars and ranking vs universe
- Technicals: price chart with indicators and signal markers
- Peers: peer table and valuation scatter
- Events: filings and notable changes (employee, market cap shifts)

## Factor model view
- Supported models: FF5 baseline with optional momentum and quality overlays
- Inputs: fundamentals facts, market cap, price-based returns
- Outputs: factor exposures, factor returns, alpha, residual risk
- Diagnostics: rolling regression stability, factor correlations

## Portfolio optimization
- Optimizer options: max Sharpe, min variance, risk parity, target beta
- Constraints: TBD
- Outputs: allocation table, frontier chart, risk contribution

## Visual design (light and dark)
Typography:
- Headings: Space Grotesk
- Body: IBM Plex Sans
- Numerals: IBM Plex Mono

Light theme tokens:
- background: #F6F3EE
- surface: #FFFFFF
- text: #1C1B1A
- muted: #6B6761
- accent: #0F5B8A
- accent_alt: #C34E1C
- positive: #1E7F5C
- negative: #B8462E
- grid: #E8E2DA

Dark theme tokens:
- background: #111315
- surface: #1B1F22
- text: #ECE9E2
- muted: #A6A09A
- accent: #4DB3FF
- accent_alt: #FF9F68
- positive: #5CCB9A
- negative: #FF6F5B
- grid: #2A2F33

Chart palette guidance:
- Use 6 to 8 colors max, consistent across views
- Reserve accent for actionable states and active selections

## Interaction and filtering
- Global filters: date range, universe, factor model, rebalance frequency
- Cross-filtering between charts and tables
- Saved views and screeners
- Search: ticker input with autosuggest and recent history

## Wireframes

### Overview
```
+----------------------------------------------------------------------------------+
| NAV: Overview | Screeners | Factor Lab | Technicals | Portfolio | Backtests | TKR|
+----------------------------------------------------------------------------------+
| Filters: Universe=US | Date Range | As-of | Model=FF5 | Theme Toggle | Search    |
+-----------------------------+-----------------------------+----------------------+
| KPI Cards                   | Factor Regime Summary       | Pipeline Health      |
| Coverage | Freshness | ...  | Market/Size/Value tilt      | Last ingest, errors  |
+-----------------------------+-----------------------------+----------------------+
| Portfolio Perf (line)       | Risk/Drawdown (area)        | Exposure Heatmap     |
+-----------------------------+-----------------------------+----------------------+
```

### Screener Hub
```
+----------------------------------------------------------------------------------+
| NAV + Global Filters                                                            |
+---------------------------+------------------------------------------------------+
| Screeners                 | Results Table                                       |
| - Value                   | [Rank | Ticker | Name | Score | Valuation | Quality] |
| - Quality                 | [Filters, sort, export, watchlist]                  |
| - Momentum                |                                                      |
| - Volatility              |                                                      |
| - Growth                  |                                                      |
| - Size/Liquidity          |                                                      |
+---------------------------+------------------------------------------------------+
| Custom Screener Builder: criteria rows with AND/OR, sliders, and date controls   |
+----------------------------------------------------------------------------------+
```

### Factor Lab
```
+----------------------------------------------------------------------------------+
| NAV + Global Filters                                                            |
+---------------------------+-----------------------------------+------------------+
| Model Settings            | Factor Returns (time series)       | Diagnostics      |
| - FF5 base                |                                   | R^2, t-stats     |
| - Momentum overlay        |                                   | Stability chart  |
| - Universe, rebalance     |                                   | Corr matrix      |
+---------------------------+-----------------------------------+------------------+
| Cross-sectional Exposures (bar) | Factor Attribution (waterfall)                 |
+----------------------------------------------------------------------------------+
```

### Technicals
```
+----------------------------------------------------------------------------------+
| NAV + Global Filters + Ticker Search                                             |
+---------------------------+------------------------------------------------------+
| Signal Summary            | Price Chart (OHLC) + MAs + RSI + ATR                  |
| Momentum score, Vol score |                                                      |
+---------------------------+------------------------------------------------------+
| Volatility Panel           | Momentum Heatmap by sector                          |
+---------------------------+------------------------------------------------------+
```

### Portfolio
```
+----------------------------------------------------------------------------------+
| NAV + Global Filters                                                            |
+---------------------------+-----------------------------------+------------------+
| Positions Table           | Allocation (treemap or pie)        | Risk Contribution|
| Weights, alpha, beta      |                                   | by asset/sector  |
+---------------------------+-----------------------------------+------------------+
| Efficient Frontier (line) | Constraints Summary (chips)                         |
+----------------------------------------------------------------------------------+
```

### Backtest Studio
```
+----------------------------------------------------------------------------------+
| NAV + Global Filters                                                            |
+---------------------------+-----------------------------------+------------------+
| Strategy Config           | Performance (equity curve)        | Drawdown         |
| Signals, rebalance, costs |                                   |                  |
+---------------------------+-----------------------------------+------------------+
| Trade Log (table)         | Metrics (CAGR, Sharpe, hit rate)                     |
+----------------------------------------------------------------------------------+
```

### Ticker Drilldown
```
+----------------------------------------------------------------------------------+
| NAV + Global Filters + Ticker Search                                             |
+----------------------------------------------------------------------------------+
| Header: Ticker | Name | Sector | Price | Market Cap | Beta | Key badges           |
+---------------------------+-----------------------------------+------------------+
| Fundamentals (income/bal) | Technicals (price + signals)      | Factor Exposures |
+---------------------------+-----------------------------------+------------------+
| Peers (table + scatter)   | Events (filings, changes)                            |
+----------------------------------------------------------------------------------+
```

## Data dictionary appendix (minimum required fields)

### Dimensions
- dim_date: date_sk, date, year, quarter, month, day, day_of_week, day_name, month_name, iso_week
- dim_company_profile: company_sk, ticker, company_name, sector, industry, exchange, currency, price, market_cap, beta, average_volume, ipo_date, is_etf, is_actively_trading
- dim_company_peer: company_peer_sk, ticker, peer, company_name, price, mkt_cap
- dim_company_officer: company_officer_sk, ticker, title, name, pay, currency_pay, gender, year_born, active
- dim_share_float: share_float_sk, ticker, free_float, float_shares, outstanding_shares

### Facts
- fact_market_cap_snapshot: company_sk, date_sk, ticker, date, market_cap
- fact_employee_filing: company_sk, date_sk, ticker, period_of_report, filing_date, employee_count, company_name, form_type
- fact_income_statement: date, fiscal_year, period, revenue, gross_profit, operating_income, ebitda, net_income, eps, weighted_average_shs_out
- fact_income_statement_growth: date, fiscal_year, period, growth_revenue, growth_ebitda, growth_operating_income, growth_net_income, growth_eps
- fact_balance_sheet: date, fiscal_year, period, total_assets, total_liabilities, total_stockholders_equity, cash_and_cash_equivalents, total_debt, net_debt
- fact_balance_sheet_growth: date, fiscal_year, period, growth_total_assets, growth_total_liabilities, growth_total_stockholders_equity, growth_total_debt, growth_net_debt
- fact_cashflow_statement: date, fiscal_year, period, operating_cash_flow, capital_expenditure, free_cash_flow, net_income
- fact_cashflow_growth: date, fiscal_year, period, growth_operating_cash_flow, growth_capital_expenditure, growth_free_cash_flow, growth_net_income
- fact_financial_statement_growth: date, fiscal_year, period, revenue_growth, operating_income_growth, net_income_growth, eps_growth, free_cash_flow_growth
- fact_financial_scores: snapshot_date, altman_z_score, piotroski_score, market_cap, total_assets, total_liabilities, revenue
- fact_key_metrics: date, fiscal_year, period, market_cap, enterprise_value, ev_to_ebitda, earnings_yield, free_cash_flow_yield, return_on_equity, return_on_assets, return_on_invested_capital
- fact_key_metrics_ttm: snapshot_date, market_cap, enterprise_value_ttm, ev_to_ebitda_ttm, earnings_yield_ttm, free_cash_flow_yield_ttm, return_on_equity_ttm, return_on_assets_ttm, return_on_invested_capital_ttm
- fact_metrics_ratios: date, fiscal_year, period, price_to_earnings_ratio, price_to_book_ratio, price_to_sales_ratio, price_to_free_cash_flow_ratio, dividend_yield, debt_to_equity_ratio, enterprise_value_multiple, gross_profit_margin, ebitda_margin, net_profit_margin
- fact_enterprise_values: date, stock_price, number_of_shares, market_capitalization, enterprise_value
- fact_owner_earnings: date, fiscal_year, period, owners_earnings, owners_earnings_per_share, maintenance_capex, growth_capex

### Derived feature inputs and required additional datasets
- price_ohlcv_eod (required for technicals and factor returns): ticker, date, open, high, low, close, adj_close, volume
- risk_free_rate (required for FF5 excess returns): date, rate
- factor_benchmarks (optional if not computed in-house): market, SMB, HML, RMW, CMA daily returns
- portfolio_positions (required for portfolio and backtest views): date, ticker, weight, strategy_id
- trades (required for backtest logs): trade_id, date, ticker, side, qty, price, fees

## Open questions
- What default optimizer constraints should be applied (position cap, sector cap, turnover, liquidity, beta bounds)?
