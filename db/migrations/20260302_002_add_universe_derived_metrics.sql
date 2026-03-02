-- Migration: 20260302_002
-- Adds silver.universe_derived_metrics table.
--
-- Stores nightly-computed eligibility metrics per symbol:
--   computed_market_cap   : price × shares_outstanding (more consistent than screener value)
--   avg_dollar_volume_30d : 30-trading-day average of (close × volume)
--   avg_dollar_volume_90d : 90-trading-day average of (close × volume)
--   is_actively_trading   : survival flag from screener or derived logic
--   data_coverage_score   : fraction of expected daily bars present (0.0–1.0, trailing 1 year)
--
-- Keyed by (symbol, as_of_date); idempotent on rerun via UPSERT.

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
