import os

from data_layer.dtos.dto_registry import DTO_REGISTRY

DEFAULT_LINE_PARAMETER = "line"
DEFAULT_LIMIT: int = 5
DEFAULT_PERIOD: str = "quarter"


# ---- TRADING STRATEGY SETTINGS (docs/AI_context/trading_strategies.md) ---- #
STRATEGY_ASSET_CLASSES = ["equities", "etfs", "bonds", "options"]
STRATEGY_PRIMARY_GEOGRAPHY = "united_states"
STRATEGY_MULTI_GEOGRAPHY_SUPPORTED = True
STRATEGY_UNIVERSE_SHARED = True

CORE_LAYER = "core"
SATELLITE_LAYER = "satellite"
SWING_LAYER = "swing"
STRATEGY_LAYERS = [CORE_LAYER, SATELLITE_LAYER, SWING_LAYER]
LAYER_HORIZONS = {
    CORE_LAYER: "years",
    SATELLITE_LAYER: "months",
    SWING_LAYER: "days-weeks",
}

LAYER_TARGET_ALLOCATIONS = {
    CORE_LAYER: 0.60,
    SATELLITE_LAYER: 0.30,
    SWING_LAYER: 0.10,
}
LAYER_MIN_FLOORS = {
    CORE_LAYER: 0.35,
    SATELLITE_LAYER: 0.05,
    SWING_LAYER: 0.0,
}
LAYER_REBALANCE_CADENCE = {
    CORE_LAYER: "quarterly",
    SATELLITE_LAYER: "weekly",
    SWING_LAYER: "daily",
}

REGIME_HEDGE = "hedge"
REGIME_SPECULATIVE = "speculative"
REGIME_PONZI = "ponzi"
REGIME_MINSKY_MOMENT = "minsky_moment"
MINSKY_REGIMES = [REGIME_HEDGE, REGIME_SPECULATIVE, REGIME_PONZI, REGIME_MINSKY_MOMENT]
REGIME_CONFIRMATION_WINDOW_DEFAULT = "multi-week"
REGIME_PROBABILITY_EVALUATION_FREQUENCY = "daily"
REGIME_OUTPUT_IS_PROBABILISTIC = True


REGIME_ALLOCATION_POLICY = {
    REGIME_HEDGE: {CORE_LAYER: "overweight", SATELLITE_LAYER: "enabled", SWING_LAYER: "enabled"},
    REGIME_SPECULATIVE: {CORE_LAYER: "neutral", SATELLITE_LAYER: "capped", SWING_LAYER: "reduced"},
    REGIME_PONZI: {CORE_LAYER: "defensive", SATELLITE_LAYER: "min_floor", SWING_LAYER: "optional"},
    REGIME_MINSKY_MOMENT: {CORE_LAYER: "min_floor", SATELLITE_LAYER: "min_floor", SWING_LAYER: "disabled"},
}

SCREENER_QUANT_VALUE = "quant_value"
SCREENERS = [SCREENER_QUANT_VALUE]
SCREENER_LAYER_SUPPORT = {
    SCREENER_QUANT_VALUE: [CORE_LAYER, SATELLITE_LAYER],
}

SELECTION_SHAPING_STEPS = [
    "fitness_scoring",
    "regime_adjustment",
    "correlation_pruning",
    "volatility_normalization",
]
SELECTION_CANDIDATE_SET_SIZE_RANGE = (20, 60)

STRATEGY_TYPES = [
    "trend_following_etf",
    "factor_value_equity",
    "quality_dividend",
    "mean_reversion_swing",
    "momentum_breakout_swing",
    "volatility_targeting",
    "crash_hedge_overlay",
]

MAX_SINGLE_NAME_BY_LAYER = {
    CORE_LAYER: 0.05,
    SATELLITE_LAYER: 0.07,
    SWING_LAYER: 0.03,
}
MAX_POSITIONS_BY_LAYER = {
    CORE_LAYER: (20, 40),
    SATELLITE_LAYER: (10, 25),
    SWING_LAYER: (5, 15),
}
PORTFOLIO_MAX_SECTOR_EXPOSURE = 0.25
PORTFOLIO_MAX_GROSS_EXPOSURE = 1.10

