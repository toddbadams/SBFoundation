# ExecPlan: Bronze Compression & Write-Once Catalog

**Version**: 1.1
**Created**: 2026-03-14
**Status**: Backlog
**Branch**: `feature/bronze-compression`

---

## Purpose / Big Picture

Currently, all Bronze payloads are stored as pretty-printed JSON files (~2–10× their data size). There is no durable, self-contained record of what Bronze artifacts exist — that knowledge lives exclusively in DuckDB's `ops` schema, which is an analytics engine, not a reliable operational registry.

This ExecPlan achieves two goals:

1. **Compress Bronze JSON → Parquet** — each Bronze file is re-encoded as a Parquet file. The request envelope and metadata are stored as Parquet file-level metadata (key-value pairs); the content rows become the Parquet row group. This reduces storage by 5–20×.

2. **Write-once Bronze catalog (`bronze/catalog.db`)** — a SQLite file co-located with the Bronze artifacts that records every Bronze artifact at the moment it is written. It is **insert-only** (never updated), making it a durable, portable, self-describing registry of the Bronze layer. Given only the `bronze/` folder, you can reconstruct the full ingestion history without DuckDB.

### What does NOT change

- **DuckDB is not removed.** Silver tables, Gold tables, and all `ops` tables in DuckDB remain exactly as they are.
- **`ops.file_ingestions` stays in DuckDB.** Silver promotion tracking — which Bronze files have been loaded to Silver, with what row counts and errors — continues to be managed by DuckDB's `ops` schema.
- **`ops.dataset_watermarks` stays in DuckDB.** Cadence gating for Silver promotion remains DuckDB-owned.
- **`OpsService` / `DuckDbOpsRepo` are not replaced.** They continue to orchestrate Silver promotion.

### Layered responsibilities after this ExecPlan

| Layer | Store | Responsibility | Write pattern |
|---|---|---|---|
| **Bronze** | Parquet files | Raw vendor payloads, compressed | Append-only (write-once per `file_id`) |
| **Bronze catalog** | `bronze/catalog.db` (SQLite) | Artifact registry — what was ingested, when, coverage, hash | INSERT-only (never updated) |
| **Ops / Silver** | DuckDB `ops.file_ingestions` | Silver promotion tracking — which Bronze files have been promoted | UPSERT (mutable) |
| **Silver** | DuckDB `silver.*` | Conformed datasets | UPSERT via KEY_COLS |
| **Gold** | DuckDB `gold.*` | Star schema analytics | MERGE/UPSERT |

### Bronze cadence gating (new behaviour)

Bronze ingestion's "is this dataset due?" check currently queries `ops.dataset_watermarks` (DuckDB). After this ExecPlan it will query `bronze/catalog.db` directly — deriving `max(bronze_to_date)` per dataset identity from the SQLite catalog. This makes the Bronze layer fully self-contained: it does not need DuckDB to decide whether to re-fetch.

### User-visible outcomes

- Bronze storage footprint drops significantly (Parquet columnar + Snappy compression).
- `bronze/catalog.db` is a portable, human-queryable record of every Bronze artifact — independent of DuckDB.
- Copying the `bronze/` folder to another machine is sufficient to reconstruct the Bronze layer's history.
- DuckDB ops tables are unaffected and continue to track Silver promotion.
- The pipeline remains fully idempotent: re-running any date skips files already in `catalog.db` and produces no duplicate rows.

---

## Progress

- [ ] Step 0 — Create feature branch
- [ ] Step 1 — Implement `BronzeCatalogDb` (SQLite, insert-only)
- [ ] Step 2 — Implement `BronzeParquetWriter` (JSON → Parquet)
- [ ] Step 3 — Implement `BronzeParquetReader` (Parquet → content rows + envelope metadata)
- [ ] Step 4 — Update `ResultFileAdapter` to write Parquet + register in SQLite catalog
- [ ] Step 5 — Update `RunRequest.bronze_relative_filename` (`.json` → `.parquet`)
- [ ] Step 6 — Update Bronze cadence gating to read from `BronzeCatalogDb`
- [ ] Step 7 — Update `BronzeBatchReader` to read Parquet files
- [ ] Step 8 — Migration utility: compress existing JSON → Parquet + back-fill SQLite catalog
- [ ] Step 9 — Write unit + integration tests
- [ ] Step 10 — Validation and acceptance

