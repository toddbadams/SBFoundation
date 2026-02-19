-- Fix silver.fmp_index_list column mapping errors:
--   stock_exchange was mapped to API key "stockExchange" which does not exist in the payload.
--   The actual payload field is "exchange" — rename the column to preserve existing data.
--   exchange_short_name and ticker do not exist in the bronze payload and are removed.
ALTER TABLE silver.fmp_index_list RENAME COLUMN stock_exchange TO exchange;
ALTER TABLE silver.fmp_index_list DROP COLUMN IF EXISTS exchange_short_name;
ALTER TABLE silver.fmp_index_list DROP COLUMN IF EXISTS ticker;
