The **Dividend Score** is a quantitative measure designed to assess how likely a company is to maintain or cut its dividend over a full economic cycle. It combines multiple financial indicators—such as payout ratios, debt levels, cash flow stability, and liquidity—to evaluate the underlying strength and sustainability of a firm’s dividend payments.

This score matters because high-yield dividends can be deceptively attractive; without proper risk screening, investors may unknowingly take on companies that are overleveraged, cash-flow unstable, or vulnerable in downturns. A well-structured Dividend Safety Score helps avoid dividend traps, build more reliable income portfolios, and make decisions grounded in both financial discipline and long-term risk management.

The composite score is structured as:

* **Financial Sustainability Score (70%)** — metrics 2–8, 13–14
* **Dividend Policy Score (30%)** — metrics 1, 9–12


# **Financial Sustainability Metrics**

These assess a company’s *capacity* to sustain dividends through economic cycles — i.e., its solvency, liquidity, cash-flow strength, and stability.  These indicate **dividend safety**, i.e., how durable the firm’s payouts are under stress.

| #  | Metric                                       | Description                                                    |
| -- | -------------------------------------------- | -------------------------------------------------------------- |
| 1  | **Free Cash Flow Payout Ratio**              | Tests whether dividends are supported by real cash generation. |
| 2  | **Cash Payout Ratio**                        | Uses operating cash flow instead of accounting earnings.       |
| 3  | **Debt-to-Equity Ratio**                     | Measures leverage and financial flexibility.                   |
| 4  | **Interest to EBIT Coverage Ratio**          | Gauges ability to pay interest from operating earnings.        |
| 5  | **Cash (EBITDA) to Interest Coverage Ratio** | Cash-based variant showing debt-servicing strength.            |
| 6  | **Cash to Dividend Coverage Ratio**          | Tests if operating cash can fully fund dividends.              |
| 7  | **Free Cash Flow Volatility**                | Evaluates stability of cash generation over time.              |
| 8  | **Revenue Drawdown**                         | Reflects business resilience and cyclicality.                  |
| 9  | **Quick Ratio**                              | Tests short-term liquidity.                                    |


## 1. Free Cash Flow Payout Ratio

**Free Cash Flow Payout Ratio** is the percentage of free cash flow paid out as dividends. It provides a sense of dividend sustainability, since free cash flow (FCF) is the cash a company actually has left after funding its operations and capital expenditures. A **30%** FCF payout ratio means the company is returning 30% of its available cash to shareholders, leaving 70% to fuel growth or pay down debt. Ratios above 100% could signal unsustainable dividends (i.e., paying out more than you generate), while very low ratios might suggest room to raise distributions. It is calculated on on a per-share basis:

 $$
 \text{Free Cash Flow Payout Ratio} = \frac{\text{Dividends per Share}} {\text{Free Cash Flow per Share}}
 $$

1. **Annual Dividends per Share**: the total cash dividends paid per share in a year.
2. **Annual Free Cash Flow per Share** is the company’s free cash flow divided by the number of outstanding shares over a year.

### Scoring Rules
  * If ratio <= 0, score = 100
  * If ratio between 0 and 120, score = linearly scale 100→10
  * If ratio >= 120, score = 10


## 2. Cash Payout Ratio

The **cash payout ratio** measures the portion of a company’s **operating cash flow** that’s paid out as cash dividends over a period. Unlike the earnings payout ratio (which uses net income), this one uses the cash the business really generated—no accruals, no non-cash charges. A **25%** cash payout ratio means the company is returning one quarter of its operating-cash generation directly to shareholders. That leaves 75% in the business for growth, debt service, or other uses. Ratios above 100% might indicate unsustainable dividends (you’re paying out more than you’re actually collecting in cash), while low ratios could signal room to boost dividends or ramp up reinvestment. It is calculated on on a per-share basis:

 $$
 \text{Cash Payout Ratio} = \frac{\text{Annual Dividends per Share}} {\text{Annual Cash Flow per Share}}
 $$

1. **Annual Dividends per Share**: the total cash dividends paid per share over a year.
2. **Cash Flow per Share**: the total operating cash flow over the trailing twelve months divided by the number of outstanding shares.

