# FMP API Load Strategy


the following are the data catagories (todo: explain how used)

``` python
class DataCategory(StrEnum):
    EQUITIES = "equities"
    ECONOMICS = "economics"
    MARKET = "market"
    COMMODITIES = "commodities"
    FX = "fx"
    CRYPTO = "crypto"
```

the following are the actions that can be applied to each data category.  (todo: explain how used)

``` python
class Action(StrEnum):
    LOAD_NEW = "load_new"
    REFRESH = "refresh"
```

(todo: explain Endoint, Documentation, Dataset as shown below)

## Load New Equities Data
(todo: define what are equities)

Domain: EQUITIES
Action: LOAD_NEW


1. Company Symbols List API
Easily retrieve a comprehensive list of financial symbols with the FMP Company Symbols List API. Access a broad range of stock symbols and other tradable financial instruments from various global exchanges, helping you explore the full range of available securities.

Endpoint: https://financialmodelingprep.com/stable/stock-list
Documentation: https://site.financialmodelingprep.com/developer/docs#stock-list
dataset: stock-list

2. Financial Statement Symbols List API
Access a comprehensive list of companies with available financial statements through the FMP Financial Statement Symbols List API. Find companies listed on major global exchanges and obtain up-to-date financial data including income statements, balance sheets, and cash flow statements, are provided.

Endpoint: https://financialmodelingprep.com/stable/financial-statement-symbol-list
Documentation: https://site.financialmodelingprep.com/developer/docs#financial-statement-symbol-list
dataset: financial-statement-symbol-list

3. ETF Symbol List API
Quickly find ticker symbols and company names for Exchange Traded Funds (ETFs) using the FMP ETF Symbol Search API. This tool simplifies identifying specific ETFs by their name or ticker.

Endpoint: https://financialmodelingprep.com/stable/etf-list
Documentation: https://site.financialmodelingprep.com/developer/docs#etf-list
dataset: etf-list

4. Company Profile Data API
Access detailed company profile data with the FMP Company Profile Data API. This API provides key financial and operational information for a specific stock symbol, including the company's market capitalization, stock price, industry, and much more.

Endpoint: https://financialmodelingprep.com/stable/profile?symbol=AAPL
Documentation: https://site.financialmodelingprep.com/developer/docs#profile
dataset: company-profile

5. Company Notes API
Retrieve detailed information about company-issued notes with the FMP Company Notes API. Access essential data such as CIK number, stock symbol, note title, and the exchange where the notes are listed. Symbols must have country=US. “Company notes” are debt securities issued by a company, similar to bonds but usually with shorter or medium maturities and more flexible structures. They represent money the company has borrowed from investors and must repay with interest.

Endpoint: https://financialmodelingprep.com/stable/company-notes?symbol=AAPL
Documentation: https://site.financialmodelingprep.com/developer/docs#company-notes
dataset: company-notes

6. Stock Peer Comparison APIGlobe Flag
Identify and compare companies within the same sector and market capitalization range using the FMP Stock Peer Comparison API. Gain insights into how a company stacks up against its peers on the same exchange.

Endpoint: https://financialmodelingprep.com/stable/stock-peers?symbol=AAPL
Documentation: https://site.financialmodelingprep.com/developer/docs#stock-peers
dataset: company-stock-peers

7.  Delisted Companies API
Stay informed with the FMP Delisted Companies API. Access a comprehensive list of companies that have been delisted from US exchanges to avoid trading in risky stocks and identify potential financial troubles. Symbols must have country=US.

Endpoint: https://financialmodelingprep.com/stable/delisted-companies?page=0&limit=100
Documentation: https://site.financialmodelingprep.com/developer/docs#delisted-companies
dataset: company-delisted-companies

8. Company Historical Employee Count API
Access historical employee count data for a company based on specific reporting periods. The FMP Company Historical Employee Count API provides insights into how a company’s workforce has evolved over time, allowing users to analyze growth trends and operational changes.  Symbols must have country=US.

Endpoint: https://financialmodelingprep.com/stable/historical-employee-count?symbol=AAPL
Documentation: https://site.financialmodelingprep.com/developer/docs#historical-employee-count
dataset: company-historical-employee-count