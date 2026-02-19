-- Migration: 20260218_002_drop_ops_instrument_catalog
-- Description: Drop the ops.instrument_catalog table. The instrument catalog was
-- dead code — sync_from_silver_tables() was never called, so the table was always
-- empty. Universe discovery now uses silver.fmp_stock_list directly, filtered by
-- exchange via silver.fmp_company_profile. The DuckDB bootstrap no longer creates
-- this table.

DROP TABLE IF EXISTS ops.instrument_catalog;
