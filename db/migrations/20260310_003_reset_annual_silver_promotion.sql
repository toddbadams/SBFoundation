-- Reset Silver promotion metadata for annual Bronze files whose Silver rows were
-- deleted by migration 20260310_002 (NULL calendar_year cleanup). Without this,
-- list_promotable_file_ingestions excludes them (silver_rows_created > 0 filter).
UPDATE ops.file_ingestions
SET silver_rows_created = 0,
    silver_rows_updated = 0,
    silver_injest_start_time = NULL,
    silver_injest_end_time = NULL,
    silver_can_promote = TRUE
WHERE domain = 'annual'
  AND silver_rows_created > 0;
