


## Data Warehouse Pipeline 

To support reliable analytics and modeling on quarterly financial data, we’ve designed a robust, layered data pipeline based on medallion architecture principles. This pipeline ingests raw API data, validates and enriches it, and ultimately transforms it into star-schema fact and dimension tables within a central data warehouse. The diagram below outlines each major stage of the pipeline, followed by a detailed breakdown of its components and responsibilities.

```mermaid
flowchart TD
    subgraph Acquisition
        A[Raw API Data] --> B[Acquisition Service]
        B --> C[Bronze Layer - Raw Storage]
    end

    subgraph Validation
        C --> D[Validation Service]
        D --> E[Silver Layer - Validated / Typed]
        D -->|Errors| DX[Data Quality Logs]
    end

    subgraph Transformation
        E --> F[Transformation & Enrichment Service]
        F --> G[Gold Layer - Modeled Tables]
        F -->|Audit Metadata| MX[Metadata Registry]
    end

    subgraph Modeling
        G --> H[Dimension Services - Stocks, Sectors, Markets]
        G --> I[Fact Services - Financials]
        H --> J[Dimension Tables]
        I --> K[Fact Tables]
    end

    J --> L[Data Warehouse - Star Schema]
    K --> L

    subgraph Downstream
        L --> M[Analytics & Dashboards]
        L --> N[ML Feature Store]
        L --> O[Export to External Consumers]
    end
```

 **Acquisition**

* **Raw API Data**: Quarterly financial data is fetched directly from a third-party source (e.g., EDGAR, Alpha Vantage APIs).
* **Acquisition Service**: Handles pulling the data, logging source metadata (timestamp, ticker, etc.).
* **Bronze Layer – Raw Storage**: Stores unmodified, original data for traceability and reprocessing. Bronze retains raw API responses as JSON, while Silver/Gold use Parquet.


* **Sources**: Alpha Vantage APIs
* **Tools**: Python extract scripts in the acquisition folder
* **Storage**: Raw data stored as JSON
* **Orchestration**: Prefect DAGs 
* **Folder**: `acquisition`

| Table                         | Partition                        |
| ----------------------------- | -------------------------------- |
| BALANCE_SHEET                 | symbol                           |
| CASH_FLOW                     | symbol                           |
| DIVIDENDS                     | symbol                           |
| EARNINGS                      | symbol                           |
| INCOME_STATEMENT              | symbol                           |
| INSIDER_TRANSACTIONS          | symbol                           |
| OVERVIEW                      | -                                |
| TIME_SERIES_MONTHLY_ADJUSTED  | symbol                           |

**Validation**

* **Validation Service**: Applies schema checks, data typing, null handling, and basic cleanup.
* **Silver Layer – Validated/Typed**: Cleaned and standardized data; safe for transformation and modeling.
* **Data Quality Logs**: Captures issues like missing fields, type mismatches, or late/malformed data for auditing and alerting.

* **Sources**: Alpha Vantage APIs
* **Tools**: Python extract scripts in the acquisition folder and saves to the validation folder
* **Cleaning**: fill or impute missing values, dedupe records, standardize formats
* **Storage**: Formatted data (date/time, float, int, str) stored in parquet format
* **Orchestration**: Prefect DAGs 
* **Folder**: `validated`

| Table                         | Partition                        |
| ----------------------------- | -------------------------------- |
| BALANCE_SHEET                 | symbol                           |
| CASH_FLOW                     | symbol                           |
| DIVIDENDS                     | symbol                           |
| EARNINGS                      | symbol                           |
| INCOME_STATEMENT              | symbol                           |
| INSIDER_TRANSACTIONS          | symbol                           |
| OVERVIEW                      | -                                |
| TIME_SERIES_MONTHLY_ADJUSTED  | symbol                           |
 

**Transformation**

