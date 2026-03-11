-- Remove Silver rows with NULL calendar_year from all three annual bulk tables.
-- Caused by calendarYear->fiscalYear mapping bug fixed in bulk fundamental DTOs.
-- 20260310_001 was swallowed (CatalogException on missing quarter table) so
-- income_statement_bulk_annual is also cleaned here.
DELETE FROM silver.fmp_income_statement_bulk_annual WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_balance_sheet_bulk_annual    WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_cashflow_bulk_annual         WHERE calendar_year IS NULL;
