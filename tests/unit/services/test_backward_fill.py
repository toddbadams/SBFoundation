"""Tests for BronzeService._run_backward_fill_loop()."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from requests.structures import CaseInsensitiveDict

from sbfoundation.services.bronze.bronze_service import BronzeService
from tests.unit.helpers import make_dataset_recipe, make_run_context, make_run_request


# ── Stubs ────────────────────────────────────────────────────────────────────


class _FakeResponse:
    """Minimal HTTP response stub."""

    def __init__(self, content: list[dict] | None = None) -> None:
        self._content_data = content if content is not None else [{"date": "2023-06-01"}]
        self.elapsed = SimpleNamespace(microseconds=10)
        self.headers = CaseInsensitiveDict({"content-type": "application/json"})
        self.status_code = 200
        self.reason = "OK"
        # Simulate empty bytes for empty content
        self.content = b"[]" if not self._content_data else b'[{"date":"2023-06-01"}]'

    def json(self) -> list[dict]:
        return self._content_data

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")


class _EmptyResponse(_FakeResponse):
    """Simulates an API response with no records."""

    def __init__(self) -> None:
        super().__init__(content=[])
        self.content = b""  # empty bytes → triggers "no data" branch in add_response


class _MultiResponseExecutor:
    """Returns successive responses for each call, repeating the last one."""

    def __init__(self, *responses: _FakeResponse) -> None:
        self._responses = list(responses)
        self.calls = 0

    def execute(self, func, log_str: str) -> _FakeResponse:
        idx = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return self._responses[idx]


class _StubResultAdapter:
    def __init__(self) -> None:
        self.written: list = []

    def write(self, result) -> Path:
        self.written.append(result)
        return Path("stub.json")


class _StubOpsServiceForBackfill:
    """Ops service stub that tracks backfill floor and earliest date lookups."""

    def __init__(
        self,
        *,
        floor_date: date | None = None,
        earliest_date: date | None = None,
    ) -> None:
        self._floor_date = floor_date
        self._earliest_date = earliest_date
        self.set_floor_calls: list[tuple] = []
        self.bronze_manifests: list = []

    # --- backfill methods ---

    def get_backfill_floor_date(self, domain, source, dataset, discriminator, ticker) -> date | None:
        return self._floor_date

    def get_earliest_bronze_from_date(self, domain, source, dataset, discriminator, ticker) -> date | None:
        return self._earliest_date

    def set_backfill_floor_date(self, domain, source, dataset, discriminator, ticker, floor_date: date) -> None:
        self._floor_date = floor_date
        self.set_floor_calls.append((domain, source, dataset, discriminator, ticker, floor_date))

    # --- manifest ---

    def insert_bronze_manifest(self, result) -> None:
        self.bronze_manifests.append(result)

    # --- normal ingestion methods (not called by backward fill loop) ---

    def get_watermark_date(self, *args, **kwargs):
        return None

    def get_last_ingestion_date(self, *args, **kwargs):
        return None


class _StubUniverse:
    def now(self) -> datetime:
        return datetime(2026, 2, 24, 10, 0)

    def today(self) -> date:
        return date(2026, 2, 24)

    @property
    def from_date(self) -> str:
        return "1990-01-01"


def _make_service(
    *,
    ops_service: _StubOpsServiceForBackfill | None = None,
    executor: _MultiResponseExecutor | None = None,
) -> BronzeService:
    return BronzeService(
        universe=_StubUniverse(),
        result_file_adapter=_StubResultAdapter(),
        request_executor=executor or _MultiResponseExecutor(_EmptyResponse()),
        ops_service=ops_service or _StubOpsServiceForBackfill(),
        backfill_to_1990=True,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_skip_if_fully_backfilled() -> None:
    """When floor == 1990-01-01, the loop exits immediately without any API calls."""
    ops = _StubOpsServiceForBackfill(floor_date=date(1990, 1, 1), earliest_date=date(2022, 1, 1))
    executor = _MultiResponseExecutor(_FakeResponse())
    service = _make_service(ops_service=ops, executor=executor)
    service.run = make_run_context()

    request = make_run_request()
    service._run_backward_fill_loop(request)

    assert executor.calls == 0
    assert len(ops.set_floor_calls) == 0


def test_skip_if_no_data_loaded() -> None:
    """When no bronze data has been ingested yet, the loop exits without any API calls."""
    ops = _StubOpsServiceForBackfill(floor_date=None, earliest_date=None)
    executor = _MultiResponseExecutor(_FakeResponse())
    service = _make_service(ops_service=ops, executor=executor)
    service.run = make_run_context()

    request = make_run_request()
    service._run_backward_fill_loop(request)

    assert executor.calls == 0
    assert len(ops.set_floor_calls) == 0


def test_empty_response_sets_sentinel() -> None:
    """An empty API response marks backfill_floor_date = 1990-01-01 (sentinel)."""
    ops = _StubOpsServiceForBackfill(floor_date=None, earliest_date=date(2024, 1, 1))
    service = _make_service(ops_service=ops, executor=_MultiResponseExecutor(_EmptyResponse()))
    service.run = make_run_context()

    request = make_run_request()
    service._run_backward_fill_loop(request)

    assert len(ops.set_floor_calls) == 1
    _, _, _, _, _, set_date = ops.set_floor_calls[0]
    assert set_date == date(1990, 1, 1)


def test_chunk_advances_floor() -> None:
    """A successful chunk sets floor to the earliest date in the response, then sentinel on empty."""
    ops = _StubOpsServiceForBackfill(floor_date=None, earliest_date=date(2024, 1, 1))
    # First response has data dated 2023-06-01; second is empty → sentinel
    executor = _MultiResponseExecutor(
        _FakeResponse(content=[{"date": "2023-06-01"}]),
        _EmptyResponse(),
    )
    service = _make_service(ops_service=ops, executor=executor)
    service.run = make_run_context()

    request = make_run_request()
    service._run_backward_fill_loop(request)

    assert executor.calls == 2
    # First call should set floor to 2023-06-01
    first_floor = ops.set_floor_calls[0][-1]
    assert first_floor == date(2023, 6, 1)
    # Second call (empty) should set sentinel
    final_floor = ops.set_floor_calls[-1][-1]
    assert final_floor == date(1990, 1, 1)


def test_stops_when_floor_reaches_1990() -> None:
    """When a chunk's earliest date is near 1990-01-01, the sentinel is set and loop terminates."""
    ops = _StubOpsServiceForBackfill(floor_date=None, earliest_date=date(1990, 1, 5))
    # Response contains a record dated 1990-01-02 → to_date becomes 1990-01-01 → stop
    executor = _MultiResponseExecutor(_FakeResponse(content=[{"date": "1990-01-02"}]))
    service = _make_service(ops_service=ops, executor=executor)
    service.run = make_run_context()

    request = make_run_request()
    service._run_backward_fill_loop(request)

    assert executor.calls == 1
    # Should have two set_floor calls: one for 1990-01-02, one for sentinel 1990-01-01
    floor_dates = [call[-1] for call in ops.set_floor_calls]
    assert date(1990, 1, 2) in floor_dates
    assert date(1990, 1, 1) in floor_dates
    assert ops._floor_date == date(1990, 1, 1)
