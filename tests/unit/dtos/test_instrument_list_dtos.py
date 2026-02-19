"""Tests for ETFListDTO and IndexListDTO field mapping correctness."""
from __future__ import annotations

from sbfoundation.dtos.instrument.etf_list_dto import ETFListDTO
from sbfoundation.dtos.instrument.index_list_dto import IndexListDTO


# ---------------------------------------------------------------------------
# ETFListDTO
# ---------------------------------------------------------------------------

ETF_PAYLOAD = {"symbol": "GBRE.L", "name": "SPDR Dow Jones Global Real Estate UCITS ETF"}


def test_etf_symbol_maps_correctly() -> None:
    dto = ETFListDTO.from_row(ETF_PAYLOAD)
    assert dto.symbol == "GBRE.L"


def test_etf_company_name_maps_correctly() -> None:
    dto = ETFListDTO.from_row(ETF_PAYLOAD)
    assert dto.company_name == "SPDR Dow Jones Global Real Estate UCITS ETF"


def test_etf_to_dict_does_not_contain_stale_fields() -> None:
    # These fields existed in a prior DTO version and must no longer be emitted.
    # 'ticker' is a BronzeToSilverDTO base-class field and is expected; its stale
    # Silver table column is removed via migration, not by changing the DTO.
    dto = ETFListDTO.from_row(ETF_PAYLOAD)
    result = dto.to_dict()
    assert "price" not in result
    assert "exchange" not in result
    assert "exchange_short_name" not in result


def test_etf_to_dict_contains_expected_fields() -> None:
    dto = ETFListDTO.from_row(ETF_PAYLOAD)
    result = dto.to_dict()
    assert "symbol" in result
    assert "company_name" in result


# ---------------------------------------------------------------------------
# IndexListDTO
# ---------------------------------------------------------------------------

INDEX_PAYLOAD = {
    "symbol": "^TTIN",
    "name": "S&P/TSX Capped Industrials Index",
    "currency": "CAD",
    "exchange": "TSX",
}


def test_index_symbol_maps_correctly() -> None:
    dto = IndexListDTO.from_row(INDEX_PAYLOAD)
    assert dto.symbol == "^TTIN"


def test_index_exchange_maps_correctly() -> None:
    """exchange field maps from API key 'exchange', not 'stockExchange'."""
    dto = IndexListDTO.from_row(INDEX_PAYLOAD)
    assert dto.exchange == "TSX"


def test_index_currency_maps_correctly() -> None:
    dto = IndexListDTO.from_row(INDEX_PAYLOAD)
    assert dto.currency == "CAD"


def test_index_company_name_maps_correctly() -> None:
    dto = IndexListDTO.from_row(INDEX_PAYLOAD)
    assert dto.company_name == "S&P/TSX Capped Industrials Index"


def test_index_to_dict_does_not_contain_stale_fields() -> None:
    # stock_exchange and exchange_short_name must no longer be emitted.
    # 'ticker' is a BronzeToSilverDTO base-class field; its stale Silver column
    # is removed via migration rather than changing the base DTO.
    dto = IndexListDTO.from_row(INDEX_PAYLOAD)
    result = dto.to_dict()
    assert "stock_exchange" not in result
    assert "exchange_short_name" not in result


def test_index_to_dict_contains_exchange() -> None:
    dto = IndexListDTO.from_row(INDEX_PAYLOAD)
    result = dto.to_dict()
    assert result.get("exchange") == "TSX"


def test_index_missing_exchange_defaults_to_none() -> None:
    """When exchange is absent from payload, field should be None."""
    dto = IndexListDTO.from_row({"symbol": "^SPX", "name": "S&P 500"})
    assert dto.exchange is None


# ---------------------------------------------------------------------------
# MarketScreenerDTO
# ---------------------------------------------------------------------------

from sbfoundation.dtos.market.market_screener_dto import MarketScreenerDTO

SCREENER_PAYLOAD = {
    "symbol": "AAPL",
    "companyName": "Apple Inc.",
    "marketCap": 2800000000000,
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "beta": 1.2,
    "price": 175.0,
    "lastAnnualDividend": 0.92,
    "volume": 50000000,
    "exchange": "NASDAQ",
    "exchangeShortName": "NASDAQ",
    "country": "US",
    "isEtf": False,
    "isActivelyTrading": True,
    "isAdr": False,
    "isFund": False,
}


def test_screener_symbol_maps_correctly() -> None:
    dto = MarketScreenerDTO.from_row(SCREENER_PAYLOAD)
    assert dto.symbol == "AAPL"


def test_screener_exchange_maps_correctly() -> None:
    dto = MarketScreenerDTO.from_row(SCREENER_PAYLOAD)
    assert dto.exchange == "NASDAQ"


def test_screener_sector_maps_correctly() -> None:
    dto = MarketScreenerDTO.from_row(SCREENER_PAYLOAD)
    assert dto.sector == "Technology"


def test_screener_industry_maps_correctly() -> None:
    dto = MarketScreenerDTO.from_row(SCREENER_PAYLOAD)
    assert dto.industry == "Consumer Electronics"


def test_screener_country_maps_correctly() -> None:
    dto = MarketScreenerDTO.from_row(SCREENER_PAYLOAD)
    assert dto.country == "US"


def test_screener_to_dict_has_all_dimension_fields() -> None:
    dto = MarketScreenerDTO.from_row(SCREENER_PAYLOAD)
    result = dto.to_dict()
    assert result["exchange"] == "NASDAQ"
    assert result["sector"] == "Technology"
    assert result["industry"] == "Consumer Electronics"
    assert result["country"] == "US"
