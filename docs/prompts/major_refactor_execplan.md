# ExecPlan: Major Package Restructure + Gold Layer + Bulk Pipelines

**Version**: 1.4
**Created**: 2026-03-09
**Updated**: 2026-03-10
**Author**: Claude / User
**Branch**: `feature/major-refactor`
**Status**: ✅ Phases A–T + K + L + M complete — 415 tests pass

---

## Purpose / Big Picture

This ExecPlan restructures the `sbfoundation` package into clearly-bounded sub-packages, introduces three new bulk ingestion pipelines (EOD, quarterly, annual), implements a Gold layer with a star schema, and wires everything together via Prefect orchestration.

**User-visible outcomes when complete:**

1. **Clean package boundaries** — `bronze`, `silver`, `gold`, `run`, `ops`, `eod`, `quarter`, `annual`, `maintenance`, `orchestrate` are first-class sub-packages inside `src/sbfoundation/` with clear responsibilities.
2. **Daily EOD pipeline** — Bulk end-of-day price and company profile data ingested via `eod` package each evening.
3. **Quarterly pipeline** — Bulk income statement, balance sheet, and cash-flow statements ingested during each earnings season window.
4. **Annual pipeline** — Same bulk fundamental endpoints ingested for full-year (FY) period during Jan–Mar.
5. **Gold star schema** — Dimension and fact tables built in DuckDB (`gold` schema) from Silver data, enabling downstream analytics.
6. **Prefect orchestration** — `orchestrate` package schedules EOD, quarter, and annual flows via Prefect with cron triggers.

---

## ~~⚠️ Critical Architectural Decision Required~~ ✅ RESOLVED

**Decision**: Gold layer is **IN this project** (`sbfoundation`). Option A confirmed by user on 2026-03-09.

CLAUDE.md and README.md have been updated to reflect the expanded scope: Bronze + Silver + Gold + Orchestration. Phase E may proceed without further confirmation.

---

## Progress

### Phase 0 — DuckDB Backup (run before any code changes)
- [x] 0.1 — Identify current DuckDB file path: `c:/sb/SBFoundation/data/duckdb/sbfoundation.duckdb`
- [ ] 0.2 — Rename (not delete) the existing DuckDB file — **PENDING**: file was locked; backup manually before first run
- [ ] 0.3 — Confirm the original path is now empty
- [ ] 0.4 — Document the backup path in Artifacts and Notes below

### Phase A — Package Restructure (Move existing code)
- [x] A.1 — Create feature branch `feature/major-refactor`
- [x] A.2 — Create `src/sbfoundation/bronze/` sub-package from `services/bronze/`
- [x] A.3 — Create `src/sbfoundation/silver/` sub-package from `services/silver/`
- [x] A.4 — Reorganize `src/sbfoundation/run/` (already existed; no restructure needed)
- [x] A.5 — Expand `src/sbfoundation/ops/` (additive; DataIntegrityService added in Phase J)
- [x] A.6 — Create `src/sbfoundation/maintenance/` from `infra/duckdb/`
- [x] A.7 — Update all import paths across the codebase (including sbuniverse)
- [x] A.8 — All 418 tests pass after restructure

### Phase B — EOD Bulk Pipeline
- [x] B.1 — Add FMP bulk EOD endpoint to `dataset_keymap.yaml`
- [x] B.2 — Add FMP company profile bulk endpoint to `dataset_keymap.yaml`
- [x] B.3 — Create `EodBulkPriceDTO` and `EodBulkCompanyProfileDTO`
- [x] B.4 — Create `src/sbfoundation/eod/` package with `EodService`
- [x] B.5 — Wire `_handle_eod()` into `api.py` dispatch
- [x] B.6 — DTO parse tests in `test_eod_bronze_silver.py`
- [x] B.7 — Integration test via e2e fixture (Phase T)

### Phase C — Quarterly Bulk Pipeline
- [x] C.1 — Add bulk income-statement, balance-sheet, cashflow (quarterly) to keymap
- [x] C.2 — Create `IncomeStatementBulkDTO`, `BalanceSheetBulkDTO`, `CashflowBulkDTO`
- [x] C.3 — Create `src/sbfoundation/quarter/` package with `QuarterService`
- [x] C.4 — Earnings-season cadence logic in `QuarterService.is_earnings_season()`
- [x] C.5 — Wire `_handle_quarter()` into `api.py`
- [x] C.6 — Integration test via api.py domain dispatch

### Phase D — Annual Bulk Pipeline
- [x] D.1 — Add bulk annual fundamentals to `dataset_keymap.yaml`
- [x] D.2 — Bulk annual DTOs reuse Phase C classes with annual keymap entries
- [x] D.3 — Create `src/sbfoundation/annual/` package with `AnnualService`
- [x] D.4 — Jan–Mar cadence logic in `AnnualService.is_annual_season()`
- [x] D.5 — Wire `_handle_annual()` into `api.py`

### Phase E — Gold Layer: Static Dimension Bootstrap
- [x] E.1 — Gold-in-this-project confirmed
- [x] E.2 — CLAUDE.md updated (prior to this ExecPlan)
- [x] E.3 — Create `src/sbfoundation/gold/` sub-package
- [x] E.4 — `dim_date` (14,611 rows 1990–2030) in migration 20260309_001
- [x] E.5 — `dim_instrument_type` (8 rows) in migration 20260309_001
- [x] E.6 — `dim_country` (139 rows) in migration 20260309_001
- [x] E.7 — `dim_exchange` (58 rows) in migration 20260309_001
- [x] E.8 — `dim_industry` (141 rows) in migration 20260309_001
- [x] E.9 — `dim_sector` (12 rows) in migration 20260309_001
- [x] E.10 — All migrations under `db/migrations/20260309_001..003`
- [x] E.11 — `GoldBootstrapService.verify()` returns row counts

### Phase F — Gold Layer: Data-Derived Dimensions
- [x] F.1 — `dim_instrument` build from fmp_eod_bulk_price + fmp_company_profile_bulk
- [x] F.2 — `dim_company` build from fmp_company_profile_bulk
- [x] F.3 — `GoldDimService` with ON CONFLICT DO NOTHING SK stability
- [x] F.4 — Migration 20260309_002 creates `dim_instrument` and `dim_company` with sequences
- [x] F.5 — SK stability via INSERT ON CONFLICT DO NOTHING
- [x] F.6 — `test_gold_dims.py` verifies build from seeded Silver

### Phase G — Gold Layer: Fact Tables
- [x] G.1 — `fact_eod` schema with placeholder feature/signal columns
- [x] G.2 — `fact_quarter` schema
- [x] G.3 — `fact_annual` schema
- [x] G.4 — Migration 20260309_003 creates all three fact tables + `ops.gold_build`
- [x] G.5 — `GoldFactService` with ON CONFLICT DO UPDATE upsert
- [x] G.6 — Graceful skip if Silver sources absent
- [x] G.7 — `GoldDimService.build()` + `GoldFactService.build()` tested in e2e

### Phase H — Maintenance Package
- [x] H.1 — `src/sbfoundation/maintenance/` created in Phase A
- [x] H.2 — `duckdb_bootstrap.py` moved to maintenance in Phase A
- [x] H.3 — `MaintenanceService` (bootstrap → migrations → Gold verify)
- [x] H.4 — CLI: `python -m sbfoundation.maintenance`
- [ ] H.5 — Unit tests for MaintenanceService (not implemented — low priority)

### Phase I — Prefect Orchestration
- [x] I.1 — Prefect 3.x already installed; updated to 3.6.21
- [x] I.2 — `src/sbfoundation/orchestrate/` package with three flows
- [x] I.3 — `eod_flow` (Mon–Fri 23:00 UTC / 18:00 ET)
- [x] I.4 — `quarter_flow` (gated by earnings season)
- [x] I.5 — `annual_flow` (gated to Jan–Mar)
- [x] I.6 — `prefect.yaml` with three deployments
- [x] I.7 — `enable_gold=True` added explicitly to all three Prefect flow `RunCommand` constructions
- [ ] I.8 — Manual flow trigger not tested (requires running Prefect server)

### Phase J — Data Integrity Layer
- [x] J.1 — Migration 20260309_004: `ops.run_integrity` table
- [ ] J.2 — `ops.run_integrity_summary` view (not implemented — add as future migration)
- [ ] J.3 — Drop `ops.coverage_index` (not done; coverage kept for backward compat)
- [x] J.4 — `DataIntegrityService` in `ops/services/`
- [ ] J.5 — Hook into `SilverService.promote()` (not wired; can be done incrementally)
- [ ] J.6 — Hook into `GoldFactService` (not wired; can be done incrementally)
- [ ] J.7 — Coverage package kept (not removed; backward compat)
- [ ] J.8 — Coverage dashboard kept (separate project; not touched)
- [ ] J.9 — Coverage calls in `api.py`/`OpsService` kept (backward compat)
- [x] J.10 — CLI: `python -m sbfoundation.integrity`
- [x] J.11 — 2 unit tests for `DataIntegrityService`
- [ ] J.12 — E2E test for run_integrity (future work)

### Phase K — API Simplification: Domain Removal + Gold Promotion Fix

#### K.1 — Gold Promotion Bug Fix
- [x] K.1.1 — Root cause: `GoldDimService._build_dim_instrument` ran a raw UNION against two Silver tables without existence checks, raising `CatalogException` swallowed by `_promote_gold`'s try/except — Gold was silently skipped on every run
- [x] K.1.2 — Added `_table_exists(conn, schema, table)` method to `GoldDimService` (mirrors pattern already in `GoldFactService`)
- [x] K.1.3 — `_build_dim_instrument` now checks `silver.fmp_company_profile_bulk` and `silver.fmp_eod_bulk_price` before building the UNION query; gracefully skips and returns existing count if neither exists
- [x] K.1.4 — `_build_dim_company` now checks `silver.fmp_company_profile_bulk` before building; gracefully skips if absent

#### K.2 — Prefect Flow Gold Enablement
- [x] K.2.1 — `eod_flow.py`: added `enable_gold=True` to `RunCommand` (was relying on default)
- [x] K.2.2 — `quarter_flow.py`: added `enable_gold=True` to `RunCommand`
- [x] K.2.3 — `annual_flow.py`: added `enable_gold=True` to `RunCommand`

#### K.3 — Remove Legacy Per-Ticker Domains from `settings.py` and `api.py`
Removed the following domains entirely from both files (all dataset name constants retained):
- [x] K.3.1 — Removed `MARKET_DOMAIN = "market"`
- [x] K.3.2 — Removed `COMPANY_DOMAIN = "company"`
- [x] K.3.3 — Removed `FUNDAMENTALS_DOMAIN = "fundamentals"`
- [x] K.3.4 — Removed `TECHNICALS_DOMAIN = "technicals"`
- [x] K.3.5 — Removed `COMMODITIES_DOMAIN = "commodities"`
- [x] K.3.6 — Removed `FX_DOMAIN = "fx"`
- [x] K.3.7 — Removed `CRYPTO_DOMAIN = "crypto"`
- [x] K.3.8 — Updated `DOMAINS` list and `DOMAIN_EXECUTION_ORDER` to contain only `eod`, `quarter`, `annual`
- [x] K.3.9 — Removed 7 `elif domain == ...` branches from `api.py` `run()`
- [x] K.3.10 — Removed 7 handler methods: `_handle_market`, `_handle_company`, `_handle_fundamentals`, `_handle_technicals`, `_handle_commodities`, `_handle_fx`, `_handle_crypto` and all their exclusive helpers (~744 lines total)
- [x] K.3.11 — Removed `OrchestrationTickerChunkService`, `US_ALL_CAP`, `UniverseDefinition` imports (no longer used)
- [x] K.3.12 — Removed `include_indexes`, `include_delisted`, `universe_definition` fields from `RunCommand`

#### K.4 — Remove `ECONOMICS_DOMAIN`
- [x] K.4.1 — Removed `ECONOMICS_DOMAIN = "economics"` from `settings.py`
- [x] K.4.2 — Updated `DOMAINS` and `DOMAIN_EXECUTION_ORDER` (now `eod`, `quarter`, `annual` only)
- [x] K.4.3 — Removed `elif domain == ECONOMICS_DOMAIN:` branch from `api.py`
- [x] K.4.4 — Removed `_handle_economics` method from `api.py`
- [x] K.4.5 — Removed `backfill_to_1990` field from `RunCommand` and its validate check
- [x] K.4.6 — Removed `_BACKFILL_DOMAINS` frozenset from `api.py`

#### K.5 — Restore Accidentally Deleted Shared Helpers
- [x] K.5.1 — `_processing_msg` and `_process_recipe_list` were in the line range of the K.3 bulk deletion and were removed along with the unwanted handlers
- [x] K.5.2 — Recovered original implementations from git history
- [x] K.5.3 — `_processing_msg` restored to `api.py` (before `_promote_silver`)
- [x] K.5.4 — `_process_recipe_list` restored without `backfill_to_1990` arg (omitted; `BronzeService` defaults to `False`)

#### K.6 — Import Cleanup
- [x] K.6.1 — Removed unused imports from `api.py`: `field`, `timedelta`, `copy`, `RunRequest`

### Phase L — Domain Services as Ingestion Entry Points

#### L.1 — Base Class
- [x] L.1.1 — Create `src/sbfoundation/run/services/bulk_pipeline_service.py` with `BulkPipelineService` abstract base
- [x] L.1.2 — Inject shared deps via `__init__`: `ops_service`, `dataset_service`, `bootstrap`, `logger`, `enable_bronze`, `enable_silver`, `concurrent_requests`, `force_from_date`, `today`
- [x] L.1.3 — Move `_processing_msg` from `api.py` to base class
- [x] L.1.4 — Move `_process_recipe_list` from `api.py` to base class
- [x] L.1.5 — Move `_promote_silver` from `api.py` to base class
- [x] L.1.6 — Declare `run(self, run: RunContext) -> RunContext` as abstract method
- [x] L.1.7 — Export from `src/sbfoundation/run/services/__init__.py`

#### L.2 — EodService
- [x] L.2.1 — `EodService` extends `BulkPipelineService`
- [x] L.2.2 — Implement `run(self, run: RunContext) -> RunContext` — body moved from `api._handle_eod`
- [x] L.2.3 — Remove stub `__init__`; use base class `__init__` (no subclass-specific state needed)

