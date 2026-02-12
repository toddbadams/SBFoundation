from __future__ import annotations

import os
from pathlib import Path
import json

import pytest

from data_layer.dtos.dto_registry import DTORegistry
from data_layer.dataset.services.dataset_service import DatasetService


def _write_keymap(repo_root: Path, payload: dict) -> Path:
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / os.environ.get("DATASET_KEYMAP_FILENAME", "dataset_keymap.yaml")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _base_dataset_entry(dataset: str) -> dict[str, object]:
    return {
        "domain": "company",
        "source": "fmp",
        "dataset": dataset,
        "silver_schema": "config",
        "silver_table": "config_table",
        "ticker_scope": "per_ticker",
        "key_cols": ["ticker"],
    }


def test_missing_ticker_scope_rejected(patch_folders: tuple[Path, Path]) -> None:
    _, repo_root = patch_folders
    payload = {"version": 1, "datasets": [dict(_base_dataset_entry("company-profile"), **{"ticker_scope": None})]}
    _write_keymap(repo_root, payload)
    with pytest.raises(ValueError, match="ticker_scope"):
        DatasetService(today="2026-01-01", plan="basic")


def test_duplicate_entries_raise(patch_folders: tuple[Path, Path]) -> None:
    _, repo_root = patch_folders
    entry = _base_dataset_entry("company-profile")
    payload = {"version": 1, "datasets": [entry, entry]}
    _write_keymap(repo_root, payload)
    with pytest.raises(ValueError, match="Duplicate dataset mapping"):
        DatasetService(today="2026-01-01", plan="basic")


def test_strict_registry_mismatch_bubbles(monkeypatch: pytest.MonkeyPatch, patch_folders: tuple[Path, Path]) -> None:
    _, repo_root = patch_folders
    payload = {"version": 1, "datasets": [_base_dataset_entry("company-profile")]}
    _write_keymap(repo_root, payload)
    monkeypatch.setenv("STRICT_DTO_REGISTRY", "1")
    monkeypatch.setattr(
        "data_layer.dtos.dto_registry.DTO_REGISTRY",
        DTORegistry({}),
    )
    service = DatasetService(today="2026-01-01", plan="basic")
    with pytest.raises(ValueError, match="DTO registry mismatch"):
        service.validate_dto_registry()


def test_load_returns_expected_entries(patch_folders: tuple[Path, Path]) -> None:
    _, repo_root = patch_folders
    payload = {
        "version": 2,
        "datasets": [
            dict(
                _base_dataset_entry("company-profile"),
                discriminator="summary",
                ticker_scope="global",
                key_cols=["ticker"],
            )
        ],
    }
    _write_keymap(repo_root, payload)
    keymap = DatasetService(today="2026-01-01", plan="basic").load_dataset_keymap()
    assert keymap.version == 2
    assert len(keymap.entries) == 1
    assert keymap.entries[0].dataset == "company-profile"
    assert keymap.entries[0].ticker_scope == "global"
