-- After adding api: fiscalYear to keymap calendar_year columns, existing Silver
-- rows still have NULL calendar_year. Delete them and reset Bronze promotion
-- flags so the next run re-promotes all annual files with correct values.
DELETE FROM silver.fmp_income_statement_bulk_annual WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_balance_sheet_bulk_annual    WHERE calendar_year IS NULL;
DELETE FROM silver.fmp_cashflow_bulk_annual         WHERE calendar_year IS NULL;

UPDATE ops.file_ingestions
SET bronze_can_promote = TRUE,
    silver_rows_created = 0,
    silver_rows_updated = 0,
    silver_injest_start_time = NULL,
    silver_injest_end_time = NULL
WHERE domain = 'annual'
  AND bronze_can_promote = FALSE
  AND silver_rows_created = 0;
