# SBFoundation — Strawberry Labs Bronze + Silver + Gold Pipeline

SBFoundation is the data acquisition, validation, and analytics modeling package for the **Strawberry Labs** AI trading platform. It implements all three layers of a medallion/lakehouse architecture:

- **Bronze** — raw, append-only vendor API responses with full ingestion metadata
- **Silver** — validated, typed, and conformed datasets (clean, standalone tables with natural business keys only)
- **Gold** — star-schema analytics layer: static dimensions, data-derived dimensions, and fact tables built from Silver

---

## Overview

The pipeline ingests financial data from external providers (primarily Financial Modeling Prep), persists raw responses as immutable JSON files (Bronze), and promotes them to structured DuckDB tables (Silver) via typed Data Transfer Objects (DTOs). Every step is traceable: each Silver row carries a `bronze_file_id` linking it back to its source file.

**Silver tables are clean, standalone datasets:**

- Natural business keys only (e.g., `ticker`, `symbol`, `date`)
- No surrogate keys (no `instrument_sk` or other `*_sk` columns)
- No foreign key relationships between tables
- Lineage metadata: `bronze_file_id`, `run_id`, `ingested_at`

**Data domains ingested** (8 domains, ~107 datasets):

| # | Domain | Scope | Content | Datasets |
|---|---|---|---|---|
| 1 | `market` | global + per exchange | Universe discovery (stock/ETF/index lists, ETF holdings) + countries, exchanges, sectors, industries, trading hours, holidays, sector/industry performance & PE (back to 2013) | 14 |
| 2 | `economics` | global | GDP, CPI, unemployment, Fed funds, treasury rates, mortgage rates, market risk premium | 29 |
| 3 | `company` | per ticker | Profile, peers, employees, market cap, shares float, officers, compensation, delisted | 9 |
| 4 | `fundamentals` | per ticker | Income/balance sheet/cash flow statements + growth series, key metrics, ratios, scores, owner earnings, enterprise values, revenue segmentation | 25 |
| 5 | `technicals` | per ticker | EOD price history (full/split/dividend-adjusted), SMA/EMA/WMA/DEMA/TEMA, RSI, ADX, Williams %R, std deviation | 24 |
| 6 | `commodities` | global + per symbol | Commodities universe list and historical EOD prices | 2 |
| 7 | `fx` | global + per pair | Forex pair universe list and historical EOD exchange rates | 2 |
| 8 | `crypto` | global + per symbol | Cryptocurrency universe list and historical EOD prices | 2 |

**📖 For full dataset details, refresh cadences, Silver table names, and API links, see [Domain & Dataset Reference](docs/domain_datasets_reference.md)**

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

**Schema layout:**

- `ops` — manifests, watermarks, migrations (managed by this project)
- `silver` — conformed datasets, one table per dataset (managed by this project)
- `gold` — star schema: static dims, data-derived dims, fact tables (managed by this project)

### 5. Silver writes are idempotent (MERGE/UPSERT)

Silver promotion uses the dataset's `key_cols` from the keymap to MERGE rows. Replaying the same Bronze file produces no duplicates.

### 6. Ingestion cadence is data-driven, not clock-driven

The `RunProvider` computes `from_date` from the last successfully ingested `to_date` stored as a dataset watermark, not from a fixed schedule. A recipe's `min_age_days` gates whether a dataset is due for re-ingestion.

### 7. Domain execution order is enforced

The `market` domain should run first — it populates `silver.fmp_stock_list` which seeds the ticker universe for company/fundamentals/technicals. Company/fundamentals/technicals each require `exchanges` in their `RunCommand` and are run as separate, standalone commands.

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
FRED_API_KEY=your_fred_api_key_here    # required for FRED datasets (fred-dgs10, fred-usrecm)
FMP_PLAN = "ultimate"                             # the data ingestion only runs import for datasets in purchased plan
DATA_ROOT_FOLDER=c:/sb/SBFoundation/data          # Bronze JSON files, DuckDB, logs
REPO_ROOT_FOLDER=c:/sb/SBFoundation               # Repo root (used for config/ and db/migrations/)
DATASET_KEYMAP_FILENAME=dataset_keymap.yaml       # The configuration for each ingested dataset
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
| Active additional source | FRED (Federal Reserve Economic Data) via REST — `fred-dgs10`, `fred-usrecm` |
| Planned / future | Alpha Vantage, BIS |
| Orchestration | Prefect OSS (nightly batch; `orchestrate/` package in this project) |
| UI | Streamlit + streamlit-echarts + Altair (separate package) |
| Deployment | Docker Compose; used for PROD deploy |

