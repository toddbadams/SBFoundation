from __future__ import annotations

from datetime import date, datetime, timedelta

from data_layer.dataset.models.dataset_identity import DatasetIdentity
from data_layer.ops.dtos.file_injestion import DatasetInjestion
from data_layer.ops.services.ops_service import OpsService
import pytest

from tests.unit.helpers import make_run_context, make_run_result


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
    summary = service.start_run(update_ticker_limit=2, enable_update_tickers=True, enable_new_tickers=False)
    assert summary.run_id == "stub-run"
    assert summary.update_tickers == ["T0", "T1"]
    assert summary.tickers == ["T0", "T1"]
    service._owns_ops_repo = True
    service.finish_run(summary)
    assert summary.finished_at == universe.now()
    assert repo.closed


def test_start_run_with_new_tickers() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    summary = service.start_run(
        update_ticker_limit=2,
        new_ticker_limit=3,
        enable_update_tickers=True,
        enable_new_tickers=True,
    )
    assert summary.run_id == "stub-run"
    assert summary.update_tickers == ["T0", "T1"]
    assert summary.new_tickers == ["N0", "N1", "N2"]
    assert summary.tickers == ["T0", "T1", "N0", "N1", "N2"]


def test_insert_bronze_manifest_surfaces_repo_errors() -> None:
    service = OpsService(ops_repo=_FailingRepo(), universe=_StubUniverse())
    with pytest.raises(RuntimeError, match="boom"):
        service.insert_bronze_manifest(make_run_result())


def test_silver_ingestion_flags_toggle() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    ingestion = DatasetInjestion.from_bronze(make_run_result())
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
    ingestion = DatasetInjestion.from_bronze(make_run_result())
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


def test_start_gold_ingestion_sets_start_time() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    ingestion = DatasetInjestion.from_bronze(make_run_result())
    repo.file_ingestions = [ingestion]
    identity = DatasetIdentity(
        domain=ingestion.domain,
        source=ingestion.source,
        dataset=ingestion.dataset,
        discriminator=ingestion.discriminator or "",
        ticker="",
    )
    service.start_gold_ingestion(run_id=ingestion.run_id, identity=identity, ticker_scope="per_ticker")
    assert ingestion.gold_injest_start_time == universe.now()
    assert repo.upserts[-1].gold_injest_start_time == universe.now()


def test_start_gold_ingestion_creates_stub_rows() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    identity = DatasetIdentity(domain="company", source="fmp", dataset="company-profile", discriminator="", ticker="")
    service.start_gold_ingestion(run_id="stub-run", identity=identity, ticker_scope="per_ticker", tickers=["AAPL"])
    assert repo.upserts
    assert repo.upserts[0].file_id.startswith("gold-stub:stub-run:company:fmp:company-profile")
    assert repo.upserts[0].ticker == "AAPL"


def test_finish_gold_ingestion_sets_gold_fields() -> None:
    universe = _StubUniverse()
    repo = _StubRepo()
    service = OpsService(ops_repo=repo, universe=universe)
    ingestion = DatasetInjestion.from_bronze(make_run_result())
    repo.file_ingestions = [ingestion]
    identity = DatasetIdentity(
        domain=ingestion.domain,
        source=ingestion.source,
        dataset=ingestion.dataset,
        discriminator=ingestion.discriminator or "",
        ticker="",
    )
    service.finish_gold_ingestion(
        run_id=ingestion.run_id,
        identity=identity,
        ticker_scope="per_ticker",
        object_types=["dim:Company", "fact:Revenue"],
        table_names=["gold.dim_company", "gold.fact_revenue"],
        rows_created=12,
        rows_updated=0,
        rows_failed=0,
        coverage_from=date(2026, 1, 1),
        coverage_to=date(2026, 1, 2),
        error=None,
        can_promote=True,
        finished_at=universe.now(),
    )
    assert ingestion.gold_rows_created == 12
    assert ingestion.gold_tablename == "gold.dim_company, gold.fact_revenue"
    assert ingestion.gold_can_promote is True
    assert ingestion.gold_injest_end_time == universe.now()