EXECUTION_END_OF_DAY_ONLY = True
EXECUTION_ALLOW_INTRADAY = False
EXECUTION_SLIPPAGE_MODELED_EXTERNALLY = True
INDUSTRY_VALUES: list = [
    "Entertainment",
    "Oil & Gas Midstream",
    "Semiconductors",
    "Specialty Industrial Machinery",
    "Banks Diversified",
    "Consumer Electronics",
    "Software Infrastructure",
    "Broadcasting",
    "Computer Hardware",
    "Building Materials",
    "Resorts & Casinos",
    "Auto Manufacturers",
    "Internet Content & Information",
    "Insurance Diversified",
    "Telecom Services",
    "Metals & Mining",
    "Capital Markets",
    "Steel",
    "Footwear & Accessories",
    "Household & Personal Products",
    "Other Industrial Metals & Mining",
    "Oil & Gas E&P",
    "Banks Regional",
    "Drug Manufacturers General",
    "Internet Retail",
    "Communication Equipment",
    "Semiconductor Equipment & Materials",
    "Oil & Gas Services",
    "Chemicals",
    "Electronic Gaming & Multimedia",
    "Oil & Gas Integrated",
    "Credit Services",
    "Online Media",
    "Business Services",
    "Biotechnology",
    "Grocery Stores",
    "Oil & Gas Equipment & Services",
    "REITs",
    "Copper",
    "Software Application",
    "Home Improvement Retail",
    "Pharmaceutical Retailers",
    "Communication Services",
    "Oil & Gas Drilling",
    "Electronic Components",
    "Packaged Foods",
    "Information Technology Services",
    "Leisure",
    "Specialty Retail",
    "Oil & Gas Refining & Marketing",
    "Tobacco",
    "Financial Data & Stock Exchanges",
    "Insurance Specialty",
    "Beverages Non-Alcoholic",
    "Asset Management",
    "REIT Diversified",
    "Residential Construction",
    "Travel & Leisure",
    "Gold",
    "Discount Stores",
    "Confectioners",
    "Medical Devices",
    "Banks",
    "Independent Oil & Gas",
    "Airlines",
    "Travel Services",
    "Aerospace & Defense",
    "Retail Apparel & Specialty",
    "Diagnostics & Research",
    "Trucking",
    "Insurance Property & Casualty",
    "Health Care Plans",
    "Consulting Services",
    "Aluminum",
    "Beverages Brewers",
    "REIT Residential",
    "Education & Training Services",
    "Apparel Retail",
    "Railroads",
    "Apparel Manufacturing",
    "Staffing & Employment Services",
    "Utilities Diversified",
    "Agricultural Inputs",
    "Restaurants",
    "Drug Manufacturers General Specialty & Generic",
    "Financial Conglomerates",
    "Personal Services",
    "Thermal Coal",
    "REIT Office",
    "Advertising Agencies",
    "Farm & Heavy Construction Machinery",
    "Consumer Packaged Goods",
    "Publishing",
    "Specialty Chemicals",
    "Engineering & Construction",
    "Utilities Independent Power Producers",
    "Utilities Regulated Electric",
    "Medical Instruments & Supplies",
    "Building Products & Equipment",
    "Packaging & Containers",
    "REIT Mortgage",
    "Department Stores",
    "Insurance Life",
    "Luxury Goods",
    "Auto Parts",
    "Autos",
    "REIT Specialty",
    "Integrated Freight & Logistics",
    "Security & Protection Services",
    "Utilities Regulated Gas",
    "Airports & Air Services",
    "Farm Products",
    "REIT Healthcare Facilities",
    "REIT Industrial",
    "Metal Fabrication",
    "Scientific & Technical Instruments",
    "Solar",
    "REIT Hotel & Motel",
    "Medical Distribution",
    "Medical Care Facilities",
    "Agriculture",
    "Food Distribution",
    "Health Information Services",
    "Industrial Products",
    "REIT Retail",
    "Conglomerates",
    "Health Care Providers",
    "Waste Management",
    "Beverages Wineries & Distilleries",
    "Marine Shipping",
    "Real Estate Services",
    "Tools & Accessories",
    "Auto & Truck Dealerships",
    "Industrial Distribution",
    "Uranium",
    "Lodging",
    "Electrical Equipment & Parts",
    "Gambling",
    "Specialty Business Services",
    "Recreational Vehicles",
    "Furnishings",
    "Fixtures & Appliances",
    "Forest Products",
    "Silver",
    "Business Equipment & Supplies",
    "Medical Instruments & Equipment",
    "Utilities Regulated",
    "Coking Coal",
    "Insurance Brokers",
    "Rental & Leasing Services",
    "Lumber & Wood Production",
    "Medical Diagnostics & Research",
    "Pollution & Treatment Controls",
    "Transportation & Logistics",
    "Other Precious Metals & Mining",
    "Brokers & Exchanges",
    "Beverages Alcoholic",
    "Mortgage Finance",
    "Utilities Regulated Water",
    "Manufacturing Apparel & Furniture",
    "Retail Defensive",
    "Real Estate Development",
    "Paper & Paper Products",
    "Insurance Reinsurance",
    "Homebuilding & Construction",
    "Coal",
    "Electronics & Computer Distribution",
    "Health Care Equipment & Services",
    "Education",
    "Employment Services",
    "Textile Manufacturing",
    "Real Estate Diversified",
    "Consulting & Outsourcing",
    "Utilities Renewable",
    "Tobacco Products",
    "Farm & Construction Machinery",
    "Shell Companies",
    "N/A",
    "Advertising & Marketing Services",
    "Capital Goods",
    "Insurance",
    "Industrial Electrical Equipment",
    "Utilities",
    "Pharmaceuticals",
    "Biotechnology & Life Sciences",
    "Infrastructure Operations",
    "Energy",
    "NULL",
    "Property Management",
    "Auto Dealerships",
    "Apparel Stores",
    "Mortgage Investment",
    "Software & Services",
    "Industrial Metals & Minerals",
    "Media & Entertainment",
    "Diversified Financials",
    "Consumer Services",
    "Commercial  & Professional Services",
    "Electronics Wholesale",
    "Retailing",
    "Automobiles & Components",
    "Materials",
    "Real Estate",
    "Food",
    "Beverage & Tobacco",
    "Closed-End Fund Debt",
    "Transportation",
    "Food & Staples Retailing",
    "Consumer Durables & Apparel",
    "Technology Hardware & Equipment",
    "Telecommunication Services",
    "Semiconductors & Semiconductor Equipment",
]
SECTOR_VALUES: list = [
    "Communication Services",
    "Energy",
    "Technology",
    "Industrials",
    "Financial Services",
    "Basic Materials",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Healthcare",
    "Real Estate",
    "Utilities",
    "Financial",
    "Building",
    "Industrial Goods",
    "Pharmaceuticals",
    "Services",
    "Conglomerates",
    "Media",
    "Banking",
    "Airlines",
    "Retail",
    "Metals & Mining",
    "Textiles",
    "Apparel & Luxury Goods",
    "Chemicals",
    "Biotechnology",
    "Electrical Equipment",
    "Aerospace & Defense",
    "Telecommunication",
    "Machinery",
    "Food Products",
    "Insurance",
    "Logistics & Transportation",
    "Health Care",
    "Beverages",
    "Consumer products",
    "Semiconductors",
    "Automobiles",
    "Trading Companies & Distributors",
    "Commercial Services & Supplies",
    "Construction",
    "Auto Components",
    "Hotels",
    "Restaurants & Leisure",
    "Life Sciences Tools & Services",
    "Communications",
    "Industrial Conglomerates",
    "Professional Services",
    "Road & Rail",
    "Tobacco",
    "Paper & Forest",
    "Packaging",
    "Leisure Products",
    "Transportation Infrastructure",
    "Distributors",
    "Marine",
    "Diversified Consumer Services",
]

