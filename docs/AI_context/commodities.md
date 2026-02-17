# Commodities Data
The Commodities Data is loaded after the market data. (todo: add description/intro of Commodities data)

All of the dataset are in the COMMODITIES_DOMAIN, which is defined in src\sbfoundation\settings.py

For each of datasets below ensure a dataset is specified in config\dataset_keymap.yaml and ensure a DTO that manages the boundry from bronze to silver in src\sbfoundation\dtos

Update the README.md file to include a section on how the commodities data is loaded and updated. This should include a concise description of each of the datasets.

Use src/sbfoundation/api.py as the entrypoint to load the commodities datasets.

## Step 1. Baseline datasets
These datasets should be run first when not present in the silver layer.  

1. Commodities List API
Access an extensive list of tracked commodities across various sectors, including energy, metals, and agricultural products. The FMP Commodities List API provides essential data on tradable commodities, giving investors the ability to explore market options in real-time.

Endpoint: https://financialmodelingprep.com/stable/commodities-list
Documentation: https://site.financialmodelingprep.com/developer/docs#Commoditiescurrency-list
dataset: commodities-list
min_age_days=365 days
run_days=mon, tues, wed, thurs, fri, sat
plans: basic, starter, premium, ultimate


The following datasets can be run concurrently:

1. Historical Commoditiescurrency Full Chart API

Access full historical end-of-day price data for commodities with the FMP Comprehensive Commodities Price API. This API enables users to analyze long-term price trends, patterns, and market movements in great detail.

This endpoint is a ticker based endpoint and should be run using ticker=(every symbol in commodities-list)

Endpoint: https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=GCUSD
Documentation: https://site.financialmodelingprep.com/developer/docs#Commoditiescurrency-historical-price-eod-full
dataset: commodities-price-eod
min_age_days=1 days
plans: basic, starter, premium, ultimate
run_days=mon, tues, wed, thurs, fri
