# 📘 MVPS-Driven Allocation Tilt Strategy

---

## 🎯 Goal

Use the Market Valuation Pendulum Score (MVPS) to guide quarterly portfolio rebalancing. When markets are cheap, increase equity exposure; when expensive, reduce equities and add bonds/cash.

---

## 🔑 Inputs

1. Portfolio Data (your actual holdings):
   - Asset classes: Equities, Bonds, Alternatives (REITs, Gold, etc.), Cash.
   - Current weights.
   - Position-level granularity optional (rebalance applies at asset-class level).
2. Market Valuation Pendulum Score (MVPS) — calculated quarterly using Alpha Vantage data:
   - Forward P/E → from EARNINGS & index price.
   - ERP → (1/Forward P/E) – 10Y yield (TREASURY_YIELD).
   - Buffett Indicator → Market Cap / GDP (OVERVIEW, REAL_GDP).
   - Credit Spreads → proxy (if available).
3. Rebalance Frequency: Quarterly (end of Mar, Jun, Sep, Dec).

---

## 📐 MVPS Interpretation & Allocation Rules

| MVPS Range | Market Regime         | Equity Weight        | Bond Weight | Cash/Alts |
|------------|----------------------|----------------------|-------------|-----------|
| < -0.5     | Deeply Undervalued    | +20% above baseline  | -10%        | -10%      |
| -0.5 to 0.0| Slightly Undervalued  | +10% above baseline  | -5%         | -5%       |
| 0.0 to 0.5 | Fair/Moderate Value   | Neutral (baseline)   | Neutral     | Neutral   |
| > 0.5      | Overvalued           | -15% below baseline  | +10%        | +5%       |
| > 0.75     | Extremely Overvalued | -25% below baseline  | +15%        | +10%      |

- Baseline = target allocation (e.g., 60% equities, 30% bonds, 10% cash/alts).
- Adjustments apply relative to baseline.

---

## ⚙️ Quarterly Rebalancing Logic

1. Compute latest MVPS (using Alpha Vantage data).
2. Map MVPS → regime → target allocation weights.
3. Compare target weights vs current portfolio weights.
4. Generate rebalance trades:
   - If deviation > 3% per asset class → rebalance.
   - Otherwise → leave unchanged (to avoid churn).
5. Output = Recommended trades (buy/sell amounts).

---

## 🖥️ System Output Example

Inputs:
- Baseline: 60% Equities, 30% Bonds, 10% Cash.
- Current Portfolio: 65% Equities, 25% Bonds, 10% Cash.
- MVPS = +0.6 (Overvalued).

Target Allocation (Rule): 45% Equities, 40% Bonds, 15% Cash.

Trades:
- Sell equities: -20% of portfolio.
- Buy bonds: +15% of portfolio.
- Increase cash: +5% of portfolio.

---

## 🔍 Risk Controls

- Max quarterly shift in equities = ±20% of portfolio.
- Cash floor = 5% minimum.
- Don’t rebalance more than once per quarter (no overtrading).

---

## 🚀 Extensions (Phase 2)

- Layer trend filter: only cut equities if MVPS > 0.5 and price < 200-day MA.
- Factor tilt: in expensive regimes, overweight value/defensives.
- Hedge overlay: add VIX calls when MVPS > 0.75.

---

👉 Todd, would you like me to write a Python prototype that:
- Takes a portfolio JSON/CSV as input,
- Pulls Alpha Vantage data to compute MVPS,
- And outputs target weights + rebalance trades each quarter?

That way you’d have a backtestable engine, not just the spec.

