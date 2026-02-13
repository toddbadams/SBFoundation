import datetime
import hashlib
import json
from pathlib import Path
import tempfile
from collections.abc import Generator
import math
from attr import asdict
import duckdb
import pandas as pd
import pytest
from freezegun import freeze_time

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.services.universe_service import UniverseService
from sbfoundation.folders import Folders
from sbfoundation.orchestrator import Orchestrator, OrchestrationSettings
from tests.e2e.test_data import TestData
from sbfoundation.settings import *
from tests.e2e.fake_api import FakeApiServer
from sbfoundation.run.dtos.bronze_result import BronzeResult


pytestmark = pytest.mark.xdist_group(name="data_layer_promotion")


@pytest.fixture(autouse=True)
def _freeze_test_time() -> Generator[None, None, None]:
    with freeze_time(TestData.TIME_UTC):
        yield


@pytest.fixture
def fake_api_server() -> Generator[tuple[str, FakeApiServer], None, None]:
    server = FakeApiServer(api_key=TestData.API_KEY)
    port = server.start()
    TestData.set_port(port)
    try:
        yield str(port), server
    finally:
        server.stop()


def _update_tickers(self, start: int = 0, limit: int = 50, instrument_type: str | None = None, is_active: bool = True) -> list[str]:
    return [] if limit <= 0 else [TestData.TICKER]


def _new_tickers(self, start: int = 0, limit: int = 50, instrument_type: str | None = None, is_active: bool = True) -> list[str]:
    return []


def _run_id() -> str:
    return TestData.RUN_ID


def _create_file_id(self) -> str:
    return self.dataset


def _hash(self, payload: json) -> str:
    return "bdcbc6ebad2e45e6990502d67d5f9e011b483b8479529cb7fba9db7fe9dd2987"


def _test_setup(port: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(DATA_SOURCES_CONFIG[FMP_DATA_SOURCE], BASE_URL, f"http://{TestData.LOCAL_IP}:{port}/")

    repo_root_path = Folders.repo_absolute_path() / "temp"
    repo_root_path.mkdir(parents=True, exist_ok=True)
    data_root_path = Path(tempfile.mkdtemp(prefix="SBFoundation-e2e-", dir=repo_root_path)).resolve()

    monkeypatch.setenv("DATA_ROOT_FOLDER", str(data_root_path))
    monkeypatch.setenv("FMP_API_KEY", TestData.API_KEY)
    monkeypatch.setenv("DATASET_KEYMAP_FILENAME", "dataset_keymap_test.yaml")
    data_root_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(UniverseService, "run_id", staticmethod(_run_id))
    monkeypatch.setattr(UniverseService, "update_tickers", _update_tickers)
    monkeypatch.setattr(UniverseService, "new_tickers", _new_tickers)
    monkeypatch.setattr(Folders, "_data_root", staticmethod(lambda: data_root_path))
    monkeypatch.setattr(DatasetRecipe, "create_file_id", _create_file_id)
    monkeypatch.setattr(BronzeResult, "_hash", _hash)


def test_01_data_layer_promotion_full_run(fake_api_server: tuple[str, FakeApiServer], monkeypatch: pytest.MonkeyPatch):
    port, _ = fake_api_server
    _test_setup(port, monkeypatch)

    Orchestrator(
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
            non_ticker_recipe_limit=99,
            ticker_recipe_limit=99,
            enable_update_tickers=True,
            enable_new_tickers=False,
            update_ticker_limit=10,
            new_ticker_limit=0,
            fmp_plan=FMP_BASIC_PLAN,
        ),
        today=TestData.DATE,
    ).run()

    # market cap bronze file (ticker and date series)
    assert_bronze_contract(
        domain=TestData.MarketCap.DOMAIN,
        source=TestData.MarketCap.SOURCE,
        dataset=TestData.MarketCap.ENDPOINT,
        expected_dict=TestData.MarketCap.RESULT,
        ticker=TestData.TICKER,
    )
    # company profile bronze file (ticker snapshot)
    assert_bronze_contract(
        domain=TestData.CompanyProfile.DOMAIN,
        source=TestData.CompanyProfile.SOURCE,
        dataset=TestData.CompanyProfile.DATASET,
        expected_dict=TestData.CompanyProfile.RESULT,
        ticker=TestData.TICKER,
    )
    # econmic inidcator bronze file (no ticker and date series)
    assert_bronze_contract(
        domain=TestData.Economics.DOMAIN,
        source=TestData.Economics.SOURCE,
        dataset=TestData.Economics.ENDPOINT,
        expected_dict=TestData.Economics.RESULT,
        ticker=None,
    )
    # error bronze file (no ticker and no date series)
    assert_bronze_contract(
        domain=TestData.Error.DOMAIN,
        source=TestData.Error.SOURCE,
        dataset=TestData.Error.DATASET,
        expected_dict=TestData.Error.RESULT,
        ticker=TestData.TICKER,
    )

    # connect to duck db
    bootstrap = DuckDbBootstrap()
    with bootstrap.connect() as conn:
        assert_query_records(conn, TestData.MarketCap.SQL_SILVER, TestData.MarketCap.SILVER_EXPECTED, TestData.MarketCap.SILVER_DATE_FIELDS)


