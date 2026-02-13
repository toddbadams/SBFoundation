from __future__ import annotations

from requests.structures import CaseInsensitiveDict
from typing import Any

from sbfoundation.run.dtos.bronze_result import BronzeResult


class FMPResultMapper:
    """Map :class:`FMPResult` objects to serializable representations."""

    # todo: reconcile mapper naming so it reflects broader Silver persistence
    # needs (not just FMP) as outlined in docs/AI_context/architecture.md.md.

    @staticmethod
    def to_serializable_dict(result: BronzeResult, *, include_payload: bool = True) -> dict[str, Any]:
        record = {
            "elapsed_microseconds": result.elapsed_microseconds,
            "headers": FMPResultMapper.headers_to_string(result.headers),
            "status_code": result.status_code,
            "reason": result.reason,
            "content": result.content,
            "ticker": result.ticker,
            "path": result.path,
            "datatype": result.datatype,
            "hash": result.hash,
            "date_key": result.date_key,
            "first_date": result.first_date,
            "last_date": result.last_date,
            "error": result.error,
            "filename": result.filename,
        }
        if not include_payload:
            record.pop("content", None)
        return record

    @staticmethod
    def to_storage_record(result: BronzeResult) -> dict[str, Any]:
        """Representation used for Bronze JSON storage (no payload)."""
        return FMPResultMapper.to_serializable_dict(result, include_payload=False)

    @staticmethod
    def from_serializable_dict(record: dict[str, Any]) -> BronzeResult:
        result = BronzeResult.__new__(BronzeResult)  # type: ignore[call-arg]

        # Core fields
        result.elapsed_microseconds = record.get("elapsed_microseconds", 0)
        result.headers = FMPResultMapper.headers_from_string(record.get("headers"))
        result.status_code = record.get("status_code", 0)
        result.reason = record.get("reason", "")
        result.content = record.get("content") or []

        # Metadata
        result.ticker = record.get("ticker")
        result.path = record.get("path")
        result.datatype = record.get("datatype")
        result.hash = record.get("hash")
        result.date_key = record.get("date_key")
        result.first_date = record.get("first_date")
        result.last_date = record.get("last_date")
        result.error = record.get("error")
        result.filename = record.get("filename")

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def headers_to_string(headers: CaseInsensitiveDict) -> str:
        return "; ".join(f"{key}={value}" for key, value in headers.items())

    @staticmethod
    def headers_from_string(header_str: str | None) -> CaseInsensitiveDict:
        headers = CaseInsensitiveDict()
        if not header_str:
            return headers

        for part in header_str.split("; "):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            headers[key] = value
        return headers
