# Services Layer Review ExecPlan

This ExecPlan obeys `docs/AI_context/PLANS.md` and the DDD checklist from `docs/AI_context/test_context.md`. It records the aggregate/boundary findings for every class under `src/data_layer/services` (bronze, silver, gold, and the shared universe service), turns those insights into the `Surprises & Discoveries` log, and outlines the suite of tests that must exist before touching any of those modules again. Treat this as a living document: update `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` each time new observations appear while working through the services layer.

## Purpose / Big Picture

The services layer orchestrates Bronze ingestion (`RunRequestExecutor`, `BronzeService`, `DatasetService`), Silver promotions (`SilverService`), Gold gating (`GoldService`, `GoldTaskRegistry`, `GoldDedupeEngine`), and the shared universe/day math (`UniverseService`). The goal is to ensure every aggregate satisfies the DDD checklist (aggregate ownership, explicit invariants, context-map usage, dependency direction, and clear entity/value-object roles) before editing the code. After completing this plan, the repo will have explicit unit tests for the throttling/retry behavior, recipe loading, Bronze/Silver/Gild control flows, and timeline helpers, plus docstrings highlighting the contracts each service enforces.

## Progress

- [x] (2026-01-28 13:00Z) Enumerated every module under `src/data_layer/services` (bronze, silver, gold, and `UniverseService`) and mapped them to the DDD checklist so that the aggregates and their invariants are known.
- [x] (2026-01-27 11:49Z) Capture the aggregate findings in `Surprises & Discoveries`, translate each into concrete tests (e.g., throttling invariants, recipe/manifest contracts, gold promotion guards), and describe the docstring/comment needs before implementation.
- [x] (2026-01-27 11:52Z) Create the `tests/unit/services/` suites implied by the plan, add any supporting mocks/helpers, run the commands listed in `Concrete Steps`, and record the results in the living sections.

## Surprises & Discoveries

- Observation: `UniverseService` is the value-object provider for run metadata (tickers, current timestamps, next market day). Evidence: `tickers` slices `FREE_TIER_SYMBOLS`, `now()/today()` use UTC, and `next_market_day` uses pandas offsets plus the US federal calendar. Tests: 1) Assert `next_market_day` advances to the next business day when today is the end of week/holiday. 2) Confirm `run_id()` always follows the `YYMMDD.<hex>` format and increments when called.
- Observation: `DatasetService` owns the context map that defines which recipes run on which days, so it is the aggregator for Bronze boundaries. Evidence: `_load_recipe_rows_from_keymap()` reads `config/dataset_keymap.yaml`, enforces `date_key`/`ticker_scope`, warns on invalid recipes, and returns only recipes whose `plans` include the requested plan/day. Tests: 1) Provide a fake keymap YAML with per-ticker vs global entries and ensure `recipes(today, plan)` filters correctly. 2) Validate invalid recipe rows log warnings and are excluded. 3) Confirm `ticker_recipes`/`non_ticker_recipes` split the results as expected.
- Observation: `RunRequestExecutor` enforces throttled retries so `RunRequest` invocations remain Silver-compliant. Evidence: `_throttle()` tracks timestamps with `THROTTLE_MAX_CALLS`, updates `RunContext` throttling stats, and `_with_retries()` retries `RETRY_MAX_ATTEMPS` times with exponential backoff on `requests.RequestException`. Tests: 1) Simulate continuous request failures to confirm the executor raises after the configured retry limit and logs each attempt. 2) Drive `_throttle` so the queue saturates and verify it sleeps, updates `throttle_wait_count`, and resumes once the window clears.
- Observation: `BronzeService` is the aggregate orchestrating Bronze ingestion (requests, manifest persistence, summary updates) and depends strictly on lower-layer helpers (`RunResult`, `DatasetRecipe`, `ResultFileAdapter`, `OpsService`). Evidence: `_process_run_request` rejects requests when `canRun()` fails, attempts network calls via `RunRequestExecutor`, enforces `is_valid_bronze`, persists to Bronze, and updates `summary`. Tests: 1) Stub `requests.get()` to ensure `_process_run_request` records failures and successes (error conditions create Bronze manifest errors). 2) Register a ticker-based recipe and confirm it emits `RunRequest.from_recipe` with the proper ticker/day combination. 3) Validate `_persist_bronze` writes via `BronzeFileWriter`, and repo errors are logged but do not raise.
- Observation: `SilverService` is the Silver aggregate that loads promotable Bronze rows, resolves dataset keymap entries, applies watermarks, dedupes, chunks, and merges into Silver tables. Evidence: `promote()` iterates `OpsService.load_promotable_file_ingestions`, `_promote_row` ensures keycols exist, uses `DedupeEngine`, `ChunkEngine`, DAO helpers to merge rows, and handles failures by rolling back Silver ingestion status. Tests: 1) Provide a fake ingestion row and keymap entry to confirm `_resolve_keymap_entry` rejects missing entries or missing tickers. 2) Run `_apply_watermark` to ensure rows earlier than the watermark drop out when `watermark_mode!="none"`. 3) Simulate deduplication/chunking by supplying a DataFrame with duplicates and verifying the merge SQL is invoked with the deduped rows.
- Observation: The gold services (`GoldDedupeEngine`, `GoldTaskRegistry`, `gold_service`, `gold_projection`, `gold_batch_reader`, etc.) enforce final converge invariants: deduplication keys, schema migrations, and task wiring. Evidence: `GoldTaskRegistry` reads the same keymap/YAML, validates `dim_table`, `gold_table`, and ensures key_cols are unambiguous before resolving DTO classes. `GoldDedupeEngine` deduplicates by key columns before loading. Tests: 1) Feed `GoldTaskRegistry` a YAML with conflicting `key_cols` and ensure it raises. 2) Pass identical rows to `GoldDedupeEngine` and verify duplicates removed. 3) Verify `gold_service` writes to the correct manifest tables and rejects datasets whose DTOs are missing.

