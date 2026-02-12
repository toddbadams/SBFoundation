## Empirical Sector Baselines

The **Empirical Sector Baselines** define the **distributional reference points** used to score each company’s financial ratios within its **sector context**.
Rather than applying fixed global thresholds, this method uses **historical sector-level statistics** (over a rolling 10-year window) to derive **percentiles, medians, and dispersion measures** for each ratio.

This ensures that scoring reflects the **typical operating norms** of each industry — for example, utilities and REITs naturally maintain higher payout and leverage ratios than technology firms, so their benchmarks must differ.

These baselines provide the foundation for **sector‐normalized**, **nonlinear scoring functions** (e.g., logistic or percentile‐based) that better capture the real‐world risk distribution of each metric.

### How It’s Calculated

For each sector ( s ), metric ( M ), and 10-year observation window:

1. **Collect** all historical metric values:

 $$
   [
   M_{s,1},, M_{s,2},, \dots,, M_{s,n}
   ]
 $$

2. **Compute central tendency and dispersion:**

   * **Median:**
 $$
     [
     \tilde{M}*s = \operatorname{median}(M*{s,i})
     ]
 $$
   * **Mean:**
 $$
     [
     \bar{M}*s = \frac{1}{n}\sum*{i=1}^n M_{s,i}
     ]
 $$
   * **Median Absolute Deviation (MAD):**
 $$
     [
     \text{MAD}*s = \operatorname{median}!\bigl(|M*{s,i} - \tilde{M}_s|\bigr)
     ]
 $$

3. **Compute key percentile thresholds** (for scoring calibration):
 $$
   [
   P_{s,q} = \operatorname{Quantile}(M_{s,i},, q)
   ]
   \text{  } where ( q \in {1, 5, 10, 25, 50, 75, 90, 95, 99} ).
 $$

4. **Store these baseline statistics** per sector in a reference table, e.g.:

| Sector     | Median |  MAD |  P10 |  P25 |  P50 |  P75 |  P90 | Mean |  Std |
| :--------- | :----: | :--: | :--: | :--: | :--: | :--: | :--: | :--: | :--: |
| Utilities  |  68.2  | 12.5 | 45.1 | 58.7 | 68.2 | 77.9 | 89.4 | 69.3 | 13.2 |
| Technology |  32.7  |  8.1 | 18.4 | 26.1 | 32.7 | 39.5 | 47.8 | 33.0 |  8.3 |

---

### Why It Matters

* **Contextual scoring:** Adjusts for structural sector differences.
* **Dynamic thresholds:** Updates automatically as distributions shift.
* **Robustness:** Uses **median** and **MAD** instead of mean/std to reduce outlier sensitivity.
* **Foundation for normalization:** Enables both **logistic** and **percentile-based** scoring curves to adapt per sector.

---

### Usage in Scoring Functions

Once baselines are computed, they feed directly into the scoring functions:

* **Logistic scaling** (using sector median and MAD):
 $$
  [
  \text{Score} = \frac{100}{1 + e^{k(M - \tilde{M}_s)}}
  \quad \text{where} \quad
  k = \frac{c}{1.4826 \times \text{MAD}_s}
  ]
 $$

* **Percentile scaling** (sector-relative linear map):
 $$
  [
  \text{Score} =
  \begin{cases}
  100, & M \le P_{s,10} \
  100 - 90 \times \dfrac{M - P_{s,10}}{P_{s,90} - P_{s,10}}, & P_{s,10} < M < P_{s,90} \
  10, & M \ge P_{s,90}
  \end{cases}
  ]
 $$


