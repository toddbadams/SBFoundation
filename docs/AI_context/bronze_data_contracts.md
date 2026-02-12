# Bronze Layer Data Contracts

The **Bronze layer** is durable, append-only storage of **exact API responses** plus enough metadata to support:

* deterministic replay
* traceability and audit
* promotion to Silver with repeatable, rule-driven logic

Bronze is the **system of record**. No business logic, interpretation, or correction is applied at this layer.

---

## 1) Bronze Record Type

### 1.1 Stored Object: `RunResult`

A **Bronze record** is a serialized `RunResult` object, persisted per ingestion request. The serialized payload includes the **RunRequest** (what we asked for) and the **response envelope** (what we got back).

`RunResult` encapsulates both the raw response payload and the minimum ingestion context required for replay, partitioning, and promotion.

---

### 1.2 `RunResult` JSON Contract (as stored)

Every stored Bronze result file MUST contain the following top-level fields:

| Field                  | Type                         | Required | Notes                                                        |
| ---------------------- | ---------------------------- | :------: | ------------------------------------------------------------ |
| `request`              | `dict`                       |    ✅    | Serialized `RunRequest` object (see table below).            |
| `now`                  | `str` (ISO8601 datetime)     |    ✅    | Service-level timestamp at processing time.                  |
| `elapsed_microseconds` | `int`                        |    ✅    | Request latency.                                             |
| `headers`              | `str \\| None`               |    ✅    | Response headers serialized as `key=value; ...`.             |
| `status_code`          | `int`                        |    ✅    | HTTP status.                                                 |
| `reason`               | `str`                        |    ✅    | HTTP reason phrase.                                          |
| `content`              | `list[dict[str, Any]]`       |    ✅    | Always a list (possibly empty).                              |
| `error`                | `str \\| None`               |    ✅    | Populated for non-200 or invalid payloads.                   |

> **Note:** `RunResult` computes `hash`, `first_date`, and `last_date` in memory for gating and replay logic, but these values are **not currently serialized** in the stored JSON.

#### 1.2.1 `RunRequest` schema (nested in `request`)

The serialized request payload MUST include:

| Field                | Type                     | Required | Notes                                                                 |
| -------------------- | ------------------------ | :------: | --------------------------------------------------------------------- |
| `ticker`             | `str`                    |    ✅    | Symbol or `_none_` for non-ticker requests.                            |
| `recipe`             | `dict`                   |    ✅    | Serialized `DatasetRecipe` (see §1.2.2).                                   |
| `injestion_date`     | `str` (ISO8601 date)     |    ✅    | Ingestion date used for cadence gating.                                |
| `run_id`             | `str`                    |    ✅    | Correlation ID shared across the run.                                  |
| `dto_type`           | `str`                    |    ✅    | Import path to Silver DTO class.                                       |
| `data_source_path`   | `str`                    |    ✅    | Vendor path fragment (no base URL).                                    |
| `url`                | `str`                    |    ✅    | Full request URL.                                                      |
| `query_vars`         | `dict[str, Any]`         |    ✅    | Query params with placeholders expanded.                               |
| `date_key`           | `str \\| None`           |    ✅    | Field name in payload rows used to derive boundary dates.              |
| `allows_empty_content` | `bool`                 |    ✅    | Whether empty payloads may promote.                                    |
| `from_date`          | `str` (ISO8601 date)     |    ✅    | Base date used to compute request range.                               |
| `to_date`            | `str` (ISO8601 date)     |    ✅    | End date for request range (usually today).                            |
| `limit`              | `int`                    |    ✅    | Requested limit (if applicable).                                       |
| `cadence_mode`        | `str`                   |    ✅    | Interval or calendar cadence mode.                                     |
| `min_age_days`       | `int`                    |    ✅    | Minimum interval days for cadence gating.                              |
| `release_day`        | `str`                    |    ✅    | Calendar-mode release day (currently optional/unused).                 |
| `error`              | `str \\| None`           |    ✅    | Request validation error (if any).                                     |

