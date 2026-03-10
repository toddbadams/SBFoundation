-- Remove Silver rows with NULL calendar_year from annual income statement table.
-- Caused by calendarYear->fiscalYear mapping bug in IncomeStatementBulkDTO.
-- Quarter tables are omitted here; they will be cleaned on first creation.
DELETE FROM silver.fmp_income_statement_bulk_annual WHERE calendar_year IS NULL;
