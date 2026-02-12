# AI Context: DatasetRecipe Contracts & How to Define Source Endpoint Recipes (Strawberry)

## 0) Purpose

This document teaches ChatGPT how to define **new source endpoint recipes** that are “drop-in” compatible with Strawberry’s ingestion engine.

A recipe is **not** just endpoint metadata — it must align with:

* deterministic URL construction,
* placeholder substitution,
* “base date” lookup,
* interval cadence gating,
* dataset-to-DTO mapping,
* and collision-free partitioning (via discriminator).

Primary implementations:

* `DatasetRecipe` contract
* `RunProvider` runtime semantics
* reference recipe sets: economics

---

## 1) What a DatasetRecipe is

A `DatasetRecipe` is a **declarative spec** for ingesting exactly one source endpoint into Bronze (and optionally promoting to Silver).

### 1.1 Canonical fields

`DatasetRecipe` fields and meaning:

* `domain: str`  Logical domain (e.g., company, economics).
* `source: str`  Data source identifier (e.g., `fmp`).
* `dataset: str`  Internal dataset name (stable across time).
* `data_source_path: str`  Relative API path appended to the source base URL.
* `query_vars: dict` Query parameters template; may contain placeholders.
* `date_key: str | None` Field name in each row of `content[]` representing the observation date **OR** `None` for non-timeseries endpoints.
* `cadence_mode: str` Typically `INTERVAL_CADENCE_MODE` (calendar mode exists but is not wired yet).
* `min_age_days: int` Interval gating threshold (market days). Concept: `injestion_date >= base_date + min_age_days`.
* `is_ticker_based: bool` `True` if the recipe runs across tickers, else `False`.
* `help_url: str` Link to vendor endpoint docs.
* `run_days: list[str] | None` Optional weekday allowlist (defaults to all days).
* `discrimnator: dict[str, str] | None` Optional discriminator used to build deterministic filenames/partitions and avoid collisions (especially for shared datasets like economics indicators).
* `error: str | None` Set when invalid.

> Note: the field name is spelled `discrimnator` in code (typo preserved for compatibility).

### 1.2 Validity rules

`DatasetRecipe.isValid()` requires:

* `domain` in `DOMAINS`
* `source` in `DATA_SOURCES`
* `dataset` in `DATASETS`
* `cadence_mode` in `CADENCES`
* `run_days` values in `DAYS_OF_WEEK`

**Implication for ChatGPT:** if you propose a new recipe whose domain/source/dataset aren’t in settings, you must also propose the settings updates in the same change.

---

## 2) How recipes become real API calls

`RunProvider._get_run_request()` builds the live request from the recipe:

### 2.1 URL construction (authoritative)

**URL is always:**
`url = f"{DATA_SOURCES_CONFIG[source][BASE_URL]}{recipe.data_source_path}"`

So recipes must set `data_source_path` as the vendor path fragment (no base URL).

### 2.2 Query var placeholder substitution

`RunProvider._get_query_vars()` substitutes placeholders in `recipe.query_vars`:

* values equal to `TICKER_PLACEHOLDER` → replaced with the current ticker
* values equal to `FROM_DATE_PLACEHOLDER` → replaced with computed `from_date` (see §3)
* values equal to `TO_DATE_PLACEHOLDER` → replaced with `today`
* `apikey` is injected automatically from `DATA_SOURCES_CONFIG[source][API_KEY]` env var name (if configured)
* any `None` valued params are removed

**Rule for ChatGPT:** always use placeholders for ticker/from/to where appropriate; don’t hardcode run dates.

---

## 3) Base-date, from-date, and interval cadence semantics

This is the most important “hidden” rule: Strawberry computes `from_date` from *prior ingested data*, not from the recipe.

### 3.1 How “base date” is stored

`RunProvider` uses a bronze manifest repo `data-dates` storing `RunDataDatesDTO.to_date` keyed by:

`"{domain}-{source}-{dataset}-{ticker_or_placeholder}"`

After a successful bronze write, it upserts:

* `to_date = result.last_date` (computed from payload)
* `key = f"{domain}-{source}-{dataset}-{ticker}"`

### 3.2 How `from_date` is computed

When building a request, Strawberry looks up that key:

* if found, `from_date = rd.to_date`
* else `from_date = universe.from_date`

So `from_date` is effectively “continue from the last ingested end date”.

### 3.3 What “due” means (interval mode)

Due-ness is based on the **most recent date of data ingested**, not a fixed schedule. That matches the `data-dates` strategy above.

---

## 4) Date handling rules (`date_key`) and snapshot endpoints

### 4.1 When `date_key` is provided

Timeseries endpoints should set `date_key` to the row field containing the observation date:

* economics uses `"date"`
* employees uses `"periodOfReport"`
* shares float uses `"date"`

### 4.2 When `date_key` is None (snapshot / metadata endpoints)

Examples: `profile`, `stock-peers`, `key-executives` use `None`.

**Runtime behavior:** when `date_key` is `None`, `RunResult._boundary_date()` falls back to **today’s date**, so cadence progression still advances.

---

## 5) Ticker-based vs global recipes

### 5.1 Ticker-based recipes

If `is_ticker_based=True`, `RunProvider` loops `for ticker in universe.tickers()` and builds a request per ticker.

