from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Mapping

from httpx import request

from sbfoundation.dtos.models import BronzeManifestRow
from sbfoundation.run.dtos.run_request import RunRequest
from sbfoundation.run.dtos.bronze_result import BronzeResult


@dataclass
class DatasetInjestion:
    run_id: str
    file_id: str
    domain: str
    source: str
    dataset: str
    discriminator: str | None = None
    ticker: str | None = None

    bronze_from_date: date | None = None
    bronze_to_date: date | None = None
    bronze_filename: str | None = None
    bronze_error: str | None = None
    bronze_rows: int = 0
    bronze_injest_start_time: datetime | None = None
    bronze_injest_end_time: datetime | None = None
    bronze_can_promote: bool | None = None
    bronze_payload_hash: str | None = None

    silver_from_date: date | None = None
    silver_to_date: date | None = None
    silver_tablename: str | None = None
    silver_errors: str | None = None
    silver_rows_created: int = 0
    silver_rows_updated: int = 0
    silver_rows_failed: int = 0
    silver_injest_start_time: datetime | None = None
    silver_injest_end_time: datetime | None = None
    silver_can_promote: bool | None = None

    @property
    def msg(self) -> str:
        return "| ".join(
            p
            for p in (
                f"dataset={self.dataset} | ",
                f"ticker={self.ticker} | " if self.ticker is not None else None,
                f"file_id={self.file_id}",
            )
            if p is not None
        )

    @classmethod
    def from_bronze(cls, result: BronzeResult) -> "DatasetInjestion":
        request = result.request
        start_time = cls._normalize_datetime(result.now)
        end_time = cls._calculate_end_time(start_time, result.elapsed_microseconds)
        filename = request.bronze_relative_filename
        bronze_rows = len(result.content or [])
        return cls(
            run_id=request.run_id,
            file_id=request.file_id,
            domain=request.recipe.domain,
            source=request.recipe.source,
            dataset=request.recipe.dataset,
            discriminator=request.recipe.discriminator,
            ticker=request.ticker,
            bronze_from_date=cls._parse_date(result.first_date),
            bronze_to_date=cls._parse_date(result.last_date),
            bronze_filename=filename,
            bronze_error=result.error,
            bronze_rows=bronze_rows,
            bronze_injest_start_time=start_time,
            bronze_injest_end_time=end_time,
            bronze_can_promote=result.canPromoteToSilverWith(allows_empty_content=request.allows_empty_content),
            bronze_payload_hash=result.hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "file_id": self.file_id,
            "domain": self.domain,
            "source": self.source,
            "dataset": self.dataset,
            "discriminator": self.discriminator,
            "ticker": self.ticker,
            "bronze_from_date": self.bronze_from_date,
            "bronze_to_date": self.bronze_to_date,
            "bronze_filename": self.bronze_filename,
            "bronze_error": self.bronze_error,
            "bronze_rows": self.bronze_rows,
            "bronze_injest_start_time": self.bronze_injest_start_time,
            "bronze_injest_end_time": self.bronze_injest_end_time,
            "bronze_can_promote": self.bronze_can_promote,
            "bronze_payload_hash": self.bronze_payload_hash,
            "silver_from_date": self.silver_from_date,
            "silver_to_date": self.silver_to_date,
            "silver_tablename": self.silver_tablename,
            "silver_errors": self.silver_errors,
            "silver_rows_created": self.silver_rows_created,
            "silver_rows_updated": self.silver_rows_updated,
            "silver_rows_failed": self.silver_rows_failed,
            "silver_injest_start_time": self.silver_injest_start_time,
            "silver_injest_end_time": self.silver_injest_end_time,
            "silver_can_promote": self.silver_can_promote,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "DatasetInjestion":
        return cls(
            run_id=str(row.get("run_id") or ""),
            file_id=str(row.get("file_id") or ""),
            domain=str(row.get("domain") or ""),
            source=str(row.get("source") or ""),
            dataset=str(row.get("dataset") or ""),
            discriminator=row.get("discriminator"),
            ticker=row.get("ticker"),
            bronze_from_date=row.get("bronze_from_date"),
            bronze_to_date=row.get("bronze_to_date"),
            bronze_filename=row.get("bronze_filename"),
            bronze_error=row.get("bronze_error"),
            bronze_rows=row.get("bronze_rows") or 0,
            bronze_injest_start_time=row.get("bronze_injest_start_time"),
            bronze_injest_end_time=row.get("bronze_injest_end_time"),
            bronze_can_promote=row.get("bronze_can_promote"),
            bronze_payload_hash=row.get("bronze_payload_hash"),
            silver_from_date=row.get("silver_from_date"),
            silver_to_date=row.get("silver_to_date"),
            silver_tablename=row.get("silver_tablename"),
            silver_errors=row.get("silver_errors"),
            silver_rows_created=row.get("silver_rows_created") or 0,
            silver_rows_updated=row.get("silver_rows_updated") or 0,
            silver_rows_failed=row.get("silver_rows_failed") or 0,
            silver_injest_start_time=row.get("silver_injest_start_time"),
            silver_injest_end_time=row.get("silver_injest_end_time"),
            silver_can_promote=row.get("silver_can_promote"),
        )

    def to_bronze_manifest_row(self) -> BronzeManifestRow:
        return BronzeManifestRow(
            bronze_file_id=self.file_id,
            run_id=self.run_id,
            domain=self.domain,
            source=self.source,
            dataset=self.dataset,
            discriminator=self.discriminator or "",
            ticker=self.ticker or "",
            file_path_rel=self.bronze_filename or "",
            coverage_from_date=self.bronze_from_date,
            coverage_to_date=self.bronze_to_date,
            ingested_at=self.bronze_injest_start_time or datetime.utcnow(),
        )

    @staticmethod
    def _parse_date(value: str | date | None) -> date | None:
        if isinstance(value, date):
            return value
        if not value:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if "T" in normalized:
            normalized = normalized.split("T", 1)[0]
        try:
            return date.fromisoformat(normalized)
        except ValueError:
            return None

    @staticmethod
    def _normalize_datetime(value: datetime | str | None) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.utcnow()
        return None

    @staticmethod
    def _calculate_end_time(start: datetime | None, micros: int | None) -> datetime | None:
        if start is None:
            return None
        if not micros:
            return start
        return start + timedelta(microseconds=micros)
