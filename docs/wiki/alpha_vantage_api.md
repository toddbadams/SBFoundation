# Alpha Vantage API 
Alpha Vantage provides realtime and historical financial market data through a set of powerful and developer-friendly data APIs and spreadsheets. From traditional asset classes (e.g., stocks, ETFs, mutual funds) to economic indicators, from foreign exchange rates to commodities, from fundamental data to technical indicators, Alpha Vantage is your one-stop-shop for enterprise-grade global market data delivered through cloud-based APIs, Excel, and Google Sheets.

## Time Series Stock Data APIs
This suite of APIs provide global equity data in 4 different temporal resolutions: (1) daily, (2) weekly, (3) monthly, and (4) intraday, with 20+ years of historical depth. A lightweight ticker quote endpoint and several utility functions such as ticker search and market open/closure status are also included for your convenience.

### TIME_SERIES_MONTHLY_ADJUSTED

This API returns monthly adjusted time series (last trading day of each month, monthly open, monthly high, monthly low, monthly close, monthly adjusted close, monthly volume, monthly dividend) of the equity specified, covering 20+ years of historical data.


| Alpha Vantage Parameter | Acquisition Parameter |
| ----------------------- | --------------------- |
| date                    | qtr_end_date          |
| 1. open                 |                       |
| 2. high                 |                       |
| 3. low                  |                       |
| 4. close                |                       |
| 5. adjusted close       | share_price           |
| 6. volume               |                       |
| 7. dividend amount      |                       |


## Alpha Intelligence
The APIs in this section contain advanced market intelligence built with our decades of expertise in AI, machine learning, and quantitative finance. We hope these highly differentiated alternative datasets can help turbocharge your trading strategy, market research, and financial software application to the next level.

### INSIDER_TRANSACTIONS
This API returns the latest and historical insider transactions made by key stakeholders (e.g., founders, executives, board members, etc.) of a specific company.

| Alpha Vantage Parameter   | Acquisition Parameter     |
| ------------------------- | ------------------------- |
| transaction\_date         | qtr\_end\_date            |
| ticker                    |                           |
| executive                 |                           |
| executive\_title          |                           |
| security\_type            |                           |
| acquisition\_or\_disposal | acquisition\_or\_disposal |
| shares                    | insider\_shares           |
| share\_price              |                           |


## Fundamental Data
We offer the following set of fundamental data APIs in various temporal dimensions covering key financial metrics, income statements, balance sheets, cash flow, and other fundamental data points.

### INCOME_STATEMENT
This API returns the annual and quarterly income statements for the company of interest, with normalized fields mapped to GAAP and IFRS taxonomies of the SEC. Data is generally refreshed on the same day a company reports its latest earnings and financials.

| Alpha Vantage Parameter           | Acquisition Parameter |
| --------------------------------- | --------------------- |
| fiscalDateEnding                  | qtr_end_date          |
| reportedCurrency                  |                       |
| grossProfit                       |                       |
| totalRevenue                      | revenue               |
| costOfRevenue                     |                       |
| costofGoodsAndServicesSold        |                       |
| operatingIncome                   |                       |
| sellingGeneralAndAdministrative   |                       |
| researchAndDevelopment            |                       |
| operatingExpenses                 |                       |
| investmentIncomeNet               |                       |
| netInterestIncome                 |                       |
| interestIncome                    |                       |
| interestExpense                   | interest_expense      |
| nonInterestIncome                 |                       |
| otherNonOperatingIncome           |                       |
| depreciation                      |                       |
| depreciationAndAmortization       |                       |
| incomeBeforeTax                   | income_before_tax     |
| incomeTaxExpense                  | income_tax_expense    |
| interestAndDebtExpense            |                       |
| netIncomeFromContinuingOperations |                       |
| comprehensiveIncomeNetOfTax       |                       |
| ebit                              | ebit                  |
| ebitda                            | ebitda                |
| netIncome                         | net_income            |


### BALANCE_SHEET
This API returns the annual and quarterly balance sheets for the company of interest, with normalized fields mapped to GAAP and IFRS taxonomies of the SEC. Data is generally refreshed on the same day a company reports its latest earnings and financials.