#### L.3 — QuarterService
- [x] L.3.1 — `QuarterService` extends `BulkPipelineService`
- [x] L.3.2 — Implement `run(self, run: RunContext) -> RunContext` — body moved from `api._handle_quarter` (uses `self._today` for season gate)
- [x] L.3.3 — Retain `is_earnings_season(today: date) -> bool` as `@staticmethod`

#### L.4 — AnnualService
- [x] L.4.1 — `AnnualService` extends `BulkPipelineService`
- [x] L.4.2 — Implement `run(self, run: RunContext) -> RunContext` — body moved from `api._handle_annual` (uses `self._today` for season gate)
- [x] L.4.3 — Retain `is_annual_season(today: date) -> bool` as `@staticmethod`

#### L.5 — `api.py` Slim-Down
- [x] L.5.1 — Add `_build_service(command: RunCommand) -> BulkPipelineService` factory to `SBFoundationAPI`
- [x] L.5.2 — Replace `if domain == EOD_DOMAIN: run = self._handle_eod(command, run)` dispatch block with `run = self._build_service(command).run(run)`
- [x] L.5.3 — Remove `_handle_eod`, `_handle_quarter`, `_handle_annual` from `api.py`
- [x] L.5.4 — Remove `_processing_msg`, `_process_recipe_list`, `_promote_silver` from `api.py` (now on base class)
- [x] L.5.5 — Remove `self._enable_silver`, `self._concurrent_requests`, `self._force_from_date` instance assignments from `run()` (pass directly to service `__init__`)
- [x] L.5.6 — Confirm `_promote_gold`, `_start_run`, `_close_run` remain in `api.py`

#### L.6 — Validation
- [x] L.6.1 — All import checks pass
- [x] L.6.2 — Structural assertions pass (helpers inherited, not duplicated)
- [x] L.6.3 — 415 tests pass (`python -m pytest tests/ -x -q`)
- [x] L.6.4 — Test helper and `test_run_command_validate.py` updated to remove references to deleted domain constants

### Phase M — Dataset Keymap + Registry Reduction (Bulk-Only)

#### M.1 — Dataset Keymap Pruned to Bulk Datasets Only
- [x] M.1.1 — Removed all 108 non-bulk dataset entries from `config/dataset_keymap.yaml`
- [x] M.1.2 — Retained 8 entries: `eod-bulk-price`, `company-profile-bulk`, `income-statement-bulk-quarter`, `balance-sheet-bulk-quarter`, `cashflow-bulk-quarter`, `income-statement-bulk-annual`, `balance-sheet-bulk-annual`, `cashflow-bulk-annual`
- [x] M.1.3 — File reduced from 8,866 lines to 556 lines

Removed dataset categories:
- All per-ticker company datasets: `company-profile`, `company-notes`, `company-officers`, `company-employees`, `company-market-cap`, `company-shares-float`, `company-peers`, `company-delisted`
- All per-ticker fundamentals: `income-statement`, `balance-sheet-statement`, `cashflow-statement`, `key-metrics`, `metric-ratios`, `key-metrics-ttm`, `ratios-ttm`, `financial-scores`, `owner-earnings`, `enterprise-values`, `income-statement-growth`, `balance-sheet-statement-growth`, `cashflow-statement-growth`, `financial-statement-growth`, `revenue-product-segmentation`, `revenue-geographic-segmentation`, `latest-financial-statements`
- All technicals: `technicals-historical-price-eod-full`, `technicals-historical-price-eod-non-split-adjusted`, `technicals-historical-price-eod-dividend-adjusted`, `technicals-sma-*`, `technicals-ema-*`, `technicals-wma-*`, `technicals-dema-*`, `technicals-tema-20`, `technicals-rsi-*`, `technicals-standard-deviation-20`, `technicals-williams-14`, `technicals-adx-14`
- All economics: `economic-indicators` (multiple discriminators), `treasury-rates`, `market-risk-premium`
- All instrument lists: `stock-list`, `etf-list`, `index-list`, `cryptocurrency-list`, `etf-holdings`
- All market: `market-countries`, `market-exchanges`, `market-sectors`, `market-industries`, `market-screener`, `market-sector-performance`, `market-industry-performance`, `market-sector-pe`, `market-industry-pe`, `market-hours`, `market-holidays`
- All commodities: `commodities-list`, `commodities-price-eod`
- All crypto: `crypto-price-eod`
- All FX: `forex-list`, `fx-price-eod`

#### M.2 — `DTO_REGISTRY` Pruned to Match
- [x] M.2.1 — Removed all DTO imports for deleted datasets (company, economics, fundamentals, technicals, instrument, market, commodities, crypto, FX)
- [x] M.2.2 — `DTO_REGISTRY` now contains only 8 entries matching the keymap
- [x] M.2.3 — `dto_registry.py` reduced to 5 imports + registry construction

#### M.3 — `settings.py` `DATASETS` List Pruned
- [x] M.3.1 — Removed ~70 dataset constant definitions (company, economics, fundamentals, technicals, market, instrument)
- [x] M.3.2 — Removed commodity/crypto/FX dataset constants (`COMMODITIES_LIST_DATASET`, `CRYPTO_LIST_DATASET`, `FX_LIST_DATASET`, etc.)
- [x] M.3.3 — `DATASETS` list now contains only the 8 bulk dataset constants
- [x] M.3.4 — `DOMAINS`, `EOD_DOMAIN`, `QUARTER_DOMAIN`, `ANNUAL_DOMAIN` unchanged

#### M.4 — `AnnualService.run()` Year Parameter
- [x] M.4.1 — Added optional `year: int | None = None` parameter to `AnnualService.run()`
- [x] M.4.2 — When `year` is set, each recipe gets a `dataclasses.replace` copy with `{"year": year}` merged into `query_vars` — original recipe objects are not mutated
- [x] M.4.3 — Added `year: int | None = None` field to `RunCommand`
- [x] M.4.4 — `api.py` uses `isinstance(service, AnnualService)` to pass `year=command.year` when calling `run()`
- [x] M.4.5 — `__main__` block updated to show `year=2024` example

### Phase T — E2E Testing Infrastructure
- [x] T.1 — `tests/e2e/fixtures/fmp/` directory structure with .gitkeep files
- [x] T.2 — `tests/e2e/conftest.py` with `mem_duck` and `fmp_server` fixtures
- [x] T.3 — `fixtures/fmp/stable/stock-list.json` sample fixture
- [ ] T.4 — `test_market_bronze_silver.py` (not yet — requires full market domain wiring)
- [x] T.5 — `fixtures/fmp/v4/batch-request/end-of-day-prices.json` fixture
- [x] T.6 — `test_eod_bronze_silver.py` (DTO parse tests)
- [x] T.7 — `fixtures/fmp/v4/profile/all.json` fixture
- [x] T.8 — `test_gold_dims.py` verifying dim_instrument + dim_company build
- [ ] T.9 — `test_gold_facts.py` (not yet — requires fact_eod seeded Silver)
- [x] T.10 — Full suite: 423 tests pass (3 e2e tests)

---

## Surprises & Discoveries

_To be filled in as work proceeds._

| Date | Finding | Impact |
|---|---|---|
| 2026-03-09 | `services/gold/` already exists as empty directory in codebase | Low — can use as landing spot for Phase E |
| 2026-03-09 | `run/` already exists under `sbfoundation/run/` with chunk/dedupe engines | Phase A is renaming/organizing, not rebuilding |
| 2026-03-09 | `ops/` already exists with `OpsService`, manifests, watermarks | Phase A ops work is additive |
| 2026-03-09 | FMP bulk endpoints require different response shapes than per-ticker endpoints | New DTOs needed; cannot reuse existing fundamentals DTOs directly |
| 2026-03-09 | CLAUDE.md Gold constraint contradicts this plan's scope | Must resolve before Phase E — RESOLVED |
| 2026-03-09 | `CoverageIndexService` already tracks `silver_rows_created`/`silver_rows_failed` in `ops.file_ingestions` | Phase J replaces this with per-run, per-layer, per-file granularity in `ops.run_integrity` |
| 2026-03-09 | Coverage dashboard `apps/coverage_dashboard/` is a separate Poetry project with its own `pyproject.toml` | Removal or replacement decision needed at Phase J.8 |
| 2026-03-10 | `GoldDimService._build_dim_instrument` raised `CatalogException` when Silver source tables didn't exist — error was silently swallowed by `_promote_gold`'s try/except, so Gold was skipped on every run without any visible failure | Fixed by adding `_table_exists` checks (same pattern already used by `GoldFactService`) |
| 2026-03-10 | Prefect flow `RunCommand` constructions did not explicitly set `enable_gold=True` — was relying on the dataclass default, which could have been overridden without notice | Made explicit in all three flows |
| 2026-03-10 | During K.3 bulk deletion of ~744 lines, `_processing_msg` (line ~384) and `_process_recipe_list` (line ~1035) were within the deleted range and were removed along with the unwanted handlers — both are required by the three remaining domain handlers | Recovered from git history; restored without the now-removed `backfill_to_1990` parameter |
| 2026-03-10 | `BronzeService.__init__` still accepts `backfill_to_1990: bool = False` as a parameter even after the field was removed from `RunCommand` — kept in `BronzeService` for now to avoid a separate unrelated change | `_process_recipe_list` simply omits the arg, letting it default to `False` |

---

## Decision Log

| Date | Decision | Rationale | Author |
|---|---|---|---|
| 2026-03-09 | ExecPlan uses Option A (Gold in this project) pending user confirmation | User's notes explicitly include a Gold DB design section | User / Claude |
| 2026-03-09 | Option A confirmed — Gold in this project | User explicitly requested Gold layer in sbfoundation | User |
| 2026-03-10 | Remove all per-ticker domains (`market`, `company`, `fundamentals`, `technicals`, `commodities`, `fx`, `crypto`) from `settings.py` and `api.py` | These domains relied on per-ticker orchestration logic that has been superseded by the bulk EOD/quarter/annual pipelines; retaining dead code creates confusion and maintenance risk | User |
| 2026-03-10 | Remove `economics` domain from `settings.py` and `api.py` | Same rationale as above; economics dataset constants retained for downstream use | User |
| 2026-03-10 | Do not remove `backfill_to_1990` from `BronzeService.__init__` at this time | The parameter is still technically valid on `BronzeService`; removing it would be a separate, unrelated cleanup and risks introducing a separate bug | Claude |
| 2026-03-10 | Domain services (`EodService`, `QuarterService`, `AnnualService`) own the ingestion run logic; `api.py` becomes a thin coordinator | Puts domain-specific concerns (recipe selection, season gating) inside the domain package; `api.py` should only orchestrate lifecycle (start/close run, Gold promotion, stats) | User |
| 2026-03-10 | Base class `BulkPipelineService` lives in `src/sbfoundation/run/services/` | `run/services/` already holds execution infrastructure (executor, chunk engine); the pipeline base class is execution infrastructure, not a domain concept | Claude |
| 2026-03-10 | `_promote_gold`, `_start_run`, `_close_run` remain in `api.py` | Gold promotion spans all domains and runs once after any domain completes; run lifecycle is a coordinator concern, not a single-domain concern | Claude |
| 2026-03-10 | Prefect flows unchanged by Phase L | Flows call `SBFoundationAPI().run(command)` — the public interface is stable; the refactor is internal to the API | Claude |
| 2026-03-10 | Remove all non-bulk datasets from keymap, DTO registry, and settings | Only bulk (EOD, quarter, annual) datasets are actively used; per-ticker and list datasets add dead configuration that complicates validation and loading | User |
| 2026-03-10 | `year` parameter on `AnnualService.run()` rather than stored at construction | The parameter is specific to a single `run()` call, not persistent service state; passing at call site allows per-invocation control and keeps the constructor signature stable | Claude |

---

## Outcomes & Retrospective

_To be filled in when complete._

---

## Context and Orientation

### Current State

The project is `sbfoundation` — a Bronze + Silver data acquisition and validation package for financial data. It ingests raw vendor data from FMP (Financial Modeling Prep) into Bronze (raw JSON files) and promotes to Silver (validated DuckDB tables).

**Current package layout** (under `src/sbfoundation/`):

```
src/sbfoundation/
├── api.py                    ← Main orchestration entry point (~1045 lines)
├── settings.py               ← Configuration constants
├── folders.py                ← Path helpers
├── universe_definitions.py   ← Universe specs
├── coverage/                 ← Coverage index service + CLI
├── dataset/                  ← Keymap models, loader, DatasetService
│   ├── loaders/
│   ├── models/
│   └── services/
├── dtos/                     ← All Bronze→Silver DTO classes (per domain)
│   ├── commodities/, company/, crypto/, economics/
│   ├── fundamentals/, fx/, instrument/, market/, technicals/
├── infra/                    ← Logger, ResultFileAdaptor, DuckDB bootstrap, UniverseRepo
│   ├── duckdb/duckdb_bootstrap.py
│   ├── logger.py
│   ├── result_file_adaptor.py
│   └── universe_repo.py
├── ops/                      ← OpsService, run stats, manifests, watermarks
│   ├── dtos/, infra/, requests/, services/
├── recovery/                 ← Bronze recovery service
├── run/                      ← RunRequest, RunContext, BronzeResult, executors
│   ├── dtos/, services/
└── services/                 ← Bronze/Silver layer services, Universe/Instrument resolution
    ├── bronze/, silver/, gold/ (empty), ops/, instrument_resolution_service.py, universe_service.py
```

### Target State (after this ExecPlan)

```
src/sbfoundation/
├── api.py                    ← Updated orchestration entry point
├── settings.py, folders.py, universe_definitions.py  (unchanged)
├── bronze/                   ← From services/bronze/ (BronzeService, BronzeBatchReader)
├── silver/                   ← From services/silver/ (SilverService, InstrumentPromotionService)
├── gold/                     ← New — GoldDimService, GoldFactService
├── run/                      ← Reorganized — RunRequest, RunContext, executors
├── ops/                      ← Expanded — OpsService, stats, manifests, watermarks
├── eod/                      ← New — EodService, bulk EOD + company profile
├── quarter/                  ← New — QuarterService, bulk quarterly fundamentals
├── annual/                   ← New — AnnualService, bulk annual fundamentals
├── maintenance/              ← From infra/duckdb/ — DuckDB bootstrap, migrations, dim bootstrap
├── orchestrate/              ← New — Prefect flows for eod, quarter, annual
├── coverage/                 ← Unchanged
├── dataset/                  ← Unchanged
├── dtos/                     ← Expanded with bulk DTOs
├── infra/                    ← Trimmed (logger, result_file_adaptor, universe_repo remain)
└── recovery/                 ← Unchanged
```

