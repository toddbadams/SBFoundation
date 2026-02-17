# Jamie Diamond's Six Economic Signals
## Data Acquisition & Signal Development Plan

**Purpose**: Implement data pipelines and analytics to monitor Jamie Diamond's six key economic warning signals that may indicate systemic financial stress and recession risk.

**Version**: 1.0
**Last Updated**: 2026-02-17
**Architecture Layer**: Bronze + Silver (data acquisition and conformed datasets)

---

## 1. Yield Curve Inversion

### What It Is
The yield curve represents the relationship between bond yields and their maturity dates. Under normal conditions, longer-term bonds have higher yields than short-term bonds (positive slope). **Inversion** occurs when short-term yields exceed long-term yields (negative slope), historically one of the most reliable recession indicators.

### Why It Matters
- **Banking profitability**: Banks borrow short-term (deposits) and lend long-term (mortgages, business loans). Inversion compresses net interest margins, reducing lending capacity
- **Economic signal**: Inverted curves have preceded every U.S. recession since 1955, typically 6-24 months before onset
- **Market psychology**: Indicates investors expect future rate cuts due to economic weakness

### Data Sources & Datasets

#### FRED (Federal Reserve Economic Data)
| Dataset | Series ID | Description | Frequency | Cadence |
|---------|-----------|-------------|-----------|---------|
| 10Y-2Y Spread | T10Y2Y | 10-Year minus 2-Year Treasury yield | Daily | Daily |
| 10Y-3M Spread | T10Y3M | 10-Year minus 3-Month Treasury yield | Daily | Daily |
| 10-Year Treasury | DGS10 | 10-Year constant maturity rate | Daily | Daily |
| 2-Year Treasury | DGS2 | 2-Year constant maturity rate | Daily | Daily |
| 3-Month Treasury | DGS3MO | 3-Month constant maturity rate | Daily | Daily |
| 1-Year Treasury | DGS1 | 1-Year constant maturity rate | Daily | Daily |

#### FMP (Financial Modeling Prep)
| Dataset | Endpoint | Description | Frequency |
|---------|----------|-------------|-----------|
| Treasury Rates | /v4/treasury | Full yield curve (1M-30Y) | Daily |
| Economic Indicators | /v4/economic?name=treasuryYield | Historical treasury yields | Daily |

### Features to Develop

**Level 1: Raw Spreads** (Bronze → Silver)
- `yield_spread_10y_2y`: 10Y - 2Y spread (basis points)
- `yield_spread_10y_3m`: 10Y - 3M spread (basis points)
- `yield_spread_10y_1y`: 10Y - 1Y spread (basis points)
- `yield_10y`, `yield_2y`, `yield_3m`, `yield_1y`: Absolute yields

**Level 2: Inversion Metrics** (Silver computed features)
- `is_inverted_10y2y`: Boolean flag (spread < 0)
- `is_inverted_10y3m`: Boolean flag
- `inversion_depth_bps`: Magnitude of inversion (max of all spreads if negative)
- `inversion_duration_days`: Consecutive days inverted
- `days_since_inversion`: Time since last inversion event

**Level 3: Trend Features** (Silver computed features)
- `spread_ma_20d`, `spread_ma_60d`: Moving averages
- `spread_slope_30d`: Rate of change (steepening/flattening)
- `spread_volatility_30d`: Standard deviation of spread
- `spread_percentile_1y`: Current spread vs. 1-year historical distribution

### Signals to Develop

**Signal 1: Inversion Alert** (Defensive)
- **Type**: Binary screener (risk-off trigger)
- **Logic**: `is_inverted_10y2y AND inversion_duration_days >= 5`
- **Action**: Reduce equity exposure, increase cash/short-term bonds
- **Backstop**: Exit when spread > +25 bps for 10 consecutive days

**Signal 2: Inversion Severity** (Directional)
- **Type**: Continuous signal (-100 to +100)
- **Formula**: `clip(-inversion_depth_bps / 2, -100, 0) + spread_slope_30d * 10`
- **Interpretation**: More negative = higher recession risk
- **Action**: Scale equity beta inversely to signal strength

**Signal 3: Curve Steepening Trade** (Tactical)
- **Type**: Mean-reversion signal
- **Logic**: Enter when `spread_percentile_1y < 10` (extremely flat/inverted)
- **Action**: Long 10Y bonds / short 2Y bonds (bet on eventual steepening)
- **Exit**: `spread_percentile_1y > 50` or maximum 180-day hold

### Implementation Plan
1. **Bronze Layer**: Ingest FRED T10Y2Y, T10Y3M, DGS10, DGS2, DGS3MO daily via `config/dataset_keymap.yaml`
2. **Silver Layer**: Create `silver.fred_treasury_yields` table with computed spreads
3. **Feature Pipeline**: Compute moving averages, percentiles, duration metrics
4. **Signal Pipeline**: (Gold layer, separate project) Implement three signals above
5. **Monitoring**: Alert on inversion events, track signal performance vs. SPY

---

## 2. Commercial Real Estate (CRE) Distress

### What It Is
Commercial real estate includes office buildings, retail centers, industrial warehouses, and multifamily properties. **Distress** occurs when property values decline, vacancies rise, and owners struggle to refinance maturing debt—often leading to defaults and foreclosures.

