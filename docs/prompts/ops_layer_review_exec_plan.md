# Ops Layer DDD Review ExecPlan

This ExecPlan obeys `docs/AI_context/PLANS.md` and the review guidance captured in `docs/AI_context/test_context.md`. It collects the aggregate/invariant/context-map insights for every class under `src/data_layer/ops` as of 2026-01-27, and it describes the unit tests that must exist before any production change touches those aggregates. Treat this document as living: revise `Progress`, `Surprises & Discoveries`, and the other living sections any time new observations arise so later reviewers can pick up where we left off.

## Purpose / Big Picture

`src/data_layer/ops` houses the persistence and orchestration glue that keeps Bronze/Silver/Gold metadata in sync. The plan’s goal is to confirm the aggregate boundaries, invariants, context-map constants, dependency direction, and entity/value-object roles listed in `docs/AI_context/test_context.md` before editing code. After this work, we will know exactly which behavior each `DatasetInjestion`, `OpsService`, repo, and promotion config class owns, and we will have concrete tests that prove the Bronze manifest/state machine cannot regress, so the dataset contracts stay intact while the UI and run services continue to build on them.

## Progress

- [x] (2026-01-27 18:10Z) Catalogued the `src/data_layer/ops` modules (`dtos`, `infra`, `services`, `requests`) and mapped them to the DDD checklist so all relevant invariants are surfaced.
- [x] (2026-01-27 18:35Z) Explained each aggregate/invariant in the `Surprises & Discoveries` section and translated the operations-layer observations into targeted test blueprints.
- [x] (2026-01-27 18:55Z) Added `tests/unit/ops/test_dataset_ingestion.py`, `tests/unit/ops/test_ops_service.py`, and `tests/unit/ops/test_promotion_config.py`, added the supporting helpers, and verified the commands `python -m pytest tests/unit/ops/test_dataset_ingestion.py|test_ops_service.py|test_promotion_config.py` all pass.

## Surprises & Discoveries

- Observation: `DatasetInjestion` is the immutable value object that carries Bronze/Silver/Gold metadata between the run services and `DuckDbOpsRepo`; every state transition (`bronze_can_promote`, `silver_can_promote`, timestamps) is captured on this object. Evidence: `src/data_layer/ops/dtos/file_injestion.py` defines `from_bronze()` and property setters for the status fields, while `OpsService` repeatedly mutates those fields before calling `upsert_file_ingestion`. Proposed tests: 1) Create a fake `RunResult` and assert `DatasetInjestion.from_bronze` fills the Bronze filename/status/data range expected by the Bronze manifest contract. 2) Simulate `OpsService` `start_silver_ingestion`/`finish_silver_ingestion` calls with a stub repo and confirm the flags (`silver_injest_start_time`, `silver_can_promote`, `bronze_can_promote`) flip in the right order and that errors halt promotion.
- Observation: `OpsService` acts as the aggregate root for run lifecycle metadata (start/finish run, bronze manifest, watermarks, gold insertions) while depending only on lower-level helpers (`DuckDbOpsRepo`, `UniverseService`, `RunContext`). Evidence: `src/data_layer/ops/services/ops_service.py` orchestrates the state machine but never calls higher-layer UI components, and every public method is either idempotent (`get_watermark_date`, `load_input_watermarks`) or wraps `_ops_repo` calls behind try/except logging. Proposed tests: 1) Verify `start_run` pulls tickers from `UniverseService` and that `finish_run` sets `finished_at` before closing the repo. 2) Test `insert_bronze_manifest` swallows repo failures without raising by injecting a repo that raises. 3) Ensure `get_watermark_date` adds one day when there is a previous `bronze_to_date`.
- Observation: `DuckDbOpsRepo` is the data-layer aggregate that merges Bronze/Silver/Gold rows into `ops.file_ingestions`, normalizes optional discriminators/tickers, and produces watermark strings for promotion. Evidence: `src/data_layer/ops/infra/duckdb_ops_repo.py` uses `MERGE`/`COALESCE`, dedupes on `(run_id, file_id)`, and builds serialized watermarks via `DatasetIdentity`. Proposed tests: 1) Use an in-memory DuckDB schema to assert repeated `upsert_file_ingestion` calls upsert rather than duplicate rows and that `list_promotable_file_ingestions` only returns Bronze rows where `bronze_can_promote` is true. 2) Confirm `load_input_watermarks` returns strings matching `DatasetIdentity.serialize_watermark` when rows include discriminator/ticker combinations.
- Observation: The operations layer depends on configuration objects such as `PromotionConfig` and `GoldLoadState` to control chunking/promotion behavior but keeps them simple so colliding modules can share them as DTOs. Evidence: `src/data_layer/ops/requests/promotion_config.py` exposes dedupe/watermark defaults, while `src/data_layer/ops/dtos/gold_load_state.py` is a frozen value object with just a key/last processed timestamp. Proposed tests: 1) Instantiate `PromotionConfig` with non-default strategies (`chunk_strategy="year"`, `dedupe_mode="hash_only"`, `row_group_size=1000`) and ensure the object preserves those values. 2) Confirm `GoldLoadState` equality and serialization remain stable for repeated load runs.
- Observation: The new `tests/unit/ops` suite now codifies the invariants described above, so regression in `DatasetInjestion`, `OpsService`, or `PromotionConfig` is immediately visible. Evidence: `tests/unit/ops/test_dataset_ingestion.py`, `tests/unit/ops/test_ops_service.py`, and `tests/unit/ops/test_promotion_config.py` all pass, guarding the Bronze manifest, service orchestration, and configuration defaults.

