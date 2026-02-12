from __future__ import annotations

import pytest
from pathlib import Path

from sbfoundation.folders import Folders


@pytest.fixture
def patch_folders(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    data_root = tmp_path / "data"
    repo_root = tmp_path / "repo"
    data_root.mkdir()
    repo_root.mkdir()

    monkeypatch.setattr(Folders, "_data_root", staticmethod(lambda: data_root))
    monkeypatch.setattr(Folders, "_repo_root", staticmethod(lambda: repo_root))

    return data_root, repo_root
