# ExecPlan: Symbol→Ticker Column Rename + Period Query Param Fix

**Version**: 1.0
**Created**: 2026-02-19
**Status**: Complete

---

## Purpose / Big Picture

Two separate but related fixes to improve data integrity and API correctness in the fundamentals and company domains.

**Feature 1 — Symbol→Ticker**: Several Silver tables contain a redundant `symbol` column that duplicates `ticker`. This is a leftover from the Bronze→Silver mapping where the API response field `"symbol"` was mapped both to the canonical `ticker` field and retained as a literal `symbol` field. The fix removes the duplicate `symbol` field from affected DTOs, drops the column from affected Silver tables via migration, and cleans up the keymap `dto_schema.columns` entries accordingly.

**Feature 2 — Period Query Param**: The FMP API accepts `period=annual` or `period=quarter` as request parameters. `annual` returns rows where the response `period` field is `"FY"`; `quarter` returns rows where `period` is `"Q1"`, `"Q2"`, `"Q3"`, or `"Q4"`. The keymap currently sends `period: FY` (not the correct `period: annual`) for the annual variant of 6 financial statement datasets. Additionally, the current `key_cols: [ticker, date]` for these tables is insufficient — since the fiscal year-end date of Q4 often equals the FY annual date for the same ticker, UPSERT on `(ticker, date)` would silently overwrite one period's data with the other. The fix corrects the query param and adds `period` to `key_cols` on all 6 affected tables.

**Bonus cleanup**: Six stale blank-discriminator keymap entries (`discriminator: ''`) for the 6 financial statement datasets have no `recipes` section and represent pre-split legacy config. These will be removed as part of this work.

---

## Progress

- [x] 1. Drop `symbol` field from 7 affected DTOs — 2026-02-19
- [x] 2. Remove `symbol` from `dto_schema.columns` in all affected keymap entries (FY, quarter, and blank-discriminator variants) — 2026-02-19
- [x] 3. Remove 6 stale blank-discriminator keymap entries — 2026-02-19
- [x] 4. Fix `period: FY` → `period: annual` in keymap query_vars for 6 FY-discriminator recipes — 2026-02-19
- [x] 5. Add `period` to `key_cols` for 6 financial statement tables (both FY and quarter discriminators) — 2026-02-19
- [x] 6. Create DB migration to DROP `symbol` column from 7 Silver tables — 2026-02-19
- [x] 7. Update `README.md` — 2026-02-19
- [x] 8. Update `docs/domain_datasets_reference.md` — 2026-02-19
- [x] 9. 310 unit tests pass; DTO output verified — 2026-02-19

---

## Surprises & Discoveries

