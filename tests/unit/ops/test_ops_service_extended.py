"""Extended unit tests for OpsService methods not covered in test_ops_service.py."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from data_layer.dataset.models.dataset_identity import DatasetIdentity
from data_layer.ops.dtos.file_injestion import DatasetInjestion
from data_layer.ops.services.ops_service import OpsService


# --- Stub classes ---


class _StubUniverse:
    def __init__(self) -> None:
        self._now = datetime(2026, 1, 27, 12, 0)

    def now(self) -> datetime:
        return self._now

    def today(self) -> date:
        return self._now.date()

    def run_id(self) -> str:
        return "stub-run"

    def update_tickers(self, *, start: int = 0, limit: int = 50, instrument_type: str | None = None, is_active: bool = True) -> list[str]:
        return [f"T{i}" for i in range(start, start + limit)]

    def new_tickers(self, *, start: int = 0, limit: int = 50, instrument_type: str | None = None, is_active: bool = True) -> list[str]:
        return [f"N{i}" for i in range(start, start + limit)]


class _StubRepo:
    def __init__(self) -> None:
        self.upserts: list[DatasetInjestion] = []
        self.closed = False
        self.latest_date = date(2026, 1, 20)
        self.latest_ingestion_time = datetime(2026, 1, 20, 10, 0)
        self.file_ingestions: list[DatasetInjestion] = []
        self.silver_to_date = date(2026, 1, 15)
        self.gold_watermark: date | None = None
        self.gold_build_id = 1
        self.promotable_ingestions: list[DatasetInjestion] = []
        self.input_watermarks: list[str] = []

    def close(self) -> None:
        self.closed = True

    def upsert_file_ingestion(self, ingestion: DatasetInjestion) -> None:
        self.upserts.append(ingestion)

    def get_latest_bronze_to_date(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> date | None:
        return self.latest_date if ticker else None

    def get_latest_bronze_ingestion_time(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> datetime | None:
        return self.latest_ingestion_time if ticker else None

    def list_promotable_file_ingestions(self) -> list[DatasetInjestion]:
        return list(self.promotable_ingestions)

    def get_latest_silver_to_date(
        self,
        *,
        domain: str,
        source: str,
        dataset: str,
        discriminator: str,
        ticker: str,
    ) -> date | None:
        return self.silver_to_date

    def load_input_watermarks(self, conn: object, *, datasets: set[str]) -> list[str]:
        return self.input_watermarks

    def next_gold_build_id(self, conn: object) -> int:
        return self.gold_build_id

    def insert_gold_build(
        self,
        conn: object,
        *,
        gold_build_id: int,
        run_id: str,
        model_version: str,
        started_at: datetime,
        finished_at: datetime,
        status: str,
        error_message: str | None,
        input_watermarks: list[str],
        row_counts: dict[str, int],
    ) -> None:
        pass

    def start_gold_manifest(self, conn: object, *, gold_build_id: int, table_name: str) -> None:
        pass

    def finish_gold_manifest(
        self,
        conn: object,
        *,
        gold_build_id: int,
        table_name: str,
        status: str,
        rows_seen: int,
        rows_written: int,
        error_message: str | None,
    ) -> None:
        pass

    def get_gold_watermark(self, conn: object, *, table_name: str) -> date | None:
        return self.gold_watermark

    def upsert_gold_watermark(self, conn: object, *, table_name: str, watermark_date: date | None) -> None:
        self.gold_watermark = watermark_date

    def update_gold_ingestion_times(
        self,
        *,
        run_id: str,
        gold_injest_start_time: datetime | None = None,
        gold_injest_end_time: datetime | None = None,
    ) -> None:
        pass

    def load_file_ingestions(
        self,
        *,
        run_id: str,
        identity: DatasetIdentity,
        ticker_scope: str,
    ) -> list[DatasetInjestion]:
        return list(self.file_ingestions)


# --- Tests for get_last_ingestion_date ---


class TestGetLastIngestionDate:
    def test_returns_date_from_latest_ingestion_time(self) -> None:
        repo = _StubRepo()
        repo.latest_ingestion_time = datetime(2026, 1, 20, 14, 30)
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        result = service.get_last_ingestion_date(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="AAPL",
        )

        assert result == date(2026, 1, 20)

    def test_returns_none_when_no_ingestion(self) -> None:
        repo = _StubRepo()
        repo.latest_ingestion_time = None
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        result = service.get_last_ingestion_date(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )

        assert result is None


# --- Tests for load_promotable_file_ingestions ---


class TestLoadPromotableFileIngestions:
    def test_returns_promotable_ingestions(self) -> None:
        repo = _StubRepo()
        ingestion = DatasetInjestion(
            run_id="run-123",
            file_id="file-1",
            domain="company",
            source="fmp",
            dataset="company-profile",
        )
        repo.promotable_ingestions = [ingestion]
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        result = service.load_promotable_file_ingestions()

        assert len(result) == 1
        assert result[0].file_id == "file-1"

    def test_returns_empty_list_when_none_promotable(self) -> None:
        repo = _StubRepo()
        repo.promotable_ingestions = []
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        result = service.load_promotable_file_ingestions()

        assert result == []


# --- Tests for get_silver_watermark ---


class TestGetSilverWatermark:
    def test_returns_silver_watermark_date(self) -> None:
        repo = _StubRepo()
        repo.silver_to_date = date(2026, 1, 15)
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        result = service.get_silver_watermark(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="AAPL",
        )

        assert result == date(2026, 1, 15)


# --- Tests for gold operations ---


class TestGoldOperations:
    def test_load_input_watermarks(self) -> None:
        repo = _StubRepo()
        repo.input_watermarks = ["company-profile:2026-01-15", "balance-sheet:2026-01-10"]
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        conn = MagicMock()
        result = service.load_input_watermarks(conn, datasets={"company-profile", "balance-sheet"})

        assert len(result) == 2

    def test_next_gold_build_id(self) -> None:
        repo = _StubRepo()
        repo.gold_build_id = 42
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        conn = MagicMock()
        result = service.next_gold_build_id(conn)

        assert result == 42

    def test_insert_gold_build_delegates_to_repo(self) -> None:
        repo = _StubRepo()
        repo.insert_gold_build = MagicMock()
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        conn = MagicMock()
        service.insert_gold_build(
            conn,
            gold_build_id=1,
            run_id="run-123",
            model_version="abc123",
            started_at=datetime(2026, 1, 27, 12, 0),
            finished_at=datetime(2026, 1, 27, 12, 30),
            status="success",
            error_message=None,
            input_watermarks=[],
            row_counts={"dim_test": 10},
        )

        repo.insert_gold_build.assert_called_once()

    def test_get_gold_watermark(self) -> None:
        repo = _StubRepo()
        repo.gold_watermark = date(2026, 1, 10)
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        conn = MagicMock()
        result = service.get_gold_watermark(conn, table_name="dim_test")

        assert result == date(2026, 1, 10)

    def test_upsert_gold_watermark(self) -> None:
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        conn = MagicMock()
        service.upsert_gold_watermark(conn, table_name="dim_test", watermark_date=date(2026, 1, 20))

        assert repo.gold_watermark == date(2026, 1, 20)


# --- Tests for update_gold_ingestion_times ---


class TestUpdateGoldIngestionTimes:
    def test_updates_start_time(self) -> None:
        repo = _StubRepo()
        repo.update_gold_ingestion_times = MagicMock()
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        start_time = datetime(2026, 1, 27, 12, 0)
        service.update_gold_ingestion_times(run_id="run-123", gold_injest_start_time=start_time)

        repo.update_gold_ingestion_times.assert_called_once_with(
            run_id="run-123",
            gold_injest_start_time=start_time,
            gold_injest_end_time=None,
        )

    def test_handles_repo_error(self) -> None:
        repo = _StubRepo()
        repo.update_gold_ingestion_times = MagicMock(side_effect=Exception("DB error"))
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        # Should not raise, just log warning
        service.update_gold_ingestion_times(run_id="run-123", gold_injest_start_time=datetime.now())


# --- Tests for load_dataset_ingestions ---


class TestLoadDatasetIngestions:
    def test_returns_ingestions(self) -> None:
        repo = _StubRepo()
        ingestion = DatasetInjestion(
            run_id="run-123",
            file_id="file-1",
            domain="company",
            source="fmp",
            dataset="company-profile",
        )
        repo.file_ingestions = [ingestion]
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )
        result = service.load_dataset_ingestions(run_id="run-123", identity=identity, ticker_scope="per_ticker")

        assert len(result) == 1

    def test_returns_empty_on_error(self) -> None:
        repo = _StubRepo()
        repo.load_file_ingestions = MagicMock(side_effect=Exception("DB error"))
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )
        result = service.load_dataset_ingestions(run_id="run-123", identity=identity, ticker_scope="per_ticker")

        assert result == []


# --- Tests for ensure_dataset_ingestions ---


class TestEnsureDatasetIngestions:
    def test_returns_existing_ingestions(self) -> None:
        repo = _StubRepo()
        ingestion = DatasetInjestion(
            run_id="run-123",
            file_id="file-1",
            domain="company",
            source="fmp",
            dataset="company-profile",
        )
        repo.file_ingestions = [ingestion]
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )
        result = service.ensure_dataset_ingestions(run_id="run-123", identity=identity, ticker_scope="per_ticker")

        assert len(result) == 1
        assert result[0].file_id == "file-1"


# --- Tests for _resolve_stub_tickers ---


class TestResolveStubTickers:
    def test_returns_empty_for_global_scope(self) -> None:
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )
        result = service._resolve_stub_tickers(identity=identity, ticker_scope="global", tickers=None)

        assert result == [""]

    def test_returns_identity_ticker_when_present(self) -> None:
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="AAPL",
        )
        result = service._resolve_stub_tickers(identity=identity, ticker_scope="per_ticker", tickers=None)

        assert result == ["AAPL"]

    def test_returns_provided_tickers_for_per_ticker(self) -> None:
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )
        result = service._resolve_stub_tickers(identity=identity, ticker_scope="per_ticker", tickers=["AAPL", "MSFT"])

        assert result == ["AAPL", "MSFT"]

    def test_filters_empty_tickers(self) -> None:
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )
        result = service._resolve_stub_tickers(identity=identity, ticker_scope="per_ticker", tickers=["AAPL", "", "MSFT"])

        assert result == ["AAPL", "MSFT"]


# --- Tests for _stub_file_id ---


class TestStubFileId:
    def test_creates_stub_file_id(self) -> None:
        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )

        result = OpsService._stub_file_id(run_id="run-123", identity=identity, ticker="AAPL")

        assert result == "gold-stub:run-123:company:fmp:company-profile::AAPL"

    def test_handles_discriminator(self) -> None:
        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="quarterly",
            ticker="",
        )

        result = OpsService._stub_file_id(run_id="run-123", identity=identity, ticker="AAPL")

        assert result == "gold-stub:run-123:company:fmp:company-profile:quarterly:AAPL"

    def test_handles_empty_ticker(self) -> None:
        identity = DatasetIdentity(
            domain="company",
            source="fmp",
            dataset="company-profile",
            discriminator="",
            ticker="",
        )

        result = OpsService._stub_file_id(run_id="run-123", identity=identity, ticker="")

        assert result == "gold-stub:run-123:company:fmp:company-profile::"


# --- Tests for start_run flags ---


class TestStartRunFlags:
    def test_empty_tickers_when_both_disabled(self) -> None:
        universe = _StubUniverse()
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=universe)

        summary = service.start_run(
            update_ticker_limit=10,
            new_ticker_limit=10,
            enable_update_tickers=False,
            enable_new_tickers=False,
        )

        assert summary.tickers == []
        assert summary.update_tickers == []
        assert summary.new_tickers == []

    def test_only_update_tickers_when_new_disabled(self) -> None:
        universe = _StubUniverse()
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=universe)

        summary = service.start_run(
            update_ticker_limit=2,
            new_ticker_limit=3,
            enable_update_tickers=True,
            enable_new_tickers=False,
        )

        assert summary.update_tickers == ["T0", "T1"]
        assert summary.new_tickers == []
        assert summary.tickers == ["T0", "T1"]

    def test_only_new_tickers_when_update_disabled(self) -> None:
        universe = _StubUniverse()
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=universe)

        summary = service.start_run(
            update_ticker_limit=2,
            new_ticker_limit=3,
            enable_update_tickers=False,
            enable_new_tickers=True,
        )

        assert summary.update_tickers == []
        assert summary.new_tickers == ["N0", "N1", "N2"]
        assert summary.tickers == ["N0", "N1", "N2"]

    def test_zero_limit_returns_empty(self) -> None:
        universe = _StubUniverse()
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=universe)

        summary = service.start_run(
            update_ticker_limit=0,
            new_ticker_limit=0,
            enable_update_tickers=True,
            enable_new_tickers=True,
        )

        assert summary.update_tickers == []
        assert summary.new_tickers == []


# --- Tests for finish_run ---


class TestFinishRun:
    def test_handles_none_summary(self) -> None:
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=_StubUniverse())

        # Should not raise
        service.finish_run(None)

    def test_sets_finished_at_and_closes(self) -> None:
        universe = _StubUniverse()
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=universe)
        service._owns_ops_repo = True

        summary = service.start_run(update_ticker_limit=1, enable_update_tickers=True)
        service.finish_run(summary)

        assert summary.finished_at == universe.now()
        assert repo.closed is True
