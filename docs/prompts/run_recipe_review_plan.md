# DatasetRecipe DDD Review Plan

This ExecPlan lives in `docs/prompts/dataset_recipe_review_plan.md` so the review artifacts are immediately visible under `/docs/prompts` as requested. It follows the requirements in `docs/AI_context/PLANS.md` and serves as a living guide for documenting the DDD check, recording Surprises, and defining the targeted tests for `src/data_layer/run/dtos/dataset_recipe.py`.

## Purpose / Big Picture

DatasetRecipe is the configuration object that describes how ingestion recipes execute, including their domain/source/dataset metadata and scheduling rules. This plan captures how DatasetRecipe fits into the DDD aggregate/value-object model, surfaces its invariants, and translates those invariants into concrete regression tests before any code edits are made. After following this plan, the reviewer will understand how DatasetRecipe guards Bronze ingestion and will have a repeatable test plan that proves the guards work.

## Progress

- [x] (2026-01-27 09:30Z) Recorded the intent to review `DatasetRecipe` per the DDD checklist and requirement to save the ExecPlan under `/docs/prompts`.
- [ ] Draft the Surprises & Discoveries, Decision Log, and test proposals for the DatasetRecipe review.
- [ ] Implement or update tests that prove DatasetRecipe’s invariants and placeholder expansion behave as expected.

## Surprises & Discoveries

- Observation: `DatasetRecipe.isValid()` cross-checks domain, source, dataset, cadence, and run days using the shared constants (`DOMAINS`, `DATA_SOURCES`, `DATASETS`, `CADENCES`, `DAYS_OF_WEEK`) before letting a recipe into Bronze, which means a misconfigured constant would silently reject recipes without descriptive logging.
  Evidence: each validation branch sets `self.error` before returning False.
- Observation: `get_query_vars()` performs placeholder substitution for ticker/date limits and always tries to append an API key by looking up `DATA_SOURCES_CONFIG[self.source][API_KEY]`, so broken config keys or missing environment variables could prevent API calls from authenticating.
  Evidence: code converts placeholders to actual dates/tickers and filters out None values while pulling the API key from the environment.
- Observation: `run_days` are normalized to lowercase strings and default to every day when empty or comprised of whitespace, which ensures `runs_on()` can operate with a predictable data shape even if the caller supplies variant input.
  Evidence: `__post_init__` handles str/list inputs and trims whitespace before reassigning `self.run_days`.

## Decision Log

- Decision: Treat DatasetRecipe as a value object whose identity is the recipe metadata, so all tests focus on configuration invariants rather than mutating behavior.
  Rationale: DatasetRecipe never mutates Bronze/Silver state and only describes how ingestion should behave; unit tests should verify its guards instead of its state transitions.
  Date/Author: 2026-01-27 / Codex.
- Decision: Document and test placeholder substitution and API key injection because they mediate how DatasetRecipe drives downstream API requests and are prone to subtle misconfigurations.
  Rationale: These behaviors are centralized in `get_query_vars()` and govern what actually reaches the upstream data sources.
  Date/Author: 2026-01-27 / Codex.

## Outcomes & Retrospective

- A reviewer can now cite this plan to know exactly where each DDD checklist item is satisfied for DatasetRecipe, what to log under Surprises & Discoveries, and which tests demonstrate the guardrails. The final ExecPlan that records the observations and test ideas lives here under `/docs/prompts` as mandated.
- Remaining work includes authoring the tests described below and updating the plan if the implementation reveals new invariants or dependency issues.

## Context and Orientation

`DatasetRecipe` lives in `src/data_layer/run/dtos/dataset_recipe.py` and inherits shared mapping utilities from `data_layer/dtos/bronze_to_silver_dto.py`. It is configured by the `settings` module, which defines constants such as `DOMAINS`, `DATA_SOURCES`, `DATASETS`, `CADENCES`, `DAYS_OF_WEEK`, placeholder tokens (e.g., `TICKER_PLACEHOLDER`), `DATA_SOURCES_CONFIG`, and API key names. DatasetRecipe describes how Bronze ingestion should operate (domain, source, dataset, cadence, run days, help url, etc.), so it behaves like a value object/DTO rather than an entity managing state. The plan enforces the DDD checklist: aggregate boundaries (value object guarding metadata), invariants (valid constants and normalized days), context map consistency (read from `settings`), dependency direction (depends only on `settings` and helper DTOs), and entity/value-object identification (value object). Good Python Practices emphasized include explicit typing, docstrings (method-level), resource safety (stateless getters), and consistent naming.

## Plan of Work

