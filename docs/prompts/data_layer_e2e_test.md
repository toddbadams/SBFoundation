# Data Layer E2E Pipeline Test Harness ExecPlan

This ExecPlan is a living document maintained under `docs/AI_context/PLANS.md`. It describes the work needed to give Strawberry a deterministic, observable Bronze → Silver → Gold end-to-end test that relies only on synthetic inputs and documents every decision so a novice can pick up the work without prior knowledge. The plan now also covers orchestrator configuration permutations controlled by `src/data_layer/orchestrator.py`'s `OrchestrationSwitches`, ensuring each stage can run in isolation and that both ticker and non-ticker recipes execute successfully.

## Purpose / Big Picture

After this change, any engineer can run a single pytest suite that
1) exercises real ingestion/promotion code paths under a fake API,
2) proves Bronze artifacts keep their contract, Silver DTOs match pandera schemas, and Gold outputs satisfy DuckDB assertions, and
3) proves ingestion behaves under happy, snapshot, and error scenarios without hitting live vendor APIs.
The harness also documents how to build new scenarios by showing the fixtures, API server shape, and validators needed to capture Bronze, Silver, and Gold invariants.

## Progress

 - [x] (2026-01-19 14:20Z) Captured the requested E2E harness plan, including fixtures, validators, scenario outlines, and OrchestrationSwitches coverage, before implementing any code.
 - [x] (2026-01-20 18:00Z) Implemented the harness, validators, and `tests/e2e/test_data_layer_promotion.py`; the suite now exercises the happy, snapshot, and error scenarios plus the orchestrator permutations mentioned in the plan.

## Surprises & Discoveries

- Observation: None yet; the plan is awaiting implementation.
  Evidence: Not run.

## Decision Log

- Decision: No implementation decisions have been made yet.
  Rationale: The work is in the planning phase.
  Date/Author: 2026-01-19 Codex

## Outcomes & Retrospective

- Not applicable until the plan is executed; will summarize what was delivered and what remains once tests and artifacts exist.

## Context and Orientation

Strawberry layers data via Bronze (vendor payloads plus metadata), Silver (DTO-conformed Parquet), and Gold (metrics/aggregations for consumers). Ingestion is orchestrated by `src/data_layer/orchestrator.py`, which uses DatasetRecipes defined under `src/data_layer/recipes` (per `docs/AI_context/recipe_contracts.md`) to fetch data for a domain/source/dataset combination, persist Bronze JSON, and build Silver/Gold outputs through DTO mappings (`docs/AI_context/bronze_to_silver_dto_contract.md`). `src/data_layer/orchestrator.py` exposes `OrchestrationSwitches`, a configuration class that runs specific stages (e.g., Bronze only, Bronze+Silver, full Bronze→Gold, ticker vs non-ticker paths). Tests must exercise these switches to verify each stage works independently and for both ticker and non-ticker recipes. Tests should reference the contracts in `docs/AI_context/bronze_data_contracts.md`, use DuckDB (per `docs/AI_context/duckdb.md`) for Gold verification, and align with the current QA stack (`pytest`, `pytest-cov`, etc.). The new harness lives alongside existing prompts in `docs/prompts`, and any code touched must remain consistent with the Bronze→Silver→Gold layering rules described in the AI context docs.

## Plan of Work

The plan consists of three major workstreams.

First, define a reusable pytest fixture (the "data-pipeline E2E harness") that creates an isolated `tmp_path` rooted workspace, overrides the Bronze/Silver/Gold base paths, and freezes `now` via `freezegun.freeze_time`. The fixture should also fix `run_id` (for example, `"test-run-001"`) and expose a tiny catalog describing the dataset(s) under test. Use a dedicated test copy of `config/dataset_keymap.yaml` that includes the requested recipes: a time-series, a snapshot, a ticker-based, a non ticker-based, and one with a non-empty discriminator. Point the orchestrator at this test map so the harness has controlled recipe metadata. The fixture is best located in `tests/conftest.py` or `tests/e2e/conftest.py`, whichever already hosts collaborative fixtures, because other tests in the suite may reuse it in the future.

