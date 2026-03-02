-- Add discriminator column to silver.fmp_market_screener.
-- Required so that universe snapshot queries can filter rows by universe+exchange
-- discriminator (e.g. WHERE discriminator LIKE 'us_large_cap-%').
-- Existing rows receive an empty-string default; they are effectively orphaned by
-- the updated key_cols = [symbol, discriminator] and will not surface in filtered
-- universe queries. Re-running the market domain will insert correctly-keyed rows.
ALTER TABLE silver.fmp_market_screener ADD COLUMN IF NOT EXISTS discriminator VARCHAR DEFAULT '';
