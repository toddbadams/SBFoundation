# SBFoundation — Strawberry Bronze + Silver Pipeline

SBFoundation is the data acquisition and validation package for the **Strawberry** AI trading platform. It implements the first two layers of a medallion/lakehouse architecture:

- **Bronze** — raw, append-only vendor API responses with full ingestion metadata
- **Silver** — validated, typed, and conformed datasets ready for downstream consumers (Gold, backtesting, strategy engines)

Downstream Gold layer construction and strategy execution live in separate packages.

---

## Overview

The pipeline ingests financial data from external providers (primarily Financial Modeling Prep), persists raw responses as immutable JSON files (Bronze), and promotes them to structured DuckDB tables (Silver) via typed Data Transfer Objects (DTOs). Every step is traceable: each Silver row carries a `bronze_file_id` linking it back to its source file.

**Data domains ingested:**

| Domain | Content |
|---|---|
| `instrument` | Stock, ETF, index, crypto, and forex lists; ETF holdings |
| `economics` | Macro indicators (GDP, CPI, unemployment, Fed funds), treasury rates, market risk premium |
| `company` | Company profile, peers, employees, market cap, shares float, officers, compensation, delisted |
| `fundamentals` | Income/balance sheet/cash flow statements and growth series, key metrics, financial scores, owner earnings, enterprise values, revenue segmentation |
| `technicals` | EOD price history (full, split-adjusted, dividend-adjusted), SMA/EMA/WMA/DEMA/TEMA, RSI, ADX, Williams %R, standard deviation |

---

## Key Design Decisions

### 1. Bronze is append-only and immutable
Raw API responses are never modified. One JSON file is written per request, preserving exact vendor payloads plus request metadata. This makes deterministic replay possible when Silver logic changes — re-process Bronze without re-calling the API.

### 2. All dataset definitions are declarative
`config/dataset_keymap.yaml` is the single source of truth for every dataset: its domain, source, Silver table mapping, key columns, DTO schema, and ingestion recipe. No dataset definition lives in code.

### 3. DTOs are the only Bronze → Silver boundary
Every Silver table is written and read exclusively through `BronzeToSilverDTO` subclasses. Raw Bronze dicts are parsed via `from_row()`; Silver rows are emitted via `to_dict()`. This prevents Bronze quirks from leaking into Silver.

### 4. DuckDB for structured storage
Silver and operational tables (manifests, watermarks, run history) are stored in a single DuckDB file. Bronze remains filesystem JSON — DuckDB stores references and metadata, not raw payloads.

### 5. Silver writes are idempotent (MERGE/UPSERT)
Silver promotion uses the dataset's `key_cols` from the keymap to MERGE rows. Replaying the same Bronze file produces no duplicates.

### 6. Ingestion cadence is data-driven, not clock-driven
The `RunProvider` computes `from_date` from the last successfully ingested `to_date` stored as a dataset watermark, not from a fixed schedule. A recipe's `min_age_days` gates whether a dataset is due for re-ingestion.

### 7. Domain execution order is enforced
The `instrument` domain always runs first to populate the ticker universe before per-ticker domains (company, fundamentals, technicals) execute.

### 8. Failures are audit-first, not crash-first
A failed ingestion request does not abort the run. A `BronzeResult` error record is written to Bronze, counters are updated, and the run continues. Every run produces a manifest (`ops.bronze_manifest`) regardless of outcome.

---

## Installation

