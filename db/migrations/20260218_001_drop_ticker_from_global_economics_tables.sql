-- Migration: Drop ticker column from global economics silver tables
-- Date: 2026-02-18
-- Issue: ticker was never present in the vendor payload for these global (non-ticker-scoped) datasets

ALTER TABLE silver.fmp_economic_indicators
DROP COLUMN IF EXISTS ticker;

ALTER TABLE silver.fmp_market_risk_premium
DROP COLUMN IF EXISTS ticker;

ALTER TABLE silver.fmp_treasury_rates
DROP COLUMN IF EXISTS ticker;
