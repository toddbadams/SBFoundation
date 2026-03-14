# ExecPlan: Remove Instrument Domain — Move Lists to Market, Standalone Ticker Domains

**Version**: 1.3
**Created**: 2026-02-18
**Completed**: 2026-02-18
**Author**: Claude Code
**Status**: Complete — all steps implemented, 270 unit tests passing

---

## Purpose / Big Picture

The `instrument` domain currently serves two unrelated purposes:
1. **Universe discovery** — loading stock-list, etf-list, index-list, etf-holdings (market reference data)
2. **Ticker-based pipeline orchestration** — sequencing company → fundamentals → technicals after universe loading

This conflation makes the ticker-based domains (company, fundamentals, technicals) impossible to run independently via `RunCommand`. The goal of this ExecPlan is to:

- **Remove** the `instrument` domain entirely
- **Move** `stock-list`, `etf-list`, `index-list`, and `etf-holdings` into the **`market` domain** (they are market structure reference data)
- **Remove** `cryptocurrency-list` and `forex-list` from the `instrument` domain (they already belong to their respective `crypto` and `fx` domains)
- **Make** `company`, `fundamentals`, and `technicals` independently callable via `RunCommand(domain=COMPANY_DOMAIN)` etc., each reading their ticker universe from `silver.fmp_stock_list`
- **Update** `docs/domain_datasets_reference.md` and `README.md` to reflect the new domain structure
- **Remove** `InstrumentCatalogService` and `ops.instrument_catalog` — the service was never called, the table is always empty, and after this change the ticker universe comes from `silver.fmp_stock_list` directly
- **Clean up** `UniverseRepo` and `UniverseService` — remove Gold-layer references (`gold.dim_instrument`) and dead `instrument_catalog` JOIN paths

After this change, the API caller decides what to run. A full pipeline run is composed of sequential `RunCommand` calls: `market` → `economics` → `company` → `fundamentals` → `technicals` → `commodities` → `fx` → `crypto`.

---

## Progress

- [x] Step 1: Update `config/dataset_keymap.yaml` — re-domain the 4 list datasets; remove crypto/forex from instrument ✅ 2026-02-18
- [x] Step 2: Update `src/sbfoundation/settings.py` — remove `INSTRUMENT_DOMAIN`, restructure constants ✅ 2026-02-18
- [x] Step 3: Refactor `src/sbfoundation/api.py` — add `RunCommand.validate()`, new domain handlers, exchange filtering, remove instrument handler ✅ 2026-02-18
- [x] Step 4: Remove `InstrumentCatalogService` and `ops.instrument_catalog` infrastructure ✅ 2026-02-18
- [x] Step 5: Clean up `UniverseRepo` and `UniverseService` ✅ 2026-02-18
- [x] Step 5b: Update `ops_service.py` — remove `enable_new_tickers` / `new_ticker_limit` params from `start_run()` ✅ 2026-02-18
- [x] Step 6: Write drop migration for `ops.instrument_catalog` ✅ 2026-02-18 (filed as `20260218_002`)
- [x] Step 7: Update `docs/domain_datasets_reference.md` ✅ 2026-02-18
- [x] Step 8: Update `README.md` ✅ 2026-02-18
- [x] Step 9: Verify with grep for remaining `INSTRUMENT_DOMAIN` and `instrument_catalog` references; 270 unit tests pass ✅ 2026-02-18

---

## Outcomes & Retrospective

### What Was Achieved
- `instrument` domain fully removed from codebase, YAML, settings, api.py, and all docs
- `stock-list`, `etf-list`, `index-list`, `etf-holdings` moved to `market` domain
- `cryptocurrency-list` re-domained to `crypto`; `forex-list` re-domained to `fx` (YAML only — both were already handled by their correct domain handlers)
- `company`, `fundamentals`, `technicals` are now independently callable via `RunCommand` with `exchanges` required
- `RunCommand.validate()` added — raises `ValueError` immediately on bad domain or missing exchange for ticker-scoped domains
- `_get_exchange_filtered_universe()` added — joins `silver.fmp_stock_list` → `silver.fmp_company_profile` filtered by `exchange_short_name`; falls back to full stock-list with warning if profile not yet populated
- `InstrumentCatalogService` (206 lines, never called) deleted; DDL removed from bootstrap
- `UniverseRepo.get_new_tickers()`, `count_new_tickers()` deleted — queried `gold.dim_instrument` (Gold-layer violation)
- `UniverseRepo.get_update_tickers()` simplified — removed catalog JOIN that always returned nothing
- `ops_service.start_run()` simplified — removed `enable_new_tickers` / `new_ticker_limit` params
- Migration `20260218_002_drop_ops_instrument_catalog.sql` created to drop the table from existing DBs
- `docs/domain_datasets_reference.md` rewritten — 8 domains, market Phase 0 for list datasets, updated flowchart
- `README.md` updated — 8 domains table, corrected execution order description
- **270 unit tests pass, 0 failures**

### Gaps
- Steps 7 and 8 (validation items 5–9 in `Validation and Acceptance`) that require a live DuckDB connection were not run during implementation. The `_get_exchange_filtered_universe()` method and market Phase 0 handlers have unit-test coverage via their logic paths but not live DB smoke tests.
- Migration `20260218_002` must be applied manually to the production DuckDB on Raspberry Pi.

