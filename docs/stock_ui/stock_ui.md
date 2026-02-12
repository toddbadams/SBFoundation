# Stock View Page

This document outlines the specification and development plan for creating a financial stock charting web application, using **Streamlit** for the frontend and **Python** for backend logic. Charts will be rendered using **Streamlit-ECharts**.

## Overview

The application will display financial charts and insights for selected stock tickers, including pricing trends, comparison benchmarks, and buy/sell signals. The layout, styling, and features are modeled after Fool IQ's charting view.

## App Structure
This page should be constructured as a python class and extend the existing streamlit application (see `app.py`). 
Add a page to the PAGES variable "Stock View". 

##  Data Repository 

**repository** (see `storage.py`)

```pyton
    self.dim_store = ParquetStorage(self.env.dim_stocks_folder)
```

### Data Table Mapping
The following are the data tables that feed the information required for the app.

| Data Category        | Table Name                   | Code Example                                       |
| -------------------- | ---------------------------- | -------------------------------------------------- |
| Stock                | DIM_STOCK                    | df = self.dim\_store.read\_df(table\_name, ticker) |
| Income Statement     | FACT\_QTR\_INCOME\_STATEMENT | df = self.dim\_store.read\_df(table\_name, ticker) |
| Balance Sheet        | FACT\_QTR\_BALANCE\_SHEET    | df = self.dim\_store.read\_df(table\_name, ticker) |
| Cash Flow            | FACT\_QTR\_CASH\_FLOW        | df = self.dim\_store.read\_df(table\_name, ticker) |
| Earnings             | FACT\_QTR\_EARNINGS          | df = self.dim\_store.read\_df(table\_name, ticker) |
| Dividends            | FACT\_QTR\_DIVIDENDS         | df = self.dim\_store.read\_df(table\_name, ticker) |
| Insider Transactions | FACT\_QTR\_INSIDERS          | df = self.dim\_store.read\_df(table\_name, ticker) |
| Pricing & Volume     | FACT\_D\_PRICING             | df = self.dim\_store.read\_df(table\_name, ticker) |


### Sidebar Area

Ticker Input is shown as a drop down from a predefined list. The following code is located in the __init__ method which is used to create the ticker list.

```pyton    
        self.dim_stock_srv = DimStocks() 
        self.tickers = sorted(self.dim_stock_srv.tickers_dimensioned()) 
```


### Main Content Area

**Stock Info Header:**

  * Stock name (e.g., IBM), exchange, ticker and currency shown as (NYSE: IBM  USD)

The following shows the data source for the header components
| Data Category | Table Name | Column   |
| ------------- | ---------- | -------- |
| Stock Name    | DIM_STOCK  | name     |
| Ticker        | DIM_STOCK  | symbol   |
| Exchange      | DIM_STOCK  | exchange |
| Currency      | DIM_STOCK  | currency |
  
**Navigation options:** (shown as tabs in the header of the page)

  * Summary
  * Income Statement (see `income_statement.md`)
  * Balance Sheet (display a place holder for now)
  * Cash Flow (display a place holder for now)
  * Earnings (display a place holder for now)
  * Dividends (display a place holder for now)
  * Insider Transactions (display a place holder for now)
  * Charting (display a place holder for now)

### Sub Page Area

Renders the selected subpage from the tabs navigation options.  
Each subpage should be it's own python class.
Start by buildingout the income statement subpage and we will add one page at a time.
Create class placeholders for the other subpages



