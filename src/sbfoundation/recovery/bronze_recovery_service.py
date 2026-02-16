from __future__ import annotations

from pathlib import Path

from sbfoundation.folders import Folders
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.infra.result_file_adaptor import ResultFileAdapter
from sbfoundation.ops.dtos.file_injestion import DatasetInjestion
from sbfoundation.recovery.bronze_recovery_repo import BronzeRecoveryRepo
from sbfoundation.settings import BRONZE_FOLDER


class BronzeRecoveryService:
    """Detects a missing or empty ops.file_ingestions table and rebuilds it
    by scanning every Bronze JSON file on disk.

    Intended to be called once per run at the entry point of SBFoundationAPI.run().
    All writes are idempotent (MERGE) so calling recover() on an already-populated
    database is safe.
    """

    def __init__(
        self,
        repo: BronzeRecoveryRepo | None = None,
        file_adapter: ResultFileAdapter | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._repo = repo or BronzeRecoveryRepo()
        self._owns_repo = repo is None
        self._file_adapter = file_adapter or ResultFileAdapter()

    def needs_recovery(self) -> bool:
        """Return True when ops.file_ingestions is empty and bronze files exist.

        Both conditions must hold:
        - The ops table has zero rows (fresh or wiped DB).
        - At least one .json file exists under the bronze root folder.
        """
        try:
            if not self._repo.is_ops_ingestions_empty():
                return False
        except Exception as exc:
            self._logger.warning("Recovery check failed — skipping: %s", exc)
            return False

        bronze_root = self._bronze_root()
        if not bronze_root.exists():
            return False

        return any(bronze_root.rglob("*.json"))

    def recover(self) -> int:
        """Scan all bronze JSON files and upsert rows into ops.file_ingestions.

        Returns the number of records successfully upserted.
        Files that cannot be parsed (corrupt, legacy format, no request field)
        are skipped and counted as failures — they do not abort the scan.
        """
        bronze_root = self._bronze_root()
        self._logger.info("Starting bronze recovery scan | bronze_root=%s", bronze_root)

        files = list(self._file_adapter.get_file_paths(bronze_root))
        total = len(files)
        ok = 0
        failed = 0

        for file in files:
            try:
                result = self._file_adapter.read(file)
                if result is None or result.request is None:
                    failed += 1
                    continue
                ingestion = DatasetInjestion.from_bronze(result)
                self._repo.upsert_ingestion(ingestion)
                ok += 1
            except Exception as exc:
                self._logger.warning("Recovery skipped file | file=%s | error=%s", file, exc)
                failed += 1

        self._logger.info(
            "Bronze recovery complete | total=%d ok=%d failed=%d", total, ok, failed
        )
        return ok

    def close(self) -> None:
        if self._owns_repo:
            self._repo.close()

    @staticmethod
    def _bronze_root() -> Path:
        return Folders.data_absolute_path() / BRONZE_FOLDER


__all__ = ["BronzeRecoveryService"]
