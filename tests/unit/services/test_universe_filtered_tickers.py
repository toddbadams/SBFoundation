"""Tests for UniverseRepo.get_filtered_tickers() and UniverseService.get_filtered_tickers()."""
from __future__ import annotations

import duckdb
import pytest

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.universe_repo import UniverseRepo
from sbfoundation.services.universe_service import UniverseService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo_with_screener(rows: list[tuple]) -> UniverseRepo:
    """Return a UniverseRepo backed by an in-memory DuckDB with fmp_market_screener populated."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA silver")
    conn.execute("""
        CREATE TABLE silver.fmp_market_screener (
            symbol VARCHAR,
            exchange_short_name VARCHAR,
            sector VARCHAR,
            industry VARCHAR,
            country VARCHAR,
            market_cap DOUBLE
        )
    """)
    conn.executemany(
        "INSERT INTO silver.fmp_market_screener VALUES (?, ?, ?, ?, ?, ?)", rows
    )
    bootstrap = DuckDbBootstrap(conn=conn)
    return UniverseRepo(bootstrap=bootstrap)


def _make_repo_with_profile(stock_rows: list[tuple], profile_rows: list[tuple]) -> UniverseRepo:
    """Return a UniverseRepo with fmp_stock_list + fmp_company_profile but NO screener."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA silver")
    conn.execute("CREATE TABLE silver.fmp_stock_list (symbol VARCHAR)")
    conn.executemany("INSERT INTO silver.fmp_stock_list VALUES (?)", [(s,) for s in stock_rows])
    conn.execute("""
        CREATE TABLE silver.fmp_company_profile (
            ticker VARCHAR,
            exchange VARCHAR,
            sector VARCHAR,
            industry VARCHAR,
            country VARCHAR
        )
    """)
    conn.executemany(
        "INSERT INTO silver.fmp_company_profile VALUES (?, ?, ?, ?, ?)", profile_rows
    )
    bootstrap = DuckDbBootstrap(conn=conn)
    return UniverseRepo(bootstrap=bootstrap)


def _make_repo_with_screener_and_mktcap(
    rows: list[tuple], mktcap_rows: list[tuple]
) -> UniverseRepo:
    """Return a UniverseRepo with fmp_market_screener + fmp_company_market_cap.

    Note: Tier 1 now uses screener.market_cap directly. fmp_company_market_cap
    is still created here for potential Tier 2/3 fallback tests.
    """
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA silver")
    conn.execute("""
        CREATE TABLE silver.fmp_market_screener (
            symbol VARCHAR,
            exchange_short_name VARCHAR,
            sector VARCHAR,
            industry VARCHAR,
            country VARCHAR,
            market_cap DOUBLE
        )
    """)
    conn.executemany(
        "INSERT INTO silver.fmp_market_screener VALUES (?, ?, ?, ?, ?, ?)", rows
    )
    conn.execute("""
        CREATE TABLE silver.fmp_company_market_cap (
            ticker VARCHAR,
            date DATE,
            market_cap DOUBLE
        )
    """)
    conn.executemany(
        "INSERT INTO silver.fmp_company_market_cap VALUES (?, ?, ?)", mktcap_rows
    )
    bootstrap = DuckDbBootstrap(conn=conn)
    return UniverseRepo(bootstrap=bootstrap)