def test_02_orchestrator_stage_sequence(fake_api_server: tuple[str, FakeApiServer], monkeypatch: pytest.MonkeyPatch):
    port, _ = fake_api_server
    _test_setup(port, monkeypatch)

    # only run bronze layer
    Orchestrator(
        OrchestrationSettings(
            enable_instrument=True,
            enable_economics=True,
            enable_company=True,
            enable_fundamentals=True,
            enable_technicals=True,
            enable_bronze=True,
            enable_silver=False,
            enable_non_ticker_run=True,
            enable_ticker_run=True,
            non_ticker_recipe_limit=99,
            ticker_recipe_limit=99,
            enable_update_tickers=True,
            enable_new_tickers=False,
            update_ticker_limit=10,
            new_ticker_limit=0,
            fmp_plan=FMP_BASIC_PLAN,
        ),
        today=TestData.DATE,
    ).run()

    # market cap bronze file (ticker and date series)
    assert_bronze_contract(
        domain=TestData.MarketCap.DOMAIN,
        source=TestData.MarketCap.SOURCE,
        dataset=TestData.MarketCap.ENDPOINT,
        expected_dict=TestData.MarketCap.RESULT,
        ticker=TestData.TICKER,
    )
    # company profile bronze file (ticker snapshot)
    assert_bronze_contract(
        domain=TestData.CompanyProfile.DOMAIN,
        source=TestData.CompanyProfile.SOURCE,
        dataset=TestData.CompanyProfile.DATASET,
        expected_dict=TestData.CompanyProfile.RESULT,
        ticker=TestData.TICKER,
    )
    # econmic inidcator bronze file (no ticker and date series)
    assert_bronze_contract(
        domain=TestData.Economics.DOMAIN,
        source=TestData.Economics.SOURCE,
        dataset=TestData.Economics.ENDPOINT,
        expected_dict=TestData.Economics.RESULT,
        ticker=None,
    )
    # error bronze file (no ticker and no date series)
    assert_bronze_contract(
        domain=TestData.Error.DOMAIN,
        source=TestData.Error.SOURCE,
        dataset=TestData.Error.DATASET,
        expected_dict=TestData.Error.RESULT,
        ticker=TestData.TICKER,
    )

    # connect to duck db
    bootstrap = DuckDbBootstrap()
    with bootstrap.connect() as conn:
        assert_empty(conn, TestData.MarketCap.SQL_SILVER)

    # Only run the silver layer
    Orchestrator(
        OrchestrationSettings(
            enable_instrument=True,
            enable_economics=True,
            enable_company=True,
            enable_fundamentals=True,
            enable_technicals=True,
            enable_bronze=False,
            enable_silver=True,
            enable_non_ticker_run=True,
            enable_ticker_run=True,
            non_ticker_recipe_limit=99,
            ticker_recipe_limit=99,
            enable_update_tickers=True,
            enable_new_tickers=False,
            update_ticker_limit=10,
            new_ticker_limit=0,
            fmp_plan=FMP_BASIC_PLAN,
        ),
        today=TestData.DATE,
    ).run()

    # connect to duck db
    bootstrap = DuckDbBootstrap()
    with bootstrap.connect() as conn:
        assert_query_records(conn, TestData.MarketCap.SQL_SILVER, TestData.MarketCap.SILVER_EXPECTED, date_fields=["date", "ingested_at"])