---

## Repo Structure

```
SBFoundation/
├── config/
│   └── dataset_keymap.yaml       # AUTHORITATIVE dataset/recipe/DTO/Silver-table definitions
├── docs/
│   ├── backlog/                  # ExecPlans queued for implementation
│   └── completed/                # ExecPlans that have been fully implemented and closed out
├── src/
│   └── sbfoundation/
│       ├── __init__.py               # Public API: SBFoundationAPI, RunCommand
│       ├── api.py                    # Main entry point for running data ingestion
│       ├── settings.py               # All constants: domains, datasets, data sources, placeholders, paths
│       ├── folders.py                # Path resolution helpers (bronze/duckdb/log/migration folders)
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
│       ├── coverage/
│       │   ├── coverage_index_service.py  # Aggregates file_ingestions → ops.coverage_index
│       │   ├── cli.py                     # CLI: python -m sbfoundation.coverage [subcommand]
│       │   └── __main__.py
│       ├── ops/
│       │   ├── dtos/                 # BronzeIngestItem, SilverIngestItem, FileIngestion
│       │   ├── infra/                # DuckDB ops table repository
│       │   ├── requests/             # PromotionConfig
│       │   └── services/             # OpsService (run lifecycle, manifest writes)
│       ├── run/
│       │   ├── dtos/                 # RunContext, RunRequest, BronzeResult, ResultMapper
│       │   └── services/             # RunRequestExecutor, ChunkEngine, DedupeEngine,
│       │                             # OrchestrationTickerChunkService
│       ├── bronze/                   # BronzeService, BronzeBatchReader
│       ├── silver/                   # SilverService, InstrumentPromotionService
│       ├── gold/                     # GoldDimService (dim_instrument, dim_company),
│       │                             # GoldFactService (fact_eod, fact_quarter, fact_annual),
│       │                             # GoldBootstrapService (static dims)
│       ├── eod/                      # EodService — daily bulk EOD price + company profile
│       ├── quarter/                  # QuarterService — quarterly bulk fundamentals (earnings seasons)
│       ├── annual/                   # AnnualService — annual bulk fundamentals (Jan–Mar)
│       ├── maintenance/              # DuckDB bootstrap, migration runner, static dim seeding
│       ├── orchestrate/              # Prefect flows: eod_flow, quarter_flow, annual_flow
│       └── services/
│           └── universe_service.py   # Resolves active ticker universe
├── apps/
│   └── coverage_dashboard/       # Standalone Streamlit app (separate Poetry project)
│       ├── pyproject.toml
│       ├── .streamlit/config.toml
│       ├── Home.py               # Landing page: global KPIs + dataset summary
│       └── pages/
│           ├── 1_Global_Overview.py
│           ├── 2_Dataset_Drilldown.py
│           ├── 3_Ticker_Drilldown.py
│           └── 4_Ingestion_Diagnostics.py
├── tests/
│   ├── unit/                     # Unit tests (dataset, DTOs, infra, coverage)
│   └── e2e/                      # End-to-end tests with fake HTTP server
└── pyproject.toml
```

---

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `api.py` | Main entry point. Provides `SBFoundationAPI` class and `RunCommand` dataclass. Orchestrates domain-specific ingestion flows (Bronze → Silver) for market, economics, company, fundamentals, technicals, commodities, forex, and crypto domains. `RunCommand.validate()` enforces domain validity and exchange requirements. |
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

## Historical Data Backfill

Each domain service file contains an `if __name__ == "__main__"` block that serves as the entrypoint for backfilling historical data. Running the file directly in VS Code also enables full debugger support (`concurrent_requests=1` keeps execution synchronous).

| Service file | What it backfills | How to control the range |
|---|---|---|
| `src/sbfoundation/eod/eod_service.py` | EOD prices — one trading day at a time (Mon–Fri) | Edit `_start` / `_end` date range in the `__main__` block |
| `src/sbfoundation/annual/annual_service.py` | Annual fundamentals — one fiscal year at a time | Edit the `range(start_year, end_year)` in the `__main__` block |
| `src/sbfoundation/quarter/quarter_service.py` | Quarterly fundamentals — one quarter at a time (Q1–Q4 × year) | Edit the year `range` and period list in the `__main__` block |

**Season gates are bypassed** when explicit date/year/period parameters are provided, so backfill runs work regardless of the current calendar date.

---

## Data Flow

