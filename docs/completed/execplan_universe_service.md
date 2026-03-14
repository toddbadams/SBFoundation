# ExecPlan: Universe Service — Bronze + Silver Data Product

**Version**: 1.0
**Created**: 2026-03-02
**Author**: Claude / Todd
**Branch**: `feature/universe-service`

---

## Purpose / Big Picture

SBFoundation needs to know **which instruments to ingest data for**. Today, `UniverseDefinition` is a thin struct (country, exchanges, market-cap bounds) and the screener runs globally over all exchanges × all sectors regardless of universe context.

This ExecPlan delivers:

1. A **`sbuniverse` Python package** (`src/sbuniverse/`) as a new namespace in this repo — the authoritative source for universe definitions and the universe service.
2. An **expanded `UniverseDefinition`** that carries all FMP Company Screener eligibility filter parameters, enabling universe-scoped, server-side-filtered screener ingestion.
3. **Per-universe screener ingestion**: replace the global exchange×sector Cartesian product with per-universe, exchange-scoped calls that pass eligibility filters as query params.
4. A **versioned universe snapshot** Silver table: each nightly run produces `silver.universe_snapshot` (metadata) and `silver.universe_member` (member symbols), keyed by `(universe_name, as_of_date, filter_hash)` for full reproducibility.
5. **Derived eligibility metrics** Silver table (`silver.universe_derived_metrics`): computed market cap, 30d/90d avg dollar volume, active-trading flag, and data coverage score — enabling the ingestion pipeline to gate on data quality.
6. A **`sbuniverse.api.UniverseAPI`** public entry point callable from VS Code debug and CLI, that exposes `tickers(universe_name, as_of_date)` for the ingestion pipeline and snapshot queries for auditing.

**What this does NOT include** (downstream Gold project):
- Selection filters (factor screens, liquidity gates for strategy construction)
- User-facing filter API returning metadata + diffs
- Star-schema universe dimension tables

---

## Progress

- [x] Step 0 — Create feature branch (`feature/universe-service`) — 2026-03-02
- [x] Step 1 — Create `src/sbuniverse/` package skeleton + update `pyproject.toml` — 2026-03-02
- [x] Step 2 — Expand `UniverseDefinition` with all FMP screener eligibility params — 2026-03-02
- [x] Step 3 — Add migration: `silver.universe_snapshot` + `silver.universe_member` tables — 2026-03-02
- [x] Step 4 — Add migration: `silver.universe_derived_metrics` table — 2026-03-02
- [x] Step 5 — Modify screener ingestion to run per-universe with eligibility filter params — 2026-03-02
- [x] Step 6 — Add universe snapshot materialization step (after screener ingestion) — 2026-03-02
- [x] Step 7 — Add derived metrics compute step (after technicals ingestion) — 2026-03-02
- [x] Step 8 — Implement `sbuniverse.api.UniverseAPI` with `tickers()` + CLI entry point — 2026-03-02
- [x] Step 9 — Update `api.py` `_get_filtered_universe` to use `silver.universe_member` — 2026-03-02
- [x] Step 10 — Unit tests (27 new + 418 total passing) — 2026-03-02
- [x] Step 11 — Validation + acceptance — **APPROVED 2026-03-02**

---

## Surprises & Discoveries

- **FMP 1000-row cap**: The existing `_run_market_screener` already works around this by splitting on exchange × sector. Per-universe calls with server-side eligibility filters may still breach the cap for large universes (e.g. US_ALL_CAP covers 300M+ market cap across all exchanges). **Decision**: retain per-exchange iteration within each universe (see Decision Log).

- **Existing screener already uses dynamic discriminators**: `_run_market_screener` patches `recipe.query_vars` and `recipe.discriminator` at runtime using `copy.copy(recipe)`. The same pattern can be used for per-universe calls with minimal structural change.

- **`fmp_market_screener` key_col is only `symbol`**: Adding `universe_name` to the key changes the idempotency semantics. Rather than modify the existing table, universe membership is materialized separately into `silver.universe_member` (see Decision Log).