## Decision Log

- Decision: Treat `OpsService` as the aggregate orchestrating Bronze/Silver/Gold metadata transitions, and rely on `DatasetInjestion` for all stateful fields. Rationale: This keeps dependencies flowing outward from the service into the repo/DTOs, preserving DDD boundaries and making failures easier to test. Date/Author: 2026-01-27 / Codex.
- Decision: Keep `PromotionConfig` and `GoldLoadState` as immutable value objects so their defaults surface in `tests/unit/ops` without needing mutation helpers. Rationale: These simple DTOs underpin chunking and load bookkeeping, so keeping them frozen prevents downstream services from accidentally sharing mutable state. Date/Author: 2026-01-27 / Codex.

## Outcomes & Retrospective

Once the tests described here exist, we will have provable coverage for every guardrail that `src/data_layer/ops` enforces: Bronze state immutability, repo merges and watermark serialization, service resiliency to repo failures, and configuration-level invariants. This plan will then serve as the definitive source for the behaviors that must stay intact before editing the ops layer again.

## Context and Orientation

The ops layer includes four packages: `dtos` (value objects such as `DatasetInjestion`, `GoldInjestItem`, `SilverInjestItem`, `BronzeInjestItem`, `GoldLoadState`), `infra` (the DuckDB repository, already reviewed in the infra ExecPlan but referenced here), `services` (the `OpsService` aggregate that orchestrates run metadata), and `requests` (configuration DTOs like `PromotionConfig`). Together they capture the Bronze manifest, Silver promotion, and Gold watermark invariants, and they depend only on `Folders`, `settings`, `RunResult`, `RunContext`, and the DuckDB infrastructure described in `docs/AI_context/bronze_data_contracts.md`. Provide docstrings/comments where the invariants are not obvious (e.g., `DatasetInjestion` status transitions, `PromotionConfig` chunk defaults).

## Plan of Work

