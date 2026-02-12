
# Leverage for the Long Run Strategy

> *Based on Michael Gayed’s award-winning research (2016 Charles Dow Award)*

Most investors apply leverage indiscriminately or not at all due to fear of risk. But leverage is only dangerous in high-volatility, choppy markets. If we can identify **low-volatility, trending environments**, we can **safely apply leverage to magnify returns** while managing downside risk.

Michael's paper introduces a systematic strategy for using leverage in equity markets that addresses the often-overlooked question of *when* to apply it. The authors demonstrate that leverage is most effective in low-volatility environments with streaks of positive returns, and that such periods can be reliably identified when the market trades above its 200-day Moving Average. Conversely, high-volatility regimes—typically when the market is below its average—are detrimental to leveraged positions. By rotating into leveraged equity exposure when the market is trending upward and into Treasury bills when it trends downward, the strategy achieves superior absolute and risk-adjusted returns compared to both unleveraged buy-and-hold and constant leverage approaches, with results consistent across different time periods, leverage levels, and market cycles.

## The Leverage Rotation Strategy (LRS)

Use the **200-day Simple Moving Average (SMA)** of the **S\&P 500 Total Return Index** to toggle between:

* **Risk-On (Leverage On)**: Invest in a **leveraged S\&P 500 ETF** when above the 200-day SMA.
* **Risk-Off (Leverage Off)**: Rotate into **3-month Treasury bills (cash)** when below the 200-day SMA.

## Strategy Parameters

| Parameter               | Value / Notes                                |
| ----------------------- | -------------------------------------------- |
| Signal Indicator        | S\&P 500 vs 200-day Simple Moving Average    |
| Signal Frequency        | Daily (end of day close)                     |
| Execution Frequency     | Daily or Weekly                              |
| Leverage Level          | 2x or 3x on S\&P 500 ETFs (e.g., UPRO, TQQQ) |
| Risk-Off Asset          | T-Bills / SHV / BIL                          |
| Strategy Costs          | 1% annual leverage fee (approx ETF expense)  |
| Trade Trigger           | Cross above or below the 200-day SMA         |
| Average Trades Per Year | \~5 (for 200-day MA)                         |

## Top 10 Leveraged S\&P 500 ETFs

| Rank | Ticker                       | Leverage                                | Notes                                                                                                           |
| ---- | ---------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 1    | **SPXL**                     | 3× S\&P 500 Bull (Direxion)             | Highest liquidity in 3× S\&P space; tightly tracked with large AUM (\~\$2.7 B) and volume ([Investopedia][1])   |
| 2    | **UPRO**                     | 3× S\&P 500 (ProShares)                 | Major product (\~\$3.9 B AUM), competitive expense ratio (\~0.91%) ([Nasdaq][2], [Investopedia][1])             |
| 3    | **SPUU**                     | 2× S\&P 500 Bull (Direxion)             | Lower fee (~~0.63%) among 2× funds; modest AUM (~~\$52 M) ([Investopedia][1], [Wikipedia][3])                   |
| 4    | **SSO**                      | 2× S\&P 500 (ProShares)                 | Highest liquidity in 2× space (\~3 B AUM, millions/day volume) ([Investopedia][1], [ProShares][4])              |
| 5    | **SPXU / SPXS** (short/long) | 3× Bear/Bull respectively               | SPXS is short; SPXL is bull; SPXS similar issuer but bear version ([Direxion][5], [Wikipedia][6])               |
| 6    | **HIBL**                     | 3× S\&P 500 High Beta Bull              | Targets high-beta stocks in S\&P; strong returns historically (\~28.5% 5‑yr) ([ETF Database][7], [Direxion][5]) |
| 7    | **GUSH**                     | 2× S\&P Oil & Gas (Direxion)            | Sector-specific but historically high leveraged return (\~23.8% 5‑yr) ([ETF Database][7], [Direxion][5])        |
| 8    | **UDOW**                     | 3× Dow but includes S\&P sector overlap | 5‑yr returns ~~24.2%, high volume (~~\$729 M AUM) ([ETF Database][7])                                           |
| 9    | **SPHB**                     | 2× S\&P 500 High Beta (Invesco)         | High volatility selections within S\&P; \~21% 5‑yr return ([ETF Database][7])                                   |
| 10   | **QLD**                      | 2× NASDAQ‑100 (ProShares)               | Not S\&P but included for comparison; strong \~25.4% 5‑yr returns ([ETF Database][7])                           |