---

## Surprises & Discoveries

_Updated as work proceeds._

- `BronzeResult.to_dict()` includes `first_date` / `last_date` computed from content — these map naturally to Parquet metadata and to SQLite catalog `coverage_from` / `coverage_to` columns.
- `apikey` is already redacted in `RunRequest.to_dict()` (`["***"]`) — safe to store in Parquet metadata and SQLite.
- `ops.file_ingestions` composite PK is `(run_id, file_id)`. The SQLite catalog uses the same PK but is insert-only — conflicts are silently ignored (`INSERT OR IGNORE`).
- Bronze cadence gating currently calls `DuckDbOpsRepo.get_latest_bronze_to_date()` which reads `ops.file_ingestions`. After this ExecPlan that call is routed to `BronzeCatalogDb.get_latest_to_date()` — no change to `ops.file_ingestions`.
- DuckDB currently reads `bronze_filename` from `ops.file_ingestions` to locate files during Silver promotion. After this ExecPlan, `BronzeBatchReader` resolves the file path from `bronze/catalog.db` (SQLite) instead, so DuckDB no longer needs to store the file path.

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-03-14 | Use Parquet + Snappy for Bronze files | Snappy is fast on read/write; good balance of compression speed vs ratio for columnar financial data |
| 2026-03-14 | Store request envelope as Parquet file-level metadata (key-value) | Keeps row group clean (content rows only); envelope is small and rarely read during Silver promotion |
| 2026-03-14 | Bronze catalog is INSERT-only (no UPDATE) | Bronze is append-only by contract — catalog must mirror that invariant; Silver promotion state belongs in DuckDB |
| 2026-03-14 | Catalog lives at `bronze/catalog.db` | Co-located with Bronze Parquet files; the whole Bronze layer is self-describing in one folder |
| 2026-03-14 | Bronze cadence gating moves to SQLite catalog | Removes Bronze layer's dependency on DuckDB at ingestion time; DuckDB ops tables remain for Silver tracking |
| 2026-03-14 | DuckDB `ops.file_ingestions` is NOT changed | Silver promotion tracking is DuckDB's responsibility; splitting it would create synchronisation risk |
| 2026-03-14 | `BronzeBatchReader` resolves file paths from SQLite catalog | DuckDB ops no longer needs `bronze_filename` column; catalog is authoritative for Bronze artifact locations |

---

## Context and Orientation

### Current state vs. target state

| Component | Before | After |
|---|---|---|
| Bronze file format | Pretty-printed JSON (`.json`) | Snappy Parquet (`.parquet`) |
| Bronze artifact registry | None (knowledge only in DuckDB) | SQLite `bronze/catalog.db` — insert-only |
| Bronze cadence gating | `DuckDbOpsRepo.get_latest_bronze_to_date()` | `BronzeCatalogDb.get_latest_to_date()` |
| Silver promotion tracking | DuckDB `ops.file_ingestions` | **Unchanged** |
| Silver + Gold storage | DuckDB `silver.*`, `gold.*` | **Unchanged** |
| `OpsService` / `DuckDbOpsRepo` | Manages both bronze registration + silver tracking | Manages silver tracking only (bronze registration moves to catalog) |

### Key files

| File | Role | Change |
|---|---|---|
| `src/sbfoundation/infra/result_file_adaptor.py` | Read/write Bronze files | Write Parquet; register in SQLite catalog |
| `src/sbfoundation/run/dtos/bronze_result.py` | `BronzeResult` — source of Parquet metadata | No change (read-only use) |
| `src/sbfoundation/run/dtos/run_request.py` | `bronze_relative_filename` property | Change extension to `.parquet` |
| `src/sbfoundation/bronze/bronze_service.py` | Orchestrates ingestion | Route cadence gating to `BronzeCatalogDb` |
| `src/sbfoundation/ops/infra/duckdb_ops_repo.py` | DuckDB ops queries | Remove `get_latest_bronze_to_date`; rest unchanged |
| `src/sbfoundation/ops/services/ops_service.py` | Orchestrates Silver promotion | Remove bronze-registration path; rest unchanged |
| `src/sbfoundation/bronze/bronze_batch_reader.py` | Reads Bronze for Silver promotion | Read from SQLite catalog + Parquet files |
| `src/sbfoundation/dtos/models.py` | `BronzeManifestRow` | `file_path_rel` now points to `.parquet` |