- **`universe_definitions.py` is imported in `api.py` and throughout the codebase**: The existing `UniverseDefinition` dataclass must remain importable from `sbfoundation.universe_definitions` for backward compatibility. It will re-export from `sbuniverse`.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-02 | Retain per-exchange iteration within each universe | FMP caps screener at 1000 rows/request. Per-exchange splits keep each request well under this limit even for large universes. |
| 2026-03-02 | `silver.universe_member` as separate table, not a column on `fmp_market_screener` | `fmp_market_screener` key is `symbol`; adding `universe_name` to the key requires a destructive migration and breaks the existing three-tier fallback. Separate table is additive and non-breaking. |
| 2026-03-02 | `sbuniverse` as new namespace in existing `pyproject.toml` | Single installable package, no separate versioning needed at this stage. Clean namespace separation. |
| 2026-03-02 | Keep `sbfoundation.universe_definitions` as a re-export shim | Avoids breaking all existing callers (`api.py`, tests, downstream consumers). |
| 2026-03-02 | Derived metrics stored in `silver.universe_derived_metrics` | Rolling averages (30d/90d ADTV) are expensive to recompute on-the-fly. Persisting them enables fast `tickers()` calls and auditable eligibility gates. |
| 2026-03-02 | Gold layer (selection filters, user API) is downstream | SBFoundation provides Bronze + Silver only. `tickers()` serves the ingestion pipeline, not strategy construction. |

---

## Outcomes & Retrospective

**Status**: Complete and approved — 2026-03-02

All 11 steps delivered as planned. Key outcomes:
- `sbuniverse` package added with `UniverseAPI`, expanded `UniverseDefinition`, and `UNIVERSE_REGISTRY` of 6 universes
- Per-universe × per-exchange market screener replaces the old exchange × sector Cartesian product
- `silver.universe_snapshot` and `silver.universe_member` tables provide versioned, reproducible universe membership
- `silver.universe_derived_metrics` table added for computed eligibility metrics
- `sbfoundation.universe_definitions` backward-compat shim preserved
- 418 unit tests passing (27 new in `tests/unit/sbuniverse/`)

**Post-approval fixes** (also committed on this branch):
- `api.py`: fixed `DatasetService(today=None)` — `UniverseService` now resolved before `DatasetService` so `today` is always a non-None `str`
- `silver.fmp_market_screener`: added `discriminator` to `key_cols` and `dto_schema`; migration `20260302_003` adds the column; `SilverService._promote_row` injects file-level discriminator when declared as a key column
- `duckdb_bootstrap.py`: removed unguarded `CHECKPOINT` from `close()` to prevent indefinite WAL-lock hangs

---

## Context and Orientation

### Key existing files

| File | Role |
|------|------|
| `src/sbfoundation/universe_definitions.py` | Current thin `UniverseDefinition` dataclass + UNIVERSE_REGISTRY |
| `src/sbfoundation/services/universe_service.py` | Current `UniverseService` — returns ticker lists from silver |
| `src/sbfoundation/infra/universe_repo.py` | `UniverseRepo` — DuckDB queries for universe data |
| `src/sbfoundation/api.py` | `SBFoundationAPI` + `RunCommand`; `_run_market_screener`, `_get_filtered_universe` |
| `config/dataset_keymap.yaml` (line ~7682) | `market-screener` dataset definition |
| `db/migrations/` | SQL migration files |

### Current screener ingestion flow

```
_handle_market()
  └─ _run_market_screener()
       ├─ Load all exchange codes from silver.fmp_market_exchanges
       ├─ Load all sector names from silver.fmp_market_sectors
       ├─ For each (exchange × sector):
       │    patch recipe.query_vars = {exchange, sector}
       │    patch recipe.discriminator = "{exchange}-{sector}"
       └─ BronzeService.execute_requests() → silver.fmp_market_screener
```

### Current universe ticker resolution

```
_get_filtered_universe(command)
  └─ UniverseService.get_filtered_tickers(exchanges, countries, market_cap_bounds)
       └─ UniverseRepo — three-tier fallback:
            1. silver.fmp_market_screener (WHERE exchange IN (...) AND market_cap BETWEEN ...)
            2. silver.fmp_company_profile JOIN fmp_stock_list
            3. All silver.fmp_stock_list symbols
```

### Target state

