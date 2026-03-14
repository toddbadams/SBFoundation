# 🔴 CRITICAL FINDING: silver.instrument Table is Broken

**Date**: 2026-02-17
**Severity**: HIGH - Code is in non-functional state
**Status**: Requires immediate decision

---

## Summary

The `silver.instrument` table is **created but never populated**. All code that reads from it would return empty results or fail.

---

## Evidence

### 1. Table is Created
**File**: `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py:51-71`
```python
SILVER_INSTRUMENT_DDL = """
CREATE TABLE IF NOT EXISTS silver.instrument (
    instrument_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    ...
);
"""
```

### 2. Table is NEVER Written To
**Searched for**: INSERT, UPDATE, MERGE statements for `silver.instrument`
**Result**: **ZERO matches** (excluding ExecPlan documentation)

### 3. InstrumentPromotionService Targets gold.instrument (NOT silver.instrument!)
**File**: `src/sbfoundation/services/silver/instrument_promotion_service.py:95`
```sql
MERGE INTO gold.instrument AS target  -- ← GOLD, not SILVER!
```

### 4. promote_to_unified_instrument() is NEVER Called
**Searched for**: Calls to `promote_to_unified_instrument()`
**Result**: Method is defined but **never invoked** anywhere in the codebase

### 5. Code Tries to Read from Empty Table
**File**: `src/sbfoundation/infra/universe_repo.py`
- Line 58: `INNER JOIN silver.instrument si ON fi.ticker = si.symbol`
- Line 151: `INNER JOIN silver.instrument si ON fi.ticker = si.symbol`
- Line 217: `SELECT * FROM silver.instrument WHERE symbol = ?`

**Impact**: All these queries would return empty results or fail the join

### 6. E2E Test Expects Data (Would FAIL)
**File**: `tests/e2e/test_data_layer_promotion.py:299-301`
```python
# Check unified instrument table is populated
instrument_df = conn.execute('SELECT * FROM "silver"."instrument"').fetchdf()
expected_total = len(TestData.StockList.DATA) + len(TestData.ETFList.DATA)
assert len(instrument_df) == expected_total  # ← Would FAIL (0 != expected_total)
```

---

## Architectural Mismatch

| Component | Target Table | Purpose |
|-----------|-------------|---------|
| `duckdb_bootstrap.py` | Creates `silver.instrument` | ❌ Never used |
| `InstrumentPromotionService` | Writes to `gold.instrument` | ⚠️ Never called |
| `UniverseRepo` | Reads from `silver.instrument` | ❌ Always empty |
| `test_data_layer_promotion.py` | Expects `silver.instrument` | ❌ Would fail |

---

## Why This Happened

**Hypothesis**: The code appears to be mid-refactor:
1. Originally, `silver.instrument` was intended to be the unified instrument table
2. Someone started refactoring to move it to `gold.instrument` (per architecture guidelines)
3. They wrote `InstrumentPromotionService` to target `gold.instrument`
4. But they **never completed the refactor**:
   - Didn't remove `silver.instrument` table creation
   - Didn't update `UniverseRepo` to query `gold.instrument` or `ops.instrument_catalog`
   - Didn't wire up calls to `promote_to_unified_instrument()`
   - Didn't update the E2E test
5. Left the codebase in a broken state

---

## Impact Assessment

### Broken Functionality
1. **Universe ticker filtering** - Cannot filter by `instrument_type` or `is_active` (joins empty table)
2. **Instrument lookup** - `get_instrument(symbol)` always returns `None`
3. **E2E tests** - `test_03_instrument_discovery_flow` would fail
4. **Orchestration** - Any code path using `UniverseRepo.get_update_tickers()` with type/active filters would fail

### Still Works (Bypasses broken code)
- Querying `ops.file_ingestions` directly without instrument filtering
- Bronze ingestion
- Silver promotion of non-instrument datasets
- `UniverseRepo.get_update_tickers()` when called WITHOUT `instrument_type` or `is_active` filters (bypasses the join)

---

## Recommended Fix

Given that CLAUDE.md §1 states **"Gold layer exists in a separate downstream project"**, SBFoundation should NOT query Gold tables.

### Option 1: Create ops.instrument_catalog (RECOMMENDED)
1. Create `ops.instrument_catalog` table for operational metadata
2. Populate it during orchestration from Silver instrument list tables
3. Update `UniverseRepo` to query `ops.instrument_catalog`
4. Remove `silver.instrument` table
5. Keep `InstrumentPromotionService` as-is (Gold project can call it)

**Pros**:
- Follows architecture (ops for operational data)
- No Gold dependency
- Maintains filtering capability

**Cons**:
- Need to write population logic

### Option 2: Remove Filtering, Query ops.file_ingestions Directly
1. Remove `instrument_type` and `is_active` parameters from `UniverseRepo`
2. Query `ops.file_ingestions` directly without joins
3. Remove `silver.instrument` table

**Pros**:
- Simplest fix
- No new tables

**Cons**:
- Loses filtering capability
- Breaking API change

### Option 3: Query gold.instrument (NOT RECOMMENDED)
1. Update `UniverseRepo` to query `gold.instrument`
2. Call `InstrumentPromotionService.promote_to_unified_instrument()` during orchestration

**Pros**:
- Uses existing code

**Cons**:
- **Violates CLAUDE.md architecture** - Gold is separate project
- Creates coupling SBFoundation → Gold

---

## Decision Required

**Question for User**: Which option should I proceed with?

1. **Option 1** (Create `ops.instrument_catalog`) - Architecturally correct, requires population logic
2. **Option 2** (Remove filtering) - Simplest but loses functionality
3. **Option 3** (Query `gold.instrument`) - Violates architecture guidelines

**My Recommendation**: **Option 1** - Create `ops.instrument_catalog` and populate it from Silver instrument list tables during orchestration. This:
- Follows CLAUDE.md architecture (ops for operational metadata)
- Maintains current API (no breaking changes)
- Fixes the broken state
- Enables proper instrument filtering

---

## Next Steps (Pending Decision)

1. Get user confirmation on approach
2. Update ExecPlan with correct implementation
3. Implement the fix
4. Update tests
5. Validate E2E orchestration works

---

## Files to Review

- `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py` (creates silver.instrument)
- `src/sbfoundation/infra/universe_repo.py` (reads from silver.instrument)
- `src/sbfoundation/services/silver/instrument_promotion_service.py` (writes to gold.instrument)
- `tests/e2e/test_data_layer_promotion.py` (expects silver.instrument data)