### Why It Matters
- **Systemic risk**: CRE represents ~$20T in value; banks hold ~$2.7T in CRE loans
- **Refinancing cliff**: ~$1.5T in CRE debt matures 2024-2027, much originated at near-zero rates (2020-2021)
- **Structural shift**: Permanent remote work reduced office demand by 15-30% in major metros
- **Banking exposure**: Regional banks are heavily exposed (40-50% of loan portfolios vs. 10% for large banks)

### Data Sources & Datasets

#### FRED (Macro indicators)
| Dataset | Series ID | Description | Frequency |
|---------|-----------|-------------|-----------|
| CRE Loan Delinquencies | DRSFRMACBS | Delinquency rate on CRE loans (all banks) | Quarterly |
| Office Vacancy Rate | (via private sources) | National office vacancy % | Quarterly |
| CMBS Delinquencies | DRCCLACBS | Commercial mortgage-backed security delinquencies | Monthly |
| Bank CRE Lending | TOTLL | Total loans and leases at commercial banks | Weekly |

#### FMP (Company-level exposure)
| Dataset | Endpoint | Description | Frequency |
|---------|----------|-------------|-----------|
| Bank Balance Sheets | /v3/balance-sheet-statement/{ticker} | CRE loan exposure by bank | Quarterly |
| REIT Financials | /v3/income-statement/{ticker} | Office REIT revenues, occupancy | Quarterly |
| Key Metrics | /v3/key-metrics/{ticker} | Debt-to-equity, interest coverage | Quarterly |
| Insider Trading | /v4/insider-trading | REIT insider selling (stress signal) | Real-time |

#### Private Data (future integration)
- **CoStar/Moody's**: Property-level vacancy, rent growth, cap rates
- **Trepp**: CMBS loan-level performance data
- **Green Street**: REIT net asset value (NAV) estimates

### Features to Develop

**Level 1: Macro Stress Indicators** (FRED → Silver)
- `cre_delinquency_rate_pct`: % of CRE loans 30+ days delinquent
- `cmbs_delinquency_rate_pct`: CMBS delinquency rate
- `cre_delinquency_yoy_chg`: Year-over-year change in delinquency rate
- `office_vacancy_rate_pct`: National office vacancy rate (if available)

**Level 2: Company Exposure Metrics** (FMP fundamentals → Silver)
- `cre_loans_to_assets_pct`: CRE loans / total assets (banks)
- `office_cre_pct`: Office CRE / total CRE (REITs, banks)
- `debt_maturity_2y_pct`: % of debt maturing in next 24 months (REITs)
- `interest_coverage_ratio`: EBITDA / interest expense
- `occupancy_rate_pct`: Current occupancy % (REITs)

**Level 3: Derived Stress Scores** (Silver computed)
- `cre_stress_index`: Composite of delinquency + vacancy + rate environment
- `refinancing_risk_score`: (Debt maturing 2Y × leverage ratio) / (property value × occupancy)
- `bank_cre_exposure_percentile`: Bank's CRE exposure vs. peer group
- `reit_distress_probability`: ML model based on coverage ratios, insider selling, NAV discount

### Signals to Develop

**Signal 1: CRE Macro Screener** (Defensive)
- **Type**: Binary sector filter
- **Logic**: `cre_delinquency_rate > 5% OR cre_delinquency_yoy_chg > 1%`
- **Action**: Exclude all REITs and regional banks from universe
- **Rationale**: Avoid sector when systemic stress is rising

**Signal 2: Bank CRE Exposure** (Stock-level defensive)
- **Type**: Continuous underweight signal
- **Logic**: Weight banks inversely to `bank_cre_exposure_percentile`
- **Formula**: `signal_weight = max(0, 1 - (cre_exposure_pct / 50))`
- **Action**: Underweight banks with >30% CRE exposure; exclude if >50%

**Signal 3: REIT Distress Fade** (Tactical short)
- **Type**: Short signal for distressed REITs
- **Entry**: `refinancing_risk_score > 75th percentile AND interest_coverage_ratio < 2.0`
- **Position**: Short or underweight office REITs
- **Exit**: Coverage ratio > 2.5 or 6-month hold limit

**Signal 4: Contrarian CRE Recovery** (Long-term)
- **Type**: Value signal for high-quality survivors
- **Entry**: After `cre_stress_index` peaks and declines 20%, buy REITs with:
  - Interest coverage > 3.0
  - Debt maturity > 3 years average
  - Occupancy > 85%
- **Rationale**: Post-crisis, high-quality CRE trades at discounts

### Implementation Plan
1. **Bronze Layer**: Ingest FRED CRE delinquency series (quarterly) and FMP balance sheets for banks/REITs
2. **Silver Layer**: Create `silver.fred_cre_macro` and `silver.fmp_cre_exposure` tables
3. **Universe Definition**: Tag banks with `industry=regional_bank` and REITs with `sector=real_estate`
4. **Feature Pipeline**: Compute exposure ratios, stress scores, percentile ranks
5. **Signal Pipeline**: Implement macro screener + stock-level signals
6. **Monitoring**: Track CRE delinquency trends, alert on >5% threshold

---

## 3. Consumer Debt Stress