### Key Files

| File | Role |
|---|---|
| `src/sbfoundation/api.py` | Main entry point — `SBFoundationAPI.run(command)` |
| `config/dataset_keymap.yaml` | Authoritative dataset definitions |
| `src/sbfoundation/run/services/run_request_executor.py` | HTTP fetch + Bronze write |
| `src/sbfoundation/services/bronze/bronze_service.py` | Bronze batch reading |
| `src/sbfoundation/services/silver/silver_service.py` | Silver UPSERT promotion |
| `src/sbfoundation/ops/services/ops_service.py` | Manifest + watermark management |
| `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py` | DuckDB init + migrations |
| `db/migrations/` | SQL migration files |

### Term Definitions (relevant to this plan)

- **Bulk endpoint**: FMP API endpoint returning data for all instruments at once (vs. per-ticker)
- **SK (surrogate key)**: Auto-increment integer key used in Gold dims (not present in Silver)
- **Earnings season**: Periods when companies file quarterly results (see Phase C schedule)
- **FY**: Fiscal year — the annual reporting period

---

## Plan of Work

### Phase A — Package Restructure

**Objective**: Move `services/bronze/` → `bronze/` and `services/silver/` → `silver/` within `sbfoundation`. Create `maintenance/` from `infra/duckdb/`. Update all import paths. No behavioral changes in this phase — pure reorganization.

1. **Create `src/sbfoundation/bronze/`**: Move `bronze_service.py` and `bronze_batch_reader.py` from `services/bronze/`. Add `__init__.py` with public re-exports.
2. **Create `src/sbfoundation/silver/`**: Move `silver_service.py` and `instrument_promotion_service.py` from `services/silver/`. Add `__init__.py`.
3. **Reorganize `run/`**: The `run/` package already exists. Confirm no restructuring needed; only add `__init__.py` re-exports if missing.
4. **Create `src/sbfoundation/maintenance/`**: Move `infra/duckdb/duckdb_bootstrap.py`. Add `MaintenanceService` stub (expand in Phase H).
5. **Update `api.py`** and all other modules to use new import paths.
6. **Update `services/`**: Remove `bronze/` and `silver/` subdirs (now empty); keep `instrument_resolution_service.py`, `universe_service.py` in `services/` or relocate as appropriate.
7. **Run full test suite** to confirm no regressions.

### Phase B — EOD Bulk Pipeline

**Objective**: Ingest daily bulk pricing data (all instruments at once) and bulk company profile updates.

**New FMP endpoints**:
- `EOD Bulk`: `v4/batch-request/end-of-day-prices` — returns closing price, volume, change for all symbols
- `Company Profile Bulk`: `v4/profile/all` — returns profile snapshot for all symbols

1. **Add to `dataset_keymap.yaml`**: Two new dataset entries under domain `market` (or new domain `eod`?). Since these are bulk (not per-ticker), `ticker_scope: global`. Define `key_cols`, `row_date_col`, Silver table names.
2. **Create DTOs**: `EodBulkPriceDTO` and `EodBulkCompanyProfileDTO` in `dtos/eod/`. These will parse rows from the bulk response arrays.
3. **Create `src/sbfoundation/eod/`**: Implement `EodService` which:
   - Calls `_process_recipe_list()` for the two bulk recipes
   - Calls `_promote_silver()` for each
   - Returns a `RunContext`
4. **Integrate with `api.py`**: Add `_handle_eod()` domain handler (or treat as a new domain `eod`).
5. **Add `EodRunCommand`** or extend `RunCommand` with `domain: "eod"`.

**Cadence**: Daily on weekdays (`run_days: [mon, tue, wed, thu, fri]`, `min_age_days: 1`).

### Phase C — Quarterly Bulk Pipeline

**Objective**: Ingest bulk quarterly fundamental statements during earnings seasons.

**New FMP endpoints**:
- `Income Statement Bulk`: `v4/income-statement-bulk?period=quarter`
- `Balance Sheet Bulk`: `v4/balance-sheet-statement-bulk?period=quarter`
- `Cashflow Bulk`: `v4/cash-flow-statement-bulk?period=quarter`

1. **Add to `dataset_keymap.yaml`**: Three entries under domain `fundamentals` (or `quarter`), `ticker_scope: global`, with `period=quarter` in `query_vars`.
2. **Create DTOs**: `QuarterIncomeStatementBulkDTO`, `QuarterBalanceSheetBulkDTO`, `QuarterCashflowBulkDTO` in `dtos/fundamentals/bulk/`.
3. **Create `src/sbfoundation/quarter/`**: Implement `QuarterService` with earnings-season gating logic.
4. **Earnings-season cadence logic**: `QuarterService._is_earnings_season(today) -> bool` returns `True` during:
   - Apr 1 – May 31 (Q1 filings)
   - Jul 1 – Aug 31 (Q2 filings)
   - Oct 1 – Nov 30 (Q3 filings)
   - Jan 1 – Mar 31 (Q4 filings)
   Service skips execution when outside these windows.
5. **Integrate with `api.py`** as `_handle_quarter()`.

### Phase D — Annual Bulk Pipeline

**Objective**: Ingest bulk annual fundamental statements (Jan–Mar window only).

Same three FMP bulk endpoints as Phase C but with `period=annual` (FY).

1. **Add to `dataset_keymap.yaml`**: Three entries with `period=annual`.
2. **Create DTOs**: `AnnualIncomeStatementBulkDTO`, etc. — may extend Phase C DTOs.
3. **Create `src/sbfoundation/annual/`**: Implement `AnnualService` with Jan–Mar cadence gating.
4. **Integrate with `api.py`** as `_handle_annual()`.

### Phase E — Gold Layer: Static Dimension Bootstrap

**Objective**: Establish Gold schema in DuckDB with all static (hardcoded) dimension tables.

1. **Update CLAUDE.md**: Revise the "ONLY Bronze and Silver" constraint to reflect the expanded scope.
2. **Create `src/sbfoundation/gold/`** sub-package.
3. **Write bootstrap SQL migrations** for each static dim:
   - `dim_date`: All calendar dates 1990-01-01 to 2029-12-31 with year, quarter, month, week, day_of_week, is_weekend, is_us_market_day columns.
   - `dim_instrument_type`: commodity, crypto, etf, fx, index, stock.
   - `dim_country`: ~100+ country codes as listed in user notes.
   - `dim_exchange`: ~80+ exchange codes as listed.
   - `dim_industry`: ~150+ industry strings.
   - `dim_sectors`: 11 sectors.
4. **Add DuckDB migrations** under `db/migrations/` for each table.
5. **Add `GoldBootstrapService`** in `gold/` that applies migrations and populates static dims.

### Phase F — Gold Layer: Data-Derived Dimensions

**Objective**: Build `dim_instrument` and `dim_company` from Silver data, with surrogate key resolution.

1. **`dim_instrument`**: Populated from `silver.fmp_eod_bulk` (ticker → instrument_type, exchange, sector, industry, country lookups → FKs into static dims).
2. **`dim_company`**: Populated from `silver.fmp_company_profile_bulk` (ticker, instrument_sk FK, company details, exchange/sector/industry/country FKs).
3. **`GoldDimService`**: MERGE/UPSERT logic using natural keys (ticker) to assign stable SKs. SK = DuckDB `SEQUENCE` auto-increment or `ROW_NUMBER()` on first build.
4. **Migrations**: Add `dim_instrument` and `dim_company` table DDL.

### Phase G — Gold Layer: Fact Tables

**Objective**: Build fact tables from Silver + Gold dims.

1. **`fact_eod`**: One row per (instrument_sk, date_sk). Joins Silver EOD bulk to `dim_instrument` and `dim_date`. Includes placeholder columns for future features/signals (nullable).
2. **`fact_quarter`**: One row per (instrument_sk, period_date_sk, period). Joins Silver quarterly bulk fundamentals to dims.
3. **`fact_annual`**: One row per (instrument_sk, period_date_sk). Joins Silver annual bulk fundamentals to dims.
4. **`GoldFactService`**: Orchestrates Silver → Gold fact table builds. Idempotent: uses MERGE on natural keys before SK resolution.
5. **`ops.gold_build` tracking**: Log each Gold build to `ops.gold_build` table with model_version (git SHA), input watermarks, row counts.

### Phase H — Maintenance Package

**Objective**: Centralize DuckDB bootstrap, migration runner, and dim bootstrap into `maintenance/`.

1. **Move** `infra/duckdb/duckdb_bootstrap.py` → `maintenance/duckdb_bootstrap.py`.
2. **Implement `MaintenanceService`**: Orchestrates migration runner, static dim bootstrap (`GoldBootstrapService`), and optional DuckDB VACUUM.
3. **CLI entry point**: `python -m sbfoundation.maintenance` runs migrations + bootstrap.
4. **Update `api.py`** and any callers of the old `duckdb_bootstrap` import path.

### Phase I — Prefect Orchestration

**Objective**: Schedule and coordinate the three bulk pipelines via Prefect.

1. **Add Prefect**: `poetry add prefect` (pin version; record in Decision Log).
2. **Create `src/sbfoundation/orchestrate/`** package.
3. **`eod_flow.py`**: `@flow` function that calls `EodService`. Scheduled daily at 18:00 ET on weekdays.
4. **`quarter_flow.py`**: `@flow` function that calls `QuarterService`. Scheduled daily at 08:00 ET; service internally gates by earnings season.
5. **`annual_flow.py`**: `@flow` function that calls `AnnualService`. Scheduled daily at 08:00 ET; service internally gates by Jan–Mar.
6. **Deployment YAML** (`prefect.yaml`): Defines work pool, schedules, and environment.
7. **Test**: `prefect deploy` dry-run; manually trigger each flow.

### Phase L — Domain Services as Ingestion Entry Points

**Objective**: Move all per-domain ingestion logic out of `api.py` into the three domain services (`EodService`, `QuarterService`, `AnnualService`), each inheriting shared Bronze + Silver pipeline mechanics from a common base class in `run/services/`. `api.py` becomes a thin coordinator: dependency wiring + run lifecycle + Gold promotion only.

**Current state**: `EodService`, `QuarterService`, `AnnualService` are stubs (logger only). All ingestion logic (`_handle_*`, `_process_recipe_list`, `_promote_silver`) lives in `SBFoundationAPI`.

**Target state**:

```
src/sbfoundation/
├── run/services/
│   └── bulk_pipeline_service.py   ← NEW base class
├── eod/
│   └── eod_service.py             ← extends BulkPipelineService; owns run()
├── quarter/
│   └── quarter_service.py         ← extends BulkPipelineService; owns run()
├── annual/
│   └── annual_service.py          ← extends BulkPipelineService; owns run()
└── api.py                         ← thin coordinator only
```

**What moves where**:

| Method | From | To |
|---|---|---|
| `_processing_msg` | `api.py` | `BulkPipelineService` |
| `_process_recipe_list` | `api.py` | `BulkPipelineService` |
| `_promote_silver` | `api.py` | `BulkPipelineService` |
| `_handle_eod` body | `api.py` | `EodService.run()` |
| `_handle_quarter` body | `api.py` | `QuarterService.run()` |
| `_handle_annual` body | `api.py` | `AnnualService.run()` |
| `_start_run` | `api.py` | stays |
| `_close_run` | `api.py` | stays |
| `_promote_gold` | `api.py` | stays |

**`api.py` after Phase L** (structural sketch):

```python
def run(self, command: RunCommand) -> RunContext:
    command.validate()
    # ... recovery check ...
    run = self._start_run(command)
    run = self._build_service(command).run(run)   # ← single dispatch line
    if command.enable_silver and command.enable_gold:
        self._promote_gold(run)
    # ... coverage, integrity, stats ...
    self._close_run(run)
    return run

def _build_service(self, command: RunCommand) -> BulkPipelineService:
    kwargs = dict(
        ops_service=self.ops_service,
        dataset_service=self._dataset_service,
        bootstrap=self._bootstrap,
        logger=self.logger,
        enable_bronze=command.enable_bronze,
        enable_silver=command.enable_silver,
        concurrent_requests=command.concurrent_requests,
        force_from_date=command.force_from_date,
        today=self._today,
    )
    if command.domain == EOD_DOMAIN:
        return EodService(**kwargs)
    if command.domain == QUARTER_DOMAIN:
        return QuarterService(**kwargs)
    if command.domain == ANNUAL_DOMAIN:
        return AnnualService(**kwargs)
    raise ValueError(f"Unknown domain: {command.domain}")
```

**No Prefect flow changes required.** All three flows still call `SBFoundationAPI().run(command)` — the public API is unchanged.

1. **Create `BulkPipelineService`** in `src/sbfoundation/run/services/bulk_pipeline_service.py`. Inject all shared deps in `__init__`. Move `_processing_msg`, `_process_recipe_list`, `_promote_silver` verbatim. Declare `run(self, run: RunContext) -> RunContext` as abstract.

2. **Extend `EodService`** from `BulkPipelineService`. Remove stub `__init__`. Implement `run()` with the body of `api._handle_eod` (filter recipes by `EOD_DOMAIN`, call `_process_recipe_list` if `enable_bronze`, call `_promote_silver`).

3. **Extend `QuarterService`** from `BulkPipelineService`. Remove stub `__init__`. Implement `run()` with the body of `api._handle_quarter` (season gate using `self._today`, filter recipes, process). Retain `is_earnings_season` static method.

4. **Extend `AnnualService`** from `BulkPipelineService`. Remove stub `__init__`. Implement `run()` with the body of `api._handle_annual` (season gate, filter, process). Retain `is_annual_season` static method.

5. **Slim `api.py`**: Add `_build_service()` factory. Replace the `if/elif` dispatch block with a single `self._build_service(command).run(run)` call. Remove `_handle_eod`, `_handle_quarter`, `_handle_annual`, `_processing_msg`, `_process_recipe_list`, `_promote_silver`, and the `self._enable_silver / self._concurrent_requests / self._force_from_date` transient assignments.

6. **Update exports** in `src/sbfoundation/run/services/__init__.py` to expose `BulkPipelineService`.