```
_handle_market()
  └─ _run_market_screener_per_universe()          ← MODIFIED
       ├─ For each UniverseDefinition in UNIVERSE_REGISTRY:
       │    For each exchange in ud.exchanges:
       │      query_vars = ud.to_screener_params() | {exchange: exchange}
       │      discriminator = "{universe_name}-{exchange}"
       └─ BronzeService → silver.fmp_market_screener (unchanged)
       └─ _materialize_universe_snapshots()        ← NEW
            ├─ For each universe: aggregate silver.fmp_market_screener
            ├─ Compute filter_hash from UniverseDefinition
            └─ UPSERT into silver.universe_snapshot + silver.universe_member

_get_filtered_universe(command)
  └─ Query silver.universe_member                  ← SIMPLIFIED
       WHERE universe_name = ud.name AND as_of_date = latest
```

---

## Plan of Work

### Step 0 — Feature branch

```bash
git checkout -b feature/universe-service
```

### Step 1 — `src/sbuniverse/` package skeleton

Create the following structure:

```
src/sbuniverse/
  __init__.py
  api.py                         ← UniverseAPI + CLI entry point
  universe_definition.py         ← Expanded UniverseDefinition (full eligibility params)
  universe_definitions.py        ← UNIVERSE_REGISTRY with expanded definitions
  infra/
    __init__.py
    universe_repo.py             ← New repo (universe_snapshot, universe_member queries)
  services/
    __init__.py
    universe_service.py          ← New UniverseService (tickers(), snapshot())
    derived_metrics_service.py   ← Derived metrics compute (ADTV, market cap, coverage score)
```

Update `pyproject.toml`:
```toml
packages = [
  {include = "sbfoundation", from = "src"},
  {include = "sbuniverse",   from = "src"},
]
```

Update `src/sbfoundation/universe_definitions.py` to re-export from `sbuniverse`:
```python
# Backward-compat shim — do not remove
from sbuniverse.universe_definition import UniverseDefinition
from sbuniverse.universe_definitions import UNIVERSE_REGISTRY, US_ALL_CAP, ...
__all__ = [...]
```

### Step 2 — Expand `UniverseDefinition`

New `sbuniverse/universe_definition.py` — `UniverseDefinition` gains all FMP Company Screener eligibility params as optional fields, plus a `to_screener_params()` method that emits a `dict[str, Any]` of non-None filter values ready for `query_vars`.

**New fields** (all optional / `None` = no filter):

```python
@dataclass(frozen=True)
class UniverseDefinition:
    # Identity
    name: str
    description: str = ""

    # Geography & listing (eligibility)
    country: str | None = None
    exchanges: list[str] = field(default_factory=list)
    is_etf: bool | None = None
    is_fund: bool | None = None
    is_actively_trading: bool | None = True  # default True
    include_all_share_classes: bool | None = None

    # Market cap (eligibility)
    market_cap_more_than: float | None = None
    market_cap_lower_than: float | None = None

    # Price (eligibility)
    price_more_than: float | None = None
    price_lower_than: float | None = None

    # Volume (eligibility)
    volume_more_than: float | None = None
    volume_lower_than: float | None = None

    # Beta (eligibility)
    beta_more_than: float | None = None
    beta_lower_than: float | None = None

    # Dividend (eligibility)
    dividend_more_than: float | None = None
    dividend_lower_than: float | None = None

    # Sector / industry (eligibility, or None = all)
    sector: str | None = None
    industry: str | None = None

    # Request limit per exchange call
    limit: int = 1000

    def to_screener_params(self) -> dict[str, Any]:
        """Emit non-None fields as FMP Company Screener query params."""
        ...

    def filter_hash(self) -> str:
        """SHA-256 of canonical JSON representation of all filter params."""
        ...

    # Backward-compat aliases
    @property
    def min_market_cap_usd(self) -> float | None:
        return self.market_cap_more_than

    @property
    def max_market_cap_usd(self) -> float | None:
        return self.market_cap_lower_than
```

Update `sbuniverse/universe_definitions.py` with all existing universe constants, expanded with new fields. Re-export from `sbfoundation/universe_definitions.py`.

### Step 3 — SQL migrations: `universe_snapshot` + `universe_member`