### What It Is
Consumer debt stress occurs when households' debt service burden rises faster than income, leading to missed payments, defaults, and reduced consumption. Key categories: credit cards, auto loans, student loans, mortgages.

### Why It Matters
- **Consumption risk**: Consumer spending = 68% of U.S. GDP; debt stress reduces discretionary spending
- **Delinquency cascade**: Credit card → auto → mortgage delinquencies signal deteriorating financial health
- **Systemic indicator**: Rising delinquencies preceded 2008 crisis, COVID shock
- **Sector impact**: Banks, auto lenders, retailers, consumer discretionary stocks are exposed

### Data Sources & Datasets

#### FRED (Macro consumer debt)
| Dataset | Series ID | Description | Frequency |
|---------|-----------|-------------|-----------|
| Credit Card Delinquency | DRCCLACBS | % of credit card loans 30+ days delinquent | Quarterly |
| Auto Loan Delinquency | DRALSACBS | % of auto loans delinquent | Quarterly |
| Student Loan Delinquency | DRSLSACBS | % of student loans delinquent | Quarterly |
| Total Consumer Credit | TOTALSL | Total outstanding consumer credit | Monthly |
| Household Debt Service Ratio | TDSP | Debt payments / disposable income | Quarterly |
| Personal Savings Rate | PSAVERT | Personal savings / disposable income | Monthly |
| Consumer Credit Growth | CONSUMER (derived) | YoY growth in consumer credit | Monthly |

#### FMP (Company-level exposure)
| Dataset | Endpoint | Description | Frequency |
|---------|----------|-------------|-----------|
| Bank Financials | /v3/income-statement/{ticker} | Loan loss provisions, charge-offs | Quarterly |
| Auto Lender Metrics | /v3/key-metrics/{ticker} | Loan delinquency rates (F, GM Financial) | Quarterly |
| Retailer Comps | /v3/income-statement/{ticker} | Same-store sales growth | Quarterly |
| Consumer Discretionary Earnings | /v3/income-statement/{ticker} | Revenue growth, margin trends | Quarterly |

#### Alternative Data (future)
- **Credit bureau data**: TransUnion/Equifax credit score distributions
- **Buy-now-pay-later (BNPL)**: Affirm, Klarna delinquency rates
- **Transaction data**: Aggregated credit/debit card spend trends

### Features to Develop

**Level 1: Macro Debt Stress** (FRED → Silver)
- `credit_card_delinquency_pct`: % of credit card balances 30+ days delinquent
- `auto_loan_delinquency_pct`: % of auto loans delinquent
- `student_loan_delinquency_pct`: % of student loans delinquent
- `total_consumer_credit_bn`: Total outstanding consumer credit (billions)
- `debt_service_ratio_pct`: Household debt payments / disposable income
- `savings_rate_pct`: Personal savings rate
- `consumer_credit_yoy_growth`: Year-over-year growth in consumer credit

**Level 2: Composite Stress Metrics** (Silver computed)
- `consumer_stress_index`: Weighted composite of delinquency rates
  - Formula: `(CC_delinq × 0.4) + (auto_delinq × 0.3) + (student_delinq × 0.2) + (debt_service_ratio × 0.1)`
- `delinquency_acceleration`: 3-month change in composite delinquency rate
- `credit_growth_vs_income`: Consumer credit growth - wage growth (stress when positive)
- `savings_rate_decline_flag`: Boolean if savings rate < 5% or down 2%+ YoY

**Level 3: Company Exposure Metrics** (FMP → Silver)
- `loan_loss_provision_ratio`: Provision for credit losses / total loans (banks)
- `charge_off_rate_pct`: Net charge-offs / average loans (banks, auto lenders)
- `same_store_sales_growth_pct`: Comp sales growth (retailers)
- `discretionary_revenue_exposure_pct`: % of revenue from consumer discretionary

### Signals to Develop

**Signal 1: Consumer Stress Screener** (Defensive)
- **Type**: Binary sector filter
- **Logic**: `consumer_stress_index > 3.5 OR delinquency_acceleration > 0.5`
- **Action**: Underweight consumer discretionary, avoid subprime auto lenders
- **Exit**: Stress index < 2.5 for 2 consecutive quarters

**Signal 2: Bank Credit Quality** (Stock-level)
- **Type**: Continuous underweight for banks with deteriorating credit
- **Logic**: Underweight banks where `loan_loss_provision_ratio` is rising AND above sector median
- **Formula**: `signal = -1 × (provision_ratio - sector_median) × provision_acceleration`
- **Action**: Reduce exposure to banks with accelerating loan losses

**Signal 3: Retailer Fade** (Tactical short)
- **Type**: Short/underweight signal for vulnerable retailers
- **Entry**: `same_store_sales_growth < 0 AND consumer_stress_index > 3.0`
- **Target**: Retailers with high exposure to low-income consumers
- **Exit**: Sales growth turns positive or stress index < 2.5

**Signal 4: Consumer Recovery Play** (Contrarian long)
- **Type**: Long signal after stress peaks
- **Entry**: After `consumer_stress_index` declines 20% from peak AND savings rate rising
- **Action**: Overweight consumer discretionary stocks with strong balance sheets
- **Rationale**: Pent-up demand + credit healing = consumption rebound

