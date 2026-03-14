# Data Layer Corrections

**Date**: 2026-02-17
**Status**: In Progress

## Summary

Two data layer issues have been identified that violate the Bronze→Silver→Gold architecture:

### Issue 1: PE Column Type Mismatch ✓ READY TO FIX
The `pe` columns in two Silver tables are stored as `INTEGER` but should be `DOUBLE` to preserve decimal precision.

**Affected Tables**:
- `silver.fmp_market_sector_pe`
- `silver.fmp_market_industry_pe`

**Root Cause**: Bronze JSON data contains decimal values (e.g., `21.453619065173097`), but DuckDB tables were created with `INTEGER` type, causing truncation.

**Current State**:
- ✓ DTOs correctly define `pe: float | None`
- ✓ `dataset_keymap.yaml` correctly specifies `type: float | None`
- ✗ DuckDB tables have `INTEGER` type (needs migration)

**Fix Created**:
- Migration file: `db/migrations/20260217_001_fix_pe_column_types.sql`
- Migration runner: `scripts/run_migration.py`

**To Apply**:
1. Close any open DuckDB CLI connections (PID 25288 currently has lock)
2. Run: `python scripts/run_migration.py db/migrations/20260217_001_fix_pe_column_types.sql`

---

### Issue 2: silver.instrument Table Violates Architecture ⚠️ NEEDS PLANNING

The `silver.instrument` table exists in the Silver layer but violates the Bronze→Silver→Gold architecture.

**Why This Violates Architecture** (per CLAUDE.md Section 1):

Silver layer should contain:
- ✓ Clean, typed business data from Bronze
- ✓ Natural business keys only (e.g., ticker, symbol, date)
- ✓ Lineage metadata (bronze_file_id, run_id, ingested_at)
- ✗ NO surrogate keys (e.g., instrument_sk, instrument_id)
- ✗ NO operational metadata (is_active, discovered_at, last_enriched_at)

**Current silver.instrument Table** (from `duckdb_bootstrap.py:51-71`):
```sql
CREATE TABLE IF NOT EXISTS silver.instrument (
    instrument_id VARCHAR PRIMARY KEY,        -- ✗ Synthetic/surrogate key
    symbol VARCHAR NOT NULL,                   -- ✓ Natural key
    instrument_type VARCHAR NOT NULL,          -- ✓ Business attribute
    source_endpoint VARCHAR NOT NULL,          -- ? Operational metadata
    name VARCHAR,                              -- ✓ Business attribute
    exchange VARCHAR,                          -- ✓ Business attribute
    exchange_short_name VARCHAR,               -- ✓ Business attribute
    currency VARCHAR,                          -- ✓ Business attribute
    base_currency VARCHAR,                     -- ✓ Business attribute (FX)
    quote_currency VARCHAR,                    -- ✓ Business attribute (FX)
    is_active BOOLEAN DEFAULT TRUE,            -- ✗ Operational metadata
    discovered_at TIMESTAMP NOT NULL,          -- ✗ Operational metadata
    last_enriched_at TIMESTAMP,                -- ✗ Operational metadata
    bronze_file_id VARCHAR,                    -- ✓ Lineage metadata
    run_id VARCHAR,                            -- ✓ Lineage metadata
    ingested_at TIMESTAMP,                     -- ✓ Lineage metadata
    UNIQUE (symbol, instrument_type)
);
```

**Where It's Used**:
1. `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py:51-71` - Creates the table
2. `src/sbfoundation/infra/universe_repo.py:58,151,213` - Queries for filtering by type/active status
3. `src/sbfoundation/services/universe_service.py` - Wraps repo calls
4. `tests/e2e/test_data_layer_promotion.py` - E2E test

**Proper Architecture**:

| Data Type | Belongs In | Reason |
|-----------|-----------|--------|
| Instrument business attributes (symbol, name, exchange, currency) | Silver tables from Bronze (e.g., `silver.fmp_stock_list`) | Conformed vendor data |
| Surrogate keys (instrument_sk) | Gold dimensions (e.g., `gold.dim_instrument`) | Dimensional modeling |
| Operational metadata (is_active, discovered_at) | ops schema (e.g., `ops.instrument_catalog`) | Orchestration metadata |

**Recommended Fix**:

1. **Create `ops.instrument_catalog`** table for operational metadata:
   ```sql
   CREATE TABLE ops.instrument_catalog (
       symbol VARCHAR,
       instrument_type VARCHAR,
       source_endpoint VARCHAR,
       is_active BOOLEAN DEFAULT TRUE,
       discovered_at TIMESTAMP,
       last_enriched_at TIMESTAMP,
       PRIMARY KEY (symbol, instrument_type)
   );
   ```

2. **Update `UniverseRepo` queries** to join `ops.file_ingestions` with `ops.instrument_catalog` instead of `silver.instrument`

3. **Migrate data** from `silver.instrument` → `ops.instrument_catalog`

4. **Drop `silver.instrument`** table

5. **Remove `SILVER_INSTRUMENT_DDL`** from `duckdb_bootstrap.py`

6. **Update tests** to use new schema

**Impact Analysis Needed**:
- Are there downstream dependencies on `silver.instrument`?
- Is there a Gold layer `dim_instrument` that should contain the business attributes?
- How should instrument discovery/enrichment populate `ops.instrument_catalog`?

**ExecPlan Created**: ✅ `docs/prompts/execplan_remove_silver_instrument.md`

---

## Next Steps

### Immediate (PE Column Fix):
1. User closes DuckDB CLI (PID 25288)
2. Run migration: `python scripts/run_migration.py db/migrations/20260217_001_fix_pe_column_types.sql`
3. Verify with: `duckdb data/duckdb/SBFoundation.duckdb "DESCRIBE silver.fmp_market_sector_pe"`

### Planning Required (silver.instrument):
1. Review CLAUDE.md architecture constraints with user
2. Confirm Gold layer implementation status (`gold.dim_instrument`)
3. Create ExecPlan for silver.instrument → ops.instrument_catalog refactor (per CLAUDE.md Section 7)
4. Design migration strategy (data preservation, query updates, test updates)
