from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from requests.structures import CaseInsensitiveDict

from sbfoundation.services.bronze.bronze_service import BronzeService
from sbfoundation.run.dtos.run_request import RunRequest
from tests.unit.helpers import make_run_context, make_run_request


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
    def __init__(self) -> None:
        self.inserted: list[RunRequest] = []

    def get_watermark_date(self, *args: object, **kwargs: object) -> None:
        return None

    def get_last_ingestion_date(self, *args: object, **kwargs: object) -> None:
        return None

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