### Implementation Plan
1. **Bronze Layer**: Ingest FRED consumer debt series (monthly/quarterly)
2. **Silver Layer**: Create `silver.fred_consumer_debt` table with all series
3. **Feature Pipeline**: Compute stress index, acceleration, growth differentials
4. **Sector Tagging**: Identify consumer discretionary stocks, subprime lenders in universe
5. **Signal Pipeline**: Implement screener + stock-level signals
6. **Monitoring**: Alert on stress index > 3.5 or delinquency acceleration > 0.5

---

## 4. Corporate Earnings Manipulation (Buyback-Driven EPS)

### What It Is
Share buybacks reduce the number of outstanding shares, mechanically increasing earnings per share (EPS) even if absolute net income is flat or declining. **Manipulation risk** arises when companies use buybacks to mask deteriorating fundamentals, often funded by debt in low-rate environments.

### Why It Matters
- **Unsustainable growth**: Buyback-driven EPS growth doesn't reflect organic business improvement
- **Debt-funded buybacks**: Many companies borrowed at low rates (2020-2022) to repurchase shares; now face higher refinancing costs
- **Earnings quality**: Deteriorating revenue growth + rising buybacks = potential value trap
- **Market risk**: When rates rise or credit tightens, buyback programs get cut, exposing weak earnings

### Data Sources & Datasets

#### FMP (Company fundamentals)
| Dataset | Endpoint | Description | Frequency |
|---------|----------|-------------|-----------|
| Income Statement | /v3/income-statement/{ticker} | Net income, EPS (diluted) | Quarterly |
| Cash Flow Statement | /v3/cash-flow-statement/{ticker} | Share repurchases, dividends | Quarterly |
| Balance Sheet | /v3/balance-sheet-statement/{ticker} | Total debt, cash | Quarterly |
| Key Metrics | /v3/key-metrics/{ticker} | Shares outstanding, P/E ratio | Quarterly |
| Enterprise Value | /v3/enterprise-values/{ticker} | Market cap, enterprise value | Quarterly |

#### FRED (Macro buyback data)
| Dataset | Series ID | Description | Frequency |
|---------|-----------|-------------|-----------|
| S&P 500 Buybacks | (via private sources) | Aggregate buyback $ by S&P 500 companies | Quarterly |
| Corporate Debt Issuance | (FRED various) | Total corporate bond issuance | Monthly |

### Features to Develop

**Level 1: Buyback Metrics** (FMP → Silver)
- `shares_repurchased_bn`: Dollar value of share buybacks (quarterly)
- `shares_outstanding_chg_pct`: % change in diluted shares outstanding (QoQ, YoY)
- `buyback_yield_pct`: Buybacks / market cap (annualized)
- `total_shareholder_return_pct`: (Buybacks + dividends) / market cap

**Level 2: Earnings Quality Indicators** (Silver computed)
- `eps_growth_pct`: YoY EPS growth rate
- `net_income_growth_pct`: YoY net income growth rate
- `buyback_contribution_to_eps`: Estimated EPS boost from share count reduction
  - Formula: `eps_growth - (net_income_growth / (1 + shares_chg))`
- `revenue_growth_pct`: YoY revenue growth
- `earnings_quality_score`: Composite score
  - Penalty if: `buyback_contribution_to_eps > 50% of total EPS growth`
  - Penalty if: `revenue_growth < eps_growth - 5%`
  - Penalty if: `debt_funded_buyback_flag = True`

**Level 3: Leverage & Sustainability** (Silver computed)
- `debt_funded_buyback_flag`: Boolean if `(buybacks > free_cash_flow) AND (debt increased)`
- `buyback_sustainability_ratio`: Free cash flow / (buybacks + dividends)
  - Healthy if > 1.2; stressed if < 0.8
- `net_debt_to_ebitda`: (Total debt - cash) / EBITDA
- `interest_coverage_ratio`: EBIT / interest expense

### Signals to Develop

**Signal 1: Earnings Quality Screener** (Defensive)
- **Type**: Binary filter to avoid low-quality earners
- **Logic**: Exclude stocks where:
  - `buyback_contribution_to_eps > 75%` (earnings growth is mostly financial engineering)
  - AND `revenue_growth < 2%` (organic growth is weak)
  - AND `debt_funded_buyback_flag = True`
- **Rationale**: Avoid companies masking deterioration with debt-funded buybacks

**Signal 2: Buyback Fade** (Tactical short/underweight)
- **Type**: Short/underweight signal for vulnerable buyback players
- **Entry**:
  - `buyback_yield > 5%` (aggressive buyback program)
  - AND `buyback_sustainability_ratio < 0.9` (unsustainable payout)
  - AND `net_debt_to_ebitda > 3.5` (high leverage)
- **Action**: Short or underweight; expect buyback cuts and EPS disappointment
- **Exit**: Buyback program is reduced or debt/EBITDA improves

**Signal 3: Quality Earnings Preference** (Long)
- **Type**: Long signal for high-quality growers
- **Logic**: Overweight stocks where:
  - `earnings_quality_score > 75th percentile`
  - `revenue_growth > eps_growth` (organic growth exceeds financial engineering)
  - `buyback_sustainability_ratio > 1.5` (disciplined capital allocation)