```
External API (FMP)
       │
       │  HTTP GET (RunRequest: URL + expanded query_vars)
       ▼
RunRequestExecutor
  ├── Retry (3x, exponential backoff)
  ├── Throttle (<=THROTTLE_MAX_CALLS_PER_MINUTE calls/min)
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
GoldDimService / GoldFactService  (gold/ package)
  ├── Resolves surrogate keys (dim_instrument, dim_company)
  ├── Builds static dims (dim_date, dim_country, dim_exchange, etc.)
  ├── MERGE/UPSERT into gold.<dim|fact_table>
  └── Logs build to ops.gold_build (model_version, input_watermarks, row_counts)
       │
       ▼
gold.<dim|fact_table>  (DuckDB)
       │
       ▼
  [Downstream: Feature Engineer, Signals, backtesting, portfolio optimization, execution — separate packages]
```

**Recommended domain execution order:** `market` → `economics` → `company` → `fundamentals` → `technicals` → `commodities` → `fx` → `crypto`

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

---

## How to Debug and Run

### Run the full pipeline

```bash
# Activate the venv (Poetry does this automatically in `poetry run`)
poetry run python src/sbfoundation/api.py
```

The `if __name__ == "__main__"` block at the bottom of `api.py` contains a ready-to-edit example. Adjust `RunCommand` parameters to scope the run.

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

Edit `api.py`'s `__main__` block and configure the `RunCommand` for the domain of interest:

```python
command = RunCommand(
    domain=MARKET_DOMAIN,           # Choose domain: MARKET, ECONOMICS, COMPANY, FUNDAMENTALS, TECHNICALS, COMMODITIES, FX, CRYPTO
    concurrent_requests=1,           # Set to 1 for synchronous debugging, 10+ for concurrent mode
    enable_bronze=True,             # True to fetch from APIs
    enable_silver=False,            # False to inspect Bronze only (skip Silver promotion)
    ticker_limit=3,                 # Process only 3 tickers
    ticker_recipe_chunk_size=10,    # Chunk size for ticker processing
)
result = SBFoundationAPI(today=date.today().isoformat()).run(command)
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

Plain-text logs are written to `$DATA_ROOT_FOLDER/logs/`. Each log file is named `logs_<YYYY-MM-DD>.txt` (one per calendar day, append mode).

**Log line format:**

```
2026-02-20 07:15:32,412 | INFO    | SBFoundationAPI | run_id=abc123 | Run Start
│                          │          │                  │               │
│                          │          │                  │               message
│                          │          │                  run_id prefix (when provided)
│                          │          logger name (padded to 15 chars)
│                          level (padded to 7 chars)
timestamp
```

**Log levels** are controlled by the `ENV` environment variable and the optional `log_level` argument to `LoggerFactory`:

| Condition | Effective level |
|---|---|
| `ENV=DEV` | `INFO` |
| `ENV` unset / other | `WARN` |
| `LoggerFactory(log_level="DEBUG")` | `DEBUG` (overrides env) |

**`run_id` correlation** — every log method (`info`, `debug`, `warning`, `error`, `critical`, `exception`, `log`) accepts an optional `run_id` keyword argument. When provided, the message is prefixed with `run_id=<value> |`, enabling grep-based filtering across the full run:

```bash
grep "run_id=abc123" "$DATA_ROOT_FOLDER/logs/logs_2026-02-20.txt"
```

**`log_section`** — marks major pipeline phases with a prominent banner:

```
run_id=abc123 | ========== Processing economics domain ==========
```

**Creating a logger** — each class obtains its logger via `LoggerFactory`:

```python
from sbfoundation.infra.logger import LoggerFactory, SBLogger

class MyService:
    def __init__(self, logger: SBLogger | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)

    def do_work(self, run_id: str) -> None:
        self._logger.log_section(run_id, "Starting work")
        self._logger.info("Processing 42 items", run_id=run_id)
        self._logger.warning("Something looks off", run_id=run_id)
```

**Both handlers are always active** — each logger writes to `sys.stdout` and to the daily log file simultaneously. `logger.propagate = False` prevents double-writing via the root logger.

**Injecting a custom logger** (for tests or controlled output):

```python
import logging
mock_logger = logging.getLogger("test")
service = MyService(logger=mock_logger)
```

---

## Coverage Dashboard

The **Data Coverage Index (DCI)** answers four questions without touching raw Bronze files:

1. What datasets exist?
2. Which tickers are covered per dataset?
3. What date range exists per ticker?
4. Where are gaps relative to expectation?

Coverage data is materialised into `ops.coverage_index` automatically after every pipeline run. It is also exposed via a CLI and a Streamlit dashboard.

### How it works

`CoverageIndexService.refresh()` aggregates `ops.file_ingestions` into one row per `(domain, source, dataset, discriminator, ticker)` and upserts the result. The refresh is non-fatal — a failure is logged as a warning and does not abort the pipeline run.

### CLI

```bash
# Summary: all datasets sorted by coverage ratio (weakest first)
poetry run python -m sbfoundation.coverage summary

