import os

DEFAULT_LIMIT: int = 1000


# ---- DOMAINS ---- #
EOD_DOMAIN = "eod"
QUARTER_DOMAIN = "quarter"
ANNUAL_DOMAIN = "annual"
DOMAINS: list = [
    EOD_DOMAIN,
    QUARTER_DOMAIN,
    ANNUAL_DOMAIN,
]

# Domain execution order for orchestration
DOMAIN_EXECUTION_ORDER: tuple[str, ...] = (
    EOD_DOMAIN,
    QUARTER_DOMAIN,
    ANNUAL_DOMAIN,
)

# ---- DATASET NAMES ---- #
# EOD Bulk
EOD_BULK_PRICE_DATASET = "eod-bulk-price"
EOD_COMPANY_PROFILE_BULK_DATASET = "company-profile-bulk"

# Quarter Bulk
INCOME_STATEMENT_BULK_QUARTER_DATASET = "income-statement-bulk-quarter"
BALANCE_SHEET_BULK_QUARTER_DATASET = "balance-sheet-bulk-quarter"
CASHFLOW_BULK_QUARTER_DATASET = "cashflow-bulk-quarter"

# Annual Bulk
INCOME_STATEMENT_BULK_ANNUAL_DATASET = "income-statement-bulk-annual"
BALANCE_SHEET_BULK_ANNUAL_DATASET = "balance-sheet-bulk-annual"
CASHFLOW_BULK_ANNUAL_DATASET = "cashflow-bulk-annual"

# Key Metrics Bulk (FMP pre-computed ratios)
KEY_METRICS_BULK_QUARTER_DATASET = "key-metrics-bulk-quarter"
KEY_METRICS_BULK_ANNUAL_DATASET = "key-metrics-bulk-annual"

# Ratios Bulk (FMP pre-computed profitability/leverage ratios)
RATIOS_BULK_ANNUAL_DATASET = "ratios-bulk-annual"

# Economics / Macro (FRED and FMP global)
FRED_DGS10_DATASET = "fred-dgs10"
FRED_USRECM_DATASET = "fred-usrecm"
MARKET_RISK_PREMIUM_DATASET = "market-risk-premium"

DATASETS: list = [
    EOD_BULK_PRICE_DATASET,
    EOD_COMPANY_PROFILE_BULK_DATASET,
    INCOME_STATEMENT_BULK_QUARTER_DATASET,
    BALANCE_SHEET_BULK_QUARTER_DATASET,
    CASHFLOW_BULK_QUARTER_DATASET,
    KEY_METRICS_BULK_QUARTER_DATASET,
    INCOME_STATEMENT_BULK_ANNUAL_DATASET,
    BALANCE_SHEET_BULK_ANNUAL_DATASET,
    CASHFLOW_BULK_ANNUAL_DATASET,
    KEY_METRICS_BULK_ANNUAL_DATASET,
    RATIOS_BULK_ANNUAL_DATASET,
    FRED_DGS10_DATASET,
    FRED_USRECM_DATASET,
    MARKET_RISK_PREMIUM_DATASET,
]

# ---- CADENCE MODE ---- #
INTERVAL_CADENCE_MODE = "interval"
CALENDAR_CADENCE_MODE = "calendar"
CADENCES = [INTERVAL_CADENCE_MODE, CALENDAR_CADENCE_MODE]

# ---- DAYS OF WEEK ---- #
MONDAY = "mon"
TUESDAY = "tues"
WEDNESDAY = "wed"
THURSDAY = "thurs"
FRIDAY = "fri"
SATURDAY = "sat"
SUNDAY = "sun"
DAYS_OF_WEEK = [
    MONDAY,
    TUESDAY,
    WEDNESDAY,
    THURSDAY,
    FRIDAY,
    SATURDAY,
    SUNDAY,
]
DAYS_OF_WEEK_BY_INDEX = {
    0: MONDAY,
    1: TUESDAY,
    2: WEDNESDAY,
    3: THURSDAY,
    4: FRIDAY,
    5: SATURDAY,
    6: SUNDAY,
}

# ---- QUERY VAR PLACEHOLDERS ----#
TICKER_PLACEHOLDER = "__ticker__"
FROM_DATE_PLACEHOLDER = "__from__"
TO_DATE_PLACEHOLDER = "__to__"
FROM_ONE_MONTH_AGO_PLACEHOLDER = "__from_one_month_ago__"
DATE_PLACEHOLDER = "__date__"
LIMIT_PLACEHOLDER = "__limit__"
PERIOD_PLACEHOLDER = "__period__"

