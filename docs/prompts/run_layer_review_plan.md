# Run Layer DDD Review Plan

This ExecPlan documents the review of every DTO and helper under `src/data_layer/run` (the repository folder that fulfills the user request to review `/src/run`) and records the DDD checklist observations, Good Python Practice checklists, and the specific tests that will prove each guardrail. The file lives under `/docs/prompts` so future reviewers can find the ExecPlan alongside the testing artifacts it asks for.

## Purpose / Big Picture

The run layer orchestrates Bronze ingestion (recipes, requests, results, run contexts) and the chunk/orchestration helpers that buffer those DTOs into batched work. This plan ensures the DDD aggregate/value-object checklist is applied to each of the classes (DatasetRecipe, RunRequest, RunResult, RunContext, RunDataDatesDTO, the result mapper, and the chunk/orchestration services), that shared configuration constants govern their invariants, and that every observation is translated into concrete unit tests before editing production code. After these tests are in place, we will have confidence that the run layer enforces Bronze immutability, context-map consistency, dependency direction, and the entity/value-object semantics spelled out in `docs/AI_context/test_context.md`.

## Progress

- [x] (2026-01-27 10:15Z) Captured the need to review `/src/data_layer/run` classes per the user's DDD checklist request and save the resulting ExecPlan under `/docs/prompts`.
- [x] (2026-01-27 11:10Z) Followed the checklist, recorded the run-layer observations, and identified where standardized comments or docstrings could clarify the contracts.
- [x] (2026-01-27 11:45Z) Added pytest modules (`tests/unit/test_dataset_recipe.py`, `tests/unit/test_run_request.py`, `tests/unit/test_run_result.py`, `tests/unit/test_run_context.py`, `tests/unit/test_run_services.py`) and ran `python -m pytest tests/unit/test_dataset_recipe.py tests/unit/test_run_request.py tests/unit/test_run_result.py tests/unit/test_run_context.py tests/unit/test_run_services.py`; 25 tests passed.

## Surprises & Discoveries

- Observation: `RunRequest.canRun()` validates recipe integrity, ticker shape, DTO type, datasource paths, and the `min_age_days` cooldown before dispatching work, meaning a single invalid field blocks Bronze ingestion silently (except for the `error` string). Evidence: each branch sets `self.error` and returns False if conditions fail.
- Observation: `RunResult` beats on parsing responses (CSV vs JSON), guarding empty payloads via `_boundary_date`, hashing payloads, and gating promotion both for Bronze (`is_valid_bronze`) and Silver (`canPromoteToSilver`), so data that fails to parse or lacks timing metadata is rejected before promotion. Evidence: `_hash`, `_boundary_date`, and the acceptance gate implement the contracts.
- Observation: `RunContext` tracks counts for bronze/silver successes/failures and derives statuses through `resolve_status`, making it the aggregate root for telemetry around atomic runs. Evidence: `result_bronze_pass`, `result_bronze_error`, and `resolve_status` mutate counters, while `elapsed_seconds` formats run durations.
- Observation: Services such as `ChunkEngine`, `DedupeEngine`, and `OrchestrationTickerChunkService` depend only on inputs and configuration constants; they do not create circular dependencies, which matches the DDD requirement that higher-level services orchestrate stateless helpers. Evidence: these services import only primitives (pandas, duckdb, enumerations) and operate on DTO slices without referencing higher layers.
- Observation: The new pytest suite demonstrates the invariants directly (RunRequest gating, RunResult Bronze/Silver gates, RunContext counters/status, and service chunk/dedupe/orchestration behavior) and currently reports 25 passing tests once dependencies (pytest, duckdb, requests) were installed. Evidence: `python -m pytest tests/unit/test_dataset_recipe.py tests/unit/test_run_request.py tests/unit/test_run_result.py tests/unit/test_run_context.py tests/unit/test_run_services.py`.

## Decision Log

