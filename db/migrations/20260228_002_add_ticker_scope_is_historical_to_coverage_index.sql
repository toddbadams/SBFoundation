-- Migration: Add ticker_scope and is_historical columns to ops.coverage_index
-- Date: 2026-02-28
-- Purpose: Enables splitting coverage data by ticker_scope (global | per_ticker)
--          and is_historical (true = dataset fetches a date-range via from/to or limit query vars).
--          Drives the 4-section Home and Global Overview dashboard pages.

-- Note: DuckDB does not support ADD COLUMN with NOT NULL DEFAULT in a single statement.
-- Add nullable columns, then back-fill defaults for any existing rows.
ALTER TABLE ops.coverage_index ADD COLUMN ticker_scope  VARCHAR;
ALTER TABLE ops.coverage_index ADD COLUMN is_historical BOOLEAN;
UPDATE ops.coverage_index SET ticker_scope  = 'per_ticker' WHERE ticker_scope  IS NULL;
UPDATE ops.coverage_index SET is_historical = FALSE         WHERE is_historical IS NULL;