| Alpha Vantage Parameter                | Acquisition Parameter        |
| -------------------------------------- | ---------------------------- |
| fiscalDateEnding                       | qtr_end_date                 |
| reportedCurrency                       |                              |
| totalAssets                            | total_assets                 |
| totalCurrentAssets                     |                              |
| cashAndCashEquivalentsAtCarryingValue  | cash_and_cash_equivalents    |
| cashAndShortTermInvestments            |                              |
| inventory                              |                              |
| currentNetReceivables                  | current_net_receivables      |
| totalNonCurrentAssets                  |                              |
| propertyPlantEquipment                 |                              |
| accumulatedDepreciationAmortizationPPE |                              |
| intangibleAssets                       |                              |
| intangibleAssetsExcludingGoodwill      |                              |
| goodwill                               |                              |
| investments                            |                              |
| longTermInvestments                    |                              |
| shortTermInvestments                   |                              |
| otherCurrentAssets                     |                              |
| otherNonCurrentAssets                  |                              |
| totalLiabilities                       |                              |
| totalCurrentLiabilities                | current_liabilities          |
| currentAccountsPayable                 |                              |
| deferredRevenue                        |                              |
| currentDebt                            |                              |
| shortTermDebt                          | short_term_debt              |
| totalNonCurrentLiabilities             |                              |
| capitalLeaseObligations                |                              |
| longTermDebt                           | long_term_debt               |
| currentLongTermDebt                    |                              |
| longTermDebtNoncurrent                 |                              |
| shortLongTermDebtTotal                 |                              |
| otherCurrentLiabilities                |                              |
| otherNonCurrentLiabilities             |                              |
| totalShareholderEquity                 | total_shareholder_equity     |
| treasuryStock                          |                              |
| retainedEarnings                       |                              |
| commonStock                            |                              |
| commonStockSharesOutstanding           | shares_outstanding           |

### CASH_FLOW
This API returns the annual and quarterly cash flow for the company of interest, with normalized fields mapped to GAAP and IFRS taxonomies of the SEC. Data is generally refreshed on the same day a company reports its latest earnings and financials.

Here’s the complete mapping table, showing every Alpha Vantage parameter with only the matching Acquisition parameters filled in:

| Alpha Vantage Parameter                                   | Acquisition Parameter |
| --------------------------------------------------------- | --------------------- |
| fiscalDateEnding                                          | qtr_end_date          |
| reportedCurrency                                          |                       |
| operatingCashflow                                         | operating_cashflow    |
| paymentsForOperatingActivities                            |                       |
| proceedsFromOperatingActivities                           |                       |
| changeInOperatingLiabilities                              |                       |
| changeInOperatingAssets                                   |                       |
| depreciationDepletionAndAmortization                      |                       |
| capitalExpenditures                                       | capital_expenditures  |
| changeInReceivables                                       |                       |
| changeInInventory                                         |                       |
| profitLoss                                                |                       |
| cashflowFromInvestment                                    |                       |
| cashflowFromFinancing                                     |                       |
| proceedsFromRepaymentsOfShortTermDebt                     |                       |
| paymentsForRepurchaseOfCommonStock                        |                       |
| paymentsForRepurchaseOfEquity                             |                       |
| paymentsForRepurchaseOfPreferredStock                     |                       |
| dividendPayout                                            |                       |
| dividendPayoutCommonStock                                 |                       |
| dividendPayoutPreferredStock                              |                       |
| proceedsFromIssuanceOfCommonStock                         |                       |
| proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet |                       |
| proceedsFromIssuanceOfPreferredStock                      |                       |
| proceedsFromRepurchaseOfEquity                            |                       |
| proceedsFromSaleOfTreasuryStock                           |                       |
| changeInCashAndCashEquivalents                            |                       |
| changeInExchangeRate                                      |                       |
| netIncome                                                 |                       |

## Earnings
This API returns the annual and quarterly earnings (EPS) for the company of interest. Quarterly data also includes analyst estimates and surprise metrics.

Here’s the full mapping for your latest Alpha Vantage fields, with only the matching Acquisition parameter filled in:

| Alpha Vantage Parameter | Acquisition Parameter |
| ----------------------- | --------------------- |
| fiscalDateEnding        | qtr_end_date          |
| reportedDate            |                       |
| reportedEPS             | eps                   |
| estimatedEPS            | estimated_eps         |
| surprise                |                       |
| surprisePercentage      | surprise_eps_pct      |
| reportTime              |                       |