### Term definitions

- **Bronze Parquet file**: a `.parquet` file containing the content rows of a single API response, with request envelope stored as Parquet file-level key-value metadata. Write-once, never overwritten.
- **Bronze catalog**: `bronze/catalog.db` — SQLite database co-located with Bronze artifacts. INSERT-only. Records what files exist and their metadata. Does not track Silver promotion.
- **Parquet file-level metadata**: the `FileMetaData.key_value_metadata` field — a list of `KeyValue` byte-string pairs attached to the Parquet file header, readable without loading row groups.
- **Silver promotion tracking**: the existing `ops.file_ingestions` table in DuckDB. Records which Bronze files have been promoted to Silver, with what results. Mutable. Not changed by this ExecPlan.

---

## Plan of Work

### Phase 1 — Bronze Artifact Catalog (SQLite, insert-only)

**1.1 Create `BronzeCatalogDb` (new file: `src/sbfoundation/bronze/catalog/bronze_catalog_db.py`)**

This class opens/creates `bronze/catalog.db` via Python's built-in `sqlite3`. It is **insert-only** — no UPDATE statements. Thread-safe via a single `threading.Lock`.

`catalog_db_path` is resolved from:
```python
Folders.data_absolute_path() / "bronze" / "catalog.db"
```

**SQLite schema (DDL)**:

```sql
CREATE TABLE IF NOT EXISTS bronze_artifacts (
    run_id          TEXT NOT NULL,
    file_id         TEXT NOT NULL,
    domain          TEXT NOT NULL,
    source          TEXT NOT NULL,
    dataset         TEXT NOT NULL,
    discriminator   TEXT NOT NULL DEFAULT '',
    ticker          TEXT NOT NULL DEFAULT '',
    file_path       TEXT NOT NULL,  -- repo-relative path to .parquet file
    status_code     INTEGER,
    error           TEXT,           -- null if successful
    row_count       INTEGER,
    coverage_from   TEXT,           -- ISO-8601 date (null for snapshots)
    coverage_to     TEXT,           -- ISO-8601 date (null for snapshots)
    payload_hash    TEXT,
    ingested_at     TEXT NOT NULL,  -- ISO-8601 datetime (UTC)
    can_promote     INTEGER NOT NULL DEFAULT 0,  -- 1 if eligible for Silver
    PRIMARY KEY (run_id, file_id)
);

CREATE INDEX IF NOT EXISTS idx_ba_identity
    ON bronze_artifacts (domain, source, dataset, discriminator, ticker);

CREATE INDEX IF NOT EXISTS idx_ba_coverage
    ON bronze_artifacts (domain, source, dataset, discriminator, ticker, coverage_to);

CREATE INDEX IF NOT EXISTS idx_ba_promotable
    ON bronze_artifacts (can_promote);
```

**Public methods on `BronzeCatalogDb`**:

```python
def register(self, result: BronzeResult) -> None:
    """INSERT OR IGNORE — silently skips if (run_id, file_id) already exists."""

def get_latest_to_date(
    self, *, domain: str, source: str, dataset: str,
    discriminator: str, ticker: str
) -> date | None:
    """Returns max(coverage_to) for the given identity. Used for cadence gating."""

def get_latest_ingestion_time(
    self, *, domain: str, source: str, dataset: str,
    discriminator: str, ticker: str
) -> datetime | None:
    """Returns max(ingested_at) for the given identity. Used for dedup gating."""

def list_promotable(self) -> list[BronzeArtifactRow]:
    """Returns all rows where can_promote=1. Used by BronzeBatchReader."""

def get_bulk_coverage(
    self, *, domain: str, source: str, dataset: str, discriminator: str
) -> dict[str, tuple[date | None, date | None]]:
    """Returns {ticker: (min_coverage_from, max_coverage_to)} for batch reads."""
```

**New value object `BronzeArtifactRow`** (add to `src/sbfoundation/dtos/models.py`):

```python
@dataclass(frozen=True)
class BronzeArtifactRow:
    run_id: str
    file_id: str
    domain: str
    source: str
    dataset: str
    discriminator: str
    ticker: str
    file_path: str           # repo-relative .parquet path
    row_count: int
    coverage_from: date | None
    coverage_to: date | None
    payload_hash: str | None
    ingested_at: datetime
    can_promote: bool
```

