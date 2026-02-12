# Magic Formula Equity Selection 

The Magic Formula, developed by hedge fund manager and Columbia professor Joel Greenblatt, is a simple yet powerful investing strategy designed to systematically identify high-quality companies trading at attractive prices. Introduced in his book "The Little Book That Beats the Market", the formula ranks stocks based on two key metrics: return on capital (quality) and earnings yield (value). By combining these into a composite score, the strategy seeks to buy good businesses at bargain prices — a practical, rules-based expression of value investing principles grounded in decades of market research and behavioral finance insights.

| **Factor**           | **Formula**                                      | **Purpose**            |
| -------------------- | ------------------------------------------------ | ---------------------- |
| ROC                  | NOPAT / Invested Capital                         | Capital efficiency     |
| GPA                  | Gross Profit / Total Assets                      | Profitability          |
| Earnings Yield (EY)  | Earnings / Market Cap or EBIT / Enterprise Value | Valuation              |
| Book-to-Market (B/M) | Book Value / Market Cap                          | Valuation (deep value) |


## Return on Capital (ROC)

**Formula:**

```
ROC = NOPAT / Invested Capital
```

* **NOPAT** = EBIT × (1 - Tax Rate)
* **Invested Capital** = Total Assets - Current Liabilities - Cash & Equivalents

**TTM Implementation:**

```python
df['NOPAT'] = df['EBIT'] * (1 - df['TaxRate'])
df['NOPAT_TTM'] = df['NOPAT'].rolling(4).sum()

df['InvestedCapital'] = df['TotalAssets'] - df['CurrentLiabilities'] - df['CashEquivalents']
df['Avg_InvestedCapital_TTM'] = df['InvestedCapital'].rolling(4).mean()

df['ROC_TTM'] = df['NOPAT_TTM'] / df['Avg_InvestedCapital_TTM']
```

---

## Gross Profitability (GPA)

**Formula:**

```
GPA = Gross Profit / Total Assets
```

* **Gross Profit** = Revenue - COGS

**TTM Implementation:**

```python
df['GrossProfit'] = df['Revenue'] - df['COGS']
df['GrossProfit_TTM'] = df['GrossProfit'].rolling(4).sum()

df['Avg_TotalAssets_TTM'] = df['TotalAssets'].rolling(4).mean()
df['GPA_TTM'] = df['GrossProfit_TTM'] / df['Avg_TotalAssets_TTM']
```



## Earnings Yield (EY)

### Option A: Net Income version

**Formula:**

```
EY = Net Income (TTM) / Market Capitalization
```

```python
df['Earnings_TTM'] = df['NetIncome'].rolling(4).sum()
df['EarningsYield'] = df['Earnings_TTM'] / df['MarketCap']
```

### Option B: EBIT / Enterprise Value (Magic Formula style)

**Formula:**

```
EY = EBIT (TTM) / Enterprise Value
```

```python
df['EBIT_TTM'] = df['EBIT'].rolling(4).sum()
df['EnterpriseValue'] = df['MarketCap'] + df['TotalDebt'] - df['CashEquivalents']
df['EY_EBIT_EV'] = df['EBIT_TTM'] / df['EnterpriseValue']
```

---

## 📘 4. Book-to-Market Ratio (B/M)

**Formula:**

```
B/M = Book Value of Equity / Market Capitalization
```

* **Book Value** = Total Assets - Total Liabilities (or Shareholders’ Equity)

```python
df['BookValue'] = df['TotalAssets'] - df['TotalLiabilities']
# Or use: df['BookValue'] = df['ShareholdersEquity']

df['BookToMarket'] = df['BookValue'] / df['MarketCap']
```

### Optional: Tangible Book-to-Market

```python
df['TangibleBook'] = df['TotalAssets'] - df['TotalLiabilities'] - df['Intangibles'] - df['Goodwill']
df['BookToMarket_Tangible'] = df['TangibleBook'] / df['MarketCap']
```

---

## 🎯 Scoring (Normalized Ranks)

For each factor:

```python
df['Factor_Score'] = df['Factor'].rank(pct=True)
```

* Higher scores = more attractive
* Use for percentile-based ranking across universe

---

Let me know if you want this turned into YAML/JSON for API specs, or wrapped into a class-based Python module for your platform.
