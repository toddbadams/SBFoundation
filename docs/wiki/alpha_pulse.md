
**AlphaPulse** is a systematic, 0–100 scoring framework enables identification of the most efficient, fastest‑growing, and most stable companies at a glance. By breaking performance into discrete factors (profitability, growth, leverage, valuation, momentum, stability) and normalizing each with transparent formulas, this framework eliminates the guesswork and emotional bias that often plague stock selection.

The result is a repeatable, data‑driven engine that not only ranks every company on the same scale but also allows weight adjustments to suit value, growth, or income strategies—ultimately accelerating research, enhancing consistency, and making backtests and live trades far more actionable.



## Setup Assumptions

 - DataFrame: `df`
 - Time indexed: (Date)
 - All source data is recorded at quarter-end dates.
 - 20 years of quarterly history provided 

| Parameter                  | Formula to calculate                                                          | Source                         |
| -------------------------- | ----------------------------------------------------------------------------- | ------------------------------ |

## 1. Return on Assets

> **As a** quant analyst, **I want to** compute a profitability score , **so that** I can compare how efficiently different companies turn assets into net income.

**Acceptance Criteria:**

* **Input Column(s):** `net_income`, `total_assets`
* **Output Column:** `return_on_assets_ratio`, `return_on_assets_ratio_score`
* **Formula:**

  ```python
        df['return_on_assets_ratio'] = (df['net_income'] / df['total_assets'] ) * 100
        df['return_on_assets_ratio_score'] = ScoreCalculator(min_ratio=5, max_ratio=20,
                                                            min_score=0, max_score=100,
                                                            ascending=True)
                                                            .calculate(df['return_on_assets'])
  ```
* **Scoring Rules:**
  * If ROA < 5%, score = 0
  * If ROA between 5% and 20%, score = linearly scale 0→100
  * If ROA > 20%, score = 100

## 2. Quarterly Revenue Growth

> **As a** quant analyst, **I want to** compute a growth score , **so that** I can spot companies growing revenue fastest.

**Acceptance Criteria:**

* **Input Column(s):** `revenue`, `revenue.shift(4)` (same quarter last year)
* **Output Column:** `revenue_growth`, `revenue_growth_score`
* **Formula:**

  ```python
        df['revenue_growth'] = (df['revenue'] - df['revenue'].shift(4)) / df['revenue'].shift(4)
        df['revenue_growth_score'] = ScoreCalculator(min_ratio=0, max_ratio=0.3,
                                                            min_score=0, max_score=100,
                                                            ascending=True)
                                                            .calculate(df['revenue_growth'])
  ```
* **Scoring Rules:**
  * If growth < 0%, score = 0
  * If growth 0%–30%, score = linear 0→100
  * If growth > 30%, score = 100

## 3. Debt / Equity Ratio

> **As a** quant analyst, **I want to** compute a quality score , **so that** I can identify companies with conservative balance‑sheet leverage.

**Acceptance Criteria:**

* **Input Column(s):** `total_debt`, `total_shareholder_equity`
* **Output Column:** `debt_to_equity_ratio`, `debt_to_equity_ratio_score`
* **Formula:**

```python
        df['debt_to_equity_ratio'] = (df['total_debt'] / df['total_shareholder_equity'] ) * 100
        df['debt_to_equity_ratio_score'] = ScoreCalculator(min_ratio=50, max_ratio=200,
                                                            min_score=0, max_score=100,
                                                            ascending=True)
                                                            .calculate(df['debt_to_equity_ratio'])
```

* **Scoring Rules:**
  * If D/E > 2.0, score = 0
  * If D/E 0.5–2.0, score = linear 0→100 (2.0→0; 0.5→100)
  * If D/E < 0.5, score = 100

## 4. Earnings Yield

> **As a** quant analyst, **I want to** compute a valuation score , **so that** I can find stocks that are cheap relative to earnings.

**Acceptance Criteria:**

* **Input Column(s):** `eps`, `share_price`
* **Output Column:** `earnings_yield`, `earnings_yield_score`
* **Formula:**

  ```python
        df['earnings_yield'] = (df['eps'] / df['share_price'] )
        df['earnings_yield_score'] = ScoreCalculator(min_ratio=50, max_ratio=200,
                                                            min_score=0, max_score=100,
                                                            ascending=True)
                                                            .calculate(df['earnings_yield_score'])
  ```
* **Scoring Rules:**
  * If EY < 2%, score = 0
  * If EY 2%–10%, score = linear 0→100
  * If EY > 10%, score = 100

## 5. Price Surge

> **As a** quant analyst, **I want to** compute a momentum score , **so that** I can flag stocks that have recently “heated up.”

**Acceptance Criteria:**

* **Input Column(s):** `share_price`, `share_price.shift(4)` (price 4 quarters ago)
* **Output Column:** `momentum`,  `momentum_score`
* **Formula:**

  ```python
        df['momentum'] = (df['share_price'] - df['share_price'].shift(4)) / df['share_price'].shift(4)
        df['momentum_score'] = ScoreCalculator(max_ratio=-0.1, max_ratio=0.5
                                               min_score=0, max_score=100,
                                               ascending=True)
                                               .calculate(df['momentum'])
  ```