New file: `db/migrations/20260302_001_add_universe_snapshot_and_member.sql`

```sql
CREATE TABLE IF NOT EXISTS silver.universe_snapshot (
    universe_name       VARCHAR      NOT NULL,
    as_of_date          DATE         NOT NULL,
    filter_hash         VARCHAR(64)  NOT NULL,
    member_count        INTEGER      NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    run_id              VARCHAR      NOT NULL,
    PRIMARY KEY (universe_name, as_of_date)
);

CREATE TABLE IF NOT EXISTS silver.universe_member (
    universe_name       VARCHAR      NOT NULL,
    as_of_date          DATE         NOT NULL,
    filter_hash         VARCHAR(64)  NOT NULL,
    symbol              VARCHAR      NOT NULL,
    run_id              VARCHAR      NOT NULL,
    ingested_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (universe_name, as_of_date, symbol)
);
```

### Step 4 — SQL migration: `universe_derived_metrics`

New file: `db/migrations/20260302_002_add_universe_derived_metrics.sql`

```sql
CREATE TABLE IF NOT EXISTS silver.universe_derived_metrics (
    symbol                  VARCHAR     NOT NULL,
    as_of_date              DATE        NOT NULL,
    computed_market_cap     DOUBLE      NULL,  -- price × shares_outstanding
    avg_dollar_volume_30d   DOUBLE      NULL,  -- 30-day avg(close × volume)
    avg_dollar_volume_90d   DOUBLE      NULL,  -- 90-day avg(close × volume)
    is_actively_trading     BOOLEAN     NULL,
    data_coverage_score     DOUBLE      NULL,  -- 0.0–1.0: fraction of expected bars present
    run_id                  VARCHAR     NOT NULL,
    ingested_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, as_of_date)
);
```

### Step 5 — Modify screener ingestion to be per-universe

In `src/sbfoundation/api.py`, replace `_run_market_screener()` logic:

- **Before**: iterate all exchanges in silver × all sectors in silver
- **After**: iterate each `UniverseDefinition` in `UNIVERSE_REGISTRY` × that universe's `exchanges`, pass `ud.to_screener_params()` as `query_vars`, discriminator = `"{ud.name}-{exchange}"`

Screener calls still go to `silver.fmp_market_screener` (key = `symbol`). This preserves the existing table as a deduped security master across all universes. Per-universe membership is materialized separately in Step 6.

> Note: sector is NOT passed as a per-request filter (unlike current approach). The screener endpoint returns all sectors for the given exchange+eligibility params. Sector-based selection is a downstream Gold concern.

### Step 6 — Universe snapshot materialization step

New method `_materialize_universe_snapshots()` in `api.py`, called after screener Bronze/Silver promotion:

For each `UniverseDefinition` in `UNIVERSE_REGISTRY`:
1. Query `silver.fmp_market_screener` for symbols matching this universe's discriminator prefix (`"{ud.name}-*"`) ingested in the current run.
2. Compute `filter_hash = ud.filter_hash()`.
3. UPSERT into `silver.universe_snapshot` (universe_name, as_of_date, filter_hash, member_count, run_id).
4. UPSERT all symbols into `silver.universe_member` (universe_name, as_of_date, filter_hash, symbol, run_id).

Implement via `sbuniverse.infra.universe_repo.UniverseRepo` methods called from a new `sbuniverse.services.universe_service.UniverseService.materialize_snapshot()`.

### Step 7 — Derived metrics compute step

New method `_compute_derived_metrics()` in `api.py`, called after technicals/price ingestion is complete:

For each symbol in the day's universe:
1. **Computed market cap**: `price × shares_outstanding` from silver tables (if available); else use screener's `market_cap`.
2. **30d/90d ADTV**: `AVG(close × volume)` over trailing 30 and 90 trading days from `silver.fmp_price_eod` (or equivalent).
3. **is_actively_trading**: from screener's `isActivelyTrading` field or survival logic.
4. **data_coverage_score**: `COUNT(DISTINCT date) / EXPECTED_TRADING_DAYS` for the trailing 1-year window.

Results UPSERT into `silver.universe_derived_metrics` keyed by `(symbol, as_of_date)`.

