from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from sbfoundation.folders import Folders
from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.maintenance.duckdb_bootstrap import DuckDbBootstrap


SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS ops.schema_migrations (
    version     VARCHAR     PRIMARY KEY,
    name        VARCHAR     NOT NULL,
    applied_at  TIMESTAMP   NOT NULL,
    checksum    VARCHAR(64) NOT NULL
);
"""


class MigrationRunner:
    """Applies SQL migration files from db/migrations/ to DuckDB.

    Tracks applied migrations in ops.schema_migrations. Idempotent — already-applied
    migrations are skipped. Migrations are applied in filename order (YYYYMMDD_NNN_...).
    """

    def __init__(
        self,
        bootstrap: DuckDbBootstrap | None = None,
        migrations_path: Path | None = None,
        logger: SBLogger | None = None,
    ) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        self._bootstrap = bootstrap or DuckDbBootstrap(logger=self._logger)
        self._owns_bootstrap = bootstrap is None
        self._migrations_path = migrations_path or Folders.migration_absolute_path()

    def close(self) -> None:
        if self._owns_bootstrap:
            self._bootstrap.close()

    def run(self) -> list[str]:
        """Apply all pending migrations. Returns list of applied migration versions."""
        self._ensure_migrations_table()
        applied = self._applied_versions()
        pending = self._pending_files(applied)

        if not pending:
            self._logger.info("No pending migrations")
            return []

        self._logger.info(f"Applying {len(pending)} migration(s)")
        newly_applied: list[str] = []

        for path in pending:
            version, name = self._parse_filename(path.name)
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            try:
                with self._bootstrap.transaction() as conn:
                    conn.execute(sql)
                    conn.execute(
                        "INSERT OR IGNORE INTO ops.schema_migrations (version, name, applied_at, checksum) VALUES (?, ?, ?, ?)",
                        [version, name, datetime.now(timezone.utc), checksum],
                    )
                self._logger.info(f"Applied migration: {version} — {name}")
                newly_applied.append(version)
            except Exception as exc:
                self._logger.error(f"Migration failed: {version} — {exc}")
                raise

        return newly_applied

    def _ensure_migrations_table(self) -> None:
        with self._bootstrap.transaction() as conn:
            conn.execute(SCHEMA_MIGRATIONS_DDL)

    def _applied_versions(self) -> set[str]:
        with self._bootstrap.read_connection() as conn:
            try:
                rows = conn.execute("SELECT version FROM ops.schema_migrations").fetchall()
                return {row[0] for row in rows}
            except Exception:
                return set()

    def _pending_files(self, applied: set[str]) -> list[Path]:
        if not self._migrations_path.exists():
            return []
        files = sorted(
            f for f in self._migrations_path.glob("*.sql")
            if self._parse_filename(f.name)[0] not in applied
        )
        return files

    @staticmethod
    def _parse_filename(filename: str) -> tuple[str, str]:
        """Parse '20260309_001_create_gold_static_dims.sql' → ('20260309_001', 'create_gold_static_dims')."""
        stem = filename.removesuffix(".sql")
        parts = stem.split("_", 2)
        if len(parts) >= 3:
            version = f"{parts[0]}_{parts[1]}"
            name = parts[2]
        elif len(parts) == 2:
            version = f"{parts[0]}_{parts[1]}"
            name = ""
        else:
            version = stem
            name = ""
        return version, name