### Scoring Rules
  * If ratio <= 10, score = 100
  * If ratio between 10 and 120, score = linearly scale 100→10
  * If ratio >= 120, score = 0


## 3. Debt-to-Equity Ratio

The **debt-to-equity ratio** measures how much a company relies on debt financing compared to shareholder equity to fund its operations and growth. It’s a core gauge of financial leverage and balance-sheet risk. A ratio of **1.0** means the company has equal parts debt and equity; **0.5** means twice as much equity as debt; and **2.0** means twice as much debt as equity. Higher ratios can amplify returns when times are good—but they also magnify losses and increase insolvency risk during downturns. Lower ratios suggest a more conservative capital structure with greater financial flexibility. It is calculated as:

$$
 \text{Debt-to-Equity Ratio} = \frac{\text{Total Debt}} {\text{Shareholders’ Equity}}
$$

1. **Total Debt** Typically the sum of short-term debt (notes and lines payable within a year) plus long-term debt (bonds, loans, leases). 
2. **Shareholders’ Equity** The residual “book value” owned by shareholders: Includes common stock, retained earnings, and other equity items.

### Scoring Rules
  * If ratio <= 0, score = 100
  * If ratio between 0 and 2, score = linearly scale 100→20
  * If ratio >= 20, score = 10

## 4. Interest to EBIT Coverage Ratio
The **interest coverage ratio** measures how many times over a company can pay its interest expense with its operating earnings. Use this ratio to compare peers in the same industry and to monitor changes over time. If interest costs rise or EBIT falls, watch for the coverage ratio slipping toward danger territory. It is calculated as:

 $$
 \text{Interest Coverage}  = \frac{\text{EBIT}} {\text{Interest Expense}}
 $$

1. **EBIT**: Earnings Before **I**nterest and **T**axes (sometimes people use **EBITDA** instead: add back Depreciation & Amortization for an “EBITDA coverage” ratio). Found on the income statement as “Operating Profit” or “Income from Operations.” If you want a more conservative view, use straight EBIT; if you want to factor in non-cash charges, you can bump it to EBITDA.
2. **Interest Expense**: The total interest the company paid (or accrued) on its borrowings over the same period. Also listed on the income statement.

### Scoring Rules
  * If ratio <= 150, score = 10
  * If ratio between 150 and 300, score = linearly scale 10→100
  * If ratio >= 300, score = 100

## 5. Cash (EBIDTA) to Interest Coverage

The **cash (EBITDA) to interest coverage ratio** measures how many times a company’s cash earnings—represented by EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)—can cover its interest expenses. Unlike traditional interest coverage ratios that rely on EBIT (accounting profits), this one focuses on true cash-generating capacity, making it a better gauge of debt-servicing strength. A 4× ratio means the company earns four times its annual interest costs in cash terms—ample breathing room for lenders and investors alike. Ratios below 1× signal potential distress (not enough cash to pay interest), while higher ratios reflect strong solvency and flexibility. It is calculated as:

$$
\text{Cash Coverage Ratio} = \frac{\text{EBITDA}}  {\text{Interest Expense}}
$$

1. **EBITDA**: Earnings Before Interest, Taxes, Depreciation & Amortization
2. **Interest Expense**: Cash interest paid over the period

### Scoring Rules
  * If ratio <= 150, score = 10
  * If ratio between 150 and 600, score = linearly scale 10→100
  * If ratio >= 600, score = 100

## 6. Cash to Dividend Coverage Ratio

Also called the **cash dividend cover** or **dividend coverage ratio** measures how many times a company’s operating cash flow covers its dividend payments. Unlike payout ratios based on earnings, this one uses actual cash generated by the business, showing whether dividends are truly funded by operations rather than borrowing or asset sales. A 2× ratio means the company produces twice as much cash as it pays out in dividends—indicating a comfortable safety margin. Ratios near or below 1× may suggest the dividend is stretched or at risk, while higher ratios point to stronger dividend sustainability and room for potential increases. It is calculated as:

 $$
