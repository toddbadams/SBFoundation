# Orchestrator Chunked Plan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds per `docs/AI_context/PLANS.md`.

## Purpose / Big Picture

Splitting orchestrator workloads by ticker affinity makes the Bronze/Silver/Gold pipeline more predictable: flat recipes run once and get promoted immediately, while the heavier ticker-based recipes run afterward in manageable chunks defined by a single `Orchestrator` constant. After implementation anyone triggering `Orchestrator.run()` will observe deterministic ordering (non-ticker first, then chunked ticker batches) and be able to trace chunk execution through the standard bronze->silver->gold log lines that already exist.

## Progress

- [x] (2026-01-18T17:45:07Z) Captured the high-level requirement to break recipes into non-ticker versus ticker groups and to chunk the ticker group, so this ExecPlan can define the remaining work.
- [x] (2026-01-18T17:58:10Z) Implemented orchestration chunking helpers, per-chunk bronze/silver/gold flow, and a focused test that confirms partitioning, chunk sizes, and promotion sequencing.
- [x] (2026-01-19T10:17:48Z) Migrated recipe partitioning into `DatasetService`, added `_process_non_ticker_recipes`/`_process_ticker_recipes`, and introduced `OrchestrationTickerChunkService` so the chunk logic lives in its own helper class per the bugs list.
- [x] (2026-01-19T11:26:26Z) Verified that silver promotions run even when bronze/bronze files are skipped during the same run and added a regression test that mirrors the described scenario.

## Surprises & Discoveries

- Observation: `pytest_cov` reports there was no coverage data because the new test module does not import the analytics/data_platform packages.
  Evidence: `poetry run pytest tests/test_orchestrator.py` prints coverage warnings that modules `analytics` and `data_platform` were never imported and "No data was collected."

## Decision Log

- Decision: Non-ticker recipes run through bronze, silver, then gold before starting ticker-based work.
  Rationale: The requirement explicitly orders the two groups to ensure the lighter data is fully promoted before the heavier ticker data is processed.
  Date/Author: 2026-01-18T17:45:07Z / Codex

- Decision: Ticker-based recipes will be chunked in batches of `TICKER_RECIPE_CHUNK_SIZE` (set to 10) within `Orchestrator` and each chunk will feed only the bronze stage; silver/gold run after every ticker chunk to keep the bronze chunks bounded while still promoting each batch before the next chunk starts.
  Rationale: This keeps the new chunking support additive (bronze is chunked for rate-limiting) while ensuring each chunk is promoted fully before starting the next chunk, which matches the clarified requirement.
  Date/Author: 2026-01-18T17:45:07Z / Codex

- Decision: `_process_recipe_list` is now shared by the non-ticker and ticker chunk loops with `TICKER_RECIPE_CHUNK_SIZE` exposed as a class constant and chunk logs describing dataset ranges before and after each bronze run.
  Rationale: Sharing the helper keeps bronze ingestion consistent, while the logging and dataset label let the operator trace chunk boundaries without hunting for metadata in other files.
  Date/Author: 2026-01-18T17:58:10Z / Codex

- Decision: `DatasetService` now owns `non_ticker_recipes` and `ticker_recipes`, while `OrchestrationTickerChunkService` encapsulates the chunk loops so orchestrator only orchestrates the phases without dealing with chunk slicing.
  Rationale: This keeps recipe filtering close to its source and isolates chunk logging/promotion behavior, making the orchestrator easier to reason about and test.
  Date/Author: 2026-01-19T10:17:48Z / Codex

## Outcomes & Retrospective

Expected outcome: `Orchestrator.run()` now partitions recipes once, routes the non-ticker block through `_process_recipe_list`, and then iterates through ticker chunks sized by `TICKER_RECIPE_CHUNK_SIZE` with per-chunk start/finish logs. Each chunk now executes bronze then immediately calls silver and gold promotions, so the final run summary reflects every chunk; the added test proves the partitioning, chunk slicing, and promotion sequence. Retrospective notes should mention that the chunk log messages and reused helper make the new behavior easy to audit during a live run.