- **Rationale**: Reward companies growing earnings via business performance, not share count tricks

**Signal 4: Buyback Capitulation Indicator** (Market timing)
- **Type**: Aggregate market signal
- **Logic**: When S&P 500 aggregate buybacks decline >30% YoY, market stress is likely
- **Action**: Reduce overall equity exposure, increase cash
- **Historical precedent**: Buyback cuts preceded market bottoms in 2009, 2020

### Implementation Plan
1. **Bronze Layer**: Ingest FMP income statements, cash flow statements, balance sheets quarterly
2. **Silver Layer**: Create `silver.fmp_buyback_metrics` with shares outstanding, buybacks, debt
3. **Feature Pipeline**: Compute buyback contribution to EPS, quality scores, sustainability ratios
4. **Universe Filtering**: Apply quality screener to exclude low-quality earnings
5. **Signal Pipeline**: Implement buyback fade short signal + quality preference long signal
6. **Monitoring**: Track aggregate S&P 500 buyback trends, alert on >20% YoY declines

---

## 5. Banking Sector Stress

### What It Is
Banking sector stress occurs when banks face margin compression, credit losses, liquidity shortages, or capital erosion—often driven by interest rate risk, loan defaults, or deposit flight. Stress can cascade via interbank lending freezes and loss of confidence.

### Why It Matters
- **Systemic risk**: Banks are the circulatory system of the economy; stress disrupts lending and payment systems
- **2023 precedent**: Silicon Valley Bank, Signature Bank, First Republic failures driven by interest rate risk + deposit flight
- **Interest rate risk**: Banks holding long-duration bonds at low yields face mark-to-market losses when rates rise
- **CRE exposure**: Regional banks heavily exposed to commercial real estate (see Signal 2)
- **Interbank contagion**: Loss of confidence in one bank can trigger deposit runs and interbank lending freezes

### Data Sources & Datasets

#### FRED (Macro banking stress)
| Dataset | Series ID | Description | Frequency |
|---------|-----------|-------------|-----------|
| Bank Credit Spreads | BAMLH0A0HYM2 | High-yield corporate bond spreads (stress indicator) | Daily |
| SOFR-OIS Spread | SOFR - EFFR | Interbank lending stress (wider = more stress) | Daily |
| Bank Reserve Balances | TOTRESNS | Reserves held at Fed (liquidity indicator) | Weekly |
| Discount Window Borrowing | DISCBORR | Emergency Fed borrowing (crisis indicator) | Weekly |
| Deposits at All Banks | DPSACBW027SBOG | Total deposits (outflows signal stress) | Weekly |
| Bank Failures | BFTT | Number of FDIC-insured bank failures | Quarterly |

#### FMP (Bank fundamentals)
| Dataset | Endpoint | Description | Frequency |
|---------|----------|-------------|-----------|
| Bank Income Statements | /v3/income-statement/{ticker} | Net interest income, loan loss provisions | Quarterly |
| Bank Balance Sheets | /v3/balance-sheet-statement/{ticker} | Securities portfolio, loan book, deposits | Quarterly |
| Key Metrics | /v3/key-metrics/{ticker} | Net interest margin, efficiency ratio | Quarterly |
| Stock Prices | /v3/historical-price-full/{ticker} | Bank stock volatility (stress signal) | Daily |

#### Bank Regulatory Filings (future integration)
- **Call Reports (FFIEC 031/041)**: Detailed loan breakdowns, unrealized securities losses, capital ratios
- **FDIC BankFind**: Bank ratings, capital ratios, problem bank list
- **Fed Stress Test Results**: Capital adequacy under adverse scenarios

### Features to Develop

**Level 1: Macro Banking Stress** (FRED → Silver)
- `credit_spread_bps`: High-yield bond spread (wider = more stress)
- `sofr_ois_spread_bps`: Interbank lending stress indicator
- `discount_window_borrowing_bn`: Emergency Fed borrowing (spikes in crises)
- `deposit_outflows_pct`: % change in total deposits (YoY, QoQ)
- `bank_failures_count`: Number of FDIC-insured bank failures (trailing 12 months)

**Level 2: Bank-Level Health Metrics** (FMP → Silver)
- `net_interest_margin_pct`: (Interest income - interest expense) / earning assets
- `loan_loss_provision_pct`: Provision for credit losses / total loans
- `tangible_common_equity_ratio`: Tangible equity / tangible assets (capital strength)
- `deposits_to_assets_pct`: Deposits / total assets (funding stability)
- `unrealized_securities_losses_pct`: Unrealized losses on securities / equity (from HTM/AFS)
  - **Note**: Requires Call Report data; proxy with duration gap analysis

**Level 3: Composite Stress Scores** (Silver computed)
- `banking_stress_index`: Composite of macro indicators
  - Formula: `(credit_spread / 100) + (sofr_ois_spread / 10) + (discount_window / 50) + (deposit_outflows × 2)`
- `bank_fragility_score`: Company-level stress score
  - Inputs: NIM decline, high loan loss provisions, deposit outflows, securities losses, CRE exposure
  - Range: 0-100 (higher = more fragile)
- `systemic_risk_flag`: Boolean if `banking_stress_index > 5.0` AND `bank_failures_count > 3`

