from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from sbfoundation.infra.result_file_adaptor import ResultFileAdapter
from tests.unit.helpers import make_bronze_result


def test_write_and_read_roundtrip(patch_folders) -> None:
    adapter = ResultFileAdapter()
    result = make_bronze_result()
    file_path = adapter.write(result)
    assert file_path.exists()
    rehydrated = adapter.read(file_path)
    assert rehydrated.status_code == result.status_code
    assert rehydrated.request is not None


def test_read_missing_request_returns_partial_result(patch_folders, tmp_path: Path) -> None:
    adapter = ResultFileAdapter()
    payload = {"status_code": 202, "reason": "Accepted", "path": None}
    file_path = tmp_path / "orphan.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    result = adapter.read(file_path)
    assert result.status_code == 202
    assert result.request is None


def test_parse_now_variations(patch_folders) -> None:
    adapter = ResultFileAdapter()
    iso = "2026-01-27T12:00:00"
    assert adapter._parse_now(iso) == datetime.fromisoformat(iso)
    now = datetime.utcnow()
    assert adapter._parse_now(now) == now
    fallback = adapter._parse_now("not-a-date")
    assert isinstance(fallback, datetime)


def test_files_to_date_dict_filters(patch_folders, tmp_path: Path) -> None:
    good_file = tmp_path / "result-2026-01-01.json"
    bad_file = tmp_path / "result-no-date.json"
    good_file.write_text("{}", encoding="utf-8")
    bad_file.write_text("{}", encoding="utf-8")
    adapter = ResultFileAdapter()
    lookup = adapter.files_to_date_dict([good_file, bad_file])
    assert Path(lookup[datetime(2026, 1, 1).date()]) == good_file


def test_write_requires_request(patch_folders) -> None:
    """Validate that write() raises ValueError when result or request is None."""
    adapter = ResultFileAdapter()
    result = make_bronze_result()
    result.request = None
    with pytest.raises(ValueError):
        adapter.write(result)


def test_write_persists_payload(patch_folders) -> None:
    """Verify JSON payload is correctly persisted with expected structure."""
    adapter = ResultFileAdapter()
    result = make_bronze_result()
    file_path = adapter.write(result)

    from sbfoundation.folders import Folders

    target = Folders.data_absolute_path() / result.request.bronze_relative_filename
    assert target.exists()
    assert file_path == target

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["request"]["run_id"] == result.request.run_id