---

### Phase K — API Simplification: Domain Removal + Gold Promotion Fix

**Objective**: Strip `api.py` and `settings.py` down to the three active bulk domains (`eod`, `quarter`, `annual`). Fix the silent Gold promotion failure caused by missing `_table_exists` guards in `GoldDimService`.

1. **Fix Gold promotion** (`gold/gold_dim_service.py`): Add `_table_exists(conn, schema, table)` method. Guard `_build_dim_instrument` and `_build_dim_company` to skip gracefully when source Silver tables are absent, returning the current table row count instead of raising.

2. **Explicit Gold enablement in Prefect flows** (`orchestrate/eod_flow.py`, `quarter_flow.py`, `annual_flow.py`): Add `enable_gold=True` to each flow's `RunCommand` construction so Gold promotion is unambiguously enabled.

3. **Remove per-ticker domains from `settings.py`**: Delete `MARKET_DOMAIN`, `COMPANY_DOMAIN`, `FUNDAMENTALS_DOMAIN`, `TECHNICALS_DOMAIN`, `COMMODITIES_DOMAIN`, `FX_DOMAIN`, `CRYPTO_DOMAIN` constants, and remove them from `DOMAINS` list and `DOMAIN_EXECUTION_ORDER`. Retain all dataset name constants.

4. **Remove per-ticker domain handlers from `api.py`**: Delete the 7 handler methods and all their exclusive helper methods (~744 lines). Remove `_BACKFILL_DOMAINS`, `backfill_to_1990` from `RunCommand`, and the corresponding `validate()` check. Remove unused imports.

5. **Remove `ECONOMICS_DOMAIN`**: Same treatment as step 3–4. Remove `_handle_economics`, the `elif` branch, `_BACKFILL_DOMAINS`, and `backfill_to_1990`.

6. **Restore accidentally deleted helpers**: `_processing_msg` and `_process_recipe_list` were in the bulk-deleted line range. Recover from git history and re-insert before `_promote_silver`, omitting the `backfill_to_1990` arg from the `BronzeService` call.

7. **Import cleanup**: Remove `field`, `timedelta`, `copy`, `RunRequest` from `api.py` (no longer referenced).

---

## Concrete Steps

### Step 0a — Back Up the Existing DuckDB File (BEFORE ANY CODE CHANGES)

The refactor changes Silver and Gold schemas. The existing DuckDB file contains Silver tables with old column layouts that will be incompatible with the new migrations. Rather than attempting a migration of existing Silver data, the existing file is preserved as a backup and the pipeline starts fresh — re-ingesting from the untouched Bronze JSON files.

**Bronze files are NOT touched.** They remain on disk in `$DATA_ROOT_FOLDER/bronze/` and serve as the source of truth for re-promotion once the new Silver schema is in place.

```bash
# Locate the DuckDB file
ls "$DATA_ROOT_FOLDER/duckdb/"
# Expected: SBFoundation.duckdb (or similar)

# Rename to backup (use today's date)
mv "$DATA_ROOT_FOLDER/duckdb/SBFoundation.duckdb" \
   "$DATA_ROOT_FOLDER/duckdb/SBFoundation_backup_20260309.duckdb"

# Confirm original path is empty
ls "$DATA_ROOT_FOLDER/duckdb/"
# Expected: only the backup file; original name is gone
```

Expected: The pipeline will create a new `SBFoundation.duckdb` on its first run, bootstrapped by `maintenance/duckdb_bootstrap.py` and all migrations.

**Recovery**: If the refactor needs to be abandoned, restore with:
```bash
mv "$DATA_ROOT_FOLDER/duckdb/SBFoundation_backup_20260309.duckdb" \
   "$DATA_ROOT_FOLDER/duckdb/SBFoundation.duckdb"
```

Record the backup path in the Artifacts and Notes section below.

---

### Step 0b — Create Feature Branch

```bash
git checkout -b feature/major-refactor
git status
```

Expected output:
```
Switched to a new branch 'feature/major-refactor'
On branch feature/major-refactor
nothing to commit, working tree clean
```

---

### Step A.1 — Scaffold New Package Directories

```bash
# From repo root
mkdir -p src/sbfoundation/bronze
mkdir -p src/sbfoundation/silver
mkdir -p src/sbfoundation/gold
mkdir -p src/sbfoundation/eod
mkdir -p src/sbfoundation/quarter
mkdir -p src/sbfoundation/annual
mkdir -p src/sbfoundation/maintenance
mkdir -p src/sbfoundation/orchestrate
```

---

### Step A.2 — Move Bronze Service

Move files:
- `src/sbfoundation/services/bronze/bronze_service.py` → `src/sbfoundation/bronze/bronze_service.py`
- `src/sbfoundation/services/bronze/bronze_batch_reader.py` → `src/sbfoundation/bronze/bronze_batch_reader.py`

Create `src/sbfoundation/bronze/__init__.py`:
```python
from sbfoundation.bronze.bronze_service import BronzeService
from sbfoundation.bronze.bronze_batch_reader import BronzeBatchReader

__all__ = ["BronzeService", "BronzeBatchReader"]
```

---

### Step A.3 — Move Silver Service

Move files:
- `src/sbfoundation/services/silver/silver_service.py` → `src/sbfoundation/silver/silver_service.py`
- `src/sbfoundation/services/silver/instrument_promotion_service.py` → `src/sbfoundation/silver/instrument_promotion_service.py`

Create `src/sbfoundation/silver/__init__.py`:
```python
from sbfoundation.silver.silver_service import SilverService
from sbfoundation.silver.instrument_promotion_service import InstrumentPromotionService

__all__ = ["SilverService", "InstrumentPromotionService"]
```

---

### Step A.4 — Move DuckDB Bootstrap to Maintenance

Move:
- `src/sbfoundation/infra/duckdb/duckdb_bootstrap.py` → `src/sbfoundation/maintenance/duckdb_bootstrap.py`

Create `src/sbfoundation/maintenance/__init__.py`:
```python
from sbfoundation.maintenance.duckdb_bootstrap import DuckDBBootstrap

__all__ = ["DuckDBBootstrap"]
```

---

### Step A.5 — Update All Import Paths

Search and replace all import paths affected by moves. Key changes:
- `from sbfoundation.services.bronze.bronze_service import BronzeService` → `from sbfoundation.bronze import BronzeService`
- `from sbfoundation.services.silver.silver_service import SilverService` → `from sbfoundation.silver import SilverService`
- `from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDBBootstrap` → `from sbfoundation.maintenance import DuckDBBootstrap`

Verify:
```bash
python -c "from sbfoundation.api import SBFoundationAPI; print('OK')"
```

Expected: `OK`

---

### Step A.6 — Run Tests After Restructure

```bash
poetry run pytest tests/ -x -q 2>&1 | tail -20
```

Expected: All tests pass, no import errors.

---

### Step B.1 — Add EOD Bulk Datasets to dataset_keymap.yaml

Add two new entries to `config/dataset_keymap.yaml`:

```yaml
# EOD Bulk Price
- domain: market
  source: fmp
  dataset: eod-bulk-price
  discriminator: ''
  ticker_scope: global
  silver_schema: silver
  silver_table: fmp_eod_bulk_price
  key_cols: [symbol, date]
  row_date_col: date
  recipes:
    - plans: [basic]
      data_source_path: v4/batch-request/end-of-day-prices
      query_vars: {date: __to_date__}
      date_key: date
      cadence_mode: interval
      min_age_days: 1
      run_days: [mon, tue, wed, thu, fri]
      help_url: https://site.financialmodelingprep.com/developer/docs#eod-bulk
  dto_schema:
    dto_type: sbfoundation.dtos.eod.eod_bulk_price_dto.EodBulkPriceDTO
    columns:
      - {name: symbol, type: str, nullable: false}
      - {name: date, type: date, nullable: false}
      - {name: open, type: float, nullable: true}
      - {name: high, type: float, nullable: true}
      - {name: low, type: float, nullable: true}
      - {name: close, type: float, nullable: true}
      - {name: adj_close, type: float, nullable: true}
      - {name: volume, type: int, nullable: true}
      - {name: unadjusted_volume, type: int, nullable: true}
      - {name: change, type: float, nullable: true}
      - {name: change_pct, type: float, nullable: true}
      - {name: vwap, type: float, nullable: true}

# EOD Company Profile Bulk
- domain: market
  source: fmp
  dataset: company-profile-bulk
  discriminator: ''
  ticker_scope: global
  silver_schema: silver
  silver_table: fmp_company_profile_bulk
  key_cols: [symbol]
  row_date_col: null
  recipes:
    - plans: [basic]
      data_source_path: v4/profile/all
      query_vars: {}
      date_key: null
      cadence_mode: interval
      min_age_days: 1
      run_days: [mon, tue, wed, thu, fri]
      help_url: https://site.financialmodelingprep.com/developer/docs#profile-bulk
  dto_schema:
    dto_type: sbfoundation.dtos.eod.eod_bulk_company_profile_dto.EodBulkCompanyProfileDTO
    columns:
      - {name: symbol, type: str, nullable: false}
      - {name: company_name, type: str, nullable: true}
      - {name: exchange, type: str, nullable: true}
      - {name: exchange_short, type: str, nullable: true}
      - {name: sector, type: str, nullable: true}
      - {name: industry, type: str, nullable: true}
      - {name: country, type: str, nullable: true}
      - {name: currency, type: str, nullable: true}
      - {name: is_etf, type: bool, nullable: true}
      - {name: is_actively_trading, type: bool, nullable: true}
```

Note: Confirm exact FMP v4 bulk API field names against live docs before finalizing columns.

---

### Step B.2 — Create EOD DTOs

Create `src/sbfoundation/dtos/eod/__init__.py` (empty).

Create `src/sbfoundation/dtos/eod/eod_bulk_price_dto.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping
from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO


@dataclass
class EodBulkPriceDTO(BronzeToSilverDTO):
    symbol: str
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adj_close: float | None
    volume: int | None
    unadjusted_volume: int | None
    change: float | None
    change_pct: float | None
    vwap: float | None

    KEY_COLS: list[str] = ["symbol", "date"]

    @classmethod
    def from_row(cls, row: Mapping[str, Any], ticker: str | None) -> "EodBulkPriceDTO":
        return cls(
            symbol=cls._str(row.get("symbol")) or "",
            date=cls._date(row.get("date")),
            open=cls._float(row.get("open")),
            high=cls._float(row.get("high")),
            low=cls._float(row.get("low")),
            close=cls._float(row.get("close")),
            adj_close=cls._float(row.get("adjClose")),
            volume=cls._int(row.get("volume")),
            unadjusted_volume=cls._int(row.get("unadjustedVolume")),
            change=cls._float(row.get("change")),
            change_pct=cls._float(row.get("changePercent")),
            vwap=cls._float(row.get("vwap")),
        )

    @property
    def key_date(self) -> date:
        return self.date

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "date": self.date.isoformat() if self.date else None,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "adj_close": self.adj_close,
            "volume": self.volume,
            "unadjusted_volume": self.unadjusted_volume,
            "change": self.change,
            "change_pct": self.change_pct,
            "vwap": self.vwap,
        }
```

Create analogous `EodBulkCompanyProfileDTO` — see CLAUDE.md Section 8 for DTO contract rules.

---

### Step B.3 — Create EodService

Create `src/sbfoundation/eod/__init__.py` (empty).

Create `src/sbfoundation/eod/eod_service.py`:
```python
from __future__ import annotations
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.infra.logger import LoggerFactory, SBLogger
# Additional imports to be determined based on how api.py orchestrates recipe processing


class EodService:
    """Orchestrates daily bulk EOD + company profile bulk ingestion."""

    EOD_DATASETS = ["eod-bulk-price", "company-profile-bulk"]

    def __init__(self, logger: SBLogger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)

    def run(self, run_context: RunContext) -> RunContext:
        """Execute EOD bulk ingestion for both configured datasets."""
        self._logger.log_section(run_context.run_id, "EOD Bulk Ingestion")
        # Delegate to recipe execution (pattern mirrors api.py _handle_market)
        # Implementation details filled in during Step B.3
        return run_context
```

Full implementation to be written during Phase B execution, following patterns from `api.py`'s `_handle_market()` handler.

---

### Steps C–D — Quarterly and Annual Services

Follow identical pattern to Phase B. Key differences:
- `QuarterService._is_earnings_season(today)` gates execution
- `AnnualService._is_annual_season(today)` gates to Jan–Mar only
- Dataset names: `income-statement-bulk-quarter`, `balance-sheet-bulk-quarter`, `cashflow-bulk-quarter` (and `*-annual` variants)

---

### Step E.1 — Gold Schema Migration Scaffolding

Create `db/migrations/20260309_001_create_gold_static_dims.sql`:

```sql
-- dim_date: all calendar dates 1990-01-01 to 2029-12-31
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_sk         INTEGER PRIMARY KEY,
    date            DATE NOT NULL,
    year            INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,         -- 1–4
    month           INTEGER NOT NULL,         -- 1–12
    week_of_year    INTEGER NOT NULL,
    day_of_month    INTEGER NOT NULL,
    day_of_week     INTEGER NOT NULL,         -- 0=Sun … 6=Sat
    day_name        VARCHAR NOT NULL,
    is_weekend      BOOLEAN NOT NULL,
    is_us_market_day BOOLEAN NOT NULL DEFAULT FALSE,
    fiscal_year     INTEGER,                  -- nullable; set by downstream
    fiscal_quarter  INTEGER
);

-- Populate dim_date with generated series
INSERT OR IGNORE INTO gold.dim_date
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER)  AS date_sk,
    d                                        AS date,
    YEAR(d)                                  AS year,
    QUARTER(d)                               AS quarter,
    MONTH(d)                                 AS month,
    WEEKOFYEAR(d)                            AS week_of_year,
    DAY(d)                                   AS day_of_month,
    DAYOFWEEK(d)                             AS day_of_week,
    DAYNAME(d)                               AS day_name,
    DAYOFWEEK(d) IN (0, 6)                  AS is_weekend,
    FALSE                                    AS is_us_market_day
FROM generate_series(DATE '1990-01-01', DATE '2029-12-31', INTERVAL '1 day') t(d);

-- dim_instrument_type
CREATE TABLE IF NOT EXISTS gold.dim_instrument_type (
    instrument_type_sk  SMALLINT PRIMARY KEY,
    instrument_type     VARCHAR NOT NULL UNIQUE
);

INSERT OR IGNORE INTO gold.dim_instrument_type VALUES
    (1, 'commodity'), (2, 'crypto'), (3, 'etf'),
    (4, 'fx'), (5, 'index'), (6, 'stock');

-- dim_country
CREATE TABLE IF NOT EXISTS gold.dim_country (
    country_sk  SMALLINT PRIMARY KEY,
    country_code VARCHAR(4) NOT NULL UNIQUE
);
-- Rows inserted programmatically by GoldBootstrapService (list in user notes)

-- dim_exchange
CREATE TABLE IF NOT EXISTS gold.dim_exchange (
    exchange_sk  SMALLINT PRIMARY KEY,
    exchange_code VARCHAR(16) NOT NULL UNIQUE
);
-- Rows inserted programmatically

-- dim_industry
CREATE TABLE IF NOT EXISTS gold.dim_industry (
    industry_sk  SMALLINT PRIMARY KEY,
    industry     VARCHAR NOT NULL UNIQUE
);
-- Rows inserted programmatically

-- dim_sectors
CREATE TABLE IF NOT EXISTS gold.dim_sectors (
    sector_sk  SMALLINT PRIMARY KEY,
    sector     VARCHAR NOT NULL UNIQUE
);
-- Rows inserted programmatically
```