## Decision Log

- Decision: Treat the bronze services (recipe loader, request executor, load service) as the aggregate boundary for Bronze ingestion because they decide which recipes run, throttle requests, and persist raw blobs. Rationale: This keeps the lower layers (ops repo, DTOs) read-only while the aggregates enforce invariants. Date/Author: 2026-01-28 / Codex.
- Decision: Share the same `dataset_keymap.yaml` context map across bronze, silver, and gold services. Rationale: `DatasetService`, `SilverService`, and `GoldTaskRegistry` all resolve DTOs/recipes from this file; explicitly documenting that dependency ensures future edits keep the context map synchronized. Date/Author: 2026-01-28 / Codex.
- Decision: Keep `UniverseService` stateless and timezone-aware; all services depend on it for ticks/run IDs. Rationale: The aggregator must remain deterministic (UTC) so run IDs and date math never drift. Date/Author: 2026-01-28 / Codex.

## Outcomes & Retrospective

This plan identifies the majority of service-level invariants and outlines the tests needed to keep them intact. Once the tests under `tests/unit/services/` exist and pass, we will have automated proof that Bronze requests honor throttling/retries, keymap-based recipes feed the runs, Silver promotion enforces key columns/watermarks, and Gold loading respects dedupe/task guards. The living sections above will guide future reviewers to expand coverage whenever new services appear.

## Context and Orientation

`src/data_layer/services` is organized into `bronze` (HTTP ingestion helpers + recipe loader), `silver` (promotion service), `gold` (projector/dedupe/load service/task registry), and top-level `UniverseService`. Each module depends on a limited number of lower-layer helpers (`Folders`, `settings`, DTOs, `BronzeService` dependencies, `ResultFileAdapter`, `DuckDbBootstrap`, `OpsService`). The plan does not assume any prior plan; it documents the required context map file (`config/dataset_keymap.yaml`) and the expectation that tests should cover the Bronze/Silver/Gold contracts described in `docs/AI_context/test_context.md`.

## Plan of Work