Recipe templates should include `"symbol": TICKER_PLACEHOLDER` unless the endpoint uses a different ticker param name.

### 5.2 Global recipes

If `is_ticker_based=False`, Strawberry builds a single request with `ticker=None`.

Economics recipes are global and use query vars like `{ "name": "GDP", "from": ..., "to": ... }`.

---

## 6) Discriminators and shared datasets (Economics pattern)

You want **one dataset** for economics indicators, and rely on discriminator to avoid collisions.

**Rule:**
If many logical series share one dataset (e.g., all are `ECONOMICS_INDICATORS_DATASET`), every recipe must define `discrimnator` so downstream filenames/partitions can be deterministic.

Example:

* `{ "name": "gdp" }`
* `{ "name": "cpi" }`

(Your economics recipes already follow this.)

---

## 7) Dataset → DTO type mapping

At runtime, `RunProvider` maps recipes to DTOs via:

`dto_type = DTO_TYPES[recipe.dataset]`

**Rule for ChatGPT:** any new dataset must:

1. be added to `DATASETS`
2. have a corresponding DTO in `DTO_TYPES`
3. and the DTO must implement `from_row(row, ticker)` (your `BronzeToSilverDTO` pattern).

---

## 8) What happens when a recipe is invalid or cannot run

A failed run request does **not** crash the run. Instead:

* a `RunResult` is still created,
* an error is written via `ResultFileAdapter`,
* and `RunContext` counters are updated.

So the system is “audit-first”: failures produce artifacts and the run continues.

**Rule for ChatGPT:** recipes should be conservative and valid, but it’s acceptable for the engine to skip invalid/unrunnable requests while still producing audit output.

---

## 9) Pagination

Explicit pagination fields are **out of scope for now**. When you add endpoints needing pagination, you’ll extend the recipe contract later (page size, cursor keys, etc.).

---

## 10) How ChatGPT should output a new recipe

When asked to “add a recipe”, ChatGPT should output:

1. **The `DatasetRecipe(...)` instance** with:

   * correct domain/source/dataset constants
   * correct `data_source_path`
   * correct placeholders (`TICKER_PLACEHOLDER`, `FROM_DATE_PLACEHOLDER`, `TO_DATE_PLACEHOLDER`)
   * `help_url`
   * and `discrimnator` if the dataset is shared

2. **Any required settings updates**:

   * `DATASETS`, `DTO_TYPES`, and optionally `DOMAINS` / `DATA_SOURCES` if new

3. **A one-line justification**:

   * cadence + min_age_days rationale
   * and whether `date_key` is reliable

---

## 11) Reference recipe patterns in the codebase

### 11.1 Economics patterns

Economics recipes demonstrate:

* shared dataset (`ECONOMICS_INDICATORS_DATASET`)
* global endpoints (`is_ticker_based=False`)
* discriminator per series (`discrimnator={"name": ...}`)
* date-based timeseries (`date_key="date"`)

---

## 12) Reusable Prompt Template
You are working inside the Strawberry data platform. Your task is to generate a new DatasetRecipes class that strictly follows the existing DatasetRecipe contracts, patterns, and conventions used in this project.

CONTEXT
-------
The project uses:
- A DatasetRecipe abstraction to define API ingestion endpoints
- Placeholder-based query_vars (e.g. TICKER_PLACEHOLDER, FROM_DATE_PLACEHOLDER)
- Cadence-based execution gating (min_age_days, cadence_mode)
- A bronze → silver → gold data pipeline
- Settings-driven constants for domains, datasets, and sources

ASSUME:
- DatasetRecipe is already defined and imported
- All constants referenced must come from settings.py
- The output class should be immediately usable by the RunProvider

INPUTS
------
Class Name:
- {dataset_recipeS_CLASS_NAME}

Domain:
- {DOMAIN_CONSTANT}

Source:
- {SOURCE_CONSTANT}

API Provider:
- {API_PROVIDER_NAME}

Endpoints:
Provide one DatasetRecipe per endpoint below.

Each endpoint definition includes:
- Dataset constant
- API path
- Query parameters
- Whether it is ticker-based
- Expected date key (or None)
- Help URL

Endpoints list:
{ENDPOINT_LIST}

REQUIREMENTS
------------
For each endpoint:
1. Use the provider’s *stable* API paths where available
2. Use placeholders (e.g. TICKER_PLACEHOLDER) instead of hard-coded values
3. Include DEFAULT_LIMIT where applicable
4. Set is_ticker_based correctly
5. Use INTERVAL_CADENCE_MODE unless otherwise specified
6. Set a sensible default min_age_days (explain assumptions if needed)
7. Include help_url pointing to official documentation
8. Do NOT invent DTOs, datasets, or constants — assume they already exist
9. Return all recipes via a single `recipes()` static method

CODE STYLE
----------
- Python 3.11+
- Use @dataclass(frozen=True, slots=True)
- No business logic inside recipes
- Deterministic, declarative configuration only

OUTPUT
------
Return:
- A single Python class named {dataset_recipeS_CLASS_NAME}
- Fully formatted, production-ready code
- No explanations unless explicitly requested

OPTIONAL (only if helpful):
- Brief notes on any assumptions made (e.g. cadence choice)