# Per-ticker coverage for a single dataset
poetry run python -m sbfoundation.coverage dataset fmp-price-eod

# Per-dataset coverage for a single ticker
poetry run python -m sbfoundation.coverage ticker AAPL

# Snapshot datasets not refreshed in ≥90 days (default)
poetry run python -m sbfoundation.coverage stale
poetry run python -m sbfoundation.coverage stale --days 30
```

### Streamlit Dashboard

The dashboard is a separate Poetry project under `apps/coverage_dashboard/`. It requires its own install.

**One-time setup:**

```bash
cd apps/coverage_dashboard
poetry install
```

**Run:**

```bash
cd apps/coverage_dashboard
poetry run streamlit run Home.py
# Opens at http://localhost:8501
```

**Pages:**

| Page | Description |
|---|---|
| **Home** | Global KPIs — total datasets, tickers, avg coverage, datasets with errors |
| **1 — Global Overview** | Heatmap of 4 coverage metrics across all datasets; bottom-20 bar chart |
| **2 — Dataset Drilldown** | Histogram + sortable table + temporal presence heatmap for a selected dataset |
| **3 — Ticker Drilldown** | Completeness gauge + per-dataset bar chart + detail table for a selected ticker |
| **4 — Ingestion Diagnostics** | Error rates, latency (avg/p95/max), hash stability, and error log from `ops.file_ingestions` |

**Prerequisites:**

- The main package must be installed in the same environment (`sb-foundation` is declared as a path dependency in `apps/coverage_dashboard/pyproject.toml`).
- The DuckDB file must exist and have data (`ops.coverage_index` populated by at least one pipeline run).
- Close any other DuckDB connections (e.g., DuckDB CLI or GUI) before launching — DuckDB allows only one writer at a time.

**Manually refresh the index** (without running the full pipeline):

```bash
poetry run python -c "
from datetime import date
from sbfoundation.coverage.coverage_index_service import CoverageIndexService
svc = CoverageIndexService()
n = svc.refresh(run_id='manual', universe_from_date=date(1990, 1, 1), today=date.today())
print(f'Upserted {n} rows')
"
```

---

## Economics Data

The Economics domain provides macroeconomic indicators, treasury rates, and market risk premium data for top-down economic analysis and risk assessment.

**Load Order:** Economics data is loaded after instrument data in the domain execution sequence.

### Datasets

#### 1. treasury-rates

- **Purpose:** Daily U.S. Treasury rates across the yield curve (1-month to 30-year maturities)
- **Scope:** Global (non-ticker-based)
- **Refresh:** Daily (min_age_days: 1)
- **Silver Table:** `silver.fmp_treasury_rates`
- **Key Columns:** `date`
- **API Endpoint:** `https://financialmodelingprep.com/stable/treasury-rates?from=__from__&to=__to__`
- **Documentation:** [FMP Treasury Rates](https://site.financialmodelingprep.com/developer/docs#treasury-rates)
- **Use Case:** Risk-free rate analysis, yield curve modeling, interest rate tracking

#### 2. market-risk-premium

- **Purpose:** Historical market risk premium for CAPM calculations
- **Scope:** Global (non-ticker-based)
- **Refresh:** Yearly (min_age_days: 365)
- **Silver Table:** `silver.fmp_market_risk_premium`
- **Key Columns:** `country`
- **API Endpoint:** `https://financialmodelingprep.com/stable/market-risk-premium`
- **Documentation:** [FMP Market Risk Premium](https://site.financialmodelingprep.com/developer/docs#market-risk-premium)
- **Use Case:** Equity risk modeling, expected return calculations

#### 3. FRED Datasets (Federal Reserve Economic Data)

**fred-dgs10** — 10-Year Treasury Constant Maturity Rate

- **Purpose:** Daily 10-year U.S. Treasury yield (risk-free rate proxy for CAPM/DCF models)
- **Source:** FRED (Federal Reserve Bank of St. Louis)
- **Scope:** Global (non-ticker-based)
- **Refresh:** Daily (min_age_days: 1)
- **Silver Table:** `silver.fred_dgs10`
- **Key Columns:** `series_id`, `date`
- **Gold:** Silver-only — no `instrument_sk` FK; consumed directly by the feature engine
- **Requires:** `FRED_API_KEY` environment variable

**fred-usrecm** — NBER U.S. Recession Indicator

- **Purpose:** Binary monthly indicator (1 = recession, 0 = expansion) from the NBER Business Cycle Dating Committee
- **Source:** FRED (Federal Reserve Bank of St. Louis)
- **Scope:** Global (non-ticker-based)
- **Refresh:** Monthly (min_age_days: 30)
- **Silver Table:** `silver.fred_usrecm`
- **Key Columns:** `series_id`, `date`
- **Gold:** Silver-only — no `instrument_sk` FK; consumed directly by the feature engine
- **Requires:** `FRED_API_KEY` environment variable

#### 4. economic-indicators (27 indicators)

- **Purpose:** U.S. macroeconomic time series data
- **Scope:** Global (non-ticker-based)
- **Refresh:** Varies by indicator (daily to monthly)
- **Silver Table:** `silver.fmp_economic_indicators`
- **Key Columns:** `ticker`, `date`
- **API Endpoint:** `https://financialmodelingprep.com/stable/economic-indicator/{indicator}?from=__from__&to=__to__`
- **Documentation:** [FMP Economic Indicators](https://site.financialmodelingprep.com/developer/docs#economic-indicators)

**Available Indicators:**

- **GDP & Growth:** GDP, Real GDP, Nominal Potential GDP, Real GDP Per Capita
- **Inflation:** CPI, Inflation Rate, Inflation
- **Labor Market:** Unemployment Rate, Total Nonfarm Payroll, Initial Jobless Claims
- **Consumer:** Consumer Sentiment, Retail Sales
- **Manufacturing:** Industrial Production Total Index, Durable Goods Orders
- **Housing:** Housing Starts, 15-Year Mortgage Average, 30-Year Mortgage Average
- **Financial:** Federal Funds Rate, 3-Month CD Rates, Commercial Bank Credit Card Rates, Retail Money Funds
- **Trade:** Trade Balance (Goods and Services)
- **Other:** Total Vehicle Sales, Smoothed US Recession Probabilities

---

## Fundamentals Data

The Fundamentals domain provides comprehensive financial statement data, key metrics, ratios, and growth rates for fundamental analysis of equities.

**Load Order:** Fundamentals data is loaded after company data in the domain execution sequence. All fundamentals datasets are ticker-based and run for every symbol in the active universe.

### Dataset Categories

#### 1. Financial Statements (Base, Annual, Quarterly)

**Three core financial statements** with multiple period variants:

- **income-statement** - Revenue, expenses, EBITDA, net income, EPS
- **balance-sheet-statement** - Assets, liabilities, equity, working capital
- **cashflow-statement** - Operating, investing, and financing cash flows

**Period Variants** (each statement has two discriminators):

- Annual (discriminator: FY) - Full-year data; requests `period=annual`, response `period` field contains `FY`
- Quarterly (discriminator: quarter) - Quarterly data; requests `period=quarter`, response `period` field contains `Q1`–`Q4`

**Scope:** Per-ticker (runs for each symbol in universe)
**Refresh:** Quarterly (min_age_days: 90)
**Silver Tables:** `silver.fmp_income_statement`, `silver.fmp_balance_sheet_statement`, `silver.fmp_cashflow_statement`
**Key Columns:** `ticker`, `date`, `period`
**API Endpoints:**

- `https://financialmodelingprep.com/stable/income-statement?symbol={ticker}&period={annual|quarter}&limit=__limit__`
- `https://financialmodelingprep.com/stable/balance-sheet-statement?symbol={ticker}&period={annual|quarter}&limit=__limit__`
- `https://financialmodelingprep.com/stable/cashflow-statement?symbol={ticker}&period={annual|quarter}&limit=__limit__`

**Documentation:**

- [Income Statement](https://site.financialmodelingprep.com/developer/docs#income-statement)
- [Balance Sheet](https://site.financialmodelingprep.com/developer/docs#balance-sheet-statement)
- [Cash Flow](https://site.financialmodelingprep.com/developer/docs#cashflow-statement)

#### 2. latest-financial-statements

- **Purpose:** Most recently reported financial statements (all three statements in one call)
- **Scope:** Per-ticker
- **Refresh:** Daily (min_age_days: 1)
- **Silver Table:** `silver.fmp_latest_financial_statements`
- **Key Columns:** `ticker`
- **API Endpoint:** `https://financialmodelingprep.com/stable/latest-financial-statements?symbol={ticker}`
- **Documentation:** [Latest Financial Statements](https://site.financialmodelingprep.com/developer/docs#latest-financial-statements)

#### 3. Key Metrics (Base, Annual, Quarterly, TTM)

**key-metrics** - Comprehensive valuation and performance metrics including P/E ratio, price-to-book, ROE, ROA

- Period variants: Base (''), Annual (FY), Quarterly (quarter)
- Refresh: Quarterly (min_age_days: 90)
- Silver Table: `silver.fmp_key_metrics`

**key-metrics-ttm** - Trailing twelve month key metrics for most current analysis

- Refresh: Daily (min_age_days: 1)
- Silver Table: `silver.fmp_key_metrics_ttm`

**API Endpoints:**

- `https://financialmodelingprep.com/stable/key-metrics?symbol={ticker}&period={FY|quarter}&limit=__limit__`
- `https://financialmodelingprep.com/stable/key-metrics-ttm?symbol={ticker}`

**Documentation:** [Key Metrics](https://site.financialmodelingprep.com/developer/docs#key-metrics)

#### 4. Financial Ratios (Base, Annual, Quarterly, TTM)

**metric-ratios** - Liquidity, solvency, profitability, and efficiency ratios

- Period variants: Base (''), Annual (FY), Quarterly (quarter)
- Refresh: Quarterly (min_age_days: 90)
- Silver Table: `silver.fmp_metric_ratios`

**ratios-ttm** - Trailing twelve month financial ratios

- Refresh: Daily (min_age_days: 1)
- Silver Table: `silver.fmp_ratios_ttm`

**API Endpoints:**

- `https://financialmodelingprep.com/stable/financial-ratios?symbol={ticker}&period={FY|quarter}&limit=__limit__`
- `https://financialmodelingprep.com/stable/financial-ratios-ttm?symbol={ticker}`

**Documentation:** [Financial Ratios](https://site.financialmodelingprep.com/developer/docs#financial-ratios)

#### 5. financial-scores

- **Purpose:** Composite financial health metrics (Altman Z-Score, Piotroski F-Score)
- **Scope:** Per-ticker
- **Refresh:** Quarterly (min_age_days: 90)
- **Silver Table:** `silver.fmp_financial_scores`
- **Key Columns:** `ticker`
- **API Endpoint:** `https://financialmodelingprep.com/stable/financial-scores?symbol={ticker}`
- **Documentation:** [Financial Scores](https://site.financialmodelingprep.com/developer/docs#financial-scores)
- **Use Case:** Bankruptcy prediction (Z-Score), quality investing (F-Score)

#### 6. owner-earnings

- **Purpose:** Owner earnings metrics (Buffett's preferred profitability measure)
- **Scope:** Per-ticker
- **Refresh:** Quarterly (min_age_days: 90)
- **Silver Table:** `silver.fmp_owner_earnings`
- **Key Columns:** `ticker`
- **API Endpoint:** `https://financialmodelingprep.com/stable/owner-earnings?symbol={ticker}`
- **Documentation:** [Owner Earnings](https://site.financialmodelingprep.com/developer/docs#owner-earnings)
- **Use Case:** Value investing, owner-oriented profitability analysis

#### 7. enterprise-values

- **Purpose:** Enterprise value and related valuation metrics
- **Scope:** Per-ticker
- **Refresh:** Quarterly (min_age_days: 90)
- **Silver Table:** `silver.fmp_enterprise_values`
- **Key Columns:** `ticker`, `date`
- **API Endpoint:** `https://financialmodelingprep.com/stable/enterprise-values?symbol={ticker}&limit=__limit__`
- **Documentation:** [Enterprise Values](https://site.financialmodelingprep.com/developer/docs#enterprise-values)
- **Use Case:** Capital structure-neutral valuation, M&A analysis

#### 8. Growth Metrics (Base, Annual, Quarterly)

**Year-over-year and quarter-over-quarter growth rates** for all financial statements:

- **income-statement-growth** - Revenue growth, earnings growth, margin expansion
- **balance-sheet-statement-growth** - Asset growth, equity growth, debt changes
- **cashflow-statement-growth** - Cash flow growth, capex trends

**Period Variants** (each has three discriminators):

- Base (discriminator: '') - Most recent growth data
- Annual (discriminator: FY) - Year-over-year growth rates
- Quarterly (discriminator: quarter) - Quarter-over-quarter growth rates

**Refresh:** Quarterly (min_age_days: 90)
**Silver Tables:** `silver.fmp_income_statement_growth`, `silver.fmp_balance_sheet_statement_growth`, `silver.fmp_cashflow_statement_growth`
**API Endpoints:**

- `https://financialmodelingprep.com/stable/income-statement-growth?symbol={ticker}&period={FY|quarter}&limit=__limit__`
- `https://financialmodelingprep.com/stable/balance-sheet-statement-growth?symbol={ticker}&period={FY|quarter}&limit=__limit__`
- `https://financialmodelingprep.com/stable/cashflow-statement-growth?symbol={ticker}&period={FY|quarter}&limit=__limit__`

**Documentation:** [Growth Metrics](https://site.financialmodelingprep.com/developer/docs#income-statement-growth)

#### 9. financial-statement-growth

- **Purpose:** Comprehensive growth metrics across all three financial statements
- **Scope:** Per-ticker
- **Refresh:** Quarterly (min_age_days: 90)
- **Silver Table:** `silver.fmp_financial_statement_growth`
- **Key Columns:** `ticker`, `date`
- **API Endpoint:** `https://financialmodelingprep.com/stable/financial-statement-growth?symbol={ticker}&limit=__limit__`
- **Documentation:** [Financial Statement Growth](https://site.financialmodelingprep.com/developer/docs#financial-statement-growth)

#### 10. Revenue Segmentation

**revenue-product-segmentation** - Revenue breakdown by product line or business segment

- **Scope:** Per-ticker
- **Refresh:** Quarterly (min_age_days: 90)
- **Silver Table:** `silver.fmp_revenue_product_segmentation`
- **API Endpoint:** `https://financialmodelingprep.com/stable/revenue-product-segmentation?symbol={ticker}`
- **Documentation:** [Product Segmentation](https://site.financialmodelingprep.com/developer/docs#revenue-product-segmentation)

**revenue-geographic-segmentation** - Revenue breakdown by geographic region

- **Scope:** Per-ticker
- **Refresh:** Quarterly (min_age_days: 90)
- **Silver Table:** `silver.fmp_revenue_geographic_segmentation`
- **API Endpoint:** `https://financialmodelingprep.com/stable/revenue-geographic-segmentation?symbol={ticker}`
- **Documentation:** [Geographic Segmentation](https://site.financialmodelingprep.com/developer/docs#revenue-geographic-segmentation)

**Use Case:** Business mix analysis, geographic diversification assessment, segment-level performance

---

## Commodities Data

The Commodities domain provides access to historical price data for tradable commodities including energy (crude oil, natural gas), metals (gold, silver, copper), and agricultural products (corn, wheat, soybeans).

**Load Order:** Commodities data is loaded after technicals data in the domain execution sequence.

### Datasets

#### 1. commodities-list (Baseline)

- **Purpose:** Discover available commodities tracked by the vendor
- **Scope:** Global (non-ticker-based)
- **Refresh:** Yearly (min_age_days: 365)
- **Silver Table:** `silver.fmp_commodities_list`
- **Key Columns:** `symbol`
- **API Endpoint:** `https://financialmodelingprep.com/stable/commodities-list`
- **Documentation:** [FMP Commodities List](https://site.financialmodelingprep.com/developer/docs#Commoditiescurrency-list)

#### 2. commodities-price-eod (Timeseries)

- **Purpose:** Historical end-of-day price data for each commodity
- **Scope:** Per-ticker (runs for each symbol from commodities-list)
- **Refresh:** Daily (min_age_days: 1)
- **Silver Table:** `silver.fmp_commodities_price_eod`
- **Key Columns:** `symbol`, `date`
- **API Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=GCUSD`
- **Documentation:** [FMP Commodities Historical Price](https://site.financialmodelingprep.com/developer/docs#Commoditiescurrency-historical-price-eod-full)

---

## Cryptocurrency Data

The Crypto domain provides access to historical price data for cryptocurrencies traded on exchanges worldwide, including Bitcoin, Ethereum, and thousands of altcoins.

**Load Order:** Crypto data is loaded after FX data in the domain execution sequence.

### Datasets

#### 1. crypto-list (Baseline)

- **Purpose:** Discover available cryptocurrencies and trading pairs
- **Scope:** Global (non-ticker-based)
- **Refresh:** Yearly (min_age_days: 365)
- **Silver Table:** `silver.fmp_crypto_list`
- **Key Columns:** `symbol`
- **API Endpoint:** `https://financialmodelingprep.com/stable/cryptocurrency-list`
- **Documentation:** [FMP Cryptocurrency List](https://site.financialmodelingprep.com/developer/docs#cryptocurrency-list)

#### 2. crypto-price-eod (Timeseries)

- **Purpose:** Historical end-of-day price data for each cryptocurrency
- **Scope:** Per-ticker (runs for each symbol from crypto-list)
- **Refresh:** Daily (min_age_days: 1)
- **Silver Table:** `silver.fmp_crypto_price_eod`
- **Key Columns:** `symbol`, `date`
- **API Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=BTCUSD`
- **Documentation:** [FMP Crypto Historical Price](https://site.financialmodelingprep.com/developer/docs#cryptocurrency-historical-price-eod-full)

---

## Foreign Exchange (FX) Data

The FX domain provides access to historical exchange rate data for currency pairs traded on the forex market, enabling multi-currency analysis and hedging strategies.

**Load Order:** FX data is loaded after commodities data in the domain execution sequence.

### Datasets

#### 1. fx-list (Baseline)

- **Purpose:** Discover available currency pairs
- **Scope:** Global (non-ticker-based)
- **Refresh:** Yearly (min_age_days: 365)
- **Silver Table:** `silver.fmp_fx_list`
- **Key Columns:** `symbol`
- **API Endpoint:** `https://financialmodelingprep.com/stable/forex-list`
- **Documentation:** [FMP Forex List](https://site.financialmodelingprep.com/developer/docs#forex-list)

#### 2. fx-price-eod (Timeseries)

- **Purpose:** Historical end-of-day exchange rates for each currency pair
- **Scope:** Per-ticker (runs for each symbol from fx-list)
- **Refresh:** Daily (min_age_days: 1)
- **Silver Table:** `silver.fmp_fx_price_eod`
- **Key Columns:** `symbol`, `date`
- **API Endpoint:** `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=EURUSD`
- **Documentation:** [FMP Forex Historical Price](https://site.financialmodelingprep.com/developer/docs#forex-historical-price-eod-full)

---

## Gold Layer and Feature Column Conventions

### Fact Tables

| Table | Grain | Source Silver Tables |
|---|---|---|
| `gold.fact_eod` | (instrument_sk, date_sk) | `fmp_eod_bulk_price` |
| `gold.fact_quarter` | (instrument_sk, period_date_sk, period) | `fmp_income_bulk_quarter`, `fmp_balance_sheet_bulk_quarter`, `fmp_cashflow_bulk_quarter` |
| `gold.fact_annual` | (instrument_sk, period_date_sk) | `fmp_income_bulk_annual`, `fmp_balance_sheet_bulk_annual`, `fmp_cashflow_bulk_annual`, `fmp_key_metrics_bulk_annual`, `fmp_ratios_bulk_annual` |

### Feature Column Naming Convention

All **feature placeholder columns** in Gold fact tables must end in **`_f`**. Signal/score columns end in **`_s`**. These suffixes are mandatory.

| Suffix | Meaning | Example |
|---|---|---|
| `_f` | Feature — measured property of an instrument at a time; computed by the feature engine | `momentum_1m_f`, `volatility_30d_f` |
| `_s` | Signal/Score — opinion derived from features; computed by the signal engine | `moat_score_s` |

Feature placeholder columns in `gold.fact_eod` (always NULL until the feature engine runs):
- `momentum_1m_f`, `momentum_3m_f`, `momentum_6m_f`, `momentum_12m_f`
- `volatility_30d_f`

### Silver-Only Datasets (no Gold promotion)

Some datasets cannot join to the Gold star schema because they have no `instrument_sk` foreign key. These remain in Silver and are consumed directly by the feature engine:

| Silver Table | Content | Reason Silver-only |
|---|---|---|
| `silver.fred_dgs10` | 10-year Treasury yield (daily) | No ticker — macro series |
| `silver.fred_usrecm` | NBER recession indicator (monthly) | No ticker — macro series |
| `silver.fmp_market_risk_premium` | Equity risk premium by country | No ticker — country-level |

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
| **FMP API key is the only configured source** | ~~Low~~ Resolved | FRED is now fully configured. `DATA_SOURCES_CONFIG` includes both FMP and FRED entries. `BronzeService` resolves API keys per-source: FMP key for FMP recipes, `FRED_API_KEY` env var for FRED recipes. Alpha Vantage and BIS remain planned. |
| **`sbfoundation/settings.py` uses wildcard import** | Low | `from sbfoundation.settings import *` is used in `api.py` and `sbfoundation/folders.py`. This makes static analysis harder and can cause name collisions if settings grow. |
| **No concurrency / parallelism** | Info | Bronze ingestion is sequential per recipe. Throughput is bounded by `THROTTLE_MAX_CALLS_PER_MINUTE` (50/min for FMP). Large universes (1000+ tickers × 40+ datasets) take significant wall-clock time. |
| **PROD runs on Raspberry Pi** | Info | Low RAM and single-core constraints apply. Chunk size (10 tickers) and recipe limits in `OrchestrationSettings` are the primary throughput controls. |