Second, design a fake HTTP API that can serve deterministic payloads for happy path timeseries, snapshot, and error scenarios. Option A from the instructions is preferred: run a FastAPI app via `pytest-httpserver` or an `httpx.AsyncClient` backed by `fastapi.testclient`. The server should mirror Strawberry's recipe placeholders (`TICKER_PLACEHOLDER`, `FROM_DATE_PLACEHOLDER`, etc.) so the test exercises URL building and query substitution; returning JSON lists ensures the Bronze contract is exercised. Capture three behaviors: a normal 200 with a 3–5 row dated series, a 200 snapshot with `date_key=None`, and a 500 error (or invalid JSON) path for error containment. Validate that the querystring contains the configured API key for the test dataset so header/auth generation is exercised. Ensure the fake API can respond differently based on switches corresponding to ticker vs non-ticker recipe endpoints so the orchestrator tests can pick the relevant response templates.

Third, create layer-specific validators and the promotion scenario tests. Bronze assertions (read the Bronze JSON files under `tmp_path/bronze/...`, confirm metadata fields, status_code, url, content list structure, and derived `first_date/last_date`). Silver validators use `pandera` schemas based on the DTO under test; check column presence, types, dedupe of key columns, and the `key_date` logic (e.g., ticker + date key). Gold assertions run DuckDB SQL over the promoted Gold Parquet files, verifying row counts, non-null metrics, and expected aggregates or derived columns from the fixed input. Each scenario test (happy timeseries, snapshot, error) should drive the real `RunProvider`/`DatasetRecipe` run (via `src/data_layer/orchestrator.py`), wait for completion if necessary, then hand the stored artifacts to validators. In addition to running the full promotion path, add tests that instantiate `OrchestrationSwitches` with flags like `bronze=True, silver=False, gold=False` or `ticker_based=True/False` to confirm each stage can run on its own and that non-ticker recipes behave just as reliably. Use pytest parametrization to cover these variations while reusing the base harness fixture.

Bundle these components into an `tests/e2e/test_data_layer_promotion.py` module. Use `pytest.mark.parametrize` to capture the three scenarios and their expected responses. Optionally, embed `syrupy` snapshot assertions for the Gold Parquet content if the dataset is stable, but focus on contract-level assertions first. Document how the fake API response JSON maps to DTO columns so future maintainers can extend scenarios safely.

## Concrete Steps

1. Add a fixture (e.g., `data_pipeline_harness`) to `tests/conftest.py` or `tests/e2e/conftest.py` that:
   - writes temporary Bronze/Silver/Gold base directories under `tmp_path`.
   - patches configuration constants or environment (via monkeypatch) so the runtime reads from those directories.
   - freezes datetime with `freezegun` and returns `run_id = "test-run-001"` plus a minimal catalog entry.
   - exposes helper functions to read Bronze JSON and Silver/Gold Parquets for assertions.

2. Implement a fake service module under `tests/e2e/fake_api.py` (or inline FastAPI app in the test file) that accepts recipe placeholder paths, responds with the three payload variants, and signals errors when requested. Prefer `FastAPI` with `TestClient` so the real HTTP stack is validated; include at least one helper to obfuscate secrets in the recorded URL before asserting.

3. Create validator helpers under `tests/e2e/validators.py` that:
   - parse Bronze JSON directories, confirm required fields, and check `first_date`/`last_date`.
   - load Silver Parquet with `pandas` and validate via `pandera` schema definitions for the selected DTO.
   - run `duckdb.query` against the Gold Parquet directory to assert business invariants (row counts, metrics ranges).

4. Author `tests/e2e/test_data_layer_promotion.py` with pytest tests that:
   - use the harness fixture to configure the runtime and the fake API.
   - parameterize scenarios for the timeseries payload, snapshot payload, and error branch.
   - invoke the real `RunProvider`/`DatasetRecipe` flow in `src/data_layer/orchestrator.py` (documenting the exact function call so a novice can reproduce it).
   - call validator helpers after the run, asserting Bronze, Silver, and Gold invariants for success scenarios and asserting Bronze error handling for the error scenario.
   - include separate tests or parameterized cases that exercise `OrchestrationSwitches` permutations, such as running only Bronze, Bronze+Silver (no Gold), and toggling `ticker_based` vs `non_ticker_based` workflows, verifying the intermediate outputs and absence/presence of Silver/Gold artifacts as expected.

5. Update `requirements.txt` or `pyproject.toml` if necessary to include `fastapi`, `uvicorn`, `pytest-httpserver`, `freezegun`, `pandera`, and any test dependencies not yet pinned. Document the dependency list inside the plan and tests cite their versions.

6. Document the new harness and scenarios inside `docs/prompts/data_layer_e2e_test.md` (this file) and add references to the new tests in `docs/prompts/orchestrator_chunks.md` or other guidance docs as needed. Mention how the harness can be extended by adding more scenarios or snapshots.

## Validation and Acceptance

