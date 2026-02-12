# Technology Stack Document

## 1. Overview

**Project name:** `strawberry`
**Purpose:** Data acquisition, analytics, and UI for an AI trading platform.

**Primary domains / packages**

* `company` — company metadata, identifiers, symbol resolution
* `economics` — macroeconomic indicators, rates, inflation, growth data
* `fundamentals` — financial statements, earnings, balance sheets
* `technicals` — indicators, signals, rolling statistics
* `orchestration` — run coordination and scheduling
* `ui` — Streamlit dashboards and interactive controls
* `shared` — DTOs, configuration, logging, utilities

**Architecture alignment:** Medallion / lakehouse style (Bronze → Silver → Gold) plus Consumers (backtesting, execution, monitoring).

---

## 2. Language & Runtime

* **Language:** Python
* **Supported versions:** `>=3.11,<3.14`
* **Packaging:** Poetry (`poetry-core` build backend)
* **Local environment tooling:** `uv` (fast installer / runner)

**Typing standard**

* Static typing via **mypy**
* Preferred typing style: built-in generics (`list[...]`, `dict[...]`)

---

## 3. Core Data & Compute Libraries

* **pandas** — primary data manipulation and dataset assembly
* **numpy** — numeric and vectorized calculations
* **requests** — HTTP client plumbing where SDKs are unavailable

**File formats**

* **Parquet** — primary persisted analytics format (Silver / Gold)
* **pyarrow** — Parquet engine
* **JSON / CSV** — raw ingest formats (Bronze), depending on source payload

---

## 4. Data Providers & External Integrations

* **Alpha Vantage** (`alpha-vantage`) — market and fundamentals data
* **Financial Modeling Prep (FMP)** (`fmpsdk`) — fundamentals, macro, market data
* **Alpaca** — research, paper trading, simulation
* **Charles Schwab** — live trade execution

**Provider usage intent**

* Market and fundamentals acquisition: FMP + Alpha Vantage
* Research, training, simulation: Alpaca
* Live execution: Schwab

**Broker SDK recommendations**

* Alpaca: `alpaca-py`
* Schwab: custom adapter over Schwab API (official SDK support limited)

---

## 5. Storage & Data Layering

**Medallion layers**

* **Bronze:** raw payloads and ingestion metadata (append-only)
* **Silver:** validated, typed, conformed datasets (dedupe planned)
* **Gold:** metrics, features, signals, model outputs (versioned, consumer-ready)

**Storage environment**

* Local filesystem for both DEV and PROD
* PROD runs on Raspberry Pi Linux

**Repository structure (current runtime)**

Bronze JSON files:

```
<ROOT>/bronze/<domain>/<source>/<dataset>/<ticker_or_none>/<injestion_date>-<uuid>.json
```

Silver Parquet tables:

```
<ROOT>/silver/<dataset>.parquet
```

Gold Parquet tables:

```
<ROOT>/gold/dims/<dim_table>.parquet
<ROOT>/gold/facts/<fact_table>.parquet
```

**Required ingestion metadata (serialized)**

Stored in Bronze `RunRequest` / `RunResult` JSON:

* `run_id`
* `injestion_date`
* `domain` / `source` / `dataset` (nested in recipe)
* `data_source_path` / `url` / `query_vars`
* response envelope (`status_code`, `reason`, `headers`, `elapsed_microseconds`)

---

## 6. UI & Visualization

* **Streamlit** — primary UI framework
* **streamlit-echarts** — interactive charting
* **Altair** — declarative analytics visualization

**Hosting**

* DEV: local machine
* PROD: Raspberry Pi (local network access only)
* No authentication required

**Operational controls**

* Manual override and pause/resume trading implemented as UI controls
* Control state persisted in a control table or file

---

## 7. Development Standards & Quality Gates

* **Formatting:** Black (line length 150)
* **Imports:** isort (Black profile)
* **Linting:** flake8
* **Testing:** pytest
* **Coverage:** coverage + pytest-cov

**Coverage scope**

* `company`
* `economics`
* `fundamentals`
* `technicals`
* `orchestration`
* `shared`

**CI quality gates**

* `pytest --cov`
* `black --check`
* `isort --check-only`
* `flake8`
* `mypy`

---

## 8. Observability & Logging

* **Logging format:** plain text
* **Library:** Python standard `logging`
* **Correlation:** `run_id` propagated through logs and outputs
* **Metrics:** persisted as Parquet datasets (Gold / monitoring domain)

---

## 9. Orchestration & Scheduling

* **Scheduler:** Prefect (OSS)
* **Execution model:** nightly batch jobs
* **Triggers:**

  * Scheduled Prefect deployments
  * Manual Streamlit-triggered runs for ad-hoc execution
* **Retry policy:** 3 retries with exponential backoff
* **Rate limiting:** enforced per data provider to respect API quotas

**Containerization**

* Docker used for PROD deployment
* **Orchestration:** Docker Compose (preferred over Kubernetes)

---

## 10. Security & Secrets

* **Secrets management:** `.env` files for local development, OS environment variables for runtime
* **Configuration:** centralized configuration loader with environment overrides
* **Key handling:** no API keys committed to source control

---

## 11. Canonical Symbol Model

* Primary key: internal `instrument_id`
* Attributes:

  * `symbol`
  * `exchange`
  * `currency`
  * `security_type`
* ADRs and multi-listed securities mapped to a single `instrument_id`
* Currency normalization performed in Silver layer

---

## 12. MLOps & Models

* **Training framework:** H2O
* **Model registry:** not used
* **Model storage:** artifacts stored in Gold with metadata
* **Feature store:** not required; Gold serves as the feature store

---

## 13. Alerts & Monitoring

* **Alerting channel:** Slack (webhook-based)
* **Monitoring store:** persisted metrics in Parquet (Gold layer)

---

## Final Note

This document defines **hard constraints and explicit defaults** for the Strawberry platform.
It is intended to eliminate ambiguity, prevent architectural drift, and enable deterministic platform construction across ingestion, analytics, simulation, execution, and monitoring.

With this file in place, ChatGPT can reliably generate implementation-level artifacts without guessing infrastructure, tooling, or design intent.
