-- finish_silver_ingestion sets bronze_can_promote=FALSE after successful promotion.
-- Migration 20260310_003 reset silver_rows_created but not bronze_can_promote, so
-- list_promotable_file_ingestions still excludes these files (requires TRUE).
-- Restore bronze_can_promote for annual files whose Silver data was deleted.
UPDATE ops.file_ingestions
SET bronze_can_promote = TRUE
WHERE domain = 'annual'
  AND bronze_can_promote = FALSE
  AND silver_rows_created = 0;
