# Rules

# Rules Dashboard

## User Stories for Dashboard Visualization

1. 🟢 **As a Portfolio Manager, I want to see a time series chart of Dividend Yield for each stock, with the 5-year historical mean and +1σ threshold overlaid, so I can visually identify when the yield signals undervaluation and when the rule is triggered.**

   * **Acceptance**: Line chart of dividend yield over time, with horizontal lines for mean and mean +1σ, and markers or shading where the rule is met.

2. 🟢 **As a Portfolio Manager, I want to see a time series of Dividend Growth Rate, with a threshold line at 5% (or user-defined), so I can track dividend growth trends and spot when the rule is satisfied.**

   * **Acceptance**: Line chart of annual dividend growth rate, with a threshold line and visual indication when the rule is met.

3. 🟢 **As a Portfolio Manager, I want to see a time series of the Chowder Rule (Dividend Yield + Dividend Growth Rate), with a threshold at 12%, to quickly identify periods when the combined metric meets the rule.**

   * **Acceptance**: Line chart of Chowder Rule value, with a threshold line and highlights for rule compliance.

4. 🟢 **As a Portfolio Manager, I want to see a time series of Fair Value Gap (%) for each stock, with a threshold at -20%, so I can monitor when the stock is undervalued according to DCF/DDM.**

   * **Acceptance**: Line chart of fair value gap, with a threshold line and visual cues for rule triggers.

5. 🟢 **As a Portfolio Manager, I want to see a time series of P/E Ratio versus Peer Group Median, with a shaded area or line for the median, so I can see when the stock’s P/E is below the peer median and the rule is met.**

   * **Acceptance**: Dual line chart (stock P/E and peer median), with highlights where the rule is satisfied.

6. 🟢 **As a Portfolio Manager, I want to see a time series of PEG Ratio, with a threshold at 1.0, so I can track valuation relative to growth and spot when the rule is attractive.**

   * **Acceptance**: Line chart of PEG ratio, with a threshold line and markers for rule compliance.

7. 🟢 **As a Portfolio Manager, I want to see a time series of EBITDA to Free Cash Flow ratio, with thresholds at 0.4 and 0.6, to monitor cash conversion efficiency and when the rule is satisfied.**

   * **Acceptance**: Line chart with two threshold lines (0.4, 0.6) and shading or markers for in-range periods.

8. 🟢 **As a Portfolio Manager, I want to see a time series of Earnings Yield versus Bond Yield + 2%, so I can visually compare the stock’s yield to the risk-free benchmark and see when the rule is met.**

   * **Acceptance**: Dual line chart (earnings yield and bond yield + 2%), with highlights for rule compliance.

9. 🟢 **As a Portfolio Manager, I want to see a time series of Debt to Fair Value Equity ratio, with a threshold at 0.5, to monitor leverage and when the rule is satisfied.**

   * **Acceptance**: Line chart of debt/equity ratio, with a threshold line and visual indication of rule compliance.

10. 🟢 **As a Portfolio Manager, I want to see a time series of Insider Ownership (%), with a threshold at 5%, to track when insider ownership meets the “skin in the game” rule.**

    * **Acceptance**: Line chart of insider ownership, with a threshold line and markers for rule compliance.

11. 🟢 **As a Portfolio Manager, I want to see a time series of Moat Score, with a threshold at 4, to monitor when the company is rated as having a wide economic moat.**

    * **Acceptance**: Line chart of moat score, with a threshold line and highlights for rule compliance.

---

*Each chart should allow the user to select the stock, adjust the threshold if desired, and clearly indicate periods where the rule is satisfied (e.g., with color, markers, or shading).*

# Dashboard


1. 🔴 **As a Portfolio Manager**, I want a Streamlit dashboard showing the ranked “buy” candidates with their composite score, fair value gap, and moat rating so that I can filter and export them.

   * **Acceptance**: Interactive table with sorting, filters, and CSV download.