**1.2 Wire `BronzeCatalogDb` into `BronzeService`**

`BronzeService` receives a `BronzeCatalogDb` instance (constructor-injected). After `ResultFileAdapter.write(result)` succeeds, call `catalog.register(result)`.

Bronze cadence gating (`_is_due` / dedup checks) is updated to call:
- `catalog.get_latest_to_date(...)` → replaces `DuckDbOpsRepo.get_latest_bronze_to_date(...)`
- `catalog.get_latest_ingestion_time(...)` → replaces `DuckDbOpsRepo.get_latest_bronze_ingestion_time(...)`

Remove these two methods from `DuckDbOpsRepo` and the corresponding queries from `OpsService`.

---

### Phase 2 — Parquet Bronze Files

**2.1 Create `BronzeParquetWriter` (new file: `src/sbfoundation/bronze/parquet/bronze_parquet_writer.py`)**

```python
class BronzeParquetWriter:
    def write(self, result: BronzeResult, path: Path) -> Path:
        ...
```

- Extracts `result.content` → `pyarrow.Table` (infer schema from first row; handle empty content as zero-row table).
- Builds Parquet file-level key-value metadata from request envelope:

| Key | Value |
|---|---|
| `sbf.run_id` | `result.request.run_id` |
| `sbf.file_id` | `result.request.file_id` |
| `sbf.domain` | `result.request.recipe.domain` |
| `sbf.source` | `result.request.recipe.source` |
| `sbf.dataset` | `result.request.recipe.dataset` |
| `sbf.discriminator` | `result.request.recipe.discriminator or ""` |
| `sbf.ticker` | `result.request.ticker or ""` |
| `sbf.now` | `result.now.isoformat()` |
| `sbf.status_code` | `str(result.status_code)` |
| `sbf.reason` | `result.reason` |
| `sbf.error` | `result.error or ""` |
| `sbf.first_date` | `result.first_date or ""` |
| `sbf.last_date` | `result.last_date or ""` |
| `sbf.elapsed_microseconds` | `str(result.elapsed_microseconds)` |
| `sbf.payload_hash` | `result.hash or ""` |

- Writes using `pyarrow.parquet.write_table(table, path, compression="snappy")`.
- Creates parent directories (`path.parent.mkdir(parents=True, exist_ok=True)`).
- Returns the written `Path`.

**2.2 Create `BronzeParquetReader` (new file: `src/sbfoundation/bronze/parquet/bronze_parquet_reader.py`)**

```python
class BronzeParquetReader:
    def read(self, path: Path) -> tuple[dict[str, str], list[dict]]:
        """Returns (envelope_metadata, content_rows)."""
```

- Reads Parquet file metadata (key-value pairs) without loading row groups.
- Reads row groups → `list[dict]` for Silver promotion.
- Falls back to empty list if file has zero rows (snapshot datasets).

**2.3 Update `ResultFileAdapter`**

`src/sbfoundation/infra/result_file_adaptor.py`:

- `write(result)` → calls `BronzeParquetWriter.write(result, abs_path)`. No JSON serialisation.
- `read(path)` → dispatches on file extension:
  - `.parquet` → `BronzeParquetReader.read(path)` → reconstruct dict compatible with existing callers
  - `.json` → existing JSON deserialization (legacy fallback — no code deletion until migration is confirmed)

**2.4 Update `RunRequest._filename`**

`src/sbfoundation/run/dtos/run_request.py`, `_filename` property:
- Change `f"{filename}.json"` → `f"{filename}.parquet"`.

---

### Phase 3 — Silver Promotion Path

**3.1 Update `BronzeBatchReader`**

`src/sbfoundation/bronze/bronze_batch_reader.py`:

- Load promotable artifact rows from `BronzeCatalogDb.list_promotable()` (returns `list[BronzeArtifactRow]`) instead of querying `ops.file_ingestions` for `bronze_can_promote=True`.
- Use `BronzeParquetReader.read(file_path)` to load content rows for each artifact.
- `BronzeManifestRow` fields map directly from `BronzeArtifactRow` — update the constructor call.

**3.2 `OpsService` — scope reduction**

Remove from `OpsService`:
- `insert_bronze_manifest()` — Bronze registration now happens via `BronzeCatalogDb.register()` in `BronzeService`
- Any call to `DuckDbOpsRepo` methods that served Bronze cadence gating

