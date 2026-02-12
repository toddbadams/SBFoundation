### RunContext persistence reminder

The previous RunSummary artifacts have been retired; the metadata now lives in `ops.file_ingestions` and is represented in code by `RunContext`.

1. Ensure Bronze/Silver/Gold services only talk to `RunContext` and never emit the old JSON summaries.
2. Keep `OpsService.start_run` / `finish_run` coupled to `RunContext`, and make sure `DuckDbOpsRepo.upsert_file_ingestion` writes the high-watermark rows that later get promoted.
3. The orchestrator should log `run_context.msg` / `formatted_elapsed_time` but otherwise avoid referencing legacy objects.
4. Write SQL when validating the pipeline:

```sql
SELECT run_id, started_at, finished_at, status
FROM ops.file_ingestions
GROUP BY run_id
ORDER BY started_at DESC
LIMIT 5;

SELECT run_id, bronze_rows, bronze_error
FROM ops.file_ingestions
WHERE bronze_rows IS NOT NULL
ORDER BY bronze_injest_start_time DESC
LIMIT 10;
```

Use these statements to confirm every run_id recorded in `ops.file_ingestions` has aggregate timestamps and counts accessible to downstream services.
