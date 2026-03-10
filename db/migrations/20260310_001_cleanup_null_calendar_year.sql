-- Remove Silver rows with NULL calendar_year caused by calendarYear→fiscalYear
-- mapping bug in bulk fundamental DTOs. Re-ingestion will repopulate with
-- correct year values keyed on (symbol, period, calendar_year).
DELETE FROM silver.fmp_income_statement_bulk_annual  WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_income_statement_bulk_quarter WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_balance_sheet_bulk_annual     WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_balance_sheet_bulk_quarter    WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_cashflow_bulk_annual          WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_cashflow_bulk_quarter         WHERE calendar_year IS NULL;
