# FX Data
The FX Data is loaded after the market data. (todo: add description/intro of FX data)

All of the dataset are in the FX_DOMAIN, which is defined in src\sbfoundation\settings.py

For each of datasets below ensure a dataset is specified in config\dataset_keymap.yaml and ensure a DTO that manages the boundry from bronze to silver in src\sbfoundation\dtos

Update the README.md file to include a section on how the FX data is loaded and updated. This should include a concise description of each of the datasets.

Use src/sbfoundation/api.py as the entrypoint to load the FX datasets.

## Step 1. Baseline datasets
These datasets should be run first when not present in the silver layer.  

1. Forex Currency Pairs API
Access a comprehensive list of all currency pairs traded on the forex market with the FMP Forex Currency Pairs API. Analyze and track the performance of currency pairs to make informed investment decisions.

Endpoint: https://financialmodelingprep.com/stable/forex-list
Documentation: https://site.financialmodelingprep.com/developer/docs#forex-list
dataset: fx-list
min_age_days=365 days
run_days=mon, tues, wed, thurs, fri, sat
plans: basic, starter, premium, ultimate


The following datasets can be run concurrently:

1. Historical Forex Full Chart API
Access comprehensive historical end-of-day forex price data with the Full Historical Forex Chart API. Gain detailed insights into currency pair movements, including open, high, low, close (OHLC) prices, volume, and percentage changes.


This endpoint is a ticker based endpoint and should be run using ticker=(every symbol in fx-list)

Endpoint: https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=EURUSD
Documentation: https://site.financialmodelingprep.com/developer/docs#forex-historical-price-eod-full
dataset: fx-price-eod
min_age_days=1 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri
