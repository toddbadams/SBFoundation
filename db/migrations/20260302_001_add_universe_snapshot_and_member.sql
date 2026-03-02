-- Migration: 20260302_001
-- Adds silver.universe_snapshot and silver.universe_member tables.
--
-- universe_snapshot: one row per (universe_name, as_of_date) recording the
--   filter hash and member count for that day's universe build.
--
-- universe_member: one row per (universe_name, as_of_date, symbol) — the
--   full membership list for each versioned snapshot.
--
-- Both tables use UPSERT semantics (PRIMARY KEY enforcement) so reruns are
-- idempotent.

CREATE TABLE IF NOT EXISTS silver.universe_snapshot (
    universe_name   VARCHAR     NOT NULL,
    as_of_date      DATE        NOT NULL,
    filter_hash     VARCHAR(64) NOT NULL,
    member_count    INTEGER     NOT NULL,
    run_id          VARCHAR     NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (universe_name, as_of_date)
);

CREATE TABLE IF NOT EXISTS silver.universe_member (
    universe_name   VARCHAR     NOT NULL,
    as_of_date      DATE        NOT NULL,
    filter_hash     VARCHAR(64) NOT NULL,
    symbol          VARCHAR     NOT NULL,
    run_id          VARCHAR     NOT NULL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (universe_name, as_of_date, symbol)
);