# --- reporting periods ---
PERIOD_ANNUAL = "annual"
PERIOD_QUARTER = "quarter"
PERIOD_Q1 = "Q1"
PERIOD_Q2 = "Q2"
PERIOD_Q3 = "Q3"
PERIOD_Q4 = "Q4"
PERIOD_FY = "FY"
PERIOD_VALUES: list = [PERIOD_ANNUAL, PERIOD_QUARTER, PERIOD_Q1, PERIOD_Q2, PERIOD_Q3, PERIOD_Q4, PERIOD_FY]

# --- to be determine ---
TIME_DELTA_VALUES: list = ["1min", "5min", "15min", "30min", "1hour", "4hour"]
TECHNICAL_INDICATORS_TIME_DELTA_VALUES: list = ["1min", "5min", "15min", "30min", "1hour", "4hour", "daily"]
SERIES_TYPE_VALUES: list = ["line"]
STATISTICS_TYPE_VALUES: list = [
    "sma",
    "ema",
    "wma",
    "dema",
    "tema",
    "williams",
    "rsi",
    "adx",
    "standardDeviation",
]
ECONOMIC_INDICATOR_VALUES: list = [
    "GDP",
    "realGDP",
    "nominalPotentialGDP",
    "realGDPPerCapita",
    "federalFunds",
    "CPI",
    "inflationRate",
    "inflation",
    "retailSales",
    "consumerSentiment",
    "durableGoods",
    "unemploymentRate",
    "totalNonfarmPayroll",
    "initialClaims",
    "industrialProductionTotalIndex",
    "newPrivatelyOwnedHousingUnitsStartedTotalUnits",
    "totalVehicleSales",
    "retailMoneyFunds",
    "smoothedUSRecessionProbabilities",
    "3MonthOr90DayRatesAndYieldsCertificatesOfDeposit",
    "commercialBankInterestRateOnCreditCardPlansAllAccounts",
    "30YearFixedRateMortgageAverage",
    "tradeBalanceGoodsAndServices",
    "15YearFixedRateMortgageAverage",
]
TREASURY_TENORS: list = ["month1", "month2", "month3", "month6", "year1", "year2", "year3", "year5", "year7", "year10", "year20", "year30"]

