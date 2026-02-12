from __future__ import annotations

import os
from pathlib import Path
import yaml

from folders import Folders
from settings import DATASET_KEYMAP_FILENAME


class DatasetKeymapLoader:
    """Pure file I/O utility for loading dataset keymap YAML.

    Responsibilities:
    - Path resolution using Folders + environment variable
    - YAML file reading and parsing
    - Returns raw dict/list structures

    Does NOT include:
    - Schema validation
    - Business logic
    - Domain model construction
    """

    @staticmethod
    def load_raw_keymap() -> dict:
        """Load the complete dataset keymap as a raw dictionary.

        Returns:
            dict: Raw YAML payload containing version, datasets, and gold sections.
                  Returns empty dict {} if file is empty.

        Raises:
            FileNotFoundError: If keymap file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        path = DatasetKeymapLoader._resolve_keymap_path()
        if not path.exists():
            raise FileNotFoundError(f"Dataset keymap file not found: {path}")

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    @staticmethod
    def load_raw_datasets() -> list[dict]:
        """Load just the datasets section as raw dictionaries.

        Returns:
            list[dict]: List of raw dataset entry dictionaries.
                        Returns empty list [] if datasets section is missing.
        """
        payload = DatasetKeymapLoader.load_raw_keymap()
        return payload.get("datasets") or []

    @staticmethod
    def _resolve_keymap_path() -> Path:
        """Resolve the keymap file path using Folders and environment variable.

        Returns:
            Path: Absolute path to the dataset keymap YAML file.
                  Uses DATASET_KEYMAP_FILENAME env var if set, otherwise uses default.
        """
        filename = os.environ.get("DATASET_KEYMAP_FILENAME", DATASET_KEYMAP_FILENAME)
        return Folders.dataset_keymap_absolute_path() / filename