* While **SPXL and UPRO** lead the pack in **3× S\&P exposure**, **SSO** and **SPUU** dominate in the **2× space**, balancing cost and liquidity ([Investopedia][1]).
* **High-beta variants** like **HIBL** and **SPHB** can outperform in trending regimes but amplify risk.
* Some sector‑specific leveraged ETFs (e.g., **GUSH**, **UDOW**) have delivered strong multiyear returns; helpful for comparative context.

When integrating one of these into the **“Leverage for the Long Run”** system:

* **SPXL or UPRO** are go‑to picks for high-performance 3× leverage.
* **SSO** is solid for lower-leverage risk management or as a benchmark.
* **SPUU** offers cost efficiency in the 2× space but less liquidity.

[1]: https://www.investopedia.com/articles/etfs/top-leveraged-sp-500-etfs/?utm_source=chatgpt.com "Top Leveraged S&P 500 ETFs - Investopedia"
[2]: https://www.nasdaq.com/articles/guide-10-most-popular-leveraged-etfs?utm_source=chatgpt.com "Guide to the 10 Most Popular Leveraged ETFs - Nasdaq"
[3]: https://en.wikipedia.org/wiki/List_of_American_exchange-traded_funds?utm_source=chatgpt.com "List of American exchange-traded funds"
[4]: https://www.proshares.com/our-etfs/leveraged-and-inverse/sso?utm_source=chatgpt.com "SSO | Ultra S&P500 - ProShares"
[5]: https://www.direxion.com/leveraged-and-inverse-etfs?utm_source=chatgpt.com "Leveraged & Inverse ETFs - Direxion"
[6]: https://en.wikipedia.org/wiki/Direxion?utm_source=chatgpt.com "Direxion"
[7]: https://etfdb.com/compare/highest-5-year-returns/?utm_source=chatgpt.com "100 Highest 5 Year ETF Returns"


## 🧮 Codified Strategy Logic

```python
def compute_moving_average(prices, window=200):
    return prices.rolling(window=window).mean()

def generate_signal(current_price, moving_average):
    return 'risk_on' if current_price > moving_average else 'risk_off'

def allocate(signal, leverage_asset='UPRO', safe_asset='SHV'):
    return {leverage_asset: 1.0} if signal == 'risk_on' else {safe_asset: 1.0}

# Main daily/weekly loop
for date in rebalance_dates:
    price_today = spy_prices.loc[date]
    ma_200 = compute_moving_average(spy_prices).loc[date]
    signal = generate_signal(price_today, ma_200)
    portfolio = allocate(signal)
    execute_trades(portfolio)
```

## Empirical Results (from paper)

| Metric            | Buy & Hold | LRS (2x) | LRS (3x) |
| ----------------- | ---------- | -------- | -------- |
| Annual Return     | 9.1%       | 19.1%    | 26.8%    |
| Annual Volatility | 18.9%      | 24.9%    | 37.3%    |
| Sharpe Ratio      | 0.30       | 0.51     | 0.47     |
| Max Drawdown      | -86.2%     | -78.7%   | -92.2%   |
| Avg Trades / Year | 0          | \~5      | \~5      |
| Alpha vs. Market  | 0%         | 10.8%    | 16.0%    |


## Why It Works

* **Volatility Regimes Matter**: Leverage suffers in volatile, whipsawing markets.
* **Streaks Favor Leverage**: Above the 200-day MA, markets are statistically more likely to show consecutive positive days.
* **Behavioral Edge**: Moving averages reduce emotional decision-making and limit exposure to crash-prone regimes.

## Acceptance Criteria 

| Feature         | Description                                  |
| --------------- | -------------------------------------------- |
| Data Source     | Daily S\&P 500 Total Return (adjusted close) |
| SMA Calculation | Uses rolling 200-day mean of daily prices    |
| Trade Logic     | Rotates between leveraged ETF and cash       |
| Rebalance Logic | Executes on crossovers only                  |
| Risk Management | No leverage applied in risk-off regime       |
| Metrics Logged  | PnL, drawdowns, CAGR, trade count, Sharpe    |


## Potential Enhancements

* Parameter optimization (e.g., 100-day or 150-day SMA variants).
* Layer in momentum overlays for confirmation.
* Add volatility-adjusted position sizing.
* Compare against volatility index (e.g., VIX) for multi-factor rotation.


