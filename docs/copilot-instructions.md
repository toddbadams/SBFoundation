# Copilot Instructions for AI Agents

## Project Overview
- **Purpose:** Model, select, and manage a 15-stock dividend growth portfolio for long-term compounding, using historical data and predictive analytics.
- **Main Components:**
  - `src/strawberry/services/`: Data acquisition, orchestration, and business logic (see `orchestration.py` for rate-limited, multi-source ingestion).
  - `src/strawberry/repository/`: Data access, Parquet storage, and API integrations.
  - `src/strawberry/ui/`: Streamlit-based dashboards and visualizations.
  - `config/`: JSON configs for acquisition, scoring, and model parameters.
  - `data/`: Input and validated data, organized by acquisition and dimensions.

## Architecture & Data Flow
- **Ingestion:**
  - Orchestrator (`orchestration.py`) rotates through tickers and services, respecting API rate limits and acquisition frequency.
  - Data is fetched via service clients (e.g., Alpha Vantage, Twelve Data), normalized, and persisted to a "bronze" Parquet repository.
  - Nulls in cashflow tables are sanitized to zero before storage.
- **Config Pattern:**
  - Use `ConfigLoader` and JSON files in `config/` for service, table, and model settings.
  - Logger setup via `LoggerFactory`.
- **Testing:**
  - Pytest is used (`pytest.ini`), with tests in `src/strawberry/tests/`.
  - Example orchestrator tests are in `orchestration.py` (copy to tests/ if needed).

## Developer Workflows
- **Build/Run:**
  - Use Poetry (`pyproject.toml`) for dependency management: `poetry install`, `poetry run <script>`.
  - Main scripts:
    - `acquisition`: `poetry run acquisition` (runs acquisition logic)
    - `ui`: `poetry run ui` (launches Streamlit dashboard)
    - `test`: `poetry run test` (runs tests with coverage)
- **Docker:**
  - `Dockerfile` installs dependencies and runs `loader.py` by default.
- **Testing:**
  - Run `pytest` or `poetry run test` for coverage and verbose output.
- **Linting/Formatting:**
  - Use `black`, `flake8`, `isort`, and `mypy` (see `[tool.poetry.group.dev.dependencies]`).

## Project-Specific Patterns & Conventions
- **Service Rotation:**
  - All data acquisition respects per-minute and per-day API limits (see `ServiceSpec` and `RateLimit` in `orchestration.py`).
- **Bronze Repository:**
  - JSON storage is abstracted; use `append` or `write` methods, partitioned by ticker symbol. Bronze retains raw API responses as JSON, while Silver/Gold use Parquet.
- **Cashflow Handling:**
  - Nulls in cashflow columns are always converted to zero before writing.
- **Config-Driven:**
  - All service and model parameters are loaded from JSON in `config/`.
- **Testing Patterns:**
  - Use monkeypatching for repo/service doubles in tests.

## External Integrations
- **APIs:** Alpha Vantage, Twelve Data, Finnhub, OpenAI (for moat analysis).
- **Visualization:** Streamlit, Altair.
- **Storage:** Parquet via PyArrow.

## Examples
- See `orchestration.py` for orchestrator logic and test patterns.
- See `pyproject.toml` for scripts and dev tool setup.
- See `config/` for service and scoring model configuration.

---

**If any section is unclear or missing key patterns, please provide feedback or specify which workflows/components need more detail.**