Keep in `OpsService` (unchanged):
- `upsert_silver_ingestion()` — Silver promotion results still written to `ops.file_ingestions`
- `get_watermark_date()` — Silver cadence watermarks remain in DuckDB
- All Gold-related calls

**3.3 DuckDB `ops.file_ingestions` — schema simplification (optional)**

The `bronze_filename`, `bronze_rows`, `bronze_from_date`, `bronze_to_date`, `bronze_payload_hash`, `bronze_can_promote` columns in `ops.file_ingestions` become redundant (that information now lives in the SQLite catalog). These columns may be dropped in a follow-up migration. For this ExecPlan, leave them in place — they will contain NULL for new rows written after this change goes live. A `NOTE` is added to the schema migration log.

---

### Phase 4 — Migration Utility

**4.1 Create `BronzeCompressMigration` (new file: `src/sbfoundation/maintenance/bronze_compress_migration.py`)**

This script is the one-shot operation that converts all existing `.json` Bronze files to Parquet and back-fills `bronze/catalog.db`. It is safe to run multiple times (fully idempotent) and safe to interrupt — progress is committed to SQLite after each file so a restart picks up where it left off.

#### Class design

```python
@dataclass
class MigrationResult:
    total: int = 0
    skipped: int = 0       # .parquet already exists AND catalog row present
    converted: int = 0     # newly written .parquet + catalog row
    failed: int = 0        # errors logged; .json left untouched
    deleted: int = 0       # .json files removed (only when delete_json=True)

class BronzeCompressMigration:
    def __init__(
        self,
        bronze_root: Path,          # absolute path to data/bronze/
        catalog_db: BronzeCatalogDb,
        writer: BronzeParquetWriter,
        reader_json: ResultFileAdapter,
        delete_json: bool = False,  # True → delete .json after confirmed .parquet write
        dry_run: bool = False,      # True → log what would happen; write nothing
        logger: SBLogger | None = None,
    ) -> None: ...

    def run(self) -> MigrationResult: ...
    def _migrate_file(self, json_path: Path) -> str:  # returns "skipped"|"converted"|"failed"
        ...
```

#### Per-file migration logic (`_migrate_file`)

```
For each json_path:
  1. Derive parquet_path = json_path.with_suffix(".parquet")

  2. Check idempotency gate:
       already_in_catalog = catalog.has_file(json_path.stem)  # lookup by file_id (stem)
       parquet_exists     = parquet_path.exists()
       if parquet_exists AND already_in_catalog:
           log DEBUG "skip {json_path.name} — already migrated"
           return "skipped"

  3. Deserialize JSON:
       result = ResultFileAdapter.read(json_path)
       if result is None or result.request is None:
           log ERROR "skip {json_path.name} — unreadable or corrupt JSON"
           return "failed"

  4. Write Parquet (unless dry_run):
       if not parquet_exists:
           BronzeParquetWriter.write(result, parquet_path)
       # If write raises → log ERROR, return "failed" (json untouched)

  5. Register in catalog (INSERT OR IGNORE):
       catalog.register(result)

  6. Optionally delete JSON:
       if delete_json and not dry_run:
           json_path.unlink()
           log DEBUG "deleted {json_path.name}"

  return "converted"
```

#### Discovery

Scan `bronze_root` recursively for `*.json` files, excluding:
- `catalog.db` (not a Bronze file)
- Any file in a `manifests/` subdirectory (run summary manifests — not BronzeResult payloads)
- Any file whose stem does not look like a 32-char hex UUID (guards against stray files)

```python
def _find_json_files(self) -> list[Path]:
    return sorted(
        p for p in self.bronze_root.rglob("*.json")
        if p.parent.name != "manifests"
        and len(p.stem.split("-")[0]) >= 32  # file_id prefix is 32-char hex
    )
```

#### Progress reporting

Print a summary line every 100 files and on completion:

```
[bronze-migrate]  500 / 3842 — converted=487 skipped=10 failed=3
[bronze-migrate] DONE — total=3842 converted=3801 skipped=38 failed=3 deleted=0
```

Use `self._logger.info(...)` with `run_id=None` (not a pipeline run).

#### `__main__` block

