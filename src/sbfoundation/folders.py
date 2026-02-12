from sbfoundation.settings import *
from pathlib import Path


class Folders:

    @staticmethod
    def _data_root() -> Path:
        return Path(DATA_ROOT_FOLDER)

    @staticmethod
    def _repo_root() -> Path:
        return Path(REPO_ROOT_FOLDER)

    @staticmethod
    def bronze_result_absolute_path(domain: str, source: str, dataset: str) -> Path:
        if not domain or not source or not dataset:
            raise ValueError("domain/source/dataset are required and must be non-empty.")
        return Folders._data_root() / BRONZE_FOLDER / domain / source / dataset

    @staticmethod
    def bronze_result_relative_path(domain: str, source: str, dataset: str) -> Path:
        if not domain or not source or not dataset:
            raise ValueError("domain/source/dataset are required and must be non-empty.")
        return Path(BRONZE_FOLDER) / domain / source / dataset

    @staticmethod
    def logs_absolute_path() -> Path:
        return Folders._data_root() / LOG_FOLDER

    @staticmethod
    def dataset_keymap_absolute_path() -> Path:
        return Folders._repo_root() / DATASET_KEYMAP_FOLDER

    @staticmethod
    def duckdb_absolute_path() -> Path:
        return Folders._data_root() / DUCKDB_FOLDER

    @staticmethod
    def repo_absolute_path() -> Path:
        return Folders._repo_root()

    @staticmethod
    def data_absolute_path() -> Path:
        return Folders._data_root()

    @staticmethod
    def migration_absolute_path() -> Path:
        return Folders._repo_root() / MIGRATIONS_FOLDER