# ---- DOMAINS ---- #
ECONOMICS_DOMAIN = "economics"
FUNDAMENTALS_DOMAIN = "fundamentals"
TECHNICALS_DOMAIN = "technicals"
COMPANY_DOMAIN = "company"
INSTRUMENT_DOMAIN = "instrument"
DOMAINS: list = [ECONOMICS_DOMAIN, FUNDAMENTALS_DOMAIN, TECHNICALS_DOMAIN, COMPANY_DOMAIN, INSTRUMENT_DOMAIN]

# Domain execution order for orchestration (instrument must run first to populate universe)
DOMAIN_EXECUTION_ORDER: tuple[str, ...] = (
    INSTRUMENT_DOMAIN,
    ECONOMICS_DOMAIN,
    COMPANY_DOMAIN,
    FUNDAMENTALS_DOMAIN,
    TECHNICALS_DOMAIN,
)

# ---- INSTRUMENT TYPES ---- #
INSTRUMENT_TYPE_EQUITY = "equity"
INSTRUMENT_TYPE_ETF = "etf"
INSTRUMENT_TYPE_INDEX = "index"
INSTRUMENT_TYPE_CRYPTO = "crypto"
INSTRUMENT_TYPE_FOREX = "forex"
INSTRUMENT_TYPES = [INSTRUMENT_TYPE_EQUITY, INSTRUMENT_TYPE_ETF, INSTRUMENT_TYPE_INDEX, INSTRUMENT_TYPE_CRYPTO, INSTRUMENT_TYPE_FOREX]

# ---- INSTRUMENT BEHAVIORS ---- #
INSTRUMENT_BEHAVIOR_CREATE = "create"
INSTRUMENT_BEHAVIOR_ENRICH = "enrich"
INSTRUMENT_BEHAVIOR_RELATIONSHIP = "relationship"
INSTRUMENT_BEHAVIORS = [INSTRUMENT_BEHAVIOR_CREATE, INSTRUMENT_BEHAVIOR_ENRICH, INSTRUMENT_BEHAVIOR_RELATIONSHIP]

# ---- EXECUTION PHASES ---- #
EXECUTION_PHASE_INSTRUMENT_DISCOVERY = "instrument_discovery"
EXECUTION_PHASE_DATA_ACQUISITION = "data_acquisition"
EXECUTION_PHASES = [EXECUTION_PHASE_INSTRUMENT_DISCOVERY, EXECUTION_PHASE_DATA_ACQUISITION]

