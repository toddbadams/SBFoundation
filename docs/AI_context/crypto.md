# Crypto Data
The Crypto Data is loaded after the market data. (todo: add description/intro of Crypto data)

All of the dataset are in the Crypto_DOMAIN, which is defined in src\sbfoundation\settings.py

For each of datasets below ensure a dataset is specified in config\dataset_keymap.yaml and ensure a DTO that manages the boundry from bronze to silver in src\sbfoundation\dtos

Update the README.md file to include a section on how the Crypto data is loaded and updated. This should include a concise description of each of the datasets.

Use src/sbfoundation/api.py as the entrypoint to load the Crypto datasets.

## Step 1. Baseline datasets
These datasets should be run first when not present in the silver layer.  

1. Cryptocurrency Currency Pairs API
Access a comprehensive list of all cryptocurrencies traded on exchanges worldwide with the FMP Cryptocurrencies Overview API. Get detailed information on each cryptocurrency to inform your investment strategies.

Endpoint: https://financialmodelingprep.com/stable/cryptocurrency-list
Documentation: https://site.financialmodelingprep.com/developer/docs#cryptocurrency-list
dataset: crypto-list
min_age_days=365 days
run_days=mon, tues, wed, thurs, fri, sat
plans: basic, starter, premium, ultimate


The following datasets can be run concurrently:

1. Historical Cryptocurrency Full Chart API
Access comprehensive end-of-day (EOD) price data for cryptocurrencies with the Full Historical Cryptocurrency Data API. Analyze long-term price trends, market movements, and trading volumes to inform strategic decisions.

This endpoint is a ticker based endpoint and should be run using ticker=(every symbol in crypto-list)

Endpoint: https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=BTCUSD
Documentation: https://site.financialmodelingprep.com/developer/docs#cryptocurrency-historical-price-eod-full
dataset: crypto-price-eod
min_age_days=1 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri
