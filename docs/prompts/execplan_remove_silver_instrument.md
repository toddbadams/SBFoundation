# ExecPlan: Remove silver.instrument Table

**Created**: 2026-02-17
**Author**: Claude (AI Assistant)
**Status**: Planning

---

## Purpose / Big Picture

**What user-visible behavior does this enable?**

This refactoring enforces the Bronze→Silver→Gold architecture contract defined in CLAUDE.md by moving the `silver.instrument` table's operational metadata and surrogate keys out of the Silver layer.

**User Impact**:
- ✓ Architecture compliance: Silver layer contains only conformed vendor data with natural keys
- ✓ Clearer separation of concerns: operational metadata in `ops`, dimensions in `gold`
- ✓ Portable data model: Silver tables remain vendor-agnostic and free of pipeline artifacts
- ⚠️ Breaking change: Code querying `silver.instrument` must be updated

**Architectural Principle Enforced**:
> "Silver must NOT: Resolve surrogate keys (e.g., instrument_sk), Query Gold tables, Create dimension or fact tables, Add foreign key columns to Silver tables" — CLAUDE.md §2.6

---

## Progress

- [ ] **Phase 1: Discovery & Analysis** (Est: 30 min)
  - [ ] Catalog all references to `silver.instrument`
  - [ ] Identify what data belongs in `ops` vs `gold`
  - [ ] Check for downstream dependencies (external projects)
  - [ ] Document current data volume and schema

- [ ] **Phase 2: Create ops.instrument_catalog** (Est: 20 min)
  - [ ] Write migration to create `ops.instrument_catalog` table
  - [ ] Migrate data from `silver.instrument` → `ops.instrument_catalog`
  - [ ] Add index on (symbol, instrument_type)

- [ ] **Phase 3: Update Repository Layer** (Est: 45 min)
  - [ ] Refactor `UniverseRepo.get_update_tickers()` to use `ops.instrument_catalog`
  - [ ] Refactor `UniverseRepo.count_update_tickers()` to use `ops.instrument_catalog`
  - [ ] Refactor `UniverseRepo.get_instrument()` to use `ops.instrument_catalog`
  - [ ] Update repo to handle missing `ops.instrument_catalog` gracefully

- [ ] **Phase 4: Remove silver.instrument** (Est: 15 min)
  - [ ] Remove `SILVER_INSTRUMENT_DDL` from `duckdb_bootstrap.py`
  - [ ] Write migration to drop `silver.instrument` table

- [ ] **Phase 5: Update Tests** (Est: 30 min)
  - [ ] Update `tests/e2e/test_data_layer_promotion.py`
  - [ ] Add test for `ops.instrument_catalog` creation
  - [ ] Verify no tests query `silver.instrument`

- [ ] **Phase 6: Validation** (Est: 20 min)
  - [ ] Run full test suite
  - [ ] Verify `silver.instrument` no longer exists
  - [ ] Verify `ops.instrument_catalog` contains expected data
  - [ ] Run sample orchestration to confirm no breakage

**Total Estimated Time**: ~2.5 hours

---

## Surprises & Discoveries

_This section will be updated as work proceeds._

### Discovery: Current silver.instrument Usage
**Date**: 2026-02-17
**Finding**: The `silver.instrument` table is used in 3 primary locations:
1. `universe_repo.py` - Joins with `ops.file_ingestions` to filter by `instrument_type` and `is_active`
2. `universe_repo.py:get_instrument()` - Direct SELECT by symbol
3. `duckdb_bootstrap.py` - Table creation only

**Evidence**: Grep results from initial analysis

**Implication**: Limited blast radius - only `UniverseRepo` needs updates

---

### Discovery: Gold Layer References
**Date**: 2026-02-17
**Finding**: `UniverseRepo.get_new_tickers()` already queries `gold.dim_instrument` (lines 108-134)

**Evidence**:
```python
sql = """
    SELECT di.symbol
    FROM gold.dim_instrument di
    WHERE di.is_current = TRUE
    AND NOT EXISTS (...)
"""
```

**Implication**: The project already has a pattern for querying instrument dimensions from Gold. Silver.instrument is redundant for business attributes.

---

## Decision Log

### Decision 1: Create ops.instrument_catalog (Not silver.instrument_metadata)
**Date**: 2026-02-17
**Rationale**:
- The `ops` schema is for "manifests, watermarks, migrations, run summaries" per CLAUDE.md §10.2
- Instrument discovery/enrichment tracking is operational metadata, not business data
- Naming as "catalog" clarifies it's an inventory of known instruments for orchestration

**Alternative Considered**: Keep in `silver` with different name
**Rejected Because**: Would still violate "Silver = conformed vendor data only" principle

---

### Decision 2: Move Business Attributes to Gold (Out of Scope)
**Date**: 2026-02-17
**Rationale**:
- Business attributes (name, exchange, currency) belong in `gold.dim_instrument`
- CLAUDE.md §1 explicitly states: "Gold layer exists in a separate downstream project"
- This refactor only addresses SBFoundation's Silver layer violation

**Alternative Considered**: Create `silver.fmp_instrument_profile` from Bronze data
**Rejected Because**: Would duplicate existing instrument list datasets; Gold already handles this

---

### Decision 3: Preserve Only Operational Fields in ops.instrument_catalog
**Date**: 2026-02-17
**Fields to Preserve**:
- `symbol`, `instrument_type` (composite natural key)
- `source_endpoint` (where discovered)
- `is_active` (orchestration filter)
- `discovered_at`, `last_enriched_at` (tracking timestamps)

**Fields to Drop**:
- `instrument_id` (surrogate key - belongs in Gold)
- `name`, `exchange`, `exchange_short_name` (business data - belongs in Gold via Bronze→Silver→Gold)
- `currency`, `base_currency`, `quote_currency` (business data - belongs in Gold)
- `bronze_file_id`, `run_id`, `ingested_at` (lineage - already in `ops.file_ingestions`)

---

## Outcomes & Retrospective

_To be filled after implementation._

---

## Context and Orientation

### Current State

**File**: `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py:51-71`
**Problem**: Creates `silver.instrument` with mixed concerns (operational + business data + surrogate keys)

**File**: `src/sbfoundation/infra/universe_repo.py:58,151,213`
**Problem**: Queries `silver.instrument` for filtering by `instrument_type` and `is_active`

**File**: `src/sbfoundation/services/universe_service.py`
**Current**: Wraps `UniverseRepo` calls (no direct DB access)

**File**: `tests/e2e/test_data_layer_promotion.py`
**Status**: Unknown - needs investigation for `silver.instrument` usage

### Key Terms

- **Natural Key**: Business identifier from the real world (ticker symbol, date)
- **Surrogate Key**: System-generated identifier (instrument_id, instrument_sk)
- **Operational Metadata**: Pipeline tracking data (discovered_at, is_active, last_enriched_at)
- **Business Attributes**: Domain facts from vendors (name, exchange, currency)
- **Lineage Metadata**: Data provenance (bronze_file_id, run_id, ingested_at)

### Architecture Layers (CLAUDE.md §1)

| Layer | Contains | Example Tables |
|-------|----------|----------------|
| **Bronze** | Raw vendor payloads + metadata | `bronze/market/fmp/stock-list/*.json` |
| **Silver** | Validated, typed, conformed datasets with natural keys | `silver.fmp_company_profile`, `silver.fmp_income_statement` |
| **Gold** | Star schemas, surrogate keys, dimensions, facts | `gold.dim_instrument` ⚠️ (separate project) |
| **ops** | Manifests, watermarks, orchestration metadata | `ops.file_ingestions`, `ops.dataset_watermarks` |

---

## Plan of Work

### Phase 1: Discovery & Analysis

**Files to inspect**:
1. `tests/e2e/test_data_layer_promotion.py` - Check for `silver.instrument` test dependencies
2. `src/sbfoundation/**/*.py` - Grep for any additional `silver.instrument` references
3. Database inspection - Query current `silver.instrument` row count and schema

**Questions to answer**:
- How many instruments are currently in `silver.instrument`?
- Are there any views or triggers depending on this table?
- Does the Gold project import and query `silver.instrument`?

### Phase 2: Create ops.instrument_catalog

**File**: `db/migrations/20260217_002_create_ops_instrument_catalog.sql`

**Action**: Create migration SQL with:
1. `CREATE TABLE ops.instrument_catalog` with operational fields only
2. `INSERT INTO ops.instrument_catalog SELECT ...` from `silver.instrument`
3. `CREATE INDEX` on `(symbol, instrument_type)`
4. Verification query showing row count match

**Schema Design**:
```sql
CREATE TABLE ops.instrument_catalog (
    symbol VARCHAR NOT NULL,
    instrument_type VARCHAR NOT NULL,
    source_endpoint VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    discovered_at TIMESTAMP NOT NULL,
    last_enriched_at TIMESTAMP,
    PRIMARY KEY (symbol, instrument_type)
);
```

### Phase 3: Update Repository Layer

**File**: `src/sbfoundation/infra/universe_repo.py`

**Changes**:

1. **Line 58** - `get_update_tickers()` with `instrument_type` or `is_active` filter:
   - **OLD**: `INNER JOIN silver.instrument si ON fi.ticker = si.symbol`
   - **NEW**: `INNER JOIN ops.instrument_catalog ic ON fi.ticker = ic.symbol AND ic.instrument_type = fi.domain`
   - **Note**: May need to map domain→instrument_type or store instrument_type in `ops.file_ingestions`

2. **Line 151** - `count_update_tickers()`:
   - **OLD**: `INNER JOIN silver.instrument si ON fi.ticker = si.symbol`
   - **NEW**: `INNER JOIN ops.instrument_catalog ic ON fi.ticker = ic.symbol`

3. **Line 213** - `get_instrument()`:
   - **OLD**: `SELECT * FROM silver.instrument WHERE symbol = ?`
   - **NEW**: `SELECT * FROM ops.instrument_catalog WHERE symbol = ?`

4. **Line 226** - `_table_exists()` calls:
   - Update schema check from `"silver"` to `"ops"`
   - Update table name from `"instrument"` to `"instrument_catalog"`

**Edge Case Handling**:
- Gracefully handle missing `ops.instrument_catalog` (return empty list/None)
- Add logging for first-time table creation

### Phase 4: Remove silver.instrument

**File**: `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py`

**Line 51-71**: Remove entire `SILVER_INSTRUMENT_DDL` constant

**Line 121**: Remove `self._conn.execute(SILVER_INSTRUMENT_DDL)` call

**File**: `db/migrations/20260217_003_drop_silver_instrument.sql`

**Action**: Create migration to drop table:
```sql
-- Migration: Drop silver.instrument table (moved to ops.instrument_catalog)
-- Date: 2026-02-17

DROP TABLE IF EXISTS silver.instrument;
```

### Phase 5: Update Tests

**File**: `tests/e2e/test_data_layer_promotion.py`

**Action**:
1. Search for `silver.instrument` references
2. Replace with `ops.instrument_catalog` or remove if testing outdated behavior
3. Add test case verifying `silver.instrument` does NOT exist after bootstrap
4. Add test case verifying `ops.instrument_catalog` exists and is queryable

**File**: `tests/unit/infra/test_universe_repo.py` (if exists)

**Action**: Update mocks/fixtures to use `ops.instrument_catalog`

### Phase 6: Update Bootstrap to Create ops.instrument_catalog

**File**: `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py`

**Line 51** (where `SILVER_INSTRUMENT_DDL` was): Add new constant:
```python
OPS_INSTRUMENT_CATALOG_DDL = """
CREATE TABLE IF NOT EXISTS ops.instrument_catalog (
    symbol VARCHAR NOT NULL,
    instrument_type VARCHAR NOT NULL,
    source_endpoint VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    discovered_at TIMESTAMP NOT NULL,
    last_enriched_at TIMESTAMP,
    PRIMARY KEY (symbol, instrument_type)
);
"""
```

**Line 121** (where `SILVER_INSTRUMENT_DDL` was executed): Replace with:
```python
self._conn.execute(OPS_INSTRUMENT_CATALOG_DDL)
```

---

## Concrete Steps

### Step 1: Close DuckDB CLI and Backup Database
```bash
# Close any DuckDB processes (check Task Manager on Windows)
# Backup current database
cp data/duckdb/SBFoundation.duckdb data/duckdb/SBFoundation.duckdb.backup_20260217
```

**Expected Output**: Backup file created successfully

---

### Step 2: Analyze Current silver.instrument Table
```bash
python -c "
import duckdb
conn = duckdb.connect('data/duckdb/SBFoundation.duckdb', read_only=True)

# Check row count
print('Row count:', conn.execute('SELECT COUNT(*) FROM silver.instrument').fetchone()[0])

# Check schema
print('\nSchema:')
for row in conn.execute('DESCRIBE silver.instrument').fetchall():
    print(f'  {row[0]}: {row[1]}')

# Sample data
print('\nSample rows:')
for row in conn.execute('SELECT * FROM silver.instrument LIMIT 3').fetchall():
    print(f'  {row}')

conn.close()
"
```

**Expected Output**:
```
Row count: 1234
Schema:
  instrument_id: VARCHAR
  symbol: VARCHAR
  instrument_type: VARCHAR
  ...
Sample rows:
  ('abc123', 'AAPL', 'equity', ...)
```

---

### Step 3: Create Migration to Create ops.instrument_catalog

**File**: `db/migrations/20260217_002_create_ops_instrument_catalog.sql`

```sql
-- Migration: Create ops.instrument_catalog and migrate data from silver.instrument
-- Date: 2026-02-17
-- Purpose: Move instrument operational metadata from Silver to ops layer

-- Create ops.instrument_catalog with operational fields only
CREATE TABLE IF NOT EXISTS ops.instrument_catalog (
    symbol VARCHAR NOT NULL,
    instrument_type VARCHAR NOT NULL,
    source_endpoint VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    discovered_at TIMESTAMP NOT NULL,
    last_enriched_at TIMESTAMP,
    PRIMARY KEY (symbol, instrument_type)
);

-- Migrate data from silver.instrument (if exists)
INSERT INTO ops.instrument_catalog (
    symbol,
    instrument_type,
    source_endpoint,
    is_active,
    discovered_at,
    last_enriched_at
)
SELECT
    symbol,
    instrument_type,
    source_endpoint,
    is_active,
    discovered_at,
    last_enriched_at
FROM silver.instrument
WHERE NOT EXISTS (
    SELECT 1 FROM ops.instrument_catalog ic
    WHERE ic.symbol = silver.instrument.symbol
    AND ic.instrument_type = silver.instrument.instrument_type
);

-- Create index for query performance
CREATE INDEX IF NOT EXISTS idx_instrument_catalog_symbol
ON ops.instrument_catalog(symbol);

CREATE INDEX IF NOT EXISTS idx_instrument_catalog_type_active
ON ops.instrument_catalog(instrument_type, is_active);
```

**Run Migration**:
```bash
python scripts/run_migration.py db/migrations/20260217_002_create_ops_instrument_catalog.sql
```

**Expected Output**:
```
Connecting to database: C:\sb\SBFoundation\data\duckdb\SBFoundation.duckdb
Running migration: 20260217_002_create_ops_instrument_catalog.sql
✓ Migration completed successfully
```

**Verify**:
```bash
python -c "
import duckdb
conn = duckdb.connect('data/duckdb/SBFoundation.duckdb', read_only=True)

silver_count = conn.execute('SELECT COUNT(*) FROM silver.instrument').fetchone()[0]
ops_count = conn.execute('SELECT COUNT(*) FROM ops.instrument_catalog').fetchone()[0]

print(f'silver.instrument rows: {silver_count}')
print(f'ops.instrument_catalog rows: {ops_count}')
print(f'Match: {silver_count == ops_count}')

conn.close()
"
```

**Expected Output**:
```
silver.instrument rows: 1234
ops.instrument_catalog rows: 1234
Match: True
```

---

### Step 4: Update UniverseRepo to Use ops.instrument_catalog

**File**: `src/sbfoundation/infra/universe_repo.py`

**Edit 1**: Update `get_update_tickers()` join (line 58)

```python
# OLD:
sql = """
    SELECT DISTINCT fi.ticker
    FROM ops.file_ingestions fi
    INNER JOIN silver.instrument si ON fi.ticker = si.symbol
    WHERE fi.ticker IS NOT NULL AND fi.ticker <> ''
    AND fi.silver_can_promote = TRUE
"""
# ...
if is_active:
    sql += " AND si.is_active = TRUE"
if instrument_type:
    sql += " AND si.instrument_type = ?"

# NEW:
sql = """
    SELECT DISTINCT fi.ticker
    FROM ops.file_ingestions fi
    INNER JOIN ops.instrument_catalog ic ON fi.ticker = ic.symbol
    WHERE fi.ticker IS NOT NULL AND fi.ticker <> ''
    AND fi.silver_can_promote = TRUE
"""
# ...
if is_active:
    sql += " AND ic.is_active = TRUE"
if instrument_type:
    sql += " AND ic.instrument_type = ?"
```

**Edit 2**: Update `count_update_tickers()` join (line 148)

```python
# OLD:
sql = """
    SELECT COUNT(DISTINCT fi.ticker)
    FROM ops.file_ingestions fi
    INNER JOIN silver.instrument si ON fi.ticker = si.symbol
    WHERE fi.ticker IS NOT NULL AND fi.ticker <> ''
    AND fi.silver_can_promote = TRUE
    AND si.instrument_type = ?
"""

# NEW:
sql = """
    SELECT COUNT(DISTINCT fi.ticker)
    FROM ops.file_ingestions fi
    INNER JOIN ops.instrument_catalog ic ON fi.ticker = ic.symbol
    WHERE fi.ticker IS NOT NULL AND fi.ticker <> ''
    AND fi.silver_can_promote = TRUE
    AND ic.instrument_type = ?
"""
```

**Edit 3**: Update `get_instrument()` query (line 213)

```python
# OLD:
if not self._table_exists(conn, "silver", "instrument"):
    return None

result = conn.execute(
    "SELECT * FROM silver.instrument WHERE symbol = ?",
    [symbol],
).fetchone()

# NEW:
if not self._table_exists(conn, "ops", "instrument_catalog"):
    return None

result = conn.execute(
    "SELECT * FROM ops.instrument_catalog WHERE symbol = ?",
    [symbol],
).fetchone()
```

---

### Step 5: Update duckdb_bootstrap.py

**File**: `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py`

**Edit 1**: Remove `SILVER_INSTRUMENT_DDL` constant (lines 51-71)

**Edit 2**: Add `OPS_INSTRUMENT_CATALOG_DDL` constant (after `OPS_FILE_INGESTIONS_DDL`)

```python
OPS_INSTRUMENT_CATALOG_DDL = """
CREATE TABLE IF NOT EXISTS ops.instrument_catalog (
    symbol VARCHAR NOT NULL,
    instrument_type VARCHAR NOT NULL,
    source_endpoint VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    discovered_at TIMESTAMP NOT NULL,
    last_enriched_at TIMESTAMP,
    PRIMARY KEY (symbol, instrument_type)
);
"""
```

**Edit 3**: Update `_initialize_schema()` method (line 121)

```python
# OLD:
self._conn.execute(SILVER_INSTRUMENT_DDL)

# NEW:
self._conn.execute(OPS_INSTRUMENT_CATALOG_DDL)
```

**Edit 4**: Update docstring (line 112)

```python
# OLD:
"""
Creates:
- ops, silver schemas
- ops.file_ingestions table (core metadata table)
- silver.instrument table
"""

# NEW:
"""
Creates:
- ops, silver schemas
- ops.file_ingestions table (core metadata table)
- ops.instrument_catalog table (instrument discovery/enrichment tracking)
"""
```

---

### Step 6: Run Tests

```bash
# Run unit tests
pytest tests/unit/infra/test_universe_repo.py -v

# Run E2E tests
pytest tests/e2e/test_data_layer_promotion.py -v

# Run full test suite
pytest tests/ -v
```

**Expected Output**: All tests pass

---

### Step 7: Create Migration to Drop silver.instrument

**File**: `db/migrations/20260217_003_drop_silver_instrument.sql`

```sql
-- Migration: Drop silver.instrument table
-- Date: 2026-02-17
-- Purpose: Remove silver.instrument after migrating to ops.instrument_catalog
-- IMPORTANT: Only run after ops.instrument_catalog is populated and code is updated

DROP TABLE IF EXISTS silver.instrument;
```

**Run Migration**:
```bash
python scripts/run_migration.py db/migrations/20260217_003_drop_silver_instrument.sql
```

**Expected Output**:
```
Connecting to database: C:\sb\SBFoundation\data\duckdb\SBFoundation.duckdb
Running migration: 20260217_003_drop_silver_instrument.sql
✓ Migration completed successfully
```

---

### Step 8: Verify silver.instrument No Longer Exists

```bash
python -c "
import duckdb
conn = duckdb.connect('data/duckdb/SBFoundation.duckdb', read_only=True)

# Check tables in silver schema
result = conn.execute('''
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'silver'
    ORDER BY table_name
''').fetchall()

print('Silver tables:')
for row in result:
    print(f'  - {row[0]}')

# Verify silver.instrument is gone
has_instrument = any('instrument' == row[0] for row in result)
print(f'\nsilver.instrument exists: {has_instrument}')

# Verify ops.instrument_catalog exists
ops_result = conn.execute('''
    SELECT COUNT(*) > 0
    FROM information_schema.tables
    WHERE table_schema = 'ops' AND table_name = 'instrument_catalog'
''').fetchone()

print(f'ops.instrument_catalog exists: {ops_result[0]}')

conn.close()
"
```

**Expected Output**:
```
Silver tables:
  - fmp_company_profile
  - fmp_income_statement
  - fmp_market_sector_pe
  - fmp_market_industry_pe
  - ... (no 'instrument')

silver.instrument exists: False
ops.instrument_catalog exists: True
```

---

### Step 9: Run Full Orchestration Test

```bash
# Run a small universe orchestration to verify everything works
python -c "
from sbfoundation.services.universe_service import UniverseService
from sbfoundation.settings import INSTRUMENT_TYPE_EQUITY

universe = UniverseService()

# Test update_tickers
tickers = universe.update_tickers(limit=10, instrument_type=INSTRUMENT_TYPE_EQUITY)
print(f'Update tickers (first 10): {tickers}')

# Test new_tickers
new = universe.new_tickers(limit=10, instrument_type=INSTRUMENT_TYPE_EQUITY)
print(f'New tickers (first 10): {new}')

# Test get_instrument
if tickers:
    instrument = universe.get_instrument(tickers[0])
    print(f'Instrument details for {tickers[0]}: {instrument}')

universe.close()
print('\n✓ All universe service calls successful')
"
```

**Expected Output**:
```
Update tickers (first 10): ['AAPL', 'MSFT', 'GOOGL', ...]
New tickers (first 10): ['XYZ', 'ABC', ...]
Instrument details for AAPL: {'symbol': 'AAPL', 'instrument_type': 'equity', ...}

✓ All universe service calls successful
```

---

## Validation and Acceptance

### Acceptance Criteria

1. ✅ **No silver.instrument table exists** in the database after migration
   - Verify: `SELECT * FROM information_schema.tables WHERE table_schema='silver' AND table_name='instrument'` returns 0 rows

2. ✅ **ops.instrument_catalog table exists** with correct schema
   - Verify: `DESCRIBE ops.instrument_catalog` shows 6 columns (symbol, instrument_type, source_endpoint, is_active, discovered_at, last_enriched_at)

3. ✅ **Data migration successful** - row counts match
   - Verify: `ops.instrument_catalog` row count equals original `silver.instrument` row count (from Step 2)

4. ✅ **Repository queries work** with ops.instrument_catalog
   - Verify: `UniverseRepo.get_update_tickers()` returns expected tickers
   - Verify: `UniverseRepo.count_update_tickers()` returns expected count
   - Verify: `UniverseRepo.get_instrument()` returns expected instrument details

5. ✅ **Bootstrap creates ops.instrument_catalog** on fresh database
   - Verify: Delete database, run bootstrap, confirm `ops.instrument_catalog` exists

6. ✅ **All tests pass** (unit + E2E)
   - Verify: `pytest tests/ -v` exits with code 0

7. ✅ **No code references silver.instrument**
   - Verify: `grep -r "silver.instrument" src/` returns no results (except comments/docs)

### Observable Behaviors

**Before Refactoring**:
```sql
-- Queries that work
SELECT * FROM silver.instrument WHERE symbol = 'AAPL';
SELECT * FROM ops.instrument_catalog;  -- ERROR: table does not exist
```

**After Refactoring**:
```sql
-- Queries that work
SELECT * FROM ops.instrument_catalog WHERE symbol = 'AAPL';
SELECT * FROM silver.instrument;  -- ERROR: table does not exist
```

### Regression Testing

Test these scenarios to ensure no breakage:

1. **Fresh database bootstrap**: Delete DuckDB file, run bootstrap, verify schemas created
2. **Universe service calls**: Call all public methods of `UniverseService` with various filters
3. **Orchestration run**: Run full orchestration for small ticker set (3-5 tickers)
4. **Filtered queries**: Test `instrument_type` filter, `is_active` filter, both filters combined

---

## Idempotence and Recovery

### Migration Idempotence

All migrations use `IF NOT EXISTS` / `IF EXISTS` for safe re-runs:

```sql
-- 20260217_002 (idempotent)
CREATE TABLE IF NOT EXISTS ops.instrument_catalog ...
INSERT INTO ops.instrument_catalog ... WHERE NOT EXISTS ...

-- 20260217_003 (idempotent)
DROP TABLE IF EXISTS silver.instrument;
```

### Rollback Strategy

If issues arise, rollback in reverse order:

**Step 1: Restore silver.instrument**
```sql
-- Re-create silver.instrument from ops.instrument_catalog
CREATE TABLE silver.instrument AS
SELECT
    gen_random_uuid()::VARCHAR as instrument_id,
    symbol,
    instrument_type,
    source_endpoint,
    NULL as name,
    NULL as exchange,
    NULL as exchange_short_name,
    NULL as currency,
    NULL as base_currency,
    NULL as quote_currency,
    is_active,
    discovered_at,
    last_enriched_at,
    NULL as bronze_file_id,
    NULL as run_id,
    NULL as ingested_at
FROM ops.instrument_catalog;
```

**Step 2: Restore code files from git**
```bash
git checkout HEAD -- src/sbfoundation/infra/duckdb/duckdb_bootstrap.py
git checkout HEAD -- src/sbfoundation/infra/universe_repo.py
```

**Step 3: Restore database from backup**
```bash
cp data/duckdb/SBFoundation.duckdb.backup_20260217 data/duckdb/SBFoundation.duckdb
```

### Safe Re-Run

To safely re-run the entire refactoring:

1. Restore from backup: `cp data/duckdb/SBFoundation.duckdb.backup_20260217 data/duckdb/SBFoundation.duckdb`
2. Run migrations in order: 002 → 003
3. Code changes are safe to re-apply (no data modifications)

---

## Artifacts and Notes

_To be filled as work proceeds with command transcripts, test outputs, and key findings._

### Migration Transcript

```
[Placeholder for migration run output]
```

### Test Results

```
[Placeholder for pytest output]
```

### Schema Diff

```
[Placeholder for before/after schema comparison]
```

---

## Interfaces and Dependencies

### Tables

**Created**:
```sql
ops.instrument_catalog (
    symbol VARCHAR NOT NULL,
    instrument_type VARCHAR NOT NULL,
    source_endpoint VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    discovered_at TIMESTAMP NOT NULL,
    last_enriched_at TIMESTAMP,
    PRIMARY KEY (symbol, instrument_type)
)
```

**Removed**:
```sql
silver.instrument (entire table dropped)
```

### Python Classes Modified

**File**: `src/sbfoundation/infra/universe_repo.py`

**Methods**:
- `get_update_tickers()` - Joins `ops.instrument_catalog` instead of `silver.instrument`
- `count_update_tickers()` - Joins `ops.instrument_catalog` instead of `silver.instrument`
- `get_instrument()` - Queries `ops.instrument_catalog` instead of `silver.instrument`

**Signature Changes**: None (all method signatures remain identical)

**File**: `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py`

**Constants**:
- Removed: `SILVER_INSTRUMENT_DDL`
- Added: `OPS_INSTRUMENT_CATALOG_DDL`

**Methods**:
- `_initialize_schema()` - Executes `OPS_INSTRUMENT_CATALOG_DDL` instead of `SILVER_INSTRUMENT_DDL`

### Dependencies

**Python Packages**: No new dependencies required

**External Systems**: None

**Database Version**: DuckDB (any recent version supporting `CREATE TABLE IF NOT EXISTS`)

---

## END OF EXECPLAN
