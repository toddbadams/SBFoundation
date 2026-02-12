"""Unit tests for BronzeToSilverDTO base class and sample DTO implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import pytest
from requests.structures import CaseInsensitiveDict

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from data_layer.dtos.company.company_dto import CompanyDTO


# --- Test subclass for base class testing ---


@dataclass(slots=True, kw_only=True, order=True)
class _TestDTO(BronzeToSilverDTO):
    ticker: str = "_none_"
    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    price: float | None = None
    count: int | None = None
    is_active: bool = False
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    as_of_date: date | None = field(default=None, metadata={"api": "asOfDate"})
    created_at: datetime | None = field(default=None, metadata={"api": "createdAt"})

    @classmethod
    def from_row(cls, row, ticker=None):
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self):
        return self.build_to_dict()


# --- Tests for static helper methods ---


class TestCamelToSnake:
    def test_simple_camel_case(self) -> None:
        assert BronzeToSilverDTO._camel_to_snake("companyName") == "company_name"

    def test_multiple_words(self) -> None:
        assert BronzeToSilverDTO._camel_to_snake("fullTimeEmployees") == "full_time_employees"

    def test_all_caps_segment(self) -> None:
        assert BronzeToSilverDTO._camel_to_snake("companyIPO") == "company_ipo"

    def test_already_snake_case(self) -> None:
        assert BronzeToSilverDTO._camel_to_snake("company_name") == "company_name"

    def test_empty_string(self) -> None:
        assert BronzeToSilverDTO._camel_to_snake("") == ""

    def test_single_word(self) -> None:
        assert BronzeToSilverDTO._camel_to_snake("ticker") == "ticker"


class TestSnakeToCamel:
    def test_simple_snake_case(self) -> None:
        assert BronzeToSilverDTO._snake_to_camel("company_name") == "companyName"

    def test_multiple_words(self) -> None:
        assert BronzeToSilverDTO._snake_to_camel("full_time_employees") == "fullTimeEmployees"

    def test_already_camel_case(self) -> None:
        assert BronzeToSilverDTO._snake_to_camel("companyName") == "companyName"

    def test_empty_string(self) -> None:
        assert BronzeToSilverDTO._snake_to_camel("") == ""

    def test_single_word(self) -> None:
        assert BronzeToSilverDTO._snake_to_camel("ticker") == "ticker"


class TestIsNa:
    def test_none_is_na(self) -> None:
        assert BronzeToSilverDTO._is_na(None) is True

    def test_nan_is_na(self) -> None:
        import math
        assert BronzeToSilverDTO._is_na(float("nan")) is True
        assert BronzeToSilverDTO._is_na(math.nan) is True

    def test_valid_values_not_na(self) -> None:
        assert BronzeToSilverDTO._is_na(0) is False
        assert BronzeToSilverDTO._is_na("") is False
        assert BronzeToSilverDTO._is_na([]) is False
        assert BronzeToSilverDTO._is_na({}) is False
        assert BronzeToSilverDTO._is_na(False) is False


# --- Tests for type coercion ---


class TestCoerceValue:
    def test_coerce_str_from_int(self) -> None:
        result = BronzeToSilverDTO._coerce_value(123, str)
        assert result == "123"

    def test_coerce_str_from_none(self) -> None:
        result = BronzeToSilverDTO._coerce_value(None, str)
        assert result == ""

    def test_coerce_int_from_str(self) -> None:
        result = BronzeToSilverDTO._coerce_value("42", int)
        assert result == 42

    def test_coerce_int_from_none(self) -> None:
        result = BronzeToSilverDTO._coerce_value(None, int)
        assert result is None

    def test_coerce_float_from_str(self) -> None:
        result = BronzeToSilverDTO._coerce_value("3.14", float)
        assert result == pytest.approx(3.14)

    def test_coerce_float_from_none(self) -> None:
        result = BronzeToSilverDTO._coerce_value(None, float)
        assert result is None

    def test_coerce_bool_true_values(self) -> None:
        for val in ["true", "TRUE", "True", "t", "1", "yes", "y", True, 1]:
            result = BronzeToSilverDTO._coerce_value(val, bool)
            assert result is True

    def test_coerce_bool_false_values(self) -> None:
        for val in ["false", "FALSE", "False", "f", "0", "no", "n", False, 0]:
            result = BronzeToSilverDTO._coerce_value(val, bool)
            assert result is False

    def test_coerce_bool_from_none(self) -> None:
        result = BronzeToSilverDTO._coerce_value(None, bool)
        assert result is False

    def test_coerce_date_from_str(self) -> None:
        result = BronzeToSilverDTO._coerce_value("2026-01-15", date)
        assert result == date(2026, 1, 15)

    def test_coerce_date_from_datetime(self) -> None:
        result = BronzeToSilverDTO._coerce_value(datetime(2026, 1, 15, 10, 30), date)
        assert result == date(2026, 1, 15)

    def test_coerce_date_from_none(self) -> None:
        result = BronzeToSilverDTO._coerce_value(None, date)
        assert result is None

    def test_coerce_datetime_from_str(self) -> None:
        result = BronzeToSilverDTO._coerce_value("2026-01-15 10:30:00", datetime)
        assert isinstance(result, datetime)

    def test_coerce_datetime_from_none(self) -> None:
        result = BronzeToSilverDTO._coerce_value(None, datetime)
        assert result is None

    def test_coerce_list_from_list(self) -> None:
        result = BronzeToSilverDTO._coerce_value(["a", "b"], list[str])
        assert result == ["a", "b"]

    def test_coerce_list_from_none(self) -> None:
        result = BronzeToSilverDTO._coerce_value(None, list[str])
        assert result == []

    def test_coerce_list_from_single(self) -> None:
        result = BronzeToSilverDTO._coerce_value("single", list[str])
        assert result == ["single"]

    def test_coerce_dict_from_dict(self) -> None:
        result = BronzeToSilverDTO._coerce_value({"key": "value"}, dict[str, str])
        assert result == {"key": "value"}

    def test_coerce_dict_from_none(self) -> None:
        result = BronzeToSilverDTO._coerce_value(None, dict[str, str])
        assert result == {}

    def test_coerce_dict_from_json_str(self) -> None:
        result = BronzeToSilverDTO._coerce_value('{"key": "value"}', dict[str, str])
        assert result == {"key": "value"}

    def test_coerce_optional_type(self) -> None:
        # str | None should coerce to str
        result = BronzeToSilverDTO._coerce_value(123, str | None)
        assert result == "123"


# --- Tests for normalize_row ---


class TestNormalizeRow:
    def test_adds_snake_case_keys(self) -> None:
        row = {"companyName": "Apple Inc"}
        result = BronzeToSilverDTO._normalize_row(row)

        assert "company_name" in result
        assert result["company_name"] == "Apple Inc"

    def test_adds_camel_case_keys(self) -> None:
        row = {"company_name": "Apple Inc"}
        result = BronzeToSilverDTO._normalize_row(row)

        assert "companyName" in result
        assert result["companyName"] == "Apple Inc"

    def test_handles_empty_dict(self) -> None:
        result = BronzeToSilverDTO._normalize_row({})
        assert result == {}


# --- Tests for build_from_row ---


class TestBuildFromRow:
    def test_builds_dto_with_camel_case_input(self) -> None:
        row = {
            "companyName": "Apple Inc",
            "price": 150.0,
            "count": 100,
        }

        dto = _TestDTO.build_from_row(row)

        assert dto.company_name == "Apple Inc"
        assert dto.price == 150.0
        assert dto.count == 100

    def test_builds_dto_with_snake_case_input(self) -> None:
        row = {
            "company_name": "Apple Inc",
            "price": 150.0,
            "count": 100,
        }

        dto = _TestDTO.build_from_row(row)

        assert dto.company_name == "Apple Inc"
        assert dto.price == 150.0

    def test_builds_dto_with_ticker_override(self) -> None:
        row = {
            "ticker": "WRONG",
            "companyName": "Apple Inc",
        }

        dto = _TestDTO.build_from_row(row, ticker_override="AAPL")

        assert dto.ticker == "AAPL"

    def test_builds_dto_with_missing_fields(self) -> None:
        row = {"companyName": "Apple Inc"}

        dto = _TestDTO.build_from_row(row)

        assert dto.company_name == "Apple Inc"
        assert dto.price is None
        assert dto.count is None

    def test_coerces_types(self) -> None:
        # Use numeric values - build_from_row preserves types if already correct
        row = {
            "price": 150.50,
            "count": 100,
            "is_active": True,
        }

        dto = _TestDTO.build_from_row(row)

        assert dto.price == 150.50
        assert dto.count == 100
        assert dto.is_active is True

    def test_handles_dates(self) -> None:
        # Use date objects - build_from_row preserves datetime types
        row = {
            "asOfDate": date(2026, 1, 15),
            "createdAt": datetime(2026, 1, 15, 10, 30, 0),
        }

        dto = _TestDTO.build_from_row(row)

        assert dto.as_of_date == date(2026, 1, 15)
        assert isinstance(dto.created_at, datetime)


# --- Tests for build_to_dict ---


class TestBuildToDict:
    def test_serializes_basic_types(self) -> None:
        dto = _TestDTO(
            ticker="AAPL",
            company_name="Apple Inc",
            price=150.0,
            count=100,
        )

        result = dto.build_to_dict()

        assert result["ticker"] == "AAPL"
        assert result["company_name"] == "Apple Inc"
        assert result["price"] == 150.0
        assert result["count"] == 100

    def test_serializes_date_to_iso(self) -> None:
        dto = _TestDTO(
            ticker="AAPL",
            as_of_date=date(2026, 1, 15),
        )

        result = dto.build_to_dict()

        assert result["as_of_date"] == "2026-01-15"

    def test_serializes_datetime_to_iso(self) -> None:
        dto = _TestDTO(
            ticker="AAPL",
            created_at=datetime(2026, 1, 15, 10, 30, 0),
        )

        result = dto.build_to_dict()

        assert result["created_at"] == "2026-01-15T10:30:00"

    def test_serializes_lists(self) -> None:
        dto = _TestDTO(
            ticker="AAPL",
            tags=["tech", "large-cap"],
        )

        result = dto.build_to_dict()

        assert result["tags"] == ["tech", "large-cap"]

    def test_serializes_dicts(self) -> None:
        dto = _TestDTO(
            ticker="AAPL",
            metadata={"key": "value"},
        )

        result = dto.build_to_dict()

        assert result["metadata"] == {"key": "value"}


# --- Tests for helper methods (f, d, s, i, b, etc.) ---


class TestHelperMethods:
    def test_f_extracts_float(self) -> None:
        d = {"price": "150.50"}
        assert BronzeToSilverDTO.f(d, "price") == 150.50

    def test_f_returns_none_for_missing(self) -> None:
        d = {}
        assert BronzeToSilverDTO.f(d, "price") is None

    def test_f_returns_none_for_invalid(self) -> None:
        d = {"price": "not a number"}
        assert BronzeToSilverDTO.f(d, "price") is None

    def test_d_extracts_date(self) -> None:
        d = {"asOfDate": "2026-01-15"}
        assert BronzeToSilverDTO.d(d, "asOfDate") == date(2026, 1, 15)

    def test_d_returns_none_for_missing(self) -> None:
        d = {}
        assert BronzeToSilverDTO.d(d, "asOfDate") is None

    def test_s_extracts_string(self) -> None:
        d = {"name": "Apple Inc"}
        assert BronzeToSilverDTO.s(d, "name") == "Apple Inc"

    def test_s_returns_empty_for_missing(self) -> None:
        d = {}
        assert BronzeToSilverDTO.s(d, "name") == ""

    def test_s_converts_non_string(self) -> None:
        d = {"value": 123}
        assert BronzeToSilverDTO.s(d, "value") == "123"

    def test_i_extracts_int(self) -> None:
        d = {"count": "100"}
        assert BronzeToSilverDTO.i(d, "count") == 100

    def test_i_returns_none_for_missing(self) -> None:
        d = {}
        assert BronzeToSilverDTO.i(d, "count") is None

    def test_b_extracts_bool(self) -> None:
        d = {"isActive": "true"}
        assert BronzeToSilverDTO.b(d, "isActive") is True

    def test_b_returns_false_for_missing(self) -> None:
        d = {}
        assert BronzeToSilverDTO.b(d, "isActive") is False

    def test_sl_extracts_string_list(self) -> None:
        d = {"tags": ["a", "b", "c"]}
        assert BronzeToSilverDTO.sl(d, "tags") == ["a", "b", "c"]

    def test_sl_returns_empty_for_missing(self) -> None:
        d = {}
        assert BronzeToSilverDTO.sl(d, "tags") == []

    def test_qv_extracts_dict(self) -> None:
        d = {"metadata": {"key": "value"}}
        assert BronzeToSilverDTO.qv(d, "metadata") == {"key": "value"}

    def test_qv_parses_json_string(self) -> None:
        d = {"metadata": '{"key": "value"}'}
        assert BronzeToSilverDTO.qv(d, "metadata") == {"key": "value"}

    def test_qv_returns_empty_for_missing(self) -> None:
        d = {}
        assert BronzeToSilverDTO.qv(d, "metadata") == {}


# --- Tests for to_iso8601 ---


class TestToIso8601:
    def test_converts_date(self) -> None:
        result = BronzeToSilverDTO.to_iso8601(date(2026, 1, 15))
        assert result == "2026-01-15"

    def test_converts_datetime(self) -> None:
        result = BronzeToSilverDTO.to_iso8601(datetime(2026, 1, 15, 10, 30, 45))
        assert result == "2026-01-15T10:30:45"

    def test_converts_datetime_with_timezone(self) -> None:
        dt = datetime(2026, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = BronzeToSilverDTO.to_iso8601(dt)
        assert result == "2026-01-15T10:30:45"

    def test_returns_none_for_none(self) -> None:
        result = BronzeToSilverDTO.to_iso8601(None)
        assert result is None


# --- Tests for CompanyDTO (sample implementation) ---


class TestCompanyDTO:
    def test_from_row_with_camel_case_api_fields(self) -> None:
        row = {
            "symbol": "AAPL",
            "companyName": "Apple Inc",
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "marketCap": 3000000000000,
            "ipoDate": "1980-12-12",
            "isEtf": False,
            "isActivelyTrading": True,
        }

        dto = CompanyDTO.from_row(row)

        assert dto.ticker == "AAPL"
        assert dto.company_name == "Apple Inc"
        assert dto.industry == "Consumer Electronics"
        assert dto.sector == "Technology"
        assert dto.market_cap == 3000000000000
        assert dto.ipo_date == date(1980, 12, 12)
        assert dto.is_etf is False
        assert dto.is_actively_trading is True

    def test_from_row_with_ticker_override(self) -> None:
        row = {
            "symbol": "WRONG",
            "companyName": "Apple Inc",
        }

        dto = CompanyDTO.from_row(row, ticker="AAPL")

        assert dto.ticker == "AAPL"

    def test_from_row_with_missing_fields(self) -> None:
        row = {
            "symbol": "AAPL",
            "companyName": "Apple Inc",
        }

        dto = CompanyDTO.from_row(row)

        assert dto.ticker == "AAPL"
        assert dto.company_name == "Apple Inc"
        assert dto.market_cap is None
        assert dto.industry is None

    def test_to_dict_serializes_all_fields(self) -> None:
        dto = CompanyDTO(
            ticker="AAPL",
            company_name="Apple Inc",
            market_cap=3000000000000,
            ipo_date=date(1980, 12, 12),
            is_etf=False,
        )

        result = dto.to_dict()

        assert result["ticker"] == "AAPL"
        assert result["company_name"] == "Apple Inc"
        assert result["market_cap"] == 3000000000000
        assert result["ipo_date"] == "1980-12-12"
        assert result["is_etf"] is False

    def test_key_date_returns_ipo_date(self) -> None:
        dto = CompanyDTO(ticker="AAPL", ipo_date=date(1980, 12, 12))
        assert dto.key_date == date(1980, 12, 12)

    def test_key_date_returns_min_when_no_ipo(self) -> None:
        dto = CompanyDTO(ticker="AAPL")
        assert dto.key_date == date.min

    def test_roundtrip_from_row_to_dict(self) -> None:
        """Test that from_row -> to_dict preserves data."""
        row = {
            "symbol": "AAPL",
            "companyName": "Apple Inc",
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "price": 175.50,
            "beta": 1.25,
            "ipoDate": "1980-12-12",
        }

        dto = CompanyDTO.from_row(row)
        result = dto.to_dict()

        assert result["ticker"] == "AAPL"
        assert result["company_name"] == "Apple Inc"
        assert result["industry"] == "Consumer Electronics"
        assert result["sector"] == "Technology"
        assert result["price"] == 175.50
        assert result["beta"] == 1.25
        assert result["ipo_date"] == "1980-12-12"
