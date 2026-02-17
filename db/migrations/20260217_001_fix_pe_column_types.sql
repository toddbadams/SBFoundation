-- Migration: Fix pe column type from INTEGER to DOUBLE
-- Date: 2026-02-17
-- Issue: pe columns were created as INTEGER but should be DOUBLE to store decimal values

-- Fix fmp_market_sector_pe
ALTER TABLE silver.fmp_market_sector_pe
ALTER COLUMN pe TYPE DOUBLE;

-- Fix fmp_market_industry_pe
ALTER TABLE silver.fmp_market_industry_pe
ALTER COLUMN pe TYPE DOUBLE;