Implement in `sbuniverse/services/derived_metrics_service.py`.

### Step 8 — `sbuniverse.api.UniverseAPI` + CLI

`src/sbuniverse/api.py`:

```python
class UniverseAPI:
    def tickers(
        self,
        universe_name: str,
        as_of_date: date | None = None,   # None = latest snapshot
    ) -> list[str]: ...

    def snapshot_info(
        self,
        universe_name: str,
        as_of_date: date | None = None,
    ) -> UniverseSnapshot | None: ...

    def run_universe_build(
        self,
        universe_names: list[str] | None = None,  # None = all in UNIVERSE_REGISTRY
    ) -> None: ...
```

CLI entry point (`if __name__ == "__main__":`):

```bash
python -m sbuniverse.api tickers --universe us_large_cap
python -m sbuniverse.api snapshot --universe us_large_cap --date 2026-03-01
python -m sbuniverse.api run
```

VS Code launch config (`.vscode/launch.json` entry):

```json
{
  "name": "sbuniverse: run universe build",
  "type": "debugpy",
  "request": "launch",
  "module": "sbuniverse.api",
  "args": ["run"],
  "cwd": "${workspaceFolder}"
}
```

### Step 9 — Update `api.py` `_get_filtered_universe`

After `silver.universe_member` is populated, simplify `_get_filtered_universe`:

```python
def _get_filtered_universe(self, command: RunCommand, run_id: str) -> list[str]:
    ud = command.universe_definition
    if ud is None:
        return []
    # Primary: query silver.universe_member for latest snapshot
    tickers = self._universe_service.tickers(ud.name)
    if tickers:
        return tickers[:command.ticker_limit] if command.ticker_limit > 0 else tickers
    # Fallback: existing three-tier repo query (bootstrap / cold start)
    return self._universe_service.get_filtered_tickers(...)
```

Keep the existing three-tier fallback in `UniverseRepo` as a cold-start bootstrap path.

### Step 10 — Unit tests

- `tests/unit/sbuniverse/test_universe_definition.py`
  - `to_screener_params()` emits only non-None params
  - `filter_hash()` is stable and changes when params change
  - Backward-compat aliases (`min_market_cap_usd`, `max_market_cap_usd`)

- `tests/unit/sbuniverse/test_universe_repo.py`
  - UPSERT into `universe_member` is idempotent
  - `tickers()` returns latest snapshot members

- `tests/unit/sbuniverse/test_derived_metrics_service.py`
  - ADTV computation with known price data fixture

---

## Concrete Steps

> Before any code: create the feature branch.

```bash
git checkout -b feature/universe-service
```

**1. Package skeleton**

```bash
mkdir -p src/sbuniverse/infra src/sbuniverse/services
touch src/sbuniverse/__init__.py
touch src/sbuniverse/api.py
touch src/sbuniverse/universe_definition.py
touch src/sbuniverse/universe_definitions.py
touch src/sbuniverse/infra/__init__.py
touch src/sbuniverse/infra/universe_repo.py
touch src/sbuniverse/services/__init__.py
touch src/sbuniverse/services/universe_service.py
touch src/sbuniverse/services/derived_metrics_service.py
```

Edit `pyproject.toml` — add `{include = "sbuniverse", from = "src"}` to `packages`.

**2. Expand UniverseDefinition** — write `sbuniverse/universe_definition.py` and `universe_definitions.py`. Update `sbfoundation/universe_definitions.py` shim.

**3. SQL migrations** — create two new `.sql` files in `db/migrations/`. Run via DuckDB bootstrap migration runner.

**4. Modify `_run_market_screener`** — swap the exchange×sector loop for per-universe×per-exchange loop using `UNIVERSE_REGISTRY`.

**5. Add `_materialize_universe_snapshots`** — implement and call from `_handle_market()` after screener completes.

**6. Add `_compute_derived_metrics`** — implement and call from `SBFoundationAPI.run()` after technicals domain.

**7. Implement `UniverseAPI`** — write `sbuniverse/api.py` with `tickers()`, `snapshot_info()`, `run_universe_build()`, and `__main__` CLI.

**8. Update `_get_filtered_universe`** — simplify with primary path via `silver.universe_member`.