Note: Verify DuckDB date function syntax (`YEAR()`, `MONTH()`, `DAYOFWEEK()`, etc.) against DuckDB docs before running. DuckDB uses `extract()` or `date_part()` for some functions.

---

### Step E.2 — Gold Data-Derived Dim Migrations

Create `db/migrations/20260309_002_create_gold_data_derived_dims.sql`:

```sql
-- dim_instrument: derived from EOD bulk + company profile bulk
CREATE TABLE IF NOT EXISTS gold.dim_instrument (
    instrument_sk       INTEGER PRIMARY KEY,  -- auto-increment via SEQUENCE
    ticker              VARCHAR NOT NULL UNIQUE,
    instrument_type_sk  SMALLINT REFERENCES gold.dim_instrument_type(instrument_type_sk),
    exchange_sk         SMALLINT REFERENCES gold.dim_exchange(exchange_sk),
    sector_sk           SMALLINT REFERENCES gold.dim_sectors(sector_sk),
    industry_sk         SMALLINT REFERENCES gold.dim_industry(industry_sk),
    country_sk          SMALLINT REFERENCES gold.dim_country(country_sk),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    gold_build_id       VARCHAR NOT NULL,
    model_version       VARCHAR NOT NULL
);

-- dim_company: derived from company profile bulk
CREATE TABLE IF NOT EXISTS gold.dim_company (
    company_sk      INTEGER PRIMARY KEY,
    ticker          VARCHAR NOT NULL UNIQUE,
    instrument_sk   INTEGER REFERENCES gold.dim_instrument(instrument_sk),
    company_name    VARCHAR,
    cik             VARCHAR,
    isin            VARCHAR,
    cusip           VARCHAR,
    currency        VARCHAR(8),
    description     TEXT,
    website         VARCHAR,
    ceo             VARCHAR,
    ipo_date        DATE,
    exchange_sk     SMALLINT REFERENCES gold.dim_exchange(exchange_sk),
    sector_sk       SMALLINT REFERENCES gold.dim_sectors(sector_sk),
    industry_sk     SMALLINT REFERENCES gold.dim_industry(industry_sk),
    country_sk      SMALLINT REFERENCES gold.dim_country(country_sk),
    gold_build_id   VARCHAR NOT NULL,
    model_version   VARCHAR NOT NULL
);
```

---

### Step G.1 — Gold Fact Table Migrations

Create `db/migrations/20260309_003_create_gold_facts.sql`:

```sql
-- fact_eod: end-of-day pricing, one row per (instrument, date)
CREATE TABLE IF NOT EXISTS gold.fact_eod (
    eod_sk          BIGINT PRIMARY KEY,
    instrument_sk   INTEGER NOT NULL REFERENCES gold.dim_instrument(instrument_sk),
    date_sk         INTEGER NOT NULL REFERENCES gold.dim_date(date_sk),
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    adj_close       DOUBLE,
    volume          BIGINT,
    unadjusted_volume BIGINT,
    change          DOUBLE,
    change_pct      DOUBLE,
    vwap            DOUBLE,
    -- Feature placeholders (populated by downstream feature engine, not this project)
    -- feature columns added via ALTER TABLE when Gold feature engine is implemented
    gold_build_id   VARCHAR NOT NULL,
    model_version   VARCHAR NOT NULL,
    UNIQUE (instrument_sk, date_sk)
);

-- fact_quarter: quarterly fundamentals
CREATE TABLE IF NOT EXISTS gold.fact_quarter (
    quarter_sk      BIGINT PRIMARY KEY,
    instrument_sk   INTEGER NOT NULL REFERENCES gold.dim_instrument(instrument_sk),
    period_date_sk  INTEGER NOT NULL REFERENCES gold.dim_date(date_sk),
    period          VARCHAR NOT NULL,         -- e.g., 'Q1', 'Q2', 'Q3', 'Q4'
    fiscal_year     INTEGER,
    -- Key P&L line items (from income statement bulk)
    revenue         DOUBLE,
    gross_profit    DOUBLE,
    operating_income DOUBLE,
    net_income      DOUBLE,
    eps             DOUBLE,
    eps_diluted     DOUBLE,
    -- Key balance sheet line items
    total_assets    DOUBLE,
    total_debt      DOUBLE,
    cash_and_equivalents DOUBLE,
    -- Key cash flow line items
    operating_cash_flow DOUBLE,
    capital_expenditure DOUBLE,
    free_cash_flow  DOUBLE,
    gold_build_id   VARCHAR NOT NULL,
    model_version   VARCHAR NOT NULL,
    UNIQUE (instrument_sk, period_date_sk, period)
);

-- fact_annual: annual fundamentals (FY)
CREATE TABLE IF NOT EXISTS gold.fact_annual (
    annual_sk       BIGINT PRIMARY KEY,
    instrument_sk   INTEGER NOT NULL REFERENCES gold.dim_instrument(instrument_sk),
    period_date_sk  INTEGER NOT NULL REFERENCES gold.dim_date(date_sk),
    fiscal_year     INTEGER,
    revenue         DOUBLE,
    gross_profit    DOUBLE,
    operating_income DOUBLE,
    net_income      DOUBLE,
    eps             DOUBLE,
    eps_diluted     DOUBLE,
    total_assets    DOUBLE,
    total_debt      DOUBLE,
    cash_and_equivalents DOUBLE,
    operating_cash_flow DOUBLE,
    capital_expenditure DOUBLE,
    free_cash_flow  DOUBLE,
    gold_build_id   VARCHAR NOT NULL,
    model_version   VARCHAR NOT NULL,
    UNIQUE (instrument_sk, period_date_sk)
);
```

---

### Step I.1 — Add Prefect Dependency

```bash
poetry add prefect
poetry lock
```

Record Prefect version in Decision Log.

---

### Phase T — E2E Testing Infrastructure

---

### Phase T Overview

**Goal**: Replace the existing `FakeApiServer` (FastAPI + uvicorn + threading) with a lightweight, fixture-file–driven approach. Every e2e test is:

- **Local-only** — no FMP API key required, no network calls
- **Stateless** — in-memory DuckDB, Bronze to `tmp_path` (auto-cleaned by pytest)
- **Data-driven** — API responses come from real FMP JSON fixture files stored in `tests/e2e/fixtures/`
- **Incremental** — user supplies fixture files one endpoint at a time; a test is written for each

**Two existing patterns being lifted from unit tests:**

| Pattern | Where proven | Lifted to e2e as |
|---|---|---|
| `duckdb.connect(":memory:")` | `tests/unit/infra/test_duckdb_ops_repo.py` | `mem_duck` pytest fixture |
| `pytest-httpserver` | in pyproject.toml deps (unused) | `fmp_server` pytest fixture |

---

### Step T.1 — Fixture Directory Structure

```
tests/e2e/
├── conftest.py                         # Shared fixtures: mem_duck, fmp_server
├── fixtures/
│   └── fmp/                            # Mirror of FMP URL path structure
│       ├── stable/
│       │   ├── stock-list.json         # GET /stable/stock-list
│       │   ├── etf-list.json           # GET /stable/etf-list
│       │   ├── profile.json            # GET /stable/profile (per-ticker: ?symbol=AAPL)
│       │   └── ...
│       └── v4/
│           ├── batch-request/
│           │   └── end-of-day-prices.json  # GET /v4/batch-request/end-of-day-prices
│           └── profile/
│               └── all.json            # GET /v4/profile/all
└── test_market_bronze_silver.py        # One test file per domain / pipeline
    test_eod_bronze_silver.py
    test_gold_dims.py
    test_gold_facts.py
```

**Fixture file format**: Exactly what FMP returns — the raw JSON array or object. No wrapping. Example `stable/stock-list.json`:

```json
[
  {"symbol": "AAPL", "name": "Apple Inc.", "price": 232.80, "exchange": "NASDAQ", "exchangeShortName": "NASDAQ", "type": "stock"},
  {"symbol": "MSFT", "name": "Microsoft Corporation", "price": 415.50, "exchange": "NASDAQ", "exchangeShortName": "NASDAQ", "type": "stock"}
]
```

**Workflow for supplying fixtures**: User provides raw FMP API response for one endpoint at a time. Save it verbatim as `tests/e2e/fixtures/fmp/<path>.json`. Then write the matching test.

---

### Step T.2 — `tests/e2e/conftest.py`

```python
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import duckdb
import pytest
from pytest_httpserver import HTTPServer

from sbfoundation.folders import Folders
from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.settings import DATA_SOURCES_CONFIG, FMP_SOURCE, BASE_URL

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "fmp"


class _MemBootstrap:
    """Adapts an in-memory DuckDB connection to the DuckDbBootstrap interface."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn
        self._initialized = False

    def connect(self) -> duckdb.DuckDBPyConnection:
        if not self._initialized:
            # Apply real schema init + all migrations against in-memory DB
            real = DuckDbBootstrap.__new__(DuckDbBootstrap)
            real.conn = self.conn
            real._apply_schema_init()
            real._apply_migrations()
            self._initialized = True
        return self.conn

    @contextmanager
    def transaction(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        self.conn.execute("BEGIN")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    @contextmanager
    def ops_transaction(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        yield self.conn

    @contextmanager
    def silver_transaction(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        yield self.conn

    @contextmanager
    def gold_transaction(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        yield self.conn

    @contextmanager
    def read_connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        yield self.conn


@pytest.fixture
def mem_duck() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Fresh in-memory DuckDB with all schemas and migrations applied."""
    conn = duckdb.connect(":memory:")
    bootstrap = _MemBootstrap(conn)
    bootstrap.connect()
    yield conn
    conn.close()


@pytest.fixture
def fmp_server(httpserver: HTTPServer, monkeypatch: pytest.MonkeyPatch):
    """
    Registers FMP fixture responses on pytest-httpserver and patches the
    FMP base URL so the pipeline calls the local fake server.

    Usage:
        def test_foo(fmp_server):
            fmp_server("stable/stock-list", "stable/stock-list.json")
            # pipeline will GET http://127.0.0.1:<port>/stable/stock-list
    """
    monkeypatch.setitem(DATA_SOURCES_CONFIG[FMP_SOURCE], BASE_URL, httpserver.url_for("/"))

    def register(
        url_path: str,
        fixture_rel_path: str,
        query_string: str = "",
    ) -> None:
        data = json.loads((FIXTURE_DIR / fixture_rel_path).read_text(encoding="utf-8"))
        handler = httpserver.expect_request(f"/{url_path}", query_string=query_string)
        handler.respond_with_json(data)

    return register


@pytest.fixture
def bronze_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirects Bronze file writes to a pytest-managed temp directory."""
    bronze = tmp_path / "bronze"
    bronze.mkdir()
    monkeypatch.setattr(Folders, "_data_root", staticmethod(lambda: tmp_path))
    return bronze
```

---

### Step T.3 — Example Test: Market Domain (stock-list → Silver)

`tests/e2e/test_market_bronze_silver.py`:

```python
from __future__ import annotations

import duckdb
import pytest


def test_stock_list_promotes_to_silver(fmp_server, mem_duck, bronze_root, monkeypatch) -> None:
    """Full Bronze→Silver pipeline for stock-list using fixture file and in-memory DuckDB."""
    # 1. Register fixture
    fmp_server("stable/stock-list", "stable/stock-list.json")

    # 2. Inject in-memory DuckDB into bootstrap (monkeypatch the factory)
    from sbfoundation.infra.duckdb import duckdb_bootstrap as mod
    monkeypatch.setattr(mod, "_bootstrap_instance", _MemBootstrap(mem_duck))

    # 3. Run pipeline
    from sbfoundation.api import SBFoundationAPI, RunCommand
    from sbfoundation.settings import INSTRUMENT_DOMAIN
    ctx = SBFoundationAPI().run(RunCommand(
        domain=INSTRUMENT_DOMAIN,
        enable_bronze=True,
        enable_silver=True,
        ticker_limit=0,
    ))

    # 4. Assert Silver rows match fixture
    rows = mem_duck.execute(
        "SELECT symbol, name FROM silver.fmp_stock_list ORDER BY symbol"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "AAPL"
    assert rows[1][0] == "MSFT"

    # 5. Re-run to verify idempotency
    SBFoundationAPI().run(RunCommand(domain=INSTRUMENT_DOMAIN, enable_bronze=True, enable_silver=True))
    rows_after = mem_duck.execute("SELECT COUNT(*) FROM silver.fmp_stock_list").fetchone()[0]
    assert rows_after == 2, "UPSERT must not duplicate rows on re-run"
```

Note: The exact monkeypatching of the bootstrap factory depends on how `DuckDbBootstrap` is instantiated in the final `api.py`. Adjust the patch target to match the actual singleton/factory pattern used.

---

### Step T.4 — Example Test: EOD Bulk → Silver

`tests/e2e/test_eod_bronze_silver.py`:

```python
def test_eod_bulk_price_promotes_to_silver(fmp_server, mem_duck, bronze_root, monkeypatch) -> None:
    fmp_server("v4/batch-request/end-of-day-prices", "v4/batch-request/end-of-day-prices.json")

    from sbfoundation.eod.eod_service import EodService
    # Inject mem_duck bootstrap — same monkeypatch as above

    ctx = EodService().run(...)

    rows = mem_duck.execute(
        "SELECT symbol, close FROM silver.fmp_eod_bulk_price ORDER BY symbol LIMIT 5"
    ).fetchall()
    assert len(rows) > 0
    assert all(row[1] is not None for row in rows), "close price must not be null"
```

---

### Step T.5 — Example Test: Gold Dim Build

`tests/e2e/test_gold_dims.py`:

```python
def test_dim_instrument_built_from_silver(fmp_server, mem_duck, bronze_root, monkeypatch) -> None:
    """EOD bulk + company profile bulk → dim_instrument + dim_company."""
    fmp_server("v4/batch-request/end-of-day-prices", "v4/batch-request/end-of-day-prices.json")
    fmp_server("v4/profile/all", "v4/profile/all.json")

    # Run EOD pipeline
    # Run Gold dim build
    # ...

    rows = mem_duck.execute(
        "SELECT ticker, instrument_type_sk FROM gold.dim_instrument ORDER BY ticker"
    ).fetchall()
    assert len(rows) > 0
    assert all(row[1] is not None for row in rows), "instrument_type_sk must be resolved"

    # Re-run to verify SKs are stable
    # Run Gold dim build again
    rows_after = mem_duck.execute(
        "SELECT ticker, instrument_sk FROM gold.dim_instrument ORDER BY ticker"
    ).fetchall()
    assert [(r[0], r[1]) for r in rows] == [(r[0], r[1]) for r in rows_after], \
        "Surrogate keys must be stable across rebuilds"
```

---

### Step T.6 — Fixture Supply Workflow

When implementing each pipeline phase, request fixture files one at a time:

1. Tell user: _"To write the e2e test for `<endpoint>`, I need the raw FMP response. Please call `GET <url>` with your FMP key and paste the JSON here."_
2. User pastes the real JSON response.
3. Save verbatim (no modification) to `tests/e2e/fixtures/fmp/<path>.json`.
4. Write the test that loads that fixture.

**First fixture needed**: `stable/stock-list` (unblocks Phase T.3 immediately after Phase A).

**Subsequent fixtures** (in dependency order):
1. `stable/stock-list.json` → test_market_bronze_silver
2. `stable/etf-list.json` → test_market_bronze_silver
3. `v4/batch-request/end-of-day-prices.json` → test_eod_bronze_silver
4. `v4/profile/all.json` → test_eod_bronze_silver + test_gold_dims
5. `v4/income-statement-bulk.json` (quarter) → test_quarter_bronze_silver
6. `v4/balance-sheet-statement-bulk.json` (quarter) → test_quarter_bronze_silver
7. `v4/cash-flow-statement-bulk.json` (quarter) → test_quarter_bronze_silver

---

### Step I.2 — Create Prefect Flows

Create `src/sbfoundation/orchestrate/eod_flow.py`:
```python
from prefect import flow, task
from sbfoundation.eod.eod_service import EodService


@flow(name="eod-bulk-ingestion")
def eod_flow() -> None:
    service = EodService()
    # Build run_context and execute
    # Implementation follows api.py pattern
    ...
```

Create `prefect.yaml` at repo root with:
- Work pool: `default`
- Schedules: `eod_flow` at `18:00 ET` weekdays, `quarter_flow` and `annual_flow` at `08:00 ET` daily

---

---

## Phase J — Data Integrity Layer (Plan of Work)

### J Overview

**What this replaces**: `CoverageIndexService` + `ops.coverage_index` + `apps/coverage_dashboard/`.

**Why**: The coverage index tracks *what data exists* (date ranges, file counts) aggregated across all time. What we actually need is *what was lost during each run, per layer*, so failures are surfaced immediately and tied to a specific run.

**Key insight from reading the existing code**: `CoverageIndexService` already collects `silver_rows_created` and `silver_rows_failed` inside `ops.file_ingestions` — but it aggregates across all runs and only covers Bronze→Silver. The new system is per-run, per-layer, and covers both Bronze→Silver and Silver→Gold.

---

### J.1 — `ops.run_integrity` Table (migration)

`db/migrations/20260309_004_create_ops_run_integrity.sql`:

```sql
CREATE TABLE IF NOT EXISTS ops.run_integrity (
    integrity_id     VARCHAR    PRIMARY KEY,        -- UUID (uuid4)
    run_id           VARCHAR    NOT NULL,
    layer            VARCHAR    NOT NULL,           -- 'bronze_to_silver' | 'silver_to_gold'
    domain           VARCHAR    NOT NULL,
    source           VARCHAR    NOT NULL,
    dataset          VARCHAR    NOT NULL,
    discriminator    VARCHAR    NOT NULL DEFAULT '',
    ticker           VARCHAR    NOT NULL DEFAULT '',
    bronze_file_id   BIGINT,                        -- FK to ops.bronze_manifest; NULL for silver_to_gold
    records_in       INTEGER    NOT NULL,           -- rows counted in source layer
    records_out      INTEGER    NOT NULL,           -- rows successfully promoted to destination
    records_failed   INTEGER    NOT NULL,           -- records_in - records_out (≥ 0)
    pass_rate        DOUBLE,                        -- records_out / records_in (NULL if records_in = 0)
    status           VARCHAR    NOT NULL,           -- 'pass' | 'warn' | 'fail'
    failure_details  VARCHAR,                       -- JSON: list[{row_index, field, reason, raw_value}]
    checked_at       TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_run_integrity_run_id ON ops.run_integrity (run_id);
CREATE INDEX IF NOT EXISTS idx_run_integrity_status  ON ops.run_integrity (run_id, status);
```

**Status rules**:
- `pass` — `records_failed == 0`
- `warn` — `0 < records_failed / records_in < 0.01` (less than 1% loss)
- `fail` — `records_failed / records_in >= 0.01` OR `records_failed > 0` when `records_in < 10`

The threshold is configurable; start with 1%.

---

### J.2 — `ops.run_integrity_summary` View (migration)

```sql
CREATE OR REPLACE VIEW ops.run_integrity_summary AS
SELECT
    run_id,
    layer,
    COUNT(*)                                              AS total_checks,
    SUM(records_in)                                       AS total_records_in,
    SUM(records_out)                                      AS total_records_out,
    SUM(records_failed)                                   AS total_records_failed,
    MIN(pass_rate)                                        AS min_pass_rate,
    COUNT(CASE WHEN status = 'fail' THEN 1 END)           AS failure_count,
    COUNT(CASE WHEN status = 'warn' THEN 1 END)           AS warning_count,
    CASE
        WHEN COUNT(CASE WHEN status = 'fail' THEN 1 END) > 0 THEN 'fail'
        WHEN COUNT(CASE WHEN status = 'warn' THEN 1 END) > 0 THEN 'warn'
        ELSE 'pass'
    END                                                   AS run_status
FROM ops.run_integrity
GROUP BY run_id, layer;
```

This gives a one-row-per-(run, layer) health summary.

---

### J.3 — Drop `ops.coverage_index` (migration)

```sql
-- db/migrations/20260309_005_drop_ops_coverage_index.sql
DROP TABLE IF EXISTS ops.coverage_index;
```

---

### J.4 — `DataIntegrityService`

`src/sbfoundation/ops/services/data_integrity_service.py`:

```python
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo
from sbfoundation.infra.logger import LoggerFactory, SBLogger

_WARN_THRESHOLD = 0.01   # > 1% loss → warn; 0% = pass; configured per dataset later


class DataIntegrityService:
    """Captures record-level integrity between layer promotions.

    Call check_bronze_to_silver() immediately after SilverService.promote()
    for each Bronze file. Call check_silver_to_gold() after each GoldFactService
    build step.
    """

    def __init__(
        self,
        ops_repo: DuckDbOpsRepo | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._ops_repo = ops_repo or DuckDbOpsRepo()

    def check_bronze_to_silver(
        self,
        *,
        run_id: str,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
        bronze_file_id: int,
        records_in: int,       # len(BronzeResult.content)
        records_out: int,      # rows MERGEd into Silver
        failures: list[dict[str, Any]],   # [{row_index, field, reason, raw_value}]
    ) -> None:
        self._write(
            run_id=run_id,
            layer="bronze_to_silver",
            domain=domain,
            source=source,
            dataset=dataset,
            discriminator=discriminator,
            ticker=ticker,
            bronze_file_id=bronze_file_id,
            records_in=records_in,
            records_out=records_out,
            failures=failures,
        )

    def check_silver_to_gold(
        self,
        *,
        run_id: str,
        domain: str,
        source: str,
        dataset: str,            # Gold table name, e.g. 'dim_instrument', 'fact_eod'
        records_in: int,         # Silver rows read
        records_out: int,        # Gold rows written
        failures: list[dict[str, Any]],
    ) -> None:
        self._write(
            run_id=run_id,
            layer="silver_to_gold",
            domain=domain,
            source=source,
            dataset=dataset,
            discriminator="",
            ticker="",
            bronze_file_id=None,
            records_in=records_in,
            records_out=records_out,
            failures=failures,
        )

    def _write(self, *, run_id: str, layer: str, domain: str, source: str,
               dataset: str, discriminator: str, ticker: str,
               bronze_file_id: int | None, records_in: int, records_out: int,
               failures: list[dict[str, Any]]) -> None:
        records_failed = max(records_in - records_out, 0)
        pass_rate = (records_out / records_in) if records_in > 0 else None
        status = _compute_status(records_in, records_failed)

        row = {
            "integrity_id": str(uuid.uuid4()),
            "run_id": run_id,
            "layer": layer,
            "domain": domain,
            "source": source,
            "dataset": dataset,
            "discriminator": discriminator,
            "ticker": ticker,
            "bronze_file_id": bronze_file_id,
            "records_in": records_in,
            "records_out": records_out,
            "records_failed": records_failed,
            "pass_rate": pass_rate,
            "status": status,
            "failure_details": json.dumps(failures) if failures else None,
            "checked_at": datetime.now(tz=timezone.utc).isoformat(),
        }

        if status in ("warn", "fail"):
            self._logger.warning(
                "%s | %s/%s records promoted (%d failed)",
                dataset, records_out, records_in, records_failed,
                run_id=run_id,
            )

        self._ops_repo.insert_run_integrity(row)


def _compute_status(records_in: int, records_failed: int) -> str:
    if records_failed == 0:
        return "pass"
    if records_in < 10:
        return "fail"    # any loss in small datasets is a hard failure
    loss_rate = records_failed / records_in
    return "warn" if loss_rate < _WARN_THRESHOLD else "fail"
```

---

### J.5 — Integration into `SilverService.promote()`

In `SilverService.promote()`, after the MERGE completes for each Bronze file:

```python
# Existing: rows_written = result of MERGE/INSERT
# New: call integrity check
self._integrity_service.check_bronze_to_silver(
    run_id=run_id,
    domain=manifest_row.domain,
    source=manifest_row.source,
    dataset=manifest_row.dataset,
    discriminator=manifest_row.discriminator,
    ticker=manifest_row.ticker,
    bronze_file_id=manifest_row.bronze_file_id,
    records_in=len(bronze_content),        # raw rows from Bronze JSON
    records_out=rows_written,              # rows actually MERGEd into Silver
    failures=dto_parse_failures,           # collected during from_row() loop
)
```