# --- reporting periods ---
PERIOD_ANNUAL = "annual"

# ---- DATA SOURCES ----#
FMP_DATA_SOURCE = "fmp"
AV_DATA_SOURCE = "alpha_vantage"
ALPACA_DATA_SOURCE = "alpaca"
SCHWAB_DATA_SOURCE = "schwab"
BIS_DATA_SOURCE = "bis"
FRED_DATA_SOURCE = "fred"
DATA_SOURCES: list = [FMP_DATA_SOURCE, AV_DATA_SOURCE, ALPACA_DATA_SOURCE, SCHWAB_DATA_SOURCE, BIS_DATA_SOURCE, FRED_DATA_SOURCE]

# ---- DATA SOURCE CONFIGURATION (used to configure settings for a given data source) ----#
RETRY_MAX_ATTEMPTS = "retry_max_attemps"
RETRY_BASE_DELAY = "retry_base_delay"
THROTTLE_MAX_CALLS_PER_MINUTE = "throttle_max_calls"
API_KEY = "API_KEY"  # this defines the label for the actual key in the .env file
API_KEY_QUERY_PARAM = "api_key_query_param"  # the query-parameter name used to pass the API key (default: "apikey")
BASE_URL = "base_url"
FMP_BASE_URL_STABLE: str = "https://financialmodelingprep.com/stable/"
FRED_BASE_URL: str = "https://api.stlouisfed.org/fred/"
DATA_SOURCES_CONFIG = {
    FMP_DATA_SOURCE: {
        RETRY_MAX_ATTEMPTS: 3,
        RETRY_BASE_DELAY: 0.5,
        THROTTLE_MAX_CALLS_PER_MINUTE: 3000,
        API_KEY: "FMP_API_KEY",
        BASE_URL: FMP_BASE_URL_STABLE,
    },
    FRED_DATA_SOURCE: {
        RETRY_MAX_ATTEMPTS: 3,
        RETRY_BASE_DELAY: 0.5,
        THROTTLE_MAX_CALLS_PER_MINUTE: 120,
        API_KEY: "FRED_API_KEY",
        BASE_URL: FRED_BASE_URL,
        API_KEY_QUERY_PARAM: "api_key",  # FRED uses "api_key", not "apikey"
    },
}

# ---- EXECUTION PHASES ---- #
EXECUTION_PHASE_INSTRUMENT_DISCOVERY = "instrument_discovery"
EXECUTION_PHASE_DATA_ACQUISITION = "data_acquisition"
EXECUTION_PHASES = [EXECUTION_PHASE_INSTRUMENT_DISCOVERY, EXECUTION_PHASE_DATA_ACQUISITION]

# --- DATA FOLDERS ---
DATA_ROOT_FOLDER = os.environ.get("DATA_ROOT_FOLDER", "c:/sb/SBFoundation/data")
REPO_ROOT_FOLDER = os.environ.get("REPO_ROOT_FOLDER", "c:/sb/SBFoundation")
BRONZE_FOLDER = "bronze"
DUCKDB_FOLDER = "duckdb"
DUCKDB_FILENAME = "SBFoundation.duckdb"
MIGRATIONS_FOLDER = "db/migrations"
LOG_FOLDER = "logs"
DATASET_KEYMAP_FOLDER = "config"
DATASET_KEYMAP_FILENAME = os.environ.get("DATASET_KEYMAP_FILENAME", "dataset_keymap.yaml")

# --- FMP PRICING TIERS ---
FMP_BASIC_PLAN = "basic"
FMP_STARTER_PLAN = "starter"
FMP_PREMIUM_PLAN = "premium"
FMP_ULTIMATE_PLAN = "ultimate"
FMP_PLANS = [FMP_BASIC_PLAN, FMP_STARTER_PLAN, FMP_PREMIUM_PLAN, FMP_ULTIMATE_PLAN]

FROM_DATE = "1980-01-01"


# --- HTTP calls, Retry and Throttle settings ---
RETRY_MAX_ATTEMPS = 3
RETRY_BASE_DELAY = 0.5
THROTTLE_PERIOD_SECONDS = 60
THROTTLE_MAX_CALLS = 2000
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 30
