
# Chart View 

This document outlines the structure and functionality of the **Charting** subpage of the financial stock charting application.

## Header

This is the same header as in the **Stock View Page** (stock_ui.md)

## Chart Controls

**Metric Selectors:** 

  * Date range filters: `5W, 1M, 6M, YTD, 1Y, 3Y, 5Y, 10Y, MAX` rendered using streamlit  st.radio
  * Toggle switches: `Show Total Returns` rendered using streamlit  st.checkbox


## Chart Area

* Uses Streamlit-echarts 0.4.0 (https://pypi.org/project/streamlit-echarts/)
* Line chart with gradient/shaded area
* X-axis: time (date range based on selection)
* Y-axis: stock price
* Interactive features:
  * Zoom and pan
  * Tooltips on hover showing date, price, ticker


The Chart code should be extracted to a separate class maintaining separation of concerns between the StreamLit page and the ECharts code.

