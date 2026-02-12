# Income Statement View 

This document outlines the structure and functionality of the **Income Statement** subpage of the financial stock charting application.

## Page Overview

The Income Statement page presents quarterly financial performance for a selected stock, including revenue, expenses, margins, and net income. It includes both a line chart and a financial table.


## Header

This is the same header as in the **Stock View Page** (see `stock_ui.md`)

## Chart Controls

**Metric Selectors:** (shown as radio buttons)

  * Revenue, Gross Profit, Operating Income, Operating Margin, Net Income, Net Margin

Metric selection updates the chart and table areas.


## Chart Area 

* Rendered using `st_echarts`
* Shaded area line chart for selected metric over time
* X-axis: Time (Quarterly labels)
* Y-axis: Percentage or value, depending on metric

The Chart code should be extracted to a seperate class maintaining seperation of concernes between the StreamLit page and the ECharts code.

## Table Area

* Displayed in tabular format with:

  * **Rows:** Financial line items (Revenue, COGS, Gross Profit, SG\&A, R\&D, Operating Income, etc.)
  * **Columns:** Quarters from oldest to latest displayed Quarterly

This display is a transpose of the data source `FACT_QTR_INCOME_STATEMENT`

* Formatting:

  * Italic sublabels (e.g., *Gross Margin*)
  * Indented subcategories
  * Bolded totals
  * Values in millions 

**Note**:  the FactDisplayCol (see `FactTableConfig.py`) DTO class describes the columns in the data table, however are transposed in the screen view.


## Data Requirements

* Source: `FACT_QTR_INCOME_STATEMENT`
* Example loader:

```python
df = self.dim_store.read_df("FACT_QTR_INCOME_STATEMENT", ticker)
```

## Required Rows

The rows (stored as columns in the data table) are retreieved from a config file (see `config_loader.py`)

* configuration loader - config_loader.py
* DTO - FactTableConfig.py
* JSON = fact_qtr_balance_sheet.json
  
```python
        self.config = ConfigLoader()
        self.table_cfg = ConfigLoader().fact_qtr_income()
```