```python
if __name__ == "__main__":
    import argparse
    from sbfoundation.folders import Folders
    from sbfoundation.bronze.catalog.bronze_catalog_db import BronzeCatalogDb
    from sbfoundation.bronze.parquet.bronze_parquet_writer import BronzeParquetWriter
    from sbfoundation.infra.result_file_adaptor import ResultFileAdapter

    parser = argparse.ArgumentParser(description="Migrate Bronze JSON files to Parquet")
    parser.add_argument(
        "--delete-json", action="store_true", default=False,
        help="Delete .json files after successful Parquet conversion"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Log what would happen without writing any files"
    )
    args = parser.parse_args()

    bronze_root = Folders.data_absolute_path() / "bronze"
    catalog = BronzeCatalogDb(bronze_root / "catalog.db")

    migration = BronzeCompressMigration(
        bronze_root=bronze_root,
        catalog_db=catalog,
        writer=BronzeParquetWriter(),
        reader_json=ResultFileAdapter(),
        delete_json=args.delete_json,
        dry_run=args.dry_run,
    )
    result = migration.run()
    print(result)
```

**CLI usage**:

```bash
# Dry run — see what would be migrated without writing anything
python src/sbfoundation/maintenance/bronze_compress_migration.py --dry-run

# Convert all .json → .parquet, keep .json files
python src/sbfoundation/maintenance/bronze_compress_migration.py

# Convert and delete .json files after confirmed conversion
python src/sbfoundation/maintenance/bronze_compress_migration.py --delete-json
```

#### `BronzeCatalogDb.has_file` (add alongside `register`)

```python
def has_file(self, file_id: str) -> bool:
    """Returns True if any row with this file_id exists in bronze_artifacts."""
    row = self._conn.execute(
        "SELECT 1 FROM bronze_artifacts WHERE file_id = ? LIMIT 1", (file_id,)
    ).fetchone()
    return row is not None
```

#### Error handling

- A corrupt or unreadable `.json` file is logged as `ERROR` and counted in `failed`. The `.json` is never deleted for failed files, even if `delete_json=True`.
- A failed Parquet write (e.g., disk full) is logged as `ERROR` and counted in `failed`. The partial `.parquet` file (if any) is deleted before returning.
- A failed catalog register is logged as `ERROR` and counted in `failed`. The `.parquet` file is left on disk (it is valid); the catalog row will be inserted on the next run via `INSERT OR IGNORE`.
- After all files are processed, the final `MigrationResult` is printed and the script exits with code `0` if `failed == 0`, else `1`.

---

## Concrete Steps

### Step 0 — Create feature branch

```bash
git checkout -b feature/bronze-compression
```

### Step 1 — Add `pyarrow` dependency

```bash
poetry add pyarrow
poetry show pyarrow
```

Expected: `pyarrow` listed at version `>=14.0`.

### Step 2 — Create `BronzeCatalogDb`

```
src/sbfoundation/bronze/catalog/__init__.py   (empty)
src/sbfoundation/bronze/catalog/bronze_catalog_db.py
```

Add `BronzeArtifactRow` dataclass to `src/sbfoundation/dtos/models.py`.

Verify schema created:
```python
from sbfoundation.bronze.catalog.bronze_catalog_db import BronzeCatalogDb
from pathlib import Path
db = BronzeCatalogDb(Path("/tmp/test_catalog.db"))
# No exception → schema initialised
```

### Step 3 — Create Parquet writer and reader

```
src/sbfoundation/bronze/parquet/__init__.py        (empty)
src/sbfoundation/bronze/parquet/bronze_parquet_writer.py
src/sbfoundation/bronze/parquet/bronze_parquet_reader.py
```

### Step 4 — Update `ResultFileAdapter`

Edit `src/sbfoundation/infra/result_file_adaptor.py`:
- `write()` → `BronzeParquetWriter`
- `read()` → dispatch on extension

### Step 5 — Update `RunRequest`

Edit `src/sbfoundation/run/dtos/run_request.py`, `_filename` property:
- `.json` → `.parquet`

### Step 6 — Wire `BronzeCatalogDb` into `BronzeService`

Edit `src/sbfoundation/bronze/bronze_service.py`:
- Constructor: accept `BronzeCatalogDb`
- After `ResultFileAdapter.write()`: call `catalog.register(result)`
- Cadence/dedup checks: route to `catalog.get_latest_to_date()` / `catalog.get_latest_ingestion_time()`
- Remove calls to `DuckDbOpsRepo` methods that served Bronze cadence gating