**9. Tests** — write unit tests as described above.

**10. Verify**

```bash
poetry run pytest tests/unit/sbuniverse/ -v
poetry run mypy src/sbuniverse/ --strict
poetry run python -m sbuniverse.api tickers --universe us_large_cap
```

---

## Validation and Acceptance

### Quick checks (no DB required, < 1 minute)

**1. Unit tests**
```bash
python -m pytest tests/unit/sbuniverse/ -v
```
Expected: 27 passed, 0 failed.

```bash
python -m pytest tests/unit/ -v
```
Expected: 418 passed, 0 failed.

**2. Backward-compat shim**
```bash
python -c "from sbfoundation.universe_definitions import US_LARGE_CAP, UniverseDefinition, UNIVERSE_REGISTRY; print(US_LARGE_CAP.name, len(UNIVERSE_REGISTRY))"
```
Expected: `us_large_cap 6`

**3. `to_screener_params()` for each universe**
```bash
python -c "
from sbuniverse.universe_definitions import UNIVERSE_REGISTRY
for name, ud in UNIVERSE_REGISTRY.items():
    params = ud.to_screener_params()
    print(f'{name}: exchanges={ud.exchanges} params={params}')
    assert 'exchange' not in params, 'exchange must NOT appear in screener params'
    assert 'isEtf' in params, 'isEtf must be present'
print('OK')
"
```
Expected: 6 lines printed, `OK` at the end.

**4. `filter_hash()` stability**
```bash
python -c "
from sbuniverse.universe_definitions import US_LARGE_CAP
h1 = US_LARGE_CAP.filter_hash()
h2 = US_LARGE_CAP.filter_hash()
assert h1 == h2 and len(h1) == 64
print('hash stable:', h1[:16], '...')
"
```
Expected: `hash stable: <16 hex chars> ...`

**5. CLI entry point**
```bash
python -m sbuniverse.api list
```
Expected: 6 universe names printed with descriptions.

```bash
python -m sbuniverse.api tickers --universe us_large_cap
```
Expected: Ticker list if a snapshot exists, or `No snapshot found for universe='us_large_cap'` — both are correct before a market run.

**6. SQL migration files present**
```bash
python -c "
import pathlib
for f in sorted(pathlib.Path('db/migrations').glob('20260302_*.sql')):
    print(f.name)
    print(f.read_text()[:80], '...')
    print()
"
```
Expected: Two files — `20260302_001_add_universe_snapshot_and_member.sql` and `20260302_002_add_universe_derived_metrics.sql`.

---

### DB checks (requires migrations to have run)

**7. Tables created**
```bash
python -c "
from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
db = DuckDbBootstrap()
conn = db.connect()
for t in ['universe_snapshot', 'universe_member', 'universe_derived_metrics']:
    n = conn.execute(f\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='silver' AND table_name='{t}'\").fetchone()[0]
    print(f'silver.{t}: {\"EXISTS\" if n else \"MISSING\"}')
db.close()
"
```
Expected: `EXISTS` for all three tables.

**8. `UniverseAPI` instantiates cleanly**
```bash
python -c "
from sbuniverse.api import UniverseAPI
api = UniverseAPI()
snap = api.snapshot_info('us_large_cap')
print('snapshot:', snap)
tickers = api.tickers('us_large_cap')
print('tickers count:', len(tickers))
api.close()
"
```
Expected: `snapshot: None` and `tickers count: 0` before any market run — no exception.

---

### Integration check (key gate — requires FMP API key)

**9. Market domain dry run**
```bash
python -c "
from sbfoundation.api import SBFoundationAPI, RunCommand
from sbfoundation.universe_definitions import US_LARGE_CAP
api = SBFoundationAPI()
result = api.run(RunCommand(
    domain='market',
    enable_bronze=False,
    enable_silver=False,
    concurrent_requests=1,
    universe_definition=US_LARGE_CAP,
))
print('run_id:', result.run_id)
print('records_written:', result.records_written)
print('records_failed:', result.records_failed)
"
```
Expected: Runs without error. `records_written=0` (dry run). Log output mentions `market-screener: 6 universes × per-exchange = N requests` (not the old `exchanges × sectors` message).