* **Scoring Rules:**
  * If surge < –10%, score = 0
  * If surge –10% to +50%, score = linear 0→100
  * If surge > 50%, score = 100

## 6. ROA Volatility

> **As a** quant analyst, **I want to** compute a stability score , **so that** I can prefer companies with consistent profitability over time.

**Acceptance Criteria:**

* **Input Column(s):** rolling 8‑quarter `return_on_assets_ratio` values
* **Output Column:** `return_on_assets_volatility`, `return_on_assets_volatility_score`
* **Formula:**

  ```python
        df['return_on_assets_volatility'] = df['return_on_assets_ratio'].shift(8).std()
        df['return_on_assets_volatility_score'] = ScoreCalculator(min_ratio=0.05, max_ratio=0.15,
                                                            min_score=0, max_score=100,
                                                            ascending=False)
                                                            .calculate(df['return_on_assets_volatility'])
  roa_vol = roa.rolling(window=8).std()
  roa_vol_score = 100 * clip((0.15 - roa_vol) / (0.15 - 0.05), 0, 1)
  ```
* **Scoring Rules:**
  * If ROA SD > 15%, score = 0
  * If ROA SD 5%–15%, score = linear 0→100 (15%→0; 5%→100)
  * If ROA SD < 5%, score = 100


### Composite Score & Weighting

> **As a** quant analyst, **I want to** combine individual factor scores into a single composite score , **so that** I can rank stocks at a glance.

**Acceptance Criteria:**

* **Input Column(s):**
  `roa_score`, `rev_growth_score`, `de_ratio_score`, `earnings_yield_score`,
  `momentum_score`, `roa_vol_score`
* **Output Column:** `composite_score`
* **Formula:**

| No. | Metric                                     | Weight |
| :-: | ------------------------------------------ | :----: |
|  1  | `return_on_assets_ratio_score`             |  0.20  |
|  2  | `revenue_growth_score`                     |  0.20  |
|  3  | `debt_to_equity_ratio_score`               |  0.15  |
|  4  | `earnings_yield_score`                     |  0.15  |
|  5  | `momentum_score`                           |  0.20  |
|  6  | `return_on_assets_volatility_score`        |  0.10  |


## Weight Configuration


> **As a** quant analyst, **I want to** be able to adjust factor weights , **so that** I can tailor the composite score to different investment styles (e.g. value vs. growth).

**Acceptance Criteria:**

* **Input:** A dictionary or config file of factor weights
* **Output:** Updated `w` mapping used in the composite formula
* **Formula/Rules:**

  * Sum of all weights must equal 1.0
  * Each weight ≥ 0
  * System validates config on load and raises an error if invalid


**Alpha Pulse Dashboard Wireframe**

## UI Dashboard

> **As an** investor, **I want to** see the Alpha Pulse Score—summarizing profitability, growth, leverage, valuation, momentum, and stability—and the detailed breakdown showing each factor’s raw value, normalized score, and weighting., **so that **I can quickly assess overall potential and understand which factors drive the score.

```
+-------------------------------------------------------------+
|                   Alpha Pulse Dashboard (Header)           |
|-------------------------------------------------------------|
|  [Date/Quarter Selector ▼]      [Export Button]    [Help ?]  |
+-------------------------------------------------------------+
|                                                             |
|   +-----------------------+     +-------------------------+  |
|   | Alpha Pulse Score     |     |        Legend / Info    |  |
|   |       Gauge           |     |  - Score Scale (0–100)  |  |
|   |    78 / 100           |     |  - Factor Weightings    |  |
|   +-----------------------+     +-------------------------+  |
|                                                             |
|-------------------------------------------------------------|
| Factor Breakdown Table (sortable, searchable)               |
|-------------------------------------------------------------|
| No. | Factor                   | Raw Value      | Score | Weight |
|-----|--------------------------|----------------|-------|--------|
| 1   | Return on Assets        | 12%            | 60    | 20%    |
| 2   | Revenue Growth (YoY)    | 25%            | 83    | 20%    |
| 3   | Debt/Equity Ratio       | 75%            | 50    | 15%    |
| 4   | Earnings Yield          | 8%             | 60    | 15%    |
| 5   | Price Surge (QoQ)       | 35%            | 70    | 20%    |
| 6   | ROA Volatility (8q SD)  | 7%             | 80    | 10%    |
|-------------------------------------------------------------|
|                                Total Weight: 100%           |
+-------------------------------------------------------------+
| Notes: 1. Scores 0–100; 2. Hover headers for definitions.   |
+-------------------------------------------------------------+
```


- **Header & Controls**: Title, quarter selector, export button, help icon.
- **Alpha Pulse Score Gauge**: Prominent radial/bar gauge showing composite `alpha_pulse_score` out of 100.
- **Legend / Info Panel**: Explains score scale and displays each factor’s default weighting (editable via settings).
- **Factor Breakdown Table**:

  - **Factor**: One of the six Alpha Pulse factors.
  - **Raw Value**: Underlying metric (percentage, ratio, volatility).
  - **Score**: Normalized 0–100 score.
  - **Weight**: Contribution to composite score.
 - Table supports sorting, filtering, and hover tooltips for each column.
- **Footer Notes**: Methodology pointers and links to detailed definitions.


