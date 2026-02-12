# Silver Layer Data Contracts

This document describes the **current Silver promotion behavior** and the **expected DTO serialization rules** in Strawberry.

---

## 1) Current Promotion Rules (as implemented)

Silver promotion happens in `RunProvider._process_run_request()` and is gated by `RunResult.canPromoteToSilverWith()`.

A Bronze payload promotes to Silver when:

1. `status_code == 200`
2. `error is None`
3. `hash` is present in memory
4. `content` is non-empty **OR** the dataset explicitly allows empty payloads

No additional schema validation, deduplication, or period normalization is enforced during promotion today.

---

## 2) DTO Serialization Rules

Silver persistence relies exclusively on DTOs that inherit from `BronzeToSilverDTO`.

**Required behaviors:**

* DTOs implement `from_row(row, ticker)` and `to_dict()`.
* `to_dict()` emits JSON-serializable primitives (`str`, `int`, `float`, `bool`) and `None`.
* Date-like values should be stored as **ISO 8601 strings** (use `BronzeToSilverDTO.to_iso8601`).
* `key_date` is derived from vendor dates or returns `date.min` for snapshots.

---

## 3) Storage Format (Silver)

Silver tables are stored as Parquet files under the Silver root folder:

```
/silver/<table_name>.parquet
```

The table name is `DatasetRecipe.dataset` and the DTO’s `to_dict()` determines the column set.

---

## 4) Key Columns & Upserts

* DTOs declare `KEY_COLS` to describe their natural keys.
* **Silver ingestion currently appends** (no dedupe) when using `ParquetRepo.add_many()`.
* Upserts are used selectively (e.g., `RunDataDatesDTO` in the bronze manifests repo) via `ParquetRepo.upsert()`.

---

## 5) Planned Enhancements (Not yet implemented)

The following ideas are valuable but are **not enforced** today:

* Period normalization for financial datasets (`annual` vs `quarterly`).
* Deduplication within or across runs.
* Quarantine logic for malformed rows.

If/when these are added, update this document to reflect the runtime behavior.
