from __future__ import annotations

from sbfoundation.infra.duckdb.duckdb_bootstrap import DuckDbBootstrap
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.ops.dtos.file_injestion import DatasetInjestion
from sbfoundation.ops.infra.duckdb_ops_repo import DuckDbOpsRepo


class BronzeRecoveryRepo:
    """DB-side concerns for bronze recovery: checks whether the ops table is
    empty and delegates ingestion upserts to DuckDbOpsRepo.

    A single DuckDbBootstrap instance is shared between this class and the
    embedded DuckDbOpsRepo so both use the same underlying connection.
    """

    def __init__(
        self,
        bootstrap: DuckDbBootstrap | None = None,
        ops_repo: DuckDbOpsRepo | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap()
        self._owns_bootstrap = bootstrap is None
        self._ops_repo = ops_repo or DuckDbOpsRepo(bootstrap=self._bootstrap)

    def is_ops_ingestions_empty(self) -> bool:
        """Return True when ops.file_ingestions has zero rows."""
        conn = self._bootstrap.connect()
        result = conn.execute("SELECT COUNT(*) FROM ops.file_ingestions").fetchone()
        return (result[0] if result else 0) == 0

    def upsert_ingestion(self, ingestion: DatasetInjestion) -> None:
        """Persist a recovered ingestion row via MERGE."""
        self._ops_repo.upsert_file_ingestion(ingestion)

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()


__all__ = ["BronzeRecoveryRepo"]
