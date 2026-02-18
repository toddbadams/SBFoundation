# SBFoundation — Strawberry Labs Bronze + Silver Pipeline

SBFoundation is the data acquisition and validation package for the **Strawberry Labs** AI trading platform. It implements **ONLY the first two layers** of a medallion/lakehouse architecture:

- **Bronze** — raw, append-only vendor API responses with full ingestion metadata
- **Silver** — validated, typed, and conformed datasets (clean, standalone tables with NO relationships)

**What this project does NOT include:**
- ❌ Gold layer (dimension modeling, star schemas, surrogate keys)
- ❌ Surrogate key resolution (e.g., `instrument_sk`, `company_sk`)
- ❌ Foreign key relationships or cross-table joins
- ❌ Aggregations, rollups, or derived analytics tables

Downstream Gold layer construction and strategy execution live in separate packages that import SBFoundation.

---

## Overview

The pipeline ingests financial data from external providers (primarily Financial Modeling Prep), persists raw responses as immutable JSON files (Bronze), and promotes them to structured DuckDB tables (Silver) via typed Data Transfer Objects (DTOs). Every step is traceable: each Silver row carries a `bronze_file_id` linking it back to its source file.

**Silver tables are clean, standalone datasets:**
- Natural business keys only (e.g., `ticker`, `symbol`, `date`)
- No surrogate keys (no `instrument_sk` or other `*_sk` columns)
- No foreign key relationships between tables
- Lineage metadata: `bronze_file_id`, `run_id`, `ingested_at`

**Data domains ingested** (9 domains, ~109 datasets):

| # | Domain | Scope | Content | Datasets |
|---|---|---|---|---|
| 1 | `instrument` | global + per ticker | Stock, ETF, index, crypto, and forex lists; ETF holdings | 6 |
| 2 | `economics` | global | GDP, CPI, unemployment, Fed funds, treasury rates, mortgage rates, market risk premium | 29 |
| 3 | `company` | per ticker | Profile, peers, employees, market cap, shares float, officers, compensation, delisted | 9 |
| 4 | `fundamentals` | per ticker | Income/balance sheet/cash flow statements + growth series, key metrics, ratios, scores, owner earnings, enterprise values, revenue segmentation | 25 |
| 5 | `technicals` | per ticker | EOD price history (full/split/dividend-adjusted), SMA/EMA/WMA/DEMA/TEMA, RSI, ADX, Williams %R, std deviation | 24 |
| 6 | `commodities` | global + per symbol | Commodities universe list and historical EOD prices | 2 |
| 7 | `fx` | global + per pair | Forex pair universe list and historical EOD exchange rates | 2 |
| 8 | `crypto` | global + per symbol | Cryptocurrency universe list and historical EOD prices | 2 |
| 9 | `market` | global + per exchange | Countries, exchanges, sectors, industries, trading hours, holidays, sector/industry performance & PE (back to 2013) | 10 |

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
| Planned / future | Alpha Vantage, FRED, BIS |
| Orchestration | Prefect OSS (nightly batch; not in this package) |
| UI | Streamlit + streamlit-echarts + Altair (separate package) |
| Deployment | Docker Compose; used for PROD deploy |

---

## Repo Structure

```
SBFoundation/
├── config/
│   └── dataset_keymap.yaml       # AUTHORITATIVE dataset/recipe/DTO/Silver-table definitions
├── docs/                         # project documentation Architecture, contracts, DuckDB design docs
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
│       ├── ops/
│       │   ├── dtos/                 # BronzeIngestItem, SilverIngestItem, FileIngestion
│       │   ├── infra/                # DuckDB ops table repository
│       │   ├── requests/             # PromotionConfig
│       │   └── services/             # OpsService (run lifecycle, manifest writes)
│       ├── run/
│       │   ├── dtos/                 # RunContext, RunRequest, BronzeResult, ResultMapper
│       │   └── services/             # RunRequestExecutor, ChunkEngine, DedupeEngine,
│       │                             # OrchestrationTickerChunkService
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
| `api.py` | Main entry point. Provides `SBFoundationAPI` class and `RunCommand` dataclass. Orchestrates domain-specific ingestion flows (Bronze → Silver) for instrument, market, economics, commodities, forex, and crypto domains. |
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
  [Downstream: Gold layer, Feature Engineer, Signals,  backtesting, portfolio optimization, execution — separate packages]
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
    domain=MARKET_DOMAIN,           # Choose domain: MARKET, INSTRUMENT, COMPANY, etc.
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

Plain-text logs are written to `$DATA_ROOT_FOLDER/logs/`. Each log line carries the `run_id` for correlation.

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

#### 3. economic-indicators (27 indicators)
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

**Period Variants** (each statement has three discriminators):
- Base (discriminator: '') - Most recent data without period specification
- Annual (discriminator: FY) - Fiscal year data
- Quarterly (discriminator: quarter) - Quarterly data

**Scope:** Per-ticker (runs for each symbol in universe)
**Refresh:** Quarterly (min_age_days: 90)
**Silver Tables:** `silver.fmp_income_statement`, `silver.fmp_balance_sheet_statement`, `silver.fmp_cashflow_statement`
**Key Columns:** `ticker`, `date`, `period`
**API Endpoints:**
- `https://financialmodelingprep.com/stable/income-statement?symbol={ticker}&period={FY|quarter}&limit=__limit__`
- `https://financialmodelingprep.com/stable/balance-sheet-statement?symbol={ticker}&period={FY|quarter}&limit=__limit__`
- `https://financialmodelingprep.com/stable/cashflow-statement?symbol={ticker}&period={FY|quarter}&limit=__limit__`

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
| **`sbfoundation/settings.py` uses wildcard import** | Low | `from sbfoundation.settings import *` is used in `api.py` and `sbfoundation/folders.py`. This makes static analysis harder and can cause name collisions if settings grow. |
| **No concurrency / parallelism** | Info | Bronze ingestion is sequential per recipe. Throughput is bounded by `THROTTLE_MAX_CALLS_PER_MINUTE` (50/min for FMP). Large universes (1000+ tickers × 40+ datasets) take significant wall-clock time. |
| **PROD runs on Raspberry Pi** | Info | Low RAM and single-core constraints apply. Chunk size (10 tickers) and recipe limits in `OrchestrationSettings` are the primary throughput controls. |