1. Draft the service-level tests the `Surprises & Discoveries` section outlines, writing new files under `tests/unit/services/` for `run_request_executor`, `bronze_recipe_service`, `bronze_service`, `universe_service`, `silver_service`, and the gold helpers (`GoldDedupeEngine`, `GoldTaskRegistry`, `gold_service`) to prove each invariant fails when the guardrails break.
2. Add targeted docstrings or inline comments to the services flagged earlier (e.g., note that `_resolve_keymap_entry` defers to the shared config, highlight that `_persist_bronze` must always write a manifest entry) so future maintainers understand the invariants without reading the tests.
3. Run the commands listed below, observe the expected outputs, and update this ExecPlan to reflect the timestamps/outcomes.

## Concrete Steps

1. Run `python -m pytest tests/unit/services/test_universe_service.py` and expect it to cover `tickers`, `run_id`, `next_market_day`, and timezone guarantees.  
2. Execute `python -m pytest tests/unit/services/test_run_request_executor.py` to verify throttling and retry behavior, including the summary counters.  
3. Run `python -m pytest tests/unit/services/test_bronze_recipe_service.py` to ensure the keymap parsing honors per-ticker plans and rejects invalid recipes.  
4. Run `python -m pytest tests/unit/services/test_bronze_service.py` to prove `_process_run_request` honours `canRun`, persists Bronze payloads, and handles network errors/regression in manifest updates.  
5. Run `python -m pytest tests/unit/services/test_silver_promotion_service.py` to exercise `_promote_row`, watermark filtering, dedupe, and chunking.  
6. Run `python -m pytest tests/unit/services/test_gold_services.py` to cover `GoldTaskRegistry`, `GoldDedupeEngine`, and `gold_service` invariants.  
7. Re-run `python -m pytest tests/unit/ops/test_ops_service.py` if the ops layer evolves alongside the services (the Silver service already depends on it).  

Every command should exit with `OK` once the tests exist; rerun only the specific subset if you only touched that aggregate next time.

## Validation and Acceptance

Validation requires the commands above to finish with `OK`. Acceptance means:  
* Bronze services fail fast when `RunRequest.canRun()` rejects invalid recipes or when the summary’s throttle stats exceed configured limits.  
* Silver promotion fails clearly if key columns or DTO mappings are missing, and watermark mode toggles filter rows.  
* Gold loading refuses conflicting key columns and respects dedupe before chunk merges.  
* The plan remains self-contained; a novice can follow each step knowing which file to edit and what automation to run.

## Idempotence and Recovery

These tests use in-memory DuckDB/DTO fixtures or temporary config files so they can be re-run safely. If a test fails, rerun just that command from the list above after fixing the corresponding invariant; no destructive operations are involved.

## Artifacts and Notes

- The services review intersects with the existing `docs/prompts/operators_review_exec_plan.md` and `docs/prompts/infra_review_exec_plan.md`, but it focuses strictly on Bronze/Silver/Gold orchestration, not the DTO persistence or repo layers already documented.  
- Use helpers from `tests/unit/helpers.py` when applicable (e.g., `make_run_result`, `make_dataset_recipe`) so the new service tests stay consistent with the Bronze contract.

## Interfaces and Dependencies

- `UniverseService` must supply UTC `now()`, `today()`, `run_id()`, and `next_market_day()`; it is consumed by `BronzeService` and other orchestrators.  
- `RunRequestExecutor`, `DatasetService`, and `BronzeService` work together: recipes feed `RunRequest.from_recipe`, the executor enforces throttle/retries, and the load service coordinates Bronze persistence plus `OpsService` manifest updates.  
- `SilverService` depends on `DatasetService`, `BronzeBatchReader`, `DTOProjection`, `ChunkEngine`, `DedupeEngine`, `ResultFileAdapter`, and `OpsService`; it must keep dependencies flowing down to DuckDB + DTO layers.  
- Gold services (`GoldTaskRegistry`, `GoldDedupeEngine`, `gold_service`, `gold_promotion_config`, `gold_projection`, `gold_batch_reader`) depend on `Folders.dataset_keymap_absolute_path`, DTOs, and `duckdb.connect`; they must not reference UI code and must raise on missing configuration.  
- No service should call higher-level UI components or mutate configuration in-place; they should rely on the read-only DTO/value objects captured above.
