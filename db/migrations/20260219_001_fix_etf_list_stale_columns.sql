-- Drop stale columns from silver.fmp_etf_list that do not exist in the bronze payload.
-- ETFListDTO only emits: symbol, company_name.
-- These columns were written by an older version of the DTO and were never dropped.
ALTER TABLE silver.fmp_etf_list DROP COLUMN IF EXISTS price;
ALTER TABLE silver.fmp_etf_list DROP COLUMN IF EXISTS exchange;
ALTER TABLE silver.fmp_etf_list DROP COLUMN IF EXISTS exchange_short_name;
ALTER TABLE silver.fmp_etf_list DROP COLUMN IF EXISTS ticker;