\text{Dividend Coverage Ratio} =  \frac{\text{Annual Cash Flow per Share}}  {\text{Annual Dividend per Share}}
 $$

1. **Annual Dividends per Share**: the total cash dividends paid per share over a year.
2. **Cash Flow per Share**: the total operating cash flow over the trailing twelve months divided by the number of outstanding shares.

### Scoring Rules
  * If ratio <= 100, score = 10
  * If ratio between 100 and 200, score = linearly scale 10→100
  * If ratio >= 200, score = 100

## 7. Free Cash Flow Volatility (FCF)

The **free cash flow volatility (FCF volatility)** measures how stable or erratic a company’s free cash flow is over time. Since free cash flow represents the cash left after operating expenses and capital investments, consistent FCF signals a reliable ability to fund dividends, reduce debt, or reinvest for growth. High volatility indicates uneven or unpredictable cash generation—often a red flag for dividend safety—while low volatility reflects strong, steady performance through economic cycles. In essence, it captures how smooth or bumpy the company’s cash generation track record is. It is typically calculated as the coefficient of variation (standard deviation divided by the mean) of free cash flow over several years.

* **High volatility** → cash flow is erratic (riskier).
* **Low volatility** → cash flow is stable (more predictable).

**How FCF Volatility is calculated**

a) Gather a free cashflow time series

$$
\text{Collect FCF for n consecutive (five annual) periods:  }  \text{FCF}_1,\;\text{FCF}_2,\;\dots,\;\text{FCF}_n
$$

b) Compute the standard deviation (σ)

$$
\sigma_{\text{FCF}} = \sqrt{\frac{1}{n-1}\sum_{i=1}^n\bigl(\text{FCF}_i - \bar{\text{FCF}}\bigr)^2}
$$

where $\bar{\text{FCF}}$ is the average free cash flow over those $n$ years.

c) Normalize with the Coefficient of Variation (CV) to express volatility relative to scale, divide by the mean:

$$
 \text{CV}_{\text{FCF}} = \frac{\sigma_{\text{FCF}}}{\bar{\text{FCF}}}
$$

This yields a **unit-less** ratio (shown as a percentage).

### Scoring Rules
  * If ratio <= 10, score = 100
  * If ratio between 10 and 250, score = linearly scale 100→10
  * If ratio >= 250, score = 10


## 8. Revenue Drawdown 

The **revenue drawdown ratio** measures the peak-to-trough decline in a company’s revenue over a given period, showing how severely sales fall during downturns before recovering. It’s a key indicator of business resilience and the stability of a firm’s top line across economic cycles. A 10% drawdown, for example, means revenue dropped 10% from its prior high before rebounding. Smaller drawdowns suggest durable demand and strong competitive positioning, while larger ones signal vulnerability to cyclical or structural shocks. It is calculated as:

1. **Gather a revenue time series**

   $$
   R_1, R_2, \dots, R_n
   $$

   where $R_i$ is revenue in period $i$.

2. **Identify peaks and troughs**

   * **Peak ($P$)**: the highest revenue value before a decline.
   * **Trough ($T$)**: the lowest point reached after that peak, before revenue rebounds or the period ends.

3. **Compute drawdown**

   $$
   \text{Drawdown} = \frac{P - T}{P} \times 100\%
   $$

   * **Numerator**: magnitude of the drop (peak minus trough).
   * **Denominator**: peak level (to normalize the drop).

### Scoring Rules
  * If ratio <= 5, score = 100
  * If ratio between 5 and 20, score = linearly scale 100→10
  * If ratio >= 20, score = 10

## 9. Quick Ratio

The **quick ratio (also known as the acid-test ratio)** measures a company’s ability to meet its short-term liabilities using only its most liquid assets—cash, marketable securities, and receivables—while excluding inventory. It assesses how quickly a firm could cover its current obligations without relying on selling inventory or raising new funds. A 1.0 quick ratio means the company has exactly enough liquid assets to pay off its short-term debts; above 1.0 is generally considered healthy, while below 1.0 may indicate potential liquidity strain. It is calculated as:

