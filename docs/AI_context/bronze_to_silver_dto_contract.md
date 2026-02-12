# Bronze → Silver DTO Contract & Generation Prompt
*(DatasetRecipe-driven, Strawberry project)*

---

## 1) Purpose

### Goal
Provide a **deterministic, repeatable contract** that allows ChatGPT to generate
**Silver DTO classes** given:

1. A **DatasetRecipe** definition (uploaded as part of the prompt), and
2. A **payload description** (example JSON, field table, or vendor docs).

The generated DTOs must integrate **without modification** into the existing
`RunProvider` ingestion pipeline.

### Non-goals
- No schema versioning until the first breaking change
- No merging of multiple endpoints into a single DTO
- No ingestion-time logic inside DTOs

---

## 2) Authoritative Inputs

### 2.1 DatasetRecipe (required)
The DatasetRecipe instance is the **source of truth** for dataset identity.

Relevant fields:
- `domain`
- `source`
- `dataset`
- `data_source_path`
- `date_key` (optional)
- `cadence_mode`
- `min_age_days`
- `is_ticker_based`
- `help_url`
- `discrimnator` (optional)

**Rule:**
The Silver dataset name comes directly from `DatasetRecipe.dataset`.

---

### 2.2 Payload description (required)
One of:
- Example JSON payload (preferred)
- Field list table
- Vendor documentation excerpt

---

## 3) DTO Scope Rules

- **One endpoint → one DTO**
- Exactly one DTO class is generated per DatasetRecipe
- DTO class name convention:
```
<DatasetNamePascalCase>DTO
```
(or follow an existing naming convention already used in the repo)

---

## 4) Identity, Keys, and Dedupe

### 4.1 Identity rule
- Prefer `ticker` when available
- If `ticker` is `None`, rely on `DatasetRecipe.discrimnator`
- If both are missing, use `"_none_"`

### 4.2 Required DTO key columns
All Silver DTOs must define `KEY_COLS`:

```python
KEY_COLS = ["ticker"]
```

**Exception:** datasets with a natural composite key (e.g., economics indicators) should override `KEY_COLS` to the appropriate columns (e.g., `"name"`, `"date"`).

### 4.3 Ticker handling

* `ticker` is passed in by the ingestion loop
* DTOs **must not** fetch or compute ticker themselves
* Discriminator-based datasets must set `is_ticker_based=False` in the recipe

---

## 5) As-of Semantics & key_date

### 5.1 Ingestion dates (important)

DTOs **do not compute ingestion dates**.

Incremental and cadence logic is handled externally by:

* `RunProvider`
* `RunDataDatesDTO`
* Bronze manifests

DTOs remain **pure row mappers**.

### 5.2 key_date rule

Each DTO must expose a `key_date` property:

* If the endpoint provides a meaningful vendor date field:

  * Parse and return that date
* Otherwise (snapshot-style endpoints):

  * Return `date.min`

This supports ordering and partitioning without embedding ingestion state.

---

## 6) Naming Rules (Payload → DTO → Silver)

### 6.1 DTO attribute naming

* DTO attributes **must be `snake_case`**

Examples:

* `exchangeFullName` → `exchange_full_name`
* `fullTimeEmployees` → `full_time_employees`

### 6.2 Silver output naming

* `to_dict()` output keys **must be snake_case**
* Output keys typically match DTO attribute names

---

## 7) Typing & Default Behavior

### 7.1 Base defaults (do not change)

Use the existing helper behavior from `BronzeToSilverDTO`:

* Missing strings → `""`
* Missing booleans → `False`
* Numeric casts:

  * Best-effort
  * Failures → `None`

### 7.2 Dates

* Vendor date fields are typically stored as **ISO 8601 strings** (e.g., `"2025-03-31"`).
* DTOs may convert to `date` objects in `key_date` or `from_series_row`.
* `to_dict()` should emit ISO 8601 strings (use `BronzeToSilverDTO.to_iso8601`).

### 7.3 Numbers

* Store raw floats/ints
* No rounding rules applied in DTOs

---

## 8) Field Mapping Table (Required)

Every DTO specification must include an explicit mapping table:

| payload_key | dto_field (snake_case) | output_key (snake_case) | type | nullable | default | notes |
| ----------- | ---------------------- | ----------------------- | ---- | -------- | ------- | ----- |

Rules:

* Renames **must be explicit**
* `output_key` is usually the same as `dto_field`
* Payload casing may vary (camelCase, snake_case, etc.)

---

## 9) Serialization Rules

### 9.1 `to_dict()`

* Returns JSON-serializable primitives only
* Keys are snake_case
* Vendor date strings remain unchanged unless normalized to ISO 8601
* `ticker` must always be included

---

## 10) Bronze → Silver Promotion Assumptions

A Bronze row is promotable when:

* HTTP response is successful
* Payload content exists (unless endpoint allows empty payloads)
* Each list element (if payload is a list) maps to one DTO row

Promotion logic itself lives outside the DTO.

---

## 11) Required DTO Factory Signature

DTOs **must** implement:

```python
@classmethod
def from_row(cls, row: Mapping[str, Any], ticker: str | None) -> Self
```

This must match the ingestion call site exactly.

---

## 12) What ChatGPT Should Generate

When invoked with this contract, ChatGPT should output:

1. **Field mapping table** (required)
2. **Complete Python DTO file** (required)
3. Optional test fixture:

   * sample payload row
   * expected `to_dict()` output

---

# Prompt Template: Generate Silver DTO from DatasetRecipe + Payload

## Role

You are a code generator for the Strawberry project.

You MUST strictly follow:

* this Bronze → Silver DTO Contract
* the provided `BronzeToSilverDTO` base class
* the ingestion behavior implied by `RunProvider`

Do NOT invent lifecycle, ingestion, or persistence logic.

---

## Inputs (attached to this prompt)

1. **Bronze → Silver DTO Contract** `bronze_to_silver_dto_contract_and_prompt.md`
2. **Base DTO class**  `bronze_to_silver_dto.py`
3. **DatasetRecipe / recipe set** `dataset_recipes.py`
4. **Payload description** (see below)

---

## Target recipe (authoritative)

* Recipe-set class: `FmpFundamentalsRunRecipies`
* Recipe `dataset`: `<DATASET_NAME>`

Use `DatasetRecipe.dataset` as the dataset identity.

---

## Payload description

```json
<PASTE_EXAMPLE_PAYLOAD_HERE>
```

---

## Hard constraints (DO NOT VIOLATE)

* One endpoint → one DTO
* DTOs are pure row mappers
* Factory signature:

  ```python
  from_row(row, ticker)
  ```
* Include `ticker` and define `KEY_COLS`
* DTO attributes and output keys are snake_case
* Vendor dates remain ISO 8601 strings (normalize if needed)
* Use existing base defaults (`""`, `False`, `None`)
* `key_date` derived from vendor date or `date.min`

---

## Required output

### 1) Mapping table

Provide a complete mapping table as defined above.

### 2) Python DTO file

Provide a complete DTO file:

* `<dataset_snake_case>_dto.py`
* Extends `BronzeToSilverDTO`
* Includes:

  * dataclass definition
  * `KEY_COLS`
  * `from_row(row, ticker)`
  * `to_dict()`
  * `key_date` property

---

## Project conventions

* Python ≥ 3.11
* Use built-in generics (`list[...]`, `dict[...]`)
* Be resilient to missing or malformed payload fields
* Do not change base-class behavior
