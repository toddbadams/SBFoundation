from __future__ import annotations

from contextlib import contextmanager
import threading
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

DATASET_WATERMARKS_DDL = """
CREATE TABLE IF NOT EXISTS ops.dataset_watermarks (
    domain        VARCHAR NOT NULL,
    source        VARCHAR NOT NULL,
    dataset       VARCHAR NOT NULL,
    discriminator VARCHAR NOT NULL DEFAULT '',
    ticker        VARCHAR NOT NULL DEFAULT '',
    backfill_floor_date DATE,
    PRIMARY KEY (domain, source, dataset, discriminator, ticker)
);
"""

OPS_COVERAGE_INDEX_DDL = """
CREATE TABLE IF NOT EXISTS ops.coverage_index (
    domain               VARCHAR NOT NULL,
    source               VARCHAR NOT NULL,
    dataset              VARCHAR NOT NULL,
    discriminator        VARCHAR NOT NULL DEFAULT '',
    ticker               VARCHAR NOT NULL DEFAULT '',

    -- Timeseries coverage extent
    min_date             DATE,
    max_date             DATE,
    coverage_ratio       DOUBLE,

    -- Expected window (universe.from_date → today at refresh time)
    expected_start_date  DATE,
    expected_end_date    DATE,

    -- Volume
    total_files          INTEGER NOT NULL DEFAULT 0,
    promotable_files     INTEGER NOT NULL DEFAULT 0,
    ingestion_runs       INTEGER NOT NULL DEFAULT 0,
    silver_rows_created  INTEGER NOT NULL DEFAULT 0,
    silver_rows_failed   INTEGER NOT NULL DEFAULT 0,

    -- Errors
    error_count          INTEGER NOT NULL DEFAULT 0,
    error_rate           DOUBLE,

    -- Recency
    last_ingested_at     TIMESTAMP,
    last_run_id          VARCHAR,

    -- Snapshot-specific (date_key IS NULL datasets)
    snapshot_count       INTEGER NOT NULL DEFAULT 0,
    last_snapshot_date   DATE,
    age_days             INTEGER,

    -- Classification
    is_timeseries        BOOLEAN NOT NULL DEFAULT TRUE,
    ticker_scope         VARCHAR  NOT NULL DEFAULT 'per_ticker',
    is_historical        BOOLEAN  NOT NULL DEFAULT FALSE,

    -- Bookkeeping
    updated_at           TIMESTAMP NOT NULL,

    PRIMARY KEY (domain, source, dataset, discriminator, ticker)
);
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


UNIVERSE_SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS silver.universe_snapshot (
    universe_name   VARCHAR     NOT NULL,
    as_of_date      DATE        NOT NULL,
    filter_hash     VARCHAR(64) NOT NULL,
    member_count    INTEGER     NOT NULL,
    run_id          VARCHAR     NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (universe_name, as_of_date)
);
"""

UNIVERSE_MEMBER_DDL = """
CREATE TABLE IF NOT EXISTS silver.universe_member (
    universe_name   VARCHAR     NOT NULL,
    as_of_date      DATE        NOT NULL,
    filter_hash     VARCHAR(64) NOT NULL,
    symbol          VARCHAR     NOT NULL,
    run_id          VARCHAR     NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (universe_name, as_of_date, symbol)
);
"""

UNIVERSE_DERIVED_METRICS_DDL = """
CREATE TABLE IF NOT EXISTS silver.universe_derived_metrics (
    symbol                  VARCHAR     NOT NULL,
    as_of_date              DATE        NOT NULL,
    computed_market_cap     DOUBLE      NULL,
    avg_dollar_volume_30d   DOUBLE      NULL,
    avg_dollar_volume_90d   DOUBLE      NULL,
    is_actively_trading     BOOLEAN     NULL,
    data_coverage_score     DOUBLE      NULL,
    run_id                  VARCHAR     NOT NULL,
    ingested_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, as_of_date)
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
        duckdb_name: str = str(duckdb_path / DUCKDB_FILENAME)
        self._logger.info(f"connecting | DuckDb={duckdb_name}")
        self._conn = conn or duckdb.connect(
            str(duckdb_path / DUCKDB_FILENAME),
            config={
                "threads": 4,
                "memory_limit": "8GB",
                "checkpoint_threshold": "64MB",
            },
        )

        self._logger.info(f"Connected | DuckDb={duckdb_name}")
        self._owns_connection = conn is None
        self._schema_initialized = False
        self._conn_lock = threading.Lock()  # Protect connection for concurrent writes

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

        Raises:
            Exception: If schema creation fails (transaction is rolled back)
        """
        try:
            self._conn.execute("BEGIN")
            self._conn.execute(SCHEMA_DDL)
            self._conn.execute(OPS_FILE_INGESTIONS_DDL)
            self._conn.execute(DATASET_WATERMARKS_DDL)
            self._conn.execute(OPS_COVERAGE_INDEX_DDL)
            self._conn.execute(UNIVERSE_SNAPSHOT_DDL)
            self._conn.execute(UNIVERSE_MEMBER_DDL)
            self._conn.execute(UNIVERSE_DERIVED_METRICS_DDL)
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

    _LOCK_TIMEOUT_SECONDS = 60

    @contextmanager
    def transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Execute a transaction with thread-safe connection locking.

        DuckDB connections are not thread-safe, so we serialize access
        to the connection using a lock. This ensures concurrent Bronze
        workers can safely write to ops.file_ingestions.

        Raises TimeoutError if the lock cannot be acquired within
        _LOCK_TIMEOUT_SECONDS (default 60s) to surface hangs quickly
        rather than blocking indefinitely.
        """
        acquired = self._conn_lock.acquire(timeout=self._LOCK_TIMEOUT_SECONDS)
        if not acquired:
            raise TimeoutError(f"Timed out waiting for DuckDB connection lock after {self._LOCK_TIMEOUT_SECONDS}s")
        try:
            conn = self.connect()
            conn.execute("BEGIN")
            try:
                yield conn
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            self._conn_lock.release()

    @contextmanager
    def read_connection(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Acquire the connection lock for a read-only query.

        DuckDB in-process connections are not thread-safe, so all access—reads
        and writes—must be serialized through the same lock to prevent
        'Invalid Input Error: Attempting to execute an unsuccessful or closed
        pending query result' errors under concurrent workers.

        Raises TimeoutError if the lock cannot be acquired within
        _LOCK_TIMEOUT_SECONDS to surface hangs quickly.
        """
        acquired = self._conn_lock.acquire(timeout=self._LOCK_TIMEOUT_SECONDS)
        if not acquired:
            raise TimeoutError(f"Timed out waiting for DuckDB connection lock after {self._LOCK_TIMEOUT_SECONDS}s")
        try:
            yield self.connect()
        finally:
            self._conn_lock.release()

    @contextmanager
    def ops_transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with self.transaction() as conn:
            yield conn

    @contextmanager
    def silver_transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with self.transaction() as conn:
            yield conn
