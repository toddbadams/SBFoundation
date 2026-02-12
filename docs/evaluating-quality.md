# Evaluating Quality

## Moat Stability & Moat Trajectory
Evaluate how durable and defensible the company’s moat is. For each use quantitative evidence where possible to assign a rating:
1 = Eroding | 2 = Stable | 3 = Strengthening
Additionally provide a concise explaination.

### 1. Capital Allocation Discipline
Trends in R&D intensity (% of revenue, 5-yr trend)
Trends in sales & marketing (% of revenue)
Trends in capex (% of revenue)
Free-cash-flow reinvestment ratio (FCF reinvested ÷ FCF generated)
Evidence of underinvestment or overinvestment

```
{
  "rd_intensity": {
    "fields": ["researchAndDevelopment", "totalRevenue"],
    "supported": true
  },
  "sm_intensity": {
    "fields": ["sellingGeneralAndAdministrative", "totalRevenue"],
    "supported": "proxy"
  },
  "capex_intensity": {
    "fields": ["capitalExpenditures", "totalRevenue"],
    "supported": true
  },
  "fcf_reinvestment_ratio": {
    "fields": ["capitalExpenditures", "freeCashFlow"],
    "supported": "proxy"
  },
  "underinvestment_overinvestment_signal": {
    "fields": ["researchAndDevelopment", "capitalExpenditures", "totalRevenue", "operatingMargins"],
    "supported": "inferred_only"
  }
}
```

Missing gaps. https://site.financialmodelingprep.com/developer/docs/pricing

The best stack is:
1. Alpha Vantage (free/cheap + what you already use)

→ Basic revenue, R&D, capex, FCF
2. Financial Modeling Prep (FMP) as upgrade

→ You get S&M (sometimes), employees, segment revenue
→ Very cheap compared to Polygon / Tikr
3. SEC API for anything missing

→ Guarantees completeness
→ You can parse XBRL tags for line items that no paid API exposes perfectly anyway

### 2. Innovation Velocity
Revenue from new products (% where available)
Product launch cadence
AI adoption, cloud modernization, platform shifts
Rate of customer experience improvements 

### 3. Cultural Health
Headcount growth vs. revenue growth
Glassdoor CEO approval / culture scores (if discussing qualitatively only)
Signs of bureaucracy, dilution of ownership mentality
Speed of decision making (qualitative)

### 4. Technology & Platform Adaptability
Migration to cloud / automation / AI
Ability to defend against platform risk (Apple/Google/AWS/etc.)
Evidence of technical debt reduction

## Founder-Quality & Leadership Effectiveness
Score how aligned management is with long-term value creation.

### 1. Ownership Mentality
Insider ownership (%)
CEO tenure & track record
Long-term incentive plan structure
Buyback effectiveness (shares outstanding trend)

### 2. Management Alpha
Capital allocation history
Pricing power decisions
Cost discipline
Strategic clarity & consistency

## Earnings Quality & Recurrence
Quantify the predictability and durability of earnings.

### 1. Revenue Recurrence
% Recurring revenue
Contract length / retention metrics
Customer concentration (top 10 customers % revenue)

### 2. Margin Quality
Gross margin trend (5 yrs)
Operating margin trend (5 yrs)
Free cash flow margin trend
Stability (standard deviation of margins)

### 3. Cash Conversion
FCF / Net Income
Working capital efficiency (DSO, DIO, DPO trends)
Capex stability

## Balance Sheet Strength
Quantify financial resilience.

### 1. Leverage
Net debt / EBITDA
Interest coverage
% fixed vs variable debt

### 2. Liquidity
Cash vs. short-term obligations
Current ratio trend

## Pricing Power & Competitive Positioning
Measure the durability of pricing power.

### 1. Pricing Power
Price increases taken (last 3–5 yrs)
Ability to pass through inflation
Evidence of customer pushback

### 2. Competitive Fragility
Market share trend
Switching costs
Network effects
Regulatory threats
Platform dependence risk

## Scorecard Summary (Quantitative)
Compute:
Moat Strength Score: average / 3
Leadership Quality Score: average / 3
Earnings Quality Score: average / 3
Balance Sheet Strength Score: average / 3
Pricing Power Score: average / 3

Total Quality Score (weighted):
Moat: 30%
Leadership: 20%
Earnings Quality: 30%
Balance Sheet: 10%
Pricing Power: 10%
