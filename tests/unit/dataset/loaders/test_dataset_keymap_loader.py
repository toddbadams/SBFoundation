from __future__ import annotations

import os
from pathlib import Path
import pytest
import yaml

from data_layer.dataset.loaders.dataset_keymap_loader import DatasetKeymapLoader


def test_load_raw_keymap_success(patch_folders: tuple[Path, Path]) -> None:
    """Test successful loading of valid YAML."""
    _, repo_root = patch_folders
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    keymap_file = config_dir / "dataset_keymap.yaml"
    keymap_file.write_text("version: 1\ndatasets: []", encoding="utf-8")

    result = DatasetKeymapLoader.load_raw_keymap()

    assert result == {"version": 1, "datasets": []}


def test_load_raw_keymap_file_not_found(patch_folders: tuple[Path, Path]) -> None:
    """Test FileNotFoundError when keymap doesn't exist."""
    with pytest.raises(FileNotFoundError, match="Dataset keymap file not found"):
        DatasetKeymapLoader.load_raw_keymap()


def test_load_raw_keymap_respects_env_var(
    patch_folders: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that DATASET_KEYMAP_FILENAME environment variable is respected."""
    _, repo_root = patch_folders
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    custom_filename = "custom_keymap.yaml"
    monkeypatch.setenv("DATASET_KEYMAP_FILENAME", custom_filename)

    keymap_file = config_dir / custom_filename
    keymap_file.write_text("version: 2\ndatasets: []", encoding="utf-8")

    result = DatasetKeymapLoader.load_raw_keymap()

    assert result["version"] == 2


def test_load_raw_datasets_extracts_section(patch_folders: tuple[Path, Path]) -> None:
    """Test load_raw_datasets extracts only datasets section."""
    _, repo_root = patch_folders
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    keymap_file = config_dir / "dataset_keymap.yaml"
    content = """version: 1
datasets:
  - domain: company
    dataset: test
gold:
  dims: []
"""
    keymap_file.write_text(content, encoding="utf-8")

    result = DatasetKeymapLoader.load_raw_datasets()

    assert len(result) == 1
    assert result[0]["domain"] == "company"
    assert result[0]["dataset"] == "test"


def test_load_raw_keymap_empty_file(patch_folders: tuple[Path, Path]) -> None:
    """Test handling of empty YAML file."""
    _, repo_root = patch_folders
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    keymap_file = config_dir / "dataset_keymap.yaml"
    keymap_file.write_text("", encoding="utf-8")

    result = DatasetKeymapLoader.load_raw_keymap()

    assert result == {}


def test_load_raw_keymap_malformed_yaml(patch_folders: tuple[Path, Path]) -> None:
    """Test that malformed YAML raises appropriate error."""
    _, repo_root = patch_folders
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    keymap_file = config_dir / "dataset_keymap.yaml"
    keymap_file.write_text("{{invalid yaml", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        DatasetKeymapLoader.load_raw_keymap()


def test_load_raw_datasets_missing_section(patch_folders: tuple[Path, Path]) -> None:
    """Test that load_raw_datasets returns empty list when datasets section is missing."""
    _, repo_root = patch_folders
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    keymap_file = config_dir / "dataset_keymap.yaml"
    keymap_file.write_text("version: 1\ngold:\n  dims: []", encoding="utf-8")

    result = DatasetKeymapLoader.load_raw_datasets()

    assert result == []