def _make_repo_stock_list_only(symbols: list[str]) -> UniverseRepo:
    """Return a UniverseRepo with only fmp_stock_list (bootstrap fallback tier)."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA silver")
    conn.execute("CREATE TABLE silver.fmp_stock_list (symbol VARCHAR)")
    conn.executemany("INSERT INTO silver.fmp_stock_list VALUES (?)", [(s,) for s in symbols])
    bootstrap = DuckDbBootstrap(conn=conn)
    return UniverseRepo(bootstrap=bootstrap)


# ---------------------------------------------------------------------------
# Tier 1: fmp_market_screener (primary source)
# ---------------------------------------------------------------------------

SCREENER_DATA = [
    ("AAPL", "NASDAQ", "Technology", "Consumer Electronics", "US", 3_000_000_000_000),
    ("MSFT", "NASDAQ", "Technology", "Software-Application", "US", 3_000_000_000_000),
    ("XOM",  "NYSE",   "Energy",     "Oil & Gas E&P",        "US",   400_000_000_000),
    ("RY",   "TSX",    "Financials",  "Banks",               "CA",   150_000_000_000),
]


def test_screener_exchange_filter() -> None:
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=["NASDAQ"], sectors=[], industries=[], countries=[])
    assert set(result) == {"AAPL", "MSFT"}


def test_screener_sector_filter() -> None:
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=[], sectors=["Technology"], industries=[], countries=[])
    assert set(result) == {"AAPL", "MSFT"}


def test_screener_industry_filter() -> None:
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=[], sectors=[], industries=["Software-Application"], countries=[])
    assert set(result) == {"MSFT"}


def test_screener_country_filter() -> None:
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=[], sectors=[], industries=[], countries=["CA"])
    assert set(result) == {"RY"}


def test_screener_exchange_and_sector_and_semantics() -> None:
    """exchange=NASDAQ AND sector=Energy should return nothing (no NASDAQ energy stocks in test data)."""
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=["NASDAQ"], sectors=["Energy"], industries=[], countries=[])
    assert result == []


def test_screener_multi_value_within_dimension() -> None:
    """Multiple values within one dimension use OR semantics."""
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=["NASDAQ", "NYSE"], sectors=[], industries=[], countries=[])
    assert set(result) == {"AAPL", "MSFT", "XOM"}


def test_screener_no_filters_returns_all() -> None:
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=[], sectors=[], industries=[], countries=[])
    assert set(result) == {"AAPL", "MSFT", "XOM", "RY"}


def test_screener_no_matching_rows_returns_empty() -> None:
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=["XNYS_FAKE"], sectors=[], industries=[], countries=[])
    assert result == []


def test_screener_limit_respected() -> None:
    repo = _make_repo_with_screener(SCREENER_DATA)
    result = repo.get_filtered_tickers(exchanges=[], sectors=[], industries=[], countries=[], limit=2)
    assert len(result) <= 2


def test_screener_market_cap_with_exchange_filter() -> None:
    """Tier 1 uses screener.market_cap directly; exchange+country+market_cap filters combine correctly."""
    # SCREENER_DATA has market_cap in column 6: AAPL/MSFT=$3T, XOM=$400B, RY=$150B
    repo = _make_repo_with_screener(SCREENER_DATA)
    # Filter: US exchanges only, min $300B — all three US stocks clear the threshold;
    # RY is excluded by both exchange (TSX) and country (CA) filters.
    result = repo.get_filtered_tickers(
        exchanges=["NASDAQ", "NYSE"],
        sectors=[],
        industries=[],
        countries=["US"],
        min_market_cap_usd=300_000_000_000,
    )
    assert set(result) == {"AAPL", "MSFT", "XOM"}


# ---------------------------------------------------------------------------
# Tier 2: company_profile fallback (screener absent)
# ---------------------------------------------------------------------------

STOCK_SYMBOLS = ["AAPL", "MSFT", "XOM"]
PROFILE_DATA = [
    ("AAPL", "NASDAQ", "Technology", "Consumer Electronics", "US"),
    ("MSFT", "NASDAQ", "Technology", "Software-Application", "US"),
    ("XOM",  "NYSE",   "Energy",     "Oil & Gas E&P",        "US"),
]


def test_profile_fallback_exchange_filter() -> None:
    repo = _make_repo_with_profile(STOCK_SYMBOLS, PROFILE_DATA)
    result = repo.get_filtered_tickers(exchanges=["NASDAQ"], sectors=[], industries=[], countries=[])
    assert set(result) == {"AAPL", "MSFT"}


def test_profile_fallback_no_filters_returns_all() -> None:
    repo = _make_repo_with_profile(STOCK_SYMBOLS, PROFILE_DATA)
    result = repo.get_filtered_tickers(exchanges=[], sectors=[], industries=[], countries=[])
    assert set(result) == {"AAPL", "MSFT", "XOM"}


# ---------------------------------------------------------------------------
# Tier 3: stock_list bootstrap fallback (neither screener nor profile)
# ---------------------------------------------------------------------------

def test_bootstrap_fallback_returns_all_stock_list() -> None:
    repo = _make_repo_stock_list_only(["AAPL", "MSFT", "XOM"])
    result = repo.get_filtered_tickers(exchanges=["NASDAQ"], sectors=[], industries=[], countries=[])
    # Filters cannot be applied without dimension data — returns all symbols
    assert set(result) == {"AAPL", "MSFT", "XOM"}


def test_bootstrap_fallback_limit_respected() -> None:
    repo = _make_repo_stock_list_only(["A", "B", "C", "D", "E"])
    result = repo.get_filtered_tickers(exchanges=[], sectors=[], industries=[], countries=[], limit=3)
    assert len(result) <= 3


# ---------------------------------------------------------------------------
# UniverseService.get_filtered_tickers() — stub repo
# ---------------------------------------------------------------------------

class _StubRepo:
    def __init__(self, tickers: list[str], delisted: list[str] | None = None) -> None:
        self._tickers = tickers
        self._delisted = delisted or []
        self.last_call: dict = {}

    def get_filtered_tickers(
        self,
        *,
        exchanges: list[str],
        sectors: list[str],
        industries: list[str],
        countries: list[str],
        limit: int = 0,
        min_market_cap_usd: float | None = None,
        max_market_cap_usd: float | None = None,
    ) -> list[str]:
        self.last_call = {
            "exchanges": exchanges,
            "sectors": sectors,
            "industries": industries,
            "countries": countries,
            "limit": limit,
            "min_market_cap_usd": min_market_cap_usd,
            "max_market_cap_usd": max_market_cap_usd,
        }
        return self._tickers

    def get_delisted_tickers(self) -> list[str]:
        return self._delisted

    # Stub remaining required methods
    def get_update_tickers(self, *, start: int = 0, limit: int = 50) -> list[str]:
        return []

    def count_update_tickers(self) -> int:
        return 0

    def close(self) -> None:
        pass


def test_universe_service_delegates_to_repo() -> None:
    stub = _StubRepo(["AAPL", "MSFT"])
    service = UniverseService(repo=stub)
    result = service.get_filtered_tickers(
        exchanges=["NASDAQ"],
        sectors=["Technology"],
        industries=[],
        countries=["US"],
        limit=10,
    )
    assert result == ["AAPL", "MSFT"]
    assert stub.last_call == {
        "exchanges": ["NASDAQ"],
        "sectors": ["Technology"],
        "industries": [],
        "countries": ["US"],
        "limit": 10,
        "min_market_cap_usd": None,
        "max_market_cap_usd": None,
    }


def test_universe_service_passes_market_cap_bounds_to_repo() -> None:
    stub = _StubRepo(["AAPL"])
    service = UniverseService(repo=stub)
    service.get_filtered_tickers(
        exchanges=["NYSE"],
        sectors=[],
        industries=[],
        countries=["US"],
        min_market_cap_usd=10_000_000_000,
        max_market_cap_usd=None,
    )
    assert stub.last_call["min_market_cap_usd"] == 10_000_000_000
    assert stub.last_call["max_market_cap_usd"] is None


def test_universe_service_returns_empty_on_repo_exception() -> None:
    class _BrokenRepo(_StubRepo):
        def get_filtered_tickers(self, **_: object) -> list[str]:  # type: ignore[override]
            raise RuntimeError("db down")

    service = UniverseService(repo=_BrokenRepo([]))
    result = service.get_filtered_tickers(exchanges=[], sectors=[], industries=[], countries=[])
    assert result == []


# ---------------------------------------------------------------------------
# get_delisted_tickers — UniverseRepo (in-memory DuckDB)
# ---------------------------------------------------------------------------


def _make_repo_with_delisted(tickers: list[str]) -> UniverseRepo:
    """Return a UniverseRepo backed by an in-memory DuckDB with fmp_company_delisted populated."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA silver")
    conn.execute("""
        CREATE TABLE silver.fmp_company_delisted (
            ticker VARCHAR,
            company_name VARCHAR,
            exchange VARCHAR,
            delisted_date DATE
        )
    """)
    if tickers:
        conn.executemany(
            "INSERT INTO silver.fmp_company_delisted VALUES (?, NULL, NULL, NULL)",
            [(t,) for t in tickers],
        )
    bootstrap = DuckDbBootstrap(conn=conn)
    return UniverseRepo(bootstrap=bootstrap)