def test_03_instrument_discovery_flow(fake_api_server: tuple[str, FakeApiServer], monkeypatch: pytest.MonkeyPatch):
    """Test the instrument discovery flow end-to-end.

    This test verifies:
    1. Bronze files are created for instrument discovery endpoints (stock-list, etf-list)
    2. Silver tables are populated (fmp_stock_list, fmp_etf_list)
    3. Unified silver.instrument table is populated via promotion
    """
    port, _ = fake_api_server
    _test_setup(port, monkeypatch)

    # Run the orchestrator with only non-ticker recipes (instrument discovery is global)
    Orchestrator(
        OrchestrationSettings(
            enable_instrument=True,
            enable_economics=True,
            enable_company=True,
            enable_fundamentals=True,
            enable_technicals=True,
            enable_bronze=True,
            enable_silver=True,
            enable_non_ticker_run=True,
            enable_ticker_run=False,  # Skip ticker-based recipes
            enable_update_tickers=False,
            enable_new_tickers=False,
            non_ticker_recipe_limit=99,
            ticker_recipe_limit=0,
            update_ticker_limit=0,
            new_ticker_limit=0,
            fmp_plan=FMP_BASIC_PLAN,
        ),
        today=TestData.DATE,
    ).run()

    # Verify Bronze files created for instrument discovery endpoints
    stock_list_bronze = get_most_recent_bronze_path(TestData.StockList.DOMAIN, TestData.StockList.SOURCE, TestData.StockList.DATASET)
    assert stock_list_bronze is not None, "stock-list Bronze file not created"
    assert stock_list_bronze.is_file()

    etf_list_bronze = get_most_recent_bronze_path(TestData.ETFList.DOMAIN, TestData.ETFList.SOURCE, TestData.ETFList.DATASET)
    assert etf_list_bronze is not None, "etf-list Bronze file not created"
    assert etf_list_bronze.is_file()

    # Verify Silver tables populated
    bootstrap = DuckDbBootstrap()
    with bootstrap.connect() as conn:
        # Check stock list silver table
        stock_list_df = conn.execute(TestData.StockList.SQL_SILVER).fetchdf()
        assert len(stock_list_df) == len(TestData.StockList.DATA), f"Expected {len(TestData.StockList.DATA)} stock rows, got {len(stock_list_df)}"

        # Check ETF list silver table
        etf_list_df = conn.execute(TestData.ETFList.SQL_SILVER).fetchdf()
        assert len(etf_list_df) == len(TestData.ETFList.DATA), f"Expected {len(TestData.ETFList.DATA)} ETF rows, got {len(etf_list_df)}"

        # Check unified instrument table is populated
        instrument_df = conn.execute('SELECT * FROM "silver"."instrument"').fetchdf()
        expected_total = len(TestData.StockList.DATA) + len(TestData.ETFList.DATA)
        assert len(instrument_df) == expected_total, f"Expected {expected_total} instruments, got {len(instrument_df)}"

        # Verify instrument types are correct
        equity_count = len(instrument_df[instrument_df["instrument_type"] == "equity"])
        etf_count = len(instrument_df[instrument_df["instrument_type"] == "etf"])
        assert equity_count == len(TestData.StockList.DATA), f"Expected {len(TestData.StockList.DATA)} equity instruments"
        assert etf_count == len(TestData.ETFList.DATA), f"Expected {len(TestData.ETFList.DATA)} ETF instruments"

        # Verify specific instruments exist in Silver
        aapl = instrument_df[instrument_df["symbol"] == "AAPL"]
        assert len(aapl) == 1, "AAPL not found in instrument table"
        assert aapl.iloc[0]["instrument_type"] == "equity"
        assert aapl.iloc[0]["source_endpoint"] == "stock-list"

        spy = instrument_df[instrument_df["symbol"] == "SPY"]
        assert len(spy) == 1, "SPY not found in instrument table"
        assert spy.iloc[0]["instrument_type"] == "etf"
        assert spy.iloc[0]["source_endpoint"] == "etf-list"


def assert_bronze_contract(domain: str, source: str, dataset: str, expected_dict: dict, ticker: str | None = None) -> dict:
    path = get_most_recent_bronze_path(domain, source, dataset, ticker)
    assert path is not None
    assert path.is_file(), f"Expected file, got: {path}"
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    try:
        actual = BronzeResult.from_row(payload)
        expected = BronzeResult.from_row(expected_dict)
    except Exception as e:
        pytest.fail("Exception reading payload")

    assert actual == expected


def _to_iso_date(value) -> str | None:
    if value is None:
        return None

    # FakeDate likely subclasses/behaves like datetime.date; handle both
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()

    if isinstance(value, datetime.date):
        return value.isoformat()

    # strings like "2026-01-15" or "2026-01-15T00:00:00"
    return pd.to_datetime(value).date().isoformat()


def _normalize_missing(value):
    # Treat pandas/numpy missing + the literal "NaT" string as missing
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if value == "NaT":
        return None
    # pandas NA/NaT scalars
    if pd.isna(value):
        return None
    return value


def assert_query_records(conn: duckdb.DuckDBPyConnection, sql: str, expected: list[dict], date_fields: list[str]) -> None:
    rel = conn.execute(sql)
    arrow = rel.fetch_arrow_table()
    df = arrow.to_pandas(date_as_object=True)

    actual = df.to_dict(orient="records")

    # Drop *_sk / *_id keys
    for row in actual:
        for key in [k for k in row if k.endswith("_sk") or k.endswith("_id")]:
            row.pop(key, None)

    for row in expected:
        for key in [k for k in row if k.endswith("_sk") or k.endswith("_id")]:
            row.pop(key, None)

    # Normalize missing values and date fields on BOTH sides
    for rows in (actual, expected):
        for row in rows:
            # first normalize missing everywhere (covers effective_to etc.)
            for k, v in list(row.items()):
                row[k] = _normalize_missing(v)

            # then normalize the configured date fields to ISO strings (or None)
            for field in date_fields:
                if field in row:
                    row[field] = None if row[field] is None else _to_iso_date(row[field])

    assert actual == expected


def assert_empty(conn: duckdb.DuckDBPyConnection, sql: str) -> None:
    try:
        conn.execute(sql).df()
        pytest.fail(f"Expected query to fail, but it succeeded. SQL:\n{sql}")
    except:
        pass


def get_most_recent_bronze_path(domain: str, source: str, dataset: str, ticker: str | None = None) -> Path | None:
    base = Folders.bronze_result_absolute_path(domain, source, dataset)
    if ticker:
        base = base / ticker
    if not base.exists():
        return None
    files = [path for path in base.iterdir() if path.is_file()]
    return max(files, key=lambda path: path.stat().st_mtime) if files else None