# ---- DATA SOURCES ----#
FMP_DATA_SOURCE = "fmp"
AV_DATA_SOURCE = "alpha_vantage"
ALPACA_DATA_SOURCE = "alpaca"
SCHWAB_DATA_SOURCE = "schwab"
BIS_DATA_SOURCE = "bis"
FRED_DATA_SOURCE = "fred"
REGIME_DATA_SOURCES = [FMP_DATA_SOURCE, BIS_DATA_SOURCE, FRED_DATA_SOURCE]
DATA_SOURCES: list = [FMP_DATA_SOURCE, AV_DATA_SOURCE, ALPACA_DATA_SOURCE, SCHWAB_DATA_SOURCE, BIS_DATA_SOURCE, FRED_DATA_SOURCE]

# ---- DATA SOURCE CONFIGURATION (used to configure settings for a given data source) ----#
RETRY_MAX_ATTEMPTS = "retry_max_attemps"
RETRY_BASE_DELAY = "retry_base_delay"
THROTTLE_MAX_CALLS_PER_MINUTE = "throttle_max_calls"
API_KEY = "API_KEY"  # this defines the label for the actual key in the .env file
BASE_URL = "base_url"
FMP_BASE_URL_STABLE: str = "https://financialmodelingprep.com/stable/"
DATA_SOURCES_CONFIG = {
    FMP_DATA_SOURCE: {
        RETRY_MAX_ATTEMPTS: 3,
        RETRY_BASE_DELAY: 0.5,
        THROTTLE_MAX_CALLS_PER_MINUTE: 50,
        API_KEY: "FMP_API_KEY",
        BASE_URL: FMP_BASE_URL_STABLE,
    }
}

# ---- INSTRUMENT DATASETS ---- #
STOCK_LIST_DATASET = "stock-list"
ETF_LIST_DATASET = "etf-list"
INDEX_LIST_DATASET = "index-list"
CRYPTOCURRENCY_LIST_DATASET = "cryptocurrency-list"
FOREX_LIST_DATASET = "forex-list"
ETF_HOLDINGS_DATASET = "etf-holdings"