---

### Post-live-run checks

10. `silver.universe_snapshot` shows `member_count > 0` for each of the 6 universes.
11. `python -m sbuniverse.api tickers --universe us_large_cap` prints tickers to stdout.
12. `silver.universe_derived_metrics` contains `is_actively_trading`, `avg_dollar_volume_30d`, `data_coverage_score` rows after a technicals run.
13. Re-running the same date is idempotent — `universe_member` and `universe_snapshot` row counts are stable on replay.

---

## Idempotence and Recovery

- All Silver writes use UPSERT (MERGE) keyed on `PRIMARY KEY` — safe to replay.
- Bronze files are append-only; a failed run creates new files on retry (audit-first).
- Migration SQL files use `CREATE TABLE IF NOT EXISTS` — safe to re-apply.
- If `_materialize_universe_snapshots` fails mid-way: re-run the same day's `_handle_market` — existing `universe_member` rows for that `(universe_name, as_of_date)` will be overwritten idempotently.
- To roll back the schema: drop `silver.universe_snapshot`, `silver.universe_member`, `silver.universe_derived_metrics`. The existing `silver.fmp_market_screener` is unmodified.

---

## Artifacts and Notes

### Test run — 2026-03-02

```
27 new sbuniverse tests: 27 passed
Full unit suite: 418 passed, 0 failed, 2 deprecation warnings (unrelated)
```

### Circular import discovery

`sbfoundation/__init__.py` eagerly re-exports `SBFoundationAPI`, which caused a
circular dependency when `api.py` imported `sbuniverse.api` at module level
(the chain: `sbfoundation.__init__` → `sbfoundation.api` → `sbuniverse.api` →
`sbuniverse.infra.universe_repo` → `sbfoundation.infra.duckdb_bootstrap` →
`sbfoundation` (partially initialized) → error).

**Fix**: `UniverseAPI` and `DerivedMetricsService` are imported lazily inside
`SBFoundationAPI.__init__` and `_compute_derived_metrics()` respectively.

---

## Interfaces and Dependencies

### New public types

```python
# sbuniverse.universe_definition
@dataclass(frozen=True)
class UniverseDefinition:
    name: str
    exchanges: list[str]
    country: str | None
    is_actively_trading: bool | None
    market_cap_more_than: float | None
    market_cap_lower_than: float | None
    price_more_than: float | None
    price_lower_than: float | None
    volume_more_than: float | None
    volume_lower_than: float | None
    beta_more_than: float | None
    beta_lower_than: float | None
    dividend_more_than: float | None
    dividend_lower_than: float | None
    sector: str | None
    industry: str | None
    is_etf: bool | None
    is_fund: bool | None
    include_all_share_classes: bool | None
    limit: int

    def to_screener_params(self) -> dict[str, Any]: ...
    def filter_hash(self) -> str: ...

    # Compat aliases
    @property
    def min_market_cap_usd(self) -> float | None: ...
    @property
    def max_market_cap_usd(self) -> float | None: ...

# sbuniverse.api
class UniverseAPI:
    def tickers(self, universe_name: str, as_of_date: date | None = None) -> list[str]: ...
    def snapshot_info(self, universe_name: str, as_of_date: date | None = None) -> UniverseSnapshot | None: ...
    def run_universe_build(self, universe_names: list[str] | None = None) -> None: ...

@dataclass
class UniverseSnapshot:
    universe_name: str
    as_of_date: date
    filter_hash: str
    member_count: int
    created_at: datetime
    run_id: str
```

### External dependencies

- **FMP Company Screener endpoint**: `GET /company-screener?exchange=NYSE&country=US&marketCapMoreThan=2000000000&isActivelyTrading=true&limit=1000`
  - 1000-row cap per request — mitigated by per-exchange iteration
  - Existing `plans: [basic, starter, premium, ultimate]` apply
- **DuckDB `>=1.4.3`**: UPSERT (`INSERT OR REPLACE` / `MERGE`) syntax
- **`hashlib.sha256`**: for `filter_hash()` (stdlib)
- **`silver.fmp_price_eod`** (or equivalent): required for ADTV computation in derived metrics — skip gracefully if not yet populated
