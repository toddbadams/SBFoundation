Problem: Bronze result files with 5-10k rows make Bronze-to-Silver promotion slow when implemented as "loop rows -> instantiate DTO -> write row-by-row". The goal is to rework promotion into a batch, set-based pipeline (DuckDB/pandas) with incremental watermarks, anti-join dedupe, chunked writes, and resumable manifests while preserving Bronze immutability and DTO boundaries.

Current codebase review (aligned to the repo)
- `src/shared/infra/duckdb/silver_service.py` performs per-bronze-file promotion: loads the dataset keymap, maps each payload row into DTOs, builds silver rows, MERGEs into DuckDB, and updates `ops.dataset_watermarks`.
- `src/shared/infra/dataset/*` loads `config/dataset_keymap.yaml` and already treats it as the source of truth for `key_cols`, `row_date_col`, `ticker_scope`, and silver table names.
- `src/orchestration/dataset_recipes.py` reads `config/dataset_keymap.yaml` for recipe definitions.
- Drift vectors today:
  - `src/shared/domain/settings.py` maintains `DATASETS` and `DTO_REGISTRY` separately from the keymap.
  - Many DTOs in `src/**/dtos` set `KEY_COLS = ["ticker"]`, which conflicts with keymap entries that include date or discriminators; these keys are used by silver/gold/manifest repos.

Updated implementation plan (keymap-first, aligned with current shape)
- Remove all parquet logic; DuckDB is the only Silver storage path.
1) Make the keymap the dataset registry (authoritative)
- Define a `DatasetRegistry` (or extend `DatasetKeymapEntry`) that loads `config/dataset_keymap.yaml` and exposes:
  - dataset identity (domain/source/dataset/discriminator)
  - `ticker_scope`, `key_cols`, `row_date_col`, `silver_schema`, `silver_table`
  - recipe attributes (data_source_path, date_key, cadence, plans)
- Ensure dataset enumerations (`DATASETS`, recipe sources, promotion targets) are derived from the keymap.

2) Resolve DTO types against the keymap (no drift)
- Selected: code-driven `DTO_REGISTRY` mapping in code, validated against the keymap on startup.
- Fail fast when strict validation is enabled; otherwise log mismatches for visibility.

3) Eliminate KEY_COLS drift
- Treat `entry.key_cols` from the keymap as the source of truth for all upserts/merges (already true in `silver_service`).
- Ensure all repo configs and merges use `entry.key_cols` instead of `dto_type.KEY_COLS`.
- Add a consistency check to compare DTO.KEY_COLS (if kept) with `entry.key_cols` and log/raise on mismatch.

4) Promote in batches (performance)
- Replace per-row DTO instantiation with a vectorized projection step that builds a DataFrame from payload content, injects `ticker`, normalizes column names, and computes `row_date_col`.
- Keep a thin DTO fallback for complex derived fields only.
- Use DuckDB MERGE on a temporary staging table per batch.

Batch projection scope (v1)
- In scope: column renames, snake_case normalization, primitive type coercions, ticker injection, `row_date_col` derivation, and discriminator columns from the keymap.
- Out of scope: complex derived fields, cross-row calculations, or schema-dependent enrichments (use DTO fallback for these).
- Output: a silver-shaped DataFrame matching `entry.key_cols` + required columns used by the silver table.

5) Incremental and idempotent
- Keep `ops.dataset_watermarks` updates (already in place).
- Use anti-join or MERGE with a temp staging table keyed by `entry.key_cols` to avoid duplicates.
- Track per-bronze-file promotion status (manifest) for resumability.

6) Snapshot endpoints handling
- For `date_key = null`, write `as_of_date` per run and treat it as the row date.
- Ensure `row_date_col` in the keymap is set to `as_of_date` for snapshot datasets.

Answers captured (from the questions section)
1) Current Silver storage format: DuckDB.
2) Definitive dedupe key per dataset: `key_cols` in `config/dataset_keymap.yaml`.
3) Overwrite on same key_date: allow overwrite (DuckDB MERGE already does this).
4) Snapshot endpoints (`date_key=None`): one row per run using `as_of_date` as the row date.
5) Biggest pain: CPU time and thermal shutdown.
6) Bronze result files are one API response per file with full `FMPResult` shape and `content` list: YES.
7) Promotion parallelism: single-threaded but fast.