* **Transformation & Enrichment Service**: Derives new metrics (e.g., ROE, EBITDA margin), performs currency normalization, standardizes structures.
* **Gold Layer – Modeled Tables**: Fully enriched, analysis-ready data structured in a consistent format across companies.
* **Metadata Registry**: Logs lineage, transformations applied, column-level metadata, and audit trail for governance.

 **Modeling**

* **Dimension Services**: Creates entity reference tables—stocks, sectors, markets—using SCD logic where necessary.
* **Fact Services**: Builds tables containing numeric, time-series data like revenue, profit, cash flow, etc.
* **Dimension Tables**: Entities and descriptors (e.g., company names, sectors, geography).
* **Fact Tables**: Measures tied to dimensions and time (e.g., Q2 2025 revenue for MSFT).

* **Enrichment**: joins, aggregations, type conversions using python in the transformation folder
* **Feature engineering**: date parts, rolling statistics, column level calculators
* **Orchestration**: Prefect DAGs 
* **Ratios**:  
* **AlphaPulse**: profitability (ROA), growth, leverage, valuation (earnings yield), momentum, stability and a weighted composite
* **Dividend Safety**: payout ratios (earnings & FCF), leverage, coverage metrics, volatility, streaks, drawdowns and a composite safety score
* **Folder**: `transformed`

| Table                         | Partition                        |
| ----------------------------- | -------------------------------- |
| DIM_STOCK                     | -                                |
| FACT_QTR_FINANCIALS           | symbol                           |



* **Dimension = the “who/what/where/when” context.** Descriptive attributes (names, categories, hierarchies).
* **Fact = the “how many/how much” measurements.** Numeric metrics tied to a specific grain (event) and foreign keys to dimensions.

|             | **Dimension**                               | **Fact**                                                |
| ----------- | ------------------------------------------- | ------------------------------------------------------- |
| Role        | Describes context (nouns)                   | Stores measures/events (verbs, numbers)                 |
| Examples    | `dim_customer`, `dim_date`, `dim_security`  | `fact_sales`, `fact_trades`, `fact_price_daily`         |
| Columns     | Text/labels, hierarchies, surrogate keys    | Foreign keys to dims + numeric measures                 |
| Size/Change | Smaller, slowly changing (SCD1/2/etc.)      | Very large, mostly insert-only/appended                 |
| Grain       | One row per **entity** at its natural grain | One row per **event/observation** at the declared grain |
| Additivity  | Not applicable                              | Measures are additive, semi-additive, or non-additive   |

**How to tell which is which**

* If you’re asking **“by what/along what axis do I slice?”** → It’s a **dimension**.
* If you’re asking **“how many/how much did we…”** → It’s a **fact**.
* If it mostly holds **numbers you aggregate** (sum, avg, min/max) → **fact**.
* If it mostly holds **descriptions** (name, type, sector, category) → **dimension**.

**Example (stocks domain)**

* **Dimension:** `dim_stock` (ticker, company name, sector, currency, IPO date, …)
* **Fact:** `fact_price_daily` (ticker\_key, date\_key, open, high, low, close, volume)

**Nuances**

* **Factless fact tables:** no measures, just the occurrence of an event (e.g., a student attended a class).
* **Bridge tables:** handle many‑to‑many between facts and dimensions (e.g., trade ↔ multiple brokers).
* **Degenerate dimensions:** IDs sitting in the fact table itself (e.g., transaction\_id as a textual attribute).


**Data Warehouse – Star Schema**

* Combines fact and dimension tables into a star schema optimized for analytics, slicing/dicing, and time-series comparison.

**Downstream Consumption**

* **Analytics & Dashboards**: Power BI, Tableau, or custom Streamlit apps use this data for executive dashboards and KPI tracking.
* **ML Feature Store**: Provides cleaned, ready-to-use features to machine learning models (e.g., for scoring or prediction).
* **Export to External Consumers**: Enables pushing data to clients, partners, or reporting systems (e.g., CSVs, APIs, S3, etc.).


## Data Warehouse Build Checklist

Here’s a checklist you can use to audit and improve your process:

### Ingestion & Raw Storage

