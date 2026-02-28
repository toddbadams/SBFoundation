-- Migration: Create ops.coverage_index table
-- Date: 2026-02-28
-- Purpose: Materialized coverage index aggregated from ops.file_ingestions.
--          Refreshed after every pipeline run via CoverageIndexService.
--          Drives the coverage CLI and Streamlit dashboard.

CREATE TABLE IF NOT EXISTS ops.coverage_index (
    domain               VARCHAR NOT NULL,
    source               VARCHAR NOT NULL,
    dataset              VARCHAR NOT NULL,
    discriminator        VARCHAR NOT NULL DEFAULT '',
    ticker               VARCHAR NOT NULL DEFAULT '',

    -- Timeseries coverage extent
    min_date             DATE,
    max_date             DATE,
    coverage_ratio       DOUBLE,       -- actual_days / expected_days; NULL for snapshots

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

    -- Bookkeeping
    updated_at           TIMESTAMP NOT NULL,

    PRIMARY KEY (domain, source, dataset, discriminator, ticker)
);