First, verify the DDD checklist by auditing `DatasetRecipe`: identify which shared constants it reads (context map consistency), enumerate each validation in `isValid()` (invariants), confirm that dependencies only point downward to DTO helpers and configuration (dependency direction), and note that the class keeps its configuration immutable after initialization (value-object identification). Next, revisit the `Surprises & Discoveries` section to log the observations above before editing any production code. After logging, outline the unit tests that exercise each invariant (invalid domain/source/dataset/cadence/run days, run_day normalization, placeholder substitution, API key injection), describing where they will live (`tests/unit/test_dataset_recipe.py`). Finally, define the Execution Plan for actually writing or updating those tests, making sure the tests fail before the fixes (if there are any corrections) and pass afterward, and specify how to record the results (test output, plan update).

## Concrete Steps

1. `cd c:\\sb\SBFoundation` then open `src/data_layer/run/dtos/dataset_recipe.py`; re-read the class to ensure no additional invariants exist beyond domain/source/dataset/cadence/run_days validation, placeholder handling, and API key injection. Expect to see the dataclass definition, `__post_init__`, `isValid()`, `get_query_vars()`, and simple property methods.
2. Document the findings in `docs/prompts/dataset_recipe_review_plan.md` before editing production code, confirming that each DDD checklist item is satisfied and that the Good Python Practices are accounted for. The plan should already list the observations above and note where further tests will be added.
3. Create `tests/unit/test_dataset_recipe.py` (if it does not exist) and write pytest cases that instantiate `DatasetRecipe` with invalid constants to confirm `isValid()` returns False and sets `error`, that `run_days` normalization behaves as described, that `runs_on()` responds accurately to empty and specific inputs, and that `get_query_vars()` substitutes placeholders and adds the API key when provided via `os.environ`. Run `python -m pytest tests/unit/test_dataset_recipe.py` after writing the tests; expect the new tests to fail if DatasetRecipe currently has bugs (e.g., missing config or placeholder handling) and then to pass once any necessary fixes are applied.
4. Update this ExecPlan after writing the tests: mark the progress checklist, add any new entries to Surprises or Decision Log if new insights emerge, and revise the Outcomes section to reflect the completed work. Leave an annotation at the bottom explaining that the plan was created to satisfy the request for a DatasetRecipe DDD review and ExecPlan file.

## Validation and Acceptance

Validation requires running `python -m pytest tests/unit/test_dataset_recipe.py` from `c:\\sb\SBFoundation`. Acceptance is behavior-driven: the tests should assert that invalid domain/source/dataset/cadence/run days are rejected with `self.error` set, that placeholder substitution produces the expected `from`/`to`/`ticker` results, and that the API key appears when the environment variable referenced by `DATA_SOURCES_CONFIG` is present. A passing test suite demonstrates the invariants and replacement logic that guard Bronze ingestion. Document any leftover issues in this ExecPlan if tests cannot pass immediately.

## Idempotence and Recovery

All steps add new units (tests and plan updates) and are repeatable; rerunning `python -m pytest tests/unit/test_dataset_recipe.py` after writing the tests should produce the same results provided the environment variables remain consistent. If a test needs to be re-run after resetting the repository, reapply the same commands above.

## Artifacts and Notes

- Evidence: Saving this plan under `/docs/prompts` satisfies the requirement that the ExecPlan be stored there and makes it easy to open and extend for future reviews.
- Note: Plan created in response to the user request to review `src/data_layer/run/dtos/dataset_recipe.py` and capture the findings plus tests in an ExecPlan file saved under `/docs/prompts`.

## Interfaces and Dependencies

The review focuses on `DatasetRecipe` (dataclass in `src/data_layer/run/dtos/dataset_recipe.py`) that inherits from `data_layer/dtos/bronze_to_silver_dto.py`. It depends only on the global settings defined in `settings.py`: `DOMAINS`, `DATA_SOURCES`, `DATASETS`, `CADENCES`, `DAYS_OF_WEEK`, `DATA_SOURCES_CONFIG`, and the placeholder constants (`TICKER_PLACEHOLDER`, `FROM_DATE_PLACEHOLDER`, `FROM_ONE_MONTH_AGO_PLACEHOLDER`, `TO_DATE_PLACEHOLDER`, `LIMIT_PLACEHOLDER`, `PERIOD_PLACEHOLDER`, `DEFAULT_LIMIT`, `PERIOD_ANNUAL`). Tests must import these constants to craft valid and invalid recipes, and should mock `os.environ` if needed when verifying API key injection. Tests should instantiate DatasetRecipe with both str and list `run_days` to confirm normalization and should call `get_query_vars()` with and without the optional parameters to exercise the placeholder paths.
