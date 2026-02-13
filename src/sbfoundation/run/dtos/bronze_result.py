import csv
from dataclasses import dataclass
from datetime import date, datetime
import io
import hashlib
import json
import typing

import requests
from requests.structures import CaseInsensitiveDict

from sbfoundation.dtos.bronze_to_silver_dto import BronzeToSilverDTO
from sbfoundation.run.dtos.run_request import RunRequest
from sbfoundation.settings import *


@dataclass(slots=True, kw_only=True)
class BronzeResult(BronzeToSilverDTO):
    request: RunRequest
    now: datetime

    elapsed_microseconds: int = 0
    headers: CaseInsensitiveDict = None
    status_code: int = 0
    reason: str = None
    content: list[dict[str, typing.Any]] = None
    hash: str = None
    error: str = None
    first_date: str = None
    last_date: str = None
    ticker: str = None
    path: str = None
    datatype: str = None
    date_key: str = None
    filename: str = None

    def _hash(self, payload: json) -> str:
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    @property
    def msg(self) -> str:
        return f"{self.request.msg} | status_code={self.status_code}"

    def add_response(self, response: requests.models.Response):
        # Capture the transport envelope and payload so Bronze remains a faithful
        # system of record per docs/AI_context/architecture.md.md.
        if "apikey" in self.request.query_vars:
            self.request.query_vars["apikey"] = ["***"]

        self.elapsed_microseconds = response.elapsed.microseconds
        self.headers = response.headers
        self.status_code = response.status_code
        self.reason = response.reason
        if len(response.content) > 0 and self.status_code == 200:
            if self.request.query_vars.get("datatype") == "csv":
                content = response.content.decode("utf-8")
                try:
                    reader = csv.DictReader(io.StringIO(content))
                    self.content = [row for row in reader]
                except csv.Error as e:
                    self.error = "Failed to parse CSV response: {e}"
                    raise e
            else:
                self.content = response.json()
        else:
            self.content = response.text

        if len(response.content) == 0 or (isinstance(self.content, dict) and len(self.content.keys()) == 0):
            self.error = "Response appears to have no data.  Returning empty List."
            self.content = []

        self.hash = self._hash(self.content)
        self.first_date = self._boundary_date(find_latest=False)
        self.last_date = self._boundary_date(find_latest=True)

    def _boundary_date(self, find_latest: bool) -> str:
        """
        Internal helper to find either the earliest or latest date.

        - If find_latest is False, returns earliest date.
        - If find_latest is True, returns latest date.
        - Assumes self.content is a list[dict] and values at self.request.recipe.date_key
          are ISO8601 strings.
        - Always returns a date string (YYYY-MM-DD).
        - If self.request.recipe.date_key is None or no valid dates are found, returns today's date.
        """
        # If we don't know which key to use, fall back to today
        if self.request.recipe.date_key is None:
            return date.today().isoformat()

        if not getattr(self, "content", None):
            return date.today().isoformat()

        boundary: date | None = None

        for row in self.content:
            if not isinstance(row, dict):
                continue

            raw_value = row.get(self.request.recipe.date_key)
            if not raw_value:
                continue

            val = raw_value.strip()

            # Normalize 'Z' to '+00:00' so fromisoformat can handle it
            if val.endswith("Z"):
                val = val[:-1] + "+00:00"

            try:
                dt = datetime.fromisoformat(val)
            except ValueError:
                # Skip unparseable values just in case
                continue

            d = dt.date()

            if boundary is None:
                boundary = d
            else:
                if find_latest and d > boundary:
                    boundary = d
                elif not find_latest and d < boundary:
                    boundary = d

        # Fall back to today if nothing valid found
        return (boundary or date.today()).isoformat()

    # ---- BRONZE ACCEPTANCE GATE ----#
    @property
    def is_valid_bronze(self) -> bool:
        """
        Bronze acceptance gate (write-time).

        A record is valid Bronze if:
        - transport fields exist: path, url, headers, status_code, reason, elapsed_microseconds
        - content is a list (possibly empty)
        - now is present (ISO8601 string, or datetime depending on how you set it)

        NOTE:
        - This does NOT enforce status_code == 200 (Bronze is permissive).
        - This does NOT reject records with error set (Bronze stores failures too).
        """

        # --- core request/response metadata --- #
        headers = getattr(self, "headers", None)
        if headers is None or not hasattr(headers, "items"):
            self.error = "INVALID HEADERS"
            return False

        if not isinstance(getattr(self, "status_code", None), int):
            self.error = "INVALID STATUS CODE"
            return False

        if not isinstance(getattr(self, "reason", None), str):
            self.error = "INVALID REASON"
            return False

        if not isinstance(getattr(self, "elapsed_microseconds", None), int):
            self.error = "INVALID ELAPSED TIME"
            return False

        # --- payload normalization contract --- #
        content = getattr(self, "content", None)
        if not isinstance(content, list):
            self.error = "INVALID CONTENT"
            return False

        # allow empty list; validate element shape if present
        if len(content) > 0 and not all(isinstance(r, dict) for r in content):
            self.error = "INVALID CONTENT"
            return False

        # --- now timestamp --- #
        now_val = getattr(self, "now", None)
        # accept either ISO string or datetime (depends on how you’re setting it today)
        if now_val is None:
            self.error = "INVALID NOW TIME"
            return False

        if not isinstance(now_val, (str, datetime)):
            self.error = "INVALID NOW TIME"
            return False

        if isinstance(now_val, str) and not now_val.strip():
            self.error = "INVALID NOW TIME"
            return False

        return True

    # ---- SILVER PROMOTION GATE ----#
    @property
    def canPromoteToSilver(self) -> bool:
        """
        Default Silver promotion gate (read-time).

        NOTE:
        - Empty payloads are NOT eligible by default.
        - For the rare datasets that *allow* empty payloads, use:
            result.canPromoteToSilverWith(allows_empty_content=True)

        Silver eligibility rules:
        - status_code == 200
        - error is None
        - hash is present
        - content is non-empty OR dataset contract allows empty payloads
        """
        return self.canPromoteToSilverWith(allows_empty_content=False)

    def canPromoteToSilverWith(self, *, allows_empty_content: bool) -> bool:
        """
        Variant that lets the dataset contract drive whether empty payloads may promote.
        """
        if self.status_code != 200:
            return False

        if self.error is not None:
            return False

        if not self.hash:
            return False

        content = getattr(self, "content", None)
        if not isinstance(content, list):
            return False

        if len(content) > 0:
            return True

        return allows_empty_content

    # ---- MAPPING ----#
    def to_dict(self) -> dict[str, typing.Any]:
        return self._to_snake_dict(
            {
                "request": self.request.to_dict(),
                "now": self.now.isoformat(),
                "elapsed_microseconds": self.elapsed_microseconds,
                "headers": None if not self.headers else self.hdr_to_str(self.headers),
                "status_code": self.status_code,
                "reason": self.reason,
                "content": self.content,
                "error": self.error,
                "first_date": self.first_date,
                "last_date": self.last_date,
            }
        )

    @classmethod
    def from_row(cls, row: typing.Mapping[str, typing.Any], ticker: typing.Optional[str] = None) -> "BronzeResult":
        row = cls._normalize_row(row)
        return cls(
            request=cls.dto(row, "request", RunRequest),
            now=cls.d(row, "now"),
            elapsed_microseconds=cls.i(row, "elapsed_microseconds"),
            headers=cls.hdrs(row, "headers") or 0,
            status_code=cls.i(row, "status_code") or 0,
            reason=cls.s(row, "reason"),
            content=row.get("content"),
            error=cls.s(row, "error"),
        )