- Decision: Treat the DTOs (`DatasetRecipe`, `RunRequest`, `RunResult`, `RunDataDatesDTO`, `RunContext`) as *value objects* whose behaviors enforce invariants (validation gates, filename builders, counter increments) rather than aggregates that mutate external state. Rationale: they only hold request or run-summary metadata and log invariants via `error`/counter updates; tests should assert these invariants without expecting side effects. Date/Author: 2026-01-27 / Codex.
- Decision: Test the service helpers as stateless utilities that merely segment or dedupe datasets before orchestration steps run; focus on their return values (chunks, deduped frames, chunk labels) instead of internal state. Rationale: chunking and deduplication feed the run aggregator, so proving their behavior ensures orchestrations see correct inputs. Date/Author: 2026-01-27 / Codex.
- Decision: Re-run the explicit pytest suite (`python -m pytest tests/unit/test_dataset_recipe.py tests/unit/test_run_request.py tests/unit/test_run_result.py tests/unit/test_run_context.py tests/unit/test_run_services.py`) before modifying the run layer again so the recorded observations and test names remain fresh. Rationale: the suite encapsulates the guardrails captured above and serves as the executable validation step. Date/Author: 2026-01-27 / Codex.

## Outcomes & Retrospective

- After applying this plan, anyone can point to the recorded observations and the pytest artifacts (`tests/unit/test_dataset_recipe.py`, `tests/unit/test_run_request.py`, `tests/unit/test_run_result.py`, `tests/unit/test_run_context.py`, `tests/unit/test_run_services.py`) to prove the run layer obeys the DDD checklist before modifying production code; the command `python -m pytest tests/unit/test_dataset_recipe.py tests/unit/test_run_request.py tests/unit/test_run_result.py tests/unit/test_run_context.py tests/unit/test_run_services.py` now passes 25 tests following the dependency installs.
- Pending work: maintain this pytest suite and rerun it whenever the run layer changes; record any new failures or invariants discovered here so future reviewers can rerun the same command and see updated Surprises/Decisions.

## Context and Orientation

`src/data_layer/run` houses the ingestion orchestration path. The DTOs (`DatasetRecipe`, `RunRequest`, `RunResult`, `RunDataDatesDTO`, `RunContext`) derive from `BronzeToSilverDTO` and rely on shared constants in `settings` (domains, data sources, datasets, cadences, days of week, placeholders, `DATA_SOURCES_CONFIG`). Services (`ChunkEngine`, `DedupeEngine`, `OrchestrationTickerChunkService`) orchestrate DTO batches without referencing higher layers. This plan enforces the DDD checklist by documenting how each class fulfills aggregate boundaries (RunContext is the aggregate root; others are value objects), invariants (validation logic, Bronze/Silver gates), context map usage (all settings come from `settings.py`), dependency direction (only downward imports), and entity/value-object identification (value objects, aggregator). Good Python Practices—explicit typing, docstrings, context-managed resources, and clear naming—are noted as we inspect each class.

## Plan of Work

1. For each DTO (recipe, request, result, context, data dates, result mapper) review its methods and note how they satisfy each DDD item: aggregate ownership, invariants, and entity/value-object status; document any missing comments under Surprises & Discoveries.
2. For the service helpers, inspect their chunking/deduping/orchestration flows to confirm they depend only on lower-level utilities and do not break the context map; note any implication for tests or instrumentation.
3. Translate those findings into pytest targets under `tests/unit` (e.g., invalid run request parameters, bronze gate behavior, RunContext counter updates, chunk strategy outputs, dedupe filtering). The tests should fail if invariants break and pass once alignments are confirmed.
4. Update this ExecPlan as progress happens: check off Progress items, append new Surprises/Decisions if tests reveal more, and summarize outcomes once tests finish.

## Concrete Steps