**Level 4: Interest Rate Sensitivity** (Silver computed)
- `duration_gap`: Difference between asset duration and liability duration (proxy)
- `rate_shock_equity_impact_pct`: Estimated equity loss from +200 bps rate shock
  - Formula: `-1 × duration_gap × 2.0%`

### Signals to Develop

**Signal 1: Banking Stress Screener** (Defensive)
- **Type**: Binary sector filter
- **Logic**: Exclude all banks when `systemic_risk_flag = True` OR `banking_stress_index > 4.0`
- **Action**: Exit all bank positions; avoid financials sector
- **Exit**: Stress index < 2.5 for 4 consecutive weeks

**Signal 2: Fragile Bank Avoidance** (Stock-level)
- **Type**: Continuous underweight for fragile banks
- **Logic**: Underweight/exclude banks where `bank_fragility_score > 70th percentile`
- **Red flags**:
  - NIM declining >50 bps YoY
  - Loan loss provisions >2% of loans
  - Deposit outflows >10% YoY
  - Unrealized securities losses >50% of equity
- **Action**: Reduce exposure; monitor for short opportunities

**Signal 3: Regional Bank Fade** (Tactical short)
- **Type**: Short signal for vulnerable regional banks
- **Entry**: `systemic_risk_flag = True` AND bank has:
  - CRE exposure >30% of loan book
  - Deposit outflows >5% QoQ
  - Stock price volatility (60d) in top decile
- **Action**: Short or buy put options
- **Exit**: Stress index declines or bank is acquired/bailed out

**Signal 4: Banking Recovery Play** (Contrarian long)
- **Type**: Long signal after stress peaks
- **Entry**: After `banking_stress_index` declines 40% from peak AND `bank_failures_count` stops increasing
- **Action**: Overweight large-cap banks with:
  - Tangible common equity >8%
  - Low CRE exposure (<15%)
  - Diversified deposit base
- **Rationale**: Post-crisis, survivors with strong capital benefit from competitor exits

### Implementation Plan
1. **Bronze Layer**: Ingest FRED banking stress series (daily/weekly) + FMP bank financials (quarterly)
2. **Silver Layer**: Create `silver.fred_banking_stress` (macro) and `silver.fmp_bank_health` (micro)
3. **Feature Pipeline**: Compute stress index, fragility scores, NIM trends
4. **Universe Tagging**: Flag banks by size (large-cap, regional) and CRE exposure
5. **Signal Pipeline**: Implement stress screener + fragile bank avoidance + tactical short
6. **Monitoring**: Alert on `banking_stress_index > 4.0` or `discount_window_borrowing > $50B`
7. **Future Enhancement**: Integrate Call Report data for unrealized securities losses and granular CRE exposure

---

## 6. Geopolitical Risk (Supply Chain & Shipping Stress)

### What It Is
Geopolitical risk encompasses military conflicts, trade disputes, sanctions, and political instability that disrupt global supply chains and increase input costs. Recent examples: Russia-Ukraine war, Red Sea shipping attacks, U.S.-China trade tensions, Taiwan Strait risk.

### Why It Matters
- **Supply chain fragility**: Just-in-time inventory systems are vulnerable to chokepoint disruptions (Suez Canal, Taiwan Strait, Strait of Hormuz)
- **Shipping cost shocks**: Freight rate spikes increase COGS and compress margins for importers
- **Commodity price volatility**: Energy, food, industrial metals spike during geopolitical crises
- **Sector rotation**: Defense, energy, domestic manufacturers benefit; global logistics, multinational retailers suffer
- **Macro shock risk**: Severe disruptions (e.g., Taiwan conflict) could trigger recession

### Data Sources & Datasets

#### FRED (Macro indicators)
| Dataset | Series ID | Description | Frequency |
|---------|-----------|-------------|-----------|
| VIX (Volatility Index) | VIXCLS | Market fear gauge (spikes during crises) | Daily |
| Oil Prices (WTI) | DCOILWTICO | West Texas Intermediate crude ($/barrel) | Daily |
| Natural Gas Prices | DHHNGSP | Henry Hub natural gas ($/MMBtu) | Daily |
| Baltic Dry Index | (external) | Dry bulk shipping costs (supply chain stress) | Daily |
| Producer Price Index | PPIACO | Input cost inflation | Monthly |

#### External APIs (future integration)
| Source | Dataset | Description | Frequency |
|--------|---------|-------------|-----------|
| Freightos | Container Rates | Global container shipping rates (FBX index) | Weekly |
| MarineTraffic | Port Congestion | Number of ships waiting at anchor (supply chain stress) | Real-time |
| ACLED | Conflict Events | Armed conflict location and event data | Daily |
| GDELT | News Sentiment | Geopolitical tension from news analysis | Real-time |

#### FMP (Company exposure)
| Dataset | Endpoint | Description | Frequency |
|---------|----------|-------------|-----------|
| Income Statements | /v3/income-statement/{ticker} | COGS, gross margin trends | Quarterly |
| Geographic Revenue | /v3/revenue-geographic-segmentation/{ticker} | Revenue by region (China exposure, Europe, etc.) | Annual |
| Key Metrics | /v3/key-metrics/{ticker} | Inventory turnover, margin trends | Quarterly |
| Commodity Prices | /v3/historical-price-full/{commodity} | Gold, silver, crude oil | Daily |