$$
\text{Quick Ratio} = 
\frac{\text{Cash + Cash Equivalents + Marketable Securities + Accounts Receivable}}
     {\text{Current Liabilities}}
$$

 **Or equivalently:**

$$
\frac{\text{Current Assets} - \text{Inventory}}
     {\text{Current Liabilities}}
$$

1. **Cash & Cash Equivalents**: Ready cash or assets that can be converted to cash within 90 days.
2. **Marketable Securities**: Short-term investments you can quickly sell at fair value.
3. **Accounts Receivable**: Money owed by customers that you expect to collect soon.
4. **Current Liabilities**: Bills, loans, and other obligations due within one year.

### Scoring Rules
  * If ratio <= 50, score = 20
  * If ratio between 50 and 200, score = linearly scale 20→100
  * If ratio >= 200, score = 100




# **Dividend Policy Metrics**

These reflect *management intent and behavior* — how the company distributes cash to shareholders and its commitment to growing dividends. These show **management’s dividend philosophy** — whether it favors stable, growing, or aggressive payouts.

| #  | Metric                           | Description                                                |
| -- | -------------------------------- | ---------------------------------------------------------- |
| 1  | **Earnings Payout Ratio**        | Policy choice on how much profit is distributed.           |
| 2  | **Dividend Growth Ratio (CAGR)** | Trend of dividend increases over time.                     |
| 3  | **Dividend Growth Streak**       | Consistency of annual dividend increases.                  |
| 4  | **Dividend Yield**               | Current cash return level; reflects policy attractiveness. |
| 5  | **Buyback Yield**                | Complementary capital-return mechanism to dividends.       |


## 1. Earnings Payout Ratio

The **earnings payout ratio** (often called the **dividend payout ratio**) measures the portion of a company’s net income that’s paid out as dividends. It is calculated on on a per-share basis:

 $$
 \text{Earnings Payout Ratio} = \frac{\text{Annual Dividends per Share}} {\text{Annual Earnings per Share}}
 $$

 1. **Annual Dividends per Share**: the total cash dividends paid per share over a year.
 2. **Annual Earnings per Share**: is the company’s net income divided by the number of outstanding shares over a year.

### Scoring Rules
  * If ratio <= 0, score = 100
  * If ratio between 0 and 120, score = linearly scale 100→10
  * If ratio >= 120, score = 10


## 2. Dividend Growth Ratio

The **dividend growth ratio** measures how quickly a company’s dividend per share increases over time, reflecting management’s confidence in future earnings and cash flow stability. Consistent dividend growth signals strong financial health, disciplined capital allocation, and a shareholder-friendly policy. A 5% annual growth rate, for example, means dividends are rising steadily year after year—enhancing long-term income and total return potential. Stagnant or negative growth can point to financial strain or shifting priorities. It is typically calculated as the compound annual growth rate (CAGR) of dividends per share over a multi-year period.

**Compound Annual Growth Rate (CAGR)**: For a multi-year span ($n$ years), CAGR smooths out volatility:

   $$
   \text{Dividend CAGR} = \biggl(\frac{D_{\!n}}{D_{0}}\biggr)^{\tfrac{1}{n}} - 1
   $$

   * $D_{0}$: Dividend per share at the start.
   * $D_{n}$: Dividend per share after $n$ years.


### Scoring Rules
  * If ratio <= 0, score = 0
  * If ratio between 0 and 150, score = linearly scale 0→100
  * If ratio >= 150, score = 100



## 3. Dividend Growth Streak

The **dividend growth streak** measures the number of consecutive years a company has increased its dividend per share without a cut or pause. It’s a hallmark of financial discipline and management’s long-term commitment to rewarding shareholders through all market conditions. A long streak—say, 10+ years—signals consistent profitability, prudent cash management, and strong cash flow reliability. Conversely, a break in the streak can indicate financial pressure or shifting capital priorities. Investors often view extended streaks as a mark of quality and stability. It is calculated as the count of uninterrupted annual dividend increases over time.

**How It’s Calculated**

1. **Gather Annual Dividends**: List the dividend per share (DPS) paid each year for the period you’re examining:

   $$
   D_0,\; D_1,\; D_2,\;\dots,\; D_n
   $$