Run `poetry run pytest tests/e2e/test_data_layer_promotion.py` (or `python -m pytest ...` depending on the project toolchain). Expect `3 passed` (timeseries, snapshot, error) and coverage for Bronze/Silver/Gold validators. Additionally run `poetry run pytest tests/e2e/test_data_layer_promotion.py::test_data_layer_promotion[happy]` individually to confirm slow scenarios can be targeted. Gold validation must pass both pandas/pandera checks and DuckDB queries; failure indicates regression. Document the expected output snippet:

    tests/e2e/test_data_layer_promotion.py::test_data_layer_promotion[happy] PASSED [100%]
    tests/e2e/test_data_layer_promotion.py::test_data_layer_promotion[snapshot] PASSED [100%]
    tests/e2e/test_data_layer_promotion.py::test_data_layer_promotion[error] PASSED [100%]

## Execution Status

- `poetry run pytest tests/e2e/test_data_layer_promotion.py` (or `python -m pytest tests/e2e/test_data_layer_promotion.py`) successfully passes the happy timeseries, snapshot, and error scenarios; the Bronze/Silver/Gold validation helpers are green in this suite.

## Workspace lifecycle note

- Because `tests/conftest.py` makes `clean_workspace` an `autouse=True` fixture (lines 19‑35) the Bronze/Silver/Gold temp folders are deleted and recreated before each test invocation, which is why saving files during development reruns pytest and regenerates `temp/`. To limit that churn to the start of a test run, set `clean_workspace` to `scope="session"` (or move the directory creation into the existing `test_root` session fixture) and restrict per-test teardown to non-critical resources; the workspace directories then only need to be created once per session instead of on every file save while editing.

## Idempotence and Recovery

The harness uses pytest `tmp_path` and `freezegun`, so every run resets Bronze/Silver/Gold directories. Rerunning the suite simply overwrites the temp directories and reuses the fixed `run_id`. Errors during runs leave the fake API server in the test process and are cleaned up automatically when pytest finishes. If a test leaves Parquet files behind, delete the `tmp_path` directory noted in failure logs or rerun the suite; no global state is mutated.

## Artifacts and Notes

Example verification artifacts will include:

    {
        "bronze_path": ".../tmp/tmpxxx/bronze/domain/source/dataset/run_id=test-run-001/...",
        "status_code": 200,
        "url": "https://api.vendor.com/... (with secrets masked)"
    }

Gold DuckDB assertions will log SQL like:

    SELECT count(*) FROM '.../gold/domain/source/dataset/*.parquet';

and return deterministic counts such as `3`.

## Interfaces and Dependencies

The harness relies on:

- `FastAPI`/`TestClient` (or `pytest-httpserver`) to expose recipe-aligned endpoints that mirror placeholder substitution.
- `requests`/`httpx` inside `RunProvider` so the URL/headers/params go through real HTTP layers.
- `src/data_layer/orchestrator.py` and its `RunProvider.run` method (call it directly, passing the harness catalog entry).
- `pandera` schemas defined for the targeted DTO (visible in `src/data_layer/dtos`), with functions named `from_row` and `key_date`.
- `duckdb` queries run against the Gold parquet output directory (path derived from the harness fixture).
- `fastuuid`? (if run_id uses uuid). If not, the harness simply uses hard-coded `run_id`.

## Questions for Clarification

1. Which existing DatasetRecipe/dataset should we target for the initial harness so the Dry run data is meaningful yet small (e.g., time-series vs snapshot)? If multiple fit, should we start with the dataset that already has Silver/Gold builders?  
   **Answer:** create a test version of `config/dataset_keymap.yaml` scoped for these tests. Define recipes for a time-series flow, a snapshot flow, a ticker-based flow, a non ticker-based flow, and one with a non-empty discriminator so the orchestrator metadata covering both ticker/non-ticker logic and discriminator enforcement can be exercised.

2. Should the fake API simulate vendor-specific headers or auth so the test validates header-building logic, or is URL/query validation sufficient for now?  
   **Answer:** validate that the configured API key appears in the query string, thereby ensuring header/auth generation logic is verified.

3. For the orchestrator stage tests, are there preferred combinations of `OrchestrationSwitches` flags (e.g., Bronze-only, Bronze+Silver, ticker vs non-ticker) we should prioritise first, or should the harness exhaustively iterate all meaningful permutations?  
   **Answer:** cover Bronze-only, Silver-only, and Gold-only permutations for both the non-ticker recipe and the ticker recipe so each stage and recipe type is exercised separately. Use parametrized cases to reduce duplication but ensure all six combinations are represented.
