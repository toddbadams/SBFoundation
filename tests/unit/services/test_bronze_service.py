from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from requests.structures import CaseInsensitiveDict

from sbfoundation.services.bronze.bronze_service import BronzeService
from sbfoundation.run.dtos.run_request import RunRequest
from tests.unit.helpers import make_run_context, make_run_request


class _StubUniverse:
    """Universe stub with a fixed 'today' for deterministic tests."""

    def __init__(self, today: date) -> None:
        self._today = today

    def now(self) -> datetime:
        return datetime(self._today.year, self._today.month, self._today.day, 10, 0)

    def today(self) -> date:
        return self._today

    @property
    def from_date(self) -> str:
        return "2025-10-01"


class _FakeResponse:
    def __init__(self) -> None:
        self.elapsed = SimpleNamespace(microseconds=10)
        self.headers = CaseInsensitiveDict({"content-type": "application/json"})
        self.status_code = 200
        self.reason = "OK"
        self.content = b'[{"date":"2026-01-26"}]'

    def json(self) -> list[dict[str, str]]:
        return [{"date": "2026-01-26"}]

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")


class _StubExecutor:
    def __init__(self, response: _FakeResponse | None = None) -> None:
        self.response = response
        self.calls = 0

    def execute(self, func, log_str: str) -> _FakeResponse:
        self.calls += 1
        return self.response or _FakeResponse()


class _StubResultAdapter:
    def __init__(self) -> None:
        self.results: list[RunRequest] = []

    def write(self, result: RunRequest) -> Path:
        self.results.append(result)
        return Path("fallback.json")


class _StubOpsService:
    def __init__(self, watermark_date=None, last_ingestion_date=None) -> None:
        self.inserted: list[RunRequest] = []
        self._watermark_date = watermark_date
        self._last_ingestion_date = last_ingestion_date
        self.watermark_calls: int = 0
        self.ingestion_date_calls: int = 0

    def get_bulk_ingestion_watermarks(self, *, domain: str, source: str, dataset: str, discriminator: str) -> dict:
        # Return an empty dict so every ticker is treated as first-time ingestion.
        return {}

    def get_watermark_date(self, *args: object, **kwargs: object):
        self.watermark_calls += 1
        return self._watermark_date

    def get_last_ingestion_date(self, *args: object, **kwargs: object):
        self.ingestion_date_calls += 1
        return self._last_ingestion_date

    def insert_bronze_manifest(self, result: RunRequest) -> None:
        self.inserted.append(result)


def _make_service(executor: _StubExecutor | None = None) -> BronzeService:
    return BronzeService(
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor or _StubExecutor(),
        ops_service=_StubOpsService(),
    )


def test_process_run_request_rejects_too_soon() -> None:
    summary = make_run_context()
    service = _make_service()
    service.summary = summary
    request = make_run_request(overrides={"from_date": summary.today})

    service._process_run_request(request)

    # TOO SOON requests should not save files or update ops
    assert summary.bronze_files_failed == 0
    assert summary.bronze_files_passed == 0
    assert not summary.bronze_injest_items
    assert len(service.result_file_adapter.results) == 0
    assert len(service.ops_service.inserted) == 0


def test_process_run_request_persists_success() -> None:
    executor = _StubExecutor(response=_FakeResponse())
    service = _make_service(executor)
    summary = make_run_context()
    service.summary = summary
    request = make_run_request()

    service._process_run_request(request)

    assert summary.bronze_files_passed == 1
    assert len(service.result_file_adapter.results) == 1
    assert len(service.ops_service.inserted) == 1
    assert executor.calls == 1


def test_concurrent_mode_processes_all_requests() -> None:
    """Test that concurrent mode processes all requests correctly."""
    executor = _StubExecutor(response=_FakeResponse())
    service = BronzeService(
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor,
        ops_service=_StubOpsService(),
        concurrent_requests=5,  # Enable concurrent mode
    )
    summary = make_run_context(tickers=["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"])
    service.run = summary

    # Create multiple requests
    requests = [make_run_request(overrides={"ticker": ticker}) for ticker in summary.tickers]

    # Process concurrently
    service._process_requests_concurrent(requests)

    # Verify all requests were processed
    assert summary.bronze_files_passed == len(requests)
    assert len(service.result_file_adapter.results) == len(requests)
    assert len(service.ops_service.inserted) == len(requests)
    assert executor.calls == len(requests)


