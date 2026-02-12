from __future__ import annotations

import pytest
import requests

from data_layer.run.services import run_request_executor as run_request_executor_module
from data_layer.run.services.run_request_executor import RunRequestExecutor
from tests.unit.helpers import make_run_context


class _StubLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def debug(self, _msg: str) -> None:
        pass

    def warning(self, msg: str, *args: object) -> None:
        self.warnings.append((msg % args) if args else msg)

    def error(self, msg: str, *args: object) -> None:
        self.errors.append((msg % args) if args else msg)


def test_execute_exhausts_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = _StubLogger()
    executor = RunRequestExecutor(logger=logger)
    executor._throttle = lambda: None
    monkeypatch.setattr(run_request_executor_module.time, "sleep", lambda _: None)

    def failing_call() -> None:
        raise requests.RequestException("boom")

    with pytest.raises(RuntimeError):
        executor.execute(failing_call, "GET https://example.com")

    assert len(logger.warnings) == run_request_executor_module.RETRY_MAX_ATTEMPS - 1
    assert len(logger.errors) == 1


def test_throttle_updates_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = _StubLogger()
    summary = make_run_context()
    executor = RunRequestExecutor(logger=logger, summary=summary)

    fake_time = {"value": 1.0}

    def fake_time_fn() -> float:
        return fake_time["value"]

    def fake_sleep(seconds: float) -> None:
        fake_time["value"] += seconds
        executor.call_timestamps.clear()

    monkeypatch.setattr(run_request_executor_module.time, "time", fake_time_fn)
    monkeypatch.setattr(run_request_executor_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(run_request_executor_module, "THROTTLE_MAX_CALLS", 1)
    monkeypatch.setattr(run_request_executor_module, "THROTTLE_PERIOD_SECONDS", 60)

    executor._throttle()
    fake_time["value"] = 1.1
    executor._throttle()

    assert summary.throttle_wait_count == 1
    assert summary.throttle_max_queue_depth == 1
    assert summary.throttle_sleep_seconds == pytest.approx(59.9, rel=1e-3)