#### 1.2.2 `DatasetRecipe` schema (nested in `request.recipe`)

`DatasetRecipe` is serialized as:

| Field              | Type             | Required | Notes                                               |
| ------------------ | ---------------- | :------: | --------------------------------------------------- |
| `domain`           | `str`            |    ✅    | Logical domain (economics, fundamentals, etc.).     |
| `source`           | `str`            |    ✅    | Data provider identifier (e.g., `fmp`).             |
| `dataset`          | `str`            |    ✅    | Internal dataset identifier.                        |
| `data_source_path` | `str`            |    ✅    | Relative API path appended to base URL.             |
| `query_vars`       | `dict`           |    ✅    | Query params template (placeholders allowed).       |
| `date_key`         | `str \\| None`   |    ✅    | Field name for observation dates (or None).         |
| `cadence_mode`     | `str`            |    ✅    | Interval or calendar.                               |
| `min_age_days`     | `int`            |    ✅    | Cadence gating threshold.                           |
| `run_days`         | `list[str]`      |    ✅    | Allowed weekdays for runs (defaults to all).        |
| `is_ticker_based`  | `bool`           |    ✅    | Whether the recipe runs across tickers.             |
| `error`            | `str \\| None`   |    ✅    | Recipe validation error (if any).                   |

> `help_url` and `discrimnator` are recipe metadata used at definition time but are **not currently serialized** into `DatasetRecipe.to_dict()`.

---

## 2) Normalization Rules

* `content` MUST always be stored as `list[dict[str, Any]]`.
* JSON root handling:

  * root `dict` → invalid for Bronze storage (must be wrapped upstream)
  * empty dict → `[]`
* CSV responses MUST be parsed into `list[dict]`.
* `error` MUST be set for:

  * any non-200 response
  * empty or invalid payloads

---

## 3) Storage Format

### 3.1 File Format

* One **JSON** file per API response
* UTF-8 encoding
* Deterministic serialization recommended:

