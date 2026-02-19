-- Drop redundant `symbol` column from financial statement Silver tables.
--
-- These columns duplicated `ticker` (both mapped from the FMP API "symbol" response field).
-- The DTO `ticker` field is the canonical identifier; `symbol` was a stale remnant.
-- Safe to run multiple times (DROP COLUMN IF EXISTS).

ALTER TABLE silver.fmp_income_statement DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_balance_sheet_statement DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_cashflow_statement DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_income_statement_growth DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_balance_sheet_statement_growth DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_cashflow_statement_growth DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_company_delisted DROP COLUMN IF EXISTS symbol;
