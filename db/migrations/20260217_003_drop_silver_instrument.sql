-- Migration: Drop silver.instrument table
-- Date: 2026-02-17
-- Purpose: Remove silver.instrument after migrating to ops.instrument_catalog
-- Note: This table was never populated and has been replaced by ops.instrument_catalog

DROP TABLE IF EXISTS silver.instrument;
