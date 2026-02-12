"""Unit tests for DTOProjection class."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pandas as pd
import pytest

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.dtos.dto_projection import DTOProjection
from sbfoundation.dataset.models.dataset_schema import DatasetDtoSchema, SchemaColumn


# --- Test DTO classes ---


@dataclass(slots=True, kw_only=True, order=True)
class _SimpleDTO(BronzeToSilverDTO):
    ticker: str = "_none_"
    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    price: float | None = None
    count: int | None = None

    @classmethod
    def from_row(cls, row, ticker=None):
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self):
        return self.build_to_dict()


@dataclass(slots=True, kw_only=True, order=True)
class _DateDTO(BronzeToSilverDTO):
    ticker: str = "_none_"
    as_of_date: date | None = field(default=None, metadata={"api": "asOfDate"})
    created_at: datetime | None = field(default=None, metadata={"api": "createdAt"})

    @classmethod
    def from_row(cls, row, ticker=None):
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self):
        return self.build_to_dict()


@dataclass(slots=True, kw_only=True, order=True)
class _BoolDTO(BronzeToSilverDTO):
    ticker: str = "_none_"
    is_active: bool = field(default=False, metadata={"api": "isActive"})

    @classmethod
    def from_row(cls, row, ticker=None):
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self):
        return self.build_to_dict()


@dataclass(slots=True, kw_only=True, order=True)
class _ListDictDTO(BronzeToSilverDTO):
    ticker: str = "_none_"
    tags: list[str] = field(default_factory=list, metadata={"api": "tags"})
    metadata: dict[str, Any] = field(default_factory=dict, metadata={"api": "metadata"})

    @classmethod
    def from_row(cls, row, ticker=None):
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self):
        return self.build_to_dict()


# --- Fixtures ---


@pytest.fixture
def projection() -> DTOProjection:
    return DTOProjection()


# --- Tests for project() ---


class TestProjectBasic:
    def test_empty_dataframe_returns_empty(self, projection: DTOProjection) -> None:
        df = pd.DataFrame()
        result = projection.project(df, dto_type=_SimpleDTO)
        assert result.empty

    def test_project_with_dto_type(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({
            "companyName": ["Apple Inc", "Microsoft Corp"],
            "price": [150.0, 350.0],
            "count": [100, 200],
        })
        result = projection.project(df, dto_type=_SimpleDTO)

        assert len(result) == 2
        assert list(result.columns) == ["ticker", "company_name", "price", "count"]
        assert result.iloc[0]["company_name"] == "Apple Inc"
        assert result.iloc[1]["price"] == 350.0

    def test_project_with_ticker_override(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({
            "companyName": ["Apple Inc"],
            "price": [150.0],
        })
        result = projection.project(df, dto_type=_SimpleDTO, ticker_override="AAPL")

        assert result.iloc[0]["ticker"] == "AAPL"

    def test_project_missing_columns_filled_with_none(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({
            "companyName": ["Apple Inc"],
        })
        result = projection.project(df, dto_type=_SimpleDTO)

        assert result.iloc[0]["company_name"] == "Apple Inc"
        assert pd.isna(result.iloc[0]["price"]) or result.iloc[0]["price"] is None

    def test_project_requires_dto_type_or_schema(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({"col": [1]})
        with pytest.raises(ValueError, match="requires either dto_type or dto_schema"):
            projection.project(df)


class TestProjectWithSchema:
    def test_project_from_schema(self, projection: DTOProjection) -> None:
        schema = DatasetDtoSchema(
            dto_type=None,
            columns=(
                SchemaColumn(name="ticker", type="str", nullable=False),
                SchemaColumn(name="company_name", type="str", nullable=True),
                SchemaColumn(name="price", type="float", nullable=True),
            ),
        )
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "companyName": ["Apple Inc"],
            "price": [150.0],
        })
        result = projection.project(df, dto_schema=schema)

        assert list(result.columns) == ["ticker", "company_name", "price"]
        assert result.iloc[0]["ticker"] == "AAPL"
        assert result.iloc[0]["company_name"] == "Apple Inc"

    def test_project_from_schema_with_ticker_override(self, projection: DTOProjection) -> None:
        schema = DatasetDtoSchema(
            dto_type=None,
            columns=(
                SchemaColumn(name="ticker", type="str", nullable=False),
                SchemaColumn(name="value", type="int", nullable=True),
            ),
        )
        df = pd.DataFrame({
            "ticker": ["IGNORED"],
            "value": [42],
        })
        result = projection.project(df, dto_schema=schema, ticker_override="MSFT")

        assert result.iloc[0]["ticker"] == "MSFT"


# --- Tests for snake case conversion ---


class TestSnakeCaseColumns:
    def test_add_snake_case_columns(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({
            "companyName": ["Apple"],
            "fullTimeEmployees": [100000],
        })
        DTOProjection._add_snake_case_columns(df)

        assert "company_name" in df.columns
        assert "full_time_employees" in df.columns
        assert df["company_name"].iloc[0] == "Apple"

    def test_snake_case_does_not_override_existing(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({
            "companyName": ["CamelCase"],
            "company_name": ["SnakeCase"],
        })
        DTOProjection._add_snake_case_columns(df)

        assert df["company_name"].iloc[0] == "SnakeCase"


# --- Tests for type coercion ---


class TestCoerceSeriesStrings:
    def test_coerce_string(self, projection: DTOProjection) -> None:
        series = pd.Series([123, None, "text"])
        result = projection._coerce_series(series, str)

        assert result.iloc[0] == "123"
        assert result.iloc[1] == ""
        assert result.iloc[2] == "text"


class TestCoerceSeriesNumbers:
    def test_coerce_int(self, projection: DTOProjection) -> None:
        series = pd.Series(["100", 200.5, None])
        result = projection._coerce_series(series, int)

        assert result.iloc[0] == 100
        assert result.iloc[1] == 200
        assert pd.isna(result.iloc[2])

    def test_coerce_float(self, projection: DTOProjection) -> None:
        series = pd.Series(["3.14", 2, None])
        result = projection._coerce_series(series, float)

        assert result.iloc[0] == pytest.approx(3.14)
        assert result.iloc[1] == 2.0
        assert pd.isna(result.iloc[2])


class TestCoerceSeriesBool:
    def test_coerce_bool_true_values(self, projection: DTOProjection) -> None:
        series = pd.Series(["true", "T", "1", "yes", "Y", True, 1])
        result = projection._coerce_series(series, bool)

        for i in range(len(series)):
            assert result.iloc[i] == True  # noqa: E712 - comparing numpy bool

    def test_coerce_bool_false_values(self, projection: DTOProjection) -> None:
        series = pd.Series(["false", "F", "0", "no", "N", False, 0])
        result = projection._coerce_series(series, bool)

        for i in range(len(series)):
            assert result.iloc[i] == False  # noqa: E712 - comparing numpy bool

    def test_coerce_bool_none_returns_false(self, projection: DTOProjection) -> None:
        series = pd.Series([None])
        result = projection._coerce_series(series, bool)

        assert result.iloc[0] == False  # noqa: E712 - comparing numpy bool


class TestCoerceSeriesDates:
    def test_coerce_date(self, projection: DTOProjection) -> None:
        series = pd.Series(["2026-01-15", "2026-02-20", None])
        result = projection._coerce_series(series, date)

        assert pd.notna(result.iloc[0])
        assert pd.notna(result.iloc[1])
        assert pd.isna(result.iloc[2])

    def test_coerce_datetime(self, projection: DTOProjection) -> None:
        series = pd.Series(["2026-01-15 10:30:00", None])
        result = projection._coerce_series(series, datetime)

        assert pd.notna(result.iloc[0])
        assert pd.isna(result.iloc[1])


class TestCoerceSeriesCollections:
    def test_coerce_list_from_list(self, projection: DTOProjection) -> None:
        series = pd.Series([["a", "b"], None, "single"])
        result = projection._coerce_series(series, list[str])

        assert result.iloc[0] == ["a", "b"]
        assert result.iloc[1] == []
        assert result.iloc[2] == ["single"]

    def test_coerce_dict_from_dict(self, projection: DTOProjection) -> None:
        series = pd.Series([{"key": "value"}, None, "not a dict"])
        result = projection._coerce_series(series, dict[str, str])

        assert result.iloc[0] == {"key": "value"}
        assert result.iloc[1] == {}
        assert result.iloc[2] == {}


# --- Tests for schema-based coercion ---


class TestCoerceSchemaSeriesTypes:
    def test_coerce_schema_str(self, projection: DTOProjection) -> None:
        series = pd.Series(["hello", None])
        result = projection._coerce_schema_series(series, "str")

        assert result.iloc[0] == "hello"
        assert result.iloc[1] == ""

    def test_coerce_schema_int(self, projection: DTOProjection) -> None:
        series = pd.Series(["100", None])
        result = projection._coerce_schema_series(series, "int")

        assert result.iloc[0] == 100
        assert pd.isna(result.iloc[1])

    def test_coerce_schema_int64(self, projection: DTOProjection) -> None:
        series = pd.Series([9999999999999, None])
        result = projection._coerce_schema_series(series, "int64")

        assert result.iloc[0] == 9999999999999

    def test_coerce_schema_bigint(self, projection: DTOProjection) -> None:
        series = pd.Series([9999999999999, None])
        result = projection._coerce_schema_series(series, "bigint")

        assert result.iloc[0] == 9999999999999

    def test_coerce_schema_float(self, projection: DTOProjection) -> None:
        series = pd.Series(["3.14", None])
        result = projection._coerce_schema_series(series, "float")

        assert result.iloc[0] == pytest.approx(3.14)

    def test_coerce_schema_bool(self, projection: DTOProjection) -> None:
        series = pd.Series(["true", "false", None])
        result = projection._coerce_schema_series(series, "bool")

        assert result.iloc[0] == True  # noqa: E712 - comparing numpy bool
        assert result.iloc[1] == False  # noqa: E712 - comparing numpy bool
        assert result.iloc[2] == False  # noqa: E712 - comparing numpy bool

    def test_coerce_schema_date(self, projection: DTOProjection) -> None:
        series = pd.Series(["2026-01-15", None])
        result = projection._coerce_schema_series(series, "date")

        assert pd.notna(result.iloc[0])
        assert pd.isna(result.iloc[1])

    def test_coerce_schema_datetime_date(self, projection: DTOProjection) -> None:
        series = pd.Series(["2026-01-15", None])
        result = projection._coerce_schema_series(series, "datetime.date")

        assert pd.notna(result.iloc[0])

    def test_coerce_schema_datetime(self, projection: DTOProjection) -> None:
        series = pd.Series(["2026-01-15 10:30:00", None])
        result = projection._coerce_schema_series(series, "datetime")

        assert pd.notna(result.iloc[0])

    def test_coerce_schema_list(self, projection: DTOProjection) -> None:
        series = pd.Series([["a", "b"], None])
        result = projection._coerce_schema_series(series, "list")

        assert result.iloc[0] == ["a", "b"]
        assert result.iloc[1] == []

    def test_coerce_schema_dict(self, projection: DTOProjection) -> None:
        series = pd.Series([{"key": "value"}, None])
        result = projection._coerce_schema_series(series, "dict")

        assert result.iloc[0] == {"key": "value"}
        assert result.iloc[1] == {}


# --- Tests for normalize_type_hint ---


class TestNormalizeTypeHint:
    def test_normalize_simple_type(self) -> None:
        assert DTOProjection._normalize_type_hint("str") == "str"
        assert DTOProjection._normalize_type_hint("int") == "int"

    def test_normalize_nullable_type(self) -> None:
        assert DTOProjection._normalize_type_hint("str | None") == "str"
        assert DTOProjection._normalize_type_hint("int|None") == "int"

    def test_normalize_empty_string(self) -> None:
        assert DTOProjection._normalize_type_hint("") == ""

    def test_normalize_with_whitespace(self) -> None:
        assert DTOProjection._normalize_type_hint("  str  ") == "str"


# --- Tests for resolve_target_type ---


class TestResolveTargetType:
    def test_resolve_simple_type(self) -> None:
        assert DTOProjection._resolve_target_type(str) is str
        assert DTOProjection._resolve_target_type(int) is int

    def test_resolve_optional_type(self) -> None:
        from typing import Optional
        assert DTOProjection._resolve_target_type(Optional[str]) is str
        assert DTOProjection._resolve_target_type(str | None) is str


# --- Tests for _is_na ---


class TestIsNa:
    def test_none_is_na(self) -> None:
        assert DTOProjection._is_na(None) is True

    def test_nan_is_na(self) -> None:
        import math
        assert DTOProjection._is_na(float("nan")) is True
        assert DTOProjection._is_na(math.nan) is True

    def test_valid_values_not_na(self) -> None:
        assert DTOProjection._is_na(0) is False
        assert DTOProjection._is_na("") is False
        assert DTOProjection._is_na([]) is False
        assert DTOProjection._is_na({}) is False


# --- Tests for _coerce_bool ---


class TestCoerceBool:
    def test_coerce_bool_true_strings(self) -> None:
        for val in ["true", "TRUE", "True", "t", "T", "1", "yes", "YES", "y", "Y"]:
            assert DTOProjection._coerce_bool(val) is True

    def test_coerce_bool_false_strings(self) -> None:
        for val in ["false", "FALSE", "False", "f", "F", "0", "no", "NO", "n", "N"]:
            assert DTOProjection._coerce_bool(val) is False

    def test_coerce_bool_integers(self) -> None:
        assert DTOProjection._coerce_bool(1) is True
        assert DTOProjection._coerce_bool(0) is False
        assert DTOProjection._coerce_bool(42) is True

    def test_coerce_bool_floats(self) -> None:
        assert DTOProjection._coerce_bool(1.0) is True
        assert DTOProjection._coerce_bool(0.0) is False

    def test_coerce_bool_none_returns_false(self) -> None:
        assert DTOProjection._coerce_bool(None) is False

    def test_coerce_bool_nan_returns_false(self) -> None:
        assert DTOProjection._coerce_bool(float("nan")) is False

    def test_coerce_bool_invalid_string_returns_false(self) -> None:
        assert DTOProjection._coerce_bool("maybe") is False
        assert DTOProjection._coerce_bool("") is False


# --- Tests for _resolve_series ---


class TestResolveSeries:
    def test_resolve_by_api_key(self, projection: DTOProjection) -> None:
        @dataclass
        class _TestDTO:
            pass

        field_mock = type("Field", (), {"metadata": {"api": "apiKey"}, "name": "field_name"})()
        df = pd.DataFrame({"apiKey": [1, 2, 3]})

        result = DTOProjection._resolve_series(df, field_mock)
        assert list(result) == [1, 2, 3]

    def test_resolve_by_snake_case_api_key(self, projection: DTOProjection) -> None:
        field_mock = type("Field", (), {"metadata": {"api": "apiKeyName"}, "name": "field_name"})()
        df = pd.DataFrame({"api_key_name": [1, 2, 3]})

        result = DTOProjection._resolve_series(df, field_mock)
        assert list(result) == [1, 2, 3]

    def test_resolve_by_field_name(self, projection: DTOProjection) -> None:
        field_mock = type("Field", (), {"metadata": {}, "name": "field_name"})()
        df = pd.DataFrame({"field_name": [1, 2, 3]})

        result = DTOProjection._resolve_series(df, field_mock)
        assert list(result) == [1, 2, 3]

    def test_resolve_returns_none_when_not_found(self, projection: DTOProjection) -> None:
        field_mock = type("Field", (), {"metadata": {"api": "missing"}, "name": "also_missing"})()
        df = pd.DataFrame({"other_col": [1, 2, 3]})

        result = DTOProjection._resolve_series(df, field_mock)
        assert result is None


# --- Tests for _resolve_column_by_name ---


class TestResolveColumnByName:
    def test_resolve_exact_match(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({"ticker": ["AAPL"]})
        result = projection._resolve_column_by_name(df, "ticker")
        assert result.iloc[0] == "AAPL"

    def test_resolve_snake_to_camel(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({"companyName": ["Apple"]})
        result = projection._resolve_column_by_name(df, "company_name")
        assert result.iloc[0] == "Apple"

    def test_resolve_camel_to_snake(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({"company_name": ["Apple"]})
        result = projection._resolve_column_by_name(df, "companyName")
        assert result.iloc[0] == "Apple"

    def test_resolve_returns_none_series_when_not_found(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({"other": ["value"]})
        result = projection._resolve_column_by_name(df, "missing")
        assert result.iloc[0] is None


# --- Integration tests ---


class TestIntegrationWithRealDTO:
    def test_project_with_mixed_types(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({
            "companyName": ["Apple Inc"],
            "price": [150.50],  # Use numeric type directly
            "count": [1000],    # Use int type directly
        })
        result = projection.project(df, dto_type=_SimpleDTO, ticker_override="AAPL")

        assert result.iloc[0]["ticker"] == "AAPL"
        assert result.iloc[0]["company_name"] == "Apple Inc"
        assert result.iloc[0]["price"] == pytest.approx(150.50)
        assert result.iloc[0]["count"] == 1000

    def test_project_with_dates(self, projection: DTOProjection) -> None:
        df = pd.DataFrame({
            "asOfDate": ["2026-01-15"],
            "createdAt": ["2026-01-15 10:30:00"],
        })
        result = projection.project(df, dto_type=_DateDTO, ticker_override="TEST")

        assert pd.notna(result.iloc[0]["as_of_date"])
        assert pd.notna(result.iloc[0]["created_at"])

    def test_project_with_booleans(self, projection: DTOProjection) -> None:
        # Use actual boolean values - string coercion is tested in TestCoerceBool
        df = pd.DataFrame({
            "isActive": [True, False, True, False],
        })
        result = projection.project(df, dto_type=_BoolDTO)

        assert result.iloc[0]["is_active"] == True  # noqa: E712 - comparing numpy bool
        assert result.iloc[1]["is_active"] == False  # noqa: E712 - comparing numpy bool
        assert result.iloc[2]["is_active"] == True  # noqa: E712 - comparing numpy bool
        assert result.iloc[3]["is_active"] == False  # noqa: E712 - comparing numpy bool

    def test_project_preserves_dataframe_index(self, projection: DTOProjection) -> None:
        df = pd.DataFrame(
            {"companyName": ["A", "B", "C"]},
            index=[10, 20, 30],
        )
        result = projection.project(df, dto_type=_SimpleDTO)

        assert list(result.index) == [10, 20, 30]