# ---- DATASETS (an internal label for a given dataset, which is represented as a table at the silver layer ----#
ECONOMICS_INDICATORS_DATASET = "economic-indicators"
TREASURY_RATES_DATASET = "treasury-rates"
MARKET_RISK_PREMIUM_DATASET = "market-risk-premium"
COMPANY_INFO_DATASET = "company-profile"
COMPANY_NOTES_DATASET = "company-notes"
COMPANY_PEERS_DATASET = "company-peers"
COMPANY_EMPLOYEES_DATASET = "company-employees"
COMPANY_MARKET_CAP_DATASET = "company-market-cap"
COMPANY_SHARES_FLOAT_DATASET = "company-shares-float"
COMPANY_OFFICERS_DATASET = "company-officers"
COMPANY_COMPENSATION_DATASET = "company-compensation"
COMPANY_DELISTED_DATASET = "company-delisted"
INCOME_STATEMENT_DATASET = "income-statement"
BALANCE_SHEET_STATEMENT_DATASET = "balance-sheet-statement"
CASHFLOW_STATEMENT_DATASET = "cashflow-statement"
LATEST_FINANCIALS_DATASET = "latest-financial-statements"
KEY_METRICS_DATASET = "key-metrics"
METRICS_RATIOS_DATASET = "metric-ratios"
KEY_METRICS_TTM_DATASET = "key-metrics-ttm"
RATIOS_TTM_DATASET = "ratios-ttm"
FINANCIAL_SCORES_DATASET = "financial-scores"
OWNER_EARNINGS_DATASET = "owner-earnings"
ENTERPRISE_VALUES_DATASET = "enterprise-values"
INCOME_STATEMENT_GROWTH_DATASET = "income-statement-growth"
BALANCE_SHEET_STATEMENT_GROWTH_DATASET = "balance-sheet-statement-growth"
CASHFLOW_STATEMENT_GROWTH_DATASET = "cashflow-statement-growth"
FINANCIAL_STATEMENT_GROWTH_DATASET = "finanical-statement-growth"
REVENUE_PRODUCT_SEGMENT_DATASET = "revenue-product-segementation"
REVENUE_GEOGRAPHIC_SEGMENT_DATASET = "revenue-geographic-segementation"
HISTORICAL_PRICE_EOD_FULL_DATASET = "technicals-historical-price-eod-full"
HISTORICAL_PRICE_EOD_NON_SPLIT_ADJUSTED_DATASET = "technicals-historical-price-eod-non-split-adjusted"
HISTORICAL_PRICE_EOD_DIVIDEND_ADJUSTED_DATASET = "technicals-historical-price-eod-dividend-adjusted"
TECHNICALS_SMA_20_DATASET = "technicals-sma-20"
TECHNICALS_SMA_50_DATASET = "technicals-sma-50"
TECHNICALS_SMA_200_DATASET = "technicals-sma-200"
TECHNICALS_EMA_12_DATASET = "technicals-ema-12"
TECHNICALS_EMA_26_DATASET = "technicals-ema-26"
TECHNICALS_EMA_50_DATASET = "technicals-ema-50"
TECHNICALS_EMA_200_DATASET = "technicals-ema-200"
TECHNICALS_WMA_20_DATASET = "technicals-wma-20"
TECHNICALS_WMA_50_DATASET = "technicals-wma-50"
TECHNICALS_WMA_200_DATASET = "technicals-wma-200"
TECHNICALS_DEMA_12_DATASET = "technicals-dema-12"
TECHNICALS_DEMA_26_DATASET = "technicals-dema-26"
TECHNICALS_DEMA_50_DATASET = "technicals-dema-50"
TECHNICALS_DEMA_200_DATASET = "technicals-dema-200"
TECHNICALS_TEMA_20_DATASET = "technicals-tema-20"
TECHNICALS_RSI_14_DATASET = "technicals-rsi-14"
TECHNICALS_RSI_7_DATASET = "technicals-rsi-7"
TECHNICALS_STANDARD_DEVIATION_20_DATASET = "technicals-standard-deviation-20"
TECHNICALS_WILLIAMS_14_DATASET = "technicals-williams-14"
TECHNICALS_ADX_14_DATASET = "technicals-adx-14"
DATASETS: list = [
    ECONOMICS_INDICATORS_DATASET,
    TREASURY_RATES_DATASET,
    MARKET_RISK_PREMIUM_DATASET,
    COMPANY_INFO_DATASET,
    COMPANY_NOTES_DATASET,
    COMPANY_PEERS_DATASET,
    COMPANY_EMPLOYEES_DATASET,
    COMPANY_MARKET_CAP_DATASET,
    COMPANY_SHARES_FLOAT_DATASET,
    COMPANY_OFFICERS_DATASET,
    COMPANY_COMPENSATION_DATASET,
    COMPANY_DELISTED_DATASET,
    INCOME_STATEMENT_DATASET,
    BALANCE_SHEET_STATEMENT_DATASET,
    CASHFLOW_STATEMENT_DATASET,
    LATEST_FINANCIALS_DATASET,
    KEY_METRICS_DATASET,
    METRICS_RATIOS_DATASET,
    KEY_METRICS_TTM_DATASET,
    RATIOS_TTM_DATASET,
    FINANCIAL_SCORES_DATASET,
    OWNER_EARNINGS_DATASET,
    ENTERPRISE_VALUES_DATASET,
    INCOME_STATEMENT_GROWTH_DATASET,
    BALANCE_SHEET_STATEMENT_GROWTH_DATASET,
    CASHFLOW_STATEMENT_GROWTH_DATASET,
    FINANCIAL_STATEMENT_GROWTH_DATASET,
    REVENUE_PRODUCT_SEGMENT_DATASET,
    REVENUE_GEOGRAPHIC_SEGMENT_DATASET,
    HISTORICAL_PRICE_EOD_FULL_DATASET,
    HISTORICAL_PRICE_EOD_NON_SPLIT_ADJUSTED_DATASET,
    HISTORICAL_PRICE_EOD_DIVIDEND_ADJUSTED_DATASET,
    TECHNICALS_SMA_20_DATASET,
    TECHNICALS_SMA_50_DATASET,
    TECHNICALS_SMA_200_DATASET,
    TECHNICALS_EMA_12_DATASET,
    TECHNICALS_EMA_26_DATASET,
    TECHNICALS_EMA_50_DATASET,
    TECHNICALS_EMA_200_DATASET,
    TECHNICALS_WMA_20_DATASET,
    TECHNICALS_WMA_50_DATASET,
    TECHNICALS_WMA_200_DATASET,
    TECHNICALS_DEMA_12_DATASET,
    TECHNICALS_DEMA_26_DATASET,
    TECHNICALS_DEMA_50_DATASET,
    TECHNICALS_DEMA_200_DATASET,
    TECHNICALS_TEMA_20_DATASET,
    TECHNICALS_RSI_14_DATASET,
    TECHNICALS_RSI_7_DATASET,
    TECHNICALS_STANDARD_DEVIATION_20_DATASET,
    TECHNICALS_WILLIAMS_14_DATASET,
    TECHNICALS_ADX_14_DATASET,
    STOCK_LIST_DATASET,
    ETF_LIST_DATASET,
    INDEX_LIST_DATASET,
    CRYPTOCURRENCY_LIST_DATASET,
    FOREX_LIST_DATASET,
    ETF_HOLDINGS_DATASET,
]