### Lessons Learned
- The `instrument` domain had been silently broken for the entire `INSTRUMENT_DOMAIN` dispatch path: catalog always empty → `get_update_tickers()` returned nothing → `new_tickers()` queried non-existent `gold.dim_instrument` → always returned `[]`. The domain existed in settings and YAML but produced zero output at runtime.
- Exchange filtering was declared as a `RunCommand` field but had no implementation — removing the instrument domain forced its implementation as a real gate.
- The CLAUDE.md §2 Gold-layer hard constraints were the right diagnostic: any method querying `gold.*` in a Bronze+Silver-only project is a defect by definition, not a missing feature.

---

## Surprises & Discoveries

- `_handle_instruments()` in `api.py` performs three distinct duties (stock-list loading, company-profile, domain orchestration). Each must be redistributed cleanly.
- `_get_tickers()` has a special-case `if command.domain == INSTRUMENT_DOMAIN` branch that returns equity tickers from the universe service. After the change, company/fundamentals/technicals must get their universe from `silver.fmp_stock_list` directly (via `_get_universe_from_silver()`).
- `_company_profile()` contains INVALID TICKER backfill logic that must be preserved in the new `_handle_company()` handler.
- `etf-holdings` is a per-ticker dataset (scope: per ETF symbol) — its universe comes from `silver.fmp_etf_list`, not the equity stock-list.
- `cryptocurrency-list` and `forex-list` in `dataset_keymap.yaml` have `domain: instrument` but are already handled by the `crypto` and `fx` domain handlers respectively, which filter by their own domain constant. Their YAML domain field must change to `crypto` and `fx` respectively.
- The `DOMAIN_EXECUTION_ORDER` tuple in settings defines orchestration ordering; `INSTRUMENT_DOMAIN` must be removed from it.
- **`InstrumentCatalogService` is defined but never called.** `sync_from_silver_tables()` has no call site in production code. As a result `ops.instrument_catalog` is always empty at runtime.
- **`UniverseRepo.get_update_tickers()` and `count_update_tickers()` JOIN on `ops.instrument_catalog`** — when the catalog is empty the JOIN eliminates all rows, making `instrument_type`-filtered queries return nothing. This renders the `_get_tickers()` and `_company_profile()` fallback path in `api.py` permanently broken for the INSTRUMENT_DOMAIN.
- **`UniverseRepo.get_new_tickers()` and `count_new_tickers()` query `gold.dim_instrument`** — a Gold-layer table that does not exist in this Bronze+Silver project (hard constraint violation per CLAUDE.md §2 rule 6). These methods always return `[]` or `0`.
- **`UniverseService.new_tickers()`** (called from `_get_tickers()` and `_company_profile()`) delegates to `get_new_tickers()` → queries Gold → always returns `[]`. The instrument domain flow has been silently broken by design.
- After our change, all three ticker-domain handlers read the universe from `silver.fmp_stock_list` directly. `UniverseRepo`'s catalog-JOIN and Gold-layer methods become entirely dead code.
- **`RunCommand` has no validation today.** An invalid domain string silently falls through the `run()` dispatch with no handler called and no error raised — the run starts and closes with zero records processed and no indication of why.
- **Exchange filtering is not implemented**, despite `exchanges` being a field on `RunCommand`. The existing `_domain_recipes()` logs a warning and processes all tickers regardless. With ticker domains now independently callable, unscoped runs over the full stock-list (potentially 10 000+ tickers × 40+ recipes) must be guarded against by requiring at least one exchange.
- **`silver.fmp_company_profile` is the correct join target for exchange filtering** — it carries `exchange_short_name` per ticker. The join must be optional (if the profile table doesn't exist yet, fall back to all stock-list symbols with a warning).

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-02-18 | Move list datasets to `market` | stock-list/etf-list/index-list are market reference data, not ticker behavior drivers |
| 2026-02-18 | Make company/fundamentals/technicals standalone | Enables independent scheduling and retry per domain |
| 2026-02-18 | Universe for ticker domains = `silver.fmp_stock_list` | Stock-list is the canonical equity universe; each domain reads it at startup |
| 2026-02-18 | etf-holdings universe = `silver.fmp_etf_list` | Holdings are per-ETF, not per-equity |
| 2026-02-18 | Preserve `_company_profile()` INVALID TICKER logic | This filtering logic is production-important; must not be dropped |
| 2026-02-18 | Remove `InstrumentCatalogService` entirely | Never called; table always empty; superseded by direct silver reads |
| 2026-02-18 | Remove `UniverseRepo.get_new_tickers()` / `count_new_tickers()` | Query `gold.dim_instrument` — hard Gold-layer violation in this project |
| 2026-02-18 | Simplify `UniverseRepo.get_update_tickers()` — remove catalog JOIN | JOIN on empty table made queries always return nothing; replacement reads `silver.fmp_stock_list` |
| 2026-02-18 | Write a new drop migration for `ops.instrument_catalog` | Table exists in production DBs from migration 20260217_002; must be explicitly dropped |
| 2026-02-18 | Add `RunCommand.validate()` | Silent no-op on bad domain is unacceptable; validation raises early with a clear message |
| 2026-02-18 | Require `exchanges` for company/fundamentals/technicals | Without scoping, a single run could trigger 10 000+ tickers × 40+ recipes; exchanges gate is the minimum viable scope guard |
| 2026-02-18 | Implement exchange filtering via `silver.fmp_company_profile` join | Profile table carries `exchange_short_name`; fall back to full stock-list if profile not yet populated |

---

## Context and Orientation

### Current State (Before)

**`api.py` `run()` dispatch:**
```
domain == INSTRUMENT_DOMAIN → _handle_instruments()
  └─ _load_instrument()        # loads stock-list → silver
  └─ _company_profile()        # loads company-profile per ticker
  └─ _domain_recipes()         # loops: company → fundamentals → technicals
domain == ECONOMICS_DOMAIN  → _handle_economics()
domain == MARKET_DOMAIN     → _handle_market()
domain == COMMODITIES_DOMAIN→ _handle_commodities()
domain == FX_DOMAIN         → _handle_fx()
domain == CRYPTO_DOMAIN     → _handle_crypto()
```

**`dataset_keymap.yaml` instrument domain entries (6 total):**
- `stock-list` — domain: instrument
- `etf-list` — domain: instrument
- `index-list` — domain: instrument
- `cryptocurrency-list` — domain: instrument ← WRONG (should be crypto)
- `forex-list` — domain: instrument ← WRONG (should be fx)
- `etf-holdings` — domain: instrument

**`settings.py`:**
- `INSTRUMENT_DOMAIN = "instrument"` in `DOMAINS` list
- `INSTRUMENT_DOMAIN` first in `DOMAIN_EXECUTION_ORDER`

### Target State (After)

**`api.py` `run()` dispatch:**
```
domain == MARKET_DOMAIN      → _handle_market()       # now includes list datasets
domain == COMPANY_DOMAIN     → _handle_company()      # standalone, reads universe from silver
domain == FUNDAMENTALS_DOMAIN→ _handle_fundamentals() # standalone, reads universe from silver
domain == TECHNICALS_DOMAIN  → _handle_technicals()   # standalone, reads universe from silver
domain == ECONOMICS_DOMAIN   → _handle_economics()    # unchanged
domain == COMMODITIES_DOMAIN → _handle_commodities()  # unchanged
domain == FX_DOMAIN          → _handle_fx()           # unchanged
domain == CRYPTO_DOMAIN      → _handle_crypto()       # unchanged
```

**`dataset_keymap.yaml` changes:**
- `stock-list`, `etf-list`, `index-list`, `etf-holdings` → `domain: market`
- `cryptocurrency-list` → `domain: crypto`
- `forex-list` → `domain: fx`
- **No more `domain: instrument` entries**

**`settings.py`:**
- `INSTRUMENT_DOMAIN` removed from `DOMAINS` and `DOMAIN_EXECUTION_ORDER`
- `STOCK_LIST_DATASET`, `ETF_LIST_DATASET`, `INDEX_LIST_DATASET`, `ETF_HOLDINGS_DATASET` moved to market section
- `CRYPTOCURRENCY_LIST_DATASET` and `FOREX_LIST_DATASET` removed from instrument section (already defined in crypto/fx sections)

### Key Files
| File | Role |
|---|---|
| `config/dataset_keymap.yaml` | Authoritative — domain field per entry |
| `src/sbfoundation/api.py` | Orchestration logic — domain handlers |
| `src/sbfoundation/settings.py` | Constants — DOMAINS, DATASETS, DOMAIN_EXECUTION_ORDER |
| `docs/domain_datasets_reference.md` | Docs — domain overview, dataset tables |
| `README.md` | Docs — overview table, domain list |

---

## Plan of Work

### Step 1 — `config/dataset_keymap.yaml`

For each of the 6 instrument-domain entries, change the `domain:` field:

| Dataset | Old Domain | New Domain |
|---|---|---|
| `stock-list` | instrument | market |
| `etf-list` | instrument | market |
| `index-list` | instrument | market |
| `cryptocurrency-list` | instrument | crypto |
| `forex-list` | instrument | fx |
| `etf-holdings` | instrument | market |

No other YAML fields change (recipes, DTO schemas, silver tables, key_cols all stay the same).

---

### Step 2 — `src/sbfoundation/settings.py`

**Remove** `INSTRUMENT_DOMAIN` from:
- `DOMAINS` list
- `DOMAIN_EXECUTION_ORDER` tuple

**Move** the four dataset constants from the `# ---- INSTRUMENT DATASETS ----` section to the `# ---- MARKET DATASETS ----` section:
```python
# Remove from instrument section:
STOCK_LIST_DATASET = "stock-list"
ETF_LIST_DATASET = "etf-list"
INDEX_LIST_DATASET = "index-list"
ETF_HOLDINGS_DATASET = "etf-holdings"

# Also remove (already defined in crypto/fx sections):
CRYPTOCURRENCY_LIST_DATASET = "cryptocurrency-list"
FOREX_LIST_DATASET = "forex-list"
```

**Add** to the market section:
```python
MARKET_STOCK_LIST_DATASET = "stock-list"
MARKET_ETF_LIST_DATASET = "etf-list"
MARKET_INDEX_LIST_DATASET = "index-list"
MARKET_ETF_HOLDINGS_DATASET = "etf-holdings"
```

**Remove** `INSTRUMENT_DOMAIN` constant and the `INSTRUMENT_TYPE_*` constants that are no longer used in api.py (keep if used elsewhere, verify with grep).

**Remove** `INSTRUMENT_BEHAVIOR_*` constants if unused.

**Update** `DOMAIN_EXECUTION_ORDER`:
```python
DOMAIN_EXECUTION_ORDER: tuple[str, ...] = (
    MARKET_DOMAIN,
    ECONOMICS_DOMAIN,
    COMPANY_DOMAIN,
    FUNDAMENTALS_DOMAIN,
    TECHNICALS_DOMAIN,
    COMMODITIES_DOMAIN,
    FX_DOMAIN,
    CRYPTO_DOMAIN,
)
```

---

### Step 3 — `src/sbfoundation/api.py`

#### 3a. Add `RunCommand.validate()`

Add a `validate()` method to the `RunCommand` dataclass. The method is compatible with `slots=True` — no change to the dataclass declaration is needed.

```python
def validate(self) -> None:
    """Validate this command before execution.

    Raises:
        ValueError: if the domain is not recognised, or if a ticker-scoped domain
                    is requested without specifying at least one exchange.
    """
    if self.domain not in DOMAINS:
        valid = ", ".join(sorted(DOMAINS))
        raise ValueError(
            f"RunCommand: unknown domain '{self.domain}'. Valid domains: {valid}"
        )

    ticker_domains = {COMPANY_DOMAIN, FUNDAMENTALS_DOMAIN, TECHNICALS_DOMAIN}
    if self.domain in ticker_domains and not self.exchanges:
        raise ValueError(
            f"RunCommand: 'exchanges' must contain at least one exchange when "
            f"domain='{self.domain}'. Specify exchanges to scope the ticker universe "
            f"(e.g., exchanges=['NASDAQ', 'NYSE'])."
        )
```

`DOMAINS`, `COMPANY_DOMAIN`, `FUNDAMENTALS_DOMAIN`, and `TECHNICALS_DOMAIN` are already available in the module via `from sbfoundation.settings import *`.

Call `validate()` as the first line of `SBFoundationAPI.run()`, before `_start_run()`:

```python
def run(self, command: RunCommand) -> RunContext:
    command.validate()
    ...
```

#### 3b. Update import block
Remove `INSTRUMENT_DOMAIN`, `INSTRUMENT_TYPE_EQUITY`, `STOCK_LIST_DATASET` from explicit imports.
Add `MARKET_STOCK_LIST_DATASET`, `MARKET_ETF_LIST_DATASET`, `MARKET_ETF_HOLDINGS_DATASET`.

#### 3c. Update `run()` dispatch
Replace:
```python
if domain == INSTRUMENT_DOMAIN:
    run = self._handle_instruments(command, run)
elif domain == ECONOMICS_DOMAIN:
    ...
```
With:
```python
if domain == MARKET_DOMAIN:
    run = self._handle_market(command, run)
elif domain == COMPANY_DOMAIN:
    run = self._handle_company(command, run)
elif domain == FUNDAMENTALS_DOMAIN:
    run = self._handle_fundamentals(command, run)
elif domain == TECHNICALS_DOMAIN:
    run = self._handle_technicals(command, run)
elif domain == ECONOMICS_DOMAIN:
    run = self._handle_economics(command, run)
elif domain == COMMODITIES_DOMAIN:
    run = self._handle_commodities(command, run)
elif domain == FX_DOMAIN:
    run = self._handle_fx(command, run)
elif domain == CRYPTO_DOMAIN:
    run = self._handle_crypto(command, run)
```

#### 3d. Update `_get_tickers()`
Remove the `INSTRUMENT_DOMAIN` special case:
```python
def _get_tickers(self, command: RunCommand) -> list[str]:
    return []  # Ticker domains self-populate via _get_exchange_filtered_universe()
```

#### 3e. Add `_get_exchange_filtered_universe()`

New private method used by all three ticker-domain handlers. Joins `silver.fmp_stock_list` → `silver.fmp_company_profile` to filter by exchange. Falls back to the full stock-list (with a warning) if the profile table is not yet populated.

```python
def _get_exchange_filtered_universe(
    self, exchanges: list[str], limit: int, run_id: str
) -> list[str]:
    """Return equity symbols scoped to the requested exchanges.

    Joins silver.fmp_stock_list to silver.fmp_company_profile and filters
    by exchange_short_name IN (exchanges).  If fmp_company_profile is not yet
    populated the filter is skipped and the full stock-list is returned.

    Args:
        exchanges:  Non-empty list of exchange short-names (e.g. ["NASDAQ", "NYSE"]).
        limit:      Maximum symbols to return (0 = no limit).
        run_id:     Current run ID for logging.
    """
    try:
        bootstrap = DuckDbBootstrap(logger=self.logger)
        with bootstrap.read_connection() as conn:
            profile_exists = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'silver' AND table_name = 'fmp_company_profile'"
            ).fetchone()
            limit_clause = f"LIMIT {limit}" if limit else ""

            if profile_exists and profile_exists[0] > 0:
                placeholders = ", ".join(["?" for _ in exchanges])
                sql = f"""
                    SELECT DISTINCT sl.symbol
                    FROM silver.fmp_stock_list sl
                    INNER JOIN silver.fmp_company_profile cp ON sl.symbol = cp.ticker
                    WHERE cp.exchange_short_name IN ({placeholders})
                    ORDER BY sl.symbol
                    {limit_clause}
                """
                rows = conn.execute(sql, exchanges).fetchall()
            else:
                self.logger.warning(
                    "silver.fmp_company_profile not yet populated — "
                    "falling back to full stock-list (exchange filter skipped)",
                    run_id=run_id,
                )
                sql = f"SELECT DISTINCT symbol FROM silver.fmp_stock_list ORDER BY symbol {limit_clause}"
                rows = conn.execute(sql).fetchall()

        bootstrap.close()
        return [row[0] for row in rows if row[0]]
    except Exception as exc:
        self.logger.error(f"Failed to get exchange-filtered universe: {exc}", run_id=run_id)
        return []
```

#### 3f. Update `_handle_market()` — add list dataset phases
Insert new phases **before** the existing countries/exchanges phases:

```
Phase 0a: stock-list (global, market domain)
Phase 0b: etf-list, index-list (global, market domain)
Phase 0c: etf-holdings (per-ETF ticker, universe from silver.fmp_etf_list)
```

Sequence:
1. Load `stock-list` → silver (using `MARKET_STOCK_LIST_DATASET`)
2. Load `etf-list`, `index-list` → silver
3. Load `etf-holdings` per ETF ticker (universe from `_get_universe_from_silver(MARKET_ETF_LIST_DATASET, "symbol")`)
4. Existing market phases: countries → exchanges/sectors/industries → hours → date-loop → holidays

#### 3g. Add `_handle_company()` handler
```python
def _handle_company(self, command: RunCommand, run: RunContext) -> RunContext:
    """Standalone company domain handler.

    1. Get equity universe from silver, scoped to command.exchanges
    2. Run company-profile (with INVALID TICKER filtering)
    3. Run remaining company domain recipes
    """
    self.logger.log_section(run.run_id, "Processing company domain")
    universe = self._get_exchange_filtered_universe(command.exchanges, command.ticker_limit, run.run_id)
    if not universe:
        self.logger.warning(
            "No symbols found for exchanges — run market domain first or check exchange names",
            run_id=run.run_id,
        )
        return run

    run.tickers = universe
    run.new_tickers = universe

    # Reuse existing company-profile logic (preserves INVALID TICKER filtering)
    run = self._company_profile(command, run)

    # Run remaining company recipes (excluding company-profile, already done)
    run = self._process_domain(COMPANY_DOMAIN, command, run)
    return run
```

#### 3h. Add `_handle_fundamentals()` handler
```python
def _handle_fundamentals(self, command: RunCommand, run: RunContext) -> RunContext:
    """Standalone fundamentals domain handler. Universe scoped to command.exchanges."""
    self.logger.log_section(run.run_id, "Processing fundamentals domain")
    universe = self._get_exchange_filtered_universe(command.exchanges, command.ticker_limit, run.run_id)
    if not universe:
        self.logger.warning("No symbols found — run market domain first or check exchange names", run_id=run.run_id)
        return run
    run.tickers = universe
    run.new_tickers = universe
    return self._process_domain(FUNDAMENTALS_DOMAIN, command, run)
```

#### 3i. Add `_handle_technicals()` handler
```python
def _handle_technicals(self, command: RunCommand, run: RunContext) -> RunContext:
    """Standalone technicals domain handler. Universe scoped to command.exchanges."""
    self.logger.log_section(run.run_id, "Processing technicals domain")
    universe = self._get_exchange_filtered_universe(command.exchanges, command.ticker_limit, run.run_id)
    if not universe:
        self.logger.warning("No symbols found — run market domain first or check exchange names", run_id=run.run_id)
        return run
    run.tickers = universe
    run.new_tickers = universe
    return self._process_domain(TECHNICALS_DOMAIN, command, run)
```

#### 3j. Remove dead methods
- `_handle_instruments()` — delete
- `_load_instrument()` — delete
- `_domain_recipes()` — delete (replaced by standalone handlers)
- `_company_profile()` fallback block (lines 550–557) — remove the `if not run.new_tickers:` guard and its `new_tickers()` call; handlers always set `run.new_tickers` before calling `_company_profile()`

Note: `_company_profile()` itself is preserved and reused by `_handle_company()`.

#### 3k. Update `__main__` block
Update the example `RunCommand` to show the new required fields:
```python
command = RunCommand(
    domain=COMPANY_DOMAIN,
    concurrent_requests=1,
    enable_bronze=True,
    enable_silver=True,
    ticker_limit=5,
    ticker_recipe_chunk_size=10,
    exchanges=["NASDAQ"],   # required for ticker-scoped domains
)
```

---

---

### Step 4 — Remove `InstrumentCatalogService` and `ops.instrument_catalog` infrastructure

#### Investigation findings

| File | Location | Finding | Action |
|---|---|---|---|
| `src/sbfoundation/services/ops/instrument_catalog_service.py` | Class definition | `sync_from_silver_tables()` never called anywhere — table always empty | **Delete entire file** |
| `src/sbfoundation/services/ops/__init__.py` | Line 6, 8 | Imports and exports `InstrumentCatalogService` | **Remove import + `__all__` entry** |
| `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py` | Lines 52–62, 113 | Defines `OPS_INSTRUMENT_CATALOG_DDL` constant and executes it in `_initialize_schema()` | **Remove constant + DDL call** |
| `db/migrations/20260217_002_create_ops_instrument_catalog.sql` | Full file | Created `ops.instrument_catalog` — table exists in prod DBs | **Leave in place** (history); add new drop migration |

#### Actions

1. **Delete** `src/sbfoundation/services/ops/instrument_catalog_service.py`
2. **Edit** `src/sbfoundation/services/ops/__init__.py` — remove `InstrumentCatalogService` import and `__all__` entry
3. **Edit** `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py`:
   - Remove the `OPS_INSTRUMENT_CATALOG_DDL` constant (lines 52–62)
   - Remove `self._conn.execute(OPS_INSTRUMENT_CATALOG_DDL)` from `_initialize_schema()` (line 113)
   - Update the docstring to remove "ops.instrument_catalog" from the list of tables created

---

### Step 5 — Clean up `UniverseRepo` and `UniverseService`

#### `UniverseRepo` — what to remove

| Method | Problem | Action |
|---|---|---|
| `get_new_tickers()` | Queries `gold.dim_instrument` — Gold-layer violation | **Delete** |
| `count_new_tickers()` | Queries `gold.dim_instrument` — Gold-layer violation | **Delete** |
| `get_instrument()` | Queries `ops.instrument_catalog` — table being dropped | **Delete** |
| `get_update_tickers()` | JOINs `ops.instrument_catalog` when `instrument_type` or `is_active` set — catalog always empty, broken | **Rewrite**: remove catalog JOIN; filter by `instrument_type` is no longer needed (caller passes universe directly) |
| `count_update_tickers()` | JOINs `ops.instrument_catalog` when `instrument_type` set | **Simplify**: remove JOIN |

**Rewritten `get_update_tickers()`** — keep only the simple path (no catalog JOIN):
```python
def get_update_tickers(self, *, start: int = 0, limit: int = 50) -> list[str]:
    """Return tickers that have been successfully promoted to silver."""
    conn = self._bootstrap.connect()
    sql = (
        "SELECT DISTINCT ticker FROM ops.file_ingestions "
        "WHERE ticker IS NOT NULL AND ticker <> '' "
        "AND silver_can_promote = TRUE "
        f"ORDER BY ticker LIMIT {limit} OFFSET {start}"
    )
    result = conn.execute(sql).fetchall()
    return [row[0] for row in result if row[0]]
```

Remove `instrument_type` and `is_active` parameters — callers no longer need catalog-based filtering.

**Rewritten `count_update_tickers()`**:
```python
def count_update_tickers(self) -> int:
    conn = self._bootstrap.connect()
    result = conn.execute(
        "SELECT COUNT(DISTINCT ticker) FROM ops.file_ingestions "
        "WHERE ticker IS NOT NULL AND ticker <> '' AND silver_can_promote = TRUE"
    ).fetchone()
    return result[0] if result else 0
```

#### `UniverseService` — what to remove

| Method | Problem | Action |
|---|---|---|
| `new_tickers()` | Delegates to `get_new_tickers()` — Gold layer | **Delete** |
| `new_ticker_count()` | Delegates to `count_new_tickers()` — Gold layer | **Delete** |
| `get_instrument()` | Delegates to repo `get_instrument()` — catalog dropped | **Delete** |
| `get_instruments_by_type()` | Calls `new_tickers()` or `update_tickers()` with `instrument_type` param | **Delete** (instrument-type filtering removed) |
| `update_tickers()` | Keeps — but remove `instrument_type` and `is_active` params | **Simplify signature** |
| `update_ticker_count()` | Keeps — remove `instrument_type` param | **Simplify signature** |

#### `api.py` — remove `new_tickers()` call sites

- `_get_tickers()`: already returns `[]` in new design — remove body referencing `new_tickers()`
- `_company_profile()`: the fallback `if not run.new_tickers: ... = self._universe_service.new_tickers(...)` block (lines 550–557) must be removed. The new `_handle_company()` always sets `run.new_tickers` before calling `_company_profile()`, making the fallback unreachable and incorrect.

---

### Step 6 — Write drop migration for `ops.instrument_catalog`

Create `db/migrations/20260218_001_drop_ops_instrument_catalog.sql`:
```sql
-- Migration: 20260218_001
-- Drop ops.instrument_catalog — table was never populated (InstrumentCatalogService
-- was never called in production). Universe discovery now reads directly from
-- silver.fmp_stock_list. Superseded by Step 4 of execplan_remove_instrument_domain.

DROP TABLE IF EXISTS ops.instrument_catalog;
```

---

### Step 7 — `docs/domain_datasets_reference.md`

1. **Section 1 (Domain Overview table)**: Change 9 domains → 8 domains. Remove `instrument` row. Update `market` row to show dataset count now including stock-list/etf-list/index-list/etf-holdings (10 + 4 = 14). Update total count.

2. **Section 2 (Dataset Loading Order / Mermaid diagram)**:
   - Remove the `INST["RunCommand: domain = instrument"]` subgraph
   - Update `MKT["RunCommand: domain = market"]` to add Phase 0 for list datasets and etf-holdings
   - Add `CO["RunCommand: domain = company"]`, `FU["RunCommand: domain = fundamentals"]`, `TE["RunCommand: domain = technicals"]` as separate RunCommand boxes
   - Update dependency rules section

3. **Section 3 (Instrument Domain)**: Replace the entire section with a note or remove it. Move the 4 datasets (stock-list, etf-list, index-list, etf-holdings) into Section 8 (Market Domain) as new sub-sections (Phase 0).

4. **Section 8 (Market Domain)**: Add Phase 0 sub-sections:
   - 8.0a `stock-list` (previously Section 3.1)
   - 8.0b `etf-list` (previously Section 3.2)
   - 8.0c `index-list` (previously Section 3.3)
   - 8.0d `etf-holdings` (previously Section 3.6)

   Note: `cryptocurrency-list` and `forex-list` already documented under their respective domains.

5. **Table of Contents**: Update numbering (remove Section 3, renumber others).

6. **Section 12 (Dataset Summary Table)**: Change `instrument` rows to `market` for the 4 datasets. Change `cryptocurrency-list` to domain `crypto` and `forex-list` to domain `fx`.

7. **Quick Reference stats**: Update total domains (9→8), verify dataset counts.

---

### Step 8 — `README.md`

1. **Data domains table**: Remove `instrument` row. Update `market` row (4 additional datasets, updated count). Ensure `company`, `fundamentals`, `technicals` descriptions note they are now independently callable.

2. **"Ticker based domain execution order" line**: Update from `instrument → company → fundamentals → technicals` to `market (list discovery) → company → fundamentals → technicals`.

3. **Key Design Decisions #7** ("Domain execution order is enforced"): Update to note that `market` domain populates `silver.fmp_stock_list` which seeds the equity universe for company/fundamentals/technicals.

---

## Concrete Steps

### Verification before starting
```bash
# Confirm all instrument domain references
grep -rn "INSTRUMENT_DOMAIN\|instrument_catalog" src/ config/ tests/ --include="*.py" --include="*.yaml"

# Confirm no duplicate dataset name clashes
grep -n "stock-list\|etf-list\|index-list\|etf-holdings" config/dataset_keymap.yaml

# Confirm new_tickers / gold.dim_instrument call sites
grep -rn "new_tickers\|dim_instrument\|instrument_catalog" src/ --include="*.py"
```

### Step 1: YAML changes (6 domain: field changes)
Edit `config/dataset_keymap.yaml`:
- Line ~4: `domain: instrument` → `domain: market` (stock-list)
- Line ~43: `domain: instrument` → `domain: market` (etf-list)
- Line ~94: `domain: instrument` → `domain: market` (index-list)
- Line ~145: `domain: instrument` → `domain: crypto` (cryptocurrency-list)
- Line ~196: `domain: instrument` → `domain: fx` (forex-list)
- Line ~(etf-holdings): `domain: instrument` → `domain: market` (etf-holdings)

### Step 2: settings.py changes
- Remove `INSTRUMENT_DOMAIN = "instrument"`
- Remove from `DOMAINS` list
- Remove from `DOMAIN_EXECUTION_ORDER` tuple
- Rename the "INSTRUMENT DATASETS" section to "MARKET LIST DATASETS"
- Rename constants: `STOCK_LIST_DATASET` → `MARKET_STOCK_LIST_DATASET`, etc.
- Update `DATASETS` list to use new constant names

### Step 3: api.py refactor
- Add `RunCommand.validate()` — domain check + exchange requirement for ticker domains
- Call `command.validate()` as first line of `SBFoundationAPI.run()`
- Update imports (remove `INSTRUMENT_DOMAIN`, `INSTRUMENT_TYPE_EQUITY`, `STOCK_LIST_DATASET` references)
- Rewrite `run()` dispatch
- Remove `new_tickers()` fallback from `_company_profile()` (lines 550–557)
- Rewrite `_get_tickers()` to return `[]`
- Add `_get_exchange_filtered_universe()` private method
- Update `_handle_market()` to include Phase 0 list datasets
- Add `_handle_company()`, `_handle_fundamentals()`, `_handle_technicals()` — all using `_get_exchange_filtered_universe()`
- Delete `_handle_instruments()`, `_load_instrument()`, `_domain_recipes()`
- Update `__main__` block to show `exchanges` field

### Step 4: Remove InstrumentCatalogService infrastructure
- Delete `src/sbfoundation/services/ops/instrument_catalog_service.py`
- Edit `src/sbfoundation/services/ops/__init__.py` — remove import + `__all__` entry
- Edit `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py` — remove `OPS_INSTRUMENT_CATALOG_DDL` constant and DDL execution call

### Step 5: Clean up UniverseRepo and UniverseService
- Edit `src/sbfoundation/infra/universe_repo.py` — delete `get_new_tickers()`, `count_new_tickers()`, `get_instrument()`; simplify `get_update_tickers()` and `count_update_tickers()` (remove catalog JOIN and instrument_type param)
- Edit `src/sbfoundation/services/universe_service.py` — delete `new_tickers()`, `new_ticker_count()`, `get_instrument()`, `get_instruments_by_type()`; simplify `update_tickers()` and `update_ticker_count()` signatures
- Remove `INSTRUMENT_TYPE_EQUITY` import from `universe_service.py` if orphaned

### Step 6: Write drop migration
Create `db/migrations/20260218_001_drop_ops_instrument_catalog.sql` with `DROP TABLE IF EXISTS ops.instrument_catalog;`

### Steps 7 & 8: Documentation
Update docs files as described in Plan of Work sections 7 and 8.

### Post-implementation verification
```bash
# No more INSTRUMENT_DOMAIN or instrument_catalog references
grep -rn "INSTRUMENT_DOMAIN\|instrument_catalog\|new_tickers\|dim_instrument" src/ config/ tests/

# Type check
poetry run mypy src/

# Lint
poetry run flake8 src/

# Run unit tests
poetry run pytest tests/unit/ -v

# Smoke test: run market domain (should load stock-list + existing market datasets)
poetry run python src/sbfoundation/api.py
```

---

## Validation and Acceptance

1. `grep -rn "INSTRUMENT_DOMAIN" src/ config/` returns **zero results**
2. `grep -n "domain: instrument" config/dataset_keymap.yaml` returns **zero results**
3. `grep -rn "instrument_catalog" src/` returns **zero results**
4. `grep -rn "dim_instrument\|get_new_tickers\|new_ticker" src/` returns **zero results**
5. `poetry run mypy src/` passes with no new errors
6. `poetry run pytest tests/unit/` all pass
7. `RunCommand(domain="invalid_domain").validate()` raises `ValueError` with a message listing valid domains
8. `RunCommand(domain=COMPANY_DOMAIN, exchanges=[]).validate()` raises `ValueError` requiring at least one exchange
9. `RunCommand(domain=MARKET_DOMAIN, exchanges=[]).validate()` passes — exchange requirement only applies to ticker domains
10. `RunCommand(domain=MARKET_DOMAIN)` executes without error; `silver.fmp_stock_list`, `silver.fmp_etf_list`, `silver.fmp_index_list` are populated
11. `RunCommand(domain=COMPANY_DOMAIN, ticker_limit=3, exchanges=["NASDAQ"])` executes; universe filtered to NASDAQ tickers from silver
12. `RunCommand(domain=FUNDAMENTALS_DOMAIN, ticker_limit=3, exchanges=["NASDAQ"])` executes successfully
13. `RunCommand(domain=TECHNICALS_DOMAIN, ticker_limit=3, exchanges=["NASDAQ"])` executes successfully
11. `docs/domain_datasets_reference.md` shows 8 domains, market domain includes stock-list/etf-list/index-list/etf-holdings
12. `README.md` domain table shows 8 rows, no `instrument` row

---

## Idempotence and Recovery

- YAML and settings.py changes are pure text edits; reversible by reverting the file
- api.py refactor: deleted methods can be restored from git (`git diff HEAD`)
- No DuckDB schema changes required — silver table names are unchanged; the `domain` column in `ops.bronze_manifest` will reflect the new domain values for new runs, old rows remain as-is
- Old Bronze files tagged `domain=instrument` remain valid; silver promotion still works because `SilverService` looks up the keymap by `(source, dataset)` not by `domain`

---

## Artifacts and Notes

### Constants renamed in settings.py

| Old Constant | New Constant |
|---|---|
| `STOCK_LIST_DATASET` | `MARKET_STOCK_LIST_DATASET` |
| `ETF_LIST_DATASET` | `MARKET_ETF_LIST_DATASET` |
| `INDEX_LIST_DATASET` | `MARKET_INDEX_LIST_DATASET` |
| `ETF_HOLDINGS_DATASET` | `MARKET_ETF_HOLDINGS_DATASET` |

### Added to api.py
| Item | Purpose |
|---|---|
| `RunCommand.validate()` method | Domain check + exchange requirement for ticker-scoped domains |
| `SBFoundationAPI._get_exchange_filtered_universe()` | Join stock-list → company_profile filtered by exchange; fallback to full list |
| `SBFoundationAPI._handle_company()` | Standalone company domain handler |
| `SBFoundationAPI._handle_fundamentals()` | Standalone fundamentals domain handler |
| `SBFoundationAPI._handle_technicals()` | Standalone technicals domain handler |

### Removed from api.py
| Method | Replacement |
|---|---|
| `_handle_instruments()` | Removed; logic redistributed |
| `_load_instrument()` | Removed; subsumed into `_handle_market()` |
| `_domain_recipes()` | Removed; replaced by 3 standalone handlers |
| `_company_profile()` fallback block (lines 550–557) | Removed; `_handle_company()` always sets `run.new_tickers` |

### Preserved in api.py
| Method | Status |
|---|---|
| `_company_profile()` (minus fallback) | Preserved; called by `_handle_company()` |
| `_process_domain()` | Preserved; used by all 3 new handlers |
| `_process_ticker_recipes()` | Preserved; unchanged |
| `_get_universe_from_silver()` | Preserved; still used by market/commodities/fx/crypto handlers |

### Files deleted
| File | Reason |
|---|---|
| `src/sbfoundation/services/ops/instrument_catalog_service.py` | Never called; table always empty |

### Files with methods deleted
| File | Methods removed |
|---|---|
| `src/sbfoundation/infra/universe_repo.py` | `get_new_tickers()`, `count_new_tickers()`, `get_instrument()` |
| `src/sbfoundation/services/universe_service.py` | `new_tickers()`, `new_ticker_count()`, `get_instrument()`, `get_instruments_by_type()` |

### Files with DDL removed
| File | Change |
|---|---|
| `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py` | Remove `OPS_INSTRUMENT_CATALOG_DDL` constant + execution call in `_initialize_schema()` |

### Migration added
| File | Purpose |
|---|---|
| `db/migrations/20260218_001_drop_ops_instrument_catalog.sql` | Drop `ops.instrument_catalog` from existing databases |

---

## Interfaces and Dependencies

### `_get_universe_from_silver(dataset, symbol_col)` — existing method
Used by `_handle_company()`, `_handle_fundamentals()`, `_handle_technicals()` with:
- `dataset = MARKET_STOCK_LIST_DATASET` ("stock-list")
- `symbol_col = "symbol"`

Returns `list[str] | None`. Callers must handle `None` (no data in silver yet).

### `_process_domain(domain, command, run)` — existing method
Filters `self._dataset_service.recipes` by `domain`, splits into ticker/non-ticker, processes both. Used by all three new standalone handlers.

### `_company_profile(command, run)` — existing method
Contains INVALID TICKER filtering and backfill logic. Called by `_handle_company()` after setting `run.tickers` and `run.new_tickers`.

### New `_handle_market()` phases require:
- `MARKET_STOCK_LIST_DATASET = "stock-list"` (from settings)
- `MARKET_ETF_LIST_DATASET = "etf-list"` (from settings)
- `MARKET_INDEX_LIST_DATASET = "index-list"` (from settings)
- `MARKET_ETF_HOLDINGS_DATASET = "etf-holdings"` (from settings)