2. **Compare Year-to-Year**: Starting from the earliest year, check whether

   $$
   D_{i} > D_{i-1}
   $$

   for each consecutive pair.
3. **Count Consecutive Increases**:

   * **Streak** = the longest run of years where each year’s dividend was strictly higher than the prior year’s.
   * If you hit a year $D_{k} \le D_{k-1}$, the streak ends there.

### Scoring Rules
  * If ratio <= 0, score = 0
  * If ratio between 0 and 10, score = linearly scale 0→100
  * If ratio >= 10, score = 100

## 4. Dividend Yield

The dividend yield measures the annual dividend income an investor receives relative to the stock’s current market price, expressed as a percentage. It shows how much cash return you’re earning per dollar invested in the company’s shares. A 4% dividend yield, for instance, means you earn £4 annually for every £100 invested, assuming the dividend remains constant. Higher yields can look attractive but may signal elevated risk or an unsustainably high payout, while lower yields often reflect stable, growing companies that reinvest for future gains. It is calculated as:

**How It’s Calculated**

$$
 \text{Dividend Yield} = \frac{\text{Annual Dividends per Share}}{\text{Current Share Price}} \times 100\%
$$

1. **Annual Dividends per Share**: Often the sum of the last four quarterly payouts (trailing yield). Or management’s forward guidance for the next 12 months (forward yield).

2. **Current Share Price**: The market price you’d pay today for one share.


**Key Tips:**

* Compare yield to the company’s **payout ratio** and **free cash flow** to ensure sustainability.
* Track both **trailing** and **forward** yields—management may guide higher or lower payouts ahead.
* Use yield alongside **total return** (price appreciation + dividends) for a full picture of investment performance.

### Scoring Rules
  * If ratio <= 0, score = 0
  * If ratio between 0 and 10, score = linearly scale 0→100
  * If ratio >= 10, score = 100

## 5. Buyback Yield

The **buyback yield** measures how much of a company’s market capitalization is being repurchased through share buybacks over a given period, expressed as a percentage. It reflects how aggressively management is returning capital to shareholders by reducing the number of shares outstanding—thereby boosting metrics like earnings per share (EPS) and ownership value. A 3% buyback yield, for example, means the company has repurchased shares equal to 3% of its market value within a year. High buyback yields indicate strong cash generation and shareholder focus, while low or negative yields may suggest limited capital flexibility or dilution from new share issuance. It is calculated as:


1. **Total Buyback Amount**

   $$
   \text{Buyback Amount} 
   = \sum (\text{Shares Repurchased}_i \times \text{Price Paid}_i)
   $$

   * Sum across all repurchase transactions in a period (often disclosed on the cash-flow statement).

2. **Buyback Yield** (a normalized measure)

   $$
   \text{Buyback Yield} = \frac{\text{Total Buyback Amount}}{\text{Average Market Capitalisation}} \times 100\%
   $$

   * **Average Market Cap**: often the mean of the period’s opening and closing market caps.
   * Expressed as a percentage of the company’s size, letting you compare buyback intensity across firms.

3. **Shares Outstanding Reduction**

   $$
   \Delta \text{Shares} = \text{Shares Before} - \text{Shares After}
   $$

   * You can track the percentage drop in shares: $\frac{\Delta \text{Shares}}{\text{Shares Before}}\times100\%$.

### Scoring Rules
  * If ratio <= 1, score = 0
  * If ratio between 1 and 3, score = linearly scale 0→100
  * If ratio >= 3, score = 100

  
## Aggregate Score 

The following is the weightings on each of the criteria to create the overall dividen growth score.