# ---- DTO REGISTRY (used to convert json raw object into a DTO to store at the silver layer) ----#
# Backwards compatibility for older call sites.
DTO_TYPES = DTO_REGISTRY

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
LIMIT_PLACEHOLDER = "__limit__"
PERIOD_PLACEHOLDER = "__period__"

# --- DATA FOLDERS ---
DATA_ROOT_FOLDER = os.environ.get("DATA_ROOT_FOLDER", "c:/strawberry/data")
REPO_ROOT_FOLDER = os.environ.get("REPO_ROOT_FOLDER", "c:/strawberry")
MANIFEST_FOLDER = "manifests"
BRONZE_FOLDER = "bronze"
DUCKDB_FOLDER = "duckdb"
DUCKDB_FILENAME = "strawberry.duckdb"
MIGRATIONS_FOLDER = "db/migrations"
LOG_FOLDER = "logs"
CHARTS_DATA_FOLDER = "charts"
DATASET_KEYMAP_FOLDER = "config"
DATASET_KEYMAP_FILENAME = os.environ.get("DATASET_KEYMAP_FILENAME", "dataset_keymap.yaml")

# --- FMP PRICING TIERS ---
FMP_BASIC_PLAN = "basic"
FMP_STARTER_PLAN = "starter"
FMP_PREMIUM_PLAN = "premium"
FMP_ULTIMATE_PLAN = "ultimate"
FMP_PLANS = [FMP_BASIC_PLAN, FMP_STARTER_PLAN, FMP_PREMIUM_PLAN, FMP_ULTIMATE_PLAN]
FREE_TIER_SYMBOLS = [
    "AAL",
    "AAPL",
    "ABBV",
    "ADBE",
    "AMD",
    "AMZN",
    "ATVI",
    "BA",
    "BAC",
    "BABA",
    "BIDU",
    "BILI",
    "C",
    "CARR",
    "CCL",
    "COIN",
    "COST",
    "CPRX",
    "CSCO",
    "CVX",
    "DAL",
    "DIS",
    "DOCU",
    "ET",
    "ETSY",
    "F",
    "FDX",
    "FUBO",
    "GE",
    "GM",
    "GOOGL",
    "GS",
    "HCA",
    "HOOD",
    "INTC",
    "JNJ",
    "JPM",
    "KO",
    "LCID",
    "LMT",
    "META",
    "MGM",
    "MRO",
    "MRNA",
    "MSFT",
    "NFLX",
    "NIO",
    "NKE",
    "NOK",
    "NVDA",
    "PEP",
    "PFE",
    "PINS",
    "PLTR",
    "PYPL",
    "RBLX",
    "RIOT",
    "RIVN",
    "RKT",
    "ROKU",
    "SBUX",
    "SHOP",
    "SIRI",
    "SNAP",
    "SOFI",
    "SONY",
    "SPY",
    "SPYG",
    "SQ",
    "T",
    "TGT",
    "TLRY",
    "TSLA",
    "TSM",
    "TWTR",
    "UAL",
    "UBER",
    "UNH",
    "V",
    "VIAC",
    "VWO",
    "VZ",
    "WBA",
    "WFC",
    "WMT",
    "XOM",
    "ZM",
]


FROM_DATE = "1980-01-01"


# --- HTTP calls, Retry and Throttle settings ---
RETRY_MAX_ATTEMPS = 3
RETRY_BASE_DELAY = 0.5
THROTTLE_PERIOD_SECONDS = 60
THROTTLE_MAX_CALLS = 60
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 30