## Context and Orientation

`src/data_layer/orchestrator.py` now drives the non-ticker and ticker paths through `_process_non_ticker_recipes` and `_process_ticker_recipes`. The first path optionally runs bronze (when `switches.bronze` is true) and always invokes `_promote_silver`/`_promote_gold` when the switches permit, while the second path fetches ticker recipes directly via `DatasetService.ticker_recipes` and lets `OrchestrationTickerChunkService` handle chunk slicing/logging and per-chunk promotions. The new `execute_non_ticker_recipes` and `execute_ticker_recipes` switches allow callers to run only one workload, `RunContext` continues to collect counters for each phase, and `DatasetService.non_ticker_recipes`/`.ticker_recipes` reuse the original filtering logic so no state is duplicated.

## Plan of Work

1. Add `TICKER_RECIPE_CHUNK_SIZE = 10`, move the recipe partitioning into `DatasetService.non_ticker_recipes`/`ticker_recipes`, and keep `_process_recipe_list` on `Orchestrator` so it continues to register recipes with `BronzeService`.

2. Restructure `run()` so that `_process_non_ticker_recipes` handles Flat recipes first, then `_promote_silver`/`_promote_gold` run once before `_process_ticker_recipes` starts the chunk loop.

3. Introduce `OrchestrationTickerChunkService`, move all chunk logging/slicing/promotion hooks into it, and have `_process_ticker_recipes` instantiate that service with `_process_recipe_list`, `_promote_silver`, and `_promote_gold`.

4. Add `tests/test_orchestrator.py` to mock `DatasetService.recipes` and `BronzeService`, inject a dummy `OpsService`, and assert that the non-ticker batch runs first, ticker recipes split into size-10 chunks, and silver/gold run once per bronze block; verify the behavior with `poetry run pytest tests/test_orchestrator.py`.

5. Confirm the silver promotion still runs when `bronze=False` but `silver=True` by adding a regression test that ensures `_promote_silver` is invoked even without a new bronze ingestion, mirroring the previously failing workflow.

## Concrete Steps

1. `DatasetService` now exposes `non_ticker_recipes` and `ticker_recipes`, and `Orchestrator` keeps `_process_recipe_list` to handle the actual ingestion so each helper returns a consistent `RunContext`.

2. `run()` now calls `_process_non_ticker_recipes`, runs `_promote_silver/_promote_gold`, then uses `_process_ticker_recipes`, which instantiates `OrchestrationTickerChunkService` to handle chunk slicing/logging and successive silver/gold promotions per chunk.

3. Added `tests/test_orchestrator.py` that mocks `DatasetService.recipes` and `BronzeService`, injects a `DummyOpsService`, and asserts chunk order, chunk sizes, and per-chunk promotions; run the suite with `poetry run pytest tests/test_orchestrator.py`.

4. Added `test_silver_runs_without_bronze` to prove `_promote_silver` still fires when `OrchestrationSwitches` disables bronze but enables silver, preventing regressions for the described scenario.
4. (Proof)
   poetry run pytest tests/test_orchestrator.py
   ... tests/test_orchestrator.py::test_orchestrator_processes_chunks PASSED
   WARNING: Failed to generate report: No data to report.

## Validation and Acceptance

Running the new or updated test suite (`poetry run pytest tests/test_orchestrator.py`) should pass; the critical assertion is that bronze is invoked twice (non-ticker chunk and chunked ticker batches) but silver/gold are invoked in the prescribed order. Manual verification via a dry run (e.g., setting `Orchestrator.switches` to skip silver/gold and watching the log output) should show the non-ticker chunk logs before the ticker chunk logs and that ticker chunks honor `TICKER_RECIPE_CHUNK_SIZE`. Any additional smoke test should catch API rate limits by confirming chunk logs appear before the ticker data hits silver/gold.