1. `cd c:\sb\SBFoundation` and open every file under `src/data_layer/run` to verify the methods listed above, paying particular attention to `RunRequest.canRun`, `RunResult.is_valid_bronze`, `RunContext` counter helpers, `ChunkEngine.chunk`, `DedupeEngine.dedupe_against_table`, and `OrchestrationTickerChunkService.process`.
2. Record each finding in the ExecPlan's Surprises & Discoveries section and identify where standard comments would clarify responsibilities or invariants (e.g., `RunRequest.msg` describing Bronze filenames).
3. Create the pytest modules `tests/unit/test_dataset_recipe.py`, `tests/unit/test_run_request.py`, `tests/unit/test_run_result.py`, `tests/unit/test_run_context.py`, and `tests/unit/test_run_services.py` to cover each observed guardrail, including invalid inputs and service outputs.
4. Run `python -m pytest tests/unit/test_dataset_recipe.py tests/unit/test_run_request.py tests/unit/test_run_result.py tests/unit/test_run_context.py tests/unit/test_run_services.py`, and revisit this ExecPlan when new issues or invariants appear so the living sections stay accurate.

## Validation and Acceptance

Run `python -m pytest tests/unit/test_dataset_recipe.py tests/unit/test_run_request.py tests/unit/test_run_result.py tests/unit/test_run_context.py tests/unit/test_run_services.py` from `c:\sb\SBFoundation`. Acceptance criteria: invalid run requests report the expected `error`, `RunResult.is_valid_bronze` enforces the Bronze contract, `RunContext` counters reflect passes/fails and `resolve_status()` returns success/partial/failure correctly, and service helpers produce the expected chunk/dedup outputs for sample DataFrames. Log the passing tests and any failures back into this ExecPlan.

## Idempotence and Recovery

All steps are additive and repeatable: rerun the same pytest command after resetting the repository to confirm invariants, and the ExecPlan can be reused as long as each revision records its date/timestamp. If a test fails mid-work, rerun only the failed module rather than the entire suite.

## Artifacts and Notes

- Evidence: The ExecPlan now lives at `docs/prompts/run_layer_review_plan.md`, and the pytest modules plus the passing `python -m pytest tests/unit/test_dataset_recipe.py tests/unit/test_run_request.py tests/unit/test_run_result.py tests/unit/test_run_context.py tests/unit/test_run_services.py` command form the artifact trail for this review.
- Note: This plan was created in response to the user’s request to review `/src/run` and document the findings/tests for that directory; rerun the listed pytest command after any further run-layer edits and stale the living sections accordingly.

## Interfaces and Dependencies

Review the following entry points and contracts:

- `src/data_layer/run/dtos/dataset_recipe.py`: domain/source/dataset metadata, validation, placeholder substitution, API-key injection, file ID creation.
- `src/data_layer/run/dtos/run_request.py`: `canRun()`, Bronze filename builders, DTO typing, `from_recipe` factory, and DTO persistence helpers.
- `src/data_layer/run/dtos/run_result.py`: HTTP response parsing, Bronze/Silver gates, `first/last date` helpers, and `to_dict()` mapping.
- `src/data_layer/run/dtos/run_context.py`: in-flight counters, bronze/silver/gold bookkeeping, elapsed time calculations, and status resolution.
- `src/data_layer/run/dtos/run_data_dates_dto.py`: simple DTO for controlling `to_date` metadata.
- `src/data_layer/run/dtos/result_mapper.py`: serialization helpers converting `RunResult` to storage payloads.
- `src/data_layer/run/services/chunk_engine.py`: chunking strategy for pandas DataFrames.
- `src/data_layer/run/services/dedupe_engine.py`: deduplication via DuckDB SQL filters.
- `src/data_layer/run/services/orchestration_ticker_chunk_service.py`: chunk-based orchestration with promotion hooks and logging.

Tests should import the constants, DTOs, and services above, mocking configuration when needed (e.g., `DATA_SOURCES_CONFIG`, placeholders) to prove the invariants in isolation.