def test_get_delisted_tickers_returns_sorted_list() -> None:
    repo = _make_repo_with_delisted(["TWTR", "ATVI", "FB"])
    result = repo.get_delisted_tickers()
    assert result == ["ATVI", "FB", "TWTR"]


def test_get_delisted_tickers_deduplicates() -> None:
    repo = _make_repo_with_delisted(["TWTR", "TWTR", "FB"])
    result = repo.get_delisted_tickers()
    assert result == ["FB", "TWTR"]


def test_get_delisted_tickers_empty_when_table_absent() -> None:
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA silver")
    bootstrap = DuckDbBootstrap(conn=conn)
    repo = UniverseRepo(bootstrap=bootstrap)
    result = repo.get_delisted_tickers()
    assert result == []


def test_get_delisted_tickers_empty_table_returns_empty() -> None:
    repo = _make_repo_with_delisted([])
    result = repo.get_delisted_tickers()
    assert result == []


# ---------------------------------------------------------------------------
# get_delisted_tickers — UniverseService (stub repo)
# ---------------------------------------------------------------------------


def test_universe_service_get_delisted_delegates_to_repo() -> None:
    stub = _StubRepo([], delisted=["TWTR", "ATVI"])
    service = UniverseService(repo=stub)
    result = service.get_delisted_tickers()
    assert result == ["TWTR", "ATVI"]


def test_universe_service_get_delisted_returns_empty_on_exception() -> None:
    class _BrokenRepo(_StubRepo):
        def get_delisted_tickers(self) -> list[str]:
            raise RuntimeError("db down")

    service = UniverseService(repo=_BrokenRepo([]))
    result = service.get_delisted_tickers()
    assert result == []
