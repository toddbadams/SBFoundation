"""Unit tests for SilverService._promote_row and related helper methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest

from data_layer.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from data_layer.dtos.models import BronzeManifestRow
from data_layer.dataset.models.dataset_keymap import DatasetKeymap
from data_layer.dataset.models.dataset_keymap_entry import DatasetKeymapEntry
from data_layer.dataset.models.dataset_schema import DatasetDtoSchema, SchemaColumn
from data_layer.services.silver.silver_service import SilverService
from data_layer.services.bronze.bronze_batch_reader import BronzeBatchItem
from data_layer.run.dtos.run_result import RunResult
from data_layer.run.services.chunk_engine import Chunk


# --- Test DTO ---


@dataclass(slots=True, kw_only=True, order=True)
class _TestDTO(BronzeToSilverDTO):
    ticker: str = "_none_"
    company_name: str | None = field(default=None, metadata={"api": "companyName"})
    as_of_date: date | None = field(default=None, metadata={"api": "asOfDate"})

    @classmethod
    def from_row(cls, row, ticker=None):
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self):
        return self.build_to_dict()


# --- Fixtures and Helpers ---


def _make_manifest_row(
    dataset: str = "company-profile",
    ticker: str = "AAPL",
    domain: str = "company",
    source: str = "fmp",
    discriminator: str = "",
    bronze_file_id: int = 1,
    run_id: str = "run-123",
    file_path_rel: str = "bronze/test.json",
) -> BronzeManifestRow:
    return BronzeManifestRow(
        bronze_file_id=bronze_file_id,
        run_id=run_id,
        domain=domain,
        source=source,
        dataset=dataset,
        discriminator=discriminator,
        ticker=ticker,
        file_path_rel=file_path_rel,
        coverage_from_date=date(2026, 1, 1),
        coverage_to_date=date(2026, 1, 15),
        ingested_at=datetime(2026, 1, 27, 12, 0),
    )


def _make_keymap_entry(
    dataset: str = "company-profile",
    silver_table: str = "company_profile",
    ticker_scope: str = "per_ticker",
    key_cols: tuple[str, ...] = ("ticker", "as_of_date"),
    row_date_col: str | None = "as_of_date",
    dto_schema: DatasetDtoSchema | None = None,
) -> DatasetKeymapEntry:
    return DatasetKeymapEntry(
        domain="company",
        source="fmp",
        dataset=dataset,
        discriminator="",
        ticker_scope=ticker_scope,
        silver_schema="silver",
        silver_table=silver_table,
        key_cols=key_cols,
        row_date_col=row_date_col,
        dto_schema=dto_schema,
    )


def _make_keymap(*entries: DatasetKeymapEntry) -> DatasetKeymap:
    return DatasetKeymap(version=1, entries=entries)


# --- Tests for _resolve_keymap_entry ---


class TestResolveKeymapEntry:
    def test_finds_exact_match(self) -> None:
        entry = _make_keymap_entry(dataset="company-profile")
        keymap = _make_keymap(entry)
        row = _make_manifest_row(dataset="company-profile", ticker="AAPL")

        service = object.__new__(SilverService)
        result = service._resolve_keymap_entry(row, keymap)

        assert result.dataset == "company-profile"

    def test_finds_match_without_ticker(self) -> None:
        entry = _make_keymap_entry(dataset="company-profile")
        keymap = _make_keymap(entry)
        row = _make_manifest_row(dataset="company-profile", ticker="AAPL")

        service = object.__new__(SilverService)
        result = service._resolve_keymap_entry(row, keymap)

        assert result is not None

    def test_raises_for_missing_entry(self) -> None:
        keymap = _make_keymap()
        row = _make_manifest_row(dataset="unknown-dataset")

        service = object.__new__(SilverService)
        with pytest.raises(KeyError, match="Missing dataset keymap entry"):
            service._resolve_keymap_entry(row, keymap)

    def test_raises_when_ticker_required_but_missing(self) -> None:
        entry = _make_keymap_entry(dataset="company-profile", ticker_scope="per_ticker")
        keymap = _make_keymap(entry)
        row = _make_manifest_row(dataset="company-profile", ticker="")

        service = object.__new__(SilverService)
        with pytest.raises(KeyError):
            service._resolve_keymap_entry(row, keymap)


# --- Tests for _ensure_row_date ---


class TestEnsureRowDate:
    def test_adds_row_date_column_if_missing(self) -> None:
        df = pd.DataFrame({"ticker": ["AAPL"]})
        row = _make_manifest_row()

        service = object.__new__(SilverService)
        service._ensure_row_date(df, "as_of_date", row)

        assert "as_of_date" in df.columns
        assert pd.notna(df["as_of_date"].iloc[0])

    def test_converts_existing_column_to_datetime(self) -> None:
        df = pd.DataFrame({"as_of_date": ["2026-01-15"]})
        row = _make_manifest_row()

        service = object.__new__(SilverService)
        service._ensure_row_date(df, "as_of_date", row)

        assert pd.api.types.is_datetime64_any_dtype(df["as_of_date"])

    def test_uses_coverage_to_date_as_fallback(self) -> None:
        df = pd.DataFrame({"ticker": ["AAPL"]})
        row = BronzeManifestRow(
            bronze_file_id=1,
            run_id="run-123",
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="AAPL",
            file_path_rel="test.json",
            coverage_from_date=date(2026, 1, 1),
            coverage_to_date=date(2026, 1, 15),
            ingested_at=datetime(2026, 1, 27, 12, 0),
        )

        service = object.__new__(SilverService)
        service._ensure_row_date(df, "as_of_date", row)

        # Should use coverage_to_date as fallback, converted to datetime
        assert pd.to_datetime(df["as_of_date"].iloc[0]).date() == row.coverage_to_date


# --- Tests for _coerce_numeric_columns ---


class TestCoerceNumericColumns:
    def test_coerces_string_to_float(self) -> None:
        df = pd.DataFrame({"market_cap": ["1000000", "2000000"]})

        service = object.__new__(SilverService)
        service._coerce_numeric_columns(df, ["market_cap"])

        assert df["market_cap"].dtype == "float64"
        assert df["market_cap"].iloc[0] == 1000000.0

    def test_handles_invalid_values(self) -> None:
        df = pd.DataFrame({"market_cap": ["invalid", "1000"]})

        service = object.__new__(SilverService)
        service._coerce_numeric_columns(df, ["market_cap"])

        assert pd.isna(df["market_cap"].iloc[0])
        assert df["market_cap"].iloc[1] == 1000.0

    def test_skips_missing_columns(self) -> None:
        df = pd.DataFrame({"other_col": [1, 2]})

        service = object.__new__(SilverService)
        service._coerce_numeric_columns(df, ["market_cap"])

        assert "market_cap" not in df.columns


# --- Tests for _ensure_key_cols_df ---


class TestEnsureKeyColsDf:
    def test_passes_when_all_key_cols_present(self) -> None:
        df = pd.DataFrame({"ticker": ["AAPL"], "as_of_date": [date(2026, 1, 15)]})
        row = _make_manifest_row()

        service = object.__new__(SilverService)
        service._ensure_key_cols_df(df, ("ticker", "as_of_date"), row)

    def test_raises_when_key_cols_missing(self) -> None:
        df = pd.DataFrame({"ticker": ["AAPL"]})
        row = _make_manifest_row()

        service = object.__new__(SilverService)
        with pytest.raises(ValueError, match="missing key columns"):
            service._ensure_key_cols_df(df, ("ticker", "as_of_date"), row)


# --- Tests for _apply_watermark ---


class TestApplyWatermark:
    def test_filters_rows_older_than_watermark(self) -> None:
        df = pd.DataFrame({
            "as_of_date": ["2026-01-01", "2026-01-10", "2026-01-15"],
            "value": [1, 2, 3],
        })

        result = SilverService._apply_watermark(df, "as_of_date", date(2026, 1, 10))

        assert len(result) == 1
        assert result.iloc[0]["value"] == 3

    def test_returns_empty_when_all_filtered(self) -> None:
        df = pd.DataFrame({
            "as_of_date": ["2026-01-01", "2026-01-05"],
            "value": [1, 2],
        })

        result = SilverService._apply_watermark(df, "as_of_date", date(2026, 1, 10))

        # All rows are older than watermark
        assert len(result) == 0

    def test_returns_df_unchanged_when_column_missing(self) -> None:
        df = pd.DataFrame({"value": [1, 2, 3]})

        result = SilverService._apply_watermark(df, "as_of_date", date(2026, 1, 10))

        assert len(result) == 3


# --- Tests for _coverage_dates ---


class TestCoverageDates:
    def test_extracts_min_max_dates(self) -> None:
        df = pd.DataFrame({
            "as_of_date": ["2026-01-05", "2026-01-15", "2026-01-10"],
        })

        min_date, max_date = SilverService._coverage_dates(df, "as_of_date")

        assert min_date == date(2026, 1, 5)
        assert max_date == date(2026, 1, 15)

    def test_returns_none_when_column_missing(self) -> None:
        df = pd.DataFrame({"other": [1, 2, 3]})

        min_date, max_date = SilverService._coverage_dates(df, "as_of_date")

        assert min_date is None
        assert max_date is None

    def test_returns_none_for_empty_df(self) -> None:
        df = pd.DataFrame({"as_of_date": []})

        min_date, max_date = SilverService._coverage_dates(df, "as_of_date")

        assert min_date is None
        assert max_date is None


# --- Tests for SQL identifier helpers ---


class TestQuoteIdent:
    def test_quotes_simple_name(self) -> None:
        result = SilverService._quote_ident("table_name")
        assert result == '"table_name"'

    def test_escapes_quotes_in_name(self) -> None:
        result = SilverService._quote_ident('table"name')
        assert result == '"table""name"'


class TestQualifiedTable:
    def test_creates_qualified_name(self) -> None:
        service = object.__new__(SilverService)
        result = service._qualified_table("silver", "company_profile")
        assert result == '"silver"."company_profile"'


class TestQualifiedIdent:
    def test_creates_qualified_column(self) -> None:
        service = object.__new__(SilverService)
        result = service._qualified_ident("t", "column_name")
        assert result == 't."column_name"'


# --- Tests for _table_exists ---


class TestTableExists:
    def test_returns_true_when_table_exists(self) -> None:
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE SCHEMA silver")
        conn.execute("CREATE TABLE silver.test_table (id INTEGER)")

        result = SilverService._table_exists(conn, "silver", "test_table")

        assert result is True
        conn.close()

    def test_returns_false_when_table_missing(self) -> None:
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE SCHEMA silver")

        result = SilverService._table_exists(conn, "silver", "nonexistent")

        assert result is False
        conn.close()


# --- Tests for _merge_rows ---


class TestMergeRows:
    def test_creates_table_when_not_exists(self) -> None:
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE SCHEMA silver")

        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "company_name": ["Apple Inc"],
        })
        entry = _make_keymap_entry(key_cols=("ticker",))

        service = object.__new__(SilverService)
        service._merge_rows(conn, entry, df, table_exists=False)

        result = conn.execute('SELECT * FROM silver."company_profile"').fetchall()
        assert len(result) == 1
        assert result[0][0] == "AAPL"
        conn.close()

    def test_merges_into_existing_table(self) -> None:
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE SCHEMA silver")
        conn.execute('CREATE TABLE silver."company_profile" (ticker VARCHAR, company_name VARCHAR)')
        conn.execute("INSERT INTO silver.company_profile VALUES ('AAPL', 'Apple Old')")

        df = pd.DataFrame({
            "ticker": ["AAPL", "MSFT"],
            "company_name": ["Apple New", "Microsoft"],
        })
        entry = _make_keymap_entry(key_cols=("ticker",))

        service = object.__new__(SilverService)
        service._merge_rows(conn, entry, df, table_exists=True)

        result = conn.execute('SELECT * FROM silver."company_profile" ORDER BY ticker').fetchall()
        assert len(result) == 2
        # AAPL should be updated
        aapl = [r for r in result if r[0] == "AAPL"][0]
        assert aapl[1] == "Apple New"
        conn.close()

    def test_handles_empty_dataframe(self) -> None:
        conn = duckdb.connect(":memory:")
        df = pd.DataFrame()
        entry = _make_keymap_entry()

        service = object.__new__(SilverService)
        service._merge_rows(conn, entry, df, table_exists=True)
        # Should complete without error
        conn.close()


# --- Tests for _resolve_dto_type ---


class TestResolveDtoType:
    def test_gets_dto_from_request(self) -> None:
        request_mock = MagicMock()
        request_mock.dto_type = _TestDTO
        result_mock = MagicMock(spec=RunResult)
        result_mock.request = request_mock

        row = _make_manifest_row()
        service = object.__new__(SilverService)

        dto_type = service._resolve_dto_type(row, result_mock)
        assert dto_type is _TestDTO

    def test_falls_back_to_registry(self) -> None:
        result_mock = MagicMock(spec=RunResult)
        result_mock.request = None

        row = _make_manifest_row(dataset="company-profile")
        service = object.__new__(SilverService)

        # Should either get from registry or raise ValueError
        with patch("data_layer.services.silver.silver_service.DTO_REGISTRY", {"company-profile": _TestDTO}):
            dto_type = service._resolve_dto_type(row, result_mock)
            assert dto_type is _TestDTO

    def test_raises_for_missing_dto(self) -> None:
        result_mock = MagicMock(spec=RunResult)
        result_mock.request = None

        row = _make_manifest_row(dataset="unknown-dataset")
        service = object.__new__(SilverService)

        with patch("data_layer.services.silver.silver_service.DTO_REGISTRY", {}):
            with pytest.raises(ValueError, match="Missing DTO mapping"):
                service._resolve_dto_type(row, result_mock)


# --- Integration test for _promote_row ---


class TestPromoteRowIntegration:
    @pytest.fixture
    def mock_silver_service(self) -> SilverService:
        """Create a SilverService with mocked dependencies."""
        service = object.__new__(SilverService)
        service._logger = MagicMock()
        service._bootstrap = MagicMock()
        service._owns_bootstrap = False
        service._result_file_adapter = MagicMock()
        service._promotion_config = MagicMock()
        service._promotion_config.watermark_mode = "none"
        service._bronze_batch_reader = MagicMock()
        service._dto_projection = MagicMock()
        service._chunk_engine = MagicMock()
        service._dedupe_engine = MagicMock()
        service._ops_service = MagicMock()
        service._owns_ops_service = False
        service._instrument_promotion_service = MagicMock()
        service._instrument_resolver = MagicMock()
        # Default to returning an instrument_sk for ENRICH behavior tests
        service._instrument_resolver.resolve.return_value = 1
        return service

    def test_promote_row_empty_projection_returns_zeros(self, mock_silver_service: SilverService) -> None:
        """Test that empty projection returns (0, 0, None, None, '')."""
        # Use dto_schema instead of dto_type to bypass DTO registry lookup
        entry = _make_keymap_entry(
            dto_schema=DatasetDtoSchema(
                dto_type=None,
                columns=(
                    SchemaColumn(name="ticker", type="str", nullable=False),
                    SchemaColumn(name="company_name", type="str", nullable=True),
                ),
            )
        )
        keymap = _make_keymap(entry)
        row = _make_manifest_row()

        # Setup mocks
        batch_item = MagicMock(spec=BronzeBatchItem)
        batch_item.df_content = pd.DataFrame()
        batch_item.result = MagicMock()
        mock_silver_service._bronze_batch_reader.read.return_value = batch_item
        mock_silver_service._dto_projection.project.return_value = pd.DataFrame()

        rows_seen, rows_written, coverage_from, coverage_to, table_name = mock_silver_service._promote_row(row, keymap)

        assert rows_seen == 0
        assert rows_written == 0
        assert coverage_from is None
        assert coverage_to is None
        assert table_name == ""

    def test_promote_row_processes_data(self, mock_silver_service: SilverService) -> None:
        """Test that promote_row processes data through the full pipeline."""
        entry = _make_keymap_entry(
            dto_schema=DatasetDtoSchema(
                dto_type=None,
                columns=(
                    SchemaColumn(name="ticker", type="str", nullable=False),
                    SchemaColumn(name="company_name", type="str", nullable=True),
                    SchemaColumn(name="as_of_date", type="date", nullable=True),
                ),
            )
        )
        keymap = _make_keymap(entry)
        row = _make_manifest_row()

        # Setup mocks
        batch_item = MagicMock(spec=BronzeBatchItem)
        batch_item.df_content = pd.DataFrame({
            "ticker": ["AAPL"],
            "companyName": ["Apple Inc"],
            "asOfDate": ["2026-01-15"],
        })
        batch_item.result = MagicMock()
        mock_silver_service._bronze_batch_reader.read.return_value = batch_item

        projected_df = pd.DataFrame({
            "ticker": ["AAPL"],
            "company_name": ["Apple Inc"],
            "as_of_date": pd.to_datetime(["2026-01-15"]),
        })
        mock_silver_service._dto_projection.project.return_value = projected_df

        mock_silver_service._ops_service.get_silver_watermark.return_value = None

        # Mock DuckDB connection
        mock_conn = MagicMock()
        mock_silver_service._bootstrap.connect.return_value = mock_conn
        mock_silver_service._bootstrap.silver_transaction.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_silver_service._bootstrap.silver_transaction.return_value.__exit__ = MagicMock(return_value=False)

        # Mock dedupe to return the same df
        mock_silver_service._dedupe_engine.dedupe_against_table.return_value = projected_df

        # Mock chunk engine to yield single chunk
        mock_silver_service._chunk_engine.chunk.return_value = iter([Chunk(key="all", df=projected_df)])

        # Need to patch _table_exists and _merge_rows
        with patch.object(mock_silver_service, "_table_exists", return_value=False):
            with patch.object(mock_silver_service, "_merge_rows"):
                rows_seen, rows_written, coverage_from, coverage_to, table_name = mock_silver_service._promote_row(row, keymap)

        assert rows_seen == 1
        assert rows_written == 1
        assert table_name == '"silver"."company_profile"'