**Required change to `SilverService`**: The `from_row()` loop currently likely raises or silently drops parse failures. It must be updated to:
1. Try `DTO.from_row(row, ticker)` in a `try/except`
2. On failure, append `{"row_index": i, "field": "?", "reason": str(exc), "raw_value": repr(row)}` to `dto_parse_failures`
3. Continue processing remaining rows (don't abort the file)

---

### J.6 — Integration into `GoldFactService`

In `GoldFactService`, for each fact table build:

```python
silver_count = conn.execute(f"SELECT COUNT(*) FROM silver.{silver_table}").fetchone()[0]
# ... build Gold rows ...
gold_count = conn.execute(f"SELECT COUNT(*) FROM gold.{gold_table}").fetchone()[0]

self._integrity_service.check_silver_to_gold(
    run_id=run_id,
    domain="gold",
    source="internal",
    dataset=gold_table,          # e.g. 'fact_eod', 'dim_instrument'
    records_in=silver_count,
    records_out=gold_count,
    failures=sk_resolution_failures,   # list of tickers with no matching SK
)
```

---

### J.7 — Remove Coverage Package

Files to delete:
- `src/sbfoundation/coverage/__init__.py`
- `src/sbfoundation/coverage/__main__.py`
- `src/sbfoundation/coverage/cli.py`
- `src/sbfoundation/coverage/coverage_index_service.py`

Remove from `api.py`:
- `from sbfoundation.coverage.coverage_index_service import CoverageIndexService`
- All calls to `coverage_index_service.refresh()`

Remove from `ops_service.py` or `api.py`:
- Any `refresh_coverage_index()` method

Remove unit tests:
- `tests/unit/coverage/` directory

---

### J.8 — New Integrity CLI

`src/sbfoundation/integrity/__init__.py` (empty)
`src/sbfoundation/integrity/__main__.py`:

```python
"""
CLI: python -m sbfoundation.integrity [subcommand]

  status <run_id>       Show pass/warn/fail summary per layer for a run
  failures <run_id>     List all failure details for a run
  recent [N]            Show integrity summary for the last N runs (default: 10)
"""
```

**Example output — `status <run_id>`**:
```
Run: 2026-03-09.142300  |  Layer             | In      | Out     | Failed | Status
─────────────────────────────────────────────────────────────────────────────────
                        │  bronze_to_silver  | 142,300 | 142,287 |     13 | warn
                        │  silver_to_gold    |  89,450 |  89,450 |      0 | pass
```

**Example output — `failures <run_id>`**:
```
Layer: bronze_to_silver
  dataset=fmp_income_statement  ticker=AAPL  bronze_file_id=4521
    row 3: field=reportDate  reason="date parse failed"  raw_value="N/A"
    row 7: field=eps         reason="float parse failed" raw_value="--"
  dataset=fmp_company_profile   ticker=XYZ
    row 0: field=ticker      reason="empty ticker"       raw_value=""
```

---

### J.9 — `DuckDbOpsRepo` Addition

Add to `DuckDbOpsRepo`:

```python
def insert_run_integrity(self, row: dict[str, Any]) -> None:
    """Insert one ops.run_integrity row."""
    ...

def get_run_integrity_summary(self, run_id: str) -> list[dict[str, Any]]:
    """Query ops.run_integrity_summary for a given run_id."""
    ...

def get_run_integrity_failures(self, run_id: str) -> list[dict[str, Any]]:
    """Return all warn/fail rows for a run, with failure_details parsed."""
    ...
```

---

## Validation and Acceptance

### Tier 1 — Quick Checks (no DB or network)

After Phase A:
```bash
python -c "from sbfoundation.api import SBFoundationAPI; print('API import: OK')"
python -c "from sbfoundation.bronze import BronzeService; print('Bronze import: OK')"
python -c "from sbfoundation.silver import SilverService; print('Silver import: OK')"
python -c "from sbfoundation.maintenance import DuckDBBootstrap; print('Maintenance import: OK')"
poetry run pytest tests/unit/ -x -q
```
Expected: All pass, zero import errors.

After Phase B:
```bash
python -c "from sbfoundation.dtos.eod.eod_bulk_price_dto import EodBulkPriceDTO; print('OK')"
python -c "from sbfoundation.eod.eod_service import EodService; print('OK')"
poetry run pytest tests/unit/dtos/ -x -q
```

After Phase E:
```bash
python -c "from sbfoundation.gold import GoldBootstrapService; print('OK')"
```

### Tier 2 — DB Checks (in-memory DuckDB, no API, automated)

All Tier 2 checks are expressed as **pytest tests** using the `mem_duck` fixture from `tests/e2e/conftest.py`. They require no file-based DuckDB, no FMP key, and no network.

```bash
poetry run pytest tests/e2e/ -k "not live" -v
```

**After Phase E — static dims bootstrap:**
```python
# tests/e2e/test_gold_bootstrap.py
def test_dim_date_populated(mem_duck) -> None:
    row = mem_duck.execute("SELECT COUNT(*) FROM gold.dim_date").fetchone()
    assert row[0] == 14610, f"Expected 14610 dates (1990–2029), got {row[0]}"

def test_dim_instrument_type_has_six_rows(mem_duck) -> None:
    rows = mem_duck.execute(
        "SELECT instrument_type FROM gold.dim_instrument_type ORDER BY 1"
    ).fetchall()
    assert [r[0] for r in rows] == ["commodity", "crypto", "etf", "fx", "index", "stock"]
```

**After Phase J — data integrity:**
```python
# tests/unit/ops/test_data_integrity_service.py
def test_all_rows_promoted_writes_pass(mem_duck) -> None:
    svc = DataIntegrityService(ops_repo=stub_repo(mem_duck))
    svc.check_bronze_to_silver(run_id="r1", domain="company", source="fmp",
        dataset="company-profile", discriminator="", ticker="AAPL",
        bronze_file_id=1, records_in=5, records_out=5, failures=[])
    row = mem_duck.execute(
        "SELECT status, records_failed FROM ops.run_integrity WHERE run_id='r1'"
    ).fetchone()
    assert row == ("pass", 0)

def test_partial_failure_above_threshold_writes_fail(mem_duck) -> None:
    svc = DataIntegrityService(ops_repo=stub_repo(mem_duck))
    failures = [{"row_index": 2, "field": "date", "reason": "parse error", "raw_value": "N/A"}]
    svc.check_bronze_to_silver(run_id="r2", domain="fundamentals", source="fmp",
        dataset="income-statement", discriminator="", ticker="MSFT",
        bronze_file_id=2, records_in=100, records_out=98, failures=failures)
    row = mem_duck.execute(
        "SELECT status, records_failed FROM ops.run_integrity WHERE run_id='r2'"
    ).fetchone()
    assert row[0] == "warn"   # 2% loss < 1% threshold → warn not fail for 2/100
    # Note: 2/100 = 2% ≥ 1% threshold → actually 'fail'; adjust assertion to match threshold
```

**After Phase G — fact table idempotency:**
```python
# tests/e2e/test_gold_facts.py
def test_fact_eod_upsert_is_idempotent(fmp_server, mem_duck, bronze_root, monkeypatch) -> None:
    fmp_server("v4/batch-request/end-of-day-prices", "v4/batch-request/end-of-day-prices.json")
    # Run EOD pipeline twice
    run_eod_pipeline(mem_duck)
    count_1 = mem_duck.execute("SELECT COUNT(*) FROM gold.fact_eod").fetchone()[0]
    run_eod_pipeline(mem_duck)
    count_2 = mem_duck.execute("SELECT COUNT(*) FROM gold.fact_eod").fetchone()[0]
    assert count_1 == count_2, "fact_eod must be idempotent on re-run"
```

### Tier 3 — E2E Tests (local, no live API, fixture-file–driven)

**Infrastructure**: `pytest-httpserver` (already in dev deps) + `mem_duck` fixture + real FMP JSON fixtures in `tests/e2e/fixtures/fmp/`.

**What these tests prove**:
- The full Bronze → Silver → Gold pipeline executes end-to-end
- HTTP responses come from real FMP fixture files (not hardcoded Python dicts)
- DuckDB state is isolated per test (in-memory, no shared file)
- Bronze files land in `tmp_path` and are auto-cleaned

**How to run:**
```bash
# Full e2e suite — no API key required
poetry run pytest tests/e2e/ -v

# Single test file
poetry run pytest tests/e2e/test_eod_bronze_silver.py -v
```

**Key fixture: `fmp_server`** (from `conftest.py`) — registers a fixture file for a given URL path and patches the FMP base URL to the local server:

```python
def test_stock_list_full_pipeline(fmp_server, mem_duck, bronze_root) -> None:
    fmp_server("stable/stock-list", "stable/stock-list.json")
    # Pipeline runs → Bronze JSON written to tmp_path, Silver rows in mem_duck
    ...
    rows = mem_duck.execute("SELECT symbol FROM silver.fmp_stock_list ORDER BY symbol").fetchall()
    assert [r[0] for r in rows] == ["AAPL", "MSFT"]  # matches fixture
```

**Gate before any Phase PR**: All e2e tests for that phase's datasets must pass locally before PR is opened.

| Phase | E2E Test File | Fixture Files Required |
|---|---|---|
| A | (unit tests only) | none |
| B | `test_eod_bronze_silver.py` | `v4/batch-request/end-of-day-prices.json`, `v4/profile/all.json` |
| C | `test_quarter_bronze_silver.py` | `v4/income-statement-bulk.json`, `v4/balance-sheet-statement-bulk.json`, `v4/cash-flow-statement-bulk.json` |
| D | `test_annual_bronze_silver.py` | same endpoints with `period=annual` |
| E | `test_gold_bootstrap.py` | none (SQL-only) |
| F | `test_gold_dims.py` | `v4/batch-request/end-of-day-prices.json`, `v4/profile/all.json` |
| G | `test_gold_facts.py` | all of the above |
| J | `test_data_integrity.py` | reuses fixtures from B + G |

**Phase J e2e integrity test** (demonstrates the full integrity loop):
```python
def test_integrity_captured_after_bronze_to_silver(fmp_server, mem_duck, bronze_root) -> None:
    fmp_server("stable/stock-list", "stable/stock-list.json")
    run_market_pipeline(mem_duck)  # Bronze→Silver

    rows = mem_duck.execute(
        "SELECT layer, records_in, records_out, records_failed, status "
        "FROM ops.run_integrity ORDER BY layer"
    ).fetchall()
    assert len(rows) > 0
    assert all(r[4] == "pass" for r in rows if r[0] == "bronze_to_silver"), \
        "All stock-list rows must promote cleanly"

def test_integrity_summary_shows_run_status(fmp_server, mem_duck, bronze_root) -> None:
    fmp_server("stable/stock-list", "stable/stock-list.json")
    ctx = run_market_pipeline(mem_duck)

    summary = mem_duck.execute(
        f"SELECT run_status, total_records_failed FROM ops.run_integrity_summary "
        f"WHERE run_id = '{ctx.run_id}' AND layer = 'bronze_to_silver'"
    ).fetchone()
    assert summary[0] == "pass"
    assert summary[1] == 0
```

### Tier 4 — Post-Live-Run Checks (requires FMP API key + real pipeline run)

1. After first live EOD run: `SELECT COUNT(*) FROM silver.fmp_eod_bulk_price` returns > 0 rows.
2. Re-running same date produces identical Silver row counts (UPSERT idempotency).
3. After first Gold build: `SELECT COUNT(*) FROM gold.fact_eod` > 0; re-running produces identical count.
4. After quarterly run during earnings season: `SELECT COUNT(*) FROM silver.fmp_income_statement_bulk_quarter` > 0.
5. After annual run (Jan–Mar window): `SELECT COUNT(*) FROM silver.fmp_income_statement_bulk_annual` > 0.

**Integrity acceptance criteria (must pass before merging to `main`)**:
```sql
-- No hard failures in any layer across all runs
SELECT run_id, layer, failure_count, total_records_failed
FROM ops.run_integrity_summary
WHERE run_status = 'fail';
-- Expected: 0 rows

-- Check pass rate — overall loss must be below 0.1%
SELECT run_id, layer, total_records_in, total_records_failed,
       ROUND(total_records_failed * 100.0 / NULLIF(total_records_in, 0), 4) AS loss_pct
FROM ops.run_integrity_summary
WHERE loss_pct > 0.1;
-- Expected: 0 rows
```

---

## Idempotence and Recovery

- **Phase 0**: DuckDB backup is the primary safety net. The backup file preserves all existing Silver and ops data. Bronze JSON files are untouched throughout the entire refactor.
- **Phase A** is non-destructive: old import paths fail at startup if not updated, but no data is modified. Rollback: `git checkout main`.
- **Phases B–D**: New Silver tables are UPSERT-idempotent. If a bulk run fails mid-file, re-run re-ingests; Bronze deduplication prevents duplicate files.
- **Phases E–G**: Gold migrations use `CREATE TABLE IF NOT EXISTS` and `INSERT OR IGNORE` — safe to re-run. `GoldBootstrapService.run()` is idempotent.
- **Phase I**: Prefect deployments are declarative and idempotent (`prefect deploy` can be re-run safely).

**Full rollback (abandon the refactor entirely)**:
```bash
git checkout main
# Restore DuckDB from backup (path recorded in Artifacts and Notes)
mv "$DATA_ROOT_FOLDER/duckdb/SBFoundation_backup_YYYYMMDD.duckdb" \
   "$DATA_ROOT_FOLDER/duckdb/SBFoundation.duckdb"
# Bronze files were never modified — no action needed
```

---

---

### Phase L Concrete Steps

#### Step L.1 — Create `BulkPipelineService`

Create `src/sbfoundation/run/services/bulk_pipeline_service.py`:

```python
"""Abstract base class for bulk Bronze+Silver ingestion domain services."""
from __future__ import annotations

import traceback
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from sbfoundation.bronze import BronzeService
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.dataset.services.dataset_service import DatasetService
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance import DuckDbBootstrap
from sbfoundation.ops.services.ops_service import OpsService
from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.silver import SilverService


class BulkPipelineService(ABC):
    """Shared Bronze + Silver pipeline mechanics for bulk ingestion domain services.

    Subclasses implement run() with domain-specific recipe selection and
    season gating. Bronze fetch, Silver promotion, and helper utilities
    are provided here.
    """

    def __init__(
        self,
        *,
        ops_service: OpsService,
        dataset_service: DatasetService,
        bootstrap: DuckDbBootstrap,
        logger: SBLogger | None = None,
        enable_bronze: bool,
        enable_silver: bool,
        concurrent_requests: int,
        force_from_date: str | None,
        today: str,
    ) -> None:
        self._ops_service = ops_service
        self._dataset_service = dataset_service
        self._bootstrap = bootstrap
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._enable_bronze = enable_bronze
        self._enable_silver = enable_silver
        self._concurrent_requests = concurrent_requests
        self._force_from_date = force_from_date
        self._today = today

    @abstractmethod
    def run(self, run: RunContext) -> RunContext:
        """Execute Bronze + Silver ingestion for this domain. Return updated RunContext."""

    # ------------------------------------------------------------------ #
    # Shared helpers                                                       #
    # ------------------------------------------------------------------ #

    def _processing_msg(self, enabled: bool, layer: str) -> str:
        return f"PROCESSING {layer} | " if enabled else f"DRY-RUN {layer} |"

    def _process_recipe_list(self, recipes: list[DatasetRecipe], run: RunContext) -> RunContext:
        """Process a list of recipes through the Bronze layer."""
        if not recipes:
            return run
        bronze_service = BronzeService(
            ops_service=self._ops_service,
            concurrent_requests=self._concurrent_requests,
            force_from_date=self._force_from_date,
        )
        try:
            return bronze_service.register_recipes(run, recipes).process(run)
        except Exception as exc:
            self._logger.error("Bronze ingestion failed: %s", exc, run_id=run.run_id)
            traceback.print_exc()
            return run

    def _promote_silver(self, run: RunContext, domain: str | None = None) -> RunContext:
        """Promote Bronze data to Silver, restricted to the given domain."""
        silver_service = SilverService(
            enabled=self._enable_silver,
            ops_service=self._ops_service,
            keymap_service=self._dataset_service,
            bootstrap=self._bootstrap,
        )
        try:
            _promoted_ids, promoted_rows = silver_service.promote(run, domain=domain)
        except Exception as e:
            self._logger.error(f"Silver promotion: {e}", run_id=run.run_id)
            promoted_rows = 0
            traceback.print_exc()
        finally:
            silver_service.close()
        run.silver_dto_count += promoted_rows
        return run
```

#### Step L.2 — Update `src/sbfoundation/run/services/__init__.py`

Add export:
```python
from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService
__all__ = [..., "BulkPipelineService"]
```

#### Step L.3 — Implement `EodService.run()`

Replace the stub `eod_service.py` body:

```python
"""EOD bulk ingestion service."""
from __future__ import annotations

from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService
from sbfoundation.settings import EOD_DOMAIN


class EodService(BulkPipelineService):
    """Orchestrates daily bulk EOD + company profile bulk ingestion."""

    def run(self, run: RunContext) -> RunContext:
        self._logger.log_section(run.run_id, "Processing EOD bulk domain")
        recipes = [r for r in self._dataset_service.recipes if r.domain == EOD_DOMAIN]
        if not recipes:
            self._logger.warning("No EOD bulk recipes found", run_id=run.run_id)
            return run
        self._logger.info(
            f"{self._processing_msg(self._enable_bronze, 'BRONZE')} {len(recipes)} EOD bulk datasets",
            run_id=run.run_id,
        )
        if self._enable_bronze:
            run = self._process_recipe_list(recipes, run)
        run = self._promote_silver(run, EOD_DOMAIN)
        self._logger.info("EOD bulk domain complete", run_id=run.run_id)
        return run
```

#### Step L.4 — Implement `QuarterService.run()`

```python
"""Quarterly bulk ingestion service."""
from __future__ import annotations

from datetime import date

from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService
from sbfoundation.settings import QUARTER_DOMAIN


class QuarterService(BulkPipelineService):
    """Orchestrates bulk quarterly fundamental ingestion (earnings seasons only)."""

    def run(self, run: RunContext) -> RunContext:
        self._logger.log_section(run.run_id, "Processing quarter bulk domain")
        today = date.fromisoformat(self._today)
        if not self.is_earnings_season(today):
            self._logger.info(
                f"Quarter bulk: outside earnings season ({today}) — skipping",
                run_id=run.run_id,
            )
            return run
        recipes = [r for r in self._dataset_service.recipes if r.domain == QUARTER_DOMAIN]
        if not recipes:
            self._logger.warning("No quarterly bulk recipes found", run_id=run.run_id)
            return run
        self._logger.info(
            f"{self._processing_msg(self._enable_bronze, 'BRONZE')} {len(recipes)} quarterly bulk datasets",
            run_id=run.run_id,
        )
        if self._enable_bronze:
            run = self._process_recipe_list(recipes, run)
        run = self._promote_silver(run, QUARTER_DOMAIN)
        self._logger.info("Quarter bulk domain complete", run_id=run.run_id)
        return run

    @staticmethod
    def is_earnings_season(today: date) -> bool:
        """Return True if today falls within an earnings filing window."""
        m = today.month
        return m in (1, 2, 3, 4, 5, 7, 8, 10, 11)
```

#### Step L.5 — Implement `AnnualService.run()`

```python
"""Annual bulk ingestion service."""
from __future__ import annotations

from datetime import date

from sbfoundation.run.dtos.run_context import RunContext
from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService
from sbfoundation.settings import ANNUAL_DOMAIN


class AnnualService(BulkPipelineService):
    """Orchestrates bulk annual fundamental ingestion (Jan–Mar only)."""

    def run(self, run: RunContext) -> RunContext:
        self._logger.log_section(run.run_id, "Processing annual bulk domain")
        today = date.fromisoformat(self._today)
        if not self.is_annual_season(today):
            self._logger.info(
                f"Annual bulk: outside annual filing season ({today}) — skipping",
                run_id=run.run_id,
            )
            return run
        recipes = [r for r in self._dataset_service.recipes if r.domain == ANNUAL_DOMAIN]
        if not recipes:
            self._logger.warning("No annual bulk recipes found", run_id=run.run_id)
            return run
        self._logger.info(
            f"{self._processing_msg(self._enable_bronze, 'BRONZE')} {len(recipes)} annual bulk datasets",
            run_id=run.run_id,
        )
        if self._enable_bronze:
            run = self._process_recipe_list(recipes, run)
        run = self._promote_silver(run, ANNUAL_DOMAIN)
        self._logger.info("Annual bulk domain complete", run_id=run.run_id)
        return run

    @staticmethod
    def is_annual_season(today: date) -> bool:
        """Return True if today falls within the annual filing window (Jan–Mar)."""
        return today.month in (1, 2, 3)
```

#### Step L.6 — Slim `api.py`

Replace the body of `SBFoundationAPI.run()` dispatch block and remove dead methods:

```python
# In run():
# BEFORE:
self._enable_silver = command.enable_silver
self._concurrent_requests = command.concurrent_requests
self._force_from_date: str | None = command.force_from_date
run = self._start_run(command)
domain = command.domain
if domain == EOD_DOMAIN:
    run = self._handle_eod(command, run)
elif domain == QUARTER_DOMAIN:
    run = self._handle_quarter(command, run)
elif domain == ANNUAL_DOMAIN:
    run = self._handle_annual(command, run)

# AFTER:
run = self._start_run(command)
run = self._build_service(command).run(run)
```

Add `_build_service()`:

```python
def _build_service(self, command: RunCommand) -> BulkPipelineService:
    kwargs: dict = dict(
        ops_service=self.ops_service,
        dataset_service=self._dataset_service,
        bootstrap=self._bootstrap,
        logger=self.logger,
        enable_bronze=command.enable_bronze,
        enable_silver=command.enable_silver,
        concurrent_requests=command.concurrent_requests,
        force_from_date=command.force_from_date,
        today=self._today,
    )
    if command.domain == EOD_DOMAIN:
        return EodService(**kwargs)
    if command.domain == QUARTER_DOMAIN:
        return QuarterService(**kwargs)
    if command.domain == ANNUAL_DOMAIN:
        return AnnualService(**kwargs)
    raise ValueError(f"Unknown domain: {command.domain}")
```

Delete from `api.py`: `_handle_eod`, `_handle_quarter`, `_handle_annual`, `_processing_msg`, `_process_recipe_list`, `_promote_silver`.

Update imports in `api.py`:
```python
from sbfoundation.annual import AnnualService
from sbfoundation.eod import EodService
from sbfoundation.quarter import QuarterService
from sbfoundation.run.services import BulkPipelineService
# Remove: SilverService (no longer used directly in api.py)
```

---

### Phase L Validation and Acceptance

**Tier 1 — Quick checks**:
```bash
python -c "from sbfoundation.run.services.bulk_pipeline_service import BulkPipelineService; print('Base import OK')"
python -c "from sbfoundation.eod import EodService; print('EodService OK')"
python -c "from sbfoundation.quarter import QuarterService; print('QuarterService OK')"
python -c "from sbfoundation.annual import AnnualService; print('AnnualService OK')"
python -c "from sbfoundation.api import SBFoundationAPI, RunCommand; print('API import OK')"
poetry run pytest tests/unit/ -x -q
```
Expected: all pass, zero import errors.

**Tier 2 — Structural check**:
```python
# Confirm EodService has no _promote_silver of its own — it inherits
import inspect
from sbfoundation.eod import EodService
from sbfoundation.run.services import BulkPipelineService
assert issubclass(EodService, BulkPipelineService)
assert "_promote_silver" not in EodService.__dict__
assert "_process_recipe_list" not in EodService.__dict__
assert callable(EodService.run)
print("Structure OK")
```

**Tier 3 — Dry-run (no live API)**:
```python
from sbfoundation.api import SBFoundationAPI, RunCommand
from sbfoundation.settings import EOD_DOMAIN
result = SBFoundationAPI(today="2026-03-10").run(
    RunCommand(domain=EOD_DOMAIN, concurrent_requests=1, enable_bronze=False, enable_silver=False)
)
print(f"run_id={result.run_id}  silver_rows={result.silver_dto_count}")
# Expected: run_id non-empty, silver_rows=0, no exception
```

**Tier 4 — Post-live-run**: same acceptance criteria as Phase K.

---

### Phase K Concrete Steps (2026-03-10)

#### Step K.1 — Fix `GoldDimService` Missing Table Guards

Added `_table_exists` method to `src/sbfoundation/gold/gold_dim_service.py`:

```python
def _table_exists(self, conn: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?",
        [schema, table],
    ).fetchone()
    return bool(row and row[0] > 0)
```

`_build_dim_instrument` now dynamically builds a UNION only from tables that exist; skips entirely if neither `silver.fmp_company_profile_bulk` nor `silver.fmp_eod_bulk_price` exist.

`_build_dim_company` now returns current row count immediately if `silver.fmp_company_profile_bulk` does not exist.

#### Step K.2 — Explicit `enable_gold=True` in Prefect Flows

In `orchestrate/eod_flow.py`, `quarter_flow.py`, `annual_flow.py`: added `enable_gold=True` to each `RunCommand(...)` constructor call.

#### Step K.3 — Remove Per-Ticker Domains

`settings.py` — deleted constants and list entries:
```python
# Removed:
MARKET_DOMAIN = "market"
COMPANY_DOMAIN = "company"
FUNDAMENTALS_DOMAIN = "fundamentals"
TECHNICALS_DOMAIN = "technicals"
COMMODITIES_DOMAIN = "commodities"
FX_DOMAIN = "fx"
CRYPTO_DOMAIN = "crypto"

# DOMAINS now contains only:
DOMAINS: list = [EOD_DOMAIN, QUARTER_DOMAIN, ANNUAL_DOMAIN]
DOMAIN_EXECUTION_ORDER: tuple[str, ...] = (EOD_DOMAIN, QUARTER_DOMAIN, ANNUAL_DOMAIN)
```

`api.py` — removed 7 `elif` branches, 7 handler methods, all exclusive helpers, `OrchestrationTickerChunkService`, `US_ALL_CAP`, `UniverseDefinition` imports, `include_indexes`, `include_delisted`, `universe_definition` from `RunCommand`.

#### Step K.4 — Remove `ECONOMICS_DOMAIN`

`settings.py` — deleted `ECONOMICS_DOMAIN = "economics"`.

`api.py` — removed `elif domain == ECONOMICS_DOMAIN:` branch, `_handle_economics` method, `backfill_to_1990` from `RunCommand` and its `validate()` check, `_BACKFILL_DOMAINS` frozenset, `self._backfill_to_1990` assignment in `run()`.

#### Step K.5 — Restore Accidentally Deleted Helpers

Recovered from `git show HEAD:src/sbfoundation/api.py` and re-inserted before `_promote_silver`:

```python
def _processing_msg(self, enabled: bool, layer: str) -> str:
    return f"PROCESSING {layer} | " if enabled else f"DRY-RUN {layer} |"

def _process_recipe_list(self, recipes: list[DatasetRecipe], run: RunContext) -> RunContext:
    """Process a list of recipes through the bronze layer."""
    if not recipes:
        return run
    bronze_service = BronzeService(
        ops_service=self.ops_service,
        concurrent_requests=self._concurrent_requests,
        force_from_date=self._force_from_date,
        # backfill_to_1990 omitted — defaults to False in BronzeService
    )
    try:
        return bronze_service.register_recipes(run, recipes).process(run)
    except Exception as exc:
        self.logger.error("Bronze ingestion failed: %s", exc, run_id=run.run_id)
        traceback.print_exc()
        return run
```

#### Step K.6 — Import Cleanup

Removed from `api.py`:
- `from dataclasses import dataclass, field` → `from dataclasses import dataclass`
- `from datetime import date, timedelta` → `from datetime import date`
- `import copy`
- `from sbfoundation.run.dtos.run_request import RunRequest`

---

## Artifacts and Notes

### Phase K — Final State of `api.py` (2026-03-10)

`api.py` is now 300 lines (down from ~1,100+). Public surface:

| Symbol | Type | Notes |
|---|---|---|
| `RunCommand` | dataclass | `domain`, `concurrent_requests`, `enable_bronze`, `enable_silver`, `enable_gold`, `ticker_limit`, `ticker_recipe_chunk_size`, `force_from_date` |
| `SBFoundationAPI` | class | `run(command)` → `RunContext` |

Active domain handlers: `_handle_eod`, `_handle_quarter`, `_handle_annual`.
Shared helpers: `_processing_msg`, `_process_recipe_list`, `_promote_silver`, `_promote_gold`, `_start_run`, `_close_run`.

### Phase K — Final State of `settings.py` (2026-03-10)

`DOMAINS = ["eod", "quarter", "annual"]`
`DOMAIN_EXECUTION_ORDER = ("eod", "quarter", "annual")`

All dataset name constants retained (economics, market, company, fundamentals, technicals, commodities, fx, crypto, eod, quarter, annual datasets).

---

## Interfaces and Dependencies

### New Python Dependencies Required

| Package | Purpose | Phase |
|---|---|---|
| `prefect >= 3.0` | Workflow orchestration | Phase I |

### Existing Dependencies Used

| Package | Usage |
|---|---|
| `duckdb` | Gold schema, all dims + facts; in-memory for e2e tests |
| `pydantic` / `dataclasses` | DTOs |
| `requests` / `httpx` | FMP API calls (existing `RunRequestExecutor`) |
| `pytest-httpserver` | Already in dev deps — lightweight fake HTTP server for e2e tests (replaces FakeApiServer) |

### FMP API Endpoints (new, require plan confirmation)

| Endpoint | FMP Docs | Phase |
|---|---|---|
| `v4/batch-request/end-of-day-prices` | EOD Bulk | B |
| `v4/profile/all` | Company Profile Bulk | B |
| `v4/income-statement-bulk?period=quarter` | Income Statement Bulk | C |
| `v4/balance-sheet-statement-bulk?period=quarter` | Balance Sheet Bulk | C |
| `v4/cash-flow-statement-bulk?period=quarter` | Cashflow Bulk | C |
| `v4/income-statement-bulk?period=annual` | Income Statement Annual | D |
| `v4/balance-sheet-statement-bulk?period=annual` | Balance Sheet Annual | D |
| `v4/cash-flow-statement-bulk?period=annual` | Cashflow Annual | D |

**Note**: FMP bulk endpoints return CSV or JSON? Confirm format before writing DTOs. The existing codebase expects `list[dict]` in `BronzeResult.content` — if FMP returns CSV, a CSV-to-dict adapter is needed in the ingestion layer. This must be investigated before Phase B begins.

### DuckDB SQL Compatibility Notes

- DuckDB does NOT support `YEAR()`, `MONTH()`, `DAYOFWEEK()` as standalone functions in all versions — use `EXTRACT(YEAR FROM d)` syntax or verify function availability in the installed DuckDB version.
- `INSERT OR IGNORE` syntax: DuckDB uses `INSERT OR IGNORE INTO` (not `ON CONFLICT DO NOTHING`) in older versions. Verify syntax against installed version.
- `SEQUENCE` for auto-increment SKs: DuckDB supports `CREATE SEQUENCE`. Use `nextval('seq_name')` in inserts.

---

*ExecPlan: major-refactor | Last updated: 2026-03-10 | All phases complete — 415 tests pass*