Edit `src/sbfoundation/ops/infra/duckdb_ops_repo.py`:
- Remove `get_latest_bronze_to_date()` and `get_latest_bronze_ingestion_time()`

Edit `src/sbfoundation/ops/services/ops_service.py`:
- Remove `insert_bronze_manifest()` and corresponding DuckDB calls

### Step 7 — Update `BronzeBatchReader`

Edit `src/sbfoundation/bronze/bronze_batch_reader.py`:
- Load artifacts from `BronzeCatalogDb.list_promotable()`
- Deserialize via `BronzeParquetReader`

### Step 8 — Migration utility

Create `src/sbfoundation/maintenance/bronze_compress_migration.py` per Phase 4 design above.

Dry-run first to verify discovery and output format:

```bash
python src/sbfoundation/maintenance/bronze_compress_migration.py --dry-run
```

Expected output (no files written):
```
[bronze-migrate] DRY RUN — found 3842 .json files
[bronze-migrate] DONE — total=3842 converted=0 skipped=0 failed=0 deleted=0
```

Then run the full conversion (keep `.json` files until Tier 4 acceptance is confirmed):
```bash
python src/sbfoundation/maintenance/bronze_compress_migration.py
```

Expected output:
```
[bronze-migrate]  100 / 3842 — converted=100 skipped=0 failed=0
...
[bronze-migrate] DONE — total=3842 converted=3842 skipped=0 failed=0 deleted=0
```

Exit code must be `0`. Any `failed > 0` requires investigation before proceeding.

After Tier 4 acceptance is confirmed, delete the originals:
```bash
python src/sbfoundation/maintenance/bronze_compress_migration.py --delete-json
```

### Step 9 — Tests

```
tests/unit/bronze/test_bronze_catalog_db.py         — insert idempotency, has_file, latest_to_date, list_promotable
tests/unit/bronze/test_bronze_parquet_writer.py     — round-trip: BronzeResult → Parquet → metadata + rows
tests/unit/bronze/test_bronze_parquet_reader.py     — read envelope + content from known fixture file
tests/unit/bronze/test_bronze_compress_migration.py — dry_run produces no files; corrupt JSON counted as failed;
                                                       idempotent re-run skips already-migrated files;
                                                       delete_json removes .json only after confirmed .parquet write
tests/e2e/test_bronze_compression_e2e.py            — full run → .parquet created + catalog.db row inserted
```

---

## Validation and Acceptance

### Tier 1 — Quick checks (< 1 minute, no DB/network)

```bash
# Import sanity
python -c "from sbfoundation.bronze.catalog.bronze_catalog_db import BronzeCatalogDb; print('OK')"
python -c "from sbfoundation.bronze.parquet.bronze_parquet_writer import BronzeParquetWriter; print('OK')"
python -c "from sbfoundation.bronze.parquet.bronze_parquet_reader import BronzeParquetReader; print('OK')"

# Type check
mypy src/sbfoundation/bronze/catalog/ src/sbfoundation/bronze/parquet/

# Unit tests
pytest tests/unit/bronze/ -v
```

Expected: all pass, no import errors, no mypy errors.

### Tier 2 — DB checks (local SQLite + Parquet, no network)

```python
# After running migration utility on existing .json files:
import sqlite3
db = sqlite3.connect("data/bronze/catalog.db")
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(tables)
# Expected: [('bronze_artifacts',)]

count = db.execute("SELECT COUNT(*) FROM bronze_artifacts").fetchone()[0]
print(count)
# Expected: N > 0 (one row per existing Bronze file)

# Check a Parquet file
import pyarrow.parquet as pq, pathlib
f = next(pathlib.Path("data/bronze").rglob("*.parquet"))
meta = pq.read_metadata(f)
print(dict(meta.metadata))
# Expected: keys include b'sbf.run_id', b'sbf.file_id', b'sbf.domain', etc.
print(meta.num_rows)
# Expected: > 0 for a non-empty dataset
```

DuckDB `ops.file_ingestions` check — confirm Silver promotion still works:
```python
import duckdb
conn = duckdb.connect("data/db/sbfoundation.duckdb")
rows = conn.execute("SELECT COUNT(*) FROM ops.file_ingestions WHERE silver_can_promote=true").fetchone()
print(rows)
# Expected: same count as before (unchanged)
```