1. Translate the Surprises & Discoveries into concrete tests: add `tests/unit/ops/test_dataset_ingestion.py`, `tests/unit/ops/test_ops_service.py`, `tests/unit/ops/test_promotion_config.py`, and build on `tests/unit/infra/test_duckdb_ops_repo.py` to cover the additional repo behaviors that ops services rely on. Make sure each test names the invariant it protects (e.g., “Bronze manifest duplicates are merged”).
2. Where invariants are implicit (e.g., `insert_bronze_manifest` suppresses repo exceptions or `PromotionConfig.dedupe_mode` must remain in `{"anti_join","hash_only","none"}`), add docstrings or comments near the aggregate root/mutator noting why the behavior exists, referencing the Bronze/Silver/Gold contracts from `docs/AI_context`.
3. Run the unit tests listed below to validate the new coverage, then update the ExecPlan’s living sections (Progress, Surprises, Decision Log) with the actual timestamps and outcomes.

## Concrete Steps

1. Run `python -m pytest tests/unit/ops/test_dataset_ingestion.py` (2 passed) to validate Bronze metadata is captured by `DatasetInjestion`.
2. Run `python -m pytest tests/unit/ops/test_ops_service.py` (5 passed) to verify `OpsService`’s lifecycle orchestration, watermark math, and repository interactions.
3. Run `python -m pytest tests/unit/ops/test_promotion_config.py` (2 passed) to keep the chunk/dedupe configuration defaults stable.
4. Optionally re-run `python -m pytest tests/unit/infra/test_duckdb_ops_repo.py` and `.../test_ui_duckdb_ops_repo.py` if the repo invariants change in tandem with the ops’ tests; they already pass with the infra suite noted earlier.

Every command now exits with status 0; rerun the specific file that changed if future edits touch the same aggregate.

## Validation and Acceptance

Validation now relies on the commands listed above, which all exit with status 0 (dataset ingestion = 2 passed, ops service = 5 passed, promotion config = 2 passed). Acceptance criteria remain: (1) each `Surprises & Discoveries` observation is covered by one of the new tests or doc comments (the failing command above will catch regressions). (2) The tests fail if the invariant is violated (e.g., `test_ops_service.py` would fail if the timestamp flags stop flipping). (3) The plan stays self-contained so another agent can rerun the identical commands to prove the ops layer still respects the stated guardrails.

## Idempotence and Recovery

Running the commands above multiple times is safe because they use in-memory DuckDB instances or temporary helpers; rerunning a single test file suffices if only one observation changes. If a test goes red, recheck the `Surprises & Discoveries` entry that drives it, fix the implementation, and re-run only the failing command.

## Artifacts and Notes

- This plan references the same DuckDB repo used in `docs/prompts/infra_review_exec_plan.md` so the overlap is intentional: the ops layer relies on those infra invariants, and this plan documents the higher-level perspective.  
- The tests listed here will share helpers from `tests/unit/helpers.py` once they exist; reuse `make_run_result`/`make_run_request` so the fixtures leverage the existing Bronze contract.

## Interfaces and Dependencies

- `data_layer.ops.services.ops_service.OpsService` depends on `DuckDbOpsRepo`, `UniverseService`, `RunResult`, `RunContext`, `LoggerFactory`, and the Bronze metadata captured by `DatasetInjestion`.  
- `data_layer.ops.dtos.file_injestion.DatasetInjestion` is built from `RunResult` via `from_bronze` and contains the status fields that `OpsService` mutates before calling `DuckDbOpsRepo`.  
- `data_layer.ops.infra.duckdb_ops_repo.DuckDbOpsRepo` depends on `data_layer.infra.duckdb.duckdb_bootstrap.DuckDbBootstrap` to execute `MERGE` statements and to read the `ops.file_ingestions` manifest.  
- `data_layer.ops.requests.promotion_config.PromotionConfig` controls chunking/dedupe/watermark behaviors that the Gold promotion pipeline uses; keep the defaults aligned with the `docs/AI_context/trading_strategies.md` cadence rules.  
- `data_layer.ops.dtos.gold_load_state.GoldLoadState` represents the timezone-agnostic watermark key for gold loads and should remain immutable so parallel loads do not race.