* [x] Ingests all raw API data in original schema
* [x] Stores raw data in append-only, immutable format
* [x] Captures source metadata (e.g. filing date, ticker, quarter)

### Validation & Data Quality

* [x] Performs schema validation (using Pandera, Pydantic, or similar)
* [x] Logs validation errors separately
* [x] Tracks % completeness, timeliness, and type coercions
* [x] Version-controls schema (especially for API changes)

### Silver Layer (Cleaned Data)

* [x] Applies typing, null handling, standard formatting
* [x] Retains data in source-native structure but cleaned
* [x] Adds metadata (timestamps, validation results, source ID)

### Transformation & Enrichment

* [x] Derives key ratios and standardized metrics (e.g., ROE, EPS)
* [x] Handles currency normalization (if needed)
* [x] Adds industry/sector tagging from a reference source
* [x] Tracks data lineage (what inputs produced which outputs)

### Gold Layer & Dimensional Modeling

* [x] Fact tables contain fully normalized, comparable metrics
* [x] Dimension tables track stock metadata with SCD2 history
* [x] All tables have surrogate keys and audit timestamps
* [x] Fact/dimension relationships conform to star schema

### Pipeline Architecture

* [x] All services are modular and composable
* [x] Pipeline orchestrated with DAG tool (Airflow, Dagster, Prefect)
* [x] Logs and metrics for each stage are centrally collected
* [x] Retry logic and alerting in place for failed steps

### Downstream Readiness

* [x] Tables are partitioned and indexed for fast queries
* [x] Supports both batch and real-time consumption
* [x] Has snapshots or slowly changing dimensions to support time travel
* [x] Feature store integration (optional but powerful for ML use)


Perfect — thanks for sharing the full markdown plan. You’ve already got a beautifully thought-out architecture. Now let’s take it further with a **detailed workflow per tier**, complete with:

* Python class structure
* Folder layout
* Suggested validation/enrichment logic
* How to expose and monitor status via a UI
* How to keep it testable and extendable

---

## 🧠 REFINED STRATEGY: TIERED DATAFLOW (Bronze → Silver → Gold)

Let’s break this down tier by tier with working patterns, reusable classes, and best-practice folder structure.

---

## 🥉 BRONZE TIER — Acquisition Service (`acquisition/`)

**Purpose:** Ingest raw data from APIs with full fidelity and metadata. Immutable, append-only.

### ✅ Tasks:

* Read `tickers.csv`
* Pull data from Alpha Vantage and/or EDGAR
 * Store raw response with metadata as JSON
* Log outcome (`success/failure`, `response time`, etc.)

### 🔧 Suggested Python Classes:

```python
# acquisition/services/fetcher.py
class AlphaVantageFetcher:
    def __init__(self, api_key: str):
        ...

    def fetch(self, ticker: str, endpoint: str) -> dict:
        ...

# acquisition/services/ingestor.py
class BronzeIngestor:
    def __init__(self, output_dir: str):
        ...

    def write_json(self, ticker: str, data: dict, table: str):
        ...

    def log_status(self, ticker: str, table: str, status: str, error: str = None):
        ...
```

### 📂 Folder Layout:

```
acquisition/
├── services/
│   ├── fetcher.py
│   └── ingestor.py
├── tickers.csv
└── bronze/
    └── earnings/
        └── 2025-08-03/
            └── AAPL.json
```

---

## 🥈 SILVER TIER — Validation & Typing (`validated/`)

**Purpose:** Clean, validate, and standardize bronze data. Still close to source format.

### ✅ Tasks:

* Validate schema with **Pandera or Pydantic**
* Apply formatting: dates, numerics, symbols
* Write data partitioned by `symbol`
* Log validation status and issues

### 🔧 Suggested Python Classes:

```python
# validated/services/validator.py
class FinancialDataValidator:
    def validate(self, df: pd.DataFrame, table: str) -> pd.DataFrame:
        ...

    def log_issues(self, df: pd.DataFrame, ticker: str, table: str):
        ...
```

