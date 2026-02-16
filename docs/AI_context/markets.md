# Market Data
The market data should be loaded first when starting with  empty data. All of this data are snapshots, and are considered dimensions in terms of a data warehouse. (todo: add meaning of dimension)

All of the dataset are in the MARKET_DOMAIN, which is defined in src\sbfoundation\settings.py

For each of datasets below ensure a dataset is specified in config\dataset_keymap.yaml and ensure a DTO that manages the boundry from bronze to silver in src\sbfoundation\dtos

Update the README.md file to include a section on how the market data is loaded and updated. This should include a concise description of each of the datasets.

Use src/sbfoundation/api.py as the entrypoint to load the market datasets.

## Step 1. Baseline datasets
These datasets should be run first when not present in the silver layer.  

1. Available Countries API
Access a comprehensive list of countries where stock symbols are available with the FMP Available Countries API. This API enables users to filter and analyze stock symbols based on the country of origin or the primary market where the securities are traded.

Endpoint: https://financialmodelingprep.com/stable/available-countries
Documentation: https://site.financialmodelingprep.com/developer/docs#available-countries
dataset: market-countries
min_age_days=365 days
run_days=mon, tues, wed, thurs, fri, sat
plans: basic, starter, premium, ultimate


The following datasets can be run concurrently:

1. Available Exchanges API 
Access a complete list of supported stock exchanges using the FMP Available Exchanges API. This API provides a comprehensive overview of global stock exchanges, allowing users to identify where securities are traded and filter data by specific exchanges for further analysis.

This dataset when in a silver table should map it's countryCode property to the table created in the silver table for dataset=available-countries

Endpoint: https://financialmodelingprep.com/stable/available-exchanges
Documentation: https://site.financialmodelingprep.com/developer/docs#available-exchanges
dataset: market-exchanges
min_age_days=365 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri, sat

2. Available Sectors API
Access a complete list of industry sectors using the FMP Available Sectors API. This API helps users categorize and filter companies based on their respective sectors, enabling deeper analysis and more focused queries across different industries.

Endpoint: https://financialmodelingprep.com/stable/available-sectors
Documentation: https://site.financialmodelingprep.com/developer/docs#available-sectors
dataset: market-sectors
min_age_days=365 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri, sat

3. Available Industries API
Access a comprehensive list of industries where stock symbols are available using the FMP Available Industries API. This API helps users filter and categorize companies based on their industry for more focused research and analysis.

Endpoint: https://financialmodelingprep.com/stable/available-industries
Documentation: https://site.financialmodelingprep.com/developer/docs#available-industries
dataset: market-industries
min_age_days=365 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri, sat


## Step 2. Detailed Market Data


These datasets have a min_age_days=365 days.

The following datasets should be run concurrently:


1. Market Sector Performance API
Get a snapshot of sector performance using the Market Sector Performance Snapshot API. Analyze how different industries are performing in the market based on average changes across sectors.

This dataset should be run without the query params exchange and sector, thus returning for all exchanges and sectors. exchange and sector should map back to the silver tables market-exchanges and market-sectors.

This dataset should be run for every market day from 2013-01-01

Endpoint: https://financialmodelingprep.com/stable/sector-performance-snapshot?date=2024-02-01
Documentation: https://site.financialmodelingprep.com/developer/docs#sector-performance-snapshot
dataset: market-sector-performance
min_age_days=1 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri


2. Industry Performance API
Access detailed performance data by industry using the Industry Performance API. Analyze trends, movements, and daily performance metrics for specific industries across various stock exchanges.

This dataset should be run without the query params exchange and sector, thus returning for all exchanges and sectors. exchange and sector should map back to the silver tables market-exchanges and market-sectors.

This dataset should be run for every market day from 2013-01-01

Endpoint: https://financialmodelingprep.com/stable/industry-performance-snapshot?date=2024-02-01
Documentation: https://site.financialmodelingprep.com/developer/docs#industry-performance-snapshot
dataset: market-industry-performance
min_age_days=1 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri

3. Sector PE API
Retrieve the price-to-earnings (P/E) ratios for various sectors using the Sector P/E API. Compare valuation levels across sectors to better understand market valuations.

This dataset should be run without the query params exchange and sector, thus returning for all exchanges and sectors. exchange and sector should map back to the silver tables market-exchanges and market-sectors.

This dataset should be run for every market day from 2013-01-01

Endpoint: https://financialmodelingprep.com/stable/sector-pe-snapshot?date=2024-02-01
Documentation: https://site.financialmodelingprep.com/developer/docs#industry-performance-snapshot
dataset: market-sector-pe
min_age_days=1 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri

4. Industry PE API
View price-to-earnings (P/E) ratios for different industries using the Industry P/E API. Analyze valuation levels across various industries to understand how each is priced relative to its earnings.

This dataset should be run without the query params exchange and industry, thus returning for all exchanges and industries. exchange and sector should map back to the silver tables market-exchanges and market-industries.

This dataset should be run for every market day from 2013-01-01

Endpoint: https://financialmodelingprep.com/stable/industry-pe-snapshot?date=2024-02-01
Documentation: https://site.financialmodelingprep.com/developer/docs#industry-pe-snapshot
dataset: market-industry-pe
min_age_days=1 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri

5. All Exchange Market Hours API
View the market hours for all exchanges. Check when different markets are active.

This dataset should add an `as-of-date` column to denote which date the data represents.

Endpoint: https://financialmodelingprep.com/stable/all-exchange-market-hours
Documentation: https://site.financialmodelingprep.com/developer/docs#all-exchange-market-hours
dataset: market-hours
min_age_days=1 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri

6. Holidays By Exchange API
Provides a list of market holidays for a given exchange.

This dataset should be run with the query params exchange where exchange maps back to the silver tables market-exchanges.

This dataset should be run for every market day from 1990-01-01

Endpoint: https://financialmodelingprep.com/stable/holidays-by-exchange?exchange=NASDAQ
Documentation: https://site.financialmodelingprep.com/developer/docs#holidays-by-exchange
dataset: market-holidays
min_age_days=365 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri, sat