def test_force_from_date_bypasses_watermark_and_duplicate_check() -> None:
    """When force_from_date is set, watermark and duplicate-ingestion lookups are skipped."""
    from datetime import date

    ops = _StubOpsService(
        watermark_date=date(2025, 12, 31),       # would normally advance from_date to 2026
        last_ingestion_date=date(2026, 2, 23),   # would normally trigger duplicate skip
    )
    executor = _StubExecutor(response=_FakeResponse())
    service = BronzeService(
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor,
        ops_service=ops,
        force_from_date="1990-01-01",
    )
    summary = make_run_context()
    service.summary = summary
    request = make_run_request()

    service._process_run_request(request)

    # Request should have been sent (not skipped)
    assert executor.calls == 1
    assert summary.bronze_files_passed == 1
    # Watermark and duplicate-ingestion lookups must be bypassed
    assert ops.watermark_calls == 0
    assert ops.ingestion_date_calls == 0
    # from_date must be the forced value
    assert request.from_date == "1990-01-01"


def test_force_from_date_overrides_request_from_date() -> None:
    """force_from_date replaces whatever from_date was set on the RunRequest."""
    ops = _StubOpsService()
    executor = _StubExecutor(response=_FakeResponse())
    service = BronzeService(
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor,
        ops_service=ops,
        force_from_date="1990-01-01",
    )
    summary = make_run_context()
    service.summary = summary
    # Request is initialised with today as from_date (would be "too soon" without force)
    request = make_run_request(overrides={"from_date": summary.today})

    service._process_run_request(request)

    assert executor.calls == 1
    assert request.from_date == "1990-01-01"


def test_normal_mode_still_uses_watermark() -> None:
    """Without force_from_date, watermark is still applied normally."""
    from datetime import date

    watermark = date(2025, 6, 30)
    ops = _StubOpsService(watermark_date=watermark)
    executor = _StubExecutor(response=_FakeResponse())
    service = BronzeService(
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor,
        ops_service=ops,
    )
    summary = make_run_context()
    service.summary = summary
    request = make_run_request()

    service._process_run_request(request)

    assert ops.watermark_calls == 1
    assert request.from_date == watermark.isoformat()


def test_ingestion_date_gate_blocks_recent_re_download() -> None:
    """Snapshot dataset ingested 5 days ago with min_age_days=90 and a stuck content
    watermark should be skipped — no HTTP request, nothing written to bronze."""
    today = date(2026, 2, 24)
    ops = _StubOpsService(
        watermark_date=date(2025, 10, 2),       # stuck before universe.from_date
        last_ingestion_date=date(2026, 2, 19),  # 5 days ago → 5 <= 90 → gated
    )
    executor = _StubExecutor(response=_FakeResponse())
    service = BronzeService(
        universe=_StubUniverse(today),
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor,
        ops_service=ops,
    )
    service.summary = make_run_context()
    request = make_run_request(overrides={"min_age_days": 90})

    service._process_run_request(request)

    assert executor.calls == 0
    assert len(service.result_file_adapter.results) == 0


def test_ingestion_date_gate_allows_after_min_age_days() -> None:
    """Same snapshot dataset, but last ingested 95 days ago — gate should allow the
    download (95 > 90 = min_age_days)."""
    today = date(2026, 2, 24)
    ops = _StubOpsService(
        watermark_date=date(2025, 10, 2),       # stuck watermark
        last_ingestion_date=date(2025, 11, 21), # 95 days ago → 95 > 90 → allowed
    )
    executor = _StubExecutor(response=_FakeResponse())
    service = BronzeService(
        universe=_StubUniverse(today),
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor,
        ops_service=ops,
    )
    service.summary = make_run_context()
    request = make_run_request(overrides={"min_age_days": 90})

    service._process_run_request(request)

    assert executor.calls == 1
    assert len(service.result_file_adapter.results) == 1


def test_sync_mode_when_concurrent_requests_is_one() -> None:
    """Test that concurrent_requests=1 uses sequential processing."""
    from tests.unit.helpers import make_dataset_recipe

    executor = _StubExecutor(response=_FakeResponse())
    service = BronzeService(
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor,
        ops_service=_StubOpsService(),
        concurrent_requests=1,  # Synchronous mode
    )
    summary = make_run_context(tickers=["AAPL", "MSFT"])
    service.run = summary

    # Create recipe
    recipe = make_dataset_recipe(is_ticker_based=True)

    # Process dataset recipe (will dispatch to sync or concurrent based on concurrent_requests)
    service._process_dataset_recipe(recipe)

    # Verify all requests were processed (sequential mode)
    assert summary.bronze_files_passed == len(summary.tickers)
    assert executor.calls == len(summary.tickers)