### Features to Develop

**Level 1: Macro Risk Indicators** (FRED + External → Silver)
- `vix_level`: VIX index level (>20 = elevated fear; >30 = crisis)
- `vix_spike_flag`: Boolean if VIX >25 and +5 points in 5 days
- `oil_price_usd`: WTI crude oil price ($/barrel)
- `oil_price_yoy_chg_pct`: Year-over-year change in oil price
- `natural_gas_price_usd`: Henry Hub natural gas ($/MMBtu)
- `baltic_dry_index`: Shipping cost index for dry bulk commodities
- `container_shipping_rate_usd`: 40-foot container rate (Asia-US route)
- `ppi_yoy_chg_pct`: Producer price inflation (input cost pressure)

**Level 2: Supply Chain Stress Metrics** (Silver computed)
- `shipping_cost_spike_flag`: Boolean if container rates >2× historical median
- `energy_shock_flag`: Boolean if oil >$100/barrel or gas >$6/MMBtu
- `supply_chain_stress_index`: Composite score
  - Formula: `(container_rate_zscore + baltic_dry_zscore + vix / 10 + ppi_chg × 5)`
  - Z-scores normalize to historical distributions
- `geopolitical_event_severity`: (Future) Text analysis of news for war, sanctions, blockade keywords

**Level 3: Company Exposure Metrics** (FMP → Silver)
- `china_revenue_exposure_pct`: % of revenue from China (geographic segmentation)
- `international_revenue_pct`: % of revenue from outside home country
- `gross_margin_pct`: Gross profit / revenue (declining margins signal cost pressure)
- `gross_margin_qoq_chg`: Quarter-over-quarter margin change (early warning)
- `inventory_turnover_ratio`: COGS / average inventory (rising inventory = supply glut or demand weakness)
- `energy_cost_exposure_pct`: Energy costs / total COGS (for manufacturers, airlines)

### Signals to Develop

**Signal 1: Supply Chain Shock Screener** (Defensive)
- **Type**: Binary sector filter
- **Logic**: Underweight/exclude sectors when:
  - `supply_chain_stress_index > 4.0` (composite stress is elevated)
  - OR `shipping_cost_spike_flag = True` AND `energy_shock_flag = True`
- **Affected sectors**: Industrials, consumer discretionary (importers), airlines
- **Action**: Rotate to domestic-focused, low-logistics companies
- **Exit**: Stress index < 2.5 for 8 consecutive weeks

**Signal 2: Margin Compression Alert** (Stock-level defensive)
- **Type**: Underweight companies with deteriorating margins due to input cost shocks
- **Logic**: Underweight stocks where:
  - `gross_margin_qoq_chg < -1.5%` (margin compression)
  - AND `ppi_yoy_chg > 3%` (high input cost inflation)
  - AND `pricing_power_flag = False` (unable to pass costs to customers)
- **Action**: Reduce exposure to low-margin importers

**Signal 3: China Exposure Fade** (Tactical underweight)
- **Type**: Underweight stocks with high China exposure during heightened Taiwan/trade tensions
- **Entry**: When `geopolitical_event_severity` flags China-related risk events
- **Logic**: Underweight stocks where `china_revenue_exposure > 25%`
- **Target**: Tech hardware, luxury goods, industrial companies with Chinese supply chains
- **Exit**: Event resolution or 180-day max hold

**Signal 4: Geopolitical Beneficiaries** (Tactical long)
- **Type**: Overweight sectors/stocks that benefit from geopolitical shocks
- **Entry**: When `supply_chain_stress_index > 3.5` OR `oil_price > $90`
- **Beneficiaries**:
  - Defense contractors (Lockheed Martin, Northrop Grumman)
  - Domestic energy producers (oil, natural gas)
  - Reshoring/nearshoring plays (North American manufacturers)
  - Commodity producers (gold, industrial metals during uncertainty)
- **Exit**: Stress index < 2.5 or event de-escalation

**Signal 5: Shipping Cost Mean Reversion** (Tactical)
- **Type**: Fade extreme shipping cost spikes
- **Entry**: When `container_shipping_rate > 95th percentile` of 5-year distribution
- **Action**: Short ocean freight companies or container shipping ETFs
- **Rationale**: Shipping rate spikes (2021-2022, Red Sea 2024) tend to normalize within 6-12 months
- **Exit**: Rates decline to median or 12-month hold limit

### Implementation Plan
1. **Bronze Layer**: Ingest FRED VIX, oil, gas, PPI daily/monthly; integrate external shipping APIs (Freightos FBX)
2. **Silver Layer**: Create `silver.fred_geopolitical_macro` + `silver.external_shipping_rates`
3. **Feature Pipeline**: Compute stress index, z-scores, spike flags
4. **Company Data**: Ingest FMP geographic revenue segmentation (annual) + quarterly margin trends
5. **Signal Pipeline**: Implement shock screener + margin compression alert + China fade + beneficiary rotation
6. **Monitoring**: Alert on `supply_chain_stress_index > 4.0` or `vix_spike_flag = True`
7. **Future Enhancement**: Integrate GDELT news sentiment analysis for real-time geopolitical event severity scoring

---