## Idempotence and Recovery

The new chunking logic is additive: calling `run()` multiple times with the same recipes and today date will still append the same bronze files because we re-use the existing `RunContext`, `OpsService`, and `BronzeService` behavior. If a chunk fails, existing bronze error handling already logs the failure while leaving the summary in a safe state, so re-running will restart at the same partition without needing manual cleanup.

## Artifacts and Notes

As work proceeds, capture the chunked bronze log entries and the additive run summary totals to demonstrate the opposite ordering (non-ticker first, ticker after). If any temporary scripts or fixtures are created for testing, note them here with short summaries of their output.

## Interfaces and Dependencies

`Orchestrator` continues to rely on `BronzeService` and `RunContext`, but recipe filtering now happens through `DatasetService.non_ticker_recipes` and `.ticker_recipes`. The class exposes `TICKER_RECIPE_CHUNK_SIZE: int`, `_process_non_ticker_recipes(run_summary: RunContext)` for flat recipes, `_process_ticker_recipes(run_summary: RunContext)` to invoke `OrchestrationTickerChunkService`, and `_process_recipe_list(recipes: list[DatasetRecipe], run_summary: RunContext)` for the actual bronze ingestion. `OrchestrationTickerChunkService` accepts the existing `_promote_silver` and `_promote_gold` callables so the orchestrator can reuse them while `RunContext` tracks cumulative counters for chunked promotions.

## Questions

- None remain; the requirements have been clarified (chunk size 10 and silver/gold after each ticker chunk).

Change Note: 2026-01-18T17:51:39Z Added the confirmed chunk size (10) everywhere it appears in the plan and noted the implication for the ticker batching decision log per the user's update request.
Change Note: 2026-01-18T17:52:30Z Updated the Decision Log, Plan of Work, and Concrete Steps to reflect that silver and gold promotions run after every ticker chunk rather than once per ticker group, aligning with the clarified behavior.
Change Note: 2026-01-18T17:58:10Z Added the orchestrator implementation, chunk logging helpers, and the focused acceptance test, capturing the coverage warning as part of the validation narrative.
Change Note: 2026-01-19T10:17:48Z Moved recipe partitioning into `DatasetService`, introduced `_process_non_ticker_recipes`/`_process_ticker_recipes`, and delegated ticker chunk slicing/promotion logging to `OrchestrationTickerChunkService`.
Change Note: 2026-01-19T11:26:26Z Fixed the silver-only replay workflow by allowing `_promote_silver` to run even when bronze ingestion is skipped and added a regression test to prove the behavior.

## Bugs and Changes

1) Move the `_load_and_partition_recipes` responsibilities into `src/data_layer/services/bronze/bronze_recipe_service.py`.
   - Two helper methods (`non_ticker_recipes`, `ticker_recipes`) now filter the recipes and are invoked directly from `Orchestrator.run()`. ✅

2) `Orchestrator` now has `_process_non_ticker_recipes` to focus on the non-ticker recipes and `_process_ticker_recipes` to run the ticker batches, so each path stays isolated. ✅

3) All chunk iteration/debug logging now lives inside `OrchestrationTickerChunkService`, which is invoked from `_process_ticker_recipes` and calls `_process_recipe_list`, `_promote_silver`, and `_promote_gold` per chunk. ✅

4) when running the orchestrator with the following switches:
        bronze: bool = True,
        silver: bool = False,
        gold: bool = False,
        ticker_limit: int = 1,
        execute_non_ticker_recipes: bool = True,
        execute_ticker_recipes: bool = False,
    This creates the json result files from the bronze load service.
    Then running the orchestrator with the following switches:
        bronze: bool = False,
        silver: bool = True,
        gold: bool = False,
        ticker_limit: int = 1,
        execute_non_ticker_recipes: bool = True,
        execute_ticker_recipes: bool = False,
    This does not pick up the previously loaded bronze json file. Therefore no silver DTOs were loaded. ✅