### Tier 3 — Integration / dry-run check (no live API writes)

```bash
# Edit __main__ block: enable_silver=False, enable_gold=False, single date
python src/sbfoundation/eod/eod_service.py
```

Expected:
- `bronze_files_passed=N` (N > 0) in logs
- `data/bronze/<domain>/.../*.parquet` files created
- `data/bronze/catalog.db` populated with matching rows
- No errors from DuckDB `ops.*` for Bronze cadence gating
- DuckDB `ops.file_ingestions` untouched by Bronze phase

### Tier 4 — Post-live-run checks (real pipeline, real API)

1. Re-run the same date → `catalog.db` row count unchanged (`INSERT OR IGNORE` is idempotent); same Parquet file overwritten with identical content.
2. Enable Silver promotion → `ops.file_ingestions` updated in DuckDB as before; `silver_rows_created > 0`.
3. Gold build completes without errors.
4. No `.json` files created for new ingestions after go-live.
5. Migration utility converts all pre-existing `.json` files → `.parquet` + SQLite rows without errors.
6. DuckDB `ops.file_ingestions` Silver promotion rows remain intact and queryable.

---

## Idempotence and Recovery

- **Parquet write**: `file_id` is the filename stem — same `file_id` always maps to the same path. Re-running overwrites with identical content (deterministic content).
- **SQLite register**: `INSERT OR IGNORE` — silently skips duplicate `(run_id, file_id)`. No data loss on replay.
- **Migration**: checks `.parquet` existence before writing; `INSERT OR IGNORE` for catalog rows. Safe to interrupt and restart.
- **Rollback**: the `.json` files are preserved by default (`delete_json=False`). `ResultFileAdapter.read()` retains the JSON fallback. Rolling back means reverting `RunRequest._filename` and `ResultFileAdapter.write()` — no data is lost.
- **DuckDB ops integrity**: DuckDB `ops` tables are never touched by this ExecPlan's Bronze path changes. Any rollback is isolated to the Bronze layer.

---

## Artifacts and Notes

_Populated as implementation proceeds._

---

## Interfaces and Dependencies

### New dependencies

| Package | Purpose | Version constraint |
|---|---|---|
| `pyarrow` | Parquet read/write | `>=14.0` |

`sqlite3` is Python standard library — no install required.

### New components

| Component | File | Role |
|---|---|---|
| `BronzeCatalogDb` | `bronze/catalog/bronze_catalog_db.py` | SQLite write-once artifact registry |
| `BronzeArtifactRow` | `dtos/models.py` | Value object — one row from `bronze_artifacts` |
| `BronzeParquetWriter` | `bronze/parquet/bronze_parquet_writer.py` | Parquet serializer for BronzeResult |
| `BronzeParquetReader` | `bronze/parquet/bronze_parquet_reader.py` | Parquet deserializer → content rows + envelope |
| `BronzeCompressMigration` | `maintenance/bronze_compress_migration.py` | One-time JSON→Parquet + catalog back-fill |

### Modified interfaces

| Interface | Change |
|---|---|
| `ResultFileAdapter.write(result)` | Writes `.parquet` instead of `.json` |
| `ResultFileAdapter.read(path)` | Dispatches on extension; `.json` fallback retained |
| `RunRequest.bronze_relative_filename` | Returns `.parquet` path |
| `BronzeService.__init__` | Accepts `BronzeCatalogDb` for Bronze cadence gating |
| `BronzeService._process_run_request` | Calls `catalog.register()` after file write |
| `BronzeBatchReader` | Loads artifacts from SQLite; deserializes via Parquet reader |

### Preserved interfaces (no change)

| Interface | Reason |
|---|---|
| `DatasetInjestion` DTO | Silver promotion DTO — unchanged |
| `OpsService.upsert_silver_ingestion()` | Silver promotion path — unchanged |
| `DuckDbOpsRepo` Silver methods | Silver promotion — unchanged |
| `ops.file_ingestions` (DuckDB) | Silver promotion tracking — unchanged |
| `ops.dataset_watermarks` (DuckDB) | Silver cadence watermarks — unchanged |
| `BronzeResult` | Source of truth for Parquet metadata — read-only use |
| Silver, Gold schemas | Out of scope — unchanged |

---

## Outcomes & Retrospective

_Populated when ExecPlan closes._
