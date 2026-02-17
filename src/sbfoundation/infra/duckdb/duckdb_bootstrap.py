from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import duckdb

from sbfoundation.infra.logger import LoggerFactory, SBLogger
from sbfoundation.folders import Folders
from sbfoundation.settings import DUCKDB_FILENAME


# Schema initialization DDL - idempotent, safe to run multiple times
SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS silver;
"""

OPS_FILE_INGESTIONS_DDL = """
CREATE TABLE IF NOT EXISTS ops.file_ingestions (
    run_id VARCHAR NOT NULL,
    file_id VARCHAR NOT NULL,
    domain VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    discriminator VARCHAR,
    ticker VARCHAR,
    bronze_filename VARCHAR,
    bronze_error VARCHAR,
    bronze_rows BIGINT,
    bronze_from_date DATE,
    bronze_to_date DATE,
    bronze_injest_start_time TIMESTAMP,
    bronze_injest_end_time TIMESTAMP,
    bronze_can_promote BOOLEAN,
    bronze_payload_hash VARCHAR,
    silver_tablename VARCHAR,
    silver_errors VARCHAR,
    silver_rows_created BIGINT,
    silver_rows_updated BIGINT,
    silver_rows_failed BIGINT,
    silver_from_date DATE,
    silver_to_date DATE,
    silver_injest_start_time TIMESTAMP,
    silver_injest_end_time TIMESTAMP,
    silver_can_promote BOOLEAN,
    PRIMARY KEY (run_id, file_id)
);
"""

OPS_INSTRUMENT_CATALOG_DDL = """
CREATE TABLE IF NOT EXISTS ops.instrument_catalog (
    symbol VARCHAR NOT NULL,
    instrument_type VARCHAR NOT NULL,
    source_endpoint VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    discovered_at TIMESTAMP NOT NULL,
    last_enriched_at TIMESTAMP,
    PRIMARY KEY (symbol, instrument_type)
);
"""


class DuckDbBootstrap:
    """Manages a single DuckDB connection, initializes schema on first connect, and exposes scoped transactions.

    The bootstrap is responsible for creating the DuckDB file, initializing the schema
    (ops/silver schemas and core ops tables) on the first connect, and managing
    the connection lifecycle.

    Schema initialization is idempotent and uses CREATE IF NOT EXISTS, making it safe
    to call multiple times and compatible with existing databases."""
    def __init__(self, logger: SBLogger | None = None, conn: duckdb.DuckDBPyConnection | None = None) -> None:
        self._logger = logger or LoggerFactory().create_logger(self.__class__.__name__)
        duckdb_path = Folders.duckdb_absolute_path()
        duckdb_path.mkdir(parents=True, exist_ok=True)
        self._conn = conn or duckdb.connect(duckdb_path / DUCKDB_FILENAME)
        self._owns_connection = conn is None
        self._schema_initialized = False

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get the database connection, initializing schema on first call.

        Returns:
            DuckDB connection ready for use
        """
        if not self._schema_initialized:
            self._initialize_schema()
            self._schema_initialized = True
        return self._conn

    def _initialize_schema(self) -> None:
        """Create schemas and core ops tables if they don't exist.

        Idempotent - safe to call multiple times. Uses CREATE IF NOT EXISTS
        to ensure existing databases are not disrupted. All DDL runs in a
        single transaction for atomicity.

        Creates:
        - ops, silver schemas
        - ops.file_ingestions table (core metadata table)
        - ops.instrument_catalog table (operational instrument metadata)

        Raises:
            Exception: If schema creation fails (transaction is rolled back)
        """
        try:
            self._conn.execute("BEGIN")
            self._conn.execute(SCHEMA_DDL)
            self._conn.execute(OPS_FILE_INGESTIONS_DDL)
            self._conn.execute(OPS_INSTRUMENT_CATALOG_DDL)
            self._conn.execute("COMMIT")
            self._logger.debug("Schema initialization complete")
        except Exception as e:
            self._conn.execute("ROLLBACK")
            self._logger.error(f"Schema initialization failed: {e}")
            raise

    def close(self) -> None:
        """Close the database connection if owned by this bootstrap."""
        if self._conn is None:
            return
        if self._owns_connection:
            self._conn.close()
        self._conn = None
        self._schema_initialized = False

    def __enter__(self) -> "DuckDbBootstrap":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        conn = self.connect()
        conn.execute("BEGIN")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    @contextmanager
    def ops_transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with self.transaction() as conn:
            yield conn

    @contextmanager
    def silver_transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with self.transaction() as conn:
            yield conn