- The `symbol` field in `query_vars` (e.g., `symbol: __ticker__`) is the **FMP API request parameter name** — not an internal field. It means "send `?symbol=<ticker>` to FMP." This must NOT be changed; it is correct.
- All 6 financial statement tables have stale `discriminator: ''` entries in the keymap at the bottom of the file (lines ~6607–7800). These have no `recipes` and are unreachable by the ingestion engine. They appear to be leftover from before the FY/quarter split was introduced.
- `BronzeToSilverDTO.build_from_row()` uses `f.metadata.get("api", f.name)` to look up the source key. Because both `ticker` and `symbol` declare `metadata={"api": "symbol"}`, the `symbol` field receives the same value as `ticker` on every row. Removing the `symbol` dataclass field entirely eliminates the redundancy.
- `KEY_COLS` on the DTO class (`KEY_COLS = ["ticker"]`) is not the same as `key_cols` in the keymap. The keymap `key_cols` is what the `SilverService` uses for UPSERT. The DTO's `KEY_COLS` attribute is currently unused by the ingestion engine (it may be used for testing or documentation). Both will be updated for consistency.
- The `company_peers_dto.py` has a field `peer: str = field(metadata={"api": "symbol"})` — this uses the FMP API field name `symbol` to populate a column named `peer` in Silver. This is semantically correct (a peer's ticker symbol becomes the `peer` field) and should NOT be changed.

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-02-19 | Remove `symbol` DTO field entirely (not rename) | The field is an exact duplicate of `ticker`; keeping it under any name adds confusion |
| 2026-02-19 | Change `period: FY` → `period: annual` in query_vars | "annual" is the documented FMP API request parameter; "FY" is a response value |
| 2026-02-19 | Add `period` to `key_cols` for all 6 statement tables | FY annual date == Q4 quarterly date for same company; `(ticker, date)` alone causes silent UPSERT collisions |
| 2026-02-19 | Remove blank-discriminator stale entries | These entries have no `recipes` and cannot be executed; they are pre-split legacy config that adds confusion and still reference the stale `symbol` column |
| 2026-02-19 | Do NOT change `symbol: __ticker__` in `query_vars` | This is the FMP API query parameter name, not an internal column name |
| 2026-02-19 | Do NOT change `company_peers_dto.py` | `peer` is the correct Silver column name for a peer ticker; using `metadata={"api": "symbol"}` is correct |

---

## Outcomes & Retrospective

*(To be completed after implementation)*

---

## Context and Orientation

### Key Files

| File | Purpose |
|---|---|
| `config/dataset_keymap.yaml` | Authoritative dataset config: query_vars, key_cols, dto_schema.columns |
| `src/sbfoundation/dtos/fundamentals/income_statement_dto.py` | DTO with redundant `symbol` field |
| `src/sbfoundation/dtos/fundamentals/balance_sheet_statement_dto.py` | DTO with redundant `symbol` field |
| `src/sbfoundation/dtos/fundamentals/cashflow_statement_dto.py` | DTO with redundant `symbol` field |
| `src/sbfoundation/dtos/fundamentals/income_statement_growth_dto.py` | DTO with redundant `symbol` field |
| `src/sbfoundation/dtos/fundamentals/balance_sheet_statement_growth_dto.py` | DTO with redundant `symbol` field |
| `src/sbfoundation/dtos/fundamentals/cashflow_statement_growth_dto.py` | DTO with redundant `symbol` field |
| `src/sbfoundation/dtos/company/company_delisted_dto.py` | DTO with redundant `symbol` field |
| `db/migrations/` | DuckDB migration SQL files |
| `docs/domain_datasets_reference.md` | Domain reference documentation |
| `README.md` | Project documentation |

### Affected Silver Tables

| Silver Table | Symbol Column to Drop | Period Added to Key |
|---|---|---|
| `silver.fmp_income_statement` | ✅ | ✅ |
| `silver.fmp_balance_sheet_statement` | ✅ | ✅ |
| `silver.fmp_cashflow_statement` | ✅ | ✅ |
| `silver.fmp_income_statement_growth` | ✅ | ✅ |
| `silver.fmp_balance_sheet_statement_growth` | ✅ | ✅ |
| `silver.fmp_cashflow_statement_growth` | ✅ | ✅ |
| `silver.fmp_company_delisted` | ✅ | — |

### Current State of Affected Keymap Entries

Each of the 6 financial statement datasets has **three** keymap entries:
1. `discriminator: FY` — has recipes with `period: FY` ← incorrect, should be `period: annual`
2. `discriminator: quarter` — has recipes with `period: quarter` ← correct
3. `discriminator: ''` — no recipes, stale, to be removed

The `company_delisted` dataset has one entry with no `symbol` issue in query_vars (only in dto_schema.columns).

---

## Plan of Work

### Step A — DTO Changes (7 files)

For each of the 7 affected DTOs, remove the `symbol` dataclass field entirely. The `ticker` field already reads from `metadata={"api": "symbol"}` and is the canonical identifier.

**Pattern to remove from each DTO:**
```python
symbol: str = field(default="", metadata={"api": "symbol"})
```

Files:
1. `src/sbfoundation/dtos/fundamentals/income_statement_dto.py` — remove line with `symbol: str = field(default="", metadata={"api": "symbol"})`
2. `src/sbfoundation/dtos/fundamentals/balance_sheet_statement_dto.py` — same
3. `src/sbfoundation/dtos/fundamentals/cashflow_statement_dto.py` — same
4. `src/sbfoundation/dtos/fundamentals/income_statement_growth_dto.py` — same
5. `src/sbfoundation/dtos/fundamentals/balance_sheet_statement_growth_dto.py` — same
6. `src/sbfoundation/dtos/fundamentals/cashflow_statement_growth_dto.py` — same
7. `src/sbfoundation/dtos/company/company_delisted_dto.py` — same

### Step B — Keymap: Remove `symbol` from dto_schema.columns

For all keymap entries belonging to the 7 affected datasets, remove:
```yaml
- name: symbol
  type: str
  nullable: false
```
from the `dto_schema.columns` list.

Affected keymap entries (by dataset + discriminator):
- `income-statement` × {FY, quarter, ''}
- `balance-sheet-statement` × {FY, quarter, ''}
- `cashflow-statement` × {FY, quarter, ''}
- `income-statement-growth` × {FY, quarter, ''}
- `balance-sheet-statement-growth` × {FY, quarter, ''}
- `cashflow-statement-growth` × {FY, quarter, ''}
- `company-delisted` × {''} (one entry, no discriminator variants)

### Step C — Keymap: Remove Stale Blank-Discriminator Entries

Remove the entire keymap block (from `- domain: fundamentals` to the end of its `dto_schema.columns`) for:
- `income-statement` with `discriminator: ''` (around line 6607)
- `balance-sheet-statement` with `discriminator: ''` (around line 6741)
- `cashflow-statement` with `discriminator: ''` (around line 6938)
- `income-statement-growth` with `discriminator: ''` (around line 7459)
- `balance-sheet-statement-growth` with `discriminator: ''` (around line 7579)
- `cashflow-statement-growth` with `discriminator: ''` (around line 7764)

### Step D — Keymap: Fix Period Query Param

For each of the 6 FY-discriminator recipe entries, change:
```yaml
period: FY
```
to:
```yaml
period: annual
```

Affected entries (dataset + discriminator:FY):
1. `income-statement` / `discriminator: FY` — around line 853
2. `balance-sheet-statement` / `discriminator: FY` — around line 1159
3. `cashflow-statement` / `discriminator: FY` — around line 1591
4. `income-statement-growth` / `discriminator: FY` — around line 2793
5. `balance-sheet-statement-growth` / `discriminator: FY` — around line 3069
6. `cashflow-statement-growth` / `discriminator: FY` — around line 3477

### Step E — Keymap: Add `period` to key_cols

For all 12 entries (6 datasets × 2 discriminators FY and quarter), change:
```yaml
key_cols:
- ticker
- date
```
to:
```yaml
key_cols:
- ticker
- date
- period
```

### Step F — DB Migration

Create `db/migrations/20260219_004_symbol_column_and_period_key_fixes.sql`:

```sql
-- Feature 1: Drop redundant symbol column from Silver tables
-- These columns duplicated the ticker column (both mapped from the "symbol" API field)

ALTER TABLE silver.fmp_income_statement DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_balance_sheet_statement DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_cashflow_statement DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_income_statement_growth DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_balance_sheet_statement_growth DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_cashflow_statement_growth DROP COLUMN IF EXISTS symbol;
ALTER TABLE silver.fmp_company_delisted DROP COLUMN IF EXISTS symbol;

-- Feature 2: No DDL change needed for key_cols — UPSERT keys are determined by
-- dataset_keymap.yaml at runtime. Adding period to key_cols in the YAML is sufficient.
-- NOTE: Existing Silver rows for fmp_income_statement, fmp_balance_sheet_statement,
-- fmp_cashflow_statement and their growth counterparts may contain merged annual+quarterly
-- data where Q4 date equals FY date for the same ticker. A full re-ingestion is recommended
-- after this fix to ensure correct period separation.
```

### Step G — Documentation Updates

**README.md**: Update any table or section that references `symbol` as a column in these Silver tables. Replace with `ticker` or remove entirely.

**docs/domain_datasets_reference.md**: Update column listings for the 7 affected datasets to remove `symbol`. Update the period query note for the 6 financial statement tables to document that `period=annual` returns `period=FY` rows and `period=quarter` returns `Q1–Q4` rows.

---

## Concrete Steps

```bash
# 1. Edit the 7 DTO files to remove the symbol field
# (use Edit tool for each)

# 2. Edit config/dataset_keymap.yaml:
#    a. Remove symbol from dto_schema.columns (7 datasets × their entries)
#    b. Remove 6 stale blank-discriminator entries
#    c. Change period: FY → period: annual in 6 FY recipe entries
#    d. Add period to key_cols in 12 entries

# 3. Create migration file
# db/migrations/20260219_004_symbol_column_and_period_key_fixes.sql

# 4. Update docs

# 5. Validate
poetry run mypy src/
poetry run flake8 src/
poetry run pytest tests/unit/ -v
poetry run pytest tests/e2e/ -v
```

---

## Validation and Acceptance

1. **mypy passes** with no new errors on the 7 modified DTO files
2. **flake8 passes** on all modified files
3. **Unit tests pass**: `tests/unit/` — especially any tests covering DTO `from_row` / `to_dict` for the affected DTOs
4. **`symbol` column absent from `to_dict()` output** for all 7 DTOs
5. **`ticker` column present and correct** in `to_dict()` output for all 7 DTOs
6. **keymap loads without error**: `DatasetService` should parse the updated YAML without validation failures
7. **Period fix**: After ingestion, `silver.fmp_income_statement` should contain rows with `period IN ('FY', 'Q1', 'Q2', 'Q3', 'Q4')` and `(ticker, date, period)` should be unique
8. **No duplicate rows** after re-ingestion: re-running should be idempotent with the new `(ticker, date, period)` key

---

## Idempotence and Recovery

- All DTO changes are backward-compatible with existing Bronze JSON (the `symbol` field was always a duplicate of `ticker`; removing it does not affect ingestion of new or replayed Bronze files)
- The DB migration uses `DROP COLUMN IF EXISTS` — safe to run multiple times
- The keymap changes are atomic (single-file edit); the prior state is recoverable via git
- A re-ingestion of fundamentals data is recommended after deployment to rebuild Silver rows with the correct `(ticker, date, period)` key

---

## Interfaces and Dependencies

- `BronzeToSilverDTO.build_from_row()` — uses `f.metadata.get("api", f.name)` for field mapping; removing the `symbol` dataclass field removes it from Silver output automatically
- `BronzeToSilverDTO.build_to_dict()` — iterates `fields(self)` to produce the dict; removing `symbol` from the dataclass removes it from Silver output
- `SilverService` — reads `key_cols` from the keymap at runtime for UPSERT; no code change required
- DuckDB `ALTER TABLE ... DROP COLUMN IF EXISTS` — supported in DuckDB ≥ 0.8

---

## Artifacts and Notes

### DTOs With `symbol` Field (to be removed)

| DTO File | Line | Field Definition |
|---|---|---|
| `income_statement_dto.py` | 28 | `symbol: str = field(default="", metadata={"api": "symbol"})` |
| `balance_sheet_statement_dto.py` | ~28 | `symbol: str = field(default="", metadata={"api": "symbol"})` |
| `cashflow_statement_dto.py` | ~28 | `symbol: str = field(default="", metadata={"api": "symbol"})` |
| `income_statement_growth_dto.py` | ~27 | `symbol: str = field(default="", metadata={"api": "symbol"})` |
| `balance_sheet_statement_growth_dto.py` | 27 | `symbol: str = field(default="", metadata={"api": "symbol"})` |
| `cashflow_statement_growth_dto.py` | ~27 | `symbol: str = field(default="", metadata={"api": "symbol"})` |
| `company_delisted_dto.py` | 21 | `symbol: str = field(default="", metadata={"api": "symbol"})` |

### Keymap Period Fix Summary

| Dataset | Discriminator | Current `period` query_var | Corrected value |
|---|---|---|---|
| income-statement | FY | `FY` | `annual` |
| balance-sheet-statement | FY | `FY` | `annual` |
| cashflow-statement | FY | `FY` | `annual` |
| income-statement-growth | FY | `FY` | `annual` |
| balance-sheet-statement-growth | FY | `FY` | `annual` |
| cashflow-statement-growth | FY | `FY` | `annual` |
| (all above) | quarter | `quarter` | *(unchanged — correct)* |

### Keymap key_cols Summary

| Dataset | Current key_cols | New key_cols |
|---|---|---|
| income-statement (FY + quarter) | [ticker, date] | [ticker, date, period] |
| balance-sheet-statement (FY + quarter) | [ticker, date] | [ticker, date, period] |
| cashflow-statement (FY + quarter) | [ticker, date] | [ticker, date, period] |
| income-statement-growth (FY + quarter) | [ticker, date] | [ticker, date, period] |
| balance-sheet-statement-growth (FY + quarter) | [ticker, date] | [ticker, date, period] |
| cashflow-statement-growth (FY + quarter) | [ticker, date] | [ticker, date, period] |
