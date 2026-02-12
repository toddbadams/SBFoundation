import threading
import time
import typing
import requests
from collections import deque

from data_layer.run.dtos.run_context import RunContext
from settings import RETRY_BASE_DELAY, RETRY_MAX_ATTEMPS, THROTTLE_MAX_CALLS, THROTTLE_PERIOD_SECONDS


class RunRequestExecutor:
    def __init__(self, logger: typing.Any, summary: typing.Optional[RunContext] = None) -> None:
        self.logger = logger
        self.summary = summary
        self.throttle_lock = threading.Lock()
        self.call_timestamps: deque[float] = deque()

    def set_summary(self, summary: RunContext) -> None:
        self.summary = summary

    def execute(self, func: typing.Callable[..., typing.Any], log_str: str) -> typing.Any:
        self._throttle()
        return self._with_retries(func, log_str)

    def _with_retries(self, func: typing.Callable[..., typing.Any], log_str: str) -> typing.Any:
        attempt = 0
        while True:
            log = f"{log_str} | attempt={attempt + 1}/{RETRY_MAX_ATTEMPS}"
            try:
                self.logger.debug(log)
                return func()
            except requests.RequestException as e:
                attempt += 1
                if attempt >= RETRY_MAX_ATTEMPS:
                    msg = f"FAILED: {log}: exception={e}"
                    self.logger.error(msg)
                    raise RuntimeError(msg) from e
                backoff = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                self.logger.warning(f"Transient error:  {log} | Retrying in {backoff:.2f}s")
                time.sleep(backoff)

    def _throttle(self) -> None:
        while True:
            with self.throttle_lock:
                now = time.time()
                window_start = now - THROTTLE_PERIOD_SECONDS
                while self.call_timestamps and self.call_timestamps[0] <= window_start:
                    self.call_timestamps.popleft()
                if self.summary is not None and len(self.call_timestamps) > self.summary.throttle_max_queue_depth:
                    self.summary.throttle_max_queue_depth = len(self.call_timestamps)
                if len(self.call_timestamps) < THROTTLE_MAX_CALLS:
                    self.call_timestamps.append(now)
                    return
                sleep_for = THROTTLE_PERIOD_SECONDS - (now - self.call_timestamps[0])
            if sleep_for > 0:
                if self.summary is not None:
                    self.summary.throttle_wait_count += 1
                    self.summary.throttle_sleep_seconds += sleep_for
                self.logger.debug(f"Throttle sleeping | {sleep_for}")
                time.sleep(sleep_for)
            else:
                time.sleep(0)