| #  | Score                              | Weight (%) |
| :- | ---------------------------------- | :--------: |
| 1  | `earnings_payout_ratio_score`      |   3        |
| 2  | `fcf_payout_ratio_score`           |   8        |
| 3  | `cash_payout_ratio_score`          |   3        |
| 4  | `debt_to_equity_ratio_score`       |   5        |
| 5  | `interest_coverage_ratio_score`    |   5        |
| 6  | `cash_interest_coverage_ratio`     |   5        |
| 7  | `cash_dividend_coverage_ratio`     |   10       |
| 8  | `fcf_volatility_ratio_score`       |   8        |
| 9  | `dividend_growth_CAGR_5yr_score`   |   15       |
| 10 | `dividend_ttm_growth_streak_score` |   10       |
| 11 | `dividend_yield_ratio_score`       |   15       |
| 12 | `share_buyback_yield_ratio_score`  |   5        |
| 13 | `revenue_drawdown_ratio_score`     |   5        |
| 14 | `quick_ratio_score`                |   3        |

# some usefule improvements

### 🔍 **1. Improve Scaling and Thresholds**

**Issue:** Many ratios use static linear scales (e.g., “linearly scale 100→10 from 0–120”) that may not reflect distributional reality.
**Suggestion:**

* **Calibrate thresholds empirically** — use historical distributions (e.g., 10-year sector medians) to define cutoffs.
* **Use nonlinear scaling**, e.g., logistic or sigmoid scoring functions, to dampen extremes instead of linear cutoffs.
* **Sector normalization:** Compare each company to its **industry peers**, not absolute values (e.g., REITs and utilities naturally have higher payout ratios).

### 💰 **2. Distinguish Between Payout Capacity vs. Policy**

**Issue:** The model mixes “capacity” ratios (e.g., FCF coverage, leverage) with “policy” ratios (payout %, yield, growth) in a single composite.
**Suggestion:**

* Create **two sub-scores**:

  * **Financial Sustainability Score** (capacity): FCF, debt, coverage, liquidity.
  * **Dividend Policy Score** (behavior): yield, payout, growth streaks.
* Combine them with weighted blending (e.g., 70% capacity, 30% policy).
  This separation mirrors institutional dividend quality models (e.g., S&P Dividend Aristocrats methodology).

---

### 🧮 **3. Strengthen Volatility and Drawdown Metrics**

**Issue:** Free cash flow volatility and revenue drawdown are excellent inclusions, but they’re **point-in-time** or limited in period.
**Suggestion:**

* Use **rolling 5-year standard deviations** for both FCF and revenue, normalized by mean values.
* Add **earnings volatility** or **operating margin stability** as additional resilience measures.
* Consider a **Z-score-based stability index**, where each volatility metric is standardized before aggregation.

---

### 🧱 **4. Add Coverage and Leverage Refinements**

**Improvements:**

* Replace or supplement **Debt-to-Equity** with **Net Debt / EBITDA**, which better reflects leverage for capital-intensive sectors.
* Replace **Interest Coverage (EBIT/Interest)** thresholds with dynamic bands based on sector norms.
* Add **Free Cash Flow to Debt Ratio**, a common institutional solvency indicator.

---

### 📈 **5. Dividend Growth and Yield Interplay**

**Issue:** High yield + high growth is rare and sometimes a red flag.
**Suggestion:**

* Introduce a **yield-growth consistency score**:
  [
  \text{Consistency} = 1 - \frac{|z_{\text{yield}} + z_{\text{growth}}|}{2}
  ]
  This rewards sustainable combinations (e.g., moderate yield + steady growth).

---

### 🧠 **6. Weight Optimization**

**Issue:** The current weights appear reasoned but manually chosen.
**Suggestion:**

* Run **backtesting or feature importance analysis** (e.g., Random Forest or LASSO regression) using historical dividend cut data to optimize weights objectively.
* Use **principal component analysis (PCA)** to check for redundancy between highly correlated metrics (e.g., payout ratios and cash coverage).

---

### 🧩 **7. Extend the Model with Market-Sensitivity Factors**

To link dividend stability to external risk:

* Add **Beta** or **Downside Capture Ratio** to measure market cyclicality.
* Include **Distance to Default** (via Merton model) for a credit-based stress indicator.
* Add **Dividend-to-FCF correlation** to detect payout rigidity (i.e., dividends maintained despite volatile cash flow).

---

### 🧾 **8. Improve Interpretability and UI Integration**

For end-users or dashboard presentation:

