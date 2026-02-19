"""Extended unit tests for OpsService methods not covered in test_ops_service.py."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from sbfoundation.dataset.models.dataset_identity import DatasetIdentity
from sbfoundation.ops.dtos.file_injestion import DatasetInjestion
from sbfoundation.ops.services.ops_service import OpsService


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

    def update_tickers(self, *, start: int = 0, limit: int = 50) -> list[str]:
        return [f"T{i}" for i in range(start, start + limit)]


class _StubRepo:
    def __init__(self) -> None:
        self.upserts: list[DatasetInjestion] = []
        self.closed = False
        self.latest_date = date(2026, 1, 20)
        self.latest_ingestion_time = datetime(2026, 1, 20, 10, 0)
        self.file_ingestions: list[DatasetInjestion] = []
        self.silver_to_date = date(2026, 1, 15)
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


# --- Tests for start_run flags ---


class TestStartRunFlags:
    def test_empty_tickers_when_update_disabled(self) -> None:
        universe = _StubUniverse()
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=universe)

        summary = service.start_run(
            update_ticker_limit=10,
            enable_update_tickers=False,
        )

        assert summary.tickers == []
        assert summary.update_tickers == []

    def test_update_tickers_returned_when_enabled(self) -> None:
        universe = _StubUniverse()
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=universe)

        summary = service.start_run(
            update_ticker_limit=2,
            enable_update_tickers=True,
        )

        assert summary.update_tickers == ["T0", "T1"]
        assert summary.tickers == ["T0", "T1"]

    def test_zero_limit_returns_empty(self) -> None:
        universe = _StubUniverse()
        repo = _StubRepo()
        service = OpsService(ops_repo=repo, universe=universe)

        summary = service.start_run(
            update_ticker_limit=0,
            enable_update_tickers=True,
        )

        assert summary.update_tickers == []
        assert summary.tickers == []


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