```python
json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

### 3.2 Append-Only Semantics

* One file = one response
* No overwrites
* Replay is achieved by re-processing Bronze

---

## 4) Directory & Partitioning Contract

Bronze storage paths are derived from `RunRequest` fields and follow the runtime filename logic.

```
/bronze/<domain>/<source>/<dataset>/<ticker_or_none>/<injestion_date>-<uuid>.json
```

### Definitions

* `<domain>` → `RunRequest.recipe.domain`
* `<source>` → `RunRequest.recipe.source`
* `<dataset>` → `RunRequest.recipe.dataset`
* `<ticker_or_none>` → `RunRequest.ticker` (omitted if ticker is `None`)
* `<injestion_date>` → `RunRequest.injestion_date`
* `<uuid>` → run-scoped unique filename token

---

## 5) Bronze → Silver Promotion Gate

### 5.1 Bronze Acceptance (Write-Time)

A record is valid Bronze if:

* Required transport fields exist
* `content` is a list (possibly empty)
* `now` timestamp is present

(See `RunResult.is_valid_bronze` for the current acceptance logic.)

### 5.2 Silver Eligibility (Read-Time)

Eligible for Silver only if:

* `status_code == 200`
* `error is None`
* `content` is non-empty **OR** dataset allows empty payloads

(Implemented in `RunResult.canPromoteToSilverWith`.)

---

## 6) Retention & Immutability

* Append-only
* No in-place mutation
* Bronze retained indefinitely
* Re-ingestion always produces a new file

---

## 7) DTO Boundary Contract (Unchanged, Reaffirmed)

DTOs remain the **only allowed boundary** between Bronze and Silver.

* Bronze parsing uses `from_row`
* Silver writes use `to_dict`
* Silver reads may use `from_series_row` when implemented (optional)

(See DTO section for mandatory method requirements.)

---

## 8) Ingestion Metadata Contract

### 8.1 Run summary manifest (required)

A single summary file MUST be written per run.

**Location (current convention):**

```
/bronze/manifests/summary-<RUN_ID>-<YYYY-MM-DD>.json
```

**Stored object:** `RunContext`

**Contract:** every run summary MUST contain the following fields:

| Field             | Type            | Required |
| ----------------- | --------------- | -------: |
| `run_id`          | `str`           |        ✅ |
| `started_at`      | `str` (ISO8601) |        ✅ |
| `finished_at`     | `str` (ISO8601) |        ✅ |
| `records_written` | `int`           |        ✅ |
| `records_failed`  | `int`           |        ✅ |
| `filenames`       | `list[str]`     |        ✅ |
| `failed_filenames`| `list[str]`     |        ✅ |

### 8.2 Semantics

* `records_written` = number of ingestion requests attempted.
* `records_failed` = number of requests that failed Bronze or Silver acceptance.
* `elapsed_seconds` is derived at runtime and is not serialized.

---

## 9) DTO Contracts (Bronze ↔ Silver Boundary)

Problem: if DTOs aren’t treated as a hard boundary, you end up leaking Bronze quirks into Silver (or worse—mixing storage concerns and business logic), which makes promotion brittle and replay unpredictable.

Solution: **DTOs are the only allowed contract surface between Bronze and Silver.** Every Silver table is written and read via DTOs, and every Bronze payload is parsed into DTOs via a strict set of required methods.

### 9.1 DTO Base Type

All DTOs MUST inherit from the shared `BronzeToSilverDTO` base class.

Key base properties:

| Field / Member | Type               | Purpose                                                     |
| -------------- | ------------------ | ----------------------------------------------------------- |
| `ticker`       | `str`              | Primary identifier (default `_none_`)                       |
| `KEY_COLS`     | `list[str]`        | Declares the key column(s) for the DTO                      |
| `msg`          | `str` (property)   | Logging-friendly identifier string (`"ticker=<...>"`)       |

### 9.2 Required Methods (Mandatory for every DTO)

Every DTO class MUST implement the following methods exactly (names + intent):

| Method                        | Required | Input                      | Output           | Used For                                |
| ----------------------------- | :------: | -------------------------- | ---------------- | --------------------------------------- |
| `from_row` (classmethod)      |    ✅    | `Mapping[str, Any]`        | `DTO`            | **Bronze → DTO** (parses one row)       |
| `to_dict`                     |    ✅    | (self)                     | `dict[str, Any]` | **DTO → Silver** (writes canonical row) |

Optional (when reading from Parquet or Gold transforms):

| Method              | Optional | Input        | Output | Used For                      |
| ------------------- | :------: | ------------ | ------ | ----------------------------- |
| `from_series_row`   |    ✅    | `pd.Series`  | `DTO`  | **Silver → DTO** round-trip   |

### 9.3 Bronze Parsing Rules (DTO-Level)

Bronze promotion logic MUST NOT “hand-cast” types inline. Instead:

* Bronze JSON `dict` rows MUST be converted to DTOs via `from_row`.
* `from_row` SHOULD use the base helper methods for safe parsing.
* Invalid or missing fields MUST degrade gracefully (return `None` / `""`) unless the DTO explicitly defines stricter requirements.

### 9.4 Silver Serialization Rules (DTO-Level)

* Silver write path MUST call `dto.to_dict()` for every record.
* `to_dict()` MUST emit:

  * primitives (`str`, `int`, `float`, `bool`)
  * ISO8601 strings for `date` / `datetime` (see helpers below)
  * `None` for missing values (not `"null"` strings)

---

## Final Principle

> **Bronze files are self-describing. Paths are a projection, not a dependency.**

By promoting the ingestion metadata into `RunRequest` and `DatasetRecipe`, you avoid reliance on directory parsing for lineage, replay, or refactors.
