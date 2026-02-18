from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import threading
import typing

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.ops.dtos.bronze_injest_item import BronzeInjestItem
from sbfoundation.ops.dtos.silver_injest_item import SilverInjestItem
from sbfoundation.run.dtos.bronze_result import BronzeResult


@dataclass(slots=True, kw_only=True, order=True)
class RunContext(BronzeToSilverDTO):
    run_id: str
    started_at: datetime
    tickers: list[str]
    update_tickers: list[str] = field(default_factory=list)  # Tickers already ingested
    new_tickers: list[str] = field(default_factory=list)  # New tickers from dimensions
    today: str
    finished_at: datetime = None
    bronze_files_passed: int = 0
    bronze_files_failed: int = 0
    silver_dto_count: int = 0
    silver_failed_count: int = 0
    throttle_wait_count: int = 0
    throttle_sleep_seconds: float = 0.0
    throttle_max_queue_depth: int = 0
    status: str | None = None

    bronze_injest_items: list[BronzeInjestItem] = field(default_factory=list)
    silver_injest_items: list[SilverInjestItem] = field(default_factory=list)

    # Thread synchronization for concurrent Bronze requests
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False, compare=False)

    @property
    def elapsed_seconds(self) -> float:
        return round((self.finished_at - self.started_at).total_seconds(), 2)

    @property
    def msg(self) -> str:
        return (
            f"elapsed_seconds={self.elapsed_seconds:.2f} | bronze_files_written={self.bronze_files_passed}"
            f" | bronze_files_failed={self.bronze_files_failed} | silver_dto_count={self.silver_dto_count}"
        )

    @property
    def formatted_elapsed_time(self) -> str:
        total_seconds = self.elapsed_seconds
        if total_seconds < 60:
            return f"{total_seconds:.2f}s"

        seconds_int = int(total_seconds)
        if seconds_int < 3600:
            minutes, seconds = divmod(seconds_int, 60)
            return f"{minutes}m {seconds}s"

        hours, remainder = divmod(seconds_int, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

    def result_bronze_error(self, result: BronzeResult, e: str, filename: str | None = None) -> BronzeInjestItem:
        filename = filename or result.request.bronze_absolute_filename
        item = BronzeInjestItem(
            domain=result.request.recipe.domain,
            source=result.request.recipe.source,
            dataset=result.request.recipe.dataset,
            discriminator=result.request.recipe.discriminator,
            ticker=result.request.ticker,
            from_date=result.first_date,
            to_date=result.last_date,
            filename=filename,
            status="failed",
            error=result.error,
        )
        with self._lock:
            self.bronze_files_failed += 1
            self.bronze_injest_items.append(item)
        return item

    def result_bronze_pass(self, result: BronzeResult, filename: str | None = None) -> BronzeInjestItem:
        filename = filename or result.request.bronze_absolute_filename
        item = BronzeInjestItem(
            domain=result.request.recipe.domain,
            source=result.request.recipe.source,
            dataset=result.request.recipe.dataset,
            discriminator=result.request.recipe.discriminator,
            ticker=result.request.ticker,
            from_date=result.first_date,
            to_date=result.last_date,
            filename=filename,
            status="passed",
            error=result.error,
        )
        with self._lock:
            self.bronze_files_passed += 1
            self.bronze_injest_items.append(item)
        return item

    def result_silver_pass(self, result: BronzeResult, dto: BronzeToSilverDTO) -> SilverInjestItem:
        item = SilverInjestItem(
            domain=result.request.recipe.domain,
            source=result.request.recipe.source,
            dataset=result.request.recipe.dataset,
            discriminator=result.request.recipe.discriminator,
            ticker=result.request.ticker,
            table_name=result.request.recipe.dataset,
            date=dto.key_date.isoformat(),
            status="passed",
            dto_type=repr(type(dto)),
            error=None,
        )
        with self._lock:
            self.silver_injest_items.append(item)
        return item

    def result_silver_error(self, result: BronzeResult, e: str) -> SilverInjestItem:
        silver_date = result.last_date or result.request.to_date
        item = SilverInjestItem(
            domain=result.request.recipe.domain,
            source=result.request.recipe.source,
            dataset=result.request.recipe.dataset,
            discriminator=result.request.recipe.discriminator,
            ticker=result.request.ticker,
            table_name=result.request.recipe.dataset,
            date=silver_date,
            status="failed",
            dto_type=repr(result.request.dto_type),
            error=result.error,
        )
        with self._lock:
            self.silver_failed_count += 1
            self.silver_injest_items.append(item)
        return item

    def resolve_status(self) -> str:
        failure_count = self._safe_int(self.bronze_files_failed) + self._safe_int(self.silver_failed_count)
        success_count = self._safe_int(self.bronze_files_passed) + self._safe_int(self.silver_dto_count)
        if failure_count <= 0:
            return "success"
        if success_count <= 0:
            return "failure"
        return "partial"

    @staticmethod
    def _safe_int(value: int | None) -> int:
        return 0 if value is None else int(value)

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "RunContext":
        return cls.build_from_row(row, ticker_override=ticker)

    def to_dict(self) -> dict[str, typing.Any]:
        return self.build_to_dict()