* Normalize all sub-scores to a 0–100 scale with labels:

  * 80–100 = “Very Safe”
  * 60–79 = “Stable”
  * 40–59 = “Moderate Risk”
  * <40 = “High Risk”
* Provide a **radar chart visualization** across dimensions:
  `Liquidity | Leverage | Coverage | Volatility | Growth | Yield`

---

### 🧩 **9. Expand Dataset Sources**

Enhance data reliability and cross-validation:

* Pull multi-source data (Morningstar, Alpha Vantage, Yahoo Finance, Finviz).
* Use **TTM + 5-year averages** for smoothing.
* Flag **data gaps or anomalies** (e.g., negative FCF years) with score penalties.

---

### ⚙️ **10. Implementation Enhancements**

If this model is to be integrated into your DDH (Digital Data Hub):

* Store formulas and weight configurations in a **JSON config file** for version control (you’ve already started that with `ScoreDTO` work).
* Implement scoring in **modular Python classes**, e.g.:

  ```python
  class DividendSafetyModel:
      def __init__(self, metrics: dict):
          self.metrics = metrics
      def compute_subscores(self) -> dict: ...
      def aggregate_score(self, weights: dict) -> float: ...
  ```

---

### 🧭 Summary of Recommended Additions

| New Metric                      | Purpose                 | Benefit                              |
| ------------------------------- | ----------------------- | ------------------------------------ |
| Net Debt / EBITDA               | True leverage           | Sector-agnostic solvency view        |
| FCF to Debt Ratio               | Debt coverage           | Measures flexibility                 |
| Yield-Growth Consistency        | Quality of return       | Penalizes unsustainable combinations |
| Earnings Volatility             | Profit stability        | Complements FCF volatility           |
| Beta / Downside Capture         | Market sensitivity      | Adds resilience layer                |
| Data-Driven Weight Optimization | Statistical calibration | Improves predictive power            |

---

Would you like me to **produce a revised model table** (v2) with updated metrics, weights, and improved scoring ranges to reflect these enhancements?


# some useful dashboards

https://www.dividend.com/stocks/financials/insurance/life-insurance/afl-aflac/

## Best Dividend Protection Stocks

Targeting very safe dividends to preserve capital and beat the savings rate. Updated daily, only the very best make it through the industry’s strictest safe dividend screening test and manual selection process. If you don't want the low savings rate to erode your hard-earned capital, this portfolio of reliable and very safe dividends is for you. Read more below*.  https://www.dividend.com/best-dividend-protection-stocks/

https://www.investopedia.com/articles/markets/060116/4-ratios-evaluate-dividend-stocks.asp?utm_source=chatgpt.com

When you’re building a dividend‐focused dashboard, you’ll want sources that not only report the raw numbers (yield, DPS, payout) but also contextualize them with coverage ratios, cash‐flow metrics, debt servicing, growth rates and volatility indicators. Here are several publicly accessible sites that offer rich dividend dashboards or stock‐level profiles featuring exactly the kinds of ratios and visualizations you need:

1. **Dividend.com**

   * **Overview page** shows Yield, Forward Dividend, Payout Ratio, Dividend Growth, Income Ratings and more in a tabular view ([Dividend][1]).
   * **Stock profiles** include a “Payout” tab with historical payout ratios vs. earnings and free cash flow (FCF), plus a “Dividend Growth” chart that tracks rolling annual increases.
   * **Risk section** highlights Beta (volatility) and correlation metrics alongside payout sustainability ([Dividend][2]).

2. **Simply Wall St**

   * **Dividend Tracker** (free feature) aggregates your positions and forecasts annual/monthly income, current yield on cost, and 3+-year dividend forecasts ([Simply Wall St][3]).
   * **Individual stock pages** (e.g. Rithm Capital) display:

     * Dividend Yield & Growth (%)
     * Payout Ratio vs. Earnings and Cash Flow Coverage
     * Volatility assessment (“Stable/Volatile” flags)
     * Debt service metrics like Cash Flow/Total Debt and Interest Coverage ([Simply Wall St][4]).