## Summary: Implementation Roadmap

### Phase 1: Macro Data Foundation (4-6 weeks)
**Objective**: Establish Bronze + Silver pipelines for all six macro signals

1. **FRED Integration** (Priority 1)
   - Add FRED datasets to `config/dataset_keymap.yaml` (treasury yields, CRE delinquencies, consumer debt, banking stress, commodities)
   - Create DTOs for each FRED series
   - Implement daily/weekly/monthly ingestion cadences
   - Build `silver.fred_*` tables for each signal domain

2. **FMP Fundamentals** (Priority 2)
   - Ensure complete coverage of balance sheets, income statements, cash flows for all universe stocks
   - Add geographic revenue segmentation endpoint
   - Validate CRE loan exposure data for banks
   - Implement quarterly ingestion for fundamentals

3. **External Data Sources** (Priority 3)
   - Integrate Freightos FBX API for container shipping rates
   - Add Baltic Dry Index (via external provider or web scraping)
   - (Future) Integrate GDELT for geopolitical news sentiment

### Phase 2: Feature Engineering (3-4 weeks)
**Objective**: Compute derived features and composite stress indices in Silver layer

1. **Signal-Specific Features**
   - Yield curve: spreads, inversion flags, duration metrics
   - CRE: delinquency rates, exposure ratios, refinancing risk scores
   - Consumer debt: stress index, acceleration, sustainability ratios
   - Earnings quality: buyback contribution to EPS, quality scores
   - Banking: stress index, fragility scores, NIM trends
   - Geopolitical: shipping cost z-scores, supply chain stress index

2. **Company-Level Exposure Metrics**
   - Bank CRE exposure percentiles
   - REIT refinancing risk scores
   - Consumer lender credit quality trends
   - Geographic revenue exposure (China, international)
   - Margin compression indicators

3. **Normalization & Percentiles**
   - Compute historical percentiles for all macro indicators (1Y, 3Y lookbacks)
   - Z-score normalization for composite indices
   - Validate data quality and handle missing values

### Phase 3: Signal Development (Gold Layer - Separate Project)
**Objective**: Implement 15+ signals across six economic domains

**Note**: This phase occurs in the **downstream Gold project**, not in SBFoundation. Gold project will:
1. Import SBFoundation Silver tables as read-only inputs
2. Build dimension tables (instruments, companies, sectors)
3. Implement signal logic using Silver features
4. Generate portfolio weights and trade recommendations

**Signals to Implement** (Gold layer):
- **Defensive screeners** (5): Yield curve inversion, CRE stress, consumer stress, banking stress, supply chain shock
- **Stock-level defensive** (4): Bank CRE exposure, REIT distress fade, margin compression, fragile bank avoidance
- **Tactical shorts** (3): Buyback fade, regional bank fade, China exposure fade
- **Contrarian longs** (3): CRE recovery, consumer recovery, banking recovery
- **Beneficiary rotations** (2): Geopolitical beneficiaries, shipping cost fade

### Phase 4: Monitoring & Alerting (2-3 weeks)
**Objective**: Build operational dashboards and alert systems

1. **Real-Time Alerts**
   - Yield curve inversion (10Y-2Y < 0 for 5+ days)
   - Banking stress index > 4.0
   - Supply chain stress index > 4.0
   - VIX spike >25
   - Discount window borrowing >$50B

2. **Weekly Reports**
   - Composite stress indices across all six signals
   - Top 10 most exposed stocks (by signal)
   - Sector rotation recommendations

3. **Backtesting Framework**
   - Validate signal performance on historical data (2000-present)
   - Measure alpha, Sharpe ratio, max drawdown
   - Identify false positives and refine thresholds

### Phase 5: Continuous Improvement (Ongoing)
1. **Data Expansion**
   - Add private data sources (CoStar for CRE, credit bureau data, ACLED conflict data)
   - Integrate alternative data (satellite imagery for port congestion, web traffic for consumer demand)

2. **Model Refinement**
   - Machine learning models for distress prediction (REIT default probability, bank fragility)
   - NLP sentiment analysis for earnings calls, geopolitical news

3. **Signal Calibration**
   - Quarterly review of signal thresholds based on performance
   - Adjust weights in composite indices
   - Add new signals based on market regime changes

---

## Expected Outcomes

**Data Coverage**:
- 30+ FRED economic series (daily/weekly/monthly)
- 15+ FMP fundamental datasets (quarterly)
- 3+ external data sources (shipping, commodities, volatility)

**Feature Count**:
- 50+ macro features (spreads, indices, growth rates)
- 75+ company-level features (exposure metrics, quality scores)
- 6 composite stress indices

**Signals**:
- 15+ actionable signals across six domains
- 3 defensive sector screeners
- 8 stock-level tactical signals
- 4 contrarian/recovery signals

**Operational Benefits**:
- Early warning system for systemic economic stress
- Quantitative framework for risk-off positioning
- Tactical alpha from shorting distressed sectors/stocks
- Contrarian entry points for post-crisis recoveries

---

**Next Steps**:
1. Review this plan with stakeholders
2. Prioritize signals (suggest: yield curve + banking stress first)
3. Begin Phase 1 FRED integration in `config/dataset_keymap.yaml`
4. Set up weekly progress reviews
