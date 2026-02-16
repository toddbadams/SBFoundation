from __future__ import annotations
from datetime import date, datetime
import json
from pathlib import Path
import re
import typing

from sbfoundation.run.dtos.result_mapper import FMPResultMapper
from sbfoundation.run.dtos.bronze_result import BronzeResult
from sbfoundation.run.dtos.run_request import RunRequest
from sbfoundation.dataset.models.dataset_recipe import DatasetRecipe
from sbfoundation.settings import *
from sbfoundation.infra.logger import LoggerFactory


class ResultFileAdapter:

    def __init__(self, logger_factory: typing.Optional[LoggerFactory] = None):
        self.logger = (logger_factory or LoggerFactory()).create_logger(self.__class__.__name__)

    def write(self, result: BronzeResult) -> Path:
        """Persist a result to Bronze layer following append-only semantics."""
        # Add validation from BronzeFileWriter
        if result is None or result.request is None:
            raise ValueError("Bronze persistence requires a result with a request.")

        # Use consistent path construction (relative + Folders.data_absolute_path)
        from sbfoundation.folders import Folders

        rel_path = Path(result.request.bronze_relative_filename)
        abs_path = Folders.data_absolute_path() / str(rel_path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        # Use write_bytes for consistency with BronzeFileWriter
        payload = result.to_dict()
        payload_bytes = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        abs_path.write_bytes(payload_bytes)

        # Use clearer log message
        self.logger.info(f"Bronze payload persisted: {abs_path}")

        return abs_path

    def read(self, file: Path) -> BronzeResult:
        with file.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict) and "request" in payload:
            return self._read_bronze_result_payload(payload, file)

        result = FMPResultMapper.from_serializable_dict(payload)
        result.request = None
        return result

    def _read_bronze_result_payload(self, payload: dict[str, typing.Any], file: Path) -> BronzeResult:
        # Bronze files are append-only; tolerate bad payloads so replay can resume safely.
        request_payload = payload.get("request")
        request: RunRequest | None = None
        if isinstance(request_payload, dict):
            normalized_payload = dict(request_payload)
            recipe_payload = request_payload.get("recipe")
            if isinstance(recipe_payload, dict):
                try:
                    normalized_payload["recipe"] = DatasetRecipe.from_row(recipe_payload)
                except Exception as exc:
                    self.logger.warning(f"bronze recipe parse failed | filename={file} | error={exc}")
            try:
                request = RunRequest.from_row(normalized_payload)
            except Exception as exc:
                self.logger.warning(f"bronze request parse failed | filename={file} | error={exc}")
        else:
            self.logger.warning(f"bronze request missing | filename={file}")

        result = BronzeResult(now=self._parse_now(payload.get("now")), request=request)
        result.elapsed_microseconds = payload.get("elapsed_microseconds") or 0
        result.headers = FMPResultMapper.headers_from_string(payload.get("headers"))
        result.status_code = payload.get("status_code") or 0
        result.reason = payload.get("reason")
        result.content = payload.get("content") or []
        result.error = payload.get("error")
        result.first_date = payload.get("first_date")
        result.last_date = payload.get("last_date")
        # hash is never serialized by BronzeResult.to_dict(); recompute from content
        # so canPromoteToSilverWith() evaluates correctly when reading files back.
        if result.content:
            result.hash = result._hash(result.content)
        return result

    def _parse_now(self, value: typing.Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.utcnow()
        return datetime.utcnow()

    def files_to_date_dict(self, files: typing.Iterable[Path]) -> dict[date, Path]:
        if not files:
            return {}

        out: dict[date, Path] = {}
        # Map YYYY-MM-DD at the end of the filename stem to the Path
        pattern = re.compile(r"(\d{4}-\d{2}-\d{2})(?:T.*)?$")

        for p in files:
            m = pattern.search(p.stem)
            if not m:
                continue
            try:
                out[date.fromisoformat(m.group(1))] = p
            except ValueError:
                # Ignores files without a terminal ISO date token.
                continue
        return out

    def get_file_paths(self, path: Path) -> typing.Iterable[Path]:
        # Allow callers to pass a single file while still supporting Bronze
        # folder traversal when replaying historical pulls.
        files: typing.Iterable[Path]
        if path.is_file():
            files = [path]
        else:
            files = path.rglob("*.json")

        return files

    def latest_date(self, path: Path) -> date:
        if path is None or not path.exists():
            return None

        files: typing.Iterable[Path] = self.get_file_paths(path)
        latest: date | None = None

        for file in files:
            try:
                result = self.read(file)
            except Exception:
                # Not a result file (or corrupted) — ignore.
                continue

            raw_last = getattr(result, "last_date", None)
            if not raw_last:
                continue

            # Be tolerant of datetime-ish strings; only keep the YYYY-MM-DD part.
            token = str(raw_last).strip()
            if "T" in token:
                token = token.split("T", 1)[0]

            try:
                d = date.fromisoformat(token)
            except ValueError:
                continue

            if latest is None or d > latest:
                latest = d

        return latest

    def get_tuple_from_content(self, path: Path, attrs: list[str]) -> list[tuple[str, str]]:
        if path is None or not path.exists():
            return []

        files: typing.Iterable[Path] = self.get_file_paths(path)
        out: list[tuple[str, str]] = []

        for file in files:
            try:
                result = self.read(file)
            except Exception:
                # Not a result file (or corrupted) — ignore.
                continue

            rows = getattr(result, "content", None)
            if not isinstance(rows, list):
                continue

            for row in rows:
                if not isinstance(row, dict):
                    continue

                values: list[str] = []
                missing = False

                for attr in attrs:
                    v = row.get(attr)
                    if v is None:
                        missing = True
                        break
                    values.append(str(v))

                if missing:
                    continue

                out.append(tuple(values))

        return out
