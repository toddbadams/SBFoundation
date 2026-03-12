-- Phase J: run integrity layer
-- Replaces the coarser ops.coverage_index with per-file, per-layer granularity.

CREATE TABLE IF NOT EXISTS ops.run_integrity (
    integrity_id     VARCHAR     PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
    run_id           VARCHAR     NOT NULL,
    layer            VARCHAR     NOT NULL,   -- 'bronze', 'silver', 'gold'
    domain           VARCHAR,
    source           VARCHAR,
    dataset          VARCHAR,
    discriminator    VARCHAR     NOT NULL DEFAULT '',
    ticker           VARCHAR     NOT NULL DEFAULT '',
    file_id          VARCHAR,
    status           VARCHAR     NOT NULL,   -- 'ok', 'skipped', 'failed'
    rows_in          BIGINT,
    rows_out         BIGINT,
    error_message    VARCHAR,
    checked_at       TIMESTAMP   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_run_integrity_run_id  ON ops.run_integrity (run_id);
CREATE INDEX IF NOT EXISTS idx_run_integrity_status  ON ops.run_integrity (status);
CREATE INDEX IF NOT EXISTS idx_run_integrity_dataset ON ops.run_integrity (domain, dataset);
