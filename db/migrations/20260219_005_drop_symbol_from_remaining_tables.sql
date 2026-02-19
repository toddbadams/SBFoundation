-- Drop redundant `symbol` column from remaining Silver tables.
--
-- These columns duplicated `ticker` (both mapped from the FMP API "symbol" response field).
-- Companion to migration 20260219_004 which covered financial statement tables.
-- Safe to run multiple times (DROP COLUMN IF EXISTS).

-- Fundamentals
ALTER TABLE silver.fmp_enterprise_values DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_financial_scores DROP COLUMN IF EXISTS symbol;
-- fmp_financial_statement_growth: table not yet ingested; symbol column will never be written (DTO cleaned up)
ALTER TABLE silver.fmp_key_metrics DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_key_metrics_ttm DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_metric_ratios DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_owner_earnings DROP COLUMN IF EXISTS symbol;
-- fmp_revenue_product_segmentation: table not yet ingested; symbol column will never be written (DTO cleaned up)
-- fmp_revenue_geographic_segmentation: table not yet ingested; symbol column will never be written (DTO cleaned up)

-- Technicals
ALTER TABLE silver.fmp_technicals_historical_price_eod_full DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_technicals_historical_price_eod_dividend_adjusted DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_technicals_historical_price_eod_non_split_adjusted DROP COLUMN IF EXISTS symbol;