**Prerequisites:** Python 3.12 (or any `>=3.11,<3.14`), [Poetry](https://python-poetry.org/)

```bash
# Clone and enter the repo
git clone https://github.com/toddbadams/SBFoundation
cd SBFoundation

# Install dependencies (Poetry manages the .venv)
poetry install --no-root

# Or if you use uv for local speed
uv pip install -r <(poetry export --without-hashes)
```

**Environment variables** — create a `.env` file (never commit it):

```dotenv
FMP_API_KEY=your_fmp_api_key_here
DATA_ROOT_FOLDER=c:/sb/SBFoundation/data          # Bronze JSON files, DuckDB, logs
REPO_ROOT_FOLDER=c:/sb/SBFoundation               # Repo root (used for config/ and db/migrations/)
DATASET_KEYMAP_FILENAME=dataset_keymap.yaml  # Optional override
```

The defaults (`DATA_ROOT_FOLDER=c:/sb/SBFoundation/data`, `REPO_ROOT_FOLDER=c:/sb/SBFoundation`) are set in `src/sbfoundation/settings.py` and apply if the env vars are absent.

---

## Tech Stack

| Category | Tool / Library |
|---|---|
| Language | Python `>=3.11,<3.14` |
| Packaging | Poetry (`poetry-core`) + uv (local dev) |
| Data manipulation | pandas `^2.3`, numpy `^2.4` |
| HTTP client | requests `^2.32` |
| Structured storage | DuckDB `^1.4` |
| Configuration | PyYAML `^6.0` |
| Testing | pytest `^9`, pytest-httpserver, freezegun, pandera |
| Code quality | Black (line-length 150), isort (Black profile), flake8, mypy |
| Primary data source | Financial Modeling Prep (FMP) via REST |
| Planned / future | Alpha Vantage, Alpaca (simulation), Charles Schwab (live execution) |
| Orchestration | Prefect OSS (nightly batch; not in this package directly) |
| UI | Streamlit + streamlit-echarts + Altair (separate package) |
| Deployment | Docker Compose; PROD on Raspberry Pi |

---

## Repo Structure

```
SBFoundation/
├── config/
│   └── dataset_keymap.yaml       # AUTHORITATIVE dataset/recipe/DTO/Silver-table definitions
├── docs/                         # project documentation
Architecture, contracts, DuckDB design docs
├── src/
│   └── sbfoundation/
│       ├── __init__.py               # Public API: Orchestrator, NewEquitiesOrchestrationService
│       ├── settings.py               # All constants: domains, datasets, data sources, placeholders, paths
│       ├── folders.py                # Path resolution helpers (bronze/duckdb/log/migration folders)
│       ├── orchestrator.py           # Top-level entry point; domain-ordered Bronze→Silver loop
│       ├── new_equities_orchestrator.py
│       ├── dataset/
│       │   ├── loaders/              # YAML keymap loader
│       │   ├── models/               # DatasetRecipe, DatasetKeymapEntry, DatasetIdentity, watermark
│       │   └── services/             # DatasetService (loads keymap, exposes recipes)
│       ├── dtos/
│       │   ├── bronze_to_silver_dto.py  # Base DTO class (from_row / to_dict contract)
│       │   ├── dto_registry.py          # Dataset → DTO class mapping
│       │   ├── dto_projection.py        # Column projection helpers
│       │   ├── models.py
│       │   ├── company/              # CompanyDTO, CompanyEmployeesDTO, etc.
│       │   ├── economics/            # EconomicsDTO, TreasuryRatesDTO, MarketRiskPremiumDTO
│       │   ├── fundamentals/         # IncomeStatementDTO, BalanceSheetDTO, CashflowDTO, etc.
│       │   ├── instrument/           # StockListDTO, ETFListDTO, ETFHoldingsDTO, etc.
│       │   └── technicals/           # PriceEODDTO, SMA/EMA/RSI/ADX/Williams DTOs
│       ├── infra/
│       │   ├── duckdb/               # DuckDB bootstrap and migration runner
│       │   ├── logger.py             # LoggerFactory
│       │   ├── result_file_adaptor.py # Bronze JSON file read/write
│       │   └── universe_repo.py      # Ticker universe persistence
│       ├── ops/
│       │   ├── dtos/                 # BronzeIngestItem, SilverIngestItem, FileIngestion
│       │   ├── infra/                # DuckDB ops table repository
│       │   ├── requests/             # PromotionConfig
│       │   └── services/             # OpsService (run lifecycle, manifest writes)
│       ├── run/
│       │   ├── dtos/                 # RunContext, RunRequest, BronzeResult, ResultMapper
│       │   └── services/             # RunRequestExecutor, ChunkEngine, DedupeEngine,
│       │                             #   OrchestrationTickerChunkService
│       └── services/
│           ├── bronze/               # BronzeService, BronzeBatchReader
│           ├── silver/               # SilverService, InstrumentPromotionService
│           └── universe_service.py   # Resolves active ticker universe
├── tests/
│   ├── unit/                     # Unit tests (dataset, DTOs, infra)
│   └── e2e/                      # End-to-end tests with fake HTTP server
└── pyproject.toml
```

---

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `orchestrator.py` | Entry point. Iterates domains in order, calls Bronze ingestion then Silver promotion per domain. Manages `OrchestrationSettings` feature switches. |
| `dataset/services/dataset_service.py` | Loads `dataset_keymap.yaml`, validates entries, exposes filtered recipe lists by plan/domain. |
| `run/dtos/run_request.py` | Encapsulates a single API call spec: URL, query vars (placeholders expanded), cadence metadata, `from_date`/`to_date`. |
| `run/dtos/bronze_result.py` | Wraps the HTTP response + metadata. Computes `is_valid_bronze` and `canPromoteToSilverWith` gates. |
| `run/services/run_request_executor.py` | Executes HTTP requests with retry + throttle. Writes `BronzeResult` to Bronze JSON via `ResultFileAdaptor`. |
| `services/bronze/bronze_service.py` | Orchestrates Bronze ingestion for a list of recipes: builds `RunRequest` objects, calls executor, records manifest rows. |
| `services/silver/silver_service.py` | Reads promotable Bronze manifest rows, instantiates DTOs via `from_row`, MERGEs into Silver DuckDB tables, updates watermarks. |
| `ops/services/ops_service.py` | Manages run lifecycle in DuckDB: `start_run`, `finish_run`, manifest writes, watermark upserts. |
| `infra/duckdb/duckdb_bootstrap.py` | Opens/creates the DuckDB file, applies pending SQL migrations from `db/migrations/`. |
| `dtos/bronze_to_silver_dto.py` | Base class enforcing the `from_row` / `to_dict` contract. Provides safe parse helpers (dates, floats, ints). |
| `dtos/dto_registry.py` | Maps dataset name strings → DTO classes. Used by `SilverService` for dynamic dispatch. |
| `sbfoundation/settings.py` | Single module of all constants: domain names, dataset names, data source config, placeholder strings, folder names, cadence modes, FMP plan tiers. |
| `sbfoundation/folders.py` | Resolves `DATA_ROOT_FOLDER` / `REPO_ROOT_FOLDER` into concrete `Path` objects for Bronze, DuckDB, logs, migrations, and keymap. |

---

## Data Flow

```
External API (FMP)
       │
       │  HTTP GET (RunRequest: URL + expanded query_vars)
       ▼
RunRequestExecutor
  ├── Retry (3x, exponential backoff)
  ├── Throttle (≤50 calls/min for FMP)
  └── → BronzeResult (raw response + metadata)
       │
       ▼
ResultFileAdaptor
  └── Writes:  bronze/<domain>/<source>/<dataset>/<ticker>/<date>-<uuid>.json
       │
       ▼
OpsService.write_manifest()
  └── Inserts row into ops.bronze_manifest
      (file_path_rel, payload_hash, coverage dates, status_code, is_promotable)
       │
       │  (after all Bronze for a domain completes)
       ▼
SilverService.promote()
  ├── Reads promotable ops.bronze_manifest rows (status_code=200, no error)
  ├── Loads Bronze JSON via ResultFileAdaptor
  ├── Parses rows → DTOs via BronzeToSilverDTO.from_row()
  ├── MERGE/UPSERT into silver.<table_name> (keyed by dataset key_cols)
  │     Every row carries: bronze_file_id, run_id, ingested_at, row_date_col
  └── Upserts ops.dataset_watermarks (coverage_from/to, last_success_at)
       │
       ▼
silver.<table_name>  (DuckDB)
       │
       ▼
  [Downstream: Gold layer, backtesting, strategy engine — separate packages]
```

**Ticker based domain execution order:** `instrument` → `company` → `fundamentals` → `technicals`

Per-ticker recipes run in chunks of 10 tickers to bound memory and allow incremental Silver promotion between chunks.

---

## Configuration

### `config/dataset_keymap.yaml`

The single authoritative source for all dataset definitions. Each entry specifies:

```yaml
- domain: company
  source: fmp
  dataset: company-profile
  discriminator: ''           # partition key for shared datasets (e.g. economics indicators)
  ticker_scope: per_ticker    # per_ticker | global
  silver_schema: silver
  silver_table: fmp_company_profile
  key_cols: [ticker]          # natural key for UPSERT
  row_date_col: null          # date column in Silver row (null = use as_of_date)
  recipes:
    - plans: [basic]          # FMP plan required: basic | starter | premium | ultimate
      data_source_path: profile
      query_vars: {symbol: __ticker__}
      date_key: null          # field in API response rows holding observation date
      cadence_mode: interval
      min_age_days: 365       # days since last ingestion before re-fetching
      run_days: [sat]         # weekday allowlist
      execution_phase: data_acquisition   # instrument_discovery | data_acquisition
      help_url: https://...
  dto_schema:
    dto_type: sbfoundation.dtos.company.company_dto.CompanyDTO
    columns:
      - {name: ticker, type: str, nullable: false}
```

**Query var placeholders** (substituted at runtime):

| Placeholder | Replaced with |
|---|---|
| `__ticker__` | Current ticker symbol |
| `__from__` | Computed `from_date` (last watermark or universe start date) |
| `__to__` | Today's date |
| `__from_one_month_ago__` | One month before today |
| `__limit__` | Default fetch limit |
| `__period__` | Reporting period (annual/quarter) |

### Environment / `.env`

| Variable | Default | Purpose |
|---|---|---|
| `FMP_API_KEY` | *(required)* | FMP REST API key |
| `DATA_ROOT_FOLDER` | `c:/sb/SBFoundation/data` | Root for Bronze files, DuckDB, logs |
| `REPO_ROOT_FOLDER` | `c:/sb/SBFoundation` | Repo root for `config/` and `db/migrations/` |
| `DATASET_KEYMAP_FILENAME` | `dataset_keymap.yaml` | Keymap filename override |

### `OrchestrationSettings` (runtime switches)

Passed to `Orchestrator` to control which domains, layers, and ticker modes are active in a given run. Useful for incremental runs, debugging, or backfilling a single domain without touching others.

```python
OrchestrationSettings(
    enable_instrument=True,
    enable_economics=True,
    enable_company=True,
    enable_fundamentals=True,
    enable_technicals=True,
    enable_bronze=True,
    enable_silver=True,
    enable_non_ticker_run=True,
    enable_ticker_run=True,
    enable_update_tickers=True,
    enable_new_tickers=True,
    non_ticker_recipe_limit=99,
    ticker_recipe_limit=99,
    update_ticker_limit=500,
    new_ticker_limit=50,
    fmp_plan="starter",         # basic | starter | premium | ultimate
)
```

---

## How to Debug and Run

### Run the full pipeline

```bash
# Activate the venv (Poetry does this automatically in `poetry run`)
poetry run python src/sbfoundation/orchestrator.py
```

The `if __name__ == "__main__"` block at the bottom of `orchestrator.py` contains a ready-to-edit example. Adjust `OrchestrationSettings` flags to scope the run.

### Run tests

```bash
poetry run pytest                       # all tests
poetry run pytest tests/unit/           # unit tests only
poetry run pytest tests/e2e/            # end-to-end tests (spins up a fake HTTP server)
poetry run pytest --cov=src             # with coverage
```

### Code quality checks

```bash
poetry run black --check src tests      # formatting
poetry run isort --check-only src tests # import ordering
poetry run flake8 src tests             # linting
poetry run mypy src                     # type checking
```

### Debugging a single domain

Edit `orchestrator.py`'s `__main__` block and set all `enable_*` flags to `False` except the domain of interest:

```python
OrchestrationSettings(
    enable_company=True,
    enable_bronze=True,
    enable_silver=False,   # skip promotion to inspect Bronze only
    enable_ticker_run=True,
    enable_new_tickers=True,
    new_ticker_limit=3,    # process only 3 tickers
    ...
)
```

### Inspecting Bronze files

Bronze JSON files are written to `$DATA_ROOT_FOLDER/bronze/<domain>/<source>/<dataset>/<ticker>/<date>-<uuid>.json`. Each file is a self-describing `BronzeResult` containing the full request spec and raw API response.

### Inspecting Silver / ops tables

```python
import duckdb
con = duckdb.connect("c:/sb/SBFoundation/data/duckdb/sb/SBFoundation.duckdb")
con.execute("SELECT * FROM ops.bronze_manifest LIMIT 10").fetchdf()
con.execute("SELECT * FROM ops.dataset_watermarks").fetchdf()
con.execute("SELECT * FROM silver.fmp_company_profile LIMIT 5").fetchdf()
```

### Logs

Plain-text logs are written to `$DATA_ROOT_FOLDER/logs/`. Each log line carries the `run_id` for correlation.

---

## Strengths

- **Full auditability** — every Silver row traces back to a specific Bronze JSON file via `bronze_file_id`. Lineage is never broken.
- **Deterministic replay** — Bronze is immutable and self-describing. Silver logic can be changed and Bronze re-promoted without re-calling external APIs.
- **Declarative, single-source configuration** — adding a new dataset requires only a `dataset_keymap.yaml` entry and a DTO class; no changes to orchestration logic.
- **Audit-first failure handling** — failed requests produce error artifacts and the run continues, preventing a single bad ticker from blocking the whole pipeline.
- **Cadence gating** — watermark-based `min_age_days` prevents wasteful re-ingestion without requiring a separate scheduler to track state.
- **Idempotent Silver** — MERGE semantics mean replaying Bronze is always safe; no manual deduplication step needed.
- **Portable DuckDB** — the single DuckDB file uses repo-relative paths, so it can be copied from Raspberry Pi (PROD) to a development machine without any path fixups.
- **Clear layer isolation** — Bronze has zero business logic; Silver has zero raw-payload knowledge. The DTO boundary enforces this structurally.

---

## Issues and Risks

| Issue | Severity | Notes |
|---|---|---|
| **Silver deduplication not yet enforced** | Medium | MERGE semantics prevent exact-key duplicates, but period normalization and late-arrival deduplication are not implemented. Downstream consumers should be aware of potential duplicates for datasets without stable natural keys. |
| **Single-writer DuckDB** | Medium | The system is designed for a single-process writer. Concurrent ingestion runs (e.g., two Prefect deployments) will cause DuckDB lock contention. |
| **Parquet → DuckDB migration** | ~~Medium~~ Resolved | All Parquet references removed from active code. `silver_data_contracts.md` does not exist in the repo. Stale Parquet comments in `result_mapper.py`, `bronze_to_silver_dto.py`, and `scripts/cleanup_ticker_state_partitions.py` have been updated. No `pyarrow` or `fastparquet` imports remain in the codebase. DuckDB is now the sole Silver/Gold storage backend. |
| **No pagination support** | Medium | `DatasetRecipe` defers pagination by design. All large datasets rely on `from_date` windowing (`from_date` → `to_date` = today) rather than offset or cursor pagination. If a single API window returns a truncated result set (e.g., FMP caps responses at 10 000 rows), data beyond that limit is silently dropped. Mitigation: use shorter `min_age_days` windows for high-volume datasets. Full fix requires adding `page`/`cursor` support to `RunProvider._get_query_vars()` and a looping driver in `bronze_service.py`. |
| **FMP API key is the only configured source** | Low | `DATA_SOURCES_CONFIG` only has an FMP entry. Alpha Vantage, BIS, FRED, and other planned sources have dataset constants defined but no HTTP configuration yet. |
| **`sbfoundation/settings.py` uses wildcard import** | Low | `from sbfoundation.settings import *` is used in `orchestrator.py` and `sbfoundation/folders.py`. This makes static analysis harder and can cause name collisions if settings grow. |
| **No concurrency / parallelism** | Info | Bronze ingestion is sequential per recipe. Throughput is bounded by `THROTTLE_MAX_CALLS_PER_MINUTE` (50/min for FMP). Large universes (1000+ tickers × 40+ datasets) take significant wall-clock time. |
| **PROD runs on Raspberry Pi** | Info | Low RAM and single-core constraints apply. Chunk size (10 tickers) and recipe limits in `OrchestrationSettings` are the primary throughput controls. |