3. **Yahoo Finance**

   * **Statistics** tab for any ticker includes:

     * Payout Ratio (TTM)
     * Forward Dividend & Yield
     * Times Interest Earned (in Key Metrics)
     * Free Cash Flow (Annual)
   * **Analysis** and **Financials** tabs let you drill into Income, Cash Flow, and Balance Sheet items to compute your own coverage ratios ([Investopedia][5]).

4. **Investopedia’s “4 Ratios to Evaluate Dividend Stocks”**

   * Outlines and defines the core metrics you’ll want to display:

     * Dividend Payout Ratio
     * Dividend Coverage Ratio
     * Free Cash Flow to Equity (FCFE) Ratio
     * Net Debt to EBITDA (and Interest Coverage) ([Investopedia][6]).

5. **Morningstar (Global site)**

   * **Dividend Safety** and **Dividend Growth** scores integrate:

     * Payout Ratio vs. FCF
     * Interest Coverage (EBIT/Interest)
     * Net Debt/EBITDA
     * Volatility factors (Distance to Default, Beta proxies) ([go.morningstar.com.au][7]).
   * Many widgets and charts require sign-up, but high-level ratio tables are viewable publicly.

6. **Wikipedia (for metric definitions)**

   * **Dividend payout ratio** – formula DPS/EPS and interpretation ([Wikipedia][8]).
   * **Dividend cover** (coverage ratio) – EPS divided by dividend per share ([Wikipedia][9]).
   * **Cash‐flow‐to‐debt ratio** and **Debt Service Coverage Ratio** – key leverage metrics ([Wikipedia][10]).
   * **Times interest earned (Interest Coverage)** – EBIT ÷ Interest Expense ([Wikipedia][11]).

---

**Dashboard‐design tips**

* **Combine multiple sources**: use Dividend.com or Simply Wall St widgets for high‐level visuals, and link through to Yahoo Finance or Morningstar for deep dives.
* **Interactive filters**: allow users to toggle between Payout vs. EPS, FCF, Cash Flow or Coverage ratios.
* **Volatility overlays**: plot historical yield alongside Beta or standard deviation (from Dividend.com’s risk section) to see how payouts fluctuate with market swings.
* **Growth vs. Yield scatter**: chart dividend growth rate on one axis and current yield on the other; annotate points by debt service metrics.

This selection will give you both the raw data and the contextual analytics to build a best-in-class dividend dashboard.

[1]: https://www.dividend.com/?utm_source=chatgpt.com "Dividend.com - Dividend Stocks - Ratings, News, and Opinion ..."
[2]: https://www.dividend.com/dividend-education/a-dividend-investors-guide-to-measuring-risk/?utm_source=chatgpt.com "Measuring & Managing Risk: A Dividend Investor's Guide"
[3]: https://simplywall.st/feature/dividend-tracker?utm_source=chatgpt.com "Stock Portfolio & Dividend Tracker"
[4]: https://simplywall.st/stocks/us/diversified-financials/nyse-ritm/rithm-capital/dividend?utm_source=chatgpt.com "Rithm Capital (NYSE:RITM) Dividend Yield, History and ..."
[5]: https://www.investopedia.com/terms/p/payoutratio.asp?utm_source=chatgpt.com "Payout Ratio: What It Is, How to Use It, and How to Calculate It - Investopedia"
[6]: https://www.investopedia.com/articles/markets/060116/4-ratios-evaluate-dividend-stocks.asp?utm_source=chatgpt.com "4 Ratios to Evaluate Dividend Stocks"
[7]: https://go.morningstar.com.au/lp-investor-stocks-dividend-highest-dki-v2?utm_source=chatgpt.com "Highest Yielding Dividend Stocks"
[8]: https://en.wikipedia.org/wiki/Dividend_payout_ratio?utm_source=chatgpt.com "Dividend payout ratio"
[9]: https://en.wikipedia.org/wiki/Dividend_cover?utm_source=chatgpt.com "Dividend cover"
[10]: https://en.wikipedia.org/wiki/Cash-flow-to-debt_ratio?utm_source=chatgpt.com "Cash-flow-to-debt ratio"
[11]: https://en.wikipedia.org/wiki/Times_interest_earned?utm_source=chatgpt.com "Times interest earned"


