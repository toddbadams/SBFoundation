from __future__ import annotations


_API_KEY = "test-key"
_LOCAL_IP = "127.0.0.1"
_PORT = "50087"
_TICKER = "AAPL"
_URL = "fake"

_TIME_UTC = "2026-01-19T12:00:00Z"
_TIME_TIME_ZONE = "2026-01-19T12:00:00+00:00"
_DATE = "2026-01-19"

_GOLD_BUILD_MODEL_VERSION = "test-model-version"
_RUN_ID = f"{_DATE}.123456"

_HASH = "bdcbc6ebad2e45e6990502d67d5f9e011b483b8479529cb7fba9db7fe9dd2987"


class TestData:
    # --- Core test constants --- #
    API_KEY = _API_KEY
    LOCAL_IP = _LOCAL_IP
    TICKER = _TICKER
    URL = _URL

    TIME_UTC = _TIME_UTC
    TIME_TIME_ZONE = _TIME_TIME_ZONE
    DATE = _DATE

    GOLD_BUILD_MODEL_VERSION = _GOLD_BUILD_MODEL_VERSION
    RUN_ID = _RUN_ID
    PORT = _PORT

    @classmethod
    def set_port(cls, port: str | int) -> None:
        _set_port(str(port))

    # ---- INSTRUMENT DOMAIN (discovery endpoints) ---- #
    class StockList:
        ENDPOINT = "stock-list"
        DATASET = "stock-list"
        DOMAIN = "instrument"
        SOURCE = "fmp"

        DATA = [
            {"symbol": "AAPL", "name": "Apple Inc.", "price": 232.8, "exchange": "NASDAQ", "exchangeShortName": "NASDAQ", "type": "stock"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "price": 415.5, "exchange": "NASDAQ", "exchangeShortName": "NASDAQ", "type": "stock"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "price": 180.2, "exchange": "NASDAQ", "exchangeShortName": "NASDAQ", "type": "stock"},
        ]

        SILVER_TABLE = "fmp_stock_list"
        SQL_SILVER = 'SELECT * FROM "silver"."fmp_stock_list" ORDER BY symbol'
        SILVER_EXPECTED = [
            {"symbol": "AAPL", "name": "Apple Inc.", "price": 232.8, "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "type": "stock", "ticker": "AAPL"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "price": 180.2, "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "type": "stock", "ticker": "GOOGL"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "price": 415.5, "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "type": "stock", "ticker": "MSFT"},
        ]
        SILVER_DATE_FIELDS = ["ingested_at"]

    class ETFList:
        ENDPOINT = "etf-list"
        DATASET = "etf-list"
        DOMAIN = "instrument"
        SOURCE = "fmp"

        DATA = [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "price": 520.3, "exchange": "NYSE Arca", "exchangeShortName": "AMEX"},
            {"symbol": "QQQ", "name": "Invesco QQQ Trust", "price": 480.1, "exchange": "NASDAQ", "exchangeShortName": "NASDAQ"},
        ]

        SILVER_TABLE = "fmp_etf_list"
        SQL_SILVER = 'SELECT * FROM "silver"."fmp_etf_list" ORDER BY symbol'
        SILVER_EXPECTED = [
            {"symbol": "QQQ", "name": "Invesco QQQ Trust", "price": 480.1, "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "ticker": "QQQ"},
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "price": 520.3, "exchange": "NYSE Arca", "exchange_short_name": "AMEX", "ticker": "SPY"},
        ]
        SILVER_DATE_FIELDS = ["ingested_at"]

    class Instrument:
        """Unified instrument table expectations after promotion."""
        SQL_SILVER = 'SELECT symbol, instrument_type, source_endpoint, name, exchange, exchange_short_name, is_active FROM "silver"."instrument" ORDER BY symbol, instrument_type'
        SILVER_EXPECTED = [
            {"symbol": "AAPL", "instrument_type": "equity", "source_endpoint": "stock-list", "name": "Apple Inc.", "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "is_active": True},
            {"symbol": "GOOGL", "instrument_type": "equity", "source_endpoint": "stock-list", "name": "Alphabet Inc.", "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "is_active": True},
            {"symbol": "MSFT", "instrument_type": "equity", "source_endpoint": "stock-list", "name": "Microsoft Corporation", "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "is_active": True},
            {"symbol": "QQQ", "instrument_type": "etf", "source_endpoint": "etf-list", "name": "Invesco QQQ Trust", "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "is_active": True},
            {"symbol": "SPY", "instrument_type": "etf", "source_endpoint": "etf-list", "name": "SPDR S&P 500 ETF Trust", "exchange": "NYSE Arca", "exchange_short_name": "AMEX", "is_active": True},
        ]

        # Gold layer expectations
        SQL_GOLD_DIM = 'SELECT symbol, instrument_type, source_endpoint, name, exchange, exchange_short_name, is_active, is_current FROM "gold"."dim_instrument" ORDER BY symbol, instrument_type'
        GOLD_EXPECTED_DIM = [
            {"symbol": "AAPL", "instrument_type": "equity", "source_endpoint": "stock-list", "name": "Apple Inc.", "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "is_active": True, "is_current": True},
            {"symbol": "GOOGL", "instrument_type": "equity", "source_endpoint": "stock-list", "name": "Alphabet Inc.", "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "is_active": True, "is_current": True},
            {"symbol": "MSFT", "instrument_type": "equity", "source_endpoint": "stock-list", "name": "Microsoft Corporation", "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "is_active": True, "is_current": True},
            {"symbol": "QQQ", "instrument_type": "etf", "source_endpoint": "etf-list", "name": "Invesco QQQ Trust", "exchange": "NASDAQ", "exchange_short_name": "NASDAQ", "is_active": True, "is_current": True},
            {"symbol": "SPY", "instrument_type": "etf", "source_endpoint": "etf-list", "name": "SPDR S&P 500 ETF Trust", "exchange": "NYSE Arca", "exchange_short_name": "AMEX", "is_active": True, "is_current": True},
        ]
        GOLD_DATE_FIELDS = ["effective_from", "effective_to", "discovered_at", "last_enriched_at"]

    # ---- COMPANY DOMAIN ---- #
    class CompanyProfile:
        # --- Endpoint / identifiers --- #
        ENDPOINT = "profile"
        DATASET = "company-profile"
        DOMAIN = "company"
        SOURCE = "fmp"

        # --- Payloads --- #
        DATA = [
            {
                "symbol": _TICKER,
                "price": 232.8,
                "marketCap": 3500823120000,
                "beta": 1.24,
                "lastDividend": 0.99,
                "range": "164.08-260.1",
                "change": 4.79,
                "changePercentage": 2.1008,
                "volume": 0,
                "averageVolume": 50542058,
                "companyName": "Apple Inc.",
                "currency": "USD",
                "cik": "0000320193",
                "isin": "US0378331005",
                "cusip": "037833100",
                "exchangeFullName": "NASDAQ Global Select",
                "exchange": "NASDAQ",
                "industry": "Consumer Electronics",
                "website": "https://www.apple.com",
                "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company offers iPhone, a line of smartphones; Mac, a line of personal computers; iPad, a line of multi-purpose tablets; and wearables, home, and accessories comprising AirPods, Apple TV, Apple Watch, Beats products, and HomePod. It also provides AppleCare support and cloud services; and operates various platforms, including the App Store that allow customers to discov...",
                "ceo": "Mr. Timothy D. Cook",
                "sector": "Technology",
                "country": "US",
                "fullTimeEmployees": "164000",
                "phone": "(408) 996-1010",
                "address": "One Apple Park Way",
                "city": "Cupertino",
                "state": "CA",
                "zip": "95014",
                "image": "https://images.financialmodelingprep.com/symbol/AAPL.png",
                "ipoDate": "1980-12-12",
                "defaultImage": False,
                "isEtf": False,
                "isActivelyTrading": True,
                "isAdr": False,
                "isFund": False,
            }
        ]

        RESULT = {
            "content": DATA,
            "elapsed_microseconds": 0,
            "error": None,
            "first_date": _DATE,
            "headers": "date=Mon, 19 Jan 2026 12:00:00 GMT; server=uvicorn; content-length=1320; content-type=application/json",
            "last_date": _DATE,
            "now": _TIME_TIME_ZONE,
            "reason": "OK",
            "request": {
                "allows_empty_content": False,
                "cadence_mode": "interval",
                "data_source_path": "fake/profile",
                "date_key": "",
                "dto_type": "data_layer.dtos.company.company_dto.CompanyDTO",
                "error": None,
                "file_id": "company-profile",
                "from_date": "1980-01-01",
                "injestion_date": _DATE,
                "limit": 5,
                "min_age_days": 0,
                "query_vars": {"apikey": ["***"], "symbol": _TICKER},
                "recipe": {
                    "cadence_mode": "interval",
                    "data_source_path": "fake/profile",
                    "dataset": DATASET,
                    "date_key": "",
                    "discriminator": None,
                    "domain": DOMAIN,
                    "error": None,
                    "execution_phase": "data_acquisition",
                    "help_url": "https://example.com/docs/profile",
                    "is_ticker_based": True,
                    "min_age_days": 0,
                    "query_vars": {"symbol": "__ticker__"},
                    "run_days": ["mon"],
                    "source": SOURCE,
                    "ticker": "_none_",
                },
                "release_day": None,
                "run_id": _RUN_ID,
                "ticker": _TICKER,
                "to_date": _DATE,
                "url": "http://" + _LOCAL_IP + ":" + _PORT + "/fake/profile",
            },
            "status_code": 200,
        }

        SQL_GOLD_DIM = 'SELECT * FROM "gold"."dim_company_profile"'

        GOLD_EXPECTED_DIM = [
            {
                "effective_from": _DATE,
                "effective_to": "NaT",
                "is_current": True,
                "company_sk": 1,
                "ticker": _TICKER,
                "cik": DATA[0]["cik"],
                "isin": DATA[0]["isin"],
                "cusip": DATA[0]["cusip"],
                "exchange": DATA[0]["exchange"],
                "exchange_full_name": DATA[0]["exchangeFullName"],
                "currency": DATA[0]["currency"],
                "company_name": DATA[0]["companyName"],
                "industry": DATA[0]["industry"],
                "sector": DATA[0]["sector"],
                "description": DATA[0]["description"],
                "website": DATA[0]["website"],
                "ceo": DATA[0]["ceo"],
                "country": DATA[0]["country"],
                "full_time_employees": 164000,
                "phone": DATA[0]["phone"],
                "address": DATA[0]["address"],
                "city": DATA[0]["city"],
                "state": DATA[0]["state"],
                "zip": DATA[0]["zip"],
                "image": DATA[0]["image"],
                "ipo_date": DATA[0]["ipoDate"],
                "default_image": DATA[0]["defaultImage"],
                "is_etf": DATA[0]["isEtf"],
                "is_actively_trading": DATA[0]["isActivelyTrading"],
                "is_adr": DATA[0]["isAdr"],
                "is_fund": DATA[0]["isFund"],
                "gold_build_id": 2,
                "model_version": _GOLD_BUILD_MODEL_VERSION,
            }
        ]
        GOLD_DATE_FIELDS = ["effective_from", "effective_to", "ipo_date"]

    class MarketCap:
        # --- Endpoint / identifiers --- #
        ENDPOINT = "company-market-cap"
        DOMAIN = "company"
        SOURCE = "fmp"

        # --- Payloads --- #
        DATA = [
            {"symbol": _TICKER, "date": "2026-01-15", "marketCap": 10_000_000},
            {"symbol": _TICKER, "date": "2026-01-16", "marketCap": 11_000_000},
            {"symbol": _TICKER, "date": "2026-01-17", "marketCap": 12_000_000},
        ]

        RESULT = {
            "content": DATA,
            "elapsed_microseconds": 0,
            "error": None,
            "first_date": "2026-01-15",
            "headers": "date=Mon, 19 Jan 2026 12:00:00 GMT; server=uvicorn; content-length=178; content-type=application/json",
            "last_date": "2026-01-17",
            "now": _TIME_TIME_ZONE,
            "reason": "OK",
            "request": {
                "allows_empty_content": False,
                "cadence_mode": "interval",
                "data_source_path": "fake/company-market-cap",
                "date_key": "date",
                "dto_type": "data_layer.dtos.company.company_market_cap_dto.CompanyMarketCapDTO",
                "error": None,
                "file_id": "company-market-cap",
                "from_date": "1980-01-01",
                "injestion_date": _DATE,
                "limit": 5,
                "min_age_days": 0,
                "query_vars": {"apikey": ["***"], "symbol": _TICKER},
                "recipe": {
                    "cadence_mode": "interval",
                    "data_source_path": "fake/company-market-cap",
                    "dataset": "company-market-cap",
                    "date_key": "date",
                    "discriminator": None,
                    "domain": DOMAIN,
                    "error": None,
                    "execution_phase": "data_acquisition",
                    "help_url": "https://example.com/docs/company-market-cap",
                    "is_ticker_based": True,
                    "min_age_days": 0,
                    "query_vars": {"symbol": "__ticker__"},
                    "run_days": ["mon"],
                    "source": SOURCE,
                    "ticker": "_none_",
                },
                "release_day": None,
                "run_id": _RUN_ID,
                "ticker": _TICKER,
                "to_date": _DATE,
                "url": "http://" + _LOCAL_IP + ":" + _PORT + "/fake/company-market-cap",
            },
            "status_code": 200,
        }

        SQL_SILVER = 'SELECT * FROM "silver"."company-market-cap"'
        SILVER_EXPECTED = [
            {
                "ticker": _TICKER,
                "date": DATA[0]["date"],
                "market_cap": DATA[0]["marketCap"],
                "bronze_file_id": "company-market-cap",
                "run_id": _RUN_ID,
                "ingested_at": _DATE,
            },
            {
                "ticker": _TICKER,
                "date": DATA[1]["date"],
                "market_cap": DATA[1]["marketCap"],
                "bronze_file_id": "company-market-cap",
                "run_id": _RUN_ID,
                "ingested_at": _DATE,
            },
            {
                "ticker": _TICKER,
                "date": DATA[2]["date"],
                "market_cap": DATA[2]["marketCap"],
                "bronze_file_id": "company-market-cap",
                "run_id": _RUN_ID,
                "ingested_at": _DATE,
            },
        ]
        SILVER_DATE_FIELDS = ["date", "ingested_at"]

        SQL_GOLD_FACT = 'SELECT * FROM "gold"."fact_market_cap_snapshot"'
        GOLD_EXPECTED = [
            {
                "company_sk": 1,
                "date_sk": 1,
                "ticker": _TICKER,
                "date": DATA[0]["date"],
                "market_cap": DATA[0]["marketCap"],
                "gold_build_id": 2,
                "model_version": _GOLD_BUILD_MODEL_VERSION,
            },
            {
                "company_sk": 1,
                "date_sk": 2,
                "ticker": _TICKER,
                "date": DATA[1]["date"],
                "market_cap": DATA[1]["marketCap"],
                "gold_build_id": 2,
                "model_version": _GOLD_BUILD_MODEL_VERSION,
            },
            {
                "company_sk": 1,
                "date_sk": 3,
                "ticker": _TICKER,
                "date": DATA[2]["date"],
                "market_cap": DATA[2]["marketCap"],
                "gold_build_id": 2,
                "model_version": _GOLD_BUILD_MODEL_VERSION,
            },
        ]
        GOLD_DATE_FIELDS = ["date"]

    class Dates:
        # --- Dates dimension (derived from data-driven rows) --- #
        SQL_GOLD_DIM_DATE = 'SELECT * FROM "gold"."dim_date"'
        GOLD_EXPECTED_DIM_DATE = [
            {
                "date_sk": 1,
                "date": "2026-01-15",
                "year": 2026,
                "quarter": 1,
                "month": 1,
                "day": 15,
                "day_of_week": 4,
                "day_name": "Thursday",
                "month_name": "January",
                "iso_week": 3,
                "gold_build_id": 2,
                "model_version": _GOLD_BUILD_MODEL_VERSION,
            },
            {
                "date_sk": 2,
                "date": "2026-01-16",
                "year": 2026,
                "quarter": 1,
                "month": 1,
                "day": 16,
                "day_of_week": 5,
                "day_name": "Friday",
                "month_name": "January",
                "iso_week": 3,
                "gold_build_id": 2,
                "model_version": _GOLD_BUILD_MODEL_VERSION,
            },
            {
                "date_sk": 3,
                "date": "2026-01-17",
                "year": 2026,
                "quarter": 1,
                "month": 1,
                "day": 17,
                "day_of_week": 6,
                "day_name": "Saturday",
                "month_name": "January",
                "iso_week": 3,
                "gold_build_id": 2,
                "model_version": _GOLD_BUILD_MODEL_VERSION,
            },
        ]
        GOLD_DATE_FIELDS = ["date"]

    class Economics:
        # --- Endpoint / identifiers --- #
        ENDPOINT = "economic-indicators"
        DOMAIN = "economics"
        SOURCE = "fmp"

        # --- Payloads --- #
        DATA = [{"name": "GDP", "date": "2026-01-01", "value": 42.0}]

        RESULT = {
            "content": DATA,
            "elapsed_microseconds": 0,
            "error": None,
            "first_date": "2026-01-01",
            "headers": "date=Mon, 19 Jan 2026 12:00:00 GMT; server=uvicorn; content-length=49; content-type=application/json",
            "last_date": "2026-01-01",
            "now": _TIME_TIME_ZONE,
            "reason": "OK",
            "request": {
                "allows_empty_content": False,
                "cadence_mode": "interval",
                "data_source_path": "fake/economic-indicators",
                "date_key": "date",
                "dto_type": "data_layer.dtos.economics.economics_dto.EconomicsDTO",
                "error": None,
                "file_id": "economic-indicators",
                "from_date": "1980-01-01",
                "injestion_date": _DATE,
                "limit": 5,
                "min_age_days": 0,
                "query_vars": {
                    "apikey": ["***"],
                    "from": "1980-01-01",
                    "name": "test-indicator",
                    "to": _DATE,
                },
                "recipe": {
                    "cadence_mode": "interval",
                    "data_source_path": "fake/economic-indicators",
                    "dataset": "economic-indicators",
                    "date_key": "date",
                    "discriminator": None,
                    "domain": DOMAIN,
                    "error": None,
                    "execution_phase": "data_acquisition",
                    "help_url": "https://example.com/docs/economic-indicators",
                    "is_ticker_based": False,
                    "min_age_days": 0,
                    "query_vars": {"from": "__from__", "name": "test-indicator", "to": "__to__"},
                    "run_days": ["mon"],
                    "source": SOURCE,
                    "ticker": "_none_",
                },
                "release_day": None,
                "run_id": _RUN_ID,
                "ticker": None,
                "to_date": _DATE,
                "url": "http://" + _LOCAL_IP + ":" + _PORT + "/fake/economic-indicators",
            },
            "status_code": 200,
        }

    class Ops:
        # --- Ops file ingestions (shown in your snippet for economics) --- #
        SQL_OPS_FILE_INGESTIONS = 'SELECT * FROM "ops"."file_ingestions" WHERE dataset = \'economic-indicators\''
        OPS_EXPECTED_FILE_INGESTIONS = {
            "run_id": _RUN_ID,
            "file_id": "economic-indicators",
            "domain": "economics",
            "source": "fmp",
            "dataset": "economic-indicators",
            "discriminator": None,
            "ticker": None,
            "bronze_filename": "bronze\\economics\\fmp\\economic-indicators\\economic-indicators.json",
            "bronze_error": None,
            "bronze_rows": 1,
            "bronze_from_date": "2026-01-01",
            "bronze_to_date": "2026-01-01",
            "bronze_injest_start_time": _DATE,
            "bronze_injest_end_time": _DATE,
            "bronze_can_promote": False,
            "bronze_payload_hash": _HASH,
            "silver_tablename": '"silver"."economic-indicators"',
            "silver_errors": None,
            "silver_rows_created": 1,
            "silver_rows_updated": 0,
            "silver_rows_failed": 0,
            "silver_from_date": "2026-01-01",
            "silver_to_date": "2026-01-01",
            "silver_injest_start_time": _DATE,
            "silver_injest_end_time": _DATE,
            "silver_can_promote": True,
            # Note: Gold columns contain aggregate metrics across all processed tables
            # This is a known limitation - ideally these would be per-dataset, not aggregate
            "gold_object_type": "dimension, fact",
            "gold_tablename": "dim_instrument, dim_company_profile, fact_market_cap_snapshot",
            "gold_errors": None,
            "gold_rows_created": 4,  # Aggregate: dims_inserted + facts_upserted
            "gold_rows_updated": 0,
            "gold_rows_failed": 0,
            "gold_from_date": _DATE,
            "gold_to_date": _DATE,
            "gold_injest_start_time": _DATE,
            "gold_injest_end_time": _DATE,
            "gold_can_promote": True,
        }
        OPS_DATE_FIELDS = [
            "bronze_from_date",
            "bronze_to_date",
            "bronze_injest_start_time",
            "bronze_injest_end_time",
            "silver_from_date",
            "silver_to_date",
            "silver_injest_start_time",
            "silver_injest_end_time",
            "gold_from_date",
            "gold_to_date",
            "gold_injest_start_time",
            "gold_injest_end_time",
        ]

    class Error:
        # --- Endpoint / identifiers --- #
        ENDPOINT = "error"
        DATASET = "company-notes"
        DOMAIN = "company"
        SOURCE = "fmp"

        RESULT = {
            "content": '{"detail":"simulated failure"}',
            "elapsed_microseconds": 0,
            "error": "Failed bronze acceptance: INVALID CONTENT",
            "first_date": _DATE,
            "headers": "date=Mon, 19 Jan 2026 12:00:00 GMT; server=uvicorn; content-length=30; content-type=application/json",
            "last_date": _DATE,
            "now": _TIME_TIME_ZONE,
            "reason": "Internal Server Error",
            "request": {
                "allows_empty_content": False,
                "cadence_mode": "interval",
                "data_source_path": "fake/error",
                "date_key": "date",
                "dto_type": "data_layer.dtos.company.company_dto.CompanyDTO",
                "error": None,
                "file_id": "company-notes",
                "from_date": "1980-01-01",
                "injestion_date": _DATE,
                "limit": 5,
                "min_age_days": 0,
                "query_vars": {"apikey": ["***"], "symbol": _TICKER},
                "recipe": {
                    "cadence_mode": "interval",
                    "data_source_path": "fake/error",
                    "dataset": DATASET,
                    "date_key": "date",
                    "discriminator": None,
                    "domain": DOMAIN,
                    "error": None,
                    "execution_phase": "data_acquisition",
                    "help_url": "https://example.com/docs/company-notes",
                    "is_ticker_based": True,
                    "min_age_days": 0,
                    "query_vars": {"symbol": "__ticker__"},
                    "run_days": ["mon"],
                    "source": SOURCE,
                    "ticker": "_none_",
                },
                "release_day": None,
                "run_id": _RUN_ID,
                "ticker": _TICKER,
                "to_date": _DATE,
                "url": "http://" + _LOCAL_IP + ":" + _PORT + "/fake/error",
            },
            "status_code": 500,
        }


def _format_url(endpoint: str) -> str:
    return f"http://{_LOCAL_IP}:{_PORT}/{_URL}/{endpoint}"


def _refresh_expected_urls() -> None:
    TestData.CompanyProfile.RESULT["request"]["url"] = _format_url(TestData.CompanyProfile.ENDPOINT)
    TestData.MarketCap.RESULT["request"]["url"] = _format_url(TestData.MarketCap.ENDPOINT)
    TestData.Economics.RESULT["request"]["url"] = _format_url(TestData.Economics.ENDPOINT)
    TestData.Error.RESULT["request"]["url"] = _format_url(TestData.Error.ENDPOINT)


def _set_port(port: str) -> None:
    global _PORT
    _PORT = port
    TestData.PORT = _PORT
    _refresh_expected_urls()


_refresh_expected_urls()
