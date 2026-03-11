-- Definitive reset for all annual Bronze files after the fiscalYear keymap fix.
-- Previous migrations used silver_rows_created=0 as a guard, but files promoted
-- with NULL calendar_year (before the fix) had rows_created > 0, so they were
-- not reset. Unconditionally restore all annual files so the next run re-promotes
-- with the correct api: fiscalYear mapping in place.
UPDATE ops.file_ingestions
SET bronze_can_promote = TRUE,
    silver_rows_created = 0,
    silver_rows_updated = 0,
    silver_injest_start_time = NULL,
    silver_injest_end_time = NULL
WHERE domain = 'annual';