Use **Pandera schemas** for runtime data contracts:

```python
from pandera import Column, DataFrameSchema, Check
schema = DataFrameSchema({
    "symbol": Column(str),
    "fiscalDateEnding": Column("datetime64[ns]"),
    "reportedEPS": Column(float, Check.ge(0.0)),
})
```

### 📂 Folder Layout:

```
validated/
├── services/
│   └── validator.py
└── silver/
    └── income_statement/
        └── symbol=AAPL/
            └── part-000.parquet
```

---

## 🥇 GOLD TIER — Transformation & Modeling (`transformed/`)

**Purpose:** Business-ready, consistent dimensional data for analytics and modeling.

### ✅ Tasks:

* Join across sources (dividends + earnings + balance sheet)
* Derive metrics (ROE, payout ratio, etc.)
* Build star schema (dim\_stock, fact\_financials)
* Track transformations via metadata registry

### 🔧 Suggested Python Classes:

```python
# transformed/services/curator.py
class FinancialCurator:
    def merge_sources(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        ...

    def compute_ratios(self, df: pd.DataFrame) -> pd.DataFrame:
        ...

    def write_fact_dim_tables(self, df: pd.DataFrame):
        ...
```

You can extract calculated ratios into modular feature calculators:

```python
class DividendSafetyScorer:
    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        ...
```

### 📂 Folder Layout:

```
transformed/
├── services/
│   ├── curator.py
│   └── scorers/
│       └── dividend_safety.py
└── gold/
    ├── dim_stock/
    └── fact_qtr_financials/
```

---

## ⚙️ DAG: Prefect-Driven Orchestration

### Example Flow:

```python
from prefect import flow, task

@task
def acquire():
    # Use BronzeIngestor here
    ...

@task
def validate():
    # Use FinancialDataValidator here
    ...

@task
def transform():
    # Use FinancialCurator here
    ...

@flow
def nightly_pipeline():
    acquire()
    validate()
    transform()
```

Add retries, alerting, and failure hooks with Prefect decorators.

---

## 📊 STATUS UI (Streamlit or FastAPI)

### Features:

* Status dashboard per symbol, per tier
* Filter by date, status, table
* Show last 7 days of pipeline activity
* Summarize failed tickers and why

### Suggested Schema (Parquet or SQLite):

```python
status_table = pd.DataFrame([
    {"ticker": "AAPL", "layer": "bronze", "status": "success", "timestamp": "..."},
    {"ticker": "AAPL", "layer": "silver", "status": "fail", "error": "Missing field"},
])
```

📂 Place this in `/status/status.parquet`

---

## 🧪 Testing & Modularity

Use `pytest` with fixtures for:

* Bronze → Silver test cases (e.g., bad/missing schema)
* Ratio calculators (e.g., test payout ratio edge cases)
* Transformation audits (mock multi-source joins)

---

## 🧱 Suggested Root Project Layout

```
strawberry/
├── acquisition/
├── validated/
├── transformed/
├── status/
├── config/
│   ├── tickers.csv
│   └── settings.yaml
├── dags/
│   └── nightly_pipeline.py
├── ui/
│   └── streamlit_app.py
└── tests/
```

---

## ✅ Final Recommendations

| Area               | Recommendation                                   |
| ------------------ | ------------------------------------------------ |
| **Validation**     | Use Pandera schemas in silver tier               |
| **Lineage**        | Add hash-based column provenance + logs          |
| **Metadata**       | Track source → table → metric lineage            |
| **Enrichment**     | Isolate ratio calculators in independent modules |
| **Retry/Backfill** | Enable reprocessing by symbol/date               |
| **Partitioning**   | Use `symbol` and/or `quarter` in all tables      |
| **Downstream**     | Point Streamlit to gold layer + status table     |

---

If you want, I can spin this into a starter repo layout or give you some boilerplate for `BronzeIngestor`, `FinancialValidator`, or `FinancialCurator`. Just say the word.
