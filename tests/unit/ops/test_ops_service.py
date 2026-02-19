from __future__ import annotations

from datetime import date, datetime, timedelta

from sbfoundation.dataset.models.dataset_identity import DatasetIdentity
from sbfoundation.ops.dtos.file_injestion import DatasetInjestion
from sbfoundation.ops.services.ops_service import OpsService
import pytest

from tests.unit.helpers import make_run_context, make_bronze_result


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
        self.file_ingestions: list[DatasetInjestion] = []

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

    def load_input_watermarks(self, conn: object, *, datasets: set[str]) -> list[str]:
        return []

    def load_file_ingestions(
        self,
        *,
        run_id: str,
        identity: DatasetIdentity,
        ticker_scope: str,
    ) -> list[DatasetInjestion]:
        return list(self.file_ingestions)


class _FailingRepo(_StubRepo):
    def upsert_file_ingestion(self, ingestion: DatasetInjestion) -> None:
        raise RuntimeError("boom")


def test_start_and_finish_run_closes_repo() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    summary = service.start_run(update_ticker_limit=2, enable_update_tickers=True)
    assert summary.run_id == "stub-run"
    assert summary.update_tickers == ["T0", "T1"]
    assert summary.tickers == ["T0", "T1"]
    service._owns_ops_repo = True
    service.finish_run(summary)
    assert summary.finished_at == universe.now()
    assert repo.closed


def test_insert_bronze_manifest_surfaces_repo_errors() -> None:
    service = OpsService(ops_repo=_FailingRepo(), universe=_StubUniverse())
    with pytest.raises(RuntimeError, match="boom"):
        service.insert_bronze_manifest(make_bronze_result())


def test_silver_ingestion_flags_toggle() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    ingestion = DatasetInjestion.from_bronze(make_bronze_result())
    service.start_silver_ingestion(ingestion)
    assert ingestion.silver_injest_start_time == universe.now()
    service.finish_silver_ingestion(
        ingestion,
        rows_seen=10,
        rows_written=5,
        rows_failed=0,
        table_name="silver",
        coverage_from=date(2026, 1, 1),
        coverage_to=date(2026, 1, 2),
        error=None,
    )
    assert ingestion.silver_rows_created == 5
    assert ingestion.bronze_can_promote is False
    assert ingestion.silver_can_promote is True


def test_silver_finish_without_force_promote() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    ingestion = DatasetInjestion.from_bronze(make_bronze_result())
    ingestion.bronze_can_promote = True
    service.finish_silver_ingestion(
        ingestion,
        rows_seen=1,
        rows_written=0,
        rows_failed=1,
        table_name="silver",
        coverage_from=date(2026, 1, 1),
        coverage_to=date(2026, 1, 2),
        error="failure",
    )
    assert ingestion.silver_can_promote is False
    assert ingestion.bronze_can_promote is True


def test_get_watermark_date_increments_previous_day() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    got = service.get_watermark_date(domain="company", source="fmp", dataset="company-profile", discriminator="", ticker="AAPL")
    assert got == repo.latest_date + timedelta(days=1)